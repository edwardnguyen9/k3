import discord, json, asyncio, math
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional
from io import BytesIO
from pprint import pformat

from bot.bot import Kiddo
from assets import config
from classes import ui, battle
from utils import utils, embeds, checks

@app_commands.default_permissions(manage_channels=True)
class Tournament(commands.GroupCog, group_name='tourney'):
    def __init__(self, bot: Kiddo):
        self.bot = bot
        self.is_first_ready = True
        self.delayed = {}
        self.guild = None
        self.channel = None
        self.role = None
        self.banned = []
        # Instances
        self.mode = None
        self.tier = None
        self.private = False
        self.disqualified = []
        self.waitlist = []
        self.participants = {}
        self.register_message = None
        self.autojoin = []
        self.delayed_messages = []     
        self.fetching = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self.is_first_ready:
            await self.bot.loading()
            self.guild = self.bot.get_guild(821988363308630068)
            self.channel = self.bot.get_channel(self.bot.event_config['channels']['tourney'])
            self.role = self.guild.get_role(self.bot.event_config['roles']['tourney']) if self.guild else None
            self.banned = self.bot.event_config['tourney']['bans']
            self.check_delayed_tourney.start()
            print(self.__class__.__name__, 'is ready')
            self.is_first_ready = False

    @tasks.loop(minutes=1)
    async def check_delayed_tourney(self):
        if not self.mode and len(self.delayed) > 0:
            first_event = sorted(self.delayed.keys())[0]
            if first_event > self.check_delayed_tourney.next_iteration.timestamp(): return
            now = discord.utils.utcnow().timestamp()
            if first_event > now: await asyncio.sleep(first_event - now)
            if self.mode:
                return await self.bot.custom_log(message='{} is currently in progress. {} scheduled for later.'.format(self.mode, self.delayed[first_event][0]))
            await self.bot.redis.hdel('delay:tourney', str(first_event))
            data = self.delayed.pop(first_event)
            data[0] = self.bot.get_user(data[0])
            await self.setup_tourney(*data)

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
            res = await battle.background_fetch(
                self.bot, self.mode, self.participants, uid, self.disqualified,
                self.guild, [] if not self.private else [17555],
                tier=self.tier,
                delay_announce=delayed
            )
            if not delayed:
                self.waitlist.remove(uid)
            elif res is not None:
                self.delayed_messages.append(res)
            self.fetching = False

    @checks.perms(guild=True, mod=True)
    @app_commands.choices(
        mode=[app_commands.Choice(name=i, value=i) for i in ['Normal tournament', 'Raid tournament', 'Fistfight tournament']],
        tier=[app_commands.Choice(name='{1} (Lv. {0} or below)'.format(*i), value=i[1]) for i in self.bot.event_config['tourney']['tiers']]
    )
    @app_commands.command(name='start')
    async def _app_tourney(self, interaction: discord.Interaction, mode: str, tier: str = 'Master', prize: app_commands.Range[int, 0] = 0, private: bool = False, delay: Optional[int] = None):
        await interaction.response.defer(thinking=True)
        author = interaction.user
        data = [author.id, mode, private, tier, prize]
        message = [
            'a', 'private' if private else None, tier,
            mode.lower(), 'with a ${:,d} reward'.format(prize) if prize else None
        ]
        timestamp = int(discord.utils.utcnow().timestamp())
        message.append('on <t:{:.0f}>'.format(delay) if delay and delay >= timestamp else None)
        message = ' '.join(message)
        if delay is not None and delay > self.check_delayed_tourney.next_iteration.timestamp():  # type: ignore
            while delay in self.delayed: delay += 1
            self.delayed[delay] = data
            await self.bot.redis.hset('delay:tourney', str(delay), json.dumps(data))
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
            await interaction.followup.send('Starting {}'.format(message))
            await self.setup_tourney(author, *data[1:])
        else:
            while timestamp in self.delayed: timestamp += 1
            self.delayed[timestamp] = data
            await self.bot.redis.hset('delay:tourney', str(timestamp), json.dumps(data))
            message = '{} is currently in progress. {} scheduled for later.'.format(self.mode, data[0].title())
            await self.bot.custom_log(message=message)
            await interaction.followup.send(message, ephemeral=True)

    async def setup_tourney(self, author, mode, private, tier, prize):
        self.private = private
        self.mode = mode
        self.tier = discord.utils.find(lambda x: x[1] == tier, self.bot.event_config['tourney']['tiers'])
        message = '\n'.join([i for i in [
            self.role,
            '{} {} as been started.'.format('A private' if private else 'A', self.mode.lower()),
            'Tier: {}'.format(tier),
            'Level cap: {}'.format(self.tier[0] or None),  # type: ignore
            'First prize: ${:,d}'.format(prize) if prize else None,
            'Tournament starts <t:{}:R>'.format(int(discord.utils.utcnow().timestamp() + self.bot.event_config['tourney']['reg'])),
            '**This event is for guild members only**' if private else None
        ] if i is not None])
        await self.bot.log_event(
            'tourney', embed=discord.Embed(
                title='{} started'.format(mode),
                timestamp=discord.utils.utcnow(),
                color=0xc93030
            ).add_field(
                name='By', value=author.mention
            ).add_field(
                name='Type', value='**Open:** {}\n**Tier:** {}'.format((not private), tier[1].title())
            ).add_field(
                name='Prize', value='${:,d}'.format(prize)
            ).set_footer(text=author.guild.name, icon_url=author.guild.icon.url)
        )
        message_list = []
        button = ui.Join(
            waitlist=self.waitlist, banlist=self.disqualified, participants=self.participants,
            label=self.mode.lower(), msg=message_list
        )
        self.register_message = await self.channel.send(message, view=button, allowed_mentions=discord.AllowedMentions(users=False, roles=True))  # type: ignore
        message_list.append(self.register_message)
        # Get autojoin list
        autojoin = []
        role_list = utils.get_role_ids('donation', self.bot.event_config)
        # Get gold donators
        gold = self.guild.get_role(role_list[0][1]) if len(role_list) > 0 else None  # type: ignore
        if gold: autojoin += [m for m in gold.members if m.id not in self.disqualified]
        self.autojoin = list(set(autojoin))

        self.background_fetch.start()
        
        await asyncio.sleep(self.bot.event_config['tourney']['reg'])
        button.stop()
        await self.register_message.edit(view=None)
        while len(self.autojoin) + len(self.waitlist) > 0 or not self.fetching:
            await asyncio.sleep(1)
        self.background_fetch.stop()
        if self.mode is None: return
        participants = await self.get_brackets(self.participants)
        report = {
            'mode': self.mode,
            'participants': [(i[0].user.id, i[1]) for i in participants]
        }
        file = discord.File(filename='bracket.txt', fp=BytesIO(pformat(report['participants']).encode()))
        await self.bot.log_event('tourney', file=file)
        self.participants = list(participants)
        start_time = discord.utils.utcnow()
        if 'normal' in self.mode.lower():
            await self.channel.send('**Tournament started**')  # type: ignore
            logs = await self.compete(participants, battle.normal_battle)
        else:
            await self.channel.send('**{} started**'.format(mode))  # type: ignore
            logs = await self.compete(participants, battle.raid_battle)
        timestamp = discord.utils.utcnow()
        report.update({
            'timestamp': (start_time.timestamp(), timestamp.timestamp()),
            'results': [(i[0].user.id, i[1]) for i in self.participants],
            'winner': participants[0][0].user.id,
            'logs': logs
        })
        await self.clear(report)
        
    async def get_brackets(self, participants):
        tourney = []
        def bracketify(bracket, level=1):
            b_left = []
            b_right = []
            for i in range(0, len(bracket), 2):
                b_left.append(bracket[i])
                if i+1 < len(bracket):
                    b_right.append(bracket[i+1])
            if len(b_left) > 1:
                bracketify(b_left, level+1)
            else:
                tourney.append([b_left[0], level])
            if len(b_right) > 1:
                bracketify(b_right, level+1)
            else:
                tourney.append([b_right[0], level])
        bracketify(list(participants.values()))
        return tourney

    async def compete(self, opponents, fight, r: int = 1, results = None):
        if results is None:
            results = {}
        level = math.ceil(math.log2(len(opponents)))
        if level == 0:
            # embed.description = f'{opponents[0][0].user.mention} won the {self.mode.lower()} in **{self.guild.name}**'  # type: ignore
            # embed.timestamp = discord.utils.utcnow()
            await asyncio.sleep(2)
            # await log_event(self.bot, 'tourney', embed=embed)
            # await redis.add_report(self.bot, 'tourney', embed.to_dict())
            await self.channel.send(  # type: ignore
                'The {}\'s winner is {}!'.format(self.mode.lower(), opponents[0][0].user.mention)  # type: ignore
            )
            return results
        matches = [m for m in opponents if m[1] == level]
        if not 2**level == len(opponents):
            r -= 1
        if r == 0:
            r_name = 'Preliminary round'
        elif len(opponents) == 2:
            r_name = 'Final'
        elif len(opponents) == 4:
            r_name = 'Semifinals'
        elif len(opponents) == 8:
            r_name = 'Quarterfinals'
        else:
            r_name = f'Round {r}'
        # f_val = '\n'.join([
        #     f'{matches[i][0].user.mention} - {matches[i+1][0].user.mention}' for i in range(0, len(matches), 2)
        # ])
        await self.channel.send(f'**{r_name}**')  # type: ignore
        results[r] = []
        for i in range(0, len(matches), 2):
            await asyncio.sleep(2)
            await self.channel.send(f'{matches[i][0].user.display_name} vs {matches[i+1][0].user.display_name}', allowed_mentions=discord.AllowedMentions.none())  # type: ignore
            cfg = [self.channel] if 'normal' in self.mode.lower() else [self.channel, False, 'fistfight' in self.mode.lower()]  # type: ignore
            winner, loser = await fight([matches[i], matches[i+1]], *cfg)
            results[r].append(((matches[i][0].user.id, matches[i][0].hp), (matches[i+1][0].user.id, matches[i+1][0].hp)))
            # f_val = f_val.replace(f'{loser[0].user.mention}', f'~~{loser[0].user.mention}~~')
            opponents.remove(loser)
            winner[1] -= 1
            await asyncio.sleep(2)
            await self.channel.send(f'~~{loser[0].user.mention}~~ has been eliminated')  # type: ignore
        await asyncio.sleep(2)
        # embed.add_field(name=r_name, value=f_val, inline=False)
        await self.channel.send('Round completed.')  # type: ignore
        return await self.compete(opponents, fight, r + 1, results)

    async def clear(self, report = None):
        if report:
            embed = embeds.report(report)
            file = discord.File(filename='results.txt', fp=BytesIO(pformat(report['results']).encode()))
            await self.bot.log_event('tourney', embed=embed, file=file)
            await self.bot.redis.lpush('report:tourney', json.dumps(report))
        self.mode = None
        self.tier = None
        self.private = False
        self.disqualified = []
        self.waitlist = []
        self.participants = {}
        self.register_message = None
        self.autojoin = []
        self.delayed_messages = []     
        self.fetching = False

async def setup(bot):
    await bot.add_cog(Tournament(bot))