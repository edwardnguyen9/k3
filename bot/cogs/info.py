import discord, random, datetime, json
from discord import app_commands
from discord.ext import commands
from typing import Union, Optional, Literal
from humanize import intcomma
from io import BytesIO
from pprint import pformat

from bot.assets import api, postgres  # type: ignore
from bot.classes.bot import Kiddo
from bot.classes.paginator import Paginator  # type: ignore
from bot.utils import command_config as config, errors, utils, embeds, queries  # type: ignore


class Info(commands.Cog):
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
                for i in res:
                    weapons = await self.bot.pool.fetchval(postgres.queries['fetch_weapons'], i['user']) or []
                    embed = embeds.profile(self.bot, i, weapons)
                    embed.set_footer(text=(embed.footer.text or interaction.user.name), icon_url=interaction.user.display_avatar.url)
                    pages.append(embed)
                if len(pages) == 1:
                    await interaction.followup.send(embed=pages[0])
                else:
                    pag = Paginator(extras=pages, footer='{0} entries found.'.format(len(res)))
                    return await pag.paginate(interaction)

    @app_commands.checks.has_permissions(kick_members=True)
    async def _menu_profile(self, interaction: discord.Interaction, user: discord.User):
        await self._get_profile(interaction, user, True)

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

    @app_commands.describe(user='User')
    @app_commands.command(name='equipped')
    async def _app_equipped(
        self, interaction: discord.Interaction, user: Optional[discord.User] = None,
    ):
        '''
        Get equipped item
        '''
        await self._get_equipped(interaction, user or interaction.user)

    @app_commands.checks.has_permissions(kick_members=True)
    async def _menu_equipped(self, interaction: discord.Interaction, user: discord.User):
        await self._get_equipped(interaction, user, True)

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
                    pag = Paginator(extras=pages, footer='{0} entries found.'.format(len(res)))
                    return await pag.paginate(interaction)

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
                    pag = Paginator(extras=pages, footer='{0} entries found.'.format(len(res)))
                    return await pag.paginate(interaction)

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
    
    @commands.command(
        name='funds',
        aliases=['fund'],
        brief='Get guild fund',
        description='Get all cash and crates of a guild\'s members',
        usage='<guild ID>',
        help='> <guild ID>: The ID of the guild.'
    )
    async def _fund(self, ctx: commands.Context, gid: int):
        await self._get_fund(ctx, gid)

    @app_commands.describe(gid='Guild ID')
    @app_commands.rename(gid='id')
    @app_commands.command(name='funds')
    async def _app_fund(
        self, interaction: discord.Interaction, gid: app_commands.Range[int, 0],
    ):
        '''
        Get guild funds
        '''
        await self._get_fund(interaction, gid)

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
                pag = Paginator(extras=pages, footer='{0} entries found.'.format(len(res)))
                return await pag.paginate(interaction)

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
                pag = Paginator(extras=pages, footer='{0} entries found.'.format(len(res)))
                return await pag.paginate(interaction)

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
            res = [l for l in api.loot if vmin <= l[1] <= vmax and (name is None or name.lower() in l[0].lower())]
            if len(res) == 0: return await interaction.followup.send('No loot item found.')
            if 'value' in sort:
                res.sort(key = lambda x: x[0])
                res.sort(key = lambda x: x[1], reverse = not reverse)
            else:
                res.sort(key = lambda x: x[0], reverse = not reverse)
            pag = Paginator(
                entries=res,
                title='List of loot items',
                parser=lambda x: x[0] + ', Value : ' + intcomma(x[1]),
                footer='{0} item{1} found.'.format(len(res), 's' if len(res) > 1 else ''),
                color=random.getrandbits(24)
            )
            return await pag.paginate(interaction)
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
                    pag = Paginator(extras=pages, footer='{0} entries found.'.format(len(res)))
                    return await pag.paginate(interaction)

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

    async def _get_profile(self, ctx: Union[commands.Context, discord.Interaction], user: Union[discord.Member, discord.User], ephemeral: bool = False):
        if isinstance(ctx, discord.Interaction):
            await ctx.response.defer(thinking=True, ephemeral=ephemeral)
            send_message = ctx.followup
            author = ctx.user
        else:
            send_message = ctx
            author = ctx.author
        weapons = await self.bot.pool.fetchval(postgres.queries['fetch_weapons'], user.id) or []
        (res, status) = await self.bot.idle_query(api.queries['profile'].format(userid=user.id), ctx)
        if status == 429:
            raise errors.TooManyRequests(ctx)
        elif not res or len(res) == 0:
            return await send_message.send('The provided user does not have a profile.')
        else:
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
        equipped_items = await self.bot.get_equipped(user.id, ctx)
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
        (res, status) = await self.bot.idle_query(api.queries['item'].format(id=iid), ctx)
        if status == 429:
            raise errors.TooManyRequests(ctx)
        elif not res or len(res) == 0:
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
        (res, status) = await self.bot.idle_query(api.queries['guild'].format(id=gid), ctx)
        if status == 429:
            raise errors.TooManyRequests(ctx)
        elif not res or len(res) != 1:
            return await send_message.send('Cannot find the guild with that ID.')
        else:
            g = res[0]
            update_guild = {
                str(g['id']): json.dumps([g['name'], g['leader'], g['alliance']['id']])
            }
            if g['id'] != g['alliance']['id']:
                update_guild[str(g['alliance']['id'])] = json.dumps([g['alliance']['name'], g['alliance']['leader'], g['alliance']['id']])
            if len(update_guild) > 0: await self.bot.redis.hset('guilds', mapping=update_guild)  # type: ignore
            (res2, status) = await self.bot.idle_query(api.queries['guildrank'].format(id=gid), ctx, 1)
            if status == 429 or not res2 or 'user' not in res2[0]:
                mcount, ocount = None, None
            else:
                officers = [i for i in res2 if i['guildrank'] == 'Officer']
                mcount, ocount = len(res2), len(officers)
            embed = embeds.guild(res[0], mcount, ocount)
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
        (res, status) = await self.bot.idle_query(api.queries['alliance'].format(id=aid), ctx)
        if status == 429:
            raise errors.TooManyRequests(ctx)
        elif not res or len(res) == 0:
            return await send_message.send('Cannot find the guild with that ID.')
        elif len(res) == 1 and res[0]['id'] != res[0]['alliance']:
            (res, status) = await self.bot.idle_query(api.queries['alliance'].format(id=res[0]['alliance']), ctx)
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

    async def _get_fund(self, ctx: Union[commands.Context, discord.Interaction], gid: int):
        if isinstance(ctx, discord.Interaction):
            await ctx.response.defer(thinking=True)
            send_message = ctx.followup
            author = ctx.user
        else:
            send_message = ctx
            author = ctx.author
        (res, status) = await self.bot.idle_query(api.queries['funds'].format(id=gid, crates=','.join(api.crates)), ctx)
        if status == 429:
            raise errors.TooManyRequests(ctx)
        elif not res or len(res) == 0:
            return await send_message.send('Cannot find the guild with that ID.')
        else:
            money, crate_count, guild = 0, [0, 0, 0, 0, 0, 0], {}
            for i in res:
                money += i['money']
                for j in range(6): crate_count[j] += i[api.crates[j]]
                if i['guild_leader_fkey']: guild = i['guild_leader_fkey'][0]
            await self.bot.redis.hset('guilds', str(gid), json.dumps([guild['name'], guild['leader'], guild['alliance']]))
            crates = ['c', 'u', 'r', 'm', 'l', 'my']
            embed = discord.Embed(
                title='{}\'s total funds'.format(discord.utils.escape_markdown(guild['name'])),
                color=random.getrandbits(24),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            ).add_field(
                name='**Money**',
                value='**In guild bank**\n${}\n**In member\'s accounts**\n${}\n**Total**\n${}'.format(
                    intcomma(guild['money']), intcomma(money), intcomma(guild['money'] + money)
                ),
                inline=True
            ).add_field(
                name='**Crates**',
                value='\n'.join(map(
                    lambda x: '{} {:,d}'.format(self.bot.crates[crates[x]], crate_count[x]),
                    range(len(crates))
                )),
                inline=True
            ).set_footer(text='Does not take into account: loot items, weapons, or alts', icon_url=author.display_avatar.url)
            await send_message.send(embed=embed)

    async def _get_query(self, ctx: Union[commands.Context, discord.Interaction], query):
        if isinstance(ctx, discord.Interaction):
            await ctx.response.defer(thinking=True)
            send_message = ctx.followup
            author = ctx.user
        else:
            send_message = ctx
            author = ctx.author
        if query.startswith(api.QUERY_PREFIX): query = query[len(api.QUERY_PREFIX):]
        (res, status) = await self.bot.idle_query(query, ctx)
        if status == 429:
            raise errors.TooManyRequests(ctx)
        elif status != 200 or not res:
            return await send_message.send('An error has occurred while trying to fetch data from the server.')
        else:
            endpoint = query[:query.index('?')]
            get_embed = 'select=' not in query or 'select=*' in query
            await send_message.send(
                '{0} entries found.'.format((len(res))),
                file=discord.File(
                    filename='{}.txt'.format(endpoint),
                    fp=BytesIO(pformat(res).encode())
                )
            )
            if get_embed and len(res):
                if endpoint == 'profile':
                    pass
                elif endpoint == 'allitems':
                    pass
                elif endpoint == 'guild':
                    pass
                elif endpoint == 'pets':
                    pass
                elif endpoint == 'children':
                    pass
                elif endpoint == 'loot':
                    pass

    async def _get_raidstats(self, ctx: Union[commands.Context, discord.Interaction], start: float, end: float):
        if isinstance(ctx, discord.Interaction): await ctx.response.defer(thinking=True)
        start += 0.1
        total, res = 0, []
        for i in range(int(10 * start), int(10 * end) + 1):
            cost = sum(j * 25000 for j in range(1, i - 9))
            total += cost
            res.append((round(i/10,1), cost))
        p = Paginator(
            entries=res,
            parser=lambda x: str(round(x[0]-0.1,1)).rjust(4) + ' \u2192 ' + str(round(x[0],1)).rjust(4) + ' : ' + ('$' + intcomma(x[1])).rjust(15),
            title='Raidstats price',
            codeblock=True,
            length=10,
            footer=f'Total cost: ${intcomma(total)}',
            color=random.getrandbits(24)
        )
        return await p.paginate(ctx)


async def setup(bot):
    await bot.add_cog(Info(bot))