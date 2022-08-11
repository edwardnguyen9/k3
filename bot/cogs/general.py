import discord
from discord.ext import commands

from bot.classes import ui

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

    @commands.command()
    async def test(self, ctx: commands.Context):
        print(await self.bot.pool.fetchval('SELECT adv FROM profile3 WHERE uid=$1', 0))
        await self.bot.pool.execute(
            'INSERT INTO profile3 (uid, adv) VALUES ($1, $2) ON CONFLICT (uid) DO UPDATE SET adv=$2;',
            0, -1
        )
        print(await self.bot.pool.fetchval('SELECT adv FROM profile3 WHERE uid=$1', 0))
        await self.bot.pool.execute(
            'INSERT INTO profile3 (uid, adv) VALUES ($1, $2) ON CONFLICT (uid) DO UPDATE SET adv=$2;',
            0, -10
        )
        print(await self.bot.pool.fetchval('SELECT adv FROM profile3 WHERE uid=$1', 0))
        await self.bot.pool.execute('DELETE FROM profile3 WHERE uid=$1;', 0)
        print(await self.bot.pool.fetchval('SELECT adv FROM profile3 WHERE uid=$1', 0))
        

async def setup(bot):
    await bot.add_cog(Admin(bot))