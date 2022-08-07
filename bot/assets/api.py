QUERY_PREFIX = 'https://public-api.travitia.xyz/idle/'

queries = {
    'profile':   'https://public-api.travitia.xyz/idle/profile?user=eq.{userid}',
}

# Profile consts

badges = [
    'Contributor', 'Designer', 'Developer', 'Game Designer', 'Game Master', 'Support', 'Betasquad', 'Veteran', 
]


classes = {
    'Adventurer':       ['rdr', '1'],
    'Swordsman':        ['rdr', '2'],
    'Fighter':          ['rdr', '3'],
    'Swashbuckler':     ['rdr', '4'],
    'Dragonslayer':     ['rdr', '5'],
    'Raider':           ['rdr', '6'],
    'Eternal Hero':     ['rdr', '7'],
    'Infanterist':      ['wrr', '1'],
    'Footman':          ['wrr', '2'],
    'Shieldbearer':     ['wrr', '3'],
    'Knight':           ['wrr', '4'],
    'Warmaster':        ['wrr', '5'],
    'Templar':          ['wrr', '6'],
    'Paladin':          ['wrr', '7'],
    'Juggler':          ['mge', '1'],
    'Witcher':          ['mge', '2'],
    'Enchanter':        ['mge', '3'],
    'Mage':             ['mge', '4'],
    'Warlock':          ['mge', '5'],
    'Dark Caster':      ['mge', '6'],
    'White Sorcerer':   ['mge', '7'],
    'Novice':           ['prg', '1'],
    'Proficient':       ['prg', '2'],
    'Artisan':          ['prg', '3'],
    'Master':           ['prg', '4'],
    'Champion':         ['prg', '5'],
    'Vindicator':       ['prg', '6'],
    'Paragon':          ['prg', '7'],
    'Mugger':           ['thf', '1'],
    'Thief':            ['thf', '2'],
    'Rogue':            ['thf', '3'],
    'Bandit':           ['thf', '4'],
    'Chunin':           ['thf', '5'],
    'Renegade':         ['thf', '6'],
    'Assassin':         ['thf', '7'],
    'Priest':           ['rtl', '1'],
    'Mysticist':        ['rtl', '2'],
    'Doomsayer':        ['rtl', '3'],
    'Seer':             ['rtl', '4'],
    'Oracle':           ['rtl', '5'],
    'Prophet':          ['rtl', '6'],
    'Ritualist':        ['rtl', '7'],
    'Caretaker':        ['rng', '1'],
    'Tamer':            ['rng', '2'],
    'Trainer':          ['rng', '3'],
    'Bowman':           ['rng', '4'],
    'Hunter':           ['rng', '5'],
    'Warden':           ['rng', '6'],
    'Ranger':           ['rng', '7'],
}

races = ['Jikill', 'Elf', 'Human', 'Dwarf', 'Orc']

gods = {
    'Lyx': 444169012809564161,
    'The Assassin': 294894701708967936,
    'Kirby': 589493375527419905,
    'Monox': 149505704569339904,
    'Eden': 339217921576402956,
    'Kvothe': 489637665633730560,
    'Jesus': 322354047162122243,
    'CHamburr': 446290930723717120
}

levels = [
    0, 1500, 9000, 22500, 42000, 67500,
    99000, 136500, 180000, 229500, 285000, 346500,
    414000, 487500, 567000, 697410, 857814, 1055112,
    1297787, 1596278, 1931497, 2298481, 2689223, 3092606,
    3494645, 3879056, 4228171, 4608707, 5023490, 5475604
]

race_options = {
    'Human': [
        'that I never confessed my true love, and now she is dead.',
        'that I have never been to the funeral of my parents.',
        'that I betrayed my best friend.',
        'One of my biggest regrets is '
    ],
    'Dwarf': [
        'a perfected ale keg.',
        'a magical infused glove.',
        'a bone-forged axe.',
        'One of my proudest creations is '
    ],
    'Elf': [
        'Beringor, the bear spirit.',
        'Neysa, the tiger spirit.',
        'Avril, the wolf spirit.',
        'Sambuca, the eagle spirit.',
        'My favourite spirit of the wild is '
    ],
    'Orc': [
        'my sister.',
        'my father.',
        'my grandmother.',
        'my uncle.',
        'The ancestor that gives me my strength is '
    ],
    'Jikill': [
        'noise.',
        'spiritual pain.',
        'extreme temperatures.',
        'strange and powerful smells.',
        'The biggest action that can outknock me, is '
    ],
}