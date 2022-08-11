import datetime

from bot.assets import idle, postgres  # type: ignore
from bot.utils import utils  # type: ignore

MAX_RAID_BUILDING = [2807, 8244, 13992, 6055, 17555, 3960, 20314, 15356, 19599, 20120, 20809, 25859]

class Profile:
    def __init__(self, *, data = {}, user = None, race = 'Human', classes = [], guild = -1, raidstats = [1,1], xp = 0, completed = 0, deaths = 0, weapons = []):
        self.user = data['user'] if 'user' in data else user
        self.race = data['race'] if 'race' in data else race
        self.classes = [idle.classes[i] for i in data['class'] if i in idle.classes] if 'class' in data else classes
        self.guild = data['guild'] if 'guild' in data else guild
        self.raidstats = [data['atkmultiply'], data['defmultiply']] if 'atkmultiply' in data and 'defmultiply' in data else raidstats
        self.xp = data['xp'] if 'xp' in data else xp
        self.completed = data['completed'] if 'completed' in data else completed
        self.deaths = data['deaths'] if 'deaths' in data else deaths
        self.luck = data['luck'] if 'luck' in data else 1
        self.weapons = weapons
        self.new = True

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
        await bot.pool.execute(
            postgres.queries['profile_update'],
            self.user,
            self.race,
            self.classes,
            self.guild,
            self.raidstats,
            datetime.datetime.now(datetime.timezone.utc)
        )

    @staticmethod
    async def update_adventures(bot, data):
        await bot.pool.execute(
            postgres.queries['adv_update'],
            *data,
        )

    @staticmethod
    async def get_profile(bot, *, user = 0, data = {}):
        uid = data['user'] if 'user' in data else user
        p = None
        res = await bot.pool.fetchrow(
            'SELECT race, classes, weapon, guild, raidstats FROM profile3 WHERE uid=$1',
            uid
        )
        if res:
            p = Profile(
                user=uid,
                race=data['race'] if 'race' in data else res['race'],
                classes=[idle.classes[i] for i in data['class'] if i in idle.classes] if 'class' in data else res['classes'],
                guild=data['guild'] if 'guild' in data else res['guild'],
                raidstats=[data['atkmultiply'], data['defmultiply']] if 'atkmultiply' in data and 'defmultiply' in data else res['raidstats'],
                weapons=res['weapon'])
            p.new = False
        if p is None:
            p = Profile(user=uid, data=data)
        return p

