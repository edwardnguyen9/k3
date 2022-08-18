import discord
from discord.ext import commands

from classes import ui

class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_first_ready = True
        self.counter = 0

    @commands.Cog.listener()
    async def on_ready(self):
        if self.is_first_ready:
            print(self.__class__.__name__, 'is ready')
            self.is_first_ready = False

    @discord.app_commands.command()
    @discord.app_commands.guilds(475033206672850945)
    async def feedback(self, interaction: discord.Interaction):
        """Send a feedback modal."""
        # We create the view and assign it to a variable so we can wait for it later.
        f = ui.Feedback()
        await interaction.response.send_modal(f)
        await f.wait()
        await interaction.followup.send(f.feedback)  # type: ignore

    @commands.command(name='test')
    async def _test(self, interaction: commands.Context):
        msg = []
        button = ui.Confirm(count=msg)
        msg.append(await interaction.send('Hello', view=button))
        await button.wait()
        await msg[0].edit(view=None)

async def setup(bot):
    await bot.add_cog(Test(bot))