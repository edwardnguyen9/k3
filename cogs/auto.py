import discord, json, asyncio, datetime, re, math
from discord import app_commands
from discord.ext import commands, tasks
from io import BytesIO
from pprint import pformat
from typing import Optional

from bot.bot import Kiddo
from assets import idle, postgres, config
from utils import utils, embeds, errors, checks

@checks.guild_bill()
@checks.mod_only()
class Auto(commands.GroupCog, group_name='update'):
    def __init__(self, bot: Kiddo):
        self.bot = bot
        self.is_first_ready = True
        # Market scan
        self.last_scanned = None
        self.market_channel = {}
        # Donation log
        self.donation_log = {}
        self.donation_leaderboard = {}
        self.recently_donated = None
        # Offline features
        # Guild Bill only feature
        self.adventure_time = None

    @commands.Cog.listener()
    async def on_ready(self):
        if self.is_first_ready:
            await self.bot.loading()
            donation_cfg = config.event_config['donator']
            for k, v in donation_cfg.items():
                if k.isdecimal():
                    self.donation_log[k] = self.bot.get_channel(v['donation:channel'])
                    self.donation_leaderboard[k] = [
                        self.bot.get_channel(v['donation:leaderboard']),
                        self.bot.get_channel(v['donation:leaderboard:monthly']),
                    ]
            for s in self.bot.guilds:
                try:
                    self.market_channel[s.id] = s.get_channel(config.config[s.id]['channels']['announce:market'])
                except KeyError:
                    continue
            print(self.__class__.__name__, 'is ready')
            self.is_first_ready = False

    @commands.Cog.listener()
    async def on_message(self, message):
        if self.is_first_ready: return
        elif not message.guild: return
        elif message.guild.id == 821988363308630068:
            for k, v in self.donation_log.items():
                if v:
                    await self.check_donation(message, k, wrong_channel=(message.channel.id != v.id))
        # Guild Bill adventure
        elif message.channel.id == 819497629439754271:
            res = re.findall('(\w+) set to (\d).(\d+)', message.content)  # type: ignore
            if len(res) == 9:
                charts = await self.bot.redis.keys('chart:*')
                luck = [int(message.created_at.timestamp())]
                for r in res[:8]: luck += [f'{r[1]}.{r[2]}']
                async with self.bot.redis.pipeline(transaction=True) as pipe:
                    pipe.lpush('lucklog', json.dumps(luck)).delete(*charts)  # type: ignore
                    await pipe.execute()
                await self.bot.log_event('luck', message='\n'.join(map(lambda x: f'{x[0]} - {x[1]}.{x[2]}', res[:8])))
        elif message.channel.id == config.guild_bill['guild_announcement'] and message.author.id == 424606447867789312 and len(message.mentions) == 0:
            embed = await self.get_guild_adv_info(message)
            if embed is not None:
                server = message.guild
                channel = server.get_channel(config.guild_bill['officer_channel'])
                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, _, message):
        if self.is_first_ready: return
        elif not message.guild: return
        elif message.guild.id == 821988363308630068:
            for k, v in self.donation_log.items():
                if v:
                    await self.check_donation(message, k, wrong_channel=(message.channel.id != v.id))

    @tasks.loop(minutes=5)
    async def guild_adventure_ping(self):
        if self.adventure_time is None:
            at = await self.bot.redis.get('adventure')
            print(type(at))
            self.adventure_time = int(at) if at is not None else 0
        if self.adventure_time > self.guild_adventure_ping.next_iteration.timestamp() or self.adventure_time == 0:
            return
        else:
            await discord.utils.sleep_until(datetime.datetime.fromtimestamp(self.adventure_time))
            server = self.bot.get_guild(config.guild_bill['server'])
            channel = server.get_channel(config.guild_bill['officer_channel'])  # type: ignore
            await channel.send(  # type: ignore
                '<@&821999684100685824> Your guild adventure has finished.'
            )
            await self.bot.redis.delete('adventure')
            self.adventure_time = 0

    @tasks.loop(minutes=3)
    async def market_scan(self):
        ms_history = await self.bot.redis.hgetall('scan:market')
        moved, removed, update_price, update_date, unchanged, sold, new = {}, {}, {}, {}, {}, {}, {}
        old_ids, ignore_ids, notification = [], [], []

        async def black_market(entries, tag):
            notifs = {
                'deleted': '{number} item{plural} destroyed',
                'sold': '{number} item{plural} sold',
                'added': '{number} item{plural} found',
                'changed': '{number} item{plural} had their price changed',
                'moved': '{number} item{plural} traded to another user',
                'removed': '{number} item{plural} removed from market',
            }
            if len(entries) > 0:
                pages = []
                items = utils.pager([v for _, v in entries.items()], 5)
                for i in items:
                    pages.append(embeds.market(i, tag))
                notification.append(notifs[tag].format(number=len(entries), plural='s' if len(entries) > 1 else ''))
                for g in self.market_channel:
                    for i in range(0, len(pages), 10):
                        await self.market_channel[g].send(embeds=pages[i:i+10])

        # Get cached items
        for k, v in ms_history.items():
            ms_history[k] = json.loads(v)
            if k not in ['last']:
                old_ids.append(int(k))
        last = ms_history.pop('last')
        # Fetch cached item data
        for i in range(0, len(old_ids), 250):
            query = idle.queries['scan_old'].format(
                ids=','.join(map(str, old_ids[i:i+250]))
            )
            try:
                (res, status) = await self.bot.idle_query(query)
            except Exception:
                return
            if status != 200: return
            for i in res:
                # Remove
                item = ms_history.pop(str(i['id']))
                if i['owner'] != item['owner']:
                    moved[i['id']] = item
                    item['current_owner'] = i['owner']
                elif not i['market']:
                    removed[i['id']] = item
                else:
                    new_item = utils.get_market_entry(i)
                    if new_item['price'] != item['price']:
                        ignore_ids.append(i['id'])
                        new_item['old_price'] = item['price']
                        update_price[i['id']] = new_item
                    elif new_item['published'] != item['published']:
                        ignore_ids.append(i['id'])
                        update_date[i['id']] = new_item
                    else:
                        unchanged[i['id']] = item
            await asyncio.sleep(3)
        await black_market(ms_history, 'deleted')
        await black_market(removed, 'removed')
        time = self.last_scanned or (discord.utils.utcnow() - datetime.timedelta(minutes=3))
        self.last_scanned = discord.utils.utcnow()
        if len(moved) > 0:
            try:
                (res, status) = await self.bot.idle_query(idle.queries['scan_moved'].format(
                    time=time.strftime('%Y-%m-%dT%H:%M:%S'),
                    ids=','.join([str(i) for i in moved.keys()])
                ))
            except Exception:
                return
            if status != 200: return
            for i in res:
                sold[i['item']] = moved.pop(i['item'])
                sold[i['item']]['sold'] = utils.get_market_entry(i)['sold']
        await black_market(moved, 'moved')
        await black_market(sold, 'sold')
        await black_market(update_price, 'changed')
        while True:
            try:
                (res, status) = await self.bot.idle_query(idle.queries['scan_new'].format(idmax=last))
            except Exception:
                return
            if status != 200: return
            for i in res:
                if i['item'] not in ignore_ids and (
                    (i['item']['hand'] == 'both' and i['item']['damage'] >= 90)
                    or (i['item']['hand'] != 'both' and i['item']['damage'] + i['item']['armor'] >= 41)
                ):
                    new[i['item']['id']] = utils.get_market_entry(i)
            if len(res) > 0:
                last = res[-1]['id']
            if len(res) < 250: break
            await asyncio.sleep(3)
        await black_market(new, 'added')
        update = {'last': last}
        for k, v in update_price.items():
            update[str(k)] = json.dumps(utils.get_market_entry(v, True))
        for k, v in update_date.items():
            update[str(k)] = json.dumps(utils.get_market_entry(v, True))
        for k, v in unchanged.items():
            update[str(k)] = json.dumps(utils.get_market_entry(v, True))
        for k, v in new.items():
            update[str(k)] = json.dumps(utils.get_market_entry(v, True))
        async with self.bot.redis.pipeline(transaction=True) as pipe:
            pipe.delete('scan:market').hset('scan:market', mapping=update)  # type: ignore
            await pipe.execute()
        if len(notification) > 0:
            await self.bot.log_event('background', message='Market scanned on <t:{}:F>, {}.'.format(
                int(self.last_scanned.timestamp()), ', '.join(notification)
            ))

    @tasks.loop(time=[
        datetime.time(hour=1 + i//2, minute=15 + 30 * i % 2) for i in range(40)
    ])
    async def update_fav_list(self):
        if self.update_fav_list.is_running(): return
        time = discord.utils.utcnow().day
        flist = await self.bot.redis.get('flist')
        if flist and int(flist) == time: return
        protected = await self.bot.pool.fetch(postgres.queries['all_fav'])
        for p in protected:
            if u:=discord.utils.get(self.bot.users, id=int(p['user'])):
                (res, status) = await self.bot.idle_query(idle.queries['fav'].format(ids=','.join([str(i) for i in p['protected']]), uid=u.id))
                if status == 200:
                    await self.bot.log_event('background', message='Update protected items for {}'.format(u))
                    updated = [i['id'] for i in res]
                    await self.bot.pool.execute(postgres.queries['update_fav'], u.id, updated)
            else:
                await self.bot.pool.execute(postgres.queries['delete_fav'], p['user'])
                await self.bot.log_event('background', message='Removed protected items of {}'.format(p['user']))
            if p != protected[-1]: await asyncio.sleep(3.5)
        await self.bot.redis.set('flist', time)
        await self.bot.log_event('background', message='Protected items updated successfully')

    @tasks.loop(time=[
        datetime.time(hour=3 + i//2, minute=30 * i % 2) for i in range(40)
    ])
    async def update_stats(self):
        for guild in idle.weapon_fetching_guilds:
            day = await self.bot.redis.hget('scan:weapons', str(guild))
            if not day or int(day) != discord.utils.utcnow().day:
                if await self.update_guild_stats(guild):
                    break

    @tasks.loop(time=datetime.time(hour=23, minute=58))
    async def update_activity(self):
        if self.update_activity.is_running(): return
        await self.update_guild_activity()

    @tasks.loop(time=datetime.time(hour=0, minute=0, second=5))
    async def update_donator_roles(self):
        time = discord.utils.utcnow()
        if time.day != 1: return
        month = (time.month - 2) % 12 + 1
        for g in self.donation_log:
            if self.donation_log[g]: await self.remove_donator_roles(self.donation_log[g])
        for g in self.donation_log:
            if await self.bot.redis.hget(f'd{month}-{g}', 'month'):
                await self.add_donator_roles(g, month)
        await self.update_guild_activity(False)

    @app_commands.command(name='activity')
    async def _activity(self, interaction: discord.Interaction):
        '''
        Manually fetch member activity data
        '''
        await interaction.response.defer(thinking=True, ephemeral=True)
        res = await self.update_guild_activity()
        await interaction.followup.send('Activity updated {}successfully.'.format('' if res else 'un'))

    @app_commands.describe(guild='The guild to fetch')
    @app_commands.choices(
        guild=[app_commands.Choice(name=str(i), value=i) for i in idle.weapon_fetching_guilds]
    )
    @app_commands.command(name='stats')
    async def _stats(self, interaction: discord.Interaction, guild: int):
        '''
        Manually fetch member weapons data
        '''
        await interaction.response.defer(thinking=True, ephemeral=True)
        if self.update_stats.is_running():
            await interaction.followup.send('This task is already running.')
        else:
            res = await self.update_guild_stats(guild)
            await interaction.followup.send('Weapon updated {}successfully.'.format('' if res else 'un'))

    @app_commands.describe(
        user='The member to update', amount='The amount to update', guild='The guild to update', month='The month to update (default to current month)'
    )
    @app_commands.command(name='donation')
    async def _donation(self, interaction: discord.Interaction, user: discord.User, amount: int, guild: int, month: Optional[app_commands.Range[int, 1, 12]] = None):
        '''
        Update guild donation
        '''
        await interaction.response.defer(thinking=True)
        if str(guild) not in self.donation_log:
            return await interaction.followup.send('Unable to find the provided guild ID in the registered list.')
        if month is None:
            month = datetime.datetime.now(datetime.timezone.utc).month
        await self.on_donate(None, user, amount, str(guild), month)
        await interaction.followup.send(
            '{} {}\'s donation in {}'.format(
                f'Added {amount} to' if amount > 0 else f'Remove {abs(amount)} from',
                user.mention, self.bot.idle_guilds[guild][0]
            )
        )

    @app_commands.describe(url='The link to the guild adventure message')
    @app_commands.command(name='adventure')
    async def _guild_adventure(self, interaction: discord.Interaction, url: str):
        '''
        Update guild adventure reminder
        '''
        await interaction.response.defer(thinking=True)
        res = re.findall('https://discord.com/channels/(\d+)/(\d+)/(\d+)', url)  # type: ignore
        server = discord.utils.get(self.bot.guilds, id=int(res[0][0]))
        if server is not None:
            channel = discord.utils.get(server.text_channels, id=int(res[0][1]))
            if channel is not None:
                message = await channel.fetch_message(int(res[0][2]))
                if message is not None:
                    embed = await self.get_guild_adv_info(message, interaction)
                    if embed is not None:
                        return await interaction.followup.send(embed=embed)
        await interaction.followup.send('Unable to get guild adventure information.')

    # Guild activity function

    async def update_guild_activity(self, log: bool = True):
        timestamp = discord.utils.utcnow()
        old_data = {}
        day = None
        old_data_raw = await self.bot.redis.hgetall('activity')
        if old_data_raw and log:
            # Not update if already did
            day = datetime.datetime.fromtimestamp(int(old_data_raw['date']), datetime.timezone.utc)
            if day.day == timestamp.day:
                return True
                    
            for i in old_data_raw:
                if i == 'date': continue
                old_data[i] = json.loads(old_data_raw[i])
            
            for guild in old_data:
                await self.bot.pool.executemany(postgres.queries['adv_update'], [[*i, day] for i in old_data[guild]])
        guilds = list(map(str, set(idle.weapon_fetching_guilds)))
        append = {}
        don_boards = {}
        don_guilds = []
        for i in range(0, len(guilds), 2):
            (res, status) = await self.bot.idle_query(idle.queries['guild'].format(id=','.join(guilds[i:i+2])))
            if status == 429:
                return False
            data = []
            for item in res:
                data += [ [item['user'], item['xp'], item['completed'] + item['deaths']] ]
            for guild in guilds[i:i+2]:
                append[guild] = json.dumps(data)
                if guild in self.donation_log:
                    don_boards[f'd{timestamp.month}-{guild}'] = monthly_board = await self.bot.redis.hgetall(f'd{timestamp.month}-{guild}')
                    for uid in monthly_board:
                        if uid.isdecimal(): monthly_board[uid] = json.loads(monthly_board[uid])
                    for item in res:
                        uid = str(item['user'])
                        if uid in monthly_board: monthly_board[uid][1] = utils.getlevel(item['xp'])
                        else: monthly_board[uid] = [0, utils.getlevel(item['xp'])]
                    for item in monthly_board: 
                        if item.isdecimal(): monthly_board[item] = json.dumps(monthly_board[item])
                    await self.bot.log_event('background', message='Donator levels for {} updated'.format(self.bot.idle_guilds[guild][0]))
                    don_guilds.append(guild)
            if not guilds[i:i+2][-1] == guilds[-1]:
                await asyncio.sleep(3.5)
        append['date'] = int(timestamp.timestamp())
        async with self.bot.redis.pipeline(transaction=True) as pipe:
            if log:
                pipe.delete('activity').hset('activity', mapping=append)  # type: ignore
            for i in don_boards: pipe.hset(i, mapping=don_boards[i])  # type: ignore
            await pipe.execute()
        for g in don_guilds: await self.refresh_donation_leaderboard(g, True)
        if log:
            await self.bot.log_event('background', message='Member activity updated for {} at <t:{}>'.format(
                ', '.join([self.bot.idle_guilds[g][0] for g in guilds]), int(timestamp.timestamp())
            ))
        return True

    # Weapon fetching function

    async def update_guild_stats(self, guild: int):
        users = []
        await self.bot.log_event('background', message='Fetching guild members of {guild}'.format(guild=self.bot.idle_guilds[str(guild)][0]))
        try:
            (res, status) = await self.bot.idle_query(idle.queries['guild'].format(id=guild, custom='name,xp,race,class,atkmultiply,defmultiply'))
        except errors.ApiIsDead:
            return False
        if status == 429:
            return False
        for i in res:
            users.append(i['user'])
        updated_data = []
        for u in users:
            await asyncio.sleep(3.5)
            user = await self.bot.fetch_user(u)
            await self.bot.log_event('background', message='Fetching data of {} ({})'.format(user, user.id))
            _, _, to_update = await self.bot.get_equipped(user.id, manual_update=True)
            updated_data.append(to_update)
        await self.bot.pool.executemany(postgres.queries['update_weapons'], updated_data)
        await self.bot.log_event('background', message=await self.bot.pool.execute(postgres.queries['delete_profile'], discord.utils.utcnow() - datetime.timedelta(days=7)))
        await self.bot.log_event('background', message='Fetched {} members'.format(len(users)))
        await self.bot.redis.hset('scan:weapons', str(guild), discord.utils.utcnow().day)
        return True

    # Donation functions

    async def refresh_donation_leaderboard(self, guild: str, monthly: bool):
        """ Refresh donation leaderboard """
        # Get log channel ID
        log_channel = self.donation_log[guild]
        if not log_channel: raise ValueError('Guild {name} has not been registered.'.format(name=self.bot.idle_guilds[guild][0]))
        # Last updated time
        time = discord.utils.utcnow()
        # Get table name
        table = f'd{time.month}-{guild}' if monthly else f'd-{guild}'
        leaderboard_key = 'month' if monthly else 'all'
        leaderboard_message_id = 0
        # Load donation data
        data = await self.bot.redis.hgetall(table)
        if not data: return False
        donation = []
        for i in data:
            if i == leaderboard_key:
                leaderboard_message_id = int(data[i])
            else: donation.append((i, json.loads(data[i])))
        # Sort by donation
        donation.sort(key=lambda x: x[1][0], reverse=True)
        if monthly:
            # Sort by level
            donation.sort(key=lambda x: x[1][1], reverse = True)
            # Get monthly leaderboard
            channel = self.donation_leaderboard[guild][1] if guild in self.donation_leaderboard else None
            if not channel: raise ValueError('Guild {name} has no donation channel.'.format(name=self.bot.idle_guilds[guild][0]))
            embed = discord.Embed(
                title='{name}\'s {month} donation board'.format(name=self.bot.idle_guilds[guild][0], month=time.strftime('%B')),
                timestamp=time
            ).set_footer(
                text='This bot only registers donations made in #{.name}.'.format(log_channel),
                icon_url=log_channel.guild.icon.url
            )
            total_donation = 0
            fields = {}
            for i in donation:
                if i[1][0] > 0:
                    total_donation += i[1][0]
                    if i[1][1] not in fields: fields[i[1][1]] = []
                    fields[i[1][1]].append('> <@{id}>: ${amount:,d}'.format(id=i[0], amount=i[1][0]))
            embed.description = 'Total donation: **${:,d}**\nLast updated: <t:{}>'.format(total_donation, int(time.timestamp()))
            if len(fields) <= 20:
                for f in fields:
                    embed.add_field(
                        name='New donation' if f == 0 else f'Level {f}',
                        value='\n'.join(fields[f]),
                        inline=False
                    )
            else:
                new_fields = []
                for k, v in fields.items():
                    new_fields.append('**{}**\n{}'.format(f'Level {k}' if k > 0 else 'New donation', '\n'.join(v)))
                for i in range(0, len(new_fields), 2):
                    embed.add_field(
                        name='Donations',
                        value='\n---------------\n'.join(new_fields[i:i+2]),
                        inline=False
                    )
        else:
            log_data = config.event_config['donator'][guild] if 'guild' in config.event_config['donator'] else None
            if not log_data: raise ValueError('Guild {name} has not been registered.'.format(name=self.bot.idle_guilds[guild][0]))
            log_started = (
                datetime.datetime.fromtimestamp(log_data['timestamp'], datetime.timezone.utc)
                if 'timestamp' in log_data else discord.utils.utcnow()
            )
            channel = self.donation_leaderboard[guild][0] if guild in self.donation_leaderboard else None
            if not channel: raise ValueError('Guild {name} has no donation channel.'.format(name=self.bot.idle_guilds[guild][0]))
            
            total_donation = 0
            rank = 0
            board = []
            for i in donation:
                if i[1][0] > 0:
                    total_donation += i[1][0]
                    rank += 1
                    board.append(
                        '{rank}. <@{id}>: ${value:,d}'.format(
                            rank=rank, id=i[0], value=i[1][0]
                        )
                    )

            embed = discord.Embed(
                title='{name}\'s Top {top} Donation Leaderboard'.format(name=self.bot.idle_guilds[guild][0], top=len(board[:100])),
                timestamp=time
            ).set_footer(
                text='This bot only registers donations made in #{.name}.'.format(log_channel),
                icon_url=log_channel.guild.icon.url
            )

            embed.description = 'First entry: <t:{}:F>\nTotal donation: **${:,d}**\nLast updated: <t:{}>'.format(int(log_started.timestamp()), total_donation, int(time.timestamp()))
            for i in range(0, len(board[:100]), 10):
                embed.add_field(
                    name='#{}-#{}'.format(i+1, len(board[:i+10])),
                    value='\n'.join(board[i:i+10]),
                    inline=False
                )
        try:
            board = await channel.fetch_message(leaderboard_message_id)
            await board.edit(content=None, embed=embed)
            return True
        except discord.NotFound:
            board = await channel.send(embed=embed)
            await self.bot.redis.hsetnx(table, leaderboard_key, board.id)
            return True
        except discord.Forbidden:
            await self.bot.log_event(
                'background',
                message='Error creating new leaderboard message for {} in <@#{}>'.format(
                    self.bot.idle_guilds[guild][0], channel.id
                )
            )
            return False

    async def remove_donator_roles(self, channel: discord.TextChannel):
        roles = [(channel.guild.get_role(r[1]), r[2]) for r in utils.get_role_ids('donation')]
        for r in roles:
            if r[0]:
                members = list(r[0].members)
                for m in members: await m.remove_roles(r[0], reason='End of month')

    async def add_donator_roles(self, guild, month):
        channel = self.donation_log[guild]
        roles = [(channel.guild.get_role(r[1]), r[2]) for r in utils.get_role_ids('donation')]
        roles = [r for r in roles if r[0] is not None]
        try:
            (res, status) = await self.bot.idle_query(idle.queries['guild'].format(id=guild))
        except errors.ApiIsDead:
            res, status = [], 500
        if status != 200: res = []
        leader, members = None, {}
        if len(res) > 0:
            for i in res:
                if i['guildrank'] == 'Leader':
                    leader = channel.guild.get_member(i['user'])
                else:
                    members[str(i['user'])] = utils.getlevel(i['xp'])
        else:
            leader = channel.guild.get_member(self.bot.idle_guilds[guild][1])
        if leader is None: return
        await leader.add_roles(roles[0][0], reason='Guild leader')
        data = await self.bot.redis.hgetall(f'd{month}-{guild}')
        log = []
        for i in data:
            if not i == 'month':
                entry = json.loads(data[i])
                if len(members) > 0 and i in members:
                    entry[1] = members[i]
                if entry[0] > 0: log.append(entry)
                if int(i) == self.bot.idle_guilds[guild][1]: continue
                elif len(members) > 0 and i not in members: continue
                else:
                    member = channel.guild.get_member(int(i))
                    if not member: continue
                    elif len(roles) > 0 and entry[1] * roles[0][1] <= entry[0]:
                        await member.add_roles(roles[0][0], reason='Previous month donator')
                    elif len(roles) > 1 and entry[1] * roles[1][1] <= entry[0]:
                        await member.add_roles(roles[1][0], reason='Previous month donator')
                    elif len(roles) > 2 and entry[1] * roles[2][1] <= entry[0]:
                        await member.add_roles(roles[2][0], reason='Previous month donator')
                    elif len(roles) > 3 and entry[0] > 0:
                        await member.add_roles(roles[3][0], reason='Previous month donator')
        log.sort(key=lambda x: x[1], reverse=True)
        discord.File(
            filename='{}.txt'.format(f'd{month}-{guild}'),
            fp=BytesIO(pformat(log).encode())
        )
        await self.bot.log_event(
            'donation',
            message='Donation data of {guild}'.format(guild=self.bot.idle_guilds[guild][0]),
            file=discord.File(
                filename='{}.txt'.format(f'd{month}-{guild}'),
                fp=BytesIO(pformat(log).encode())
            )
        )
        await self.bot.redis.delete(f'd{month}-{guild}')

    async def check_donation(self, message: discord.Message, guild: str, month = None, wrong_channel: bool = False):
        """ Check if the donation is valid """
        if not message.guild or message.channel.id in [
            821999241999155201, # command channel
            833573201997070386, # intern channel
            824709803276369970, # lottery channel
            824719589819809792, # lottery ticket channel
            904018578603409439, # race track channel
        ]: return
        if month is None: month = discord.utils.utcnow().month
        if not message.author.bot:
            msg_content = message.content.lower().split(' ')
            if len(msg_content) < 3: return
            amount = -1
            if not message.content.startswith('$'): return
            elif msg_content[0] == '$guild' and msg_content[1] == 'invest' and msg_content[2].isdecimal():
                amount = int(msg_content[2])
            elif msg_content[0] == '$give' and msg_content[1].isdecimal():
                leader = message.guild.get_member(self.bot.idle_guilds[guild][1])
                if leader is None: return
                if (
                    re.match('^<@!?{}>$'.format(leader.id), msg_content[2])
                    or str(leader.id) == msg_content[2]
                    or (
                        (n:=leader.display_name) == msg_content[2]
                    ) or (
                        (n:=leader.name) == msg_content[2]
                    )
                ):
                    amount = int(msg_content[1])
            if amount > 0:
                if not wrong_channel:
                    await self.on_donate(message, message.author, amount, guild, month)  # type: ignore
                else:
                    embed = discord.Embed(
                        title='Warning!',
                        description=(
                            f'A donation might have been made in the wrong channel. '
                            f'If that is the case, use ```/donation update``` to add it to the log.'
                        ),
                        color= 0xFF0000,
                        timestamp=message.created_at
                    ).add_field(
                        name='Go to message', value=f'[Click here]({message.jump_url})'
                    )
                    await self.bot.custom_log(embed=embed, channel=827546848750338143)
        elif (
            message.author.id == 424606447867789312
            and self.recently_donated
            and (self.recently_donated + datetime.timedelta(seconds=10) > discord.utils.utcnow())
            and len(re.findall('\$(\d+)', message.content)) == 0  # type: ignore
            and '`other`' not in message.content
            and not wrong_channel
        ):
            embed = discord.Embed(
                title='Warning!',
                description=(
                    f'The bot might have added a false donation amount of whichever message that created the following error. '
                    f'If that is the case, use ```/donation update``` to subtract it from the log.'
                ),
                color= 0xFF0000,
                timestamp=message.created_at
            ).add_field(
                name='Go to message', value=f'[Click here]({message.jump_url})'
            )
            await self.bot.custom_log(embed=embed, channel=827546848750338143)

    async def on_donate(self, message, user: discord.User, amount: int, guild: str, month: int = -1):    
        """ Process valid donation message """
        this_month = discord.utils.utcnow().month
        if not 1 <= month <= 12: month = this_month
        if message: await message.add_reaction('\u23f3')
        uid = user.id
        await self.on_update_donation(uid, amount, guild, month)
        await self.on_update_donation(uid, amount, guild)
        if message:
            await message.remove_reaction("\u23f3", self.bot.user)
            await message.add_reaction('\u2705')
        if month == this_month:
            await self.refresh_donation_leaderboard(guild, True)
        await self.refresh_donation_leaderboard(guild, False)

    async def on_update_donation(self, uid, amount: int, guild: str, month = None):
        """ Update donation leaderboard """
        uid = str(uid)
        # Get table name
        table = f'd{month}-{guild}' if month else f'd-{guild}'
        # Try adding new donation
        if not await self.bot.redis.hsetnx(table, uid, json.dumps([amount, 0])):
            # If not new donation, get current user data
            data = await self.bot.redis.hget(table, uid)
            data = json.loads(data)  # type: ignore
            # Update data
            data[0] += amount
            await self.bot.redis.hset(table, uid, json.dumps(data))

    # Guild adventure functions

    async def get_guild_adv_info(self, message, ctx = None):
        lines = message.content.splitlines()
        if len(lines) != 6 or len(lines[3] > 0): return None
        res = re.findall('#(\d{4}),', lines[2]+',')  # type: ignore
        if len(res) == 0: return None
        guild_name = ' '.join(lines[0].split()[3:-1])[2:-2]
        ids = []
        for i in res:
            user = discord.utils.find(
                lambda x: x.discriminator == i and x.name in message.content,
                message.channel.members
            )
            if user: ids.append(user.id)  # type: ignore
        try:
            (res, _) = await self.bot.idle_query(idle.queries['xp'].format(id=','.join(map(str,ids))), ctx)
        except errors.KiddoException:
            res = []
        total_levels = sum([utils.getlevel(i['xp']) for i in res])
        time = re.findall('\*\*(\d+)(\s\w+\,\s)?(\d+)\:(\d+)\:(\d+)\*\*', lines[5])[0]  # type: ignore
        end_time = math.ceil((message.created_at + datetime.timedelta(days=int(time[0]), hours=int(time[2]), minutes=int(time[3]))).timestamp())
        await self.bot.redis.set('adventure', end_time)
        self.adventure_time = end_time
        diff = int(re.findall('\*\*(\d+)\*\*', lines[4])[0])  # type: ignore
        rewards = [
            'Adventure finish time: <t:{}:F>'.format(end_time),
            '```',
            '> Difficulty: **{:,d}**'.format(diff),
            '> Rewards: **${:,d}**'.format(0 if diff < 400 else 50000 * (diff//100 - 3)),
            '> Participants: **{:,d}**'.format(len(ids)),
            'Each participant received: **${:,d}**'.format(int(50000 * (diff//100 - 3) / len(ids))),
            '```',
        ]
        embed = discord.Embed(
            title=guild_name + (' | Total levels: {:,d}'.format(total_levels) if total_levels else ''),
            description='\n'.join(rewards),
            color=message.author.color.value,
            timestamp=message.created_at
        ).add_field(
            name='{}/{} found'.format(len(ids), len(res)),
            inline=False,
            value='$give {} {}'.format(
                int(50000 * (diff//100 - 3) / len(ids)),
                ' '.join(map(str,ids))
            )
        )
        for i in range(0, len(ids), 10):
            embed.add_field(
                name='{}-{}'.format(i+1, i+len(ids[i:i+10])),
                value='\n'.join(map(lambda x: f'<@{x}>',ids[i:i+10]))
            )
        embed.add_field(
            name='Go to message', value = '[Click here]({})'.format(message.jump_url), inline=False
        )
        return embed

async def setup(bot):
    await bot.add_cog(Auto(bot))