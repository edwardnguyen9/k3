import discord, traceback
from discord.ext import commands
from discord import app_commands

from bot.bot import Kiddo
from utils import errors
from utils.utils import get_timedelta

class ErrorHandler(commands.Cog, name='Error Handler'):
    def __init__(self, bot: Kiddo):
        self.bot = bot
        self.is_first_ready = True

    @commands.Cog.listener()
    async def on_ready(self):
        if self.is_first_ready:
            print(self.__class__.__name__, 'is ready')
            self.is_first_ready = False
            self.bot.tree.on_error = self.on_command_error
            # self.bot.on_error = self.on_command_error

    # @commands.Cog.listener()
    # async def on_app_command_error(self, interaction, error):
    #     await self.on_command_error(interaction, error)

    @commands.Cog.listener()
    async def on_command_error(self, interaction, error):
        if isinstance(error, commands.CommandNotFound):
            return

        elif isinstance(error, errors.ApiIsDead):
            status = await self.bot.redis.get('idle-api') or 0
            cd = error.ttl or 900
            if error.status and int(status) != error.status:
                await self.bot.redis.set('idle-api', status, ex=900)
            await self.send_error_message(
                interaction,
                f'The API is currently unavailable (Error Code: {status}). Please try again in {get_timedelta(cd)}.'
            )

        elif isinstance(error, errors.KiddoException):
            await self.send_error_message(error.context, str(error))
        
        elif isinstance(error, commands.NotOwner):
            await self.send_error_message(interaction, 'You are not the boss of me.')

        elif isinstance(error, (app_commands.CommandInvokeError, commands.CommandInvokeError, commands.BadArgument, ValueError)):
            await self.send_error_message(interaction, str(error))

        elif isinstance(error, commands.BadUnionArgument):
            message = 'The provided {.name} is not a valid {}'.format(
                error.param, ' or '.join(map(lambda x: x.__name__, error.converters))
            )
            await self.send_error_message(interaction, message)

        else:
            try:
                await self.bot.log_error(error)
            except Exception:
                print(
                    "Error while using this command!\n\n**{0}**: {1}\n{2}".format(
                        type(error).__name__,
                        error,
                        "\n".join([x for x in traceback.format_tb(error.__traceback__)]),
                    )
                )
            return await self.send_error_message(interaction, f'{type(error).__name__}! {error}')

    async def send_error_message(self, ctx, error):
        
        if isinstance(ctx, discord.Interaction):
            try:
                await ctx.response.send_message(error, ephemeral=True)
            except discord.InteractionResponded:
                await ctx.followup.send(error, ephemeral=True)
        elif isinstance(ctx, commands.Context):
            await ctx.send(error)
        else:
            print(error)

async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))