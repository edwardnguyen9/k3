import discord
from urllib.parse import quote

from bot.assets import api

def minmax(_name, _min, _max):
    temp = []
    if _min is not None: temp.append('gte.{}'.format(_min))
    if _max is not None: temp.append('lte.{}'.format(_max))
    if len(temp) == 2: return '&and=({name}.{},{name}.{})'.format(name=_name, *temp)
    elif len(temp) == 1: return '&{name}={}'.format(name=_name, *temp)
    else: return ''

def query_class(class_tree: str):
    tree = [k for k, v in api.classes.items() if v[0] == class_tree]
    return '&class=ov.{' + ','.join(tree) + '}'

def query_profile(
    name: str, lvmin: int, lvmax: int, race: str, classes: str,
    emin: int, emax: int, ratkmin: float, ratkmax: float, rdefmin: float, rdefmax: float,
    pvpmin: int, pvpmax: int, spouse: discord.User, lsmin: int, lsmax: int,
    god: str, luck: float, fmin: int, fmax: int, guild: int,
    limit: int, sort: str, reverse: bool
) -> str:
    if reverse:
        if '.desc' in sort: sort.replace('.desc', '.asc')
        else: sort.replace('.asc', '.desc')
    query = 'profile?limit={}&order={}'.format(limit if 0 < limit < 250 else 250, sort)
    if name: query += '&name=plfts.{}'.format(quote(name))
    temp = []
    if lvmin: temp.append('gte.{}'.format(api.levels[lvmin - 1]))
    if lvmax: temp.append('lte.{}'.format(api.levels[lvmax] - 1))
    if len(temp) == 2: query += '&and=(xp.{},xp.{})'.format(*temp)
    elif len(temp) == 1: query += '&xp={}'.format(*temp)
    if race: query += '&race=in.({})'.format(race.title().replace(' ', ''))
    if classes:
        query += query_class(classes)
        # classes = classes.title()
        # if ' Or ' in classes:
        #     query += '&class=ov.{' + ','.join([r.strip() for r in classes.split('Or')]) + '}'
        # elif ' And ' in classes:
        #     query += '&class=cs.{' + ','.join([r.strip() for r in classes.split('And')]) + '}'
        # elif classes.endswith(' Class'):
        #     tree = (
        #         api.raider if classes.startswith('Raider') else
        #         api.warrior if classes.startswith('Warrior') else
        #         api.mage if classes.startswith('Mage') else
        #         api.paragon if classes.startswith('Paragon') else
        #         api.thief if classes.startswith('Thief') else
        #         api.ritualist if classes.startswith('Ritualist') else
        #         api.ranger if classes.startswith('Ranger') else
        #         []
        #     )
        #     query += '&class=ov.{' + ','.join(tree) + '}'
        # else:
        #     query+= '&class=ov.{' + classes + '}'
    if luck: query += f'&luck=eq.{luck:.2f}'
    query += minmax('money', emin, emax)
    query += minmax('atkmultiply', ratkmin, ratkmax)
    query += minmax('defmultiply', rdefmin, rdefmax)
    query += minmax('pvpwins', pvpmin, pvpmax)
    query += minmax('lovescore', lsmin, lsmax)
    query += minmax('favor', fmin, fmax)
    if spouse: query += '&marriage=eq.{}'.format(spouse.id)
    if god: query += '&god=in.({})'.format(quote(god.title().replace('Chamburr', 'CHamburr').replace('The', '').replace(' ', '').replace('Assassin', 'The Assassin')))
    if guild: query += '&guild=eq.{}'.format(guild)
    return query