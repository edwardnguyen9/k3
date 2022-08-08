import discord

from bot.assets import api

def check_if_all_null(*args):
    for i in args:
        if i is not None: return False
    return True

async def class_autocomplete(interaction: discord.Interaction, current: str) -> list[discord.app_commands.Choice[str]]:  # type: ignore
    classes = {
        'Warrior': 'wrr', 'Mage': 'mge', 'Paragon': 'prg', 'Raider': 'rdr', 'Ranger': 'rng', 'Ritualist': 'rtl', 'Thief': 'thf'
    }
    return [
        discord.app_commands.Choice(name=k, value=v) for k, v in classes.items() if current.lower() in k.lower()
    ]

async def race_autocomplete(interaction: discord.Interaction, current: str) -> list[discord.app_commands.Choice[str]]:  # type: ignore
    return [
        discord.app_commands.Choice(name=i, value=i) for i in api.races if current.lower() in i.lower()
    ]
