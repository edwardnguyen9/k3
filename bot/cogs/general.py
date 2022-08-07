from discord.ext import commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_first_ready = True

    @commands.Cog.listener()
    async def on_ready(self):
        if self.is_first_ready:
            self.bot.command_prefix = self.bot._get_prefix
            print(self.__class__.__name__, 'is ready')
            self.is_first_ready = False

    @commands.hybrid_command(name='test')
    async def test(self, ctx):
        print('Test called')
        await ctx.send('Hybrid command!')

    @commands.command(name='hello')
    async def hello(self, ctx):
        print('Hello called')
        await ctx.send('Hi!')

async def setup(bot):
    await bot.add_cog(General(bot))