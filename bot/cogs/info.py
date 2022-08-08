import discord
from discord import app_commands
from discord.ext import commands
from typing import Union

from bot.assets.api import queries
from bot.classes.bot import Kiddo
from bot.classes.profile import Profile
from bot.classes.paginator import Paginator  # type: ignore
from bot.utils import get, errors
from bot.utils.queries import query_profile  # type: ignore

crates = {
    'c': 834980524913197106,
    'u': 834980525298679808,
    'r': 834980525247692840,
    'm': 834980524723929109,
    'l': 834980524652363799,
    'my': 926861270680993813
}

class Info(commands.Cog):
    def __init__(self, bot: Kiddo):
        self.bot = bot
        self.is_first_ready = True
        self.ctx_menu = app_commands.ContextMenu(
            name='Profile', callback=self._menu_profile
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    @commands.Cog.listener()
    async def on_ready(self):
        if self.is_first_ready:
            await self.bot.loading()
            server = discord.utils.get(self.bot.guilds, id=475033206672850945)
            async def get_crate(bot, c):
                try:
                    return await server.fetch_emoji(crates[c])  # type: ignore
                except Exception:
                    if c == 'c': return 'Common crates'
                    elif c == 'u': return 'Uncommon crates'
                    elif c == 'r': return 'Rare crates'
                    elif c == 'm': return 'Magic crates'
                    elif c == 'l': return 'Legendary crates'
                    else: return 'Mystery crates'
            self.bot.crates = {
                'c': await get_crate(self.bot, 'c'),
                'u': await get_crate(self.bot, 'u'),
                'r': await get_crate(self.bot, 'r'),
                'm': await get_crate(self.bot, 'm'),
                'l': await get_crate(self.bot, 'l'),
                'my': await get_crate(self.bot, 'my')
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
    async def _profile(self, ctx: commands.Context, user: discord.User = None):  # type: ignore
        user = user or ctx.author
        if isinstance(user, (discord.Member, discord.User)):
            person = user
            uid = user.id
        else:
            try:
                person = await self.bot.fetch_user(user)
                uid = person.id
            except discord.NotFound:
                return await ctx.send('This user does not exist.')
        await self._get_profile(ctx, person)

    @app_commands.describe(
        user='User (override all other filters)', name='Character name',
        lvmin='Min level', lvmax='Max level', race='Character race', classes='Character class',
        emin='Min balance', emax='Max balance', ratkmin='Min raid damage multiplier', ratkmax='Max raid damage multiplier',
        rdefmin='Min raid defense multiplier', rdefmax='Max raid defense multiplier',
        pvpmin='Min PvP win count', pvpmax='Max PvP win count', spouse='Married to', lsmin='Min lovescore value', lsmax='Max lovescore value',
        god='God', luck='Luck value', fmin='Min favor', fmax='Max favor', guild='Guild', limit='Limit', sort='Order by', reverse='Reverse order'
    )
    @app_commands.rename(
        lvmin='level_min', lvmax='level_max', classes='class', emin='balance_min', emax='balance_max',
        ratkmin='damage_multiply_min', ratkmax='damage_multiply_max', rdefmin='defense_multiply_min', rdefmax='defense_multiply_max',
        pvpmin='pvp_min', pvpmax='pvp_max', lsmin='lovescore_min', lsmax='lovescore_max', fmin='favor_min', fmax='favor_max',
        sort='order_by'
    )
    @app_commands.autocomplete(classes=get.class_autocomplete)
    @app_commands.autocomplete(race=get.race_autocomplete)
    @app_commands.command(name='profile')
    async def _profile_app(
        self, interaction: discord.Interaction, user: discord.User = None,  # type: ignore
        name: str = None, lvmin: int = None, lvmax: int = None,  # type: ignore
        race: str = None, classes: str = None, emin: int = None, emax: int = None,  # type: ignore
        ratkmin: float = None, ratkmax: float = None, rdefmin: float = None, rdefmax: float = None,  # type: ignore
        pvpmin: int = None, pvpmax: int = None, spouse: discord.User = None,  # type: ignore
        lsmin: int = None, lsmax: int = None, god: str = None, luck: float = None,  # type: ignore
        fmin: int = None, fmax: int = None, guild: int = None,  # type: ignore
        limit: int = 100, sort: str = 'xp.desc,money.desc', reverse: bool = False
    ):
        '''
        Get IdleRPG profile
        '''
        if get.check_if_all_null(
            name, lvmin, lvmax, race, classes, emin, emax, ratkmin, ratkmax, rdefmin, rdefmax,
            pvpmin, pvpmax, spouse, lsmin, lsmax, god, luck, fmin, fmax, guild
        ):
            user = user or interaction.user
            await self._get_profile(interaction, user)
        else:
            await interaction.response.defer(thinking=True)
            query = query_profile(
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
                    embed = Profile.profile_embed(self.bot, i)
                    embed.set_footer(text=(embed.footer.text or interaction.user.name), icon_url=interaction.user.avatar.url)  # type: ignore
                    pages.append(embed)
                if len(pages) == 1:
                    await interaction.followup.send(embed=pages[0])
                else:
                    pag = Paginator(extras=pages, footer='{0} entries found.'.format(len(res)))
                    return await pag.paginate(interaction)

    @app_commands.checks.has_permissions(kick_members=True)
    async def _menu_profile(self, interaction: discord.Interaction, user: discord.User):
        await self._get_profile(interaction, user, True)

    async def _get_profile(self, ctx: Union[commands.Context, discord.Interaction], user: discord.User, ephemeral: bool = False):
        if isinstance(ctx, discord.Interaction):
            await ctx.response.defer(thinking=True, ephemeral=ephemeral)
            send_message = ctx.followup
            author = ctx.user
        else:
            send_message = ctx
            author = ctx.author
        (res, status) = await self.bot.idle_query(queries['profile'].format(userid=user.id), ctx)
        if status == 429:
            raise errors.TooManyRequests(ctx)
        elif not res or len(res) == 0:
            return await send_message.send('The provided user does not have a profile.', ephemeral=ephemeral)
        else:
            embed = Profile.profile_embed(self.bot, res[0])
            embed.set_footer(text=(embed.footer.text or author.name), icon_url=author.avatar.url)  # type: ignore
            return await send_message.send(embed=embed, ephemeral=ephemeral)

async def setup(bot):
    await bot.add_cog(Info(bot))