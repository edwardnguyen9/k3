import discord, random, asyncio

from assets import raid
from discord.abc import Snowflake
from utils import utils

class Fighter:
    def __init__(
        self, user, *, 
        name: str = None, thumbnail: str = None, data: dict = None,  # type: ignore
        hp: float = 250, dmg: int = None, amr: int = None, atkm: float = None, defm: float = None,  # type: ignore
        bounty: int = 0,
        building: int = 0
    ):
        self.user: discord.User = user
        self.name: str = name if name is not None else user.display_name if isinstance(user, Snowflake) else ''  # type: ignore
        self.thumbnail: str = thumbnail or (user.avatar_url if user else None)  # type: ignore
        self.color: int = random.getrandbits(24)
        self.boosted: bool = False
        self.equipped: bool = False
        self.cached: bool = data is None
        self.bounty: int = bounty

        if data is not None:
            self.classes = utils.transmute_class(data['class'])
            bonus = utils.get_class_bonus('rdr', data)
            pbonus = utils.get_class_bonus('prg', data)
            (dmg, amr) = utils.get_race_bonus(data['race'])
            dmg += (pbonus + utils.get_class_bonus('mge', data))
            amr += (pbonus + utils.get_class_bonus('wrr', data))
            self.dmg, self.amr = dmg, amr
            self.atkm, self.defm = round(data['atkmultiply'] + (bonus + building) / 10, 1), round(data['defmultiply'] + (bonus + building) / 10, 1)
            self.hp = 250 + 10 * utils.get_class_bonus('rng', data)
            self.level = utils.getlevel(data['xp'])
            self.guild = data['guild']
            self.luck = data['luck']
            self.basedmg, self.baseamr, self.ffdmg, self.ffamr = None, None, None, None
        else:
            self.classes = None
            self.dmg, self.amr = dmg, amr
            self.atkm, self.defm = atkm, defm
            self.hp = hp
            self.level = 0
            self.guild = 0
            self.luck = 1
            self.basedmg, self.baseamr, self.ffdmg, self.ffamr = None, None, None, None

    def increase(self, *, dmg = 0, amr = 0):
        if not self.equipped:
            self.equipped = True
            self.ffdmg, self.ffamr = self.dmg, self.amr
        self.dmg += dmg
        self.amr += amr

    def boost(self):
        if not self.boosted:
            self.boosted = True
            self.basedmg = self.dmg
            self.baseamr = self.amr
            self.dmg = round(self.dmg * self.atkm, 1)
            self.amr = round(self.amr * self.defm, 1)
    
    def hit(self, damage: float, ignore_armor: bool = False):
        if ignore_armor:
            taken = damage
        else:
            taken = round(damage - self.amr, 1) if damage > self.amr else 0
        self.hp -= taken
        if self.hp < 0: self.hp = 0
        return (taken, self.hp)

    async def cache(self, bot):
        if not await bot.pool.fetchval(
        'SELECT EXISTS(SELECT 1 FROM profile WHERE uid=$1);',
        self.user.id,
        ):
            await bot.pool.execute(
                'INSERT INTO profile (uid, wt, atk, def, ratk, rdef, guild, uatk, udef, classes)'
                ' VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10);',
                self.user.id,
                discord.utils.utcnow(),
                self.dmg, self.amr,
                self.atkm, self.defm,
                self.guild,
                self.ffdmg if self.ffdmg else self.dmg, self.ffamr if self.ffamr else self.amr,
                self.classes
            )
        else:
            await bot.pool.execute(
                'UPDATE profile SET wt=$2, atk=$3, def=$4, ratk=$5, rdef=$6, guild=$7, uatk=$8, udef=$9, classes=$10'
                ' WHERE uid=$1;',
                self.user.id,
                discord.utils.utcnow(),
                self.dmg, self.amr,
                self.atkm, self.defm,
                self.guild,
                self.ffdmg if self.ffdmg else self.dmg, self.ffamr if self.ffamr else self.amr,
                self.classes
            )

    @staticmethod
    async def get_cached_fighter(bot, user):
        if await bot.pool.fetchval(
            'SELECT EXISTS(SELECT 1 FROM profile WHERE uid=$1);',
            user.id
        ):
            res = await bot.pool.fetchval(
                'SELECT (atk, def, ratk, rdef, guild, uatk, udef, xp, classes[1:2]) FROM profile WHERE uid=$1', user.id
            )
            f = Fighter(user, dmg=int(res[0]), amr=int(res[1]), atkm=float(res[2]), defm=float(res[3]))
            f.guild = res[4]
            f.ffdmg = res[5]
            f.ffamr = res[6]
            f.level = utils.getlevel(res[7])
            f.classes = res[8]
            return f
        else:
            return None

class CityDefenses:
    def __init__(self, name):
        self.name = name.title()
        self.hp = raid.city_defenses[name][0]
        self.total_hp = raid.city_defenses[name][0]
        self.damage = raid.city_defenses[name][1]
        if self.name.startswith(('O', 'I')):
            self.name = 'an ' + self.name + ' Wall'
        elif self.name.startswith('A'):
            self.name = 'an ' + self.name + ' Tower'
        else:
            self.name = 'a ' + self.name

    def attacked(self, dmg: float = 0):
        self.hp -= dmg
        return self.hp if round(self.hp,1) > 0 else 0

def get_undead(no: int = 100, bounty: int = 0):
    if not no: no = 100
    undeads = []
    weights = []
    for _ in range(no):
        if random.randrange(100):
            undead = Fighter(
                user=None,
                dmg=round(random.triangular(50, 80, 60)),
                amr=random.randint(0, 20),
                hp=75 + 5 * random.randint(0, 5),
                atkm=round(random.triangular(1, 2, 1.8), 1),
                defm=round(random.triangular(1, 2, 1.8), 1),
                thumbnail=raid.full_zombie,
                name='An undead'
            )
        else:
            undead = Fighter(
                user=None,
                dmg=round(random.triangular(50, 100, 85)),
                amr=random.choices([30, 40], weights=[3, 2])[0],
                hp=200 + 10 * random.randint(0, 10),
                atkm=round(random.triangular(2, 3, 2.6), 1),
                defm=round(random.triangular(2, 3, 2.6), 1),
                thumbnail=raid.big_zombie,
                name='A giant undead'
            )
        weights.append(int(10 * (undead.dmg * undead.atkm + undead.amr * undead.defm )) + undead.hp)
        undeads.append(undead)
    if bounty:
        d = 0
        count = 0
        for i in random.choices(undeads, weights, k=bounty//10):
            count += 1
            if count == bounty//10 and count % 2 == 1:
                i.bounty += 10
            elif d == 0:
                d = random.randint(0, 10)
                i.bounty += (10 + d)
            else:
                i.bounty += (10 - d)
                d = 0
    return undeads

async def background_fetch(bot, mode, registered, uid, disqualified, guild, guildlist, *, tier = None, belthazor_prev = {}, delay_announce = False):
    # Get data from ID
    user = bot.get_user(uid)
    fighter = await bot.get_equipped(str(uid), orgs=False)
    # If user does not have a character
    if not fighter:
        disqualified.append(uid)
        await bot.log_event('tourney' if 'tourney' in mode else 'raid', message=f'{user} disqualified from the {mode} in {guild.name}')
        if not delay_announce:
            try:
                await user.send('Unable to fetch your character.')
            except discord.Forbidden:
                pass
    else:
        # If user does not belong to guild in private event
        if guildlist and fighter.guild not in guildlist:
            disqualified.append(uid)
            await bot.log_event('tourney' if 'tourney' in mode else 'raid', message=f'{user} disqualified from the {mode} in {guild.name}')
            if not delay_announce:
                try:
                    await user.send('Guests cannot join this event.', delete_after=300)
                except discord.Forbidden:
                    pass
        # If not tourney or tourney has no tier
        elif tier is None:
            # Raidstats bonus for Belthazor raid
            bonus = (
                0.3 if ('belthazor' in mode.lower() and uid == belthazor_prev['lucky'])
                else 0.1 if ('belthazor' in mode.lower() and uid in belthazor_prev['survivors']) 
                else 0
            )
            fighter.raidstats = [i + bonus for i in fighter.raidstats]
            # Get stats
            stats = fighter.fighter_data('fistfight' not in mode)
            participant = Fighter(
                user=user,
                name=fighter.name,
                dmg=stats[0],
                amr=stats[1],
                atkm=stats[2],
                defm=stats[3],)
            # if 'city' in mode.lower(): participant.hp = 250
            registered[uid] = participant
            if not delay_announce:
                try:
                    await user.send(
                        'You joined the {type} in **{server}**.\nYour stats have been recorded, and any modification will not change them now.'.format(
                            type = mode,
                            server = guild.name
                        )
                    )
                except discord.Forbidden:
                    pass
            await bot.log_event(
                'tourney' if 'tourney' in mode else 'raid',
                message='{} {} the {} in {}'.format(
                    user, 'joined' if not delay_announce else 'cached for',
                    mode, guild.name
                )
            )
            if delay_announce:
                return (
                    user,
                    'You joined the {type} in **{server}**.\nYour stats have been recorded, and any modification will not change them now.'.format(
                        type = mode,
                        server = guild.name
                    )
                )
        else:
        # elif (
        #     'tourney' not in config.config[guild.id]['misc']
        #     or (t:=discord.utils.find(lambda x: x[1] == tier, config.config[guild.id]['misc']['tourney']['tiers']))[0] is None
        #     or fighter.level <= t[0]
        # ):
            stats = fighter.fighter_data('fistfight' not in mode)
            participant = Fighter(
                user=user,
                name=fighter.name,
                dmg=stats[0],
                amr=stats[1],
                atkm=stats[2],
                defm=stats[3],)
            registered[uid] = participant
            if not delay_announce:
                try:
                    await user.send(
                        'You joined the {type} in **{server}**.\nYour stats have been recorded, and any modification will not change them now.'.format(
                            type = mode,
                            server = guild.name
                        )
                    )
                except discord.Forbidden:
                    pass
            await bot.log_event(
                'tourney' if 'tourney' in mode else 'raid',
                message='{} {} the {} in {}'.format(
                    user, 'joined' if not delay_announce else 'cached for',
                    mode, guild.name
                )
            )
            if delay_announce:
                return (
                    user,
                    'You joined the {type} in **{server}**.\nYour stats have been recorded, and any modification will not change them now.'.format(
                        type = mode,
                        server = guild.name
                    )
                )
        # else:
        #     count -= 1
        #     waitlist.remove(u_id)
        #     disqualified.append(u_id)
        #     await message.remove_reaction('\u2694', fetched_user)
        #     try:
        #         await fetched_user.send('You do not meet the level requirement.', delete_after=300)
        #     except discord.Forbidden:
        #         pass
        #     await log_event(bot, 'tourney' if 'tourney' in mode else 'raid', message=f'{fetched_user} disqualified from the {mode} in {guild.name}')
    return None

async def boss_battle(channel, fighters, boss, until, *, feature = None):
    boss.boost()
    totalatk = 0
    for fighter in fighters:
        fighter.hp = 3500 if feature is None else 4000
        fighter.boost()
        totalatk += fighter.dmg
    turn = 0
    while (
        boss.hp > 0
        and len(fighters) > 0
        and discord.utils.utcnow() < until
    ):
        await asyncio.sleep(4)
        turn += 1
        # Raiders attack
        (boss_dmg, boss_hp) = boss.hit(totalatk)
        embed = discord.Embed(title="The fighters attacked.", color=0xfffffe)
        embed.set_thumbnail(url=boss.thumbnail)
        embed.set_footer(text=f'Attack #{turn} - Fighters left: {len(fighters)}')
        if round(boss_hp,1) == 0:
            embed.description=f"{discord.utils.escape_markdown(boss.name)} is defeated."
            embed.color = 0x00FF00
            await channel.send(embed=embed)
            break
        else:
            embed.description=f"{discord.utils.escape_markdown(boss.name)} has {boss_hp:,.1f} HP left."
            embed.add_field(name='Theoretical damage', value=f'{totalatk:,.1f}')
            embed.add_field(name='Shield absorbed', value=f'{boss.amr:,.1f}')
            embed.add_field(name='Damage taken', value=f'{boss_dmg:,.1f}')
            await channel.send(embed=embed)
            # Boss attacks
            await asyncio.sleep(4)
            content = None
            fighter = random.choice(fighters)
            embed = discord.Embed(title=f"{discord.utils.escape_markdown(boss.name)} attacked.", color=fighter.color)
            embed.set_thumbnail(url=fighter.thumbnail)
            boss_attack = boss.dmg * (1.5 + 1.5 * random.random())
            hp_before = fighter.hp
            (dmg, hp) = fighter.hit(boss_attack)
            description = []
            content = []
            if round(hp,1) == 0:
                content.append(fighter.user.mention)
                fighters.remove(fighter)
                totalatk -= fighter.dmg
                description.append(f'{discord.utils.escape_markdown(fighter.name)} died.')
                embed.color = 0
            else:
                description.append(f'{discord.utils.escape_markdown(fighter.name)} has {hp:,.1f} HP left.')
            embed.add_field(name='Theoretical damage', value=f'{boss_attack:,.1f}')
            embed.add_field(name='Shield absorbed', value=f'{fighter.amr:,.1f}')
            embed.add_field(name='Damage taken', value=f'{dmg:,.1f}')
            if feature is not None:
                if 'heal' in feature:
                    healed = round(dmg * feature['heal'], 1) if round(hp, 1) > 0 else round(hp_before * feature['heal'], 1)
                    boss.hp += healed
                    description.append(f'{discord.utils.escape_markdown(boss.name)} restored {healed:,.1f} HP with his ability.')
                    embed.add_field(name='HP healed', value=f'{healed:,.1f}')
                elif 'mines' in feature and random.random() < feature['mines']:
                    target_sample = [f for f in fighters if f.user.id != fighter.user.id]
                    if len(target_sample) > 0:
                        targets = random.sample(target_sample, k=2 if len(target_sample) > 2 else len(target_sample))
                        description.append(
                            '{} also detonated a bomb, dealing damage to {}.'.format(
                                discord.utils.escape_markdown(boss.name), ' and '.join([discord.utils.escape_markdown(t.name) for t in targets])
                            )
                        )
                        for t in targets:
                            (dmg, hp) = t.hit(boss_attack)
                            if round(hp,1) == 0:
                                content.append(t.user.mention)
                                fighters.remove(t)
                                totalatk -= t.dmg
                                description.append(f'{discord.utils.escape_markdown(t.name)} died.')
                                embed.color = 0
                            else:
                                description.append(f'{discord.utils.escape_markdown(t.name)} has {hp:,.1f} HP left.')
                elif 'psn' in feature:
                    damage = round(boss_attack * feature['psn'], 1) or 0.1
                    description.append('{}\'s poison dealt damage to all surviving fighters.'.format(discord.utils.escape_markdown(boss.name)))
                    embed.add_field(name='Poison damage', value=damage)
                    for t in fighters:
                        (dmg, hp) = t.hit(damage, True)
                        if round(hp,1) == 0:
                            content.append(t.user.mention)
                            fighters.remove(t)
                            totalatk -= t.dmg
                            description.append(f'{discord.utils.escape_markdown(t.name)} died.')
                            embed.color = 0
            embed.set_footer(text=f'Attack #{turn} - Fighters left: {len(fighters)}')
            embed.description = '\n'.join(description)
            await channel.send(content=' '.join(content), embed=embed)
    return turn

async def undead_battle(
    channel: discord.TextChannel, fighters: 'list[Fighter]', undeads: 'list[Fighter]', *,
    until = None, turn: int = 0, turned: int = 0, total: int = 0, og: int = 0,
    board: dict = {}, undead_board: dict = {}, payout = {}
):
    while (
        (until is None or discord.utils.utcnow() < until)
        and len(undeads) > 0
        and len(fighters) > 0
    ):
        await asyncio.sleep(4)
        turn += 1
        # Get random fighter
        fighter = random.choice(fighters)
        # Get random undead
        undead = random.choice(undeads)
        # Check critical attack
        crit = random.randrange(5) == 0
        # Zombie does 30-60% damage
        dmg = round(undead.dmg * undead.atkm * random.uniform(0.3, 0.6), 1)
        # Armor reduced to 40-50% efficiency
        odds = len(undeads)/len(fighters)
        amr = round(fighter.amr * fighter.defm * random.choices([0.5, 0.4], weights=[1 / (turn/100 + 1), odds], k=1)[0], 1)
        # Critical hits ignore armor
        taken = dmg if crit else 0 if (dmg - amr) < 0 else (dmg - amr)
        description = 'It\'s a critical hit! ' if crit else ''
        fighter.hp = round(fighter.hp - taken, 1)
        content = None
        died = fighter.hp <= 0
        if died:
            description += '{} died.'.format(fighter.user.mention)
            if payout is None:
                val = fighter.bounty // 2
                undead.bounty += val
                fighter.bounty -= val
                if val > 0: description += '\nThis target is worth **${:,d}** more'.format(val)
            elif fighter.user.id in payout:
                val = payout[fighter.user.id] // 2
                undead.bounty += val
                payout[fighter.user.id] -= val
                if val > 0: description += '\nThis target is worth **${:,d}** more'.format(val)
            content = fighter.user.mention
            if undead.user:
                content += f' {undead.user.mention}'
                if undead.user.id in undead_board:
                    undead_board[undead.user.id] += 1
                else:
                    undead_board[undead.user.id] = 1
            # Pop fighter and add to undead list
            fighters.remove(fighter)
            undeads.append(fighter)
            # Fighter as a damaged undead
            fighter.hp = random.choices([150, 175, 200], weights=[6, 3, 1], k=1)[0] + 10 * utils.get_class_bonus('rng', fighter.classes or [])
            turned += 1
        else:
            description += '{} has {} HP left.'.format(fighter.user.mention, fighter.hp)
        title = (
            'A giant undead' if undead.thumbnail == raid.big_zombie else
            (('Undead ' + discord.utils.escape_markdown(undead.name)) if undead.user else 'An undead') if not undead.thumbnail == raid.half_a_zombie else
            ('Half the body of ' + discord.utils.escape_markdown(undead.name)) if undead.user else 'Half an undead'
        )
        footer = ['Round {}'.format(turn), 'Fighters: {}'.format(len(fighters))]
        if until is not None: footer.append('Undeads: {}'.format(len(undeads)))
        else: footer.append('Undeads killed: {}'.format(total))
        embed = discord.Embed(
            title = '{} attacked {}'.format(
                title,
                discord.utils.escape_markdown(fighter.name)
            ),
            description = description,
            color = 0 if died else fighter.color
        ).set_thumbnail(
            url= fighter.thumbnail
        ).add_field(
            name='Theoretical damage', value = round(dmg, 1)
        ).add_field(
            name='Shield absorbed', value = 0 if crit else round(amr, 1)
        ).add_field(
            name='Damage taken', value = round(taken, 1)
        ).set_footer(text=' | '.join(footer))
        await channel.send(content=content, embed=embed)
        if died: continue
        await asyncio.sleep(4)
        # Check critical attack
        crit = random.randrange(5) == 0
        # Fighter damage
        dmg = fighter.dmg * fighter.atkm
        # Armor reduced to 20-30% efficiency
        amr = round(undead.amr * undead.defm * random.choices([0.2, 0.3], weights=[1/(1 + turn/100), odds], k=1)[0], 1)
        # Critical hits ignore armor
        taken = dmg if crit else 0 if (dmg - amr) < 0 else (dmg - amr)
        description = 'It\'s a critical hit! ' if crit else ''
        undead.hp = -50 if crit else round(undead.hp - taken, 1)
        
        embed = discord.Embed(
            title = '{} retaliated'.format(
                discord.utils.escape_markdown(fighter.name)
            ),
            description = description,
            color = 0x696969
        ).set_thumbnail(
            url= undead.thumbnail
        ).add_field(
            name='Theoretical damage', value = round(dmg, 1)
        ).add_field(
            name='Shield absorbed', value = 0 if crit else round(amr, 1)
        ).add_field(
            name='Damage taken', value = round(taken, 1)
        )
        if undead.hp <= 0:
            undead.hp += random.randrange(50)
            # Revive undead
            if undead.hp >= 0:
                if undead.thumbnail == raid.big_zombie:
                    undead.hp += random.randrange(50) + 1
                    embed.description += 'The undead is too big to be cut in half.'  # type: ignore
                else:
                    undead.hp += 1
                    undead.dmg /= 2
                    undead.amr = 0
                    undead.thumbnail = raid.half_a_zombie
                    embed.description += 'The {} is cut in half, but is still moving.'.format('undead' if not undead.user else 'corpse of ' + undead.name)  # type: ignore
            else:
                embed.description += 'The {} is decapitated. It stopped moving.'.format('undead' if not undead.user else 'corpse of ' + undead.name)  # type: ignore
                if payout is None:
                    fighter.bounty += undead.bounty
                    if undead.bounty > 0: embed.description += '\n{} will collect **${:,d}** if they survive.'.format(fighter.user.mention, undead.bounty)
                elif fighter.user.id in payout:
                    payout[fighter.user.id] += undead.bounty
                else:
                    payout[fighter.user.id] = undead.bounty
                if payout and undead.bounty > 0: embed.description += '\n{} collected **${:,d}**.'.format(fighter.name, undead.bounty)
                embed.color = 0x00ff00
                undeads.remove(undead)
                total += 1
                if not undead.user: og += 1
                if fighter.user.id in board:
                    board[fighter.user.id] += 1
                else:
                    board[fighter.user.id] = 1
        else:
            embed.description += 'The {} has {} HP left.'.format('undead' if not undead.user else 'corpse of ' + undead.name, undead.hp)  # type: ignore
        for z in undeads: z.hp += round(random.triangular(1, 3, 1), 1)
        footer = ['Round {}'.format(turn), 'Fighters: {}'.format(len(fighters))]
        if until is not None: footer.append('Undeads: {}'.format(len(undeads)))
        else: footer.append('Undeads killed: {:,d}'.format(total))
        embed.set_footer(text=' | '.join(footer))
        await channel.send(embed=embed)
    return (fighters, undeads, turn, turned, total, og, board, undead_board, payout)

async def city_battle(channel, fighters, defenses, until, delay = 5):
    atk = 0
    dealt = 0
    turn = 0
    destroyed = []
    for fighter in fighters:
        fighter.boost()
        fighter.hp = 250
        atk += fighter.dmg
    fighters.sort(key = lambda x: x.amr)
    fighters.sort(key = lambda x: x.dmg, reverse = True)
    while (
        len(defenses) > 1
        and len(fighters) > 0
        and discord.utils.utcnow() < until
    ):
        await asyncio.sleep(delay)
        turn += 1
        # Raiders attack
        defenses_hp = defenses[1].attacked(atk)
        embed = discord.Embed(title="The fighters attacked.", color=random.getrandbits(24)) if delay else None
        if round(defenses_hp,1) == 0:
            defense = defenses.pop(1)
            dealt += defense.total_hp
            defenses[0][1] -= defense.damage
            destroyed.append(' '.join(defense.name.split()[1:] + ['-', '**Destroyed**']))
            if embed: embed.description=f"The fighters destroyed {defense.name}."
        elif embed:
            embed.description = 'The {} has {:,.1f} HP left.'.format(
                ' '.join(defenses[1].name.split()[1:]), defenses_hp
            )
            embed.add_field(name='Damage dealt', value='{:,.1f}'.format(atk))
        if embed: embed.set_footer(text=f'Attack #{turn} | Fighters: {len(fighters)} | Defenses: {len(defenses[1:])}')
        if embed: await channel.send(embed=embed)
        # City attacks
        if len(defenses) > 1:
            await asyncio.sleep(delay)
            fighter = fighters[0]
            embed = discord.Embed(title=f"{defenses[0][0]}'s defenses attacked.", color=0xfffffe).set_thumbnail(url=fighter.thumbnail) if delay else None
            (dmg, hp) = fighter.hit(defenses[0][1])
            if round(hp,1) == 0:
                atk -= fighter.dmg
                if embed:
                    embed.description =f'{fighter.user} died.'
                    embed.color = 0
                fighters.remove(fighter)
            elif embed:
                embed.description=f'{fighter.user} has {hp:,.1f} left.'
            if embed:
                embed.add_field(name='Damage dealt', value='{:,.1f}'.format(defenses[0][1]))
                embed.add_field(name='Shield absorbed', value='{:,.1f}'.format(fighter.amr))
                embed.add_field(name='Damage taken', value='{:,.1f}'.format(dmg))
                embed.set_footer(text=f'Fighters: {len(fighters)} | Defenses: {len(defenses[1:])}')
                await channel.send(embed=embed)
    return (turn, destroyed, dealt)
