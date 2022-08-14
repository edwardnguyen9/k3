import discord, math, json, datetime
from typing import Union
from decimal import Decimal

from bot.assets import idle, postgres  # type: ignore

def pager(entries, chunk: int, similar_chunk: bool = False):
    if similar_chunk:
        total = math.ceil(len(entries) / chunk)
        per_chunk = math.floor(len(entries) / total)
        leftover = len(entries) - per_chunk * total
        pointer = 0
        for i in range(total):
            start, pointer, leftover = pointer, pointer + per_chunk + int(leftover > 0), leftover - 1
            yield entries[start:pointer]
    else:
        for x in range(0, len(entries), chunk):
            yield entries[x : x + chunk]

def check_if_all_null(*args):
    for i in args:
        if i is not None: return False
    return True

def embedcolor(colours: dict):
    """Returns color from (r,g,b) dict"""
    r = colours['red']
    g = colours['green']
    b = colours['blue']
    return discord.Color.from_rgb(r, g, b)

def getlevel(xp: int):
    """Returns user's level (int)"""
    level = 0
    for i in idle.levels:
        if xp >= i:
            level += 1
        else:
            return level
    return level

def getnextlevel(xp: int):
    """Returns user's XP until next level (int)"""
    level = 0
    for i in idle.levels:
        if xp >= i:
            level += 1
        else:
            break
    if level == 30:
        return None
    else:
        return idle.levels[level] - xp

def getnextevol(xp: int):
    """Returns user's XP until next milestone (int)"""
    level = 0
    for i in idle.levels:
        if xp >= i:
            level += 1
        else:
            break
    if level < 12:
        return idle.levels[11] - xp
    elif level == 30:
        return None
    else:
        return idle.levels[(level // 5 + 1) * 5 - 1] - xp

def getto30(xp: int):
    return idle.levels[-1] - xp if idle.levels[-1] > xp else 0

def get_class_bonus(check: str, data: Union[dict, list]):
    bonus = 0
    c = ['wrr', 'prg'] if check == 'amr' else ['mge', 'prg'] if check == 'dmg' else [check]
    classes = [idle.classes[i] for i in data['class'] if i in idle.classes] if isinstance(data, dict) else data
    for i in classes:
        if i[0] in c: bonus += int(i[1])
    return bonus

def get_race_bonus(r: str):
    i = idle.races.index(r)
    return (4-i, i)

def get_weapon_bonus(weapons, classes):
    bonus = 0
    for i in weapons:
        if isinstance(i, dict):
            if (
                i['type'] in idle.weapon_bonus
                and len(idle.weapon_bonus[i['type']][0].intersection([j[0] for j in classes])) > 0
            ):
                bonus += idle.weapon_bonus[i['type']][1]
            else:
                continue
        else:
            if (
                i[1] in idle.weapon_bonus
                and len(idle.weapon_bonus[i[1]][0].intersection([j[0] for j in classes])) > 0
            ):
                bonus += idle.weapon_bonus[i[1]][1]
    return bonus

def transmute_class(data):
    return [idle.classes[i] for i in data['class'] if i in idle.classes]

def get_class(data):
    return [k for k, v in idle.classes.items() if v in data]

def adv_success(profile, level, booster, building):
    a, d, _, _ = profile.fighter_data()
    const = a + d + 75 + building
    chances = []
    for i in range(7): chances += [const - (i + 1) * level - 0.5 * getlevel(profile.xp), const - (i + 1) * level + getlevel(profile.xp)]
    chances.sort()
    if chances[0] < 0 and profile.luck == 0: return None
    else: return [(round(c * profile.luck if c >= 0 else c / profile.luck) + 25 * booster) for c in chances]

async def get_luck(bot, limit = 10):
    res = await bot.redis.lrange('lucklog', 0, limit-1)
    data = []
    for i in res:
        i_loaded = json.loads(i.replace('\'', '"'))
        data.append([i_loaded[0], *[Decimal(x) for x in i_loaded[1:]]])
    return data

def get_market_entry(item, trimmed = False):
    res = {}
    if trimmed:
        res['id'] = item['id']
        res['name'] = item['name']
        res['type'] = item['type']
        res['stat'] = item['stats'] if 'stats' in item else item['stat']
        res['value'] = item['value']
        res['price'] = item['price']
        res['published'] = item['published']
        res['signature'] = item['signature'] if 'signature' in item else None
        res['owner'] = item['owner']
    elif 'owner' in item:
        res['id'] = item['id']
        res['name'] = item['name']
        res['type'] = item['type']
        res['stat'] = int(item['damage'] + item['armor'])
        res['value'] = item['value']
        res['price'] = item['market'][0]['price']
        res['published'] = res['last_updated'] = int(datetime.datetime.fromisoformat(
            item['market'][0]['published'][:item['market'][0]['published'].index('.')] + item['market'][0]['published'][item['market'][0]['published'].index('+'):]
        ).timestamp())
        res['signature'] = item['signature']
        res['owner'] = item['owner']
    elif 'published' in item:
        res['id'] = item['item']['id']
        res['name'] = item['item']['name']
        res['type'] = item['item']['type']
        res['stat'] = int(item['item']['damage'] + item['item']['armor'])
        res['value'] = item['item']['value']
        res['price'] = item['price']
        res['published'] = res['last_updated'] = int(datetime.datetime.fromisoformat(
            item['published'][:item['published'].index('.')] + item['published'][item['published'].index('+'):]
        ).timestamp())
        res['signature'] = item['item']['signature']
        res['owner'] = item['item']['owner']
    else:
        res['id'] = item['item']
        res['name'] = item['name']
        res['type'] = item['type']
        res['stat'] = int(item['damage'] + item['armor'])
        res['value'] = item['value']
        res['price'] = item['price']
        res['sold'] = int(datetime.datetime.fromisoformat(
            item['timestamp'][:item['timestamp'].index('.')] + item['timestamp'][item['timestamp'].index('+'):]
        ).timestamp())
        res['signature'] = item['signature']
    return res

def get_role_ids(key: str, cfg: dict):
    role_list = []
    if 'misc' in cfg:
        config = cfg['misc']
        if key == 'arena':
            role_list = config['arena:archive'][config['arena']]['titles'] if 'arena' in config else []
        elif key == 'donation':
            role_list = config['donation']['tiers'] if 'donation' in config else []

    return sorted(
        [[i[1], cfg['role'][i[1]], i[0]] for i in role_list],
        key=lambda x: x[2],
        reverse=True
    )