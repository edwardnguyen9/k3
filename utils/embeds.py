import discord, datetime
from random import getrandbits

from assets import idle, raid
from utils import utils

# Profile

def profile(bot, p, weapons: list = []):
    embed = discord.Embed(
        title=discord.utils.escape_markdown(p['name']),
        color=utils.embedcolor(p['colour']),
        timestamp=discord.utils.utcnow()
    )
    if not p['background'] == '0':
        embed.set_thumbnail(url=p['background'])
    
    # General field
    p_dmg = utils.get_class_bonus('dmg', p)
    p_amr = utils.get_class_bonus('amr', p)
    ranger = utils.get_class_bonus('rng', p)
    thief = utils.get_class_bonus('thf', p)
    ritualist = utils.get_class_bonus('rtl', p)
    raider = utils.get_class_bonus('rdr', p) / 10
    
    boosted = []
    if p_dmg + p_amr:
        boosted.append([])
        if p_dmg:
            boosted[0].append('+{0} ATK'.format(p_dmg))
        if p_amr:
            boosted[0].append('+{0} DEF'.format(p_amr))
        boosted[0] = ' and '.join(boosted[0])
    if raider:
        boosted.append(f'Raidstats +{raider:.1f}x')
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
        '*{} {}*'.format(idle.race_options[p['race']][-1], idle.race_options[p['race']][p['cv']]) if p['cv'] > -1 else None,
        '**Classes:** {}'.format(' - '.join(p['class'])),
        '\n'.join(boosted) if len(boosted) > 0 else None,
    ]
    embed.description = '\n'.join([i for i in field_general if i is not None])

    # Stats field
    rate = 0 if (p['deaths'] + p['completed']) == 0 else 100.0 * p['deaths'] / (p['deaths'] + p['completed'])
    field_lvl = utils.getlevel(p['xp'])
    field_xptonext = utils.getnextevol(p['xp'])
    field_stats = []
    if len(weapons):
        (dmg, amr) = utils.get_race_bonus(p['race'])
        dmg += sum([int(i[2]) for i in weapons if i[1] != 'Shield']) + p_dmg + utils.get_weapon_bonus(weapons, [idle.classes[i] for i in p['class'] if i in idle.classes])
        amr += sum([int(i[2]) for i in weapons if i[1] == 'Shield']) + p_amr
        field_stats.append('**ATK:** {} - **DEF:** {}'.format(dmg, amr))
    raid_bonus = 0 if p['guild'] not in idle.max_raid_building else 1
    field_stats.append('**ATK/DEF multiplier:** {:.1f}/{:.1f}'.format(p['atkmultiply'] + raider + raid_bonus, p['defmultiply'] + raider + raid_bonus))
    field_stats.append('**Death rate:** {:,d}/{:,d} ({:.2f}%)'.format(p['deaths'], p['deaths'] + p['completed'], rate))
    field_stats.append('**PvP wins:** {:,d}'.format(p['pvpwins']))
    field_stats.append('**XP:** {0:,d} (Lvl. {1})'.format(p['xp'], field_lvl))
    if field_xptonext is not None: field_stats.append('**To {}:** {:,d} XP'.format('next evolution' if field_lvl > 11 else 'second class', field_xptonext))

    # Inventory field
    field_inventory = []
    field_inventory.append('**Money:** ${:,d}'.format(p['money']))
    field_crate = []
    if p['crates_common']: field_crate.append('{1:,d} {0}'.format(str(bot.crates['c']), p['crates_common']))
    if p['crates_uncommon']: field_crate.append('{1:,d} {0}'.format(str(bot.crates['u']), p['crates_uncommon']))
    if p['crates_rare']: field_crate.append('{1:,d} {0}'.format(str(bot.crates['r']), p['crates_rare']))
    if p['crates_magic']: field_crate.append('{1:,d} {0}'.format(str(bot.crates['m']), p['crates_magic']))
    if p['crates_legendary']: field_crate.append('{1:,d} {0}'.format(str(bot.crates['l']), p['crates_legendary']))
    if p['crates_mystery']: field_crate.append('{1:,d} {0}'.format(str(bot.crates['my']), p['crates_mystery']))
    if len(field_crate) > 0: field_inventory.append('**Crates:** {}'.format(', '.join(field_crate)))
    field_booster = []
    if p['time_booster']: field_booster.append('{:,d} T'.format(p['time_booster']))
    if p['money_booster']: field_booster.append('{:,d} M'.format(p['money_booster']))
    if p['luck_booster']: field_booster.append('{:,d} L'.format(p['luck_booster']))
    if len(field_booster) > 0: field_inventory.append('**Boosters:** {}'.format(', '.join(field_booster)))
    if p['backgrounds'] and len(p['backgrounds']) > 0: field_inventory.append('**Event backgrounds:** {:,d}'.format(len(p['backgrounds'])))
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
            '**Spouse:** <@{uid}>\n(Lovescore: {ls:,d} - {bonus:,.2f}% bonus gold)'.format(
                uid=p["marriage"],
                ls=p['lovescore'],
                bonus=50 * (1 + p['lovescore']/1_000_000)
            )
        )
    # God
    field_god = '**God:** {}'.format(
        p['god'] if p['god'] is not None else 
        'Heathen' if p['reset_points'] == -1 else 
        'Nonbeliever'
    )
    if p['god'] in idle.gods: field_god += ' (<@{}>)'.format(idle.gods[p['god']])
    if p['god'] or int(100 * p['luck']) != 100: field_god += '\n**Luck:** {:.2f}'.format(p['luck'])
    if p['favor']: field_god += ' - **Favor:** {:,d}'.format(p['favor'])
    field_community.append(field_god)

    # Event field
    field_event = []
    if p['chocolates']: field_event.append('**Chocolate boxes:** {:,d}'.format(p['chocolates']))
    if p['eastereggs']: field_event.append('**Easter eggs:** {:,d}'.format(p['eastereggs']))
    if p['trickortreat']: field_event.append('**Trick-or-treat bags:** {:,d}'.format(p['trickortreat']))
    if p['puzzles']: field_event.append('**Christmas puzzles:** {:,d}'.format(p['puzzles']))
    
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
        for i in range(0, len(idle.badges)):
            if i > len(badges): break
            elif badges[i] == '1': blist.append(idle.badges[i])
        embed.set_footer(text='Badge{}: {}'.format('s' if len(blist) > 1 else '', ', '.join(blist)))
    # elif cache:
    #     embed.set_footer(
    #         text='Weapons last updated: {}'.format(
    #             naturaltime(cache[2], when=discord.utils.utcnow())
    #         )
    #     )
    return embed

# Items

def items(page):
    embed = discord.Embed(
        title='Weapon crate',
        color=0xb5ffde,
        timestamp=discord.utils.utcnow()
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
            None if 'market' not in item or not item['market'] else 'Selling price: ${:,d}'.format(item['market'][0]['price']),
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

def market(page, status = None):
    title = (
        'Item removed' if status == 'removed'
        else 'Price changed' if status == 'changed'
        else 'Item traded' if status == 'moved'
        else 'Item sold' if status == 'sold'
        else 'Item deleted' if status == 'deleted'
        else 'Item added' if status == 'added'
        else 'Marketplace'
    )
    color = 0xff0000 if status in ['removed', 'moved', 'sold'] else 0xf59025 if status == 'changed' else 0xffff00
    embed = discord.Embed(
        title=title,
        color=color,
        timestamp=discord.utils.utcnow()
    )
    for item in page:
        embed.add_field(
            name=item['name'],
            value='\n'.join([i for i in [
                '{stat} {type} - ID: {id} - Value: ${value:,d}'.format(
                    stat=item['stat'], type=item['type'], id=item['id'], value=item['value']
                ),
                'Price: {old}${price:,d}'.format(
                    price=item['price'],
                    old='' if 'old_price' not in item else '~~${:,d}~~ '.format(item['old_price'])
                ),
                'Previous owner: <@{owner}>'.format(owner=item['owner']) if 'current_owner' in item else None,
                'Owner: <@{owner}>'.format(owner=item['current_owner'] if 'current_owner' in item else item['owner']),
                'Signature: {sign}'.format(item['signature']) if item['signature'] else None,
                'Published: <t:{time}:R>'.format(time=item['published']),
                'Last updated: <t:{time}:R>'.format(time=item['last_updated']) if 'last_updated' in item and item['last_updated'] != item['published'] else None,
                'Sold: <t:{time}:R>'.format(time=item['sold']) if 'sold' in item else None,
                '*Item removed.*' if status == 'removed' else '*Item removed.*' if status == 'deleted' else None
            ] if i is not None]),
            inline=False
        )
    return embed

# Guild

def guild(g, members: int = 0, officers: list = [], money_data: list = [], crates: list = []):
    if isinstance(g['alliance'], int) and g['alliance'] != g['id']:
        al_info = 'Alliance: {}'.format(g['alliance'])
    elif isinstance(g['alliance'], dict) and g['alliance']['id'] != g['id']:
        al_info = 'Alliance: {name} ({id})\n Alliance leader: <@{leader}>'.format(
            name=discord.utils.escape_markdown(g['alliance']['name']), id=g['alliance']['id'], leader=g['alliance']['leader']
        )
    else:
        al_info = 'Alliance leader'
    info = ['ID: {}'.format(g['id']), 'Leader: <@{}>'.format(g['leader']), al_info]
    if g['channel']: info.append('Guild channel: <#{}>'.format(g['channel']))
    m_count = []
    if members > 0: m_count.append('Member count: {}/{}'.format(members, g['memberlimit']))
    if len(m_count) > 0: info.insert(1, ' | '.join(m_count))
    stats = [
        'Bank: ${:,d}/${:,d}'.format(g['money'],g['banklimit']),
        None if len(money_data) == 0 else 'In member account: ${:,d}'.format(money_data[0]),
        'GvG wins: {:,d}'.format(g['wins']),
        'Times upgraded: {}'.format(g['upgrade'])
    ]
    if members == 0: stats.append('Member limit: {}'.format(g['memberlimit']))
    embed = discord.Embed(
        title=discord.utils.escape_markdown(g['name']),
        description=g['description'],
        color=0xCE71EB,
        timestamp=discord.utils.utcnow()
    ).add_field(
        name='Info',
        value='\n'.join(info)
    ).add_field(
        name='Stats',
        value='\n'.join([i for i in stats if i is not None])
    )
    if len(officers) > 0:
        embed.add_field(
            name='Officer',
            value='\n'.join(map(lambda x: f'<@{x}>', officers)),
            inline=False
        )
    if len(money_data) > 0:
        embed.add_field(
            name='Crates',
            value=' | '.join(map(lambda x: f'{money_data[x]:,d} {crates[0][crates[x]]}', range(1,len(money_data)))),
            inline=len(officers) > 0
        )
    if not g['id'] in [760]: embed.set_thumbnail(url=g['icon'])
    return embed

def alliance(guilds):
    embed = discord.Embed(
        title='{}\'s alliance'.format(discord.utils.escape_markdown(guilds[0]['name'])),
        color=getrandbits(24),
        timestamp= discord.utils.utcnow()
    ).add_field(
        name=discord.utils.escape_markdown(guilds[0]['name']),
        value='\n'.join([
            'ID: {}'.format(guilds[0]['id']),
            'Alliance leader: <@{}>'.format(guilds[0]['leader']),
            'Bank: ${:,d}'.format(guilds[0]['money'])
        ])
    ).set_footer(text='Total money in bank: ${:,d}'.format(sum(i['money'] for i in guilds)))
    for i in guilds[1:]:
        embed.add_field(
            name=discord.utils.escape_markdown(i['name']),
            value='\n'.join([
                'ID: {}'.format(i['id']),
                'Guild leader: <@{}>'.format(i['leader']),
                'Bank: ${:,d}'.format(i['money'])
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
        timestamp=discord.utils.utcnow()
    ).set_thumbnail(
        url=p['image']
    ).add_field(
        name='Last updated', value='<t:{:.0f}:R>'.format(
            datetime.datetime.fromisoformat(p['last_update'][:23] + p['last_update'][-6:]).timestamp()
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
        timestamp=discord.utils.utcnow()
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

def report(report: dict):
    embed = None
    if 'raid' in report['mode'].lower():
        fields = [
            ('Boss HP', '{:,.1f}/{:,.1f}'.format(*report['boss'][1:2]), True) if 'boss' in report else None,
            ('{}\'s HP'.format(report['impostor'][0]['name']), '{:,.1f}/{:,.1f}'.format(*report['impostor'][1:2]), True) if 'impostor' in report else None,
            ('City statistics', '\n'.join([
                'Name: {}'.format(report['city'][0]),
                'Ruler: {}'.format(report['city'][2]),
                'Total defenses: {:,d}'.format(report['city'][1]),
            ]), True) if 'city' in report else None,
            (
                'Raiders remaining', '{:,d}/{:,d}'.format(
                    len([i for i in report['fighters'] if i[1] > 0]),
                    len(report['fighters'])
                ),
                True
            ),
            ('Undead statistics', '\n'.join([
                'Summoned: {}'.format(report['undeads'][0] if report['undeads'][0] else 'Infinite'),
                'Undead raiders killed: {}/{}'.format(report['undeads'][3]-report['undeads'][1], report['undeads'][2]),
                'Total killed: {}'.format(report['undeads'][3])
            ]), True) if 'undeads' in report else None,
            ('Increased possessed chance', '<@{}>'.format(report['blessed']), True) if 'blessed' in report and report['blessed'] else None,
            ('Time elapsed', utils.get_timedelta(report['timestamps'][1] - report['timestamps'][0]), True),
            ('Defenses', '\n'.join(report['damage']), False) if 'damage' in report else None
        ]
        print(
            len([i for i in report['fighters'] if i[1] > 0]),
            len([i for i in report['fighters'] if i[1] == 0]),
            len([i for i in report['fighters'] if i[1] < 0])
        )
        embed = discord.Embed(
            title='{} results'.format(report['mode']),
            description='\n'.join(map(lambda x: '<@{}> - {:,.1f} HP'.format(*x), report['fighters'])),
            color=0x00ff00 if (report['timestamps'][1] - report['timestamps'][0]) < raid.raid_cfg['time'] and len([i for i in report['fighters'] if i[1] > 0]) > 0 else 0xff0000,
            timestamp=datetime.datetime.fromtimestamp(report['timestamps'][1], tz=datetime.timezone.utc)
        ).set_footer(text='{} rounds'.format(report['rounds']))
        for i in fields:
            if i is not None:
                embed.add_field(name=i[0], value=i[1], inline=i[2])
    elif 'arena' in report['mode'].lower():
        hps = [[l[-1][l[0].index(report['challenger'][0])], l[-1][l[0].index(report['defender'][0])]] for l in report['logs']]
        embed = discord.Embed(
            title='Arena challenge: {}'.format(report['title'][0]),
            color=report['title'][2],
            timestamp=datetime.datetime.fromtimestamp(report['timestamps'][1], tz=datetime.timezone.utc),
            description='\n'.join([
                'Title: <@&{}>'.format(report['title'][1]),
                'Challenger: <@{}>'.format(report['challenger'][0]),
                'Defender: <@{}>'.format(report['defender'][0]),
                'Battle duration: *{}*'.format(utils.get_timedelta(report['timestamps'][1]-report['timestamps'][0]))
            ])
        ).add_field(
            name='Results', inline=False,
            value='\n'.join([i for i in [
                '```',
                '{:^10} {} - {} {:^10}'.format('Challenger', len([i for i in hps if i[1] == 0]), len([i for i in hps if i[0] == 0]), 'Defender'),
                # '\n'.join(['{:^12} - {:^12}'.format('{:.1f} HP'.format(i[0]), '{:.1f} HP'.format(i[1])) for i in hps]),
                '\n'.join(map(lambda i: '  {:<10} - {:>10}'.format('{:.1f} HP'.format(i[0]), '{:.1f} HP'.format(i[1])), hps)),
                '```',
                (
                    None if 'results' not in report
                    else '<@{}> triggered a 6 hour protection period'.format(report['challenger'][0]) if report['results'] == 'protected'
                    else '<@{}> lost the title'.format(report['defender'][0]) if report['results'] == 'lost'
                    else '<@{}> took the title from <@{}>'.format(report['challenger'][0], report['defender'][0]) if report['results'] == 'stole'
                    else '<@{}> lost the title'.format(report['defender'][0]) if report['results'] == 'lost'
                    else '\n'.join([
                        '<@{}> now has **{}**'.format(report['defender'][0], report['results'][0]),
                        '<@{}> now has **{}**'.format(report['challenger'][0], report['title'][0]),
                    ])
                )
            ] if i is not None])
        ).add_field(
            name='Go to battles', inline=False,
            value=' | '.join(map(
                lambda x: '[Battle #{}]({})'.format(x+1, report['urls'][x]),
                range(len(report['urls']))
            ))
        )
    elif 'game' in report['mode'].lower():
        items = {
            'item-m': 'Masks',
            'item-r': 'Rifles',
            'item-e': 'Explosives',
            'item-c': 'Canned food',
            'item-k': 'Knives',
            'item-f': 'First-aid kits',
            'item-w': 'Winter clothes'
        }
        deaths = {
            's-kill': 'choosing to unalive oneselves',
            'f-kill': 'fisting',
            'k-kill': 'stabbing',
            'r-kill': 'gun violence',
            'a-kill': 'wandering around places one should not be',
            'e-kill': 'stepping on stuff',
            'w-kill': 'petting the wrong dog',
            'h-kill': 'negligence',
            'n-kill': 'the hand of their sexual partners'
        }
        embed = discord.Embed(
            title='Armageddon game',
            description='\n'.join([
                'Started by: <@{}>'.format(report['author']),
                'Duration: *{}*'.format(utils.get_timedelta(report['timestamps'][1]-report['timestamps'][0])),
                '{} on day {}'.format('Everybody died' if not report['winner'] else '<@{}> won'.format(report['winner']), report['day'])
            ]),
            timestamp=datetime.datetime.fromtimestamp(report['timestamps'][1], tz=datetime.timezone.utc),
            color=0xedf069
        ).add_field(
            name='{} players joined'.format(len(report['participants'])),
            value=' '.join(map(lambda x: f'<@{x}>', report['participants'])),
            inline=False
        )
        allitems = sum([report['stats'][i] for i in items])
        if allitems > 0:
            embed.add_field(
                name='Total items found: {}'.format(sum([report['stats'][i] for i in items])),
                value='\n'.join([i for i in [
                    '{}: {}'.format(items[k], report['stats'][k])  if report['stats'][k] > 0 else None for k in items
                ] if i is not None])
            )
        embed.add_field(
            name='Death board', value='\n'.join([
                'Times attack options were chosen: {}'.format(report['stats']['attacks']),
                '\n'.join([i for i in ['{death} death{s} by {method}'.format(
                    death=report['stats'][k], s='s' if report['stats'][k] > 1 else '', method=deaths[k]
                ) if report['stats'][k] > 0 else None for k in deaths] if i is not None])
            ])
        )
    elif 'event' in report['mode'].lower():
        winners = sum([i[1] for i in report['winners']])
        embed = discord.Embed(
            title='Armageddon event',
            description='\n'.join([
                'Started by: <@{}>'.format(report['author']),
                'Duration: *{}*'.format(utils.get_timedelta(report['timestamps'][1]-report['timestamps'][0])),
                '{}/{} game{} played, {}{} winner{} found ({} unique winner{})'.format(
                    len(report['reports']),
                    report['games'][0],
                    's' if report['games'][0] > 1 else '',
                    winners,
                    '/{}'.format(report['games'][1]) if report['games'][1] else '',
                    's' if (report['games'][1] and report['games'][1] > 1) or (not report['games'][1] and winners > 1) else '',
                    len(report['winners']),
                    's' if len(report['winners']) > 1 else ''
                )
            ]),
            timestamp=datetime.datetime.fromtimestamp(report['timestamps'][1], tz=datetime.timezone.utc),
            color=0xedf069
        ).add_field(
            name='{} members participated'.format(len(report['participants'])),
            value=' '.join(map(lambda x: f'<@{x}>', report['participants'])),
            inline=False
        ).add_field(
            name='Winners',
            value='\n'.join(map(lambda x: '<@{}> - {} game{}'.format(x[0], x[1], 's' if x[1] > 1 else ''), report['winners']))
        )
    elif 'tournament' in report['mode'].lower():
        embed = discord.Embed(
            title=report['mode'],
            timestamp=datetime.datetime.fromtimestamp(report['timestamps'][1], tz=datetime.timezone.utc),
            description='\n'.join([
                'Participants: {}'.format(len(report['participants'])),
                'Winner: <@{}>'.format(report['winner']),
                'Tourney duration: *{}*'.format(utils.get_timedelta(report['timestamps'][1]-report['timestamps'][0])),
            ])
        )
        for i in report['logs']:
            embed.add_field(
                name='Round {}'.format(i),
                value='\n'.join(map(
                    lambda x: '{s1}<@{id1}>{s1} {hp1:,.1f} - {hp2:,.1f} {s2}<@{id2}>{s2}'.format(
                        id1=x[0][0], id2=x[1][0], hp1=x[0][1], hp2=x[1][1], s1='~~' if x[0][1] == 0 else '', s2='~~' if x[1][1] == 0 else ''
                    ),
                    report['logs'][i]
                ))
            )
    elif 'lottery' in report['mode'].lower():
        sold = len([i for i in report['tickets'] if report['tickets'][i]])
        embed = discord.Embed(
            title='Lottery report',
            description='\n'.join([
                'Host: <@{}>'.format(report['author']),
                'Lottery duration: *{}*'.format(utils.get_timedelta(report['timestamps'][1]-report['timestamps'][0])),
                'The winning number is: **{}**'.format(report['winner'])
            ]),
            timestamp=datetime.datetime.fromtimestamp(report['timestamps'][1], tz=datetime.timezone.utc),
            color=0xFF0000
        )
        if report['tickets'][report['winner']]:
            embed.color = 0x00FF00
            embed.add_field(
                name='Winner', value='<@{}>'.format(report['tickets'][report['winner']])
            ).add_field(
                name='Tax', value='{:,.0f}'.format(sold * report['tax'] * report['price'])
            ).add_field(
                name='Prize', value='{:,.0f}'.format(sold * (1 - report['tax']) * report['price'])
            )
        embed.add_field(
            name='Max tickets per user', value='{}'.format(sold, len(report['max']))
        ).add_field(
            name='Tickets sold', value='{}/{}'.format(sold, len(report['tickets']))
        ).add_field(
            name='Price per ticket', value='{:,d}'.format(report['price'])
        ).add_field(
            name='Total', value='${:,d}'.format(sold * report['price'])
        )
    return embed