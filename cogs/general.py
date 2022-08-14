import discord, random, datetime, json, asyncio, math, matplotlib.pyplot as plt, os
from discord import app_commands
from discord.ext import commands
from typing import Union, Optional, Literal
from humanize import intcomma, precisedelta
from io import BytesIO
from pprint import pformat
from decimal import Decimal

from assets import idle, postgres
from bot.bot import Kiddo
from classes.profile import Profile
from classes.paginator import Paginator
from utils import command_config as config, errors, utils, embeds, queries


class General(commands.Cog):
    def __init__(self, bot: Kiddo):
        self.bot = bot
        self.is_first_ready = True
        self.ctx_menu = [
            app_commands.ContextMenu(
                name='Profile', callback=self._menu_profile
            ),
            app_commands.ContextMenu(
                name='Equipped', callback=self._menu_equipped
            ),
            app_commands.ContextMenu(
                name='XP', callback=self._menu_xp
            ),
        ]
        for i in self.ctx_menu:
            self.bot.tree.add_command(i)

    async def cog_unload(self):
        for i in self.ctx_menu:
            self.bot.tree.remove_command(i.name, type=i.type)

    @commands.Cog.listener()
    async def on_ready(self):
        if self.is_first_ready:
            await self.bot.loading()
            server = self.bot.get_guild(475033206672850945)
            crates = {
                'c': (834980524913197106, 'Common crates'),
                'u': (834980525298679808, 'Uncommon crates'),
                'r': (834980525247692840, 'Rare crates'),
                'm': (834980524723929109, 'Magic crates'),
                'l': (834980524652363799, 'Legendary crates'),
                'my': (926861270680993813, 'Mystery crates'),
            }
            async def get_crate(c):
                emoji = None
                if server is not None:
                    try:
                        emoji = await server.fetch_emoji(crates[c][0])
                    except Exception:
                        print('Error fetching crate', c)
                return emoji or crates[c][1]
            self.bot.crates = {
                'c': await get_crate('c'),
                'u': await get_crate('u'),
                'r': await get_crate('r'),
                'm': await get_crate('m'),
                'l': await get_crate('l'),
                'my': await get_crate('my')
            }
            print(self.__class__.__name__, 'is ready')
            self.is_first_ready = False

    @app_commands.checks.has_permissions(kick_members=True)
    async def _menu_profile(self, interaction: discord.Interaction, user: discord.User):
        await self._get_profile(interaction, user, True)

    @app_commands.checks.has_permissions(kick_members=True)
    async def _menu_equipped(self, interaction: discord.Interaction, user: discord.User):
        await self._get_equipped(interaction, user, True)

    @app_commands.checks.has_permissions(kick_members=True)
    async def _menu_xp(self, interaction: discord.Interaction, user: discord.User):
        await self._get_xp(interaction, user, True)


    @commands.command(
        name='profile',
        aliases=['p', 'pp', 'p2', 'me'],
        brief='Get IdleRPG profile',
        description='Get a user\'s IdleRPG profile',
        usage='[user]',
        help='> [user]: The person whose profile you wish to get. If left blank, will get your own profile'
    )
    async def _profile(self, ctx: commands.Context, user: discord.User = commands.Author):
        await self._get_profile(ctx, user)
    
    @commands.command(
        name='equipped',
        aliases=['eq', 'e'],
        brief='Get equipped items',
        description='Get a user\'s equipped items',
        usage='[user]',
        help='> [user]: The person whose items you wish to get. If left blank, will get your own items.'
    )
    async def _equipped(self, ctx: commands.Context, user: discord.User = commands.Author):
        await self._get_equipped(ctx, user)

    @commands.command(
        name='item',
        aliases=['i'],
        brief='Get item info',
        description='Get an item\'s information',
        usage='<item id>',
        help='> <item id>: The ID of the item.'
    )
    async def _item(self, ctx: commands.Context, iid: int):
        await self._get_item(ctx, iid)

    @commands.command(
        name='guild',
        aliases=['g'],
        brief='Get guild info',
        description='Get a guild\'s information',
        usage='<guild id>',
        help='> <guild id>: The ID of the guild.'
    )
    async def _guild(self, ctx: commands.Context, gid: int):
        await self._get_guild(ctx, gid)

    @commands.command(
        name='alliance',
        aliases=['a'],
        brief='Get alliance members',
        description='Get an alliance\'s members',
        usage='<guild ID>',
        help='> <guild ID>: The ID of an alliance member.'
    )
    async def _alliance(self, ctx: commands.Context, aid: int):
        await self._get_alliance(ctx, aid)

    @commands.command(
        name='query',
        aliases=['q'],
        brief='Send query',
        description='Send a query to IdleRPG API',
        usage='<query>',
        help='''
        > <query>: The query to send
        '''
    )
    async def _query(self, ctx: commands.Context, *, query: str = ''):
        await self._get_query(ctx, query)

    @commands.command(
        name='raidstats',
        aliases=['rs'],
        brief='Get raidstat cost',
        description='Get the cost of increasing raidstats',
        usage='[start] [end]',
        help='''
        > [start]: The starting value (must be at least 1, default to 1).
        > [end]: The final value (must be greater than starting value, default to 10).
        '''
    )
    async def _raidstats(self, ctx: commands.Context, start: float = 1.0, end: float = 10.0):
        if start < 1: raise errors.InvalidInput(ctx, 'start', start)
        if end <= start: raise errors.InvalidInput(ctx, 'end', end)
        await self._get_raidstats(ctx, start, end)

    @commands.command(
        name='xp',
        brief='Get required XP to next milestones',
        description='Get required XP to next milestones',
        usage='[user/XP value]',
        help='''
        > [user/XP value]: The user or the XP to get.
        '''
    )
    async def _xp(self, ctx: commands.Context, target: Optional[Union[discord.User, int]]):
        if isinstance(target, int) and target < 0: raise errors.InvalidInput(ctx, 'value', target)
        await self._get_xp(ctx, target)

    @commands.command(
        name='missions',
        aliases=['adventures', 'adv'],
        brief='Get adventure information',
        description='Get adventure information',
        usage='[custom settings]',
        help='''
        > [custom settings] includes:
        > • `user` - The user used to calculate the chance, default to the command user
        > • `level` - The adventure level, will get all levels if not provided
        > • `booster` - Whether luck booster is used (False by default)
        > • `building` - The level of the adventure building (10 by default)
        '''
    )
    async def _missions(self, ctx: commands.Context, flags: config.AdventureChance):
        await self._get_missions(ctx, flags.user or ctx.author, flags.level, flags.booster, flags.building)

    @commands.command(
        name='gvg',
        brief='Get guild\'s top 20 GvG members',
        description='Get 20 members with the highest PvP stats in a guild',
        help='''
        * Guild member data is updated at least once a day
        '''
    )
    async def _gvg(self, ctx):
        members = []
        res = await self.bot.pool.fetchval('SELECT guild FROM profile3 WHERE uid=$1', ctx.author.id)
        if res is None or res < 1: return await ctx.send('Your data has not been updated.')
        (res, status) = await self.bot.idle_query(
            idle.queries['guild'].format(
                id=res,
                custom=','.join(['race', 'class', 'atkmultiply', 'defmultiply', 'guild'])
            ),
            ctx
        )
        if status == 429:
            raise errors.TooManyRequests(ctx)
        elif res is None:
            return await ctx.send('An error has occurred while trying to fetch data from the server.')
        elif len(res) == 0:
            return await ctx.send('Guild not found.')
        else:
            for i in res:
                p = await Profile.get_profile(self.bot, data=i)
                data = p.fighter_data()
                print(p.user, data[0]+data[1])
                members.append([p, data[0] + data[1]])
            now = discord.utils.utcnow()
            await self.bot.pool.executemany(
                postgres.queries['profile_update'],
                [(i[0].user, i[0].race, i[0].classes, i[0].guild, i[0].raidstats, now) for i in members]
            )
            members.sort(key=lambda x: x[1], reverse=True)
            description = ['{stats} - battle nominate {id}'.format(id=u[0].user, stats=u[1]) for u in members[:20]]
            return await ctx.send('\n'.join(description))

    @commands.command(
        name='activity',
        aliases=['ac', 'activitycheck'],
        brief='Get adventure activity of guild members',
        description='Get adventure activity of guild members',
        usage='[inactive]',
        help='''
        > [inactive]: Whether to only get inactive members (default: True)
        * Guild member data is updated at least once a day
        '''
    )
    async def _activity(self, ctx: commands.Context, inactive: bool = True, gid: Optional[int] = None):
        '''
        Get adventure activity of guild members.
        '''
        gid = gid if ctx.author.id == self.bot.owner.id else None  # type: ignore
        await self._get_activity(ctx, inactive, gid)

    @app_commands.describe(
        user='User (override all other filters)', name='Character name',
        lvmin='Min level', lvmax='Max level', race='Character race', classes='Character class',
        emin='Min balance', emax='Max balance', ratkmin='Min raid damage multiplier', ratkmax='Max raid damage multiplier',
        rdefmin='Min raid defense multiplier', rdefmax='Max raid defense multiplier',
        pvpmin='Min PvP win count', pvpmax='Max PvP win count', spouse='Married to', lsmin='Min lovescore value', lsmax='Max lovescore value',
        god='God', luck='Luck value', fmin='Min favor', fmax='Max favor', guild='Guild', limit='Max number of profiles to fetch', sort='Results order', reverse='Reverse order'
    )
    @app_commands.rename(
        lvmin='level_min', lvmax='level_max', classes='class', emin='balance_min', emax='balance_max',
        ratkmin='damage_multiply_min', ratkmax='damage_multiply_max', rdefmin='defense_multiply_min', rdefmax='defense_multiply_max',
        pvpmin='pvp_min', pvpmax='pvp_max', lsmin='lovescore_min', lsmax='lovescore_max', fmin='favor_min', fmax='favor_max',
        sort='order_by'
    )
    @app_commands.autocomplete(
        classes=config.auto_class, race=config.auto_race, god=config.auto_god
    )
    @app_commands.choices(
        sort=[
            app_commands.Choice(value='name.asc', name='Character name'),
            app_commands.Choice(value='user.asc', name='User ID'),
            app_commands.Choice(value='guild.asc', name='Guild ID'),
            app_commands.Choice(value='guildrank.asc', name='Guild rank'),
            app_commands.Choice(value='race.asc', name='Race'),
            app_commands.Choice(value='class.asc', name='Class'),
            app_commands.Choice(value='xp.desc', name='XP'),
            app_commands.Choice(value='money.desc', name='Money'),
            app_commands.Choice(value='pvpwins.desc', name='PvP wins'),
            app_commands.Choice(value='atkmultiply.desc', name='Damage multiplier'),
            app_commands.Choice(value='defmultiply.desc', name='Defense multiplier'),
            app_commands.Choice(value='completed.desc', name='Adventures completed'),
            app_commands.Choice(value='deaths.desc', name='Adventure deaths'),
            app_commands.Choice(value='god.asc', name='Gods'),
            app_commands.Choice(value='favor.desc', name='Favor'),
            app_commands.Choice(value='luck.desc', name='Luck'),
            app_commands.Choice(value='reset_points.desc', name='Reset points'),
            app_commands.Choice(value='lovescore.desc', name='Love score'),
            app_commands.Choice(value='crates_common.desc', name='Common crates'),
            app_commands.Choice(value='crates_uncommon.desc', name='Uncommon crates'),
            app_commands.Choice(value='crates_rare.desc', name='Rare crates'),
            app_commands.Choice(value='crates_magic.desc', name='Magic crates'),
            app_commands.Choice(value='crates_legendary.desc', name='Legendary crates'),
        ],
    )
    @app_commands.command(name='profile')
    async def _app_profile(
        self, interaction: discord.Interaction, user: Optional[discord.User] = None,
        name: Optional[str] = None, lvmin: Optional[app_commands.Range[int, 1, 30]] = None, lvmax: Optional[app_commands.Range[int, 1, 30]] = None,
        race: Optional[str] = None, classes: Optional[str] = None, emin: Optional[int] = None, emax: Optional[int] = None,
        ratkmin: Optional[app_commands.Range[float, 1]] = None, ratkmax: Optional[app_commands.Range[float, 1]] = None,
        rdefmin: Optional[app_commands.Range[float, 1]] = None, rdefmax: Optional[app_commands.Range[float, 1]] = None,
        pvpmin: Optional[app_commands.Range[int, 0]] = None, pvpmax: Optional[app_commands.Range[int, 0]] = None, spouse: Optional[discord.User] = None,
        lsmin: Optional[app_commands.Range[int, 0]] = None, lsmax: Optional[app_commands.Range[int, 0]] = None, god: Optional[str] = None, luck: Optional[app_commands.Range[float, 0, 2]] = None,
        fmin: Optional[app_commands.Range[int, 0]] = None, fmax: Optional[app_commands.Range[int, 0]] = None, guild: Optional[int] = None,
        limit: app_commands.Range[int, 1, 250] = 100, sort: str = 'xp.desc,money.desc', reverse: bool = False
    ):
        '''
        Get IdleRPG profile
        '''
        if user is not None:
            await self._get_profile(interaction, user)
        elif utils.check_if_all_null(
            name, lvmin, lvmax, race, classes, emin, emax, ratkmin, ratkmax, rdefmin, rdefmax,
            pvpmin, pvpmax, spouse, lsmin, lsmax, god, luck, fmin, fmax, guild
        ):
            await self._get_profile(interaction, interaction.user)
        else:
            await interaction.response.defer(thinking=True)
            query = queries.profiles(
                name, lvmin, lvmax, race, classes, emin, emax, ratkmin, ratkmax, rdefmin, rdefmax,
                pvpmin, pvpmax, spouse, lsmin, lsmax, god, luck, fmin, fmax, guild, limit, sort, reverse
            )
            (res, status) = await self.bot.idle_query(query, interaction)
            if status == 429:
                raise errors.TooManyRequests(interaction)
            elif res is None:
                return await interaction.followup.send('An error has occurred while trying to fetch data from the server.')
            elif len(res) == 0:
                return await interaction.followup.send('No user found.')
            else:
                pages = []
                all_weapons = await self.bot.pool.fetch(postgres.queries['fetch_all_users']) or []
                for i in res:
                    weapons = discord.utils.find(lambda x: x['uid'] == i['user'], all_weapons) or {'weapon': []}
                    embed = embeds.profile(self.bot, i, weapons['weapon'])
                    embed.set_footer(text=(embed.footer.text or interaction.user.name), icon_url=interaction.user.display_avatar.url)
                    pages.append(embed)
                if len(pages) == 1:
                    await interaction.followup.send(embed=pages[0])
                else:
                    return await Paginator(extras=pages, text='{0} entries found.'.format(len(res))).paginate(interaction)

    @app_commands.describe(user='User')
    @app_commands.command(name='equipped')
    async def _app_equipped(
        self, interaction: discord.Interaction, user: Optional[discord.User] = None,
    ):
        '''
        Get equipped item
        '''
        await self._get_equipped(interaction, user or interaction.user)

    @app_commands.describe(
        iid='The ID of the item (override all other filters)',
        imin='Min ID of item', imax='Max ID of item', name='Included in item name', user='Item owner',
        smin='Min stat', smax='Max stat', vmin='Min value', vmax='Max value', wtype='Weapon type',
        otype='Original weapon type (for weapons whose types were changed)', hand='Hand used',
        market='Whether the weapon is currently on market', sign='Whether the weapon is signed',
        mod='Whether the weapon has been modified (name or type)', ex='Excluding weapons',
        limit='Max number of weapons to fetch', sort='Results order', reverse='Reverse order'
    )
    @app_commands.rename(
        iid='id', imin='min_id', imax='max_id', user='owner', smin='min_stat', smax='max_stat', vmin='min_value', vmax='max_value',
        wtype='type', otype='original_type', sign='has_signature', market='is_on_market', mod='modified', ex='exclude', sort='order_by'
    )
    @app_commands.autocomplete(
        wtype=config.auto_type, otype=config.auto_type, hand=config.auto_hand
    )
    @app_commands.choices(
        sort=[
            app_commands.Choice(value='damage.desc', name='Damage'),
            app_commands.Choice(value='armor.desc', name='Armor'),
            app_commands.Choice(value='value.desc', name='Value'),
            app_commands.Choice(value='name.asc', name='Name'),
            app_commands.Choice(value='type.asc', name='Item type'),
            app_commands.Choice(value='hand.asc', name='Hand'),
            app_commands.Choice(value='id.asc', name='ID'),
            app_commands.Choice(value='owner.asc', name='Owner')
        ]
    )
    @app_commands.command(name='item')
    async def _app_item(
        self, interaction: discord.Interaction, iid: Optional[app_commands.Range[int, 0]] = None,
        imin: Optional[app_commands.Range[int, 0]] = None, imax: Optional[app_commands.Range[int, 0]] = None,
        name: Optional[str] = None, user: Optional[discord.User] = None,
        smin: Optional[app_commands.Range[int, 0, 101]] = None, smax: Optional[app_commands.Range[int, 0, 101]] = None,
        vmin: Optional[app_commands.Range[int, 0]] = None, vmax: Optional[app_commands.Range[int, 0]] = None,
        wtype: Optional[str] = None, otype: Optional[str] = None, hand: Optional[str] = None, market: Optional[bool] = None,
        sign: Optional[bool] = None, mod: Optional[Literal['No', 'Name', 'Type', 'Both', 'Any']] = None, ex: Optional[str] = None,
        limit: app_commands.Range[int, 1, 250] = 100, sort: str = 'damage.desc,armor.desc,value.desc', reverse: bool = False
    ):
        '''
        Get item's information
        '''
        if iid is not None:
            await self._get_item(interaction, iid)
        else:
            await interaction.response.defer(thinking=True)
            query = queries.items(
                imin, imax, name, user, smin, smax, vmin, vmax,
                wtype, otype, hand, sign, mod, ex, limit, sort, reverse
            )
            (res, status) = await self.bot.idle_query(query, interaction)
            if status == 429:
                raise errors.TooManyRequests(interaction)
            elif res is None:
                return await interaction.followup.send('An error has occurred while trying to fetch data from the server.')
            elif len(res) == 0:
                return await interaction.followup.send('No item found.')
            else:
                pages = []
                entries = utils.pager(res, 5)
                for i in entries:
                    embed = embeds.items(i)
                    embed.set_footer(text=(embed.footer.text or interaction.user.name), icon_url=interaction.user.display_avatar.url)
                    pages.append(embed)
                if len(pages) == 1:
                    await interaction.followup.send(embed=pages[0])
                else:
                    return await Paginator(extras=pages, text='{0} entries found.'.format(len(res))).paginate(interaction)

    @app_commands.describe(
        gid='The ID of the guild (override all other filters)',
        imin='Min guild ID', imax='Max guild ID', aimin='Min alliance ID', aimax='Max alliance ID', name='Guild name', user='Guild leader',
        mlim='Guild\'s member limit', blmin='Minimum bank limit', blmax='Maximum bank limit', bmin='Minimum guild fund', bmax='Maximum guild fund',
        umin='Minimum guild upgrade', umax='Maximum guild upgrade', gmin='Minimum GvG wins', gmax='Maximum GvG wins',
        limit='Max number of guilds to fetch', sort='Results order', reverse='Reverse order'
    )
    @app_commands.rename(
        gid='id', imin='min_id', imax='max_id', aimin='min_alliance_id', aimax='max_alliance_id', user='leader', mlim='member_limit',
        blmin='bank_limit_min', blmax='bank_limit_max', umin='upgrade_min', umax='upgrade_max', gmin='gvg_wins_min', gmax='gvg_wins_max',
        sort='order_by'
    )
    @app_commands.choices(
        sort=[
            app_commands.Choice(value='alliance.desc', name='Alliance ID'),
            app_commands.Choice(value='id.desc', name='Guild ID'),
            app_commands.Choice(value='name.asc', name='Guild name'),
            app_commands.Choice(value='money.desc', name='Bank balance'),
            app_commands.Choice(value='banklimit.desc', name='Bank limit'),
            app_commands.Choice(value='wins.desc', name='GvG wins'),
            app_commands.Choice(value='memberlimit.desc', name='Member limit'),
        ]
    )
    @app_commands.command(name='guild')
    async def _app_guild(
        self, interaction: discord.Interaction, gid: Optional[app_commands.Range[int, 0]] = None,
        imin: Optional[app_commands.Range[int, 0]] = None, imax: Optional[app_commands.Range[int, 0]] = None,
        aimin: Optional[app_commands.Range[int, 0]] = None, aimax: Optional[app_commands.Range[int, 0]] = None,
        name: Optional[str] = None, user: Optional[discord.User] = None, mlim: Optional[app_commands.Range[int, 50]] = None,
        blmin: Optional[app_commands.Range[int, 0]] = None, blmax: Optional[app_commands.Range[int, 0]] = None,
        bmin: Optional[app_commands.Range[int, 0]] = None, bmax: Optional[app_commands.Range[int, 0]] = None,
        umin: Optional[app_commands.Range[int, 0, 10]] = None, umax: Optional[app_commands.Range[int, 0, 10]] = None,
        gmin: Optional[app_commands.Range[int, 0]] = None, gmax: Optional[app_commands.Range[int, 0]] = None,
        limit: app_commands.Range[int, 1, 250] = 100, sort: str = 'alliance.asc,id.asc', reverse: bool = False
    ):
        '''
        Get guild's information
        '''
        if gid is not None:
            await self._get_guild(interaction, gid)
        else:
            await interaction.response.defer(thinking=True)
            query = queries.guilds(
                imin, imax, aimin, aimax, name, user, mlim, blmin, blmax,
                bmin, bmax, umin, umax, gmin, gmax, limit, sort, reverse
            )
            (res, status) = await self.bot.idle_query(query, interaction)
            if status == 429:
                raise errors.TooManyRequests(interaction)
            elif res is None:
                return await interaction.followup.send('An error has occurred while trying to fetch data from the server.')
            elif len(res) == 0:
                return await interaction.followup.send('No guild found.')
            else:
                pages = []
                update_guild = {}
                for i in res:
                    if str(i['id']) not in update_guild:
                        self.bot.idle_guilds[str(i['id'])] = [i['name'], i['leader'], i['alliance']['id']]
                        update_guild[str(i['id'])] = json.dumps([i['name'], i['leader'], i['alliance']['id']])
                    if i['id'] != i['alliance']['id'] and str(i['alliance']['id']) not in update_guild:
                        self.bot.idle_guilds[str(i['alliance']['id'])] = [i['alliance']['name'], i['alliance']['leader'], i['alliance']['id']]
                        update_guild[str(i['alliance']['id'])] = json.dumps([i['alliance']['name'], i['alliance']['leader'], i['alliance']['id']])
                    if len(update_guild) > 0: await self.bot.redis.hset('guilds', mapping=update_guild)
                    embed = embeds.guild(res[0])
                    embed.set_footer(text=(embed.footer.text or interaction.user.name), icon_url=interaction.user.display_avatar.url)
                    pages.append(embed)
                if len(pages) == 1:
                    await interaction.followup.send(embed=pages[0])
                else:
                    return await Paginator(extras=pages, text='{0} entries found.'.format(len(res))).paginate(interaction)

    @app_commands.describe(aid='Guild ID')
    @app_commands.rename(aid='id')
    @app_commands.command(name='alliance')
    async def _app_alliance(
        self, interaction: discord.Interaction, aid: app_commands.Range[int, 0],
    ):
        '''
        Get alliance members
        '''
        await self._get_alliance(interaction, aid)
    
    @app_commands.describe(
        name='Included in pet name', user='Pet owner',
        limit='Max number of pets to fetch', sort='Results order', reverse='Reverse order',
        fmin='Min food level', dmin='Min drink leve', jmin='Min joy level', lmin='Min love level',
        fmax='Max food level', dmax='Max drink leve', jmax='Max joy level', lmax='Max love level',
    )
    @app_commands.rename(
        user='owner', sort='order_by',
        fmin='min_food', dmin='min_drink', jmin='min_joy', lmin='min_love',
        fmax='max_food', dmax='max_drink', jmax='max_joy', lmax='max_love',
    )
    @app_commands.choices(
        sort=[
            app_commands.Choice(value='name.asc', name='Pet\'s name'),
            app_commands.Choice(value='owner.asc', name='Owner\'s ID'),
            app_commands.Choice(value='food.desc', name='Food level'),
            app_commands.Choice(value='drink.desc', name='Drink level'),
            app_commands.Choice(value='love.desc', name='Love level'),
            app_commands.Choice(value='joy.desc', name='Joy level'),
            app_commands.Choice(value='last_update.desc', name='Last updated'),
        ]
    )
    @app_commands.command(name='pets')
    async def _app_pets(
        self, interaction: discord.Interaction,
        name: Optional[str] = None, user: Optional[discord.User] = None,
        fmin: app_commands.Range[int, 0, 100] = 0, fmax: app_commands.Range[int, 0, 100] = 100,
        dmin: app_commands.Range[int, 0, 100] = 0, dmax: app_commands.Range[int, 0, 100] = 100,
        jmin: app_commands.Range[int, 0, 100] = 0, jmax: app_commands.Range[int, 0, 100] = 100,
        lmin: app_commands.Range[int, 0, 100] = 0, lmax: app_commands.Range[int, 0, 100] = 100,
        limit: app_commands.Range[int, 1, 250] = 100, sort: str = 'last_update.desc', reverse: bool = False
    ):
        '''
        Get pet info
        '''
        await interaction.response.defer(thinking=True)
        query = queries.pets(
            name, user, fmin, fmax, dmin, dmax,
            jmin, jmax, lmin, lmax, limit, sort, reverse
        )
        (res, status) = await self.bot.idle_query(query, interaction)
        if status == 429:
            raise errors.TooManyRequests(interaction)
        elif res is None:
            return await interaction.followup.send('An error has occurred while trying to fetch data from the server.')
        elif len(res) == 0:
            return await interaction.followup.send('No pet found.')
        else:
            pages = []
            for i in res:
                embed = embeds.pet(i)
                embed.set_footer(text=(embed.footer.text or interaction.user.name), icon_url=interaction.user.display_avatar.url)
                pages.append(embed)
            if len(pages) == 1:
                await interaction.followup.send(embed=pages[0])
            else:
                return await Paginator(extras=pages, text='{0} entries found.'.format(len(res))).paginate(interaction)

    @app_commands.describe(
        name='Included in child\'s name', father='Father (the one who did not use $child)', mother='Mother (the one who used $child)',
        parent='Either parent', amin='Min age', amax='Max age', gender='Gender',
        limit='Max number of children to fetch', sort='Results order', reverse='Reverse order',
    )
    @app_commands.rename(
        amin='min_age', amax='max_age', sort='order_by'
    )
    @app_commands.choices(
        gender=[app_commands.Choice(value='m', name='Male'), app_commands.Choice(value='f', name='Female')],
        sort=[
            app_commands.Choice(value='name.asc', name='Child\'s name'),
            app_commands.Choice(value='age.desc', name='Child\'s age'),
            app_commands.Choice(value='gender.asc', name='Gender'),
            app_commands.Choice(value='mother.asc', name='Mother\'s ID'),
            app_commands.Choice(value='father.asc', name='Father\'s ID'),
        ]
    )
    @app_commands.command(name='children')
    async def _app_children(
        self, interaction: discord.Interaction,
        name: Optional[str] = None, father: Optional[discord.User] = None, mother: Optional[discord.User] = None, parent: Optional[discord.User] = None, 
        amin: Optional[app_commands.Range[int, 0]] = None, amax: Optional[app_commands.Range[int, 0]] = None, gender: Optional[str] = None,
        limit: app_commands.Range[int, 1, 250] = 100, sort: str = 'age.desc', reverse: bool = False
    ):
        '''
        Get children info
        '''
        await interaction.response.defer(thinking=True)
        query = queries.children(
            name, father, mother, parent, amin, amax, gender, limit, sort, reverse
        )
        (res, status) = await self.bot.idle_query(query, interaction)
        if status == 429:
            raise errors.TooManyRequests(interaction)
        elif res is None:
            return await interaction.followup.send('An error has occurred while trying to fetch data from the server.')
        elif len(res) == 0:
            return await interaction.followup.send('No child found.')
        else:
            pages = []
            entries = utils.pager(res, 6)
            for i in entries:
                embed = embeds.children(i)
                embed.set_footer(text=(embed.footer.text or interaction.user.name), icon_url=interaction.user.display_avatar.url)
                pages.append(embed)
            if len(pages) == 1:
                await interaction.followup.send(embed=pages[0])
            else:
                return await Paginator(extras=pages, text='{0} entries found.'.format(len(res))).paginate(interaction)

    @app_commands.describe(
        user='The user the loot items belong to', name='Loot item name', imin='Min ID of loot item', imax='Max ID of loot item',
        vmin='Min value of loot item', vmax='Max value of loot item', limit='Max number of loot items to fetch',
        sort='Results order', reverse='Reverse order', ex='Whether to return exchange commands',
    )
    @app_commands.rename(
        user='owner', imin='min_id', imax='max_id', vmin='min_value', vmax='max_value', sort='order_by', ex='exchange'
    )
    @app_commands.choices(
        sort=[
            app_commands.Choice(value='value.desc', name='Loot value'),
            app_commands.Choice(value='id.desc', name='Loot ID'),
            app_commands.Choice(value='name.asc', name='Loot name'),
            app_commands.Choice(value='user.desc', name='Owner'),
        ]
    )
    @app_commands.command(name='loot')
    async def _app_loot(
        self, interaction: discord.Interaction,
        user: Optional[discord.User] = None, name: Optional[str] = None,
        imin: Optional[app_commands.Range[int, 0]] = None, imax: Optional[app_commands.Range[int, 0]] = None,
        vmin: app_commands.Range[int, 100, 10000] = 100, vmax: app_commands.Range[int, 100, 10000] = 10000,
        limit: app_commands.Range[int, 1, 250] = 100, sort: str = 'value.desc,name.asc', reverse: bool = False, ex: bool = False
    ):
        '''
        Get loot item info
        '''
        if user is None and imin is None and imax is None and not ex:
            res = [l for l in idle.loot if vmin <= l[1] <= vmax and (name is None or name.lower() in l[0].lower())]
            if len(res) == 0: return await interaction.followup.send('No loot item found.')
            if 'value' in sort:
                res.sort(key = lambda x: x[0])
                res.sort(key = lambda x: x[1], reverse = not reverse)
            else:
                res.sort(key = lambda x: x[0], reverse = not reverse)
            return await Paginator(
                entries=res,
                title='List of loot items',
                parser=lambda x: x[0] + ', Value : ' + intcomma(x[1]),
                footer='{0} item{1} found.'.format(len(res), 's' if len(res) > 1 else ''),
                color=random.getrandbits(24)
            ).paginate(interaction)
        else:
            await interaction.response.defer(thinking=True)
            if ex or (imin is None and imax is None):
                target = user or interaction.user
            else:
                target = user
            query = queries.loot(
                target, name, imin, imax, vmin, vmax, limit, sort, reverse
            )
            (res, status) = await self.bot.idle_query(query, interaction)
            if status == 429:
                raise errors.TooManyRequests(interaction)
            elif res is None:
                return await interaction.followup.send('An error has occurred while trying to fetch data from the server.')
            elif len(res) == 0:
                return await interaction.followup.send('No loot item found.')
            elif ex:
                value = sum([i['value'] for i in res if 'value' in i])
                entries = utils.pager(res, 150, True)
                await interaction.followup.send('{total} item{plural} found, ${value} in total, or {xp} XP (might be less if exchange in more than one message).'.format(
                    total = len(res), plural = 's' if len(res) > 1 else '', value=intcomma(value), xp=intcomma(int(value/4))
                ))
                for i in entries:
                    msg = await interaction.followup.send('$ex {}'.format(' '.join(map(str, i))), wait=True)
                    await msg.delete(delay=90)
            else:
                pages = []
                entries = utils.pager(res, 6)
                for i in entries:
                    embed = embeds.loot(i)
                    embed.set_footer(text=(embed.footer.text or interaction.user.name), icon_url=interaction.user.display_avatar.url)
                    pages.append(embed)
                if len(pages) == 1:
                    await interaction.followup.send(embed=pages[0])
                else:
                    return await Paginator(extras=pages, text='{0} entries found.'.format(len(res))).paginate(interaction)

    @app_commands.describe(
        wtype='Weapon type', smin='Min weapon stats', smax='Max weapon stats', pmin='Min price', pmax='Max price', iid='Ignore IDs'
    )
    @app_commands.rename(
        wtype='type', smin='min_stat', smax='max_stat', pmin='min_price', pmax='max_price', iid='ignore_id'
    )
    @app_commands.autocomplete(
        wtype=config.auto_market_type
    )
    @app_commands.command(name='market')
    async def _app_market(
        self, interaction: discord.Interaction,
        wtype: Optional[str] = None, smin: Optional[app_commands.Range[int, 0, 101]] = None, smax: Optional[app_commands.Range[int, 0, 101]] = None,
        pmin: Optional[app_commands.Range[int, 0]] = None, pmax: Optional[app_commands.Range[int, 0]] = None, iid: Optional[str] = None
    ):
        '''
        Get market entries
        '''
        await interaction.response.defer(thinking=True)
        query = queries.market(
            wtype, smin, smax, pmin, pmax, iid
        )
        (res, status) = await self.bot.idle_query(query, interaction)
        if status == 429:
            raise errors.TooManyRequests(interaction)
        elif res is None:
            return await interaction.followup.send('An error has occurred while trying to fetch data from the server.')
        else:
            items = []
            for i in res:
                if i['item']: items.append(utils.get_market_entry(i))
            if len(items) == 0: return await interaction.followup.send('No entry found.')
            items.sort(key=lambda x: x['id'])
            items.sort(key=lambda x: x['price'])
            items.sort(key=lambda x: x['stat'], reverse=True)
            entries = utils.pager(items, 5)
            pages = []
            for i in entries:
                embed = embeds.market(i)
                embed.set_footer(text=(embed.footer.text or interaction.user.name), icon_url=interaction.user.display_avatar.url)
                pages.append(embed)
            return await Paginator(extras=pages, text='{0} entries found.'.format(len(items))).paginate(interaction)


    @app_commands.describe(query='The query to send to IdleRPG API')
    @app_commands.command(name='query')
    async def _app_query(self, interaction: discord.Interaction, query: Optional[str] = ''):
        '''
        Send a query to IdleRPG API
        '''
        await self._get_query(interaction, query or '')

    @app_commands.describe(
        start='The starting value (must be at least 1, default to 1)', end='The final value (must be greater than starting value, default to 10)'
    )
    @app_commands.rename(start='start_value', end='final_value')
    @app_commands.command(name='raidstats')
    async def _app_raidstats(self, interaction: discord.Interaction, start: app_commands.Range[float, 1] = 1, end: app_commands.Range[float, 1] = 10):
        '''
        Get the cost of increasing raidstats
        '''
        if end <= start: raise errors.InvalidInput(interaction, 'final_value', end)
        else: await self._get_raidstats(interaction, start, end)

    @app_commands.describe(
        xp='The XP to calculate (override user filter)', user='The user to fetch'
    )
    @app_commands.command(name='xp')
    async def _app_xp(self, interaction: discord.Interaction, xp: Optional[app_commands.Range[int, 0]] = None, user: Optional[discord.User] = None):
        '''
        Get required XP to next milestones
        '''
        if xp is not None:
            await self._get_xp(interaction, xp)
        else:
            await self._get_xp(interaction, user)

    @app_commands.describe(
        user='Get success chance for this user (default to the command user)',
        level='Get detailed information for this adventure level',
        booster='Whether luck booster is used', building='The level of the adventure building (10 by default)'
    )
    @app_commands.rename(
        booster='time_booster', building='adventure_building',
    )
    @app_commands.command(name='adventures')
    async def _app_missions(self, interaction: discord.Interaction,
        user: Optional[discord.User] = None, level: Optional[app_commands.Range[int, 1, 30]] = None,
        booster: bool = False, building: app_commands.Range[int, 0, 10] = 10
    ):
        '''
        Get adventure information
        '''
        await self._get_missions(interaction, user or interaction.user, level, booster, building)

    @app_commands.choices(
        god=[
            app_commands.Choice(value=idle.luck_label[i+1], name=idle.luck_options[i]) for i in range(len(idle.luck_options))
        ]
    )
    @app_commands.command(name='luck')
    async def _app_luck(self, interaction: discord.Interaction, god: Optional[str] = None, limit: Optional[app_commands.Range[int, 10]] = None):
        '''
        Get luck statistics
        '''
        await interaction.response.defer(thinking=True)
        if god is None:
            data = await utils.get_luck(self.bot, 0 if limit is None else limit)
            avg = []
            range_and_current = []
            timestamp = discord.utils.utcnow()
            for i in range(len(idle.luck_range)):
                range_and_current.append([idle.luck_options[i], idle.luck_range[i], data[0][i+1]])
                time = [entry[0] for entry in data if entry[i+1] >= 0]
                vals = [entry[i+1] for entry in data if entry[i+1] >= 0]
                total = []
                for k, v in enumerate(vals):
                    if k != 0:
                        total.append(v * Decimal(time[k-1] - time[k]))
                    else:
                        total.append(v * Decimal(timestamp.timestamp() - time[k]))
                average = Decimal(sum(total) / Decimal(timestamp.timestamp()-time[-1]))
                avg.append([idle.luck_options[i], average, Decimal((average - Decimal(1)) / idle.luck_range[i])])
            range_and_current.sort(key=lambda x: x[2], reverse=True)
            avg.sort(key=lambda x: x[1], reverse=True)
            description = 'God\'s luck\n```\n{luck}```\nGod\'s average luck\n```\n{avg}```'.format(
                luck='\n'.join(['{0:12}: 1 ± {1:.2f} | Current: {2:.2f}'.format(*i) for i in range_and_current]),
                avg='\n'.join(['{0:12}: {1:.3f} ({2:=+7.2%})'.format(*i) for i in avg])
            )
            embed = discord.Embed(
                title='Luck statistics',
                description=description,
                color=random.getrandbits(24),
                timestamp=timestamp
            ).add_field(
                name='Last luck update', value=f'<t:{data[0][0]}:f>'
            ).add_field(
                name='First luck update', value='<t:1591006380:f>'
            ).set_footer(text=interaction.user.name, icon_url=interaction.user.display_avatar.url)
            await interaction.followup.send(embed=embed)
        else:
            if limit is None: limit = 10
            index = idle.luck_label.index(god)
            data = await utils.get_luck(self.bot, limit)
            time = [i[0] for i in data if i[index] >= 0]
            vals = [i[index] for i in data if i[index] >= 0]
            url = await self.bot.redis.get(f'chart:{god}:{len(vals)}')
            if url is None:
                font = {
                    'family': 'serif',
                    'color':  'darkred',
                    'weight': 'normal',
                    'size': 24,
                }
                font2 = {
                    'family': 'serif',
                    'color':  'green',
                    'weight': 'normal',
                    'size': 10,
                }
                avg_msg = []
                isnow = discord.utils.utcnow()
                ts = isnow.timestamp()
                week = datetime.timedelta(days=7).total_seconds()
                mon = isnow.replace(hour=0, minute=0, second=0) - datetime.timedelta(days=isnow.weekday())
                xes = [(ts-i)/week for i in time]
                width = (ts - time[-1])/week
                gap = (ts - mon.timestamp()) / week
                if round(width) == math.floor(width): width = math.ceil(width)
                else: width = math.ceil(width) + 0.5
                avg_msg.append(
                    '{:d} weeks in total'.format(math.floor((ts - time[-1])/week))
                )
                plt.figure(figsize=(width-2, 8), dpi=80).patch.set_facecolor('#bdbdbd')
                axis = plt.gca()
                axis.set_ylim([0,2])
                axis.set_xlim([width,-0.5])
                axis.axes.get_xaxis().set_visible(False)
                axis.set_facecolor('#bdbdbd')
                for i in range(-1, math.ceil(width)):
                    if i + gap > -0.5:
                        plt.plot([i + gap, i + gap], [0, 2], color='white', lw=0.3, ls=':')
                plt.plot([-0.5, width], [Decimal(1) + idle.luck_range[index-1], Decimal(1) + idle.luck_range[index-1]], color='red', lw=0.1)
                plt.plot([-0.5, width], [Decimal(1) - idle.luck_range[index-1], Decimal(1) - idle.luck_range[index-1]], color='red', lw=0.1)
                plt.plot([-0.5, width], [1, 1], color='blue', lw=0.1)
                total = []
                for k, v in enumerate(vals):
                    if k != 0:
                        total.append(v * Decimal(xes[k] - xes[k-1]))
                    else:
                        total.append(v * Decimal(xes[k]))
                average = Decimal(sum(total) / Decimal(xes[-1]))
                plt.plot([-0.5, width], [average, average], color='green', lw=0.3)
                plt.plot([0] + xes, [vals[0]] + vals, drawstyle='steps')
                for x, y in zip(xes, vals):
                    label = '{:.2f}'.format(y)
                    offsety = 8 if (x != xes[-1] and vals[xes.index(x)+1] < y) or (x == xes[-1] and vals[-1] < 1) else -13
                    offsetx = (x - xes[xes.index(x)-1])/2 if x != xes[0] else x/2
                    plt.annotate(label, (x-offsetx,y), textcoords='offset points', xytext=(0, offsety), ha='center', bbox=dict(boxstyle="round", fc="w", lw=1, alpha=0.8))
                avg_msg.insert(0, f'Average: {average:.3f}')
                plt.text(width, -0.1, '\n'.join(avg_msg), horizontalalignment='left', verticalalignment='top', fontdict=font2)
                plt.title(f'Last {len(vals)} Luck Values of {idle.luck_options[index-1]}', fontdict=font, pad=10)
                plt.savefig(fname='luck', bbox_inches='tight', pad_inches=0.5)
                message = await self.bot.log_event('luck', file=discord.File('luck.png'))
                os.remove('luck.png')
                plt.close()
                await self.bot.redis.set(f'chart:{god}:{len(vals)}', message.attachments[0].url, ex=43200)  # type: ignore
                url = message.attachments[0].url  # type: ignore
            time_unix = (await utils.get_luck(self.bot, 1))[0][0]
            embed = discord.Embed(
                title=f'{idle.luck_options[index-1]} Luck History',
                timestamp=discord.utils.utcnow()
            ).set_image(url=url).add_field(
                name='Last luck reroll', value='<t:{0}:F> (<t:{0}:R>)'.format(time_unix)
            ).add_field(
                name='First data', value='<t:{0}:F> (<t:{0}:R>)'.format(time[-1])
            )
            await interaction.followup.send(embed=embed)

    @app_commands.describe(
        imin='Min ID of item', imax='Max ID of item', name='Included in item name', user='Item owner (default to command user)',
        smin='Min stat', smax='Max stat', vmin='Min value', vmax='Max value', wtype='Weapon type',
        hand='Hand used', ex='Excluding weapons', limit='Max number of weapons to fetch',
        trade='Get command for trade instead of merch (default to True)'
    )
    @app_commands.autocomplete(
        wtype=config.auto_type, hand=config.auto_hand
    )
    @app_commands.rename(
        user='owner', smax='max_stat', smin='min_stat', wtype='type', imin='min_id', imax='max_id', vmin='min_value', vmax='max_value', ex='exclude', trade='for_trade'
    )
    @app_commands.command(name='trademerch')
    async def _app_trademerch(
        self, interaction: discord.Interaction, user: Optional[discord.User] = None,
        smax: Optional[app_commands.Range[int, 0, 101]] = None, smin: Optional[app_commands.Range[int, 0, 101]] = None,
        wtype: Optional[str] = None, hand: Optional[str] = None, name: Optional[str] = None,
        imax: Optional[app_commands.Range[int, 0]] = None, imin: Optional[app_commands.Range[int, 0]] = None,
        vmax: Optional[app_commands.Range[int, 0]] = None, vmin: Optional[app_commands.Range[int, 0]] = None, ex: Optional[str] = None,
        limit: app_commands.Range[int, 1, 250] = 250, trade: bool = True
    ):
        '''
        Get items for trading/merching
        '''
        await interaction.response.defer(thinking=True)
        owner = user or interaction.user
        protected = await self.bot.pool.fetchval(postgres.queries['view_fav'], owner.id) or []
        if ex: protected += [int(i) for i in ex.split()]  # type: ignore
        query = queries.items(
            imin, imax, name, owner, smin, smax, vmin, vmax, wtype, None, hand, None, None, list(set(protected)), limit, 'id.desc', False  # type: ignore
        ) + '&select=id,value,inventory(equipped),market(price)&inventory.equipped=is.false'
        (res, status) = await self.bot.idle_query(query, interaction)
        if status == 429:
            raise errors.TooManyRequests(interaction)
        elif res is None:
            return await interaction.followup.send('An error has occurred while trying to fetch data from the server.')
        elif len(res) == 0:
            return await interaction.followup.send('No item found.')
        else:
            total = 0
            messages = []
            prefix = '$trade add items' if trade else '$merch'
            msg_lim = 30 if trade else 125
            items = []
            for i in res:
                if i['inventory'] and not i['market']:
                    total += i['value']
                    items.append(i['id'])
            pages = utils.pager(items, msg_lim, True)
            for i in pages:
                messages.append(
                    '{} {}'.format(
                        prefix, ' '.join(map(str, i))
                    )
                )
            msg_lim = 5 if trade else 1
            await interaction.followup.send(
                'Total: {} items (removed {} item{})\nMerch value at 1x: ${:,d}\nThe other messages will be deleted after 2 minutes.'.format(
                    t:=len(items), r:=len(res)-len(items), '' if r == 1 else 's', total
                )
            )
            for i in range(0, len(messages), msg_lim):
                msg = await interaction.followup.send('```\n{}```'.format('\n\n'.join(messages[i:i+msg_lim])), wait=True)
                await msg.delete(delay=120)

    @app_commands.describe(
        add='Item IDs to add to protected list', remove='Item IDs to remove from protected list'
    )
    @app_commands.command(name='protected')
    async def _app_protected(
        self, interaction: discord.Interaction, add: Optional[str] = None, remove: Optional[str] = None
    ):
        '''
        Get your protected items (items excluded from /trademerch)
        '''
        await interaction.response.defer(thinking=True)
        message = []
        def get_id_list_from_str(string: Optional[str]) -> list:
            if string is None: return []
            ids = []
            for i in string.replace(',', ' ').split():
                if not i.isdecimal(): raise errors.InvalidInput(interaction, 'ID', i)
                ids.append(int(i))
            return sorted(list(set(ids)))
        async with self.bot.pool.acquire() as conn:
            already_protected = set(await conn.fetchval(postgres.queries['view_fav'], interaction.user.id) or [])
            remove_list = get_id_list_from_str(remove)
            add_list = get_id_list_from_str(add)
            if remove_list:
                message.append('Removed {} item{} from favorite list.'.format(r:=len(already_protected.intersection(remove_list)), 's' if r != 1 else ''))
                already_protected.difference_update(remove_list)
            if add_list:
                add_list = set(add_list).difference(already_protected)
                already_protected.update(add_list)
            (res, status) = await self.bot.idle_query(
                idle.queries['fav'].format(uid=interaction.user.id, ids=','.join(map(str, already_protected))),
                interaction
            )
            if status == 429:
                raise errors.TooManyRequests(interaction)
            elif res is None:
                return await interaction.followup.send('An error has occurred while trying to fetch data from the server.')
            else:
                ids = sorted(i['id'] for i in res)
                message.insert(0, 'Removed invalid item{}.'.format('s' if r > 1 else '') if (r:=len(already_protected.difference(ids))) > 0 else None)
                message.append('Added {} new item{} to favorites list.'.format(r:=len(set(add_list).intersection(ids)), 's' if r > 1 else '') if len(add_list) else None)
                already_protected = ids
            await conn.execute(postgres.queries['update_fav'], interaction.user.id, already_protected)
        if len(already_protected) == 0:
            return await interaction.followup.send(
                ' '.join([i for i in message if i is not None]),
                embed = discord.Embed(
                    title='Protected items',
                    color=discord.Color.gold(),
                    timestamp=discord.utils.utcnow(),
                    description='You have no favorite item.'
                ).set_footer(text=interaction.user.name, icon_url=interaction.user.display_avatar.url)
            )
        else:
            res.sort(key = lambda x: x['damage'] + x['armor'],reverse=True)
            entries = utils.pager(res, 5)
            pages = []
            for items in entries:
                e = discord.Embed(
                    title='Protected items ({})'.format(len(res)),
                    color=discord.Color.gold(),
                    timestamp=discord.utils.utcnow(),
                ).set_footer(text=interaction.user.name, icon_url=interaction.user.display_avatar.url)
                for item in items:
                    e.add_field(
                        name=item['name'],
                        value='{val:.0f} {type} | ID: {id}'.format(
                            id=item['id'], type=item['type'],
                            val=item['damage'] + item['armor']
                        ),
                        inline=False
                    )
                pages.append(e)
            await Paginator(
                extras=pages,
                text=' '.join([i for i in message if i is not None])
            ).paginate(interaction)

    @app_commands.describe(sort='Leaderboard category', limit='Limit')
    @app_commands.rename(sort='leaderboard')
    @app_commands.choices(sort=[
            app_commands.Choice(value='xp', name='XP'),
            app_commands.Choice(value='e', name='Money'),
            app_commands.Choice(value='adv', name='Adventures completed'),
            app_commands.Choice(value='deaths', name='Adventures failed'),
            app_commands.Choice(value='pvp', name='PvP wins'),
            app_commands.Choice(value='ls', name='Lovescore'),
            app_commands.Choice(value='f', name='Favor'),
            app_commands.Choice(value='atkm', name='Damage multiplier'),
            app_commands.Choice(value='defm', name='Defense multiplier'),
            app_commands.Choice(value='c', name='Common crates'),
            app_commands.Choice(value='u', name='Uncommon crates'),
            app_commands.Choice(value='r', name='Rare crates'),
            app_commands.Choice(value='m', name='Magic crates'),
            app_commands.Choice(value='l', name='Legendary crates'),
            app_commands.Choice(value='my', name='Mystery crates'),
        ])
    @app_commands.command(name='leaderboard')
    async def _app_leaderboard(self, interaction: discord.Interaction, sort: str, limit: app_commands.Range[int, 5, 100] = 100):
        '''
        Get top players (up to top 100)
        '''
        await interaction.response.defer(thinking=True)
        sort_by = {
            'xp': ['xp.desc', 'XP', 'xp'],
            'e': ['money.desc,xp&money=gt.0', 'Money', 'money'],
            'adv': ['completed.desc,xp', 'Adventures Completed', 'completed'],
            'deaths': ['deaths.desc,xp', 'Adventures Failed', 'deaths'],
            'pvp': ['pvpwins.desc,xp', 'Pvp Wins', 'pvpwins'],
            'ls': ['lovescore.desc,xp&lovescore=gt.0', 'Lovescore', 'lovescore'],
            'f': ['favor.desc,xp&favor=gt.0', 'Favor', 'favor'],
            'atkm': ['atkmultiply.desc,xp', 'Damage multiplier', None],
            'defm': ['defmultiply.desc,xp', 'Defense multiplier', None],
            'c': ['crates_common.desc,xp&crates_common=gt.0', 'Common Crates', 'crates_common'],
            'u': ['crates_uncommon.desc,xp&crates_uncommon=gt.0', 'Uncommon Crates', 'crates_uncommon'],
            'r': ['crates_rare.desc,xp&crates_rare=gt.0', 'Rare Crates', 'crates_rare'],
            'm': ['crates_magic.desc,xp&crates_magic=gt.0', 'Magic Crates', 'crates_magic'],
            'l': ['crates_legendary.desc,xp&crates_legendary=gt.0', 'Legendary Crates', 'crates_legendary'],
            'my': ['crates_mystery.desc,xp&crates_mystery=gt.0', 'Mystery Crates', 'crates_mystery'],
        }
        if sort in sort_by:
            (res, status) = await self.bot.idle_query(idle.queries['leaderboard'].format(order=sort_by[sort][0]), interaction)
            if status == 429:
                raise errors.TooManyRequests(interaction)
            elif not res:
                return await interaction.followup.send('An error has occurred while trying to fetch data from the server.')
            else:
                for i in res:
                    raider = utils.get_class_bonus('rdr', i)
                    if raider:
                        i['atkmultiply'] += raider/10
                        i['defmultiply'] += raider/10
                    if i['guild'] in idle.max_raid_building:
                        i['atkmultiply'] += 1
                        i['defmultiply'] += 1
                rs = ['atkm', 'defm']
                if sort in rs:
                    rss = ['atkmultiply', 'defmultiply']
                    res.sort(key=lambda x: x['xp'])
                    res.sort(key=lambda x: x[rss[1 - rs.index(sort)]], reverse=True)
                    res.sort(key=lambda x: x[rss[rs.index(sort)]], reverse=True)
                res = res[:limit]
                def parser(p):
                    if p['guild'] > 0:
                        guild_id = str(p['guild'])
                        guild_text = f'Guild: {self.bot.idle_guilds[guild_id][0]} ({guild_id})' if guild_id in self.bot.idle_guilds else f'**Guild ID:** {guild_id}'
                    else:
                        guild_text = None
                    return '\n'.join([i for i in [
                        '**{name}** by <@{id}>'.format(
                            name=discord.utils.escape_markdown(p['name']),
                            id=p['user']
                        ),
                        'Level: {level} | Classes: {classes}'.format(
                            level=utils.getlevel(p['xp']),
                            classes=' - '.join(p['class'])
                        ),
                        guild_text,
                        '{quality}'.format(
                            quality=(
                                'Raidstats: {:.1f}/{:.1f}'.format(p['atkmultiply'], p['defmultiply'])
                                if sort in rs
                                else '{label}: {value:,d}'.format(label=sort_by[sort][1], value=p[sort_by[sort][2]])
                            )
                        )
                    ] if i is not None])
                await Paginator(
                    title='IdleRPG Leaderboard by {}'.format(sort_by[sort][1]),
                    entries=res,
                    parser=lambda x: str(res.index(x) + 1) + '. ' + parser(x) + '\n',
                    length=5
                ).paginate(interaction)
        else:
            pass

    @app_commands.describe(inactive='Only fetch inactive members (default to True)')
    @app_commands.command(name='activity')
    async def _app_activity(self, interaction: discord.Interaction, inactive: bool = True):
        '''
        Get adventure activity of guild members.
        '''
        await self._get_activity(interaction, inactive)

    @app_commands.describe(
        maxprice='Max buying price ($500 by default)', minprice='Min buying price', level='Trade building level (10 by default)',
        minid='Ignore market entries with this ID or higher', profit='Get at least this much profit upon merching'
    )
    @app_commands.rename(
        maxprice='max_price', minprice='min_price', minid='ignore_id'
    )
    @app_commands.command(name='cheap')    
    async def _app_cheap(
        self, interaction: discord.Interaction,
        maxprice: app_commands.Range[int, 1] = 500, minprice: app_commands.Range[int, 1] = 1,
        level: app_commands.Range[int, 1, 10] = 10, minid: Optional[app_commands.Range[int, 0]] = None, profit: app_commands.Range[int, 0] = 1
    ):
        '''
        Get a list of items on the market that yields profit when merching
        '''
        await interaction.response.defer(thinking=True)
        (res, status) = await self.bot.idle_query(
            idle.queries['cheap'].format(
                id='' if minid is None else '&id=lt.{}'.format(str(minid)), max=maxprice, min=minprice
            ),
            interaction
        )
        if status == 429:
            raise errors.TooManyRequests(interaction)
        elif not res:
            return await interaction.followup.send('An error has occurred while trying to fetch data from the server.')
        else:
            merch_multiplier = 1 + 0.5 * level
            shoppinglist = [i for i in res if int(i['allitems']['value'] * merch_multiplier) - i['price'] >= profit]
            total = sum([i['price'] for i in shoppinglist])
            vals = sum([i['allitems']['value'] * merch_multiplier for i in shoppinglist])
            footer_text = '{} items scanned - Last entry ID: {}'.format(len(res), res[-1]['id'] if len(res) > 0 else 'None')
            if len(shoppinglist) == 0:
                return await interaction.followup.send(
                    embed=discord.Embed(
                        title='Cheap item list',
                        description='No item found.',
                        timestamp=discord.utils.utcnow(),
                        color=discord.Color.dark_red()
                    ).set_footer(text=footer_text, icon_url=interaction.user.display_avatar.url)
                )
            else:
                print(interaction.user, vals - total)
                shoppinglist.sort(key=lambda x: int(x['allitems']['value'] * merch_multiplier) - x['price'], reverse=True)
                await Paginator(
                    title='Cheap item list',
                    entries=shoppinglist,
                    parser=lambda x: '__**{stats} {type}**__\nBuy: **{price}** \u2192 Sell: **{val}**\n```$buy {id}```'.format(
                        stats=int(x['allitems']['damage'] + x['allitems']['armor']),
                        type=x['allitems']['type'],
                        price=x['price'],
                        val=int(x['allitems']['value'] * merch_multiplier),
                        id=x['item']
                    ),
                    length=5,
                    footer=footer_text
                ).paginate(interaction)
                if interaction.user.id == self.bot.owner.id:  # type: ignore
                    allids = [i['item'] for i in shoppinglist]
                    f = discord.File(
                        filename='{}-{}-{}.txt'.format(total, len(res), res[-1]['id']),
                        fp=BytesIO(pformat(allids).encode())
                    )
                    await self.bot.owner.send(file=f)  # type: ignore

    @app_commands.choices(
        order=[app_commands.Choice(value=k, name=v) for k, v in idle.sort_strength.items()]
    )
    @app_commands.command(name='strength')
    async def _app_strength(self, interaction: discord.Interaction, order: str = 'str'):
        '''
        Get guild member's ranking in strength
        '''
        await interaction.response.defer(thinking=True)
        gid = await self.bot.pool.fetchval('SELECT guild FROM profile3 WHERE uid=$1', interaction.user.id)
        if gid is None or gid not in idle.weapon_fetching_guilds:
            return await interaction.followup.send('Your data has not been updated.')
        (res, status) = await self.bot.idle_query(idle.queries['guild'].format(id=gid, custom='name,xp,race,class,atkmultiply,defmultiply'), interaction)
        if status == 429:
            raise errors.TooManyRequests(interaction)
        elif status != 200 or res is None:
            return await interaction.followup.send('An error has occurred while trying to fetch data from the server (Code {}).'.format(status))
        elif len(res) == 0:
            return await interaction.followup.send('This guild no longer exists.')
        else:
            users = []
            for i in res:
                p = await Profile.get_profile(self.bot, data=i)
                users.append([p, *p.fighter_data()])
            users.sort(key=lambda x: x[0].xp, reverse=True)
            if order == 'pvp' or order == 'def':
                users.sort(key=lambda x: x[1], reverse=True)
                users.sort(key=lambda x: x[2], reverse=True)
                if order == 'pvp': users.sort(key=lambda x: x[1] + x[2], reverse=True)
            if order == 'atk':
                users.sort(key=lambda x: x[2], reverse=True)
                users.sort(key=lambda x: x[1], reverse=True)
            if order in ['ratk', 'str']:
                users.sort(key=lambda x: round(x[2] * x[4], 1), reverse=True)
                users.sort(key=lambda x: round(x[1] * x[3], 1), reverse=True) if order == 'ratk' else users.sort(key=lambda x: round(x[1] * x[3] + x[2] * x[4], 1), reverse=True)
            if order == 'rdef':
                users.sort(key=lambda x: round(x[1] * x[3], 1), reverse=True)
                users.sort(key=lambda x: round(x[2] * x[4], 1), reverse=True)
            if order == 'atkm':
                users.sort(key=lambda x: x[4], reverse=True)
                users.sort(key=lambda x: x[3], reverse=True)
            if order == 'defm':
                users.sort(key=lambda x: x[3], reverse=True)
                users.sort(key=lambda x: x[4], reverse=True)
            pages = utils.pager(users, 5)
            pgs = []
            timestamp = discord.utils.utcnow()
            for page in pages:
                embed = discord.Embed(
                    title='{name} Members, Sorted by {order}'.format(
                        name=self.bot.idle_guilds[str(gid)][0],
                        order=idle.sort_strength[order]
                    ),
                    color=random.getrandbits(24),
                    timestamp=timestamp
                )
                for data in page:
                    body = 'Classes: {classes} | Raid strength: {strength}\nATK-DEF: {batk} - {bdef} | Raid Multiplier: {atkm}/{defm}\nRaidstats: {ratk} - {rdef}\nUser: <@{id}> ({id})'.format(
                        classes=' - '.join(utils.get_class(data[0].classes)),
                        batk=data[1],
                        bdef=data[2],
                        atkm=round(data[3], 1),
                        defm=round(data[4], 1),
                        ratk=round(data[3] * data[1], 1),
                        rdef=round(data[4] * data[2], 1),
                        id=data[0].user,
                        strength=round(data[1] * data[3] + data[2] * data[4], 1)
                    )
                    embed.add_field(
                        name='{name} (Lv. {level})'.format(name=data[0].name, level=utils.getlevel(data[0].xp)),
                        value=body,
                        inline=False
                    )
                pgs.append(embed)
            await Paginator(extras=pgs).paginate(interaction)

    async def _get_profile(self, ctx: Union[commands.Context, discord.Interaction], user: Union[discord.Member, discord.User], ephemeral: bool = False):
        if isinstance(ctx, discord.Interaction):
            await ctx.response.defer(thinking=True, ephemeral=ephemeral)
            send_message = ctx.followup
            author = ctx.user
        else:
            send_message = ctx
            author = ctx.author
        weapons = await self.bot.pool.fetchval(postgres.queries['fetch_weapons'], user.id) or []
        (res, status) = await self.bot.idle_query(idle.queries['profile'].format(userid=user.id), ctx)
        if status == 429:
            raise errors.TooManyRequests(ctx)
        elif res is None:
            return await send_message.send('An error has occurred while trying to fetch data from the server.')
        elif len(res) == 0:
            return await send_message.send('The provided user does not have a profile.')
        else:
            p = Profile(data=res[0])
            await p.update_profile(self.bot)
            embed = embeds.profile(self.bot, res[0], weapons)
            embed.set_footer(text=(embed.footer.text or author.name), icon_url=author.display_avatar.url)
            return await send_message.send(embed=embed)

    async def _get_equipped(self, ctx: Union[commands.Context, discord.Interaction], user: Union[discord.Member, discord.User], ephemeral: bool = False):
        if isinstance(ctx, discord.Interaction):
            await ctx.response.defer(thinking=True, ephemeral=ephemeral)
            send_message = ctx.followup
            author = ctx.user
        else:
            send_message = ctx
            author = ctx.author
        start_time = datetime.datetime.now()
        equipped_items, _, _ = await self.bot.get_equipped(user.id, ctx)
        delay = round((datetime.datetime.now() - start_time)/datetime.timedelta(microseconds=1000))
        if len(equipped_items) == 0:
            return await send_message.send('The provided user does not have any item equipped.')
        else:
            embed = discord.Embed(
                title=f"{user}'s equipped items:",
                color=random.getrandbits(24)
            ).set_footer(text=author.name + f' | {delay}ms', icon_url=author.display_avatar.url)
            for item in equipped_items:
                itemtype = 'Armor' if item["armor"] > 0 else 'Damage'
                embed.add_field(
                    name=item['name'], 
                    value=(
                        f'{itemtype}: {int(item["armor"] + item["damage"])}\n'
                        f'Type: {item["type"]}\n'
                        f'ID: {item["id"]}\n'
                        f'{("Signature: " + item["signature"]) if item["signature"] else ""}'
                    ), 
                    inline=True
                )
            return await send_message.send(embed=embed)

    async def _get_item(self, ctx: Union[commands.Context, discord.Interaction], iid: int):
        if isinstance(ctx, discord.Interaction):
            await ctx.response.defer(thinking=True)
            send_message = ctx.followup
            author = ctx.user
        else:
            send_message = ctx
            author = ctx.author
        (res, status) = await self.bot.idle_query(idle.queries['item'].format(id=iid), ctx)
        if status == 429:
            raise errors.TooManyRequests(ctx)
        elif res is None:
            return await send_message.send('An error has occurred while trying to fetch data from the server.')
        elif len(res) == 0:
            return await send_message.send('Cannot find the item with that ID.')
        else:
            embed = embeds.items(res)
            embed.set_footer(text=(embed.footer.text or author.name), icon_url=author.display_avatar.url)
            return await send_message.send(embed=embed)

    async def _get_guild(self, ctx: Union[commands.Context, discord.Interaction], gid: int):
        if isinstance(ctx, discord.Interaction):
            await ctx.response.defer(thinking=True)
            send_message = ctx.followup
            author = ctx.user
        else:
            send_message = ctx
            author = ctx.author
        (res, status) = await self.bot.idle_query(idle.queries['guild'].format(id=gid, custom=','.join(idle.crates)), ctx)
        if status == 429:
            raise errors.TooManyRequests(ctx)
        elif res is None:
            return await send_message.send('An error has occurred while trying to fetch data from the server.')
        elif len(res) == 0:
            return await send_message.send('Cannot find the guild with that ID.')
        else:
            money, crate_count, g, officers = 0, [0, 0, 0, 0, 0, 0], {}, []
            for i in res:
                money += i['money']
                for j in range(6): crate_count[j] += i[idle.crates[j]]
                if i['guildrank'] == 'Officer': officers.append(i['user'])
                if i['guild_leader_fkey']: g = i['guild_leader_fkey'][0]
            update_guild = {
                str(g['id']): json.dumps([g['name'], g['leader'], g['alliance']['id']])
            }
            if g['id'] != g['alliance']['id']:
                i = g['alliance']
                self.bot.idle_guilds[str(i['id'])] = [i['name'], i['leader'], i['alliance']]
                update_guild[str(g['alliance']['id'])] = json.dumps([g['alliance']['name'], g['alliance']['leader'], g['alliance']['id']])
            if len(update_guild) > 0: await self.bot.redis.hset('guilds', mapping=update_guild)  # type: ignore
            embed = embeds.guild(g, len(res), officers, [money] + crate_count, [self.bot.crates, 'c', 'u', 'r', 'm', 'l', 'my'])
            embed.set_footer(text=(embed.footer.text or author.name), icon_url=author.display_avatar.url)
            return await send_message.send(embed=embed)

    async def _get_alliance(self, ctx: Union[commands.Context, discord.Interaction], aid: int):
        if isinstance(ctx, discord.Interaction):
            await ctx.response.defer(thinking=True)
            send_message = ctx.followup
            author = ctx.user
        else:
            send_message = ctx
            author = ctx.author
        alliance = self.bot.idle_guilds[str(aid)][2] if str(aid) in self.bot.idle_guilds and len(self.bot.idle_guilds[str(aid)]) == 3 else aid
        (res, status) = await self.bot.idle_query(idle.queries['alliance'].format(gid=aid, aid=alliance), ctx)
        if status == 429:
            raise errors.TooManyRequests(ctx)
        elif res is None:
            return await send_message.send('An error has occurred while trying to fetch data from the server.')
        elif len(res) == 0:
            return await send_message.send('Cannot find the guild with that ID.')
        elif len(res) == 1 and res[0]['id'] != res[0]['alliance']:
            (res, status) = await self.bot.idle_query(idle.queries['alliance'].format(gid=res[0]['alliance'], aid=res[0]['alliance']), ctx)
            if status == 429:
                raise errors.TooManyRequests(ctx)
            elif not res or len(res) == 0:
                return await send_message.send('An error has occurred while trying to fetch data from the server.')
        else:
            g = discord.utils.find(lambda x: x['id'] == aid, res)
            if g is not None and g['alliance'] != int(alliance):
                (res, status) = await self.bot.idle_query(idle.queries['alliance'].format(gid=g['alliance'], aid=g['alliance']), ctx)
                if status == 429:
                    raise errors.TooManyRequests(ctx)
                elif not res or len(res) == 0:
                    return await send_message.send('An error has occurred while trying to fetch data from the server.')
        guilds = []
        update_guild = {}
        for i in res:
            if i['id'] == i['alliance']: guilds.insert(0, i)
            else: guilds.append(i)
            self.bot.idle_guilds[str(i['id'])] = [i['name'], i['leader'], i['alliance']]
            update_guild[str(i['id'])] = json.dumps([i['name'], i['leader'], i['alliance']])
        if len(update_guild) > 0: await self.bot.redis.hset('guilds', mapping=update_guild)
        embed = embeds.alliance(guilds)
        embed.set_footer(text=(embed.footer.text or author.name), icon_url=author.display_avatar.url)
        return await send_message.send(embed=embed)

    async def _get_query(self, ctx: Union[commands.Context, discord.Interaction], query: str):
        if isinstance(ctx, discord.Interaction):
            await ctx.response.defer(thinking=True)
            send_message = ctx.followup
            author = ctx.user
        else:
            send_message = ctx
            author = ctx.author
        if len(query) > 0 and query.startswith(idle.QUERY_PREFIX): query = query[len(idle.QUERY_PREFIX):]
        (res, status) = await self.bot.idle_query(query, ctx)
        if status == 429:
            raise errors.TooManyRequests(ctx)
        elif status != 200 or res is None:
            return await send_message.send('An error has occurred while trying to fetch data from the server (Code {}).'.format(status))
        else:
            endpoint = query[:query.index('?')] if len(query) > 0 and '?' in query else 'query'
            get_embed = len(query) > 0 and ('select=' not in query or 'select=*' in query) and '?' in query
            await send_message.send(
                '{0} entries found.'.format((len(res))),
                file=discord.File(
                    filename='{}.txt'.format(endpoint),
                    fp=BytesIO(pformat(res).encode())
                )
            )
            if get_embed and len(res):
                pages = []
                def get_pages(data, embed_builder):
                    embed = embed_builder(data)
                    embed.set_footer(text=(embed.footer.text or author.name), icon_url=author.display_avatar.url)
                    pages.append(embed)
                if endpoint == 'profile':
                    for i in res:
                        weapons = await self.bot.pool.fetchval(postgres.queries['fetch_weapons'], i['user']) or []
                        embed = embeds.profile(self.bot, i, weapons)
                        embed.set_footer(text=(embed.footer.text or author.name), icon_url=author.display_avatar.url)
                        pages.append(embed)
                elif endpoint == 'allitems':
                    entries = utils.pager(res, 5)
                    for i in entries:
                        get_pages(i, embeds.items)
                elif endpoint == 'guild':
                    update_guild = {}
                    for i in res:
                        if str(i['id']) not in update_guild:
                            self.bot.idle_guilds[str(i['id'])] = [i['name'], i['leader'], i['alliance']]
                            update_guild[str(i['id'])] = json.dumps([i['name'], i['leader'], i['alliance']])
                        if len(update_guild) > 0:
                            await self.bot.redis.hset('guilds', mapping=update_guild)
                        get_pages(i, embeds.guild)
                elif endpoint == 'pets':
                    for i in res:
                        get_pages(i, embeds.pet)
                elif endpoint == 'children':
                    entries = utils.pager(res, 6)
                    for i in entries:
                        get_pages(i, embeds.children)
                elif endpoint == 'loot':
                    entries = utils.pager(res, 6)
                    for i in entries:
                        get_pages(i, embeds.loot)
                if len(pages) == 1:
                    await send_message.send(embed=pages[0])
                else:
                    return await Paginator(extras=pages, text='{0} entries found.'.format(len(res))).paginate(ctx)

    async def _get_raidstats(self, ctx: Union[commands.Context, discord.Interaction], start: float, end: float):
        if isinstance(ctx, discord.Interaction): await ctx.response.defer(thinking=True)
        start += 0.1
        total, res = 0, []
        for i in range(int(10 * start), int(10 * end) + 1):
            cost = sum(j * 25000 for j in range(1, i - 9))
            total += cost
            res.append((round(i/10,1), cost))
        return await Paginator(
            entries=res,
            parser=lambda x: str(round(x[0]-0.1,1)).rjust(4) + ' \u2192 ' + str(round(x[0],1)).rjust(4) + ' : ' + ('$' + intcomma(x[1])).rjust(15),
            title='Raidstats price',
            codeblock=True,
            length=10,
            footer=f'Total cost: ${intcomma(total)}',
            color=random.getrandbits(24)
        ).paginate(ctx)

    async def _get_xp(self, ctx: Union[commands.Context, discord.Interaction], target: Optional[Union[discord.User, int]], ephemeral: bool = False):
        if isinstance(ctx, discord.Interaction):
            await ctx.response.defer(thinking=True, ephemeral=ephemeral)
            send_message = ctx.followup
            user = ctx.user
        else:
            send_message = ctx
            user = ctx.author
        if target is None:
            level_table = []
            for i in range(0, len(idle.levels)):
                level_table += [
                    'Level {}'.format((i+1)).ljust(12) + ('Beginner' if i == 0 else intcomma(idle.levels[i])).rjust(12)
                ]
            return await Paginator(
                title='Level table',
                entries=level_table,
                length=10,
                codeblock=True,
                color=random.getrandbits(24)
            ).paginate(ctx)
        elif isinstance(target, (discord.Member, discord.User)):
            user = target
            (res, status) = await self.bot.idle_query(idle.queries['xp'].format(id=user.id), ctx)
            if status == 429:
                raise errors.TooManyRequests(ctx)
            elif status != 200 or res is None:
                return await send_message.send('An error has occurred while trying to fetch data from the server.')
            elif len(res) == 0:
                return await send_message.send('{} does not have a profile.'.format(user.mention))
            else:
                value = res[0]['xp']
        else:
            value = target
        lvl = utils.getlevel(value)
        embed = discord.Embed(
            title=f'XP statistics (Lv. {lvl})',
            color=random.getrandbits(24),
            timestamp=discord.utils.utcnow()
        ).set_footer(
            text=user.name, icon_url=user.display_avatar.url
        )
        if lvl < 25:
            embed.add_field(
                name='To {}'.format('next evolution' if lvl > 11 else 'second class'),
                value='{} XP\n{} lv1 adv (375 XP/adv)\n{} days (48 a1s/day)'.format(
                    intcomma(a := utils.getnextevol(value)), intcomma(b:= a / 375, 2), intcomma(b / 48, 2) # type: ignore
                )
            )
        if lvl < 29:
            embed.insert_field_at(0,
                name='To next level',
                value='{} XP\n{} lv1 adv (375 XP/adv)\n{} days (48 a1s/day)'.format(
                    intcomma(a := utils.getnextlevel(value)), intcomma(b:= a / 375, 2), intcomma(b / 48, 2) # type: ignore
                )
            )
        if lvl < 30:
            embed.add_field(
                name='To level 30',
                value='{} XP\n{} lv1 adv (375 XP/adv)\n{} days (48 a1s/day)'.format(
                    intcomma(a := utils.getto30(value)), intcomma(b:= a / 375, 2), intcomma(b / 48, 2)
                )
            )
        else:
            embed.description = 'Already at max level.'
        await send_message.send(embed=embed)

    async def _get_missions(self, ctx: Union[commands.Context, discord.Interaction], user: Union[discord.Member, discord.User], level: Optional[int], booster: bool, building: int):
        if isinstance(ctx, discord.Interaction):
            await ctx.response.defer(thinking=True)
            send_message = ctx.followup
            author = ctx.user
            bot = ctx.client
        else:
            send_message = ctx
            author = ctx.author
            bot = ctx.bot
        try:
            equipped, profile, _ = await self.bot.get_equipped(user.id, ctx, True)
        except errors.ApiIsDead:
            profile, equipped = {}, []
        if profile is not None:
            p = Profile(data=profile, weapons=equipped)
            def calcchance(lvl):
                chances = utils.adv_success(p, lvl, booster, building)
                if chances is None: return None
                chances.sort()
                chance = 0
                for c in chances:
                    if c >= 100:
                        chance += 1
                    elif c >= 0:
                        chance += (c+1)/101
                return [chances, round(100 * chance / len(chances), 2)]
            if level:
                chance = calcchance(level)
                time = datetime.timedelta(hours=level * (1 - building / 100))
                if chance is not None:
                    descriptions = '\n'.join([
                        ', '.join(map(lambda x: f'{x}', chance[0][i:i+5])) for i in range(0,len(chance[0]), 5)
                    ])
                    embed = discord.Embed(
                        title='Adventure {} - {}'.format(level, idle.adventures[level - 1]),
                        description=(
                            f'For the adventure to succeed, a random number between `[0, 100]` '
                            f'picked by the bot has to be less than or equal to one of these numbers:'
                            f'```\n{descriptions}\n```'
                            f'The chance of that happening is: {chance[1]}%'
                        ),
                        color=random.getrandbits(24),
                        timestamp=discord.utils.utcnow()
                    ).set_footer(
                        text=user.name, icon_url=author.display_avatar.url
                    ).add_field(
                        name='Duration', value='\n'.join([
                            'Regular player: *{}* (*{}* with time booster)'.format(precisedelta(time, suppress=['days']), precisedelta(time * 0.5, suppress=['days'])),
                            'Silver donator: *{}* (*{}* with time booster)'.format(precisedelta(time * 0.95, suppress=['days']), precisedelta(time * 0.5 * 0.95, suppress=['days'])),
                            'Gold donator: *{}* (*{}* with time booster)'.format(precisedelta(time * 0.9, suppress=['days']), precisedelta(time * 0.5 * 0.9, suppress=['days'])),
                            'Emerald donator: *{}* (*{}* with time booster)'.format(precisedelta(time * 0.75, suppress=['days']), precisedelta(time * 0.5 * 0.75, suppress=['days'])),
                        ]),
                    )
                    return await send_message.send(embed=embed)
                else:
                    embed = discord.Embed(
                        title='Adventure {} - {}'.format(level, idle.adventures[level - 1]),
                        description='The bot might crash if you attempt to finish this adventure while your luck is 0.0',
                        color=random.getrandbits(24),
                        timestamp=discord.utils.utcnow()
                    ).set_footer(
                        text=user.name, icon_url=author.display_avatar.url
                    ).add_field(
                        name='Duration', value='\n'.join([
                            'Regular player: *{}* (*{}* with time booster)'.format(precisedelta(time, suppress=['days']), precisedelta(time * 0.5, suppress=['days'])),
                            'Silver donator: *{}* (*{}* with time booster)'.format(precisedelta(time * 0.95, suppress=['days']), precisedelta(time * 0.5 * 0.95, suppress=['days'])),
                            'Gold donator: *{}* (*{}* with time booster)'.format(precisedelta(time * 0.9, suppress=['days']), precisedelta(time * 0.5 * 0.9, suppress=['days'])),
                            'Emerald donator: *{}* (*{}* with time booster)'.format(precisedelta(time * 0.75, suppress=['days']), precisedelta(time * 0.5 * 0.75, suppress=['days'])),
                        ]),
                    )
                    return await send_message.send(embed=embed)
            else:
                all_adventures = []
                for i in range(len(idle.adventures)):
                    c = calcchance(i+1)
                    if c is not None: all_adventures += [
                        '\n'.join([
                            '**Adventure {}** - {}'.format(i+1, idle.adventures[i]),
                            'Duration: *{}*'.format(precisedelta(datetime.timedelta(hours=(i+1) * (1 - building / 100)), suppress=['days'])),
                            'Success range: *{}% - {}%*'.format(min(c[0]), max(c[0])),
                            'Success chance: {}%'.format(c[1]),
                            ''
                        ])
                    ]
                async def customnav(ctx):
                    def valid(msg):
                        if msg.guild and msg.channel.id == ctx.channel.id and msg.author.id == author.id and msg.content.isdecimal():
                            pg = int(msg.content)
                            return pg >= 1 and pg <= 30
                        return False
                    prompt = await ctx.channel.send('Select a mission level')
                    try:
                        jumpto = await bot.wait_for('message', check=valid, timeout=15)
                    except asyncio.TimeoutError:
                        await prompt.delete()
                        msg = await ctx.channel.send('You did not enter a valid level.')
                        await msg.delete(delay=10)
                        return None
                    await prompt.delete()
                    pnum = (int(jumpto.content) - 1) // 5
                    await jumpto.delete()
                    return pnum
                return await Paginator(
                    title='{}\'s success chance'.format(user.name),
                    entries=all_adventures,
                    length=5,
                    color=random.getrandbits(24),
                    customnav=customnav
                ).paginate(ctx)
        else:
            all_adventures = []
            for i in range(len(idle.adventures)):
                all_adventures += ['\n'.join([
                    '**Adventure {}** - {}'.format(i+1, idle.adventures[i]),
                    'Duration: *{}*'.format(precisedelta(datetime.timedelta(hours=(i+1) * (1 - building / 100)), suppress=['days'])),
                    '',
                ])]
            async def customnav(ctx):
                def valid(msg):
                    if msg.guild and msg.channel.id == ctx.channel.id and msg.author.id == author.id and msg.content.isdecimal():
                        pg = int(msg.content)
                        return pg >= 1 and pg <= 30
                    return False
                prompt = await ctx.channel.send('Select a mission level')
                try:
                    jumpto = await bot.wait_for('message', check=valid, timeout=15)
                except asyncio.TimeoutError:
                    await prompt.delete()
                    msg = await ctx.channel.send('You did not enter a valid level.')
                    await msg.delete(delay=10)
                    return None
                await prompt.delete()
                pnum = (int(jumpto.content) - 1) // 5
                await jumpto.delete()
                return pnum
            return await Paginator(
                title='{}\'s success chance'.format(user.name),
                entries=all_adventures,
                length=5,
                color=random.getrandbits(24),
                customnav=customnav
            ).paginate(ctx)

    async def _get_activity(self, ctx: Union[commands.Context, discord.Interaction], inactive: bool, gid = None):
        if isinstance(ctx, discord.Interaction):
            await ctx.response.defer(thinking=True)
            send_message = ctx.followup
            user = ctx.user
        else:
            send_message = ctx
            user = ctx.author
        gid = gid or await self.bot.pool.fetchval('SELECT guild FROM profile3 WHERE uid=$1', user.id)
        if gid is None or gid not in idle.weapon_fetching_guilds:
            return await send_message.send('Your data has not been updated.')
        (res, status) = await self.bot.idle_query(idle.queries['guild'].format(id=gid, custom='xp,completed,deaths'), ctx)
        if status == 429:
            raise errors.TooManyRequests(ctx)
        elif status != 200 or res is None:
            return await send_message.send('An error has occurred while trying to fetch data from the server (Code {}).'.format(status))
        elif len(res) == 0:
            return await send_message.send('This guild no longer exists.')
        else:
            timestamp = discord.utils.utcnow()
            data = [[i['user'], i['xp'], i['completed'] + i['deaths'], None] for i in res]
            for line in data:
                activity_data = await self.bot.pool.fetchval(postgres.queries['get_activity'], line[0])
                if activity_data is not None:
                    line[1], line[2], line[3] = line[1] - activity_data[0], line[2] - activity_data[1], activity_data[2]
            active_members = [u for u in data if u[3] and not u[1] + u[2] == 0 and u[3].year != 1970]
            idle_members = [u for u in data if u[3] and u[1] + u[2] == 0 and u[3] + datetime.timedelta(days=3) > discord.utils.utcnow()]
            inactive_members = [u for u in data if u[3] and u[1] + u[2] == 0 and u[3] + datetime.timedelta(days=3) <= discord.utils.utcnow() and u[3].year != 1970]
            new_members = [u for u in data if (not u[3] or u[3].year == 1970)]
            active_list, idle_list, added_list, pages = [], [], [], []
            inactive_members.sort(key=lambda x: x[3])
            inactive_list = utils.pager(inactive_members, 10)
            if not inactive:
                active_members.sort(key=lambda x: x[1], reverse=True)
                active_list = utils.pager(active_members, 10)
                idle_members.sort(key=lambda x: x[3])
                idle_list = utils.pager(idle_members, 10)
                added_list = utils.pager(new_members, 10)
            for i in active_list:
                embed = discord.Embed(
                    title='{} active members ({})'.format(self.bot.idle_guilds[str(gid)][0], len(active_members)),
                    description='\n'.join([
                        '<@{user}>{member} gained {xp}XP after {adv} adventure(s) since <t:{time}:R> {avg}'.format(
                            user=line[0],
                            member='' if (m:=ctx.guild.get_member(int(line[0]))) is None else ' ({}#{})'.format(m.name, m.discriminator),  # type: ignore
                            xp=intcomma(line[1]),
                            adv=line[2],
                            time=int(line[3].timestamp()),
                            avg = '' if line[2] == 0 else '\n> ({}XP/adventure)'.format(intcomma(round(line[1]/line[2])))
                        ) for line in i
                    ]),
                    timestamp=timestamp,
                    color=0x70ff96
                )
                pages.append(embed)
            for i in idle_list:
                embed = discord.Embed(
                    title='{} idle members ({})'.format(self.bot.idle_guilds[str(gid)][0], len(idle_members)),
                    description='\n'.join([
                        '<@{}>{} has not finished any adventure since <t:{}:R>.'.format(
                            line[0],
                            '' if (m:=ctx.guild.get_member(int(line[0]))) is None else ' ({}#{})'.format(m.name, m.discriminator),  # type: ignore
                            int(line[3].timestamp())
                        ) for line in i
                    ]),
                    timestamp=timestamp,
                    color=0xf5bf42
                )
                pages.append(embed)
            for i in inactive_list:
                embed = discord.Embed(
                    title='{} inactive members ({})'.format(self.bot.idle_guilds[str(gid)][0], len(inactive_members)),
                    description='\n'.join([
                        '<@{}>{} has not finished any adventure since <t:{}:R>.'.format(
                            line[0],
                            '' if (m:=ctx.guild.get_member(int(line[0]))) is None else ' ({}#{})'.format(m.name, m.discriminator),  # type: ignore
                            int(line[3].timestamp())
                        ) for line in i
                    ]),
                    timestamp=timestamp,
                    color=0xba1111
                )
                pages.append(embed)
            for i in added_list:
                embed = discord.Embed(
                    title='{} new members ({})'.format(self.bot.idle_guilds[str(gid)][0], len(new_members)),
                    description='\n'.join(['<@{}>\'s data is less than 2 days old.'.format(line[0]) for line in i]),
                    timestamp=timestamp,
                    color=0x57fff1
                )
                pages.append(embed)
            return await Paginator(extras=pages).paginate(ctx)

async def setup(bot):
    await bot.add_cog(General(bot))