import discord, asyncio, random, json
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional

from bot.bot import Kiddo
from assets import armageddon as assets
from classes import armageddon, ui
from utils import checks, embeds, utils

@app_commands.default_permissions(manage_messages=True)
class Armageddon(commands.GroupCog, group_name='armageddon'):
    def __init__(self, bot: Kiddo):
        self.bot = bot
        self.is_first_ready = True
        self.channel = None  # type: ignore
        self.regmsg = None
        self.banned = []
        self.participants = []
        self.field = None
        self.total_deaths = 0
        self.stats = {
            'attacks': 0, # Attack encounters
            'item-m': 0, # Mask
            'item-r': 0, # Rifle
            'item-e': 0, # Explosives
            'item-c': 0, # Canned food
            'item-k': 0, # Knife
            'item-f': 0, # First-aid kit
            'item-w': 0, # Winter clothes
            'k-kill': 0, # Knife kill
            'r-kill': 0, # Rifle kill
            'f-kill': 0, # Fistfight kill
            'e-kill': 0, # Explosives kill
            'w-kill': 0, # Wolf kill
            'n-kill': 0, # Night kill
            'h-kill': 0, # Hunger kill
            's-kill': 0, # Suicide kill
            'a-kill': 0, # Ambush kill
        }
        self.delayed = {}

    @commands.Cog.listener()
    async def on_ready(self):
        if self.is_first_ready:
            await self.bot.loading()
            self.channel: discord.TextChannel = self.bot.get_channel(821995624525201419)  # type: ignore
            print(self.__class__.__name__, 'is ready')
            self.is_first_ready = False

    @tasks.loop(minutes=1)
    async def check_delayed_armageddon(self):
        if not self.regmsg and len(self.delayed) > 0 and self.channel:
            first_event = sorted(self.delayed.keys())[0]
            if first_event > self.check_delayed_armageddon.next_iteration.timestamp(): return
            now = discord.utils.utcnow().timestamp()
            if first_event > now: await asyncio.sleep(first_event - now)
            await self.bot.redis.hdel('delay:armageddon', str(first_event))
            data = self.delayed.pop(first_event)
            if self.regmsg:
                return await self.bot.custom_log(message='An Armageddon event is currently in progress... Scheduled event cancelled...')
            data[0] = self.bot.get_user(data[0])
            data[-1] = self.channel.guild.get_role(data[-1])
            await self.armageddon_setup(*data)

    @checks.perms(mod=True, guild=True)
    @app_commands.describe(
        _max='Stop after starting this many games', wins='Stop after getting this many winners',
        role='Ping this role with each game', delay='Schedule a set of games for later (at specific epoch timestamp)'
    )
    @app_commands.rename(
        _max='max_games', wins='max_winners', role='ping'
    )
    @app_commands.command(name='start')
    async def _app_start(
        self, interaction: discord.Interaction,
        _max: app_commands.Range[int, 1, 10] = 1, wins: Optional[app_commands.Range[int, 1, 5]] = None,
        role: Optional[discord.Role] = None, delay: Optional[int] = None
    ):
        await interaction.response.defer(thinking=True)
        author = interaction.user
        data = [author.id, _max, wins, role.id if role else 0]
        message = [
            None if wins else 'an' if _max == 1 else str(_max),
            'Armageddon game{}'.format('' if wins is None and _max == 1 else 's'),
            'until {wins} winner{s} {be} decided or {max} game{has} passed'.format(
                wins='a' if wins == 1 else wins, s='' if wins == 1 else 's', be='is' if wins == 1 else 'are',
                max=_max, has=' has' if _max == 1 else 's have'
            ) if wins is not None else None,
            'and informing {.mention}'.format(role) if role is not None else None
        ]
        timestamp = int(discord.utils.utcnow().timestamp())
        message.insert(2, 'on <t:{:.0f}>'.format(delay) if delay and delay >= timestamp else None)
        if delay is not None and delay > self.check_delayed_armageddon.next_iteration.timestamp():  # type: ignore
            while delay in self.delayed: message.append('(instead of the previous setting)')
            self.delayed[delay] = data
            await self.bot.redis.hset('delay:armageddon', str(delay), json.dumps(data))
            message = ' '.join(message)
            await interaction.followup.send('Scheduling {}'.format(message), allowed_mentions=discord.AllowedMentions.none())
            return await self.bot.custom_log(message=f'{author.mention} scheduled {message}>')
        elif delay is not None and delay >= timestamp:
            await interaction.followup.send('Scheduling {}'.format(message))
            await self.bot.custom_log(message=f'{author.mention} scheduled {message}>')
            await asyncio.sleep(delay-timestamp)
            timestamp = int(discord.utils.utcnow().timestamp())
        else:
            await interaction.followup.send('Starting {}'.format(message))
        if self.regmsg is None:
            await self.armageddon_setup(author, _max, wins, role)
        else:
            await interaction.followup.send('An Armageddon game is currently in progress... Scheduled event cancelled...', ephemeral=True)

    @checks.perms(mod=True, guild=True)
    @app_commands.describe(
        reward='The total amount to split to the winners', winners='The number of winners to get (get all from last event if not provided)'
    )
    @app_commands.command(name='reward')
    async def _app_reward(
        self, interaction: discord.Interaction,
        reward: app_commands.Range[int, 0] = 50000, winners: Optional[app_commands.Range[int, 1]] = None
    ):
        await interaction.response.defer(thinking=True)
        if winners is None and (res:=await self.bot.redis.lrange('report:armageddons', 0, 0)):
            report = json.loads(res[0])
            wins = sum([i[1] for i in report['winners']])
            message = '\n'.join([
                '```',
                '\n'.join(['$give {} {}'.format(reward // wins * i[1], i[0]) for i in report['winners']]),
                '```'
            ])
            embed = discord.Embed(
                title='Rewarding the last {} wins'.format(wins),
                description=message,
                timestamp=discord.utils.utcnow(),
                color=interaction.user.color.value
            ).add_field(
                name='Statistics',
                value='\n'.join([
                    'Event time: {}'.format(utils.get_timedelta(report['timestamps'][1]-report['timestamps'][0])),
                    '{} players won {}/{} games'.format(
                        len(report['winners']), wins, len(report['reports'])
                    )
                ])
            )
            await interaction.followup.send(embed=embed)
        else:
            w = winners or 5
            res = await self.bot.redis.lrange(f'armageddon:{self.channel.guild.id}:board', 0, w-1)
            if not res: return await interaction.followup.send('No data found')
            message = '\n'.join([
                '```',
                '\n'.join(['$give {} {}'.format(reward // len(res) * res.count(i), i) for i in list(set(res))]),
                '```'
            ])
            embed = discord.Embed(
                title='Rewarding the last {} wins'.format(len(res)),
                description=message,
                timestamp=discord.utils.utcnow(),
                color=interaction.user.color.value
            )
            await interaction.followup.send(embed=embed)

    async def armageddon_setup(self, author, _max, wins, role):
        if self.regmsg or self.channel is None: return
        games = winners = 0
        reports = []
        while True:
            self.field = armageddon.Field()
            timestamp = int(discord.utils.utcnow().timestamp() + 60)
            self.regmsg = ' '.join([i for i in [
                role.mention if role else None,
                'An Armageddon game will start <t:{}:R>.'.format(timestamp)
            ] if i is not None])
            message_list = []
            button = ui.Join(
                waitlist=None, banlist=self.banned, participants=None, label='Armageddon game', msg=message_list
            )
            message_list.append(await self.channel.send(self.regmsg, view=button))
            await asyncio.sleep(60)
            button.stop()
            self.participants = [self.channel.guild.get_member(i) for i in button.reacted]
            self.regmsg = ' '.join([i for i in [
                role.mention if role else None,
                'An Armageddon game started <t:{}:R>.'.format(timestamp),
                '*{} players joined.*'.format(len(self.participants))
            ] if i is not None])
            await message_list[0].edit(content=self.regmsg, view=None)
            report = {
                'mode': 'armageddon game',
                'author': author.id,
                'participants': list(button.reacted)
            }
            if len(self.participants) < 2:
                await self.channel.send('Not enough people joined...')
                break
            if await self.armageddon_start(report):
                winners += 1
            games += 1
            reports.append(report)
            self.clear()
            if _max == games or (wins and wins == winners): break
            await asyncio.sleep(10)
        self.regmsg = None
        total_participants = []
        winners = {}
        for i in reports:
            total_participants += i['participants']
            if i['winner']:
                if i['winner'] in winners: winners[i['winner']] +=1
                else: winners[i['winner']] = 1
        report = {
            'mode': 'armageddon event',
            'author': author.id,
            'timestamp': (reports[0]['timestamp'][0], reports[-1]['timestamp'][1]),
            'games': (_max, wins),
            'winners': sorted([(k, v) for k, v in winners.items()], key=lambda x: x[1], reverse=True),
            'participants': list(set(total_participants)),
            'reports': reports
        }
        embed = embeds.report(report)
        await self.bot.log_event('armageddon', embed=embed)
        await self.bot.custom_log(embed=embed)
        await self.bot.redis.lpush('report:armageddons', json.dumps(report))
    
    async def armageddon_start(self, report):
        if self.field is None: return
        winner = None
        start = discord.utils.utcnow()
        self.participants = [armageddon.Tribute(u) for u in self.participants if u is not None]
        while len(self.participants) > 1:
            random.shuffle(self.participants)
            await self.new_day()
            await self.channel.send(
                '\n'.join([
                    f'**DAY {self.field.day}** - {assets.weather[self.field.weather]}',
                    'Everyone, choose your action! You have 30 seconds to do so.'
                ])
            )
            participants = [asyncio.create_task(self.dm(u)) for u in self.participants if u is not None]
            responses = await asyncio.gather(*participants)
            await self.narrate(responses)
        timestamp = discord.utils.utcnow()
        if len(self.participants) == 1:
            winner = self.participants[0].user
            await self.channel.send(f'The winner is {winner.mention}')
            await self.bot.redis.lpush(f'armageddon:{self.channel.guild.id}:board', winner.id)
        else:
            await self.channel.send('Everyone died!')
        report.update({
            'day': self.field.day,
            'winner': winner.id if winner else None,
            'timestamp': (start.timestamp(), timestamp.timestamp()),
            'stats': dict(self.stats)
        })
        embed = embeds.report(report)
        await self.bot.log_event('armageddon', embed=embed)
        await self.bot.redis.lpush('report:armageddon', json.dumps(report))
        return winner

    async def new_day(self):
        if self.field is None: return
        # Get weather
        self.field.day += 1
        if self.field.day > 1: self.field.weather = random.choices(['blz', 'fld', 'drt', 'fog', 'clr'], cum_weights=[1,2,3,5,10])[0]
        self.field.sniper = False
        if self.field.weather == 'fld': self.field.explosive = 0
        self.participants.sort(key=lambda x: x.rifle, reverse=True)  # type: ignore
        killers = []
        for _ in range(3 if len(self.participants) > 7 else 2):
            sample = []
            weights = []
            for t in self.participants:
                if t not in killers and (self.field.weather != 'blz' or t.clothes):  # type: ignore
                    w = (t.food + t.canned + 3 * t.rifle + 4 * t.annoyed - 2 * t.wounded - 2)  # type: ignore
                    if w > 0:
                        sample.append(t)
                        weights.append(w)
            if len(sample) == 0: break
            killers += random.choices(sample, weights=weights, k=1)
        nonkillers = list(set(self.participants) - set(killers))
        for t in self.participants:
            if self.field.weather == 'drt': t.canned = 0  # type: ignore
            t.options = []  # type: ignore
            functional = self.field.weather != 'blz' or t.clothes  # type: ignore
            # First option: gather food or hide
            if not functional:
                t.options.append(armageddon.ArenaChoice('g2'))  # type: ignore
            else:
                t.options.append(armageddon.ArenaChoice('g1'))  # type: ignore
            # Second option: loot or suicide
            if t.food > 0 and functional:  # type: ignore
                t.options.append(armageddon.ArenaChoice('g3'))  # type: ignore
            else:
                t.options.append(armageddon.ArenaChoice('s1'))  # type: ignore
            # Third option: kill, die, heal, or relationship
            if t in killers:
                if t.rifle and not self.field.sniper and self.field.weather != 'fog' and random.randrange(3) < 2:  # type: ignore
                    target = random.choice(list(set(self.participants) - set([t])))
                    t.options.append(armageddon.ArenaChoice('k3', target))  # type: ignore
                    self.field.sniper = True
                    killers.remove(t)
                else:
                    target = None
                    if random.randrange(100) < 50 and len(list(set(killers) - set([t]))) > 0:
                        target = random.choice(list(set(killers) - set([t])))
                    elif len(nonkillers) > 0:
                        t_pool = []
                        t_weight = []
                        for p in nonkillers:
                            p_id = str(p.user.id)  # type: ignore
                            w = 20 - t.relationship[p_id] if p_id in t.relationship else 20  # type: ignore
                            t_weight.append(w if w > 0 else 1)
                            t_pool.append(p)
                        target = random.choices(t_pool, weights=t_weight)[0]
                    ac = random.randrange(100)
                    if target is not None and ((self.field.weather == 'fog' and ac < 25) or ac < 75):
                        t.options.append(armageddon.ArenaChoice('k2', target))  # type: ignore
                    else:
                        target = random.choice(['river', 'warehouse'])
                        t.options.append(armageddon.ArenaChoice('k1', target))  # type: ignore
            if len(t.options) < 3:  # type: ignore
                if t.wounded and t.kit and t.available_option('i1'):  # type: ignore
                    t.options.append(armageddon.ArenaChoice('i1'))  # type: ignore
                elif t.wounded > 2:  # type: ignore
                    t.options.append(armageddon.ArenaChoice('s2'))  # type: ignore
            functional *= len(t.options) < 3  # type: ignore
            count = 0
            while functional and count < 10:
                if t.available_option('g2') and random.randrange(4) == 2:  # type: ignore
                    t.options.append(armageddon.ArenaChoice('g2'))  # type: ignore
                elif t.wounded > 2 and t.available_option('s2') and random.randrange(5) > 1:  # type: ignore
                    t.options.append(armageddon.ArenaChoice('s2'))  # type: ignore
                elif t.wounded and t.kit and t.available_option('i1') and random.randrange(2) == 1:  # type: ignore
                    t.options.append(armageddon.ArenaChoice('i1'))  # type: ignore
                elif t.explosive and self.field.weather != 'fld' and t.available_option('i2') and random.randrange(2):  # type: ignore
                    t.options.append(armageddon.ArenaChoice('i2'))  # type: ignore
                elif t.available_option('s1') and random.randrange(10) == 5:  # type: ignore
                    t.options.append(armageddon.ArenaChoice('s1'))  # type: ignore
                elif t.available_option('g3') and random.randrange(10) == 7:  # type: ignore
                    t.options.append(armageddon.ArenaChoice('g3'))  # type: ignore
                elif t.available_option('r1') and len(t.relationship) == 0:  # type: ignore
                    t.options.append(armageddon.ArenaChoice('r1'))  # type: ignore
                elif len(t.relationship) > 0:  # type: ignore
                    rel = random.choice(list(t.relationship.keys()))  # type: ignore
                    target = discord.utils.find(lambda x: x.user.id == int(rel), self.participants)  # type: ignore
                    gesture = random.randrange(t.relationship[rel]) if t.relationship[rel] > 0 else 0  # type: ignore
                    if not target: t.relationship.pop(rel)  # type: ignore
                    if target and gesture < 3 and t.available_option('r2', target):  # type: ignore
                        t.options.append(armageddon.ArenaChoice('r2', target))  # type: ignore
                    elif target and gesture < 8 and t.available_option('r4', target):  # type: ignore
                        t.options.append(armageddon.ArenaChoice('r4', target))  # type: ignore
                    elif target and t.available_option('r5', target):  # type: ignore
                        t.options.append(armageddon.ArenaChoice('r5', target))  # type: ignore
                    elif t.available_option('r1') and not target:  # type: ignore
                        t.options.append(armageddon.ArenaChoice('r1'))  # type: ignore
                functional = len(t.options) < t.food  # type: ignore
                count += 1
            random.shuffle(t.options)  # type: ignore

    async def dm(self, tribute):
        if self.field is None: return
        inventory = ''
        if tribute.food > 0:
            for _ in range(tribute.food):
                inventory += '💧'
        inventory += '\nItems:'
        if tribute.clothes: inventory += '\n> Some winter clothes'
        if tribute.canned: inventory += '\n> Some canned food'
        if tribute.kit:
            inventory += '\n> '
            for _ in range(tribute.kit):
                inventory += '❤️‍🩹'
            inventory += ' A first-aid kit'
        if tribute.explosive: inventory += '\n> Some explosives'
        if tribute.knife: inventory += '\n> A rusty knife'
        if tribute.rifle: inventory += '\n> An old rifle'
        if inventory.endswith(':'): inventory += ' None'
        if tribute.wounded:
            inventory += '\n'
            for _ in range(tribute.wounded):
                inventory += '🩸'
            inventory += ' You are bleeding.'
        if tribute.food + tribute.canned < 1:
            inventory += '\n🧟‍♂️ You will die of malnourishment if you don\'t have anything to eat.'
        elif tribute.food + tribute.canned + 3 * tribute.rifle + 4 * tribute.annoyed - 2 * tribute.wounded - 2 <= 0:
            inventory += '\nYou cannot fight in your current state. Try to get more food or heal your wounds.'
        options = tribute.options

        o_list = [
            f'{assets.emojis[i]} {assets.options[options[i].option].format(target=(options[i].target if options[i].target and isinstance(options[i].target, str) else options[i].target.user.name if options[i].target else None))}' for i in range(len(options))
        ]
        def check(r, u):
            return u.id == tribute.user.id and str(r) in assets.emojis[:len(o_list)]
        embed = discord.Embed(
            title=f'Day {self.field.day} - {assets.weather[self.field.weather]}',
            description=inventory
        ).set_footer(
            text=random.choice(assets.tips) + ('' if self.field.mask['fake'] and self.field.mask['fake'].user.id == tribute.user.id else '.')
        ).add_field(
            name='Pick an option', value='\n'.join(o_list)
        ).set_author(
            name=self.channel.guild.name,
            icon_url=self.channel.guild.icon.url  # type: ignore
        )
        try:
            dm_message = await tribute.user.send(embed=embed)
            for i in range(len(o_list)):
                await dm_message.add_reaction(assets.emojis[i])
            try:
                (r, u) = await self.bot.wait_for('reaction_add', check=check, timeout=30)
                r = str(r)
                await tribute.user.send('You picked {}\nReturn to {}'.format(r, self.channel.mention), delete_after = 15)
            except asyncio.TimeoutError:
                r = random.choice(assets.emojis[:len(o_list)])
                await tribute.user.send('You did not pick an option, a random option was selected.\nReturn to {}'.format(self.channel.mention), delete_after = 15)
            await dm_message.delete(delay=15)
        except Exception:
            r = random.choice(assets.emojis[:len(o_list)])

        return {
            'trb': tribute,
            'tgt': options[assets.emojis.index(r)].target,
            'opt': options[assets.emojis.index(r)].option
        }

    async def narrate(self, participants):
        p_count = len(self.participants)
        new_mask = {
            'real': None,
            'fake': None
        }
        await self.channel.send('The remaining survivors split up.')
        await asyncio.sleep(3)
        msg = []
        for p in self.participants:
            p.annoyed = False  # type: ignore
            if p.canned > 0:  # type: ignore
                p.canned -= 1  # type: ignore
            else:
                p.food -= 1  # type: ignore
        action = [p for p in participants if p['opt'] == 's2']
        if len(action) > 0:
            self.stats['s-kill'] += len(action)
            self.total_deaths += len(action)
            msg.append([
                '{} bled to death from their wounds.'.format(
                    self.getname(action[0]['trb']) if len(action) < 2 else
                    (
                        ', '.join([self.getname(p['trb']) for p in action[:-1]])
                        + (',' if len(action) > 2 else '')
                        + ' and ' + self.getname(action[-1]['trb'])
                    )
                ),
                [p['trb'].user.send(random.choice(assets.elimination_phrases), delete_after=300) for p in action]
            ])
            for p in action:
                try:
                    self.participants.remove(p['trb'])
                except Exception:
                    pass
        action = [p for p in participants if p['opt'] == 's1']
        if len(action) > 0:
            self.stats['s-kill'] += len(action)
            self.total_deaths += len(action)
            for p in action:
                if self.field.mask['fake'] and self.field.mask['fake'].user.id == p['trb'].user.id:  # type: ignore
                    msg.append([
                        '{name} threw {name} off a cliff.'.format(name=self.getname(p['trb'])),
                        [self.field.mask['real'].user.send('You got thrown off a cliff.', delete_after=300)]  # type: ignore
                    ])
                    try:
                        self.participants.remove(self.field.mask['real'])  # type: ignore
                    except Exception:
                        pass
                else:
                    msg.append([
                        '{} threw themself off a cliff.'.format(self.getname(p['trb'])),
                        [p['trb'].user.send(random.choice(assets.elimination_phrases), delete_after=300)]
                    ])
                    try:
                        self.participants.remove(p['trb'])
                    except Exception:
                        pass
        if random.randrange(8) < self.field.explosive:  # type: ignore
            casualty = random.choice([2, 3]) if len(self.participants) > 3 else len(self.participants)
            self.stats['e-kill'] += casualty
            self.total_deaths += casualty
            action = random.sample(self.participants, k=casualty)
            msg.append([
                '{} stepped on an explosive trap... They didn\'t make it, and neither did {}, who stood nearby...'.format(
                    self.getname(action[0]), ' and '.join([self.getname(p) for p in action[1:]])
                ),
                [p.user.send(random.choice(assets.elimination_phrases), delete_after=300) for p in action]  # type: ignore
            ])
            self.field.explosive = 1  # type: ignore
            for p in action:
                try:
                    self.participants.remove(p)  # type: ignore
                    a = discord.utils.find(lambda x: x['trb'].user.id == p.user.id, participants)  # type: ignore
                    participants.remove(a)
                except Exception:
                    pass
        action = [p for p in participants if p['opt'] == 'i1']
        for p in action:
            p['trb'].kit -= 1
            p['trb'].wounded = 0
            msg.append([
                '{} applied first-aid to their wounds.'.format(self.getname(p['trb'])),
                [] if p['trb'].kit > 0 else [p['trb'].user.send('You used up everything in your first-aid kit.', delete_after=300)]
            ])
        action = [p for p in participants if p['opt'] == 'i2']
        for p in action:
            self.field.explosive += p['trb'].explosive  # type: ignore
            p['trb'].explosive = 0
            msg.append([
                '{} set some explosive traps around the arena.'.format(self.getname(p['trb'])), 
                [p['trb'].user.send('You used all your explosives.', delete_after=300)]
            ])
        action = [p for p in participants if p['opt'] == 'g3']
        random.shuffle(action)
        for p in action:
            chance = random.randrange(25)
            mask_choices = [t for t in self.participants if t.user.id != p['trb'].user.id]  # type: ignore
            if new_mask['real'] == None and len(mask_choices) > 0 and random.randrange(4) == 0:
                self.stats['item-m'] += 1
                new_mask['real'] = p['trb']
                new_mask['fake'] = random.choice(mask_choices)  # type: ignore
                msg.append([
                    '{} looted an abandoned warehouse.'.format(self.getname(p['trb'])),
                    [p['trb'].user.send('You found a mask that looks like {}. For an entire day next day, you will look like them.'.format(new_mask['fake'].user), delete_after=300)]  # type: ignore
                ])
            elif chance < 1:
                self.stats['item-r'] += 1
                msg.append([
                    '{} looted an abandoned warehouse.'.format(self.getname(p['trb'])),
                    [p['trb'].user.send('You found an old rifle.' + (' You disposed of your damaged one.' if p['trb'].rifle else ''), delete_after=300)]
                ])
                p['trb'].rifle = True
            elif chance < 5:
                self.stats['item-e'] += 1
                p['trb'].explosive += 1
                msg.append([
                    '{} looted an abandoned warehouse.'.format(self.getname(p['trb'])),
                    [p['trb'].user.send('You found some explosives.', delete_after=300)]
                ])
            elif chance < 9:
                self.stats['item-c'] += 1
                msg.append([
                    '{} looted an abandoned warehouse.'.format(self.getname(p['trb'])),
                    [p['trb'].user.send('You found some canned food.', delete_after=300)]
                ])
                p['trb'].canned = 3
            elif chance < 14:
                self.stats['item-k'] += 1
                msg.append([
                    '{} looted an abandoned warehouse.'.format(self.getname(p['trb'])),
                    [p['trb'].user.send('You found a rusty knife.' + (' You threw away your old one.' if p['trb'].knife else ''), delete_after=300)]
                ])
                p['trb'].knife = 2
            elif chance < 19:
                self.stats['item-f'] += 1
                kval = random.choices([1, 2, 3], weights=[5, 3, 2])[0]
                msg.append([
                    '{} looted an abandoned warehouse.'.format(self.getname(p['trb'])),
                    [p['trb'].user.send(f'You found a{" tiny" if kval == 1 else " small" if kval == 2 else ""} first-aid kit.' + (' You threw away old kit.' if p['trb'].kit > 0 and p['trb'].kit < kval else ''), delete_after=300)]
                ])
                if kval > p['trb'].kit: p['trb'].kit = kval
            else:
                self.stats['item-w'] += 1
                msg.append([
                    '{} looted an abandoned warehouse.'.format(self.getname(p['trb'])),
                    [p['trb'].user.send('You found some winter clothes.', delete_after=300)]
                ])
                p['trb'].clothes = 5
        action = [p for p in participants if p['opt'] == 'g1']
        for p in action:
            msg.append([
                '{} found food near the river.'.format(self.getname(p['trb'])), []
            ])
            p['trb'].food = 5
        random.shuffle(msg)
        action = [p for p in participants if p['opt'] == 'k3']
        if len(action) > 0:
            p = action[0]
            if discord.utils.find(lambda x: x.user.id == p['trb'].user.id, self.participants):  # type: ignore
                target = discord.utils.find(lambda x: x.user.id == p['tgt'].user.id, self.participants)  # type: ignore
                if target:
                    t_action = discord.utils.find(lambda x: x['trb'].user.id == target.user.id, participants)  # type: ignore
                    if t_action['opt'] == 'g2' or (self.field.mask['real'] is not None and target.user.id == self.field.mask['real'].user.id):  # type: ignore
                        msg.append([None, [p['trb'].user.send('You couldn\'t locate {}.'.format(target.user.name), delete_after=300)]])  # type: ignore
                    else:
                        target = self.gettarget(target)
                        self.stats['r-kill'] += 1
                        self.total_deaths += 1
                        p['trb'].rifle = False
                        msg.append([
                            '{} were walking when suddenly a bullet went through their head.'.format(self.getname(target)),
                            [p['trb'].user.send('Your rifle broke.', delete_after=300), target.user.send('You died', delete_after=300)]  # type: ignore
                        ])
                        try:
                            self.participants.remove(target)  # type: ignore
                        except Exception:
                            pass
        action = [p for p in participants if p['opt'] == 'k1']
        if len(action) > 0:
            for p in action:
                if discord.utils.find(lambda x: x.user.id == p['trb'].user.id, self.participants):  # type: ignore
                    if p['tgt'] == 'river':
                        p_target = [t for t in participants if t['opt'] == 'g1' and t['trb'] in self.participants]
                    else:
                        p_target = [t for t in participants if t['opt'] == 'g3' and t['trb'] in self.participants]
                    if len(p_target) == 0:
                        msg.append([None, [p['trb'].user.send('Nobody came near the {}'.format(p['tgt']), delete_after=300)]])
                    else:
                        target = random.choice(p_target)
                        killed = False
                        target['trb'].wounded += 1
                        killed = random.randrange(2) == 1 or p['trb'].knife or self.field.weather == 'fog'  # type: ignore
                        msg.append([
                            'While returning from the {}, {} was attacked{}by {}{}'.format(
                                p['tgt'], self.getname(target['trb']), ' and killed ' if killed else ' ', self.getname(p['trb']), '.' if killed else ' but managed to get away.'
                            ),
                            ([p['trb'].user.send('Your knife broke.', delete_after=300)] if p['trb'].knife == 1 else []) + ([target['trb'].user.send(random.choice(assets.elimination_phrases), delete_after=300)] if killed else [])
                        ])
                        if p['trb'].knife: p['trb'].knife -= 1
                        if killed:
                            self.stats['a-kill'] += 1
                            self.total_deaths += 1
                            try:
                                self.participants.remove(target['trb'])
                            except Exception:
                                pass
                        else:
                            target['trb'].impression(p['trb'].user, 'attack')
        action = [p for p in participants if p['opt'] == 'k2']
        if len(action) > 1:
            pair = []
            for p in action[:-1]:
                for i in range(action.index(p)+1, len(action)):
                    if (
                        p['tgt'].user.id == action[i]['trb'].user.id
                        and p['trb'].user.id == action[i]['tgt'].user.id
                        and (
                            self.field.mask['real'] is None  # type: ignore
                            or (p['tgt'].user.id != self.field.mask['real'].user.id and action[i]['tgt'].user.id != self.field.mask['real'].user.id)  # type: ignore
                        )
                    ):
                        pair = [p, action[i]]
                        break
                if len(pair) > 0: break
            if len(pair) > 0:
                action = [p for p in action if p not in pair]
                chance = random.random()
                knives = (pair[0]['trb'].knife > 0) + (pair[1]['trb'].knife > 0)
                pair.sort(key=lambda p: p['trb'].knife)
                if knives == 2:
                    # DD
                    if chance < 0.5625:
                        self.stats['attacks'] += 2
                        self.stats['k-kill'] += 2
                        self.total_deaths += 2
                        msg.append([
                            '{} and {} engaged in a knife fight. Neither survived.'.format(*[p['trb'].user.name for p in pair]),
                            [p['trb'].user.send(random.choice(assets.elimination_phrases), delete_after=300) for p in pair]
                        ])
                        for p in pair:
                            try:
                                self.participants.remove(p['trb'])
                            except Exception:
                                pass
                    # WD
                    elif chance < 0.75:
                        self.stats['attacks'] += 2
                        self.stats['k-kill'] += 1
                        self.total_deaths += 1
                        msg.append([
                            '{} and {} engaged in a knife fight. {} came out on top, but not without sustaining serious injury.'.format(*[p['trb'].user.name for p in pair], pair[0]['trb'].user.name),
                            ([] if pair[0]['trb'].knife != 1 else [pair[0]['trb'].user.send('Your knife broke.', delete_after=300)]) + [pair[1]['trb'].user.send(random.choice(assets.elimination_phrases), delete_after=300)]
                        ])
                        pair[0]['trb'].knife -= 1
                        pair[0]['trb'].wounded += 1
                        try:
                            self.participants.remove(pair[1]['trb'])
                        except Exception:
                            pass
                    # DW
                    elif chance < 0.9375:
                        self.stats['attacks'] += 2
                        self.stats['k-kill'] += 1
                        self.total_deaths += 1
                        msg.append([
                            '{} and {} engaged in a knife fight. {} came out on top, but not without sustaining serious injury.'.format(*[p['trb'].user.name for p in pair], pair[1]['trb'].user.name),
                            ([] if pair[1]['trb'].knife != 1 else [pair[1]['trb'].user.send('Your knife broke.', delete_after=300)]) + [pair[0]['trb'].user.send(random.choice(assets.elimination_phrases), delete_after=300)]
                        ])
                        pair[1]['trb'].knife -= 1
                        pair[1]['trb'].wounded += 1
                        try:
                            self.participants.remove(pair[0]['trb'])
                        except Exception:
                            pass
                    # WW
                    else:
                        self.stats['attacks'] += 2
                        msg.append([
                            '{} and {} engaged in a knife fight. Both managed to walk away with some injury.'.format(*[p['trb'].user.name for p in pair]),
                            ([] if pair[0]['trb'].knife != 1 else [pair[0]['trb'].user.send('Your knife broke.', delete_after=300)]) + ([] if pair[1]['trb'].knife != 1 else [pair[1]['trb'].user.send('Your knife broke.', delete_after=300)])
                        ])
                        for i in range(2):
                            pair[i]['trb'].impression(pair[1-i]['trb'].user, 'attack')
                            pair[i]['trb'].knife -= 1
                            pair[i]['trb'].wounded += 1
                elif knives == 1:
                    # DD
                    if chance < 0.1875:
                        self.stats['attacks'] += 2
                        self.stats['f-kill'] += 1
                        self.stats['k-kill'] += 1
                        self.total_deaths += 2
                        msg.append([
                            '{} and {} engaged in a fight. Neither survived.'.format(*[p['trb'].user.name for p in pair]),
                            [p['trb'].user.send('You died', delete_after=300) for p in pair]
                        ])
                        for p in pair:
                            try:
                                self.participants.remove(p['trb'])
                            except Exception:
                                pass
                    # WD
                    elif chance < 0.25:
                        self.stats['attacks'] += 2
                        self.stats['f-kill'] += 1
                        self.total_deaths += 1
                        msg.append([
                            '{} and {} engaged in a fight. Despite having a knife, {} was killed while {} could still walk away with heavy injury.'.format(*[p['trb'].user.name for p in pair], pair[1]['trb'].user.name, pair[0]['trb'].user.name),
                            [pair[1]['trb'].user.send('You died', delete_after=300)]
                        ])
                        try:
                            self.participants.remove(pair[1]['trb'])
                        except Exception:
                            pass
                        pair[0]['trb'].wounded += 1
                    # DW
                    elif chance < 0.625:
                        self.stats['attacks'] += 2
                        self.stats['k-kill'] += 1
                        self.total_deaths += 1
                        msg.append([
                            '{} and {} engaged in a fight. Bringing a knife to a fistfight, {} managed to kill {} while sustaining some injury.'.format(*[p['trb'].user.name for p in pair], pair[1]['trb'].user.name, pair[0]['trb'].user.name),
                            ([] if pair[1]['trb'].knife != 1 else [pair[1]['trb'].user.send('Your knife broke.', delete_after=300)]) + [pair[0]['trb'].user.send(random.choice(assets.elimination_phrases), delete_after=300)]
                        ])
                        try:
                            self.participants.remove(pair[0]['trb'])
                        except Exception:
                            pass
                        pair[1]['trb'].wounded += 1
                        pair[1]['trb'].knife -= 1
                    # WW
                    elif chance < 0.75:
                        self.stats['attacks'] += 2
                        msg.append([
                            '{} and {} engaged in a fight. Both managed to walk away with some injury.'.format(*[p['trb'].user.name for p in pair]),
                            [] if pair[1]['trb'].knife != 1 else [pair[1]['trb'].user.send('Your knife broke.', delete_after=300)]
                        ])
                        pair[1]['trb'].knife -= 1
                        for i in range(2):
                            pair[i]['trb'].impression(pair[1-i]['trb'].user, 'attack')
                            pair[i]['trb'].wounded += 1
                    # DU
                    elif chance < 0.9375:
                        self.stats['attacks'] += 2
                        self.stats['k-kill'] += 1
                        self.total_deaths += 1
                        msg.append([
                            '{} and {} engaged in a fight. Bringing a knife to a fistfight, {} was able to kill {} unscathed.'.format(*[p['trb'].user.name for p in pair], pair[1]['trb'].user.name, pair[0]['trb'].user.name),
                            ([] if pair[1]['trb'].knife != 1 else [pair[1]['trb'].user.send('Your knife broke.', delete_after=300)]) + [pair[0]['trb'].user.send(random.choice(assets.elimination_phrases), delete_after=300)]
                        ])
                        try:
                            self.participants.remove(pair[0]['trb'])
                        except Exception:
                            pass
                        pair[1]['trb'].knife -= 1
                    # WU
                    else:
                        self.stats['attacks'] += 2
                        msg.append([
                            '{} and {} engaged in a fight. Upon seeing {}\'s knife, {} was able to escape with some injury.'.format(*[p['trb'].user.name for p in pair], pair[1]['trb'].user.name, pair[0]['trb'].user.name),
                            [] if pair[1]['trb'].knife != 1 else [pair[1]['trb'].user.send('Your knife broke.', delete_after=300)]
                        ])
                        pair[0]['trb'].wounded += 1
                        pair[1]['trb'].knife -= 1
                        for i in range(2):
                            pair[i]['trb'].impression(pair[1-i]['trb'].user, 'attack')
                else:
                    # DD
                    if chance < 0.0625:
                        self.stats['attacks'] += 2
                        self.stats['f-kill'] += 2
                        self.total_deaths += 2
                        msg.append([
                            '{} and {} engaged in a fistfight. Neither survived.'.format(*[p['trb'].user.name for p in pair]),
                            [p['trb'].user.send(random.choice(assets.elimination_phrases), delete_after=300) for p in pair]
                        ])
                        for p in pair:
                            try:
                                self.participants.remove(p['trb'])
                            except Exception:
                                pass
                    # UU
                    elif chance < 0.125:
                        self.stats['attacks'] += 2
                        msg.append([
                            '{} and {} engaged in a fistfight. Both managed to walk away without any serious injury.'.format(*[p['trb'].user.name for p in pair]),
                            []
                        ])
                        for i in range(2):
                            pair[i]['trb'].impression(pair[1-i]['trb'].user, 'attack')
                    # DU
                    elif chance < 0.25:
                        self.stats['attacks'] += 2
                        self.stats['f-kill'] += 1
                        self.total_deaths += 1
                        winner = random.randrange(2)
                        msg.append([
                            '{} and {} engaged in a fistfight. {} managed to kill {} without any serious injury.'.format(*[p['trb'].user.name for p in pair], pair[winner]['trb'].user.name, pair[1-winner]['trb'].user.name),
                            [pair[1-winner]['trb'].user.send(random.choice(assets.elimination_phrases), delete_after=300)]
                        ])
                        try:
                            self.participants.remove(pair[1-winner]['trb'])
                        except Exception:
                            pass
                    # WW
                    elif chance < 0.5:
                        self.stats['attacks'] += 2
                        msg.append([
                            '{} and {} engaged in a fistfight. Both managed to walk away with some injury.'.format(*[p['trb'].user.name for p in pair]),
                            []
                        ])
                        for i in range(2):
                            pair[i]['trb'].impression(pair[1-i]['trb'].user, 'attack')
                            pair[i]['trb'].wounded += 1
                    # DW
                    elif chance < 0.75:
                        self.stats['attacks'] += 2
                        self.stats['f-kill'] += 1
                        self.total_deaths += 1
                        winner = random.randrange(2)
                        msg.append([
                            '{} and {} engaged in a fistfight. {} managed to kill {} while sustaining some injury.'.format(*[p['trb'].user.name for p in pair], pair[winner]['trb'].user.name, pair[1-winner]['trb'].user.name),
                            [pair[1-winner]['trb'].user.send(random.choice(assets.elimination_phrases), delete_after=300)]
                        ])
                        try:
                            self.participants.remove(pair[1-winner]['trb'])
                        except Exception:
                            pass
                        pair[winner]['trb'].wounded += 1
                    # WU
                    else:
                        self.stats['attacks'] += 2
                        winner = random.randrange(2)
                        msg.append([
                            '{} and {} engaged in a fistfight. {} managed to run away from {} while sustaining some injury.'.format(*[p['trb'].user.name for p in pair], pair[1-winner]['trb'].user.name, pair[winner]['trb'].user.name),
                            []
                        ])
                        pair[1-winner]['trb'].wounded += 1
                        for i in range(2):
                            pair[i]['trb'].impression(pair[1-i]['trb'].user, 'attack')
        if len(action) > 0:
            for p in action:
                if discord.utils.find(lambda x: x.user.id == p['trb'].user.id, self.participants):  # type: ignore
                    target = discord.utils.find(lambda x: x.user.id == p['tgt'].user.id, self.participants)  # type: ignore
                    if target:
                        #TODO: Check this
                        tid = target.user.id  # type: ignore
                        tname = target.user.name  # type: ignore
                        target = self.gettarget(target)
                        t_action = discord.utils.find(lambda x: x['trb'].user.id == target.user.id, participants)  # type: ignore
                        located = (
                            (
                                (t_action and t_action['opt'] != 'g2' and t_action['opt'] != 'k1')  # type: ignore
                                or (random.random() < 0.25 and self.field.weather != 'fog')  # type: ignore
                            ) and (self.field.mask['real'] is None or tid != self.field.mask['real'].user.id)  # type: ignore
                        )
                        if not located:
                            msg.append([None, [p['trb'].user.send('You couldn\'t find {}.'.format(tname), delete_after=300)]])
                        else:
                            chance = random.random()
                            if chance < 0.25 or (p['trb'].knife and chance < 0.5):
                                self.stats['attacks'] += 1
                                self.total_deaths += 1
                                if p['trb'].knife:
                                    self.stats['k-kill'] += 1
                                else:
                                    self.stats['f-kill'] += 1
                                msg.append([
                                    '{} killed {}.'.format(self.getname(p['trb']), self.getname(target)),
                                    ([] if p['trb'].knife != 1 else [p['trb'].user.send('Your knife broke.', delete_after=300)]) + [target.user.send(random.choice(assets.elimination_phrases), delete_after=300)]  # type: ignore
                                ])
                                if p['trb'].knife: p['trb'].knife -= 1
                                try:
                                    self.participants.remove(target)  # type: ignore
                                except Exception:
                                    pass
                            elif chance < 0.75 or p['trb'].knife:
                                self.stats['attacks'] += 1
                                msg.append([
                                    '{} attacked and injured {}.'.format(self.getname(p['trb']), self.getname(target)),
                                    [] if p['trb'].knife != 1 else [p['trb'].user.send('Your knife broke.', delete_after=300)]
                                ])
                                if p['trb'].knife: p['trb'].knife -= 1
                                target.wounded += 1  # type: ignore
                                target.impression(p['trb'].user, 'attack')  # type: ignore
                                p['trb'].impression(target.user, 'attack')  # type: ignore
                            else:
                                self.stats['attacks'] += 1
                                msg.append([
                                    '{} failed to attack {}.'.format(self.getname(p['trb']), self.getname(target)), []
                                ])
                                target.impression(p['trb'].user, 'attack')  # type: ignore
                                p['trb'].impression(target.user, 'attack')  # type: ignore
        action = [p for p in participants if p['opt'] == 'r1' and discord.utils.find(lambda x: x.user.id == p['trb'].user.id, self.participants)]  # type: ignore
        random.shuffle(action)
        if len(action) % 2 != 0:
            index = random.randrange(len(msg)) if len(msg) > 0 else 0
            msg.insert(index, ['{} wandered around without running into anyone.'.format(self.getname(action[-1]['trb'])), []])
            action = action[:-1]
        for i in range(0, len(action), 2):
            m = '{} decided to team up with {}'.format(self.getname(action[i]['trb']), self.getname(action[i+1]['trb']))
            index = random.randrange(len(msg)) if len(msg) > 0 else 0
            msg.insert(index, [m, []])
            action[i]['trb'].impression(action[i+1]['trb'].user, 'ally')
            action[i+1]['trb'].impression(action[i]['trb'].user, 'ally')
        action = [p for p in participants if p['opt'] == 'r2' and discord.utils.find(lambda x: x.user.id == p['trb'].user.id, self.participants)]  # type: ignore
        if len(action) > 0:
            for i in range(len(action)):
                action[i]['tgt'] = self.gettarget(action[i]['tgt'])
                m = '{} annoyed {}.'.format(self.getname(action[i]['trb']), self.getname(action[i]['tgt']))
                index = random.randrange(len(msg)) if len(msg) > 0 else 0
                msg.insert(index, [m, []])
                action[i]['trb'].impression(action[i]['tgt'].user, 'annoy')
                action[i]['tgt'].impression(action[i]['trb'].user, 'annoy')
        action = [p for p in participants if p['opt'] == 'r3' and discord.utils.find(lambda x: x.user.id == p['trb'].user.id, self.participants)]  # type: ignore
        if len(action) > 1:
            users = [p['trb'] for p in action]
            index = random.randrange(len(msg)) if len(msg) > 0 else 0
            msg.insert(index, [
                '{} hung out together.'.format(
                    ', '.join([self.getname(p) for p in users[:-1]])
                    + (',' if len(users) > 2 else '')
                    + ' and ' + self.getname(users[-1])
                ),
                []
            ])
            for p in action:
                for u in users:
                    if p['trb'].user.id != u.user.id:
                        p['trb'].impression(u.user, 'group')
        action = [p for p in participants if p['opt'] == 'r4' and discord.utils.find(lambda x: x.user.id == p['trb'].user.id, self.participants)]  # type: ignore
        if len(action) > 0:
            for p in action:
                p['tgt'] = self.gettarget(p['tgt'])
                activity = random.choice(['movie', 'picnic', 'sleep'])
                if activity == 'movie':
                    m = '{} dragged {} to a movie.'.format(self.getname(p['trb']), self.getname(p['tgt']))
                elif activity == 'picnic':
                    m = '{} invited {} to a picnic.'.format(self.getname(p['trb']), self.getname(p['tgt']))
                else:
                    m = '{} asked {} over for a sleepover.'.format(self.getname(p['trb']), self.getname(p['tgt']))
                index = random.randrange(len(msg)) if len(msg) > 0 else 0
                msg.insert(index, [m, []])
                p['trb'].impression(p['tgt'].user, activity)
                p['tgt'].impression(p['trb'].user, activity)
        # Release the wolves
        action = [p for p in participants if p['opt'] == 'g2' and discord.utils.find(lambda x: x.user.id == p['trb'].user.id, self.participants)]  # type: ignore
        self.field.wolf += len(action)  # type: ignore
        if len(action) > 0 and random.randrange(50) < self.field.wolf:  # type: ignore
            self.stats['w-kill'] += 1
            self.total_deaths += 1
            p = random.choice(action)['trb']
            m = '{} was attacked and killed by wild wolves because they accidentally hid inside a wolf\'s den.'.format(self.getname(p))
            index = random.randrange(len(msg)) if len(msg) > 0 else 0
            msg.insert(index, [m, [p.user.send(random.choice(assets.elimination_phrases), delete_after=300)]])
            try:
                self.participants.remove(p)
            except Exception:
                pass
        # Evening activities
        if len(self.participants) == p_count:
            self.field.no_deaths += 1  # type: ignore
        else:
            self.field.no_deaths = 0  # type: ignore
        action = [p for p in participants if p['opt'] == 'r5' and discord.utils.find(lambda x: x.user.id == p['trb'].user.id, self.participants)]  # type: ignore
        if len(action) > 0:
            for p in action:
                activity = random.choice(['dinner', 'stargaze', 'kiss'])
                p['tgt'] = self.gettarget(p['tgt'])
                if activity == 'dinner':
                    m = '{} and {} enjoyed a candlelit dinner.'.format(self.getname(p['trb']), self.getname(p['tgt']))
                elif activity == 'stargaze':
                    m = '{} and {} went stargazing.'.format(self.getname(p['trb']), self.getname(p['tgt']))
                else:
                    m = '{} and {} kissed under the moonlight.'.format(self.getname(p['trb']), self.getname(p['tgt']))
                msg.append([m, []])
                p['trb'].impression(p['tgt'].user, activity)
                p['tgt'].impression(p['trb'].user, activity)
        group1 = []
        group2 = []
        group3 = []
        if len(self.participants) > 5: group1 = random.sample(self.participants, k=5)
        if len(self.participants) > 3: group2 = random.sample(self.participants, k=3)
        if len(self.participants) > 1: group3 = random.sample(self.participants, k=2)
        if len(group1) > 0:
            users = [p for p in group1]
            msg.append([
                '{} gathered around and played Truth or Dare.'.format(
                    ', '.join([self.getname(p) for p in users[:-1]])
                    + ', and ' + self.getname(users[-1])
                ),
                []
            ])
            for p in group1:
                for u in users:
                    if p.user.id != u.user.id:  # type: ignore
                        p.impression(u.user, 'tod')  # type: ignore
        if len(group2) > 0:
            users = [p for p in group2]
            msg.append([
                '{} enjoyed the silence of the night.'.format(
                    ', '.join([self.getname(p) for p in users[:-1]])
                    + ', and ' + self.getname(users[-1])
                ),
                []
            ])
            for p in group2:
                for u in users:
                    if p.user.id != u.user.id:  # type: ignore
                        p.impression(u.user, 'silence')  # type: ignore
        if len(group3) > 0:
            if self.field.no_deaths < random.randrange(10):  # type: ignore
                msg.append([
                    '{} and {} disappeared into the night.'.format(*[
                        self.getname(p) for p in group3
                    ]),
                    []
                ])
                group3[0].impression(group3[1].user, 'snuck')  # type: ignore
                group3[1].impression(group3[0].user, 'snuck')  # type: ignore
            else:
                if self.field.no_deaths > 2 and random.randrange(20) < self.field.wolf:  # type: ignore
                    index = random.randrange(len(msg)) if len(msg) > 0 else 0
                    msg.insert(index, ['The sound of wolves howling caught the survivors\' attention.', []])
                    if len(self.participants) < self.field.wolf:  # type: ignore
                        sample = random.randrange(len(self.participants)) + 1
                    else:
                        sample = random.randrange(self.field.wolf) + 1  # type: ignore
                    self.stats['w-kill'] += sample
                    self.total_deaths += sample
                    targets = random.sample(self.participants, k=sample)
                    names = (
                        self.getname(targets[0]) if len(targets) == 1
                        else (', '.join([self.getname(p) for p in targets[:-1]]) + (',' if len(targets) > 2 else '') + ' and ' + self.getname(targets[-1]))
                    )
                    msg.append([
                        '{} {} attacked and killed by wolves.'.format(names, 'was' if len(targets) == 1 else 'were'),
                        [p.user.send(random.choice(assets.elimination_phrases), delete_after=300) for p in targets]  # type: ignore
                    ])
                    for p in targets:
                        try:
                            self.participants.remove(p)  # type: ignore
                        except Exception:
                            pass
                    self.field.no_deaths = 0  # type: ignore
                else:
                    if (group3[1].food + group3[1].canned + group3[1].knife + 2 * group3[1].annoyed - 3 * group3[1].wounded) == (group3[0].food + group3[0].canned + group3[0].knife + 2 * group3[0].annoyed - 3 * group3[0].wounded):  # type: ignore
                        msg.append([
                            '{} and {} disappeared into the night.'.format(*[
                                self.getname(p) for p in group3
                            ]),
                            []
                        ])
                        group3[0].impression(group3[1].user, 'snuck')  # type: ignore
                        group3[1].impression(group3[0].user, 'snuck')  # type: ignore
                    else:
                        self.stats['n-kill'] += 1
                        self.total_deaths += 1
                        winner = (group3[1].food + group3[1].canned + group3[1].knife + 2 * group3[1].annoyed - 3 * group3[1].wounded) > (group3[0].food + group3[0].canned + group3[0].knife + 2 * group3[0].annoyed - 3 * group3[0].wounded)  # type: ignore
                        msg.append([
                            '{} and {} disappeared into the night.'.format(*[
                                self.getname(p) for p in group3
                            ]),
                            [group3[winner].user.send('You killed {}.'.format(self.getname(group3[1-winner])), delete_after=300)]  # type: ignore
                        ])
                        msg.append([
                            'Later that night, {} returned alone.'.format(self.getname(group3[winner])),
                            [group3[1-winner].user.send('You have been brutally murdered by {}.'.format(self.getname(group3[winner])), delete_after=300)]  # type: ignore
                        ])
                        try:
                            self.participants.remove(group3[1-winner])  # type: ignore
                        except Exception:
                            pass
                        self.field.no_deaths = 0  # type: ignore
        for p in self.participants:
            if p.food == -1:  # type: ignore
                self.stats['h-kill'] += 1
                self.total_deaths += 1
                msg.append([
                    '{} died of malnourishment.'.format(self.getname(p)),
                    [p.user.send(random.choice(assets.elimination_phrases), delete_after=300)]  # type: ignore
                ])
                try:
                    self.participants.remove(p)  # type: ignore
                except Exception:
                    pass
            elif p.clothes > 0:  # type: ignore
                p.clothes -= 1  # type: ignore
                if p.clothes == 0:  # type: ignore
                    msg.append([
                        None,
                        [p.user.send('Your winter clothes are too damaged to be usable.', delete_after=300)]  # type: ignore
                    ])
        self.field.mask = new_mask  # type: ignore
        self.field.wolf += self.total_deaths  # type: ignore
        for m in msg:
            if len(m[1]) > 0: 
                for i in m[1]: await i
            if m[0] is not None:
                await self.channel.send(m[0])
                await asyncio.sleep(3)

    def gettarget(self, tribute):
        if self.field.mask['fake'] and self.field.mask['fake'].user.id == tribute.user.id and random.randrange(2):  # type: ignore
            return self.field.mask['real']  # type: ignore
        return tribute

    def getname(self, tribute):
        if self.field.mask['real'] and self.field.mask['real'].user.id == tribute.user.id:  # type: ignore
            return self.field.mask['fake'].user.name  # type: ignore
        return tribute.user.name

    def clear(self):
        self.field = None
        self.participants = []
        self.total_deaths = 0
        self.stats = {
            'attacks': 0, # Attack encounters
            'item-m': 0, # Mask
            'item-k': 0, # Knife
            'item-f': 0, # First-aid kit
            'item-r': 0, # Rifle
            'item-e': 0, # Explosives
            'item-w': 0, # Winter clothes
            'item-c': 0, # Canned food
            'k-kill': 0, # Knife kill
            'r-kill': 0, # Rifle kill
            'f-kill': 0, # Fistfight kill
            'e-kill': 0, # Explosives kill
            'w-kill': 0, # Wolf kill
            'n-kill': 0, # Night kill
            'h-kill': 0, # Hunger kill
            's-kill': 0, # Suicide kill
            'a-kill': 0, # Ambush kill
        }

async def setup(bot):
    await bot.add_cog(Armageddon(bot))