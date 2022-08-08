import asyncio, os, asyncpg, discord
from redis import asyncio as aioredis
from discord.ext import commands
from aiohttp import ClientSession
from dotenv import load_dotenv


from bot.classes.bot import Kiddo

load_dotenv()
intents = discord.Intents.default()
intents.reactions = True
intents.members = True
intents.message_content = True

async def main():
    
    async with ClientSession() as client, asyncpg.create_pool(os.getenv('DATABASE')) as pool, aioredis.from_url(os.getenv('REDIS'), decode_responses=True) as redis:  # type: ignore

        exts = [f[:-3] for f in os.listdir('bot/cogs') if f.endswith('.py')]
        pool = asyncpg.create_pool(os.getenv('DATABASE', ''))
        redis = aioredis.from_url(os.getenv('REDIS', ''), decode_responses=True)
        PREFIX = os.getenv('DEFAULT_PREFIX', 'bea ')
        LOG_SERVER = int(os.getenv('LOG_SERVER', 0))
        
        async with Kiddo(
            command_prefix=commands.when_mentioned_or(PREFIX),
            pool=pool,
            session=client,
            redis=redis,
            initial_extensions=exts,
            intents=intents,
            case_insensitive=True,
            log_guild_id=LOG_SERVER,
            help_command=None
        ) as bot:

            await bot.start(os.getenv('TOKEN', ''))


# For most use cases, after defining what needs to run, we can just tell asyncio to run it:
asyncio.run(main())
