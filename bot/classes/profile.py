import datetime, discord

from humanize import intcomma

from bot.assets import api, postgres  # type: ignore
from bot.utils import utils  # type: ignore

MAX_RAID_BUILDING = [2807, 8244, 13992, 6055, 17555, 3960, 20314, 15356, 19599, 20120, 20809, 25859]

class Profile:
    def __init__(self, *, data = {}, user = None, race = 'Human', classes = [], guild = -1, raidstats = [1,1], xp = 0, completed = 0, deaths = 0, weapons = []):
        self.user = data['user'] if 'user' in data else user
        self.race = data['race'] if 'race' in data else race
        self.classes = [api.classes[i] for i in data['class'] if i in api.classes] if 'class' in data else classes
        self.guild = data['guild'] if 'guild' in data else guild
        self.raidstats = [data['atkmultiply'], data['defmultiply']] if 'atkmultiply' in data and 'defmultiply' in data else raidstats
        self.xp = data['xp'] if 'xp' in data else xp
        self.completed = data['completed'] if 'completed' in data else completed
        self.deaths = data['deaths'] if 'deaths' in data else deaths
        self.luck = data['luck'] if 'luck' in data else 1
        self.weapons = weapons

    def fighter_data(self):
        dmg, amr = utils.get_race_bonus(self.race)
        dmg += utils.get_class_bonus('dmg', self.classes)
        amr += utils.get_class_bonus('amr', self.classes)
        if len(self.weapons) > 0:
            if isinstance(self.weapons[0], list):
                dmg += sum([int(i[2]) for i in self.weapons if i[1] != 'Shield']) + utils.get_weapon_bonus(self.weapons, self.classes)
                amr += sum([int(i[2]) for i in self.weapons if i[1] == 'Shield'])
            else:
                dmg += int(sum([i['damage'] for i in self.weapons])) + utils.get_weapon_bonus(self.weapons, self.classes)
                amr += int(sum([i['armor'] for i in self.weapons]))
        rd = round(self.raidstats[0] + utils.get_class_bonus('rdr', self.classes) / 10 + (1 if self.guild in MAX_RAID_BUILDING else 0), 1)
        ra = round(self.raidstats[1] + utils.get_class_bonus('rdr', self.classes) / 10 + (1 if self.guild in MAX_RAID_BUILDING else 0), 1)
        return (dmg, amr, rd, ra)

    async def update_profile(self, bot):
        now = datetime.datetime.now(datetime.timezone.utc)
        if not await bot.pool.fetchval(
            postgres.queries['existed'],
            self.user,
        ):
            await bot.pool.execute(
                postgres.queries['profile_new'],
                self.user,
                self.race,
                self.classes,
                self.guild,
                self.raidstats,
                now
            )
        else:
            await bot.pool.execute(
                postgres.queries['profile_update'],
                self.user,
                self.race,
                self.classes,
                self.guild,
                self.raidstats,
                now
            )

    @staticmethod
    async def update_adventures(bot, data):
        if not await bot.pool.fetchval(
            postgres.queries['existed'],
            data[0],
        ):
            await bot.pool.execute(
                postgres.queries['adv_new'],
                *data,
            )
        else:
            await bot.pool.execute(
                postgres.queries['adv_update'],
                *data,
            )

    @staticmethod
    async def update_weapons(bot, user, data):
        now = datetime.datetime.now(datetime.timezone.utc)
        if not await bot.pool.fetchval(
            postgres.queries['existed'],
            user[0],
        ):
            await bot.pool.execute(
                postgres.queries['weapon_new'],
                *user,
                data,
                now
            )
        else:
            await bot.pool.execute(
                postgres.queries['weapon_updated'],
                *user,
                data,
                now
            )
    
    @staticmethod
    async def get_stats(bot, user):
        old_equipped = await bot.pool.fetchval(postgres.queries['fetch_weapons'], user.id) or []

    @staticmethod
    def profile_embed(bot, p, weapons: list = []):
        embed = discord.Embed(
            title=discord.utils.escape_markdown(p['name']),
            color=utils.embedcolor(p['colour']),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        if not p['background'] == '0':
            embed.set_thumbnail(url=p['background'])
        
        # General field
        ranger = utils.get_class_bonus('rng', p)
        warrior = utils.get_class_bonus('wrr', p)
        mage = utils.get_class_bonus('mge', p)
        paragon = utils.get_class_bonus('prg', p)
        thief = utils.get_class_bonus('thf', p)
        ritualist = utils.get_class_bonus('rtl', p)
        raider = utils.get_class_bonus('rdr', p)
        
        boosted = []
        if (paragon + mage + warrior):
            boosted.append([])
            if paragon + mage:
                boosted[0].append('+{0} ATK'.format(paragon + mage))
            if paragon + warrior:
                boosted[0].append('+{0} DEF'.format(paragon + warrior))
            boosted[0] = ' and '.join(boosted[0])
        if raider:
            boosted.append(f'Raidstats +{round(raider/10, 1)}x')
        if thief:
            boosted.append(f'Steal chance: {thief * 8}%')
        if ritualist:
            boosted.append(f'Sacrifice boost: {ritualist * 5}%')
        if ranger:
            boosted.append(f'Pet Lv.{ranger}')
        if len(boosted) == 0: boosted.append('None')

        field_general = [
            '**User:** <@{}>'.format(p['user']),
            '**Race:** {}'.format(p['race']),
            '*{} {}*'.format(api.race_options[p['race']][-1], api.race_options[p['race']][p['cv']]) if p['cv'] > -1 else None,
            '**Classes:** {}'.format(' - '.join(p['class'])),
            '\n'.join(boosted) if len(boosted) > 0 else None,
        ]
        embed.description = '\n'.join([i for i in field_general if i is not None])

        # Stats field
        rate = 0 if (p['deaths'] + p['completed']) == 0 else round(100.0 * p['deaths'] / (p['deaths'] + p['completed']), 2)
        field_lvl = utils.getlevel(p['xp'])
        field_xptonext = utils.getnextevol(p['xp'])
        field_stats = []
        if len(weapons):
            (dmg, amr) = utils.get_race_bonus(p['race'])
            dmg += sum([int(i[2]) for i in weapons if i[1] != 'Shield']) + utils.get_weapon_bonus(weapons, [api.classes[i] for i in p['class'] if i in api.classes]) + paragon + mage
            amr += sum([int(i[2]) for i in weapons if i[1] == 'Shield']) + paragon + warrior
            field_stats.append('**ATK:** {} - **DEF:** {}'.format(dmg, amr))
        raid_bonus = 0 if p['guild'] not in MAX_RAID_BUILDING else 1
        field_stats.append('**ATK/DEF multiplier:** {}/{}'.format(round(p['atkmultiply'] + raider + raid_bonus, 1), round(p['defmultiply'] + raider + raid_bonus, 1)))
        field_stats.append('**Death rate:** {}/{} ({}%)'.format(intcomma(p['deaths']), intcomma(p['deaths'] + p['completed']), rate))
        field_stats.append('**PvP wins:** {}'.format(intcomma(p['pvpwins'])))
        field_stats.append('**XP:** {0} (Lvl. {1})'.format(intcomma(p['xp']), field_lvl))
        if field_xptonext is not None: field_stats.append('**To {}:** {} XP'.format('next evolution' if field_lvl > 11 else 'second class', intcomma(field_xptonext)))

        # Inventory field
        field_inventory = []
        field_inventory.append('**Money:** ${}'.format(intcomma(p['money'])))
        field_crate = []
        if p['crates_common']: field_crate.append('{1} {0}'.format(str(bot.crates['c']), intcomma(p['crates_common'])))
        if p['crates_uncommon']: field_crate.append('{1} {0}'.format(str(bot.crates['u']), intcomma(p['crates_uncommon'])))
        if p['crates_rare']: field_crate.append('{1} {0}'.format(str(bot.crates['r']), intcomma(p['crates_rare'])))
        if p['crates_magic']: field_crate.append('{1} {0}'.format(str(bot.crates['m']), intcomma(p['crates_magic'])))
        if p['crates_legendary']: field_crate.append('{1} {0}'.format(str(bot.crates['l']), intcomma(p['crates_legendary'])))
        if p['crates_mystery']: field_crate.append('{1} {0}'.format(str(bot.crates['my']), intcomma(p['crates_mystery'])))
        if len(field_crate) > 0: field_inventory.append('**Crates:** {}'.format(', '.join(field_crate)))
        field_booster = []
        if p['time_booster']: field_booster.append('{} T'.format(p['time_booster']))
        if p['money_booster']: field_booster.append('{} M'.format(p['money_booster']))
        if p['luck_booster']: field_booster.append('{} L'.format(p['luck_booster']))
        if len(field_booster) > 0: field_inventory.append('**Boosters:** {}'.format(', '.join(field_booster)))
        if p['backgrounds'] and len(p['backgrounds']) > 0: field_inventory.append('**Event backgrounds:** {}'.format(len(p['backgrounds'])))
        field_inventory.append('**Reset points:** {}'.format(str(p['reset_points'])))

        field_community = []
        # Guild
        guild_name = ''
        guild_leader = ''
        guild_id = str(p["guild"])
        if guild_id in bot.idle_guilds:
            guild_name = f'**Guild:** {bot.idle_guilds[guild_id][0]} ({guild_id})'
            if p['guildrank'] != 'Leader':
                guild_leader = '\n**Guild leader:** <@{}>'.format(bot.idle_guilds[guild_id][1])
        else:
            guild_name = f'**Guild:** {guild_id}'
        if p['guild']:
            field_community.append(guild_name + f'\n**Rank:** {p["guildrank"]}' + guild_leader) 
        else: field_community.append('**Guild:** None')
        # Marriage
        if p['marriage']:
            field_community.append(
                '**Spouse:** <@{uid}>\n(Lovescore: {ls} - {bonus}% bonus gold)'.format(
                    uid=str(p["marriage"]),
                    ls=intcomma(p['lovescore']),
                    bonus=intcomma(50 * (1 + p['lovescore']/1_000_000), 2)
                )
            )
        # God
        field_god = '**God:** {}'.format(
            p['god'] if p['god'] is not None else 
            'Heathen' if p['reset_points'] == -1 else 
            'Nonbeliever'
        )
        if p['god'] in api.gods: field_god += ' (<@{}>)'.format(api.gods[p['god']])
        if p['god'] or int(100 * p['luck']) != 100: field_god += '\n**Luck:** {}'.format(intcomma(p['luck'], 2))
        if p['favor']: field_god += ' - **Favor:** {}'.format(intcomma(p['favor']))
        field_community.append(field_god)

        # Event field
        field_event = []
        if p['chocolates']: field_event.append('**Chocolate boxes:** {}'.format(intcomma(p['chocolates'])))
        if p['eastereggs']: field_event.append('**Easter eggs:** {}'.format(intcomma(p['eastereggs'])))
        if p['trickortreat']: field_event.append('**Trick-or-treat bags:** {}'.format(intcomma(p['trickortreat'])))
        if p['puzzles']: field_event.append('**Christmas puzzles:** {}'.format(intcomma(p['puzzles'])))
        
        embed.add_field(name='__**STATS**__', value='\n'.join(field_stats))
        embed.add_field(name='__**INVENTORY**__', value='\n'.join(field_inventory))
        if field_event:
            embed.add_field(name='\u200b', value='\u200b')
            embed.add_field(name='__**COMMUNITY**__', value='\n'.join(field_community))
            embed.add_field(name='__**EVENT**__', value='\n'.join(field_event))
        else:
            embed.add_field(name='__**COMMUNITY**__', value='\n'.join(field_community), inline=False)

        if len(p['badges']) > 1:
            blist = []
            badges = p['badges'][::-1]
            for i in range(0, len(api.badges)):
                if i > len(badges): break
                elif badges[i] == '1': blist.append(api.badges[i])
            embed.set_footer(text='Badge{}: {}'.format('s' if len(blist) > 1 else '', ', '.join(blist)))
        # elif cache:
        #     embed.set_footer(
        #         text='Weapons last updated: {}'.format(
        #             naturaltime(cache[2], when=datetime.datetime.now(datetime.timezone.utc))
        #         )
        #     )
        return embed
