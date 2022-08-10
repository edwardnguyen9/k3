import discord, math

from bot.assets import api

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
    for i in api.levels:
        if xp >= i:
            level += 1
        else:
            return level
    return level

def getnextevol(xp: int):
    """Returns user's XP until next milestone (int)"""
    level = 0
    for i in api.levels:
        if xp >= i:
            level += 1
        else:
            break
    if level < 12:
        return api.levels[11] - xp
    elif level == 30:
        return None
    else:
        return api.levels[(level // 5 + 1) * 5 - 1] - xp

def get_class_bonus(c: str, data):
    classes = [api.classes[i] for i in data['class'] if i in api.classes]
    for i in classes:
        if c == i[0]: return int(i[1])
    return 0

def get_race_bonus(r: str):
    i = api.races.index(r)
    return (4-i, i)

def get_weapon_bonus(weapons, classes):
    bonus = 0
    for i in weapons:
        if i[1] in api.weapon_bonus and len(api.weapon_bonus[i[1]][0].intersection([i[0] for i in classes])) > 0: bonus += api.weapon_bonus[i[1]][1]
    return bonus

def transmute_class(data):
    return [api.classes[i] for i in data['class'] if i in api.classes]