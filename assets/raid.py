gods = {
    'lyx': ['Ouroboros has spawned.', 'The bravest warrior will get a legendary crate!', 793873023245615104], 
    'jesus': ['Atheistus the Tormentor has returned.', 'The highest bidder among the survivors will get a legendary crate!', 613817172191346726], 
    'chamburr': ['The giant hamburger has spawned.', 'The highest bidder among the survivors will get a legendary crate!', 606388494922809345], 
    'monox': ['Mathis Mensing is guarding the top secret cheese factory in Indonesia.', 'One lucky survivor will get a legendary crate!', 793876041323511818], 
    'eden': ['The guardian to the Garden of Eden has awoken.', 'One lucky survivor will get a legendary crate!', 694110880442482700], 
    'kirby': ['Dark Mind is attacking Dream Land.', 'Each survivor gets $10,000, and one lucky warrior will also get a legendary crate!', 793886562533769226], 
    'kvothe': ['The cthae has gathered {number:,d} scrael. They drop money upon being killed.', 'The warrior with the most kills will get a legendary crate!', 606386904157388800],
    'none': ['A raid has been started.', 'Survive and defeat the boss within 45 minutes for a chance for a legendary crate!', 506133354874404874]
}

hp = 'This boss has {hp:,d} HP.'
cash = 'The total payout is ${cash:,d}.'
link = 'Head to <#{id}> to join the raid.'

wuxi_gif = 'https://i.imgur.com/4tmo6I3.gif'
half_a_zombie = 'https://i.imgur.com/apqa5bj.jpg'
full_zombie = 'https://i.imgur.com/EZHrSvx.jpg'
big_zombie = 'https://i.imgur.com/bxX4de7.jpg'

raid_cfg = {
    'hp': 1000000,
    'mod': 200000,
    'reg': 600.0,
    'time': 2700.0,
}

prompts = {
    'belthazor': {
        'possessed': (
            '<@{boss}> broke into your home while under Belthazor\'s control. '
            'Although you tried your best to fight back, you made the rookie mistake of making eye contact with them. '
            'Since everyone knows eyes are windows to the soul, you are now under Belthazor\'s control.'
        ),
        'success_summon': (
            'You successfully summonned Belthazor. '
            'It tried to take your body, but lucky for you, your summoning circle protected you from it. '
            'Belthazor is now looking for another victim.'
        ),
        'failed_summon': (
            'You did a poor job drawing your summoning circle. Belthazor took one look at you and decided it wanted your body.'
        ),
        'message': (
            'The evil spirit Belthazor has possessed {boss.name} and is wreaking havoc. '
            'The good people of **{guild.name}** has been requested to intervene, seeing that the possessed warrior is one of us.\n'
            '{boss.user.mention} has {bosshp:,d} HP.\nRegistration period ends <t:{regtime}:R>.'
            # '\nReact with \u2694 to join!'
        ),
        'wiped': (
            'Belthazor managed to wipe everyone out with {boss.user.mention}...\n'
            '**{boss.name}** is now under its control and won\'t be able to participate in the next battle.'
        ),
        'timeout': (
            'Everyone did not manage to defeat {boss.user.mention} in time.\n'
            '**{boss.name}** is now under Belthazor control and won\'t be able to participate in the next battle.'
        ),
        'won': (
            'Everyone managed to defeat {boss.user.mention}, expelling Belthazor from their body.\n'
            '**Survivors:** {survivors}\n'
            'The evil spirit exploded into golden dust, covering everyone in it. '
            'The survivors can\'t help but inhale the dust... {blessed.user.mention} feels like something has entered their body...'
        ),
        'blessed': (
            'Congratulations! You have a 30% chance of being Belthazor\'s next victim in **{guild.name}**.'
        ),
        'possess': (
            'Congratulations! You have a 30% chance of successfully picking the next Belthazor victim in **{guild.name}**. '
            'Your target can be anyone but yourself. Try to do that before another mod starts a Belthazor raid.'
        ),
    },
    'impostor': {
        'possessed': (
            'While walking home at night, you decided to take a shortcut through a very shady neighborhood '
            '(yes, *very* smart). As you approached a cloaked figure who was standing in your path ("How dare they?"), '
            'your head started spinning and you lost consciousness...'
        ),
        'message': (
            '{boss.name} has been acting very suspicious lately. '
            'The good people of **{guild.name}** have decided to confront them.\n'
            'Suddenly, **{boss.name}** takes out a weird purplish vial from their pocket and drank it. Their body immediately grows, and they turn into a giant.\n'
            '{boss.user.mention} has {bosshp:,.0f} HP.\nRegistration period ends <t:{regtime}:R>.'
            # '\nReact with \u2694 to join!'
        ),
        'fake_wiped': '{boss.user.mention} managed to wipe everyone out...',
        'fake_timeout': '{boss.user.mention} ran away... The remaining survivors are too badly wounded to pursue...',
        'boss_reveal': (
            'Everyone managed to defeat **{boss.name}**. They shrunk back to their original size.\n'
            'Wait a minute...\n'
            'What\'s happening?\n'
            'No! It wasn\'t {boss.user.mention}, it was **{real_boss}** all along! '
            'They have come back in their true form with {bosshp:,.0f} HP and is looking a lot stronger now!!!'
        ),
        'wiped': '**{boss}** managed to wipe everyone out...',
        'timeout': '**{boss}** escaped, and the remaining survivors are too badly wounded to pursue...',
        'won': (
            'Everyone managed to defeat **{real_boss}**.\n**Survivors:** {survivors}\n'
            'After searching their house, the city leaders found {boss.user.mention} tied to a chair in their own basement.'
        )
    },
    'enhanced': {
        'dm': (
            'The people of **{guild.name}** have pissed you off for the last time. '
            'Through shady deals, you have acquired for yourself a potion that would give you power. '
            'After locking your door to make sure no one could interrupt this process, you drank the potion.'
        ),
        'message': (
            '**{boss.name}**\'s temper has become worse and worse these days. '
            'After claiming that **{pissoff.display_name}** was looking at them in a funny way, they started to attack anyone in sight. '
            'The city leader has requested everyone\'s help to subdue **{boss.name}**.\n'
            '{boss.user.mention} has {bosshp:,d} HP.\nRegistration period ends <t:{regtime}:R>.'
            # '\nReact with \u2694 to join!'
        ),
        'wiped': '{boss.user.mention} killed everyone and walked away.',
        'timeout': 'After a fierce battle, {boss.user.mention} managed to escape.',
        'won': (
            'Everyone managed to apprehend {boss.user.mention}. They now will have to answer for their crimes.\n'
            '**Survivors:** {survivors}\n{lucky.user.mention} was the lucky one to get the last hit.'
        )
    },
    'undead': {
        'undead': (
            'The peaceful day the inhabitants of **{guild.name}** were enjoying was cut short when their scout returned with bad news: *A horde of undeads is heading towards their city!*\n'
            'Although slow and weak, those walking corpses could pose a threat in great numbers. Your scout spotted {no} of them heading your way.\n'
            'Everyone in **{guild.name}** was asked to help the leaders defend their beloved city.\n'
            'Registration period ends <t:{regtime}:R>.'
            # '\nReact with \u2694 to join!'
        ),
        'endless': (
            'The somber day just got worse when you felt the unmistakable presence of dark magic in the air. '
            'Before you could alert anyone, the ground cracked open and a horde of undeads crawled back to the land of the living.\n'
            'You are surrounded. Your only choices are to fight the undeads, or become one in a gruesome way.\n'
            'Registration period ends <t:{regtime}:R>.'
            # '\nReact with \u2694 to join!'
        ),
        'wiped': 'The undeads have managed to wipe everyone out.',
        'timeout': 'The remaining undeads suddenly fall to the ground, as if their strings have been cut.\nSurvivors: {survivors}',
        'won': 'The brave warriors have managed to defeat the horde of undeads.\nSurvivors: {survivors}',
    },
    'city': {
        'message': (
            'The city **{name}** has been invaded by the army of **{enemy}**. '
            'Its inhabitants are terrorized by the heinous acts of their new ruler. '
            'The good people of **{guild.name}** has been asked to liberate the people of **{name}**.\n'
            '{name}\'s total defense is {defenses}.\nRegistration period ends <t:{regtime}:R>.'
            # '\nReact with \u2694 to join!'
        ),
        'wiped': (
            'The warriors were wiped out by the defenses of {name}...\n'
            'The people continue to live under the reign of terror of {enemy}.\n'
            '{destroyed}'
        ),
        'timeout': (
            'The warriors took too long... {enemy} has managed to ask for reinforcement. '
            'It is wiser to leave {name} for now, lest you all be wiped out.\n'
            '**Survivors:** {survivors}\n'
            '{destroyed}'
        ),
        'won': (
            'The warriors managed to tear down the defenses of {name} and drive the army of {enemy} away. '
            '{enemy} vow to have their revenge soon.\n**Survivors:** {survivors}\n'
            '{destroyed}'
        ),
    }
}

impostor_bosses = [
    {
        "name": "The Absorber",
        "title": "The Absorber",
        "gif": "https://i.imgur.com/QW1eu3N.png",
        "heal": 0.5,
        "dmg": 1,
        "def": 1,
        "hp_mod": 1.1
    },
    {
        "name": "Thanos",
        "title": "Thanos the Mad Titan",
        "gif": "https://i.imgur.com/TyybbwU.png",
        "dmg": 1.5,
        "def": 1,
        "hp_mod": 0.85
    },
    {
        "name": "Bomb Voyage",
        "title": "Bomb Voyage",
        "gif": "https://i.imgur.com/9iGX8M3.png",
        "mines": 0.3,
        "dmg": 1,
        "def": 1,
        "hp_mod": 1
    },
    {
        "name": "Dr. Poison",
        "title": "Dr. Poison",
        "gif": "https://i.imgur.com/4ukRT9U.png",
        "psn": 0.1,
        "dmg": 0.5,
        "def": 1,
        "hp_mod": 1
    }
]

defenses = ['cannon', 'archer', 'outer', 'inner', 'moat', 'tower', 'ballista']
defense_labels = ['Cannons', 'Archers', 'Outer walls', 'Inner walls', 'Moats', 'Towers', 'Ballistas']
defense_cost = [200_000, 100_000, 500_000, 200_000, 150_000, 200_000, 100_000]
        
city_defenses = {
    'cannon': (500, 60),
    'archer': (1000, 50),
    'outer': (40000, 0),
    'inner': (20000, 0),
    'moat': (10000, 25),
    'tower': (2000, 50),
    'ballista': (500, 30)
}