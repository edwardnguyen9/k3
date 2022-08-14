import os, traceback, discord, datetime, json, asyncio, asyncpg
from redis import asyncio as aioredis
from typing import List, Optional
from itertools import cycle
from discord.ext import commands
from aiohttp import ClientSession
from io import BytesIO
from pprint import pformat
from dotenv import load_dotenv

from assets import idle, postgres
from utils import errors, utils

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
        self.tree.on_error = self.on_error

    async def on_error(self, interaction, error):
        if isinstance(error, errors.ApiIsDead):
            status = await self.redis.get('idle-api') or 0
            if error.status and int(status) != error.status:
                await self.redis.set('idle-api', status, ex=900)

        elif isinstance(error, errors.KiddoException):
            await interaction.response.send_message(str(error), ephemeral=True)
            
        else:
            try:
                await self.log_error(error)
            except Exception:
                print(interaction.guild.name if interaction.guild else 'DM', error, traceback.extract_stack())

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
            timestamp=discord.utils.utcnow()
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
        author = None if ctx is None else ctx.author if isinstance(ctx, commands.Context) else ctx.user
        message = None if not ctx else 'Query called by {} in {}'.format(
            author.name, f'#{ctx.channel.name} ({ctx.channel.mention})' # type: ignore
        )
        try:
            await channel.send(
                content=message,
                embed=discord.Embed(
                    title='Autofetch' if not ctx else ctx.command.qualified_name, # type: ignore
                    description=f'```{query} ```',
                    timestamp=discord.utils.utcnow(),
                    color=0xc77bed if status // 100 == 2 else 0xc91e1e
                ).add_field(
                    name='Response', value='.'.join([str(i) for i in [status, len(res) if res is not None else None] if i is not None])
                ).set_footer(
                    text=' | '.join([str(i) for i in [ctx.guild.name if ctx else None, '{}ms'.format(delay)] if i is not None]) # type: ignore
                ),
                file=discord.File(
                    filename='{}.txt'.format(query[:query.index('?')] if '?' in query else 'query'),
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

    async def log_event(self, event: str, *, message: Optional[str] = None, embed: Optional[discord.Embed] = None, file: Optional[discord.File] = None):
        if utils.check_if_all_null(message, embed, file): return
        server = self.get_guild(self.log_guild_id)
        if server is None: return
        channel = discord.utils.get(server.text_channels, name=f'k3-{event}-logs')
        if channel is None:
            cat = discord.utils.get(server.categories, name='kiddo 3 logs')
            if cat is None: return
            try:
                channel = await server.create_text_channel(name=f'k3-{event}-logs', category=cat)
            except discord.Forbidden:
                return
        return await channel.send(message, embed=embed, file=file)  # type: ignore

    async def setup_hook(self) -> None:
        # Load extensions
        for extension in self.initial_extensions:
            try:
                await self.load_extension(f'cogs.{extension}')
                # print(f'{extension.title()} loaded')
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

    async def idle_query(self, query, ctx = None, tries: int = 3):
        res, status = [], 0
        for i in range(tries):
            start_time = datetime.datetime.now()
            if len(query) > 0 and query.startswith(idle.QUERY_PREFIX): query = query[len(idle.QUERY_PREFIX):]
            async with self.session.get(
                idle.QUERY_PREFIX + query, headers=self.get_token()
            ) as r:
                end_time = datetime.datetime.now()
                delay = round((end_time - start_time)/datetime.timedelta(microseconds=1000))
                status = r.status
                try:
                    res = await r.json()
                except Exception:
                    res = []
                await self.log_api_call(ctx, query, status, delay, res)
                if status // 100 == 5:
                    self.api_available = False
                    await self.change_presence(status=discord.Status.dnd, activity=discord.Game(f'\u203c API unavailable'))
                    raise errors.ApiIsDead(ctx)
                elif status == 429 and i < 2:
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

    async def get_equipped(self, uid, ctx=None, orgs=False, *, manual_update=False):
        old_equipped = await self.pool.fetchval(postgres.queries['fetch_weapons'], uid) or []
        equipped = [i[0] for i in old_equipped]
        hands, dmg_lim, amr_lim = 0, 101, 101
        shield = False
        skipped = []
        profile = {}
        idmin = 0
        if len(equipped) > 0:
            (res, status) = await self.idle_query(idle.queries['equip_old'].format(owner=uid, ids=','.join(equipped)), ctx)
            if status == 429:
                raise errors.TooManyRequests(ctx)
            equipped.clear()
            if len(res) > 0 and 'profile' in res[0]:
                profile = res[0]['profile']
            for i in res:
                if 'inventory' in i and i['inventory']:
                    hands += 2 if i['hand'] == 'both' else 1
                    equipped.append(i)
                    if i['type'] == 'Shield': shield = True
        while hands < 2 and (
            dmg_lim + amr_lim > 0 or len(skipped) > 0
        ):
            hand_query = ['right', 'any']
            if not shield: hand_query += ['left']
            if hands == 0: hand_query += ['both']
            if idmin > 0:
                skipped = [i for i in skipped if i > idmin]
                s_query = f'&armor=eq.{amr_lim}'
                if amr_lim == 0: s_query += f'&damage=eq.{dmg_lim}'
                query = idle.queries['scan_stats'].format(
                    owner=uid, ids=','.join([str(i['id']) for i in equipped] + [str(i) for i in skipped]), hands=','.join(hand_query),
                    idmin=idmin, stats=s_query
                )
            elif len(skipped) > 0 or dmg_lim + amr_lim > 0:
                query = idle.queries['equipped'].format(
                    owner=uid, ids=','.join([str(i['id']) for i in equipped] + [str(i) for i in skipped]), hands=','.join(hand_query),
                    damage=dmg_lim, armor=amr_lim
                )
            else:
                query = idle.queries['scan_stats'].format(
                    owner=uid, ids=','.join([str(i['id']) for i in equipped] + [str(i) for i in skipped]), hands=','.join(hand_query),
                    idmin=idmin, stats='&damage=eq.0&armor=eq.0'
                )
            (res, status) = await self.idle_query(query, ctx)
            if len(res) == 0:
                if amr_lim > 0:
                    amr_lim -= 1
                    skipped = []
                elif dmg_lim > 0:
                    dmg_lim -= 1
                    skipped = []
                else:
                    break
                await asyncio.sleep(3.5)
            else:
                if len(profile) == 0 and 'profile' in res[0]:
                    profile = res[0]['profile']
                for i in res:
                    if hands == 2: break
                    if 'inventory' in i and i['inventory']:
                        hands += 2 if i['hand'] == 'both' else 1
                        equipped.append(i)
                        if i['type'] == 'Shield': shield = True
                if hands < 2:
                    if amr_lim > 0 and shield:
                        amr_lim, idmin, skipped = 0, 0, []
                    elif amr_lim > 0 and amr_lim > int(res[-1]['armor']):
                        amr_lim, idmin, skipped = int(res[-1]['armor']), 0, [i['id'] for i in res if i['armor'] == res[-1]['armor']]
                    elif amr_lim > 0 and amr_lim == int(res[-1]['armor']):
                        if len(res) < 250:
                            amr_lim, idmin, skipped = amr_lim - 1, 0, []
                        elif idmin == 0:
                            idmin = 1
                            skipped += [i['id'] for i in res if i['armor'] == res[-1]['armor']]
                        else:
                            idmin = res[-1]['id']
                    elif dmg_lim > int(res[-1]['damage']):
                        dmg_lim, idmin, skipped = int(res[-1]['damage']), 0, [i['id'] for i in res if i['damage'] == res[-1]['damage']]
                    elif len(res) < 250:
                        dmg_lim, idmin, skipped = dmg_lim - 1, 0, []
                    elif idmin == 0:
                        idmin = 1
                        skipped += [i['id'] for i in res if i['damage'] == res[-1]['damage']]
                    else: idmin = res[-1]['id']
                    await asyncio.sleep(3.5)
        if len(profile) == 0:
            (res, status) = await self.idle_query(idle.queries['profile'].format(userid=uid), ctx)
            if status == 429:
                raise errors.TooManyRequests(ctx)
            if len(res) > 0 and 'profile' in res[0]:
                profile = res[0]['profile']
        to_update = None
        if len(profile) > 0:
            log_p = [profile['race'], utils.transmute_class(profile), profile['guild'], [profile['atkmultiply'], profile['defmultiply']]]
            log_w = [[str(i['id']), i['type'], str(int(i['damage'] + i['armor'])), i['name']] for i in equipped]
            to_update = [uid, *log_p, log_w, discord.utils.utcnow()]
            if not manual_update:
                await self.pool.execute(postgres.queries['update_weapons'], *to_update)
        else: log_p, log_w = [], []
        if orgs:
            return equipped, profile, to_update if manual_update else None
        else:
            return log_w, log_p, to_update if manual_update else None

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