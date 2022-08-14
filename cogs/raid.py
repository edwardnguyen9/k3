import discord
from discord import app_commands
from discord.ext import commands, tasks

from assets import raid

class Raid(commands.GroupCog, group_name='raid'):
    def __init__(self, bot):
        self.bot = bot
        self.is_first_ready = True

    @commands.Cog.listener()
    async def on_ready(self):
        if self.is_first_ready:
            await self.bot.loading()
            print(self.__class__.__name__, 'is ready')
            self.is_first_ready = False


async def setup(bot):
    await bot.add_cog(Raid(bot))