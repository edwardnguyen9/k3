from discord.ext import commands

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_first_ready = True

    @commands.Cog.listener()
    async def on_ready(self):
        if self.is_first_ready:
            self.bot.command_prefix = self.bot._get_prefix
            print(self.__class__.__name__, 'is ready')
            self.is_first_ready = False

async def setup(bot):
    await bot.add_cog(Admin(bot))