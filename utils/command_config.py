import discord
from discord.ext import commands
from typing import Optional

from assets import idle

# Profile

class AdventureChance(commands.FlagConverter):
    user: Optional[discord.User] = None
    level: Optional[int] = None
    booster: bool = False
    building: int = 10

async def auto_class(interaction: discord.Interaction, current: str) -> list[discord.app_commands.Choice[str]]:  # type: ignore
    classes = {
        'Warrior': 'wrr', 'Mage': 'mge', 'Paragon': 'prg', 'Raider': 'rdr', 'Ranger': 'rng', 'Ritualist': 'rtl', 'Thief': 'thf'
    }
    return [
        discord.app_commands.Choice(name=k, value=v) for k, v in classes.items() if current.lower() in k.lower()
    ]

async def auto_race(interaction: discord.Interaction, current: str) -> list[discord.app_commands.Choice[str]]:  # type: ignore
    return [
        discord.app_commands.Choice(name=i, value=i) for i in idle.races if current.lower() in i.lower()
    ]

async def auto_god(interaction: discord.Interaction, current: str) -> list[discord.app_commands.Choice[str]]:  # type: ignore
    return [
        discord.app_commands.Choice(name=i, value=i) for i in idle.gods if current.lower() in i.lower()
    ]

# Item

async def auto_type(interaction: discord.Interaction, current: str) -> list[discord.app_commands.Choice[str]]:  # type: ignore
    return [
        discord.app_commands.Choice(name=i, value=i) for i in idle.weapontypes if current.lower() in i.lower()
    ]

async def auto_market_type(interaction: discord.Interaction, current: str) -> list[discord.app_commands.Choice[str]]:  # type: ignore
    return [
        discord.app_commands.Choice(name=i, value=i) for i in (idle.weapontypes + ['One-handed', 'Two-handed']) if current.lower() in i.lower()
    ]

async def auto_hand(interaction: discord.Interaction, current: str) -> list[discord.app_commands.Choice[str]]:  # type: ignore
    return [
        discord.app_commands.Choice(name=i, value=i) for i in idle.weaponhands if current.lower() in i.lower()
    ]

