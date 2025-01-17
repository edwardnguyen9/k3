from urllib.parse import quote

from assets import idle

def minmax(_name, _min, _max):
    temp = []
    if _min is not None: temp.append('gte.{}'.format(_min))
    if _max is not None: temp.append('lte.{}'.format(_max))
    if len(temp) == 2: return '&and=({name}.{},{name}.{})'.format(name=_name, *temp)
    elif len(temp) == 1: return '&{name}={}'.format(name=_name, *temp)
    else: return ''

def query_class(class_tree,):
    tree = [k for k, v in idle.classes.items() if v[0] == class_tree]
    return '&class=ov.{' + ','.join(tree) + '}'

def profiles(
    name, lvmin, lvmax, race, classes,
    emin, emax, ratkmin, ratkmax, rdefmin, rdefmax,
    pvpmin, pvpmax, spouse, lsmin, lsmax,
    god, luck, fmin, fmax, guild,
    limit, sort, reverse,
) -> str:
    if reverse:
        if '.desc' in sort: sort.replace('.desc', '.asc')
        else: sort.replace('.asc', '.desc')
    query = 'profile?limit={}&order={}'.format(limit, sort)
    if name: query += '&name=plfts.{}'.format(quote(name))
    temp = []
    if lvmin: temp.append('gte.{}'.format(idle.levels[lvmin - 1]))
    if lvmax: temp.append('lte.{}'.format(idle.levels[lvmax] - 1))
    if len(temp) == 2: query += '&and=(xp.{},xp.{})'.format(*temp)
    elif len(temp) == 1: query += '&xp={}'.format(*temp)
    if race: query += '&race=in.({})'.format(race.title().replace(' ', ','))
    if classes:
        classes = classes.lower()
        if ' or ' in classes:
            clist = [r.strip().title() for r in classes.split('or')]
            query += '&class=ov.{' + ','.join(clist) + '}'
        elif ' and ' in classes:
            clist = [r.strip().title() for r in classes.split('and')]
            query += '&class=' + ('cs' if len(clist) < 3 else 'cd') + '.{' + ','.join(clist) + '}'
        elif classes in ['rdr', 'wrr', 'mge', 'prg', 'rng', 'thf', 'rtl']:
            query += query_class(classes)
        else:
            query+= '&class=ov.{' + classes + '}'
    if luck: query += f'&luck=eq.{luck:.2f}'
    query += minmax('money', emin, emax)
    query += minmax('atkmultiply', ratkmin, ratkmax)
    query += minmax('defmultiply', rdefmin, rdefmax)
    query += minmax('pvpwins', pvpmin, pvpmax)
    query += minmax('lovescore', lsmin, lsmax)
    query += minmax('favor', fmin, fmax)
    if spouse: query += '&marriage=eq.{}'.format(spouse.id)
    if god: query += '&god=in.({})'.format(quote(god.title().replace('Chamburr', 'CHamburr').replace('The', '').replace(' ', ',').replace('Assassin', 'The Assassin')))
    if guild: query += '&guild=eq.{}'.format(guild)
    return query

def guilds(
    imin, imax, aimin, aimax, name, user, mlim, blmin, blmax,
    bmin, bmax, umin, umax, gmin, gmax, limit, sort, reverse,
) -> str:
    if reverse:
        if '.desc' in sort: sort.replace('.desc', '.asc')
        else: sort.replace('.asc', '.desc')
    query = 'guild?select={}&limit={}&order={}'.format(
        'badge,badges,banklimit,channel,description,icon,id,leader,memberlimit,money,name,upgrade,wins,alliance(*)',
        limit, sort
    )
    if name: query += '&name=plfts.{}'.format(quote(name))
    if user: query += '&leader=eq.{}'.format(user.id)
    if mlim: query += '&memberlimit=eq.{}'.format(mlim)
    query += minmax('id', imin, imax)
    query += minmax('alliance', aimin, aimax)
    query += minmax('banklimit', blmin, blmax)
    query += minmax('money', bmin, bmax)
    query += minmax('upgrade', umin, umax)
    query += minmax('wins', gmin, gmax)
    return query

def items(
    imin, imax, name, user, smin, smax, vmin, vmax,
    wtype, otype, hand, sign, mod, ex, limit, sort, reverse,
) -> str:
    if reverse:
        if '.desc' in sort: sort.replace('.desc', '.asc')
        else: sort.replace('.asc', '.desc')
    # if name is None:
    #     query = 'allitems?limit={}&order={}&select=*,market(price),inventory(equipped)'.format(limit, sort)
    # else:
    #     query = 'allitems?limit={}'.format(limit)
    query = 'allitems?limit={}&order={}&select=*,market(price),inventory(equipped)'.format(limit, sort)
    if user: query += '&owner=eq.{}'.format(user.id)
    temp = []
    if smin: temp.append('(damage.gte.{s},armor.gte.{s})'.format(s=smin))
    if smax: temp.append('(and(damage.lte.{s},armor.eq.0),and(armor.lte.{s},damage.eq.0))'.format(s=smax))
    if len(temp) == 2: query += '&and=(or{},or{})'.format(*temp)
    elif len(temp) == 1: query += '&or={}'.format(*temp)
    if wtype: query += '&type=in.({})'.format(wtype.title().replace(' ', ','))
    if otype: query += '&original_type=in.({})'.format(otype.title().replace(' ', ','))
    if hand: query += '&hand=in.({})'.format(hand.lower().replace(' ', ','))
    query += minmax('value', vmin, vmax)
    query += minmax('id', imin, imax)
    if name: query += '&name=plfts.{}'.format(quote(name)) if len(name.split()) == 1 else '&name=eq.{}'.format(quote(name))
    if sign is not None: query += '&signature={}is.null'.format('not.' if sign else '')
    if mod is not None:
        if mod == 'No': query += '&original_name=is.null&original_type=is.null'
        elif mod == 'Name': query += '&original_name=not.is.null&original_type=is.null'
        elif mod == 'Type': query += '&original_name=is.null&original_type=not.is.null'
        elif mod == 'Both': query += '&original_name=not.is.null&original_type=not.is.null'
        else: query += '&or=(original_name.not.is.null,original_type.not.is.null)'
    if ex:
        if isinstance(ex, str):
            ex = [i for i in ex.replace(',', ' ').split() if i.isdecimal()]
        query += '&id=not.in.({})'.format(','.join(map(str, ex)))
    return query

def pets(
    name, user, fmin, fmax, dmin, dmax,
    jmin, jmax, lmin, lmax, limit, sort, reverse,
) -> str:
    if reverse:
        if '.desc' in sort: sort.replace('.desc', '.asc')
        else: sort.replace('.asc', '.desc')
    query = 'pets?limit={}&order={}'.format(limit, sort)
    if name: query += '&name=plfts.{}'.format(quote(name))
    if user: query += '&user=eq.{}'.format(user.id)
    query += minmax('food', fmin, fmax)
    query += minmax('drink', dmin, dmax)
    query += minmax('joy', jmin, jmax)
    query += minmax('love', lmin, lmax)
    return query

def children(
    name, father, mother, parent, amin, amax, gender, limit, sort, reverse,
) -> str:
    if reverse:
        if '.desc' in sort: sort.replace('.desc', '.asc')
        else: sort.replace('.asc', '.desc')
    query = 'children?limit={}&order={}'.format(limit if 0 < limit < 250 else 250, sort)
    if name: query += '&name=plfts.{}'.format(quote(name))
    if father: query += '&father=eq.{}'.format(father.id)
    if mother: query += '&mother=eq.{}'.format(mother.id)
    if parent: query += '&or=(father.eq.{i},mother.eq.{i})'.format(i=parent.id)
    if gender: query += '&gender=eq.{}'.format(gender)
    query += minmax('age', amin, amax)
    return query

def loot(
    user, name, imin, imax, vmin, vmax, limit, sort, reverse,
) -> str:
    if reverse:
        if '.desc' in sort: sort.replace('.desc', '.asc')
        else: sort.replace('.asc', '.desc')
    query = 'loot?limit={}&order={}'.format(limit if 0 < limit < 250 else 250, sort)
    if name: query += '&name=plfts.{}'.format(quote(name))
    if user: query += '&user=eq.{}'.format(user.id)
    query += minmax('id', imin, imax)
    query += minmax('value', vmin, vmax)
    return query

def market(
    wtype, smin, smax, pmin, pmax, iid,
) -> str:
    query = 'market?select=id,price,published,item(*)'
    query += minmax('price', pmin, pmax)
    if smin is not None: query += '&or=(item.damage.gte.{0},armor.gte.{0})'.format(smin)
    if smax is not None: query += '&item.damage=lte.{0}&item.armor=lte.{0}'.format(smax)
    if wtype is not None:
        if 'Two' in wtype: query += '&item.hand=eq.both'
        elif 'One' in wtype: query += '&item.hand=not.eq.both'
        else: query += '&item.type=in.({})'.format(','.join([i.title() for i in wtype.replace(',',' ').split()]))
    if isinstance(iid, str):
        ex = [i for i in iid.replace(',', ' ').split() if i.isdecimal()]
        query += '&id=not.in.({})'.format(','.join(map(str, ex)))
    return query