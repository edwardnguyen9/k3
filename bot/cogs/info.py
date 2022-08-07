import discord
from discord import app_commands
from discord.ext import commands

from bot.assets.api import queries
from bot.classes.bot import Kiddo
from bot.classes.profile import Profile  # type: ignore

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

    @app_commands.describe(user='User')
    @app_commands.command(name='profile')
    async def _profile(self, interaction: discord.Interaction, user: discord.User = None):  # type: ignore
        '''
        Get IdleRPG profile
        '''
        await interaction.response.defer(thinking=True)
        user = user or interaction.user
        (res, status) = await self.bot.idle_query(queries['profile'].format(userid=user.id), interaction)
        if status != 200 or not res:
            return await interaction.followup.send('An error has occurred.')
        else:
            embed = Profile.profile_embed(self.bot, res[0])
            embed.set_footer(text=(embed.footer.text or interaction.user.name), icon_url=interaction.user.avatar.url)  # type: ignore
            return await interaction.followup.send(embed=embed)

    # @discord.app_commands.describe(user='The user to fetch')
    # @commands.hybrid_command(name='profile')
    # async def _profile(self, ctx: commands.Context, user: discord.User = None):  # type: ignore
    #     if user is not None:
    #         await ctx.send(user.name, ephemeral=True)
    #     else:
    #         msg = await ctx.send('Counting', ephemeral=True)
    #         for i in range(5):
    #             await asyncio.sleep(2)
    #             await msg.edit(content=i)  # type: ignore

async def setup(bot):
    await bot.add_cog(Info(bot))