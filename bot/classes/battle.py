import discord, random

from bot.assets import battle  # type: ignore
from bot.utils import utils  # type: ignore

class Fighter:
    def __init__(
        self, user, *, 
        name: str = None, thumbnail: str = None, data: dict = None,  # type: ignore
        hp: float = 250, dmg: int = None, amr: int = None, atkm: float = None, defm: float = None,  # type: ignore
        bounty: int = 0,
        building: int = 0
    ):
        self.user: discord.User = user
        self.name: str = name if name is not None else user.display_name
        self.thumbnail: str = thumbnail or (user.avatar_url if user else None)  # type: ignore
        self.color: int = random.getrandbits(24)
        self.boosted: bool = False
        self.equipped: bool = False
        # self.cached: dict = data is None
        self.bounty: int = bounty

        if data is not None:
            self.classes = data['class']
            bonus = utils.get_class_bonus('rdr', data)
            pbonus = utils.get_class_bonus('prg', data)
            (dmg, amr) = utils.get_race_bonus(data['race'])
            dmg += (pbonus + utils.get_class_bonus('mge', data))
            amr += (pbonus + utils.get_class_bonus('wrr', data))
            self.dmg, self.amr = dmg, amr
            self.atkm, self.defm = round(data['atkmultiply'] + (bonus + building) / 10, 1), round(data['defmultiply'] + (bonus + building) / 10, 1)
            self.hp = 250 + 10 * utils.get_class_bonus('rng', data)
            self.level = utils.getlevel(data['xp'])
            self.guild = data['guild']
            self.luck = data['luck']
            self.basedmg, self.baseamr, self.ffdmg, self.ffamr = None, None, None, None
        else:
            self.classes = None
            self.dmg, self.amr = dmg, amr
            self.atkm, self.defm = atkm, defm
            self.hp = hp
            self.level = 0
            self.guild = 0
            self.luck = 1
            self.basedmg, self.baseamr, self.ffdmg, self.ffamr = None, None, None, None

    def increase(self, *, dmg = 0, amr = 0):
        if not self.equipped:
            self.equipped = True
            self.ffdmg, self.ffamr = self.dmg, self.amr
        self.dmg += dmg
        self.amr += amr

    def boost(self):
        if not self.boosted:
            self.boosted = True
            self.basedmg = self.dmg
            self.baseamr = self.amr
            self.dmg = round(self.dmg * self.atkm, 1)
            self.amr = round(self.amr * self.defm, 1)
    
    def hit(self, damage: float, ignore_armor: bool = False):
        if ignore_armor:
            taken = damage
        else:
            taken = round(damage - self.amr, 1) if damage > self.amr else 0
        self.hp -= taken
        if self.hp < 0: self.hp = 0
        return (taken, self.hp)

    async def cache(self, bot):
        if not await bot.pool.fetchval(
        'SELECT EXISTS(SELECT 1 FROM profile WHERE uid=$1);',
        self.user.id,
        ):
            await bot.pool.execute(
                'INSERT INTO profile (uid, wt, atk, def, ratk, rdef, guild, uatk, udef, classes)'
                ' VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10);',
                self.user.id,
                discord.utils.utcnow(),
                self.dmg, self.amr,
                self.atkm, self.defm,
                self.guild,
                self.ffdmg if self.ffdmg else self.dmg, self.ffamr if self.ffamr else self.amr,
                self.classes
            )
        else:
            await bot.pool.execute(
                'UPDATE profile SET wt=$2, atk=$3, def=$4, ratk=$5, rdef=$6, guild=$7, uatk=$8, udef=$9, classes=$10'
                ' WHERE uid=$1;',
                self.user.id,
                discord.utils.utcnow(),
                self.dmg, self.amr,
                self.atkm, self.defm,
                self.guild,
                self.ffdmg if self.ffdmg else self.dmg, self.ffamr if self.ffamr else self.amr,
                self.classes
            )

    @staticmethod
    async def get_cached_fighter(bot, user):
        if await bot.pool.fetchval(
            'SELECT EXISTS(SELECT 1 FROM profile WHERE uid=$1);',
            user.id
        ):
            res = await bot.pool.fetchval(
                'SELECT (atk, def, ratk, rdef, guild, uatk, udef, xp, classes[1:2]) FROM profile WHERE uid=$1', user.id
            )
            f = Fighter(user, dmg=int(res[0]), amr=int(res[1]), atkm=float(res[2]), defm=float(res[3]))
            f.guild = res[4]
            f.ffdmg = res[5]
            f.ffamr = res[6]
            f.level = utils.getlevel(res[7])
            f.classes = res[8]
            return f
        else:
            return None

class CityDefenses:
    def __init__(self, name):
        self.name = name.title()
        self.hp = battle.city_defenses[name][0]
        self.total_hp = battle.city_defenses[name][0]
        self.damage = battle.city_defenses[name][1]
        if self.name.startswith(('O', 'I')):
            self.name = 'an ' + self.name + ' Wall'
        elif self.name.startswith('A'):
            self.name = 'an ' + self.name + ' Tower'
        else:
            self.name = 'a ' + self.name

    def attacked(self, dmg: float = 0):
        self.hp -= dmg
        return self.hp if round(self.hp,1) > 0 else 0