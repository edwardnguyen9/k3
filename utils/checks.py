import discord
from discord import app_commands
from discord.ext import commands

from utils import errors

def guild_bill(): return app_commands.guilds(821988363308630068)
def api_guilds(): return app_commands.guilds(821988363308630068,637415907785965628,475033206672850945,688144867766960223,865304773828542544)
def mod_only(): return app_commands.default_permissions(kick_members=True)

def perms(app = True, *, gold=False, guild=False, mod=False, muted=True, bronze=False, sponsor=False, all=False):
    def predicate(interaction):
        if isinstance(interaction, discord.Interaction):
            author = interaction.user
            bot = interaction.client
        else:
            author = interaction.author
            bot = interaction.bot
        if author.id == bot.owner.id:  # type: ignore
            return True
        elif not isinstance(author, discord.Member):
            raise errors.NoDm(interaction)
        elif author.guild.id not in [821988363308630068,637415907785965628,475033206672850945,688144867766960223,865304773828542544]:
            raise errors.InsufficientPermissions(interaction)
        elif author.guild.id != 821988363308630068:
            if guild: raise errors.InsufficientPermissions(interaction, 'This command is disabled in **{}**'.format(author.guild.name))
            elif author.guild_permissions.manage_roles or author.guild_permissions.manage_channels:
                return True
            else: raise errors.InsufficientPermissions(interaction, 'This command is enabled for people with **Manage Channels** or **Manage Roles** permissions only.')
        elif all: return True
        elif muted and author.get_role(822009394517770261):
            raise errors.InsufficientPermissions(interaction, 'You cannot use this command while jailed.')
        elif muted and author.get_role(822009538240708638):
            raise errors.InsufficientPermissions(interaction, 'You cannot use this command while in isolation.')
        elif (
            author.guild_permissions.kick_members or
            author.guild_permissions.manage_roles or
            author.guild_permissions.manage_channels
        ): return True
        elif mod: raise errors.InsufficientPermissions(interaction, 'This command is reserved for Guild Officers.')
        elif author.get_role(825349199583379466): return True
        elif gold: raise errors.InsufficientPermissions(interaction, 'You need to be a Gold Donator to use this command.')
        else:
            roles = [825349207236935731, 838449672435138560, 840923406143848450, 921709742508883988]
            if bronze or sponsor: roles.append(825306327894720512)
            if sponsor: roles.append(824734262661218365)
            for i in roles:
                if author.get_role(i): return True
            raise errors.InsufficientPermissions(interaction, 'You need to be a {} or higher to use this command.'.format(
                'Guild Donator' if sponsor else 'Bronze Donator' if bronze else 'Silver Donator'
            ))

    if app: return app_commands.check(predicate)
    else: return commands.check(predicate)

async def cooldown(ctx, *, arrest = False, breakout = False, arena = False, fistfight = False, goldrush = False):
    if isinstance(ctx, commands.Context): bot, author = ctx.bot, ctx.author
    else: bot, author = ctx.client, ctx.user 
    if not arena:
        key = (
            'gr{id}' if goldrush else 'ff{id}' if fistfight else 'breakout{id}' if breakout else 'arrest{id}' if arrest else 'cd{id}'
        ).format(id=author.id)
        cd =  await bot.redis.ttl(key)
        if cd and cd > 0:
            raise errors.CommandOnCooldown(ctx, cd)
    else:
        async with bot.redis.pipeline(transaction=True) as pipe:
            res = await pipe.ttl(f'acd{author.id}').ttl(f'acd{author.guild.id}').execute()  # type: ignore
        cd = max([i or 0 for i in res])
        if cd and cd > 0: raise errors.CommandOnCooldown(ctx, cd)
