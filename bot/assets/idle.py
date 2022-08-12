from decimal import Decimal

QUERY_PREFIX = 'https://public-api.travitia.xyz/idle/'


weapon_fetching_guilds = [17555, 3960, 2807, 8244, 6055, 20314]
max_raid_building = [2807, 8244, 13992, 6055, 17555, 3960, 20314, 15356, 19599, 20120, 20809, 25859]

crates = ['crates_common', 'crates_uncommon', 'crates_rare', 'crates_magic', 'crates_legendary', 'crates_mystery']

queries = {
    # Profile
    'profile':      'profile?user=eq.{userid}',
    'xp':           'profile?select=xp&user=eq.{id}',
    'leaderboard':  'profile?user=not.eq.356091260429402122&order={order}',
    # Equipped
    'equip_old':    'allitems?select=*,inventory(equipped),profile(user,race,class,atkmultiply,defmultiply,guild,luck,xp)&owner=eq.{owner}&inventory.equipped=is.true&id=in.({ids})',
    'equipped':     'allitems?select=*,inventory(equipped),profile(user,race,class,atkmultiply,defmultiply,guild,luck,xp)&owner=eq.{owner}&inventory.equipped=is.true&hand=in.({hands})&id=not.in.({ids})&damage=lte.{damage}&armor=lte.{armor}&hand=in.({hands})&order=armor.desc,damage.desc',
    'scan_stats':   'allitems?select=*,inventory(equipped),profile(user,race,class,atkmultiply,defmultiply,guild,luck,xp)&owner=eq.{owner}&inventory.equipped=is.true&hand=in.({hands})&id=not.in.({ids})&id=gt.{idmin}&{stats}&order=id',
    # Item
    'item':         'allitems?id=eq.{id}&select=*,market(price),inventory(equipped)',
    'fav':          'allitems?select=owner,name,id,armor,damage,type&id=in.({ids})&owner=eq.{uid}',
    # Guild
    'guild':        'profile?guild=eq.{id}&order=xp.desc&select=guildrank,user,money,{custom},guild_leader_fkey(id,leader,channel,memberlimit,money,banklimit,wins,upgrade,name,description,icon,alliance(*))',
    'alliance':     'guild?select=name,id,alliance,leader,description,money&or=(id.eq.{gid},alliance.eq.{aid})',
    'stats':        'profile?guild=in.({ids})&select=user,name,xp,race,class,atkmultiply,defmultiply&order=xp.desc',
    # Market
    'cheap':    'market?price=lte.{max}&price=gte.{min}&select=id,item,price,allitems(value,damage,armor,type)&order=id.desc{id}',
    'search':   'market?select=price,published,item(*)'
}

# Profile consts

badges = [
    'Contributor', 'Designer', 'Developer', 'Game Designer', 'Game Master', 'Support', 'Betasquad', 'Veteran', 
]

weapon_bonus = {
    'Sword':    ({'wrr'}, 5),
    'Spear':    ({'prg'}, 5),
    'Axe':      ({'rdr'}, 5),
    'Wand':     ({'mge', 'rtl'}, 5),
    'Knife':    ({'thf'}, 5),
    'Dagger':   ({'thf'}, 5),
    'Bow':      ({'rng'}, 10),
}

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
    'The Assassin': 294894701708967936,
    'Kvothe': 489637665633730560,
    'CHamburr': 446290930723717120,
    'Eden': 339217921576402956,
    'Jesus': 322354047162122243,
    'Lyx': 444169012809564161,
    'Kirby': 589493375527419905,
    'Monox': 149505704569339904,
}

luck_options = ['The Assassin', 'Kvothe', 'CHamburr', 'Eden', 'Jesus', 'Lyx', 'Kirby', 'Monox']

luck_label = [
    'Timestamp', 'Assassin', 'Kvothe', 'CHamburr', 'Eden', 'Jesus', 'Lyx', 'Kirby', 'Monox'
]

luck_range = [
    Decimal(0.25), Decimal(0.3), Decimal(0.2), Decimal(0.5), Decimal(1), Decimal(0.4), Decimal(1), Decimal(1)
]


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

weapontypes = ["Sword", "Shield", "Axe", "Wand", "Dagger", "Knife", "Spear", "Bow", "Hammer", "Scythe", "Howlet"]
weaponhands = ['left', 'right', 'any', 'both']

loot = [
    ("Punjabi Remix", 9500),
    ("Cold Shower", 8406),
    ("Hot Coffee", 7416),
    ("Unenriched Uranium", 9999),
    ("Wetstone", 2400),
    ("Bandit Essence", 1544),
    ("Catharsis", 9463),
    ("Cathartic Sacrifice", 10000),
    ("Leaf Blower", 150),
    ("Happy Noises", 274),
    ("Smelly Durian", 110),
    ("Vibranium", 6974),
    ("The Eternal Flesh", 8196),
    ("The Locksmith's Key", 7519),
    ("Flying Bullet", 4471),
    ("Nasty Roots", 3603),
    ("Psycadelic Mushrooms", 408),
    ("Smitten Dandruff", 505),
    ("Cute Kittens", 1337),
    ("Lots Of Cats", 7331),
    ("Wine Bottle", 105),
    ("Random Sheep", 375),
    ("Golden Nugget", 1009),
    ("Shiny Nickel", 196),
    ("White Crimson", 604),
    ("Lucky Penny", 706),
    ("Cinderellas Shoe", 126),
    ("Charged Quartz", 676),
    ("Rapunzel's Locks", 779),
    ("Kek's Laptops", 6004),
    ("Warrior's Scalp", 2004),
    ("Evangelion", 9098),
    ("Self-Purity", 1067),
    ("Plastic Memories", 1046),
    ("Ability To Feel", 10000),
    ("Sense Of Affection", 8994),
    ("Childhood Innocence", 7095),
    ("Cherished Memories", 6013),
    ("Phoenix Feather", 777),
    ("Excalibur", 9954),
    ("Saber Fang", 1016),
    ("Lion Tooth", 503),
    ("Dragon Claw", 5996),
    ("Spirits", 7995),
    ("Phoenix Feather", 1024),
    ("Cursed Parrot", 1464),
    ("Dragon Heartstring", 8099),
    ("Spiritual Birb", 5421),
    ("Power Stone", 6421),
    ("Time Stone", 5063),
    ("Soul Stone", 4134),
    ("Tiger Claws", 9412),
    ("Eagle Wings", 1644),
    ("Frog", 100),
    ("John Cena", 10000),
    ("Rabbit's Foot", 120),
    ("Cyclop's Eye", 470),
    ("Gold Pot", 2510),
    ("Goblin Stone", 1900),
    ("Dwarf Hat", 707),
    ("Unbreaking 3 Diamond Pickaxe", 8610),
    ("Ivory Needle", 253),
    ("Noodle Brain", 330),
    ("Maiden By The Water", 3005),
    ("Lover's Limb", 1010),
    ("Bran Just Bran", 5960),
    ("Beans", 100),
    ("Master Ball", 339),
    ("Master Sword", 604),
    ("Pepper", 105),
    ("Discarded Remenants", 180),
    ("Sugar", 103),
    ("Salt", 102),
    ("Bible", 777),
    ("Holy Water", 168),
    ("Holy Cross", 199),
    ("Holy Shit", 255),
    ("Holy Corpse", 321),
    ("Morning Coffee Cup", 109),
    ("The Gilded Grave", 222),
    ("Warm Blanket", 239),
    ("Bejeweled Egg", 3051),
    ("Zerekiel's Claw", 9946),
    ("Heart Of Zerekiel", 9999),
    ("Unwavering Gaze", 1001),
    ("Cobblestone", 101),
    ("Chiseled Stone", 120),
    ("Engraved Stone", 170),
    ("Moonstone", 553),
    ("Smoothestone", 774),
    ("Burnt Toast", 100),
    ("Shiny Stone", 278),
    ("Twice Baked Potato", 100),
    ("Shiny Rock", 208),
    ("The Lost Night", 404),
    ("Gold Mist", 4096),
    ("Old Man's Stick", 125),
    ("Angel Tears", 777),
    ("Llama Spit", 140),
    ("Yandel Guide Of The Wind", 603),
    ("Adrian's Sweat", 6666),
    ("Goat's Heart", 201),
    ("Essence Of Adrian", 10000),
    ("Smooth Rock", 153),
    ("Maiden Hair", 181),
    ("Broken Branch", 103),
    ("Golden Fleece", 1005),
    ("Maidens Wool", 180),
    ("Mjolnir", 9909),
    ("Kibble And Bits", 164),
    ("Random Food", 444),
    ("Lucky Can", 778),
    ("Baked Bread", 109),
    ("Busted Bifocals", 507),
    ("The Pen Of Writing", 704),
    ("Temporal Tablet", 7055),
    ("Oracle Stone", 6016),
    ("My Soul", 7777),
    ("Beta Worshippers", 808),
    ("Belle Delphine's Gamer Girl Bath Water", 9988),
    ("Box Of Parts", 503),
    ("Elixir", 611),
    ("Sword Parts", 313),
    ("Bone Handle", 215),
    ("Some Random Guy's Spleen", 630),
    ("Gold", 746),
    ("Rubies", 847),
    ("Diamonds", 1021),
    ("Gold Dust", 401),
    ("Ingots", 1053),
    ("Copper", 305),
    ("Iron", 407),
    ("Bronze", 349),
    ("Precious Metal", 939),
    ("Fairy Dust", 991),
    ("Fairy Wings", 998),
    ("Goat", 400),
    ("Magical Water", 221),
    ("Amber Amulet", 4015),
    ("Dragon's Heart", 8888),
    ("Glowing Stone", 1035),
    ("Blood", 122),
    ("Necronomicon", 9612),
    ("Mysterious Tablet", 6014),
    ("Book Of Spells", 6066),
    ("Berhala", 179),
    ("Arcane Stone", 6135),
    ("Statue", 507),
    ("Pixie Dust", 779),
    ("Unicorn Horn", 777),
    ("Iron Ingot", 507),
    ("Hand Guard", 704),
    ("Toilet Paper", 9999),
]

adventures = [
    "Spider Cave",
    "Troll Bridge",
    "A Night Alone Outside",
    "Ogre Raid",
    "Proof Of Confidence",
    "Dragon Canyon",
    "Orc Tower",
    "Seamonster's Temple",
    "Dark Wizard's Castle",
    "Slay The Famous Dragon Arzagor",
    "Search For Excalibur",
    "Find Atlantis",
    "Tame A Phoenix",
    "Slay The Death Reaper",
    "Meet Adrian In Real Life",
    "The League Of Vecca",
    "The Gem Expedition",
    "Gambling Problems?",
    "The Necromancer Of Kord",
    "Last One Standing",
    "Gambling Problems? Again?",
    "Insomnia",
    "Illuminated",
    "Betrayal",
    "IdleRPG",
    "Learn Programming",
    "Scylla's Temple",
    "Trial Of Osiris",
    "Meet The War God In Hell",
    "Divine Intervention",
]

sort_strength = {
    'str': 'Raid Strength',
    'pvp': 'Total PvP Stat',
    'atk': 'Attack',
    'def': 'Defense',
    'ratk': 'Raid Attack',
    'rdef': 'Raid Defense',
    'atkm': 'Raid Damage Multiplier',
    'defm': 'Raid Defense Multiplier',
    'lvl': 'Level',
}