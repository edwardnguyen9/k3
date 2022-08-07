import os, traceback, discord, datetime, json, asyncio, asyncpg
from redis import asyncio as aioredis
from typing import List, Optional
from itertools import cycle
from discord.ext import commands
from aiohttp import ClientSession
from io import BytesIO
from pprint import pformat
from dotenv import load_dotenv

from bot.assets.api import QUERY_PREFIX
from bot.utils.errors import ApiIsDead  # type: ignore

load_dotenv()

PREFIX = os.getenv('DEFAULT_PREFIX', 'bea ')
TOKEN1 = os.getenv('IDLE_API1')
TOKEN2 = os.getenv('IDLE_API2')

class Kiddo(commands.Bot):
    def __init__(
        self,
        *args,
        initial_extensions: List[str],
        pool: asyncpg.Pool,
        session: ClientSession,
        redis: aioredis.Redis,
        log_guild_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.pool = pool
        self.session = session
        self.redis = redis
        self.log_guild_id = log_guild_id or 0
        self.initial_extensions = initial_extensions
        self.headers = cycle([
            {"Authorization": TOKEN1},
            {"Authorization": TOKEN2}
        ])
        self.all_prefixes = {
            '865304773828542544': '+',
            '475033206672850945': '!!!'
            }
        self.loaded = False
        self.owner = None
        self.cfg = {}
        self.api_guilds = []
        self.donator_guilds = []
        self.idle_guilds = {}
        self.api_available = True
        self.crates = {}

    async def loading(self):
        while not self.loaded:
            await asyncio.sleep(1)
        return True

    async def log_command(self, ctx):
        server = self.get_guild(self.log_guild_id)
        if server is None: return
        channel = discord.utils.get(server.text_channels, name='k3-command-logs')
        if channel is None: return
        embed = discord.Embed(
            title=ctx.guild.name if ctx.guild else ctx.author.name,
            color=0x79f2ce,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        ).add_field(
            name='User', value=f'{ctx.author.name} ({ctx.author.mention})', inline=False
        ).add_field(
            name='Command', value=ctx.command.qualified_name, inline=False
        ).add_field(
            name='Channel', value=ctx.channel.mention if ctx.guild else 'DM', inline=False
        ).add_field(
            name='Go to message', value=f'[Click here]({ctx.message.jump_url})', inline=False
        ).set_footer(
            text=f'#{ctx.channel.name}' if ctx.guild else ctx.author.name, icon_url=ctx.guild.icon.url if ctx.guild else ctx.author.display_avatar.url
        ).set_thumbnail(url=ctx.author.display_avatar.url)
        await channel.send(embed=embed)

    async def log_api_call(self, ctx, query: str, status: int, delay: int, res = None):
        server = self.get_guild(self.log_guild_id)
        if server is None: return
        channel = discord.utils.get(server.text_channels, name='k3-api-logs')
        if channel is None: return
        author = ctx.author if isinstance(ctx, commands.Context) else ctx.user
        message = None if not ctx else 'Query called by {} in {}'.format(
            author.name, f'#{ctx.channel.name} ({ctx.channel.mention})' # type: ignore
        )
        try:
            await channel.send(
                content=message,
                embed=discord.Embed(
                    title='Autofetch' if not ctx else ctx.command.qualified_name, # type: ignore
                    description=f'```{query}```',
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                    color=0xc77bed if status // 100 == 2 else 0xc91e1e
                ).add_field(
                    name='Response', value='.'.join([str(i) for i in [status, len(res) if res is not None else None] if i is not None])
                ).set_footer(
                    text=' | '.join([str(i) for i in [ctx.guild.name if ctx else None, '{}ms'.format(delay)] if i is not None]) # type: ignore
                ),
                file=discord.File(
                    filename='{}.txt'.format(query[:query.index('?')]),
                    fp=BytesIO(pformat(res).encode())
                ) if (ctx is not None and status // 100 == 2 and res is not None and len(res) > 0) else None  # type: ignore
            )
        except discord.HTTPException:
            print(query)
            print(status)

    async def log_error(self, err):
        server = self.get_guild(self.log_guild_id)
        if server is None: return
        channel = discord.utils.get(server.text_channels, name='k3-error-logs')
        if channel is None: return
        error_body = '\n'.join([x for x in traceback.format_tb(err.__traceback__)])
        embed = discord.Embed(
            title=type(err).__name__,
            description=f'```{error_body}```'
        )
        try:
            await channel.send(
                content= '{}\n\n\n**{}**: {}'.format(self.owner.mention, type(err).__name__, err),  # type: ignore
                embed=embed
            )
        except Exception:
            File = discord.File(filename='error-{}.json'.format(type(err).__name__), fp=BytesIO(pformat(error_body).encode()))
            await channel.send(content='{}\n\n\n**{}**: {}'.format(self.owner.mention, type(err).__name__, err), file=File)  # type: ignore

    async def setup_hook(self) -> None:
        # Load extensions
        for extension in self.initial_extensions:
            try:
                await self.load_extension(f'bot.cogs.{extension}')
                print(f'{extension.title()} loaded')
            except Exception:
                print(f'Error loading cog {extension}')
                traceback.print_exc()
                if extension == 'admin':
                    print('Shutting down {}'.format(self.user))
                    await self.redis.close()
                    await self.session.close()
                    await self.close()
                    return

        # This would also be a good place to connect to our database and
        # load anything that should be in memory prior to handling events.
        # self.pool = await self.pool
        # self.redis = await self.redis

        self.owner = await self.fetch_user(249189842326388738)
        prefixes = await self.redis.hgetall('prefix')
        for k, v in prefixes.items():
            self.all_prefixes[k] = v
        updated = {}
        for s in self.guilds:
            s_id = str(s.id)
            if s_id not in self.all_prefixes:
                self.all_prefixes[s_id] = PREFIX
                updated[s_id] = PREFIX
        if len(updated) > 0:
            await self.redis.hset('prefix', mapping=updated)

        cfglist = []

        async for k, v in self.redis.hscan_iter('k3:cfg'):
            self.cfg[int(k)] = json.loads(v)
            cfglist.append(int(k))
            for g in self.guilds:
                if g.id not in cfglist:
                    self.cfg[g.id] = {'role': {}, 'channel': {}, 'bans': {}, 'misc': {}}
                elif 'misc' in self.cfg[g.id] and 'guilds' in self.cfg[g.id]['misc']:
                    self.api_guilds += [int(i) for i in self.cfg[g.id]['misc']['guilds']]
        self.api_guilds = list(set(self.api_guilds))
        self.api_guilds.sort(key=lambda x: 0 if x == 17555 else x)
        guilds_raw = await self.redis.hgetall('guilds')
        for i in guilds_raw:
            self.idle_guilds[i] = json.loads(guilds_raw[i])
        self.loaded = True
        await self.tree.sync()
        print(f'{self.user} is online')
        
        self.before_invoke(self.log_command)

    def get_token(self):
        return next(self.headers)

    async def idle_query(self, query, ctx = None):
        res, status = None, 0
        for _ in range(3):
            start_time = datetime.datetime.now()
            if query.startswith(QUERY_PREFIX): query = query[len(QUERY_PREFIX):]
            q, h = QUERY_PREFIX + query, self.get_token()
            async with self.session.get(
                q, headers=h
            ) as r:
                end_time = datetime.datetime.now()
                delay = round((end_time - start_time)/datetime.timedelta(microseconds=1000))
                status = r.status
                try:
                    res = await r.json()
                except Exception:
                    res = None
                await self.log_api_call(ctx, query, status, delay, res)
                if status // 100 == 5:
                    self.api_available = False
                    await self.change_presence(status=discord.Status.dnd, activity=discord.Game(f'\u203c API unavailable'))
                    raise ApiIsDead
                elif status == 429:
                    await asyncio.sleep(3.5)
                else:
                    bstatus = discord.Status.dnd
                    bot_user = discord.utils.get(self.guilds[0].members, id=self.user.id) # type: ignore
                    if bot_user.status == bstatus: # type: ignore
                        self.api_available = True
                        await self.change_presence(
                            status=discord.Status.idle,
                            activity=discord.Game(
                                'Byeler is fucking real'
                            )
                        )
                    break
        return (res, status)

    def _get_prefix(self, bot, message):
        if not message.guild:
            return PREFIX
        try:
            return commands.when_mentioned_or(self.all_prefixes[str(message.guild.id)])(
                bot, message
            )
        except KeyError:
            return commands.when_mentioned_or(PREFIX)(
                bot, message
            )