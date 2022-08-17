import discord, asyncio, datetime, random, json
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional

from bot.bot import Kiddo
from assets import raid, config, strings  # type: ignore
from classes import battle, ui
from utils import utils, embeds, checks  # type: ignore

async def announce(bot, msg, god=None):
    role = 'raid' if god is None else god
    announcements = []
    for s in bot.guilds:
        try:
            raid_channel = s.get_channel(config.config[s.id]['channels']['announce:raid'])
            if raid_channel:
                r = s.get_role(config.config[s.id]['roles'][f'announce:{role}']) if f'announce:{role}' in config.config[s.id]['roles'] else None
                announcements.append(await raid_channel.send('{} {}'.format(r.mention if r else '', msg)))
                if god is not None:
                    if c:=s.get_channel(config.config[s.id]['channels']['announce:god']):
                        announcements.append(await c.send('{} {}'.format(r.mention if r else '', msg)))
        except discord.Forbidden:
            print(s)
        except KeyError:
            continue
    return announcements

@checks.mod_only()
@checks.api_guilds()
class Raid(commands.GroupCog, group_name='raid'):
    def __init__(self, bot: Kiddo):
        self.bot = bot
        self.is_first_ready = True
        # Raid announcements
        self.announcements = []
        self.switch = False
        # Guild raid
        self.channel = None
        self.role = None
        self.banned = [367158268671557643]
        self.default_bosses = []
        self.arena_titles = []
        self.delayed_raid = {}
        # Raid instances
        self.private = False
        self.mode = None
        self.disqualified = []
        self.waitlist = []
        self.participants = {}
        self.register_message = None
        self.register = False
        self.autojoin = []
        self.delayed_messages = []
        self.boss = None
        # Belthazor data
        self.belthazor_prev = {}

    @commands.Cog.listener()
    async def on_ready(self):
        if self.is_first_ready:
            await self.bot.loading()
            server = self.bot.get_guild(config.guild_bill['server'])
            if server is not None:
                role = server.get_role(config.guild_bill['officer_role'])
                if role is not None: self.default_bosses = [u.id for u in role.members]
                arena = config.config[server.id]['misc']['arena']
                title_data = config.config[server.id]['misc']['arena:archive'][arena]['titles']
                titles = [server.get_role(config.config[server.id]['roles'][i[1]]) for i in title_data]
                self.arena_titles = [t for t in titles if t is not None]
                self.channel = server.get_channel(config.config[server.id]['channels']['raid'])
                self.role = server.get_role(config.config[server.id]['roles']['raid'])
            self.reset_announcements.start()
            delayed = await self.bot.redis.hgetall('delay:raid')
            for k, v in delayed.items():
                self.delayed_raid[int(k)] = json.loads(v)
            self.check_delayed_raids.start()
            print(self.__class__.__name__, 'is ready')
            self.is_first_ready = False

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild: return
        elif message.channel.id == 819497629439754271:
            if 'spawned' in message.content:
                await asyncio.sleep(600)
                if len(self.announcements) == 0:
                    msg = ' '.join([
                        raid.gods['none'][0],
                        raid.gods['none'][1],
                        raid.link.format(id=raid.gods['none'][2])
                    ])
                    self.announcements = await announce(self.bot, msg)
            elif 'Raid result' in message.content:
                self.announcements = []
                self.switch = False

    @tasks.loop(minutes=15)
    async def reset_announcements(self):
        if len(self.announcements) > 0:
            if self.switch:
                self.announcements = []
            self.switch = not self.switch

    @tasks.loop(minutes=1)
    async def check_delayed_raids(self):
        if not self.mode and len(self.delayed_raid) > 0:
            data = self.delayed_raid[sorted(self.delayed_raid.keys())[0]]
            data[1] = self.bot.get_user(data[1])
            if data[0] == 'belthazor':
                data[-1] = self.bot.get_user(data[-1])
                await self.setup_belthazor(*data[1:])
            elif data[0] == 'impostor':
                await self.setup_impostor(*data[1:])
            elif data[0] == 'enhanced':
                data[-1] = self.bot.get_user(data[-1])
                await self.setup_enhanced(*data[1:])
            elif data[0] == 'undead':
                await self.setup_undead(*data[1:])
            elif data[0] == 'city':
                await self.setup_city(*data[1:])

    @tasks.loop(seconds=4)
    async def background_fetch(self):
        if self.register_message and not self.fetching and len(self.waitlist) + len(self.autojoin) > 0:
            self.fetching = True
            if len(self.waitlist) == 0:
                uid = self.autojoin.pop(0)
                delayed = True
            else:
                uid = self.waitlist[0]
                self.delayed_messages = [i for i in self.delayed_messages if i[0].id != uid]
                delayed = False
            guild = self.register_message.guild
            res = await battle.background_fetch(
                self.bot, self.mode, self.participants, uid, self.disqualified,
                guild, [] if not self.private else map(int, config.config[guild.id]['misc']['guilds']),  # type: ignore
                belthazor_prev = self.belthazor_prev if self.belthazor_prev else {"lucky": 0, "possessed": 0, "survivors": []},
                delay_announce=delayed
            )
            if not delayed:
                self.waitlist.remove(uid)
            elif delayed and res is not None:
                self.delayed_messages.append(res)
            self.fetching = False

    @app_commands.describe(hp='The boss HP (or the number of scrael)', god='Whether it\'s a god raid')
    @app_commands.command(name='announce')
    @checks.mod_only()
    async def _app_announcements(self, interaction: discord.Interaction, hp: app_commands.Range[int, 0] = 0, god: Optional[str] = None):
        '''
        Send a raid announcement
        '''
        await interaction.response.defer(thinking=True, ephemeral=True)
        if len(self.announcements) > 0:
            view = ui.RaidAnnouncement('Sending new announcement', 'Deleting announcement')
            await interaction.followup.send('An announcement has already been sent. Would you like to send another announcement or delete the last one?', view=view)
            await view.wait()
            if view.value is None: return
            for i in self.announcements: await i.delete()
            if not view.value:
                self.announcements = []
                self.switch = False
                return
        else:
            await interaction.followup.send('Sending announcement', ephemeral=True)
        if god is None:
            msg = ' '.join([
                s for s in [
                    raid.gods['none'][0],
                    raid.hp.format(hp=hp) if hp else None,
                    raid.cash.format(cash=int(hp/4)),
                    raid.gods['none'][1],
                    raid.link.format(id=raid.gods['none'][2])
                ] if s is not None
            ])
            self.announcements = await announce(self.bot, msg)
        else:
            if god == 'eden' and hp == 0: hp = 15000
            msg = ' '.join([s for s in [
                raid.gods[god][0].format(number=hp),
                raid.hp.format(hp=hp) if not god in ['lyx', 'kvothe'] else None,
                raid.cash.format(cash=int(hp/4)) if god in ['jesus', 'eden', 'chamburr'] else None,
                raid.gods[god][1],
                raid.link.format(id=raid.gods[god][2])
            ] if s is not None])
            self.announcements = await announce(self.bot, msg, god)
        if len(self.announcements) > 0:
            await interaction.followup.send('Announcement sent to {} channels.'.format(len(self.announcements)), ephemeral=True)

    @app_commands.describe(
        private='Only allow guild members to join', delay='Schedule a raid for later (at specific epoch timestamp)', possess='Attempt to possess another player'
    )
    @app_commands.rename(delay='at')
    @app_commands.command(name='belthazor')
    @checks.mod_only()
    @checks.guild_bill()
    @checks.perms(guild=True, mod=True)
    async def _belthazor(self, interaction: discord.Interaction, private: bool = False, possess: Optional[discord.User] = None, delay: Optional[int] = None):
        '''
        Start a Belthazor raid
        '''
        message = [
            '{} Belthazor raid'.format('a private' if private else 'a'),
        ]
        args = ['belthazor', private, possess if possess else None]
        await self.check_delay(interaction, args, delay, message, self.setup_belthazor)
        
    @app_commands.describe(
        private='Only allow guild members to join', delay='Schedule a raid for later (at specific epoch timestamp)',
    )
    @app_commands.rename(delay='at')
    @app_commands.command(name='impostor')
    @checks.mod_only()
    @checks.guild_bill()
    @checks.perms(guild=True, mod=True)
    async def _impostor(self, interaction: discord.Interaction, private: bool = False, delay: Optional[int] = None):
        '''
        Start an Impostor raid
        '''
        message = [
            '{} Impostor raid'.format('a private' if private else 'an'),
        ]
        args = ['impostor', private]
        await self.check_delay(interaction, args, delay, message, self.setup_impostor)
        
    @app_commands.describe(
        hp='The boss HP', private='Only allow guild members to join',
        delay='Schedule a raid for later (at specific epoch timestamp)', user='Select another user as the raid boss'
    )
    @app_commands.rename(delay='at')
    @app_commands.command(name='enhanced')
    @checks.mod_only()
    @checks.guild_bill()
    @checks.perms(guild=True, mod=True)
    async def _enhanced(self, interaction: discord.Interaction, hp: app_commands.Range[int, 100000] = raid.raid_cfg['hp'], private: bool = False, user: Optional[discord.User] = None, delay: Optional[int] = None):
        '''
        Start an Enhanced raid
        '''
        message = [
            '{} Enhanced raid'.format('a private' if private else 'an'),
            'with {.mention} as the boss'.format(user) if user is not None else None,
            'at {:,d} HP'.format(hp)
        ]
        args = ['enhanced', private, hp, user or interaction.user]
        await self.check_delay(interaction, args, delay, message, self.setup_enhanced)
        
    @app_commands.describe(
        no='The size of the undead army, if not provided, will spawn indefinitely',
        prize='Total prize the players win for defeating the army, or suggested prize for every 100 undeads',
        payout='Whether to rewards all participants or only survivors',
        private='Only allow guild members to join', delay='Schedule a raid for later (at specific epoch timestamp)',
    )
    @app_commands.rename(no='size', delay='at')
    @app_commands.command(name='undead')
    @checks.mod_only()
    @checks.guild_bill()
    @checks.perms(guild=True, mod=True)
    async def _undead(self, interaction: discord.Interaction, no: app_commands.Range[int, 50] = 0, prize: app_commands.Range[int, 0] = 0, payout: str = 'everyone', private: bool = False, delay: Optional[int] = None):
        '''
        Start an Undead raid
        '''
        message = [
            '{} Undead raid'.format('a private' if private else 'an'),
            'with {:,d} undeads'.format(no) if no else None,
        ]
        args = ['undead', private, no, prize, payout]
        await self.check_delay(interaction, args, delay, message, self.setup_undead)
        
    @app_commands.describe(
        name='City name', enemy='Enemy army name', private='Only allow guild members to join',
        delay='Schedule a raid for later (at specific epoch timestamp)', c='Number of cannons',
        a='Number of archer towers', o='Number of outer walls', i='Number of inner walls',
        m='Number of moats', t='Number of towers', b='Number of ballistae',
    )
    @app_commands.rename(
        name='city_name', enemy='enemy_army', c='cannons', a='archer_towers', o='outer_walls', i='inner_walls',
        m='moats', t='towers', b='ballistae', delay='at'
    )
    @app_commands.command(name='city')
    @checks.mod_only()
    @checks.guild_bill()
    @checks.perms(guild=True, mod=True)
    async def _city(
        self, interaction: discord.Interaction, name: Optional[str] = None, enemy: Optional[str] = None,
        c: app_commands.Range[int, 0, 10] = 0, a: app_commands.Range[int, 0, 10] = 0,
        o: app_commands.Range[int, 0, 10] = 0, i: app_commands.Range[int, 0, 10] = 0,
        m: app_commands.Range[int, 0, 10] = 0, t: app_commands.Range[int, 0, 10] = 0, b: app_commands.Range[int, 0, 10] = 0,
        private: bool = False, delay: Optional[int] = None
    ):
        '''
        Start a City raid
        '''
        defenses = [c,a,o,i,m,t,b]
        if sum(defenses) > 10:
            return await interaction.response.send_message('A city cannot have more than 10 defenses')
        elif sum(defenses) == 0:
            d_names = ['c', 'a', 'o', 'i', 'm', 't', 'b']
            d_random = random.choices(d_names, k=10)
            defenses = [d_random.count(i) for i in d_names]
        message = [
            '{} City raid'.format('a private' if private else 'an'),
        ]
        args = ['city', private, name, enemy, defenses]
        await self.check_delay(interaction, args, delay, message, self.setup_undead)
        
    async def check_delay(self, interaction: discord.Interaction, args, delay, message, setup):
        await interaction.response.defer(thinking=True)
        author = interaction.user
        data = list(args)
        data.insert(1, author.id)
        if isinstance(data[-1], discord.abc.Snowflake): data[-1] = data[-1].id
        timestamp = int(discord.utils.utcnow().timestamp())
        message.insert(1, 'on <t:{:.0f}>'.format(delay) if delay and delay >= timestamp else None)
        message = ' '.join([i for i in message if i is not None])
        if delay is not None and delay > self.check_delayed_raids.next_iteration.timestamp():  # type: ignore
            while delay in self.delayed_raid: delay += 1
            self.delayed_raid[delay] = data
            await self.bot.redis.hset('delay:raid', str(delay), json.dumps(data))
            await interaction.followup.send('Scheduling {}'.format(message))
            return await self.bot.custom_log(message=f'{author.mention} scheduled {message}>')
        elif delay is not None and delay >= timestamp:
            await interaction.followup.send('Scheduling {}'.format(message))
            await self.bot.custom_log(message=f'{author.mention} scheduled {message}>')
            await asyncio.sleep(delay-timestamp)
            timestamp = int(discord.utils.utcnow().timestamp())
        else:
            await interaction.followup.send('Starting {}'.format(message))
        if self.mode is None:
            await setup(author, *args[1:])
        else:
            while timestamp in self.delayed_raid: timestamp += 1
            self.delayed_raid[timestamp] = data
            await self.bot.redis.hset('delay:raid', str(timestamp), json.dumps(data))
            await interaction.followup.send('{} is currently in progress. This raid will start after.'.format(self.mode), ephemeral=True)

    async def setup_belthazor(self, author, private, possess):
        self.private = private
        guild = self.channel.guild  # type: ignore
        self.mode = 'Belthazor raid'
        res = await self.bot.redis.hget('raid_results', str(guild.id))
        self.belthazor_prev = prev_raid = json.loads(res) if res else {"lucky": 0, "possessed": 0, "survivors": []}
        prev_boss = prev_raid['possessed']
        prev_survivors = prev_raid['survivors']
        possessed = 0
        target = None
        self.disqualified = list(self.banned) if len(prev_survivors) > 0 else list(set(self.banned + [prev_boss]))
        if author.id == prev_boss:
            target = None if possess is None else possess
            if target and not target.id == prev_boss and len(prev_survivors) == 0 and not random.randrange(0, 3):
                possessed = target.id
                try:
                    await target.send(raid.prompts['belthazor']['possessed'].format(boss=prev_boss))
                except discord.Forbidden:
                    pass
        if not possessed:
            chance = random.randrange(0,10)
            star_candidate = prev_raid['lucky'] if len(prev_survivors) > 0 else None
            title_holders = [t.members[0].id for t in self.arena_titles if len(t.members) == 1]
            if star_candidate:
                possessed = author.id if chance < 2 else star_candidate if chance < 5 else random.choice(list(set(self.default_bosses + title_holders)))
            else:
                possessed = author.id if chance < 2 else random.choice(list(set(self.default_bosses + title_holders)))
            if possessed == author.id:
                try:
                    await author.send(raid.prompts['belthazor']['failed_summon'])
                except discord.Forbidden:
                    pass
            else:
                try:
                    await author.send(raid.prompts['belthazor']['success_summon'])
                except discord.Forbidden:
                    pass
        fetched_user = target if target and possessed == target.id else self.bot.get_user(possessed)
        if fetched_user is None: return
        self.disqualified.append(fetched_user.id)
        p = await self.bot.get_equipped(fetched_user.id, orgs=False)

        bonus = 0.1 if fetched_user.id in prev_raid['survivors'] else 0 if not fetched_user.id == prev_boss else -0.2
        p.raidstats = [i + bonus for i in p.raidstats]
        god = random.random() - p.luck / 2
        stats = p.fighter_data()
        self.boss = battle.Fighter(
            user=fetched_user,
            name=p.name,
            dmg=stats[0],
            amr=stats[1],
            atkm=stats[2],
            defm=stats[3],
            hp=raid.raid_cfg['hp'] + round(god * raid.raid_cfg['mod'])
        )
        await self.bot.log_event('raid',
            embed = discord.Embed(
                title=f'{self.mode} started in {guild.name}',
                timestamp=discord.utils.utcnow(),
                color=0x31cccc
            ).add_field(
                name='Started by', value=f'{author} ({author.mention})'
            ).add_field(
                name='Boss', value=f'{self.boss.user} ({self.boss.user.mention})'
            ).add_field(
                name='HP', value=f'{self.boss.hp:,d}'
            ).set_author(
                name=author, icon_url=author.display_avatar.url
            ).set_thumbnail(url=guild.icon.url)  # type: ignore
        )
        raidmsg = raid.prompts['belthazor']['message'].format(
            guild=guild, boss=self.boss, bosshp=self.boss.hp, regtime=int(raid.raid_cfg['reg'] + discord.utils.utcnow().timestamp())
        )
        await self.sign_up(raidmsg, self.belthazor_battle)

    async def setup_impostor(self, author, private):
        self.private = private
        guild = self.channel.guild  # type: ignore
        self.mode = 'Impostor raid'
        title_holders = [t.members[0].id for t in self.arena_titles if len(t.members) == 1]
        possessed = author.id if random.randrange(0,10) < 3 else random.choice(list(set(self.default_bosses + title_holders)))
        fetched_user = self.bot.get_user(possessed)
        if fetched_user is None: return
        self.disqualified = list(self.banned) + [fetched_user.id]
        p = await self.bot.get_equipped(fetched_user.id, orgs=False)
        god = random.random() - p.luck / 2
        stats = p.fighter_data()
        self.boss = battle.Fighter(
            user=fetched_user,
            name=p.name,
            dmg=stats[0],
            amr=stats[1],
            atkm=stats[2],
            defm=stats[3],
            hp=round((raid.raid_cfg['hp'] + god * raid.raid_cfg['mod']))
        )
        try:
            await fetched_user.send(raid.prompts['impostor']['possessed'])
        except discord.Forbidden:
            pass
        await self.bot.log_event('raid',
            embed = discord.Embed(
                title=f'{self.mode} started in {guild.name}',
                timestamp=discord.utils.utcnow(),
                color=0x31cccc
            ).add_field(
                name='Started by', value=f'{author} ({author.mention})'
            ).add_field(
                name='Boss', value=f'{self.boss.user} ({self.boss.user.mention})'
            ).add_field(
                name='HP', value=f'{(self.boss.hp * 0.3):,.0f}'
            ).set_author(
                name=author, icon_url=author.display_avatar.url
            ).set_thumbnail(url=guild.icon.url)  # type: ignore
        )
        raidmsg = raid.prompts['impostor']['message'].format(
            guild=guild, boss=self.boss, bosshp=self.boss.hp*0.3, regtime=int(raid.raid_cfg['reg'] + discord.utils.utcnow().timestamp())
        )
        await self.sign_up(raidmsg, self.impostor_battle)

    async def setup_enhanced(self, author, private, hp, user):
        self.private = private
        guild = self.channel.guild  # type: ignore
        self.mode = 'Enhanced raid'
        self.disqualified = list(self.banned) + [user.id]
        p = await self.bot.get_equipped(user.id, orgs=False)
        stats = p.fighter_data()
        self.boss = battle.Fighter(
            user=user,
            name=p.name,
            dmg=stats[0],
            amr=stats[1],
            atkm=stats[2],
            defm=stats[3],
            hp=hp
        )
        try:
            await user.send(raid.prompts['enhanced']['dm'].format(guild=guild))
        except discord.Forbidden:
            pass
        await self.bot.log_event(
            'raid',
            embed= discord.Embed(
                title=f'{self.mode} started in {guild.name}',
                timestamp=discord.utils.utcnow(),
                color=0x31cccc
            ).add_field(
                name='Started by', value=f'{author} ({author.mention})'
            ).add_field(
                name='Boss', value=f'{self.boss.user} ({self.boss.user.mention})'
            ).add_field(
                name='HP', value=f'{self.boss.hp:,d}'
            ).set_author(
                name=author, icon_url=author.display_avatar.url
            ).set_thumbnail(url=guild.icon.url)  # type: ignore
        )
        raidmsg = raid.prompts['enhanced']['message'].format(
            boss=self.boss, bosshp=self.boss.hp, regtime=int(raid.raid_cfg['reg'] + discord.utils.utcnow().timestamp()),
            pissoff=random.choice([m for m in guild.members if not m.bot])
        )
        await self.sign_up(raidmsg, self.enhanced_battle)

    async def setup_undead(self, author, private, no, prize, payout):
        guild = self.channel.guild  # type: ignore
        self.private = private
        key = 'endless' if no == 0 else 'undead'
        self.mode = 'Undead raid'
        self.boss = (no, prize, payout)
        await self.bot.log_event(
            'raid',
            embed= discord.Embed(
                title=f'{self.mode} started in {guild.name}',
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                color=0x31cccc
            ).add_field(
                name='Started by', value=f'{author} ({author.mention})'
            ).add_field(
                name='Army size', value=no if no else 'Infinite'
            ).set_author(
                name=author, icon_url=author.avatar_url
            ).set_thumbnail(url=guild.icon.url)  # type: ignore
        )
        raidmsg = raid.prompts['undead'][key].format(
            guild=guild.name, no=no, regtime=int(raid.raid_cfg['reg'] + discord.utils.utcnow().timestamp()),
        )
        await self.sign_up(raidmsg, self.undead_battle)

    async def setup_city(self, author, private, name, enemy, defenses):
        self.private = private
        guild = self.channel.guild  # type: ignore
        self.mode = 'City raid'
        self.disqualified = list(self.banned)
        self.boss = []
        for d in range(len(raid.defenses)):
            for _ in range(defenses[d]):
                self.boss.append(battle.CityDefenses(raid.defenses[d]))
        total_defense = sum([i.damage for i in self.boss])
        self.boss.sort(key = lambda x: x.damage, reverse = True)
        self.boss.sort(key = lambda x: x.hp, reverse = True)
        city_name = name or random.choice(strings.cities)
        attackers = enemy or random.choice(strings.supervillains)[0]
        self.boss.insert(0, [city_name, total_defense, attackers])
        await self.bot.log_event( 
            'raid',
            embed= discord.Embed(
                title=f'{self.mode} started in {guild.name}',
                timestamp=discord.utils.utcnow(),
                color=0x31cccc
            ).add_field(
                name='Started by', value=f'{author} ({author.mention})', inline=False
            ).add_field(
                name='City',
                value='\n'.join([
                    '**Name:** {name}',
                    '**Invaders:** {invaders}',
                    '**Defenses:**',
                    '{defenses}',
                    '> Total damage: {damage:,d}',
                    '> Cost: ${cost:,d}']).format(
                        name=city_name, invaders=attackers, damage=total_defense,
                        cost=sum([ x * y for (x, y) in zip(defenses, raid.defense_cost)]),
                        defenses='\n'.join([
                            f'> {raid.defense_labels[k]}: {defenses[k]}' for k in range(len(raid.defense_labels)) if defenses[k] > 0
                        ])
                    )
            ).set_author(
                name=author, icon_url=author.display_avatar.url
            ).set_thumbnail(url=guild.icon.url)  # type: ignore
        )
        raidmsg = raid.prompts['city']['message'].format(
            name=city_name, enemy=attackers, guild=guild, defenses=total_defense,
            regtime=int(raid.raid_cfg['reg'] + discord.utils.utcnow().timestamp()),
        )
        await self.sign_up(raidmsg, self.city_battle)        

    async def sign_up(self, msg, battle):
        # Create sign up message
        raidmsg = f'{self.role.mention} {msg}' if self.role else msg
        if self.private: raidmsg += '\n**This is a private event, guests cannot join this raid.**'
        # Send message
        if self.channel is None: return
        message_list = []
        self.delayed_messages = []
        button = ui.Join(
            waitlist=self.waitlist, banlist=self.disqualified, participants=self.participants, label=self.mode or 'guild raid', msg=message_list
        )
        self.register_message = await self.channel.send(msg, view=button, allowed_mentions=discord.AllowedMentions(users=False, roles=True))  # type: ignore
        message_list.append(self.register_message)
        # Get autojoin list
        autojoin = []
        #Get arena titles
        arena_list = utils.get_role_ids('arena', config.config[self.register_message.guild.id])  # type: ignore
        if 'arena' in config.config[self.register_message.guild.id]['misc']:  # type: ignore
            for i in map(lambda x: self.register_message.guild.get_role(x[1]), arena_list): # type: ignore
                autojoin += [m for m in i.members if m.id not in self.disqualified]  # type: ignore
        
        role_list = utils.get_role_ids('donation', config.config[self.register_message.guild.id])  # type: ignore
        # Get gold donators
        gold = self.register_message.guild.get_role(role_list[0][1]) if len(role_list) > 0 else None  # type: ignore
        if gold: autojoin += [m for m in gold.members if m.id not in self.disqualified]
        self.autojoin = list(set(autojoin))

        self.background_fetch.start()
        
        await asyncio.sleep(raid.raid_cfg['reg'])
        button.stop()
        await self.register_message.edit(view=None)
        if self.mode is None: return
        while len(self.autojoin) + len(self.waitlist) > 0 or not self.fetching:
            await asyncio.sleep(1)
        self.background_fetch.stop()
        if len(self.participants) == 0:
            await self.channel.send(f'Not enough people joined... Unable to start the {self.mode}.')  # type: ignore
        else:
            for i in self.delayed_messages:
                await i[0].send(i[1])
            await battle()
        
    async def belthazor_battle(self):
        guild_id = str(self.channel.guild.id)  # type: ignore
        # Add to leaderboard
        b_id = str(self.boss.user.id)  # type: ignore
        async with self.bot.redis.pipeline(transaction=True) as pipe:
            boss_board, raider_board = (await pipe.hget('b' + guild_id, 'boss').hget('b' + guild_id, 'raider').execute())  # type: ignore
        boss_board = json.loads(boss_board.replace('\'', '"')) if boss_board else dict()
        if b_id in boss_board:
            boss_board[b_id][0] += 1
        else:
            boss_board[b_id] = [1, 0]
        raider_board = json.loads(raider_board.replace('\'', '"')) if raider_board else dict()
        fighters = []
        for k, v in self.participants.items():
            fighters.append(v)
            f_id = str(k)
            if f_id in raider_board:
                raider_board[f_id][0] += 1
            else:
                raider_board[f_id] = [1, 0]
        
        # Boss original HP
        original_hp = self.boss.hp  # type: ignore
        # Start time and duration
        end_time = (start_time:=discord.utils.utcnow()) + datetime.timedelta(seconds=config.config[int(guild_id)]['time'])
        # Fight
        turn = await battle.boss_battle(self.channel, fighters, self.boss, end_time)
        blessed = None
        # Result messages
        timestamp = discord.utils.utcnow()
        fighters.sort(key = lambda x: x.hp, reverse=True)
        if self.boss.hp > 0:  # type: ignore
            msg = raid.prompts['belthazor']['wiped' if len(fighters) == 0 else 'timeout'].format(boss=self.boss)
        else:
            blessed = random.choice(fighters)
            msg = raid.prompts['belthazor']['won'].format(
                boss=self.boss, blessed=blessed,
                survivors=' '.join(map(lambda x: x.user.mention, fighters))
            )
        # Update Belthazor raid data
        this_raid = {
            'possessed': self.boss.user.id,  # type: ignore
            'survivors': [s.user.id for s in fighters if self.boss.hp == 0],  # type: ignore
            'lucky': blessed.user.id if self.boss.hp == 0 else 0  # type: ignore
        }
        # Update raid leaderboard
        if self.boss.hp == 0:  # type: ignore
            await self.channel.send(raid.wuxi_gif)  # type: ignore
            for survivor in this_raid['survivors']:
                if str(survivor) in raider_board:
                    raider_board[str(survivor)][1] += 1
                else:
                    raider_board[str(survivor)] = [1, 1]
            # Send DM to lucky raider
            try:
                await blessed.user.send(raid.prompts['belthazor']['blessed'].format(guild=self.channel.guild))  # type: ignore
            except discord.Forbidden:
                pass
        else:
            if b_id in boss_board:
                boss_board[b_id][1] += 1
            else:
                boss_board[b_id] = [1, 1]
            # If boss is an officer
            if self.boss.user.id in config.config[int(guild_id)]['boss']:  # type: ignore
                try:
                    await self.boss.user.send(raid.prompts['belthazor']['possess'].format(guild=self.channel.guild))  # type: ignore
                except discord.Forbidden:
                    pass
        async with self.bot.redis.pipeline(transaction=True) as pipe:
            (
                await pipe
                .hset('raid_results', guild_id, json.dumps(this_raid))
                .hset('r_winners', guild_id, json.dumps(this_raid['survivors']))  # type: ignore
                .hset('b' + guild_id, 'boss', json.dumps(boss_board))
                .hset('b' + guild_id, 'raider', json.dumps(raider_board))
                .hsetnx('b' + guild_id, 'start', timestamp.strftime('%b %d, %y'))
                .execute()
            )
        # Raid report
        report = {
            'mode': self.mode,
            'fighters': sorted([(f.user.id, f.hp) for f in self.participants.values()], key=lambda x: x[1], reverse=True),
            'boss': (self.boss.user.id, self.boss.hp, original_hp),  # type: ignore
            'timestamps': (start_time.timestamp(), timestamp.timestamp()),
            'blessed': blessed.user.id if blessed is not None else None,
            'rounds': turn
        }
        await self.clear(msg, report)
 
    async def impostor_battle(self):
        guild_id = str(self.channel.guild.id)  # type: ignore
        # Get impostor boss
        real_boss = random.choice(raid.impostor_bosses)
        real_hp = round(self.boss.hp * real_boss['hp_mod'])  # type: ignore
        self.boss.hp = round(self.boss.hp * 0.3)  # type: ignore
        fake_hp = self.boss.hp  # type: ignore
        # Add to leaderboard
        b_id = str(self.boss.user.id)  # type: ignore
        async with self.bot.redis.pipeline(transaction=True) as pipe:
            boss_board, raider_board = (await pipe.hget('i' + guild_id, 'boss').hget('i' + guild_id, 'raider').execute())  # type: ignore
        boss_board = json.loads(boss_board.replace('\'', '"')) if boss_board else dict()
        if b_id in boss_board:
            boss_board[b_id][0] += 1
        else:
            boss_board[b_id] = [1, 0]
        raider_board = json.loads(raider_board.replace('\'', '"')) if raider_board else dict()
        fighters = []
        for k, v in self.participants.items():
            fighters.append(v)
            f_id = str(k)
            if f_id in raider_board:
                raider_board[f_id][0] += 1
            else:
                raider_board[f_id] = [1, 0]
        
        # Start time and duration
        end_time = (start_time:=discord.utils.utcnow()) + datetime.timedelta(seconds=config.config[int(guild_id)]['time'])
        # Report
        report = {}
        report.update({'mode': self.mode})
        # Fight
        turn = await battle.boss_battle(self.channel, fighters, self.boss, end_time)
        timestamp = discord.utils.utcnow()
        report.update({
            'timestamps': (start_time.timestamp(), timestamp.timestamp()),
            'boss': (self.boss.user.id, self.boss.hp, fake_hp),  # type: ignore
            'fighters': sorted([(f.user.id, f.hp) for f in self.participants.values()], key=lambda x: x[1], reverse=True),
            'rounds': turn
        })
        await asyncio.sleep(4)
        if self.boss.hp > 0:  # type: ignore
            msg = raid.prompts['impostor']['fake_wiped' if len(fighters) == 0 else 'fake_timeout'].format(boss=self.boss)
        else:
            self.boss.name = real_boss['name']  # type: ignore
            self.boss.thumbnail = real_boss['gif']  # type: ignore
            self.boss.hp = real_hp  # type: ignore
            self.boss.dmg *= real_boss['dmg']  # type: ignore
            self.boss.amr *= real_boss['def']  # type: ignore
            messages = raid.prompts['impostor']['boss_reveal'].format(boss=self.boss, real_boss=real_boss['title'], bosshp=real_hp).splitlines()
            for i in messages:
                await self.channel.send(i)  # type: ignore
                await asyncio.sleep(4)
            turn = await battle.boss_battle(self.channel, fighters, self.boss, end_time, feature=real_boss)
            timestamp = discord.utils.utcnow()
            report['rounds'] += turn
            report.update({
                'impostor': (real_boss, self.boss.hp, real_hp),  # type: ignore
                'timestamps': (start_time.timestamp(), timestamp.timestamp()),
                'fighters': sorted([(f.user.id, f.hp) for f in self.participants.values()], key=lambda x: x[1], reverse=True),
            })
            if self.boss.hp > 0:  # type: ignore
                if b_id in boss_board:
                    boss_board[b_id][1] += 1
                else:
                    boss_board[b_id] = [1, 1]
                msg = raid.prompts['impostor']['wiped' if len(fighters) == 0 else 'timeout'].format(boss=self.boss)
            else:
                fighters.sort(key=lambda x: x.hp, reverse=True)
                msg = raid.prompts['impostor']['won'].format(
                    real_boss=real_boss['title'], boss=self.boss,
                    survivors=' '.join(map(lambda x: x.user.mention, fighters))
                )
                for s in fighters:
                    if str(s.user.id) in raider_board:
                        raider_board[str(s.user.id)][1] += 1
                    else:
                        raider_board[str(s.user.id)] = [1, 1]
                await self.bot.redis.hset('r_winners', guild_id, json.dumps([i.user.id for i in fighters]))
            async with self.bot.redis.pipeline(transaction=True) as pipe:
                (
                    await pipe
                    .hset('i' + guild_id, 'boss', json.dumps(boss_board))
                    .hset('i' + guild_id, 'raider', json.dumps(raider_board))  # type: ignore
                    .hsetnx('i' + guild_id, 'start', timestamp.strftime('%b %d, %y'))
                    .execute()
                )
        await self.clear(msg, report)

    async def enhanced_battle(self):
        guild_id = str(self.channel.guild.id)  # type: ignore
        fighters = list(self.participants.values())
        # Boss original HP
        original_hp = self.boss.hp  # type: ignore
        # Start time and duration
        end_time = (start_time:=discord.utils.utcnow()) + datetime.timedelta(seconds=config.config[int(guild_id)]['time'])
        # Fight
        turn = await battle.boss_battle(self.channel, fighters, self.boss, end_time)
        # Result messages
        timestamp = discord.utils.utcnow()
        fighters.sort(key = lambda x: x.hp, reverse=True)
        report = {
            'mode': self.mode,
            'fighters': sorted([(f.user.id, f.hp) for f in self.participants.values()], key=lambda x: x[1], reverse=True),
            'boss': (self.boss.user.id, self.boss.hp, original_hp),  # type: ignore
            'timestamps': (start_time.timestamp(), timestamp.timestamp()),
            'rounds': turn
        }
        if self.boss.hp > 0:  # type: ignore
            msg = raid.prompts['enhanced']['wiped' if len(fighters) == 0 else 'timeout'].format(boss=self.boss)
        else:
            lucky = random.choice(fighters)
            report.update({'lucky': lucky.user.id})
            msg = raid.prompts['enhanced']['won'].format(
                boss=self.boss, lucky=lucky,
                survivors=' '.join(map(lambda x: x.user.mention, fighters))
            )
            await self.bot.redis.hset('r_winners', guild_id, json.dumps([i.user.id for i in fighters]))
        await self.clear(msg, report)

    async def undead_battle(self):
        guild_id = str(self.channel.guild.id)  # type: ignore
        no, prize, payto = self.boss  # type: ignore
        size = no if no else 100
        undeads = battle.get_undead(size, prize)
        turn = turned = total_killed = original_killed = 0
        leaderboard, undeadboard = {}, {}
        start_time = discord.utils.utcnow()
        payout = {} if payto == 'everyone' else None
        fighters = []
        for f in self.participants:
            leaderboard[f] = 0
            fighter = self.participants[f]
            fighter.hp = 150 + 10 * utils.get_class_bonus('rng', fighter.classes)
            fighters.append(fighter)
        while True:
            # Fight
            fighters, undeads, turn, turned, total_killed, original_killed, leaderboard, undeadboard, payout = (
                await battle.undead_battle(
                    self.channel, fighters, undeads,  # type: ignore
                    turn=turn, turned=turned, total=total_killed, og=original_killed,
                    board=leaderboard, undead_board=undeadboard, payout=payout
                )
            )
            # End if not endless or if all fighters are dead
            if no > 0 or len(fighters) == 0: break
            undeads = battle.get_undead(size, prize)
        timestamp = discord.utils.utcnow()
        leaderboard = list(leaderboard.items())
        leaderboard.sort(key=lambda x: x[1], reverse=True)
        money = []
        def get_money(id: int):
            if id in payout and payout[id] > 0:
                money.append((id, payout[id]))
                return '(${:,d})'.format(payout[id])
            return ''
        highscore = [
            '<@{id}>: {kills} kill{plural} {payout}'.format(
                id=i[0], kills=i[1], plural='s' if i[1] > 1 else '',
                payout=get_money(i[0])
            ).strip() for i in leaderboard if i[1] > 0
        ]
        survived = [i.user.id for i in fighters]
        undead_report = []
        for k, v in self.participants.items():
            if k in survived:
                undead_report.append((v.user.id, v.hp))
            else:
                undead_report.append((v.user.id, 0 if v.hp < 0 else 0 - v.hp))
        async with self.bot.redis.pipeline(transaction=True) as pipe:
            if len(fighters) == 0:
                msg = raid.prompts['undead']['wiped']
            else:
                msg = raid.prompts['undead']['timeout' if (timestamp - start_time).total_seconds() > raid.raid_cfg['time'] else 'won'].format(
                    survivors=' '.join(map(lambda x: x.user.mention, fighters))
                )
                await pipe.hset('r_winners', guild_id, json.dumps(survived))
            for i in undeadboard: pipe.hincrby('zz{}'.format(self.channel.guild.id), i, undeadboard[i])  # type: ignore
            for i in leaderboard:
                (
                    pipe
                    .hincrby('z{}'.format(self.channel.guild.id), i[0], i[1])  # type: ignore
                    .hincrby('z:e:{}'.format(self.channel.guild.id), i[0], i[1])  # type: ignore
                )
            pipe.set('z:pay:{}'.format(self.channel.guild.id), json.dumps(money))  # type: ignore
            await pipe.execute()
        report = {
            'mode': self.mode,
            'fighters': sorted(undead_report, key=lambda x: x[1], reverse=True),
            'timestamps': (start_time.timestamp(), timestamp.timestamp()),
            'rounds': turn,
            'undeads': (no, original_killed, turned, total_killed)
        }

        if len(highscore) > 0:
            embed = discord.Embed(
                title='Undead raid result',
                description='Original undead: {init_zombies}\nTotal raiders: {init_raiders}\nOriginal undead killed: {org_killed}\nRaiders turned: {turned}\nUndead raiders killed: {killed}'.format(
                    init_zombies=no if no else 'Infinite',
                    init_raiders=len(self.participants),
                    org_killed=original_killed,
                    turned=turned,
                    killed=total_killed - original_killed
                ),
                color=0xFFD700,
                timestamp=timestamp
            ).set_footer(text=f'{turn} rounds', icon_url=self.channel.guild.icon.url)  # type: ignore
            for i in range(0, len(highscore), 10):
                embed.add_field(
                    name='Highscore', value='\n'.join(highscore[i:i+10])
                )
        else:
            embed = None
        await self.clear(msg, report, msgembed=embed)

    async def city_battle(self):
        guild_id = str(self.channel.guild.id)  # type: ignore
        fighters = list(self.participants.values())
        defenses = self.boss if isinstance(self.boss, list) else []
        report = {
            'mode': self.mode,
            'city': list(defenses[0])
        }
        end_time = (start_time:=discord.utils.utcnow()) + datetime.timedelta(seconds=config.config[int(guild_id)]['time'])
        turn, destroyed, dealt = await battle.city_battle(self.channel, fighters, defenses, end_time)
        timestamp = discord.utils.utcnow()
        if len(defenses) > 1:
            dealt += (defenses[1].total_hp - defenses[1].hp)
            for i in range(1, len(defenses)):
                destroyed.append(' '.join(defenses[i].name.split()[1:] + ['-', '{:,.1f} HP'.format(defenses[i].hp)]))
        else:
            await self.bot.redis.hset('r_winners', guild_id, json.dumps([i.user.id for i in fighters]))
        destroyed.append('Total damage dealt: {:,.1f} damage.'.format(dealt))
        report.update({
            'fighters': [
                (f.user.id, f.hp) for f in
                sorted(sorted(self.participants.values(), key = lambda x: x.amr), key = lambda y: y.dmg, reverse = True)
            ],
            'damage': destroyed,
            'timestamps': (start_time.timestamp(), timestamp.timestamp()),
            'rounds': turn
        })
        msg =  raid.prompts['city']['timeout' if timestamp > end_time else 'wiped' if len(fighters) == 0 else 'won'].format(
            name=defenses[0][0], enemy=defenses[0][2], destroyed='\n'.join(destroyed),
            survivors=' '.join(map(lambda x: x.user.mention, fighters))
        )
        msg = f'{self.role.mention} {msg}' if self.role else msg
        async with self.bot.redis.pipeline(transaction=True) as pipe:
            (
                await pipe
                .hset(f'c{guild_id}', timestamp.strftime('%Y-%m-%d'), json.dumps([len(self.participants), dealt]))
                .hsetnx('c' + str(guild_id), 'start', timestamp.strftime('%b %d, %y'))  # type: ignore
                .execute()
            )
        await self.clear(msg, report)

    async def clear(self, msg = None, report = None, *, msgembed = None):
        if msg: await self.channel.send(msg, embed=msgembed)  # type: ignore
        if report:
            embed = embeds.report(report)
            await self.bot.log_event('raid', embed=embed)
            await self.bot.redis.lpush('report:raid', json.dumps(report))
        # Raid instances
        self.private = False
        self.mode = None
        self.disqualified = []
        self.waitlist = []
        self.participants = {}
        self.register_message = None
        self.register = False
        self.autojoin = []
        self.delayed_messages = []
        self.boss = None
        # Belthazor data
        self.belthazor_prev = {}


async def setup(bot):
    await bot.add_cog(Raid(bot))