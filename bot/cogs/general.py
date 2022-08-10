import discord
from discord.ext import commands
from typing import Union

from bot.classes import ui
from bot.utils import utils

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
    async def test(self, ctx: commands.Context, user: discord.User):
        profile, weapons = await self.bot.get_equipped(user.id, ctx)
        damage, armor = utils.get_race_bonus(profile[0])
        damage += sum([int(i[2]) for i in weapons if i[1] != 'Shield']) + utils.get_weapon_bonus(weapons, profile[1]) + utils.get_class_bonus('dmg', profile[1])
        armor += sum([int(i[2]) for i in weapons if i[1] == 'Shield']) + utils.get_class_bonus('amr', profile[1])
        rd = round(profile[3][0] + utils.get_class_bonus('rdr', profile[1]) / 10, 1)
        ra = round(profile[3][1] + utils.get_class_bonus('rdr', profile[1]) / 10, 1)
        await ctx.send(' | '.join(map(str, [damage, armor, rd, ra])))

async def setup(bot):
    await bot.add_cog(Admin(bot))