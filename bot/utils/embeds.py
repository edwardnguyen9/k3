import discord, datetime
from random import getrandbits
from humanize import intcomma, naturaldelta
from typing import Optional

from bot.assets import api
from bot.utils import utils  # type: ignore

# Profile

def profile(bot, p, weapons: list = []):
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
    raid_bonus = 0 if p['guild'] not in api.max_raid_building else 1
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
        guild_name = f'**Guild:** {discord.utils.escape_markdown(bot.idle_guilds[guild_id][0])} ({guild_id})'
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

# Items

def items(page):
    embed = discord.Embed(
        title='Weapon crate',
        color=0xb5ffde,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    for item in page:
        hand = ''
        if item['hand'] in ['left', 'right']:
            hand = ' ({}-handed)'.format(item['hand'])
        elif item['hand'] == 'both':
            hand = ' (uses both hands)'
        stat = int(item['damage'] + item['armor'])
        stat_type = 'Armor: ' if item['armor'] > 0 else 'Damage: '
        signature = None if not item['signature'] else 'Signature: *{}*'.format(discord.utils.escape_markdown(item['signature']))
        original = None
        if item['original_type'] or item['original_name']:
            original = 'Used to be'
            if item['original_type']:
                original += ' an ' if item['original_type'].startswith(('A','E','I','O','U')) else ' a '
                original += item['original_type']
            original += ' called **{}**.'.format(item['original_name']) if item['original_name'] else '.'
        values = [
            'Type: {}{} - {}{} - ID: {} - Value: {}'.format(item['type'], hand, stat_type, stat, item['id'], item['value']),
            'Owner: <@{}>'.format(item['owner']),
            signature,
            original,
            None if 'market' not in item or not item['market'] else 'Selling price: ${}'.format(intcomma(item['market'][0]['price'])),
        ]
        embed.add_field(
            name=' '.join([i for i in [
                discord.utils.escape_markdown(item['name']),
                None if 'inventory' not in item or not item['inventory'] or not item['inventory'][0]['equipped'] else '(Equipped)'
            ] if i is not None]),
            value='\n'.join([i for i in values if i is not None]),
            inline=False
        )
    return embed

# Guild

def guild(g, members: Optional[int] = None, officers: Optional[int] = None):
    if g['alliance']['id'] != g['id']:
        al_info = 'Alliance: {name} ({id})\n Alliance leader: <@{leader}>'.format(
            name=discord.utils.escape_markdown(g['alliance']['name']), id=g['alliance']['id'], leader=g['alliance']['leader']
        )
    else:
        al_info = 'Alliance leader'
    info = ['ID: {}'.format(g['id']), 'Leader: <@{}>'.format(g['leader']), al_info]
    if g['channel']: info.append('Guild channel: <#{}>'.format(g['channel']))
    m_count = []
    if members is not None: m_count.append('Member count: {}/{}'.format(members, g['memberlimit']))
    if officers is not None: m_count.append('Officer count: {}'.format(officers))
    if len(m_count) > 0: info.insert(1, ' | '.join(m_count))
    stats = ['Bank: ${}/${}'.format(intcomma(g['money']),intcomma(g['banklimit'])), 'GvG wins: {}'.format(g['wins']), 'Times upgraded: {}'.format(g['upgrade'])]
    if members is None: stats.append('Member limit: {}'.format(g['memberlimit']))
    embed = discord.Embed(
        title=discord.utils.escape_markdown(g['name']),
        description=g['description'],
        color=0xCE71EB,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    ).add_field(
        name='Info',
        value='\n'.join(info)
    ).add_field(
        name='Stats',
        value='\n'.join(stats)
    )
    if not g['id'] in [760]: embed.set_thumbnail(url=g['icon'])
    return embed

def alliance(guilds):
    embed = discord.Embed(
        title='{}\'s alliance'.format(discord.utils.escape_markdown(guilds[0]['name'])),
        color=getrandbits(24),
        timestamp= datetime.datetime.now(datetime.timezone.utc)
    ).add_field(
        name=discord.utils.escape_markdown(guilds[0]['name']),
        value='\n'.join([
            'ID: {}'.format(guilds[0]['id']),
            'Alliance leader: <@{}>'.format(guilds[0]['leader']),
            'Bank: ${}'.format(intcomma(guilds[0]['money']))
        ])
    ).set_footer(text='Total money in bank: ${}'.format(intcomma(sum(i['money'] for i in guilds))))
    for i in guilds[1:]:
        embed.add_field(
            name=discord.utils.escape_markdown(i['name']),
            value='\n'.join([
                'ID: {}'.format(i['id']),
                'Guild leader: <@{}>'.format(i['leader']),
                'Bank: ${}'.format(intcomma(i['money']))
            ])
        )
    return embed

def pet(p):
    return discord.Embed(
        title=discord.utils.escape_markdown(p['name']),
        description=(
            'Owner: <@{}>\nFood: {}\nDrink: {}\nJoy: {}\nLove:{}'.format(
                p['user'], p['food'], p['drink'], p['joy'], p['love']
            )
        ),
        color=0xb5ffd8,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    ).set_thumbnail(
        url=p['image']
    ).set_author(
        name='Last update: {} ago.'.format(
            naturaldelta(
                datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(p['last_update'][:23] + p['last_update'][-6:])
            )
        )
    )

def children(c):
    embed = discord.Embed(
        title='Santa\'s Naughty List',
        color=0xfff94d
    )
    for child in c:
        embed.add_field(
            name=discord.utils.escape_markdown(child['name']),
            value=(
                'Gender: {} - Age: {}\n'.format(child['gender'].upper(), child['age']) +
                'Mother: <@{}>\n'.format(child['mother']) +
                'Father: <@{}>\n'.format(child['father'])
            )
        )
    return embed

def loot(page):
    embed = discord.Embed(
        title='Lootbox',
        color=0xeeb5ff,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    for loot in page:
        embed.add_field(
            name=loot['name'],
            value=(
                'ID: {} - Value: {}\n'.format(loot['id'], loot['value']) +
                'Owner: <@{}>'.format(loot['user'])
            )
        )
    return embed
