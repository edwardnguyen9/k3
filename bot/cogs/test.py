import discord, datetime
from discord.ext import commands

from bot.classes import ui
from bot.utils import utils  # type: ignore

class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_first_ready = True

    @commands.Cog.listener()
    async def on_ready(self):
        if self.is_first_ready:
            print(self.__class__.__name__, 'is ready')
            self.is_first_ready = False

    
    @discord.app_commands.command()
    async def ask(self, interaction: discord.Interaction):
        """Asks the user a question to confirm something."""
        # We create the view and assign it to a variable so we can wait for it later.
        view = ui.Confirm()
        await interaction.response.send_message('Do you want to continue?', view=view)
        # Wait for the View to stop listening for input...
        await view.wait()
        if view.value is None:
            await interaction.followup.send('Timed out...')
        elif view.value:
            await interaction.followup.send('Confirmed...')
        else:
            await interaction.followup.send('Cancelled...')

    @discord.app_commands.command()
    async def feedback(self, interaction: discord.Interaction):
        """Send a feedback modal."""
        # We create the view and assign it to a variable so we can wait for it later.
        f = ui.Feedback()
        await interaction.response.send_modal(f)
        await f.wait()
        await interaction.followup.send(f.feedback)  # type: ignore

    @commands.command(name='test')
    async def _test(self, ctx: commands.Context):
        await ctx.send('One')
        await discord.utils.sleep_until(
            discord.utils.utcnow() + datetime.timedelta(seconds=10),
        )
        await ctx.send('Three')

async def setup(bot):
    await bot.add_cog(Test(bot))