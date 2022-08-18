import discord, traceback
from discord.ext import commands
from io import BytesIO
from pprint import pformat

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_first_ready = True
        self.messages = {}

    @commands.Cog.listener()
    async def on_ready(self):
        if self.is_first_ready:
            self.bot.command_prefix = self.bot._get_prefix
            print(self.__class__.__name__, 'is ready')
            self.is_first_ready = False

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        elif message.guild is None:
            server = self.bot.get_guild(self.bot.log_guild_id)
            if server is None: return
            channel = discord.utils.get(server.text_channels, name=str(message.author.id))
            if channel is None:
                cat = discord.utils.get(server.categories, name='k3 dms')
                if cat is None: cat = await server.create_category('k3 dms')
                try:
                    channel = await server.create_text_channel(name=str(message.author.id), category=cat)
                except discord.Forbidden:
                    return
            hooks = await channel.webhooks()  # type: ignore
            if len(hooks) == 0:
                hook = await channel.create_webhook(name=str(message.author.id))  # type: ignore
            else:
                hook = hooks[0]
            files = []
            if len(message.attachments) > 0:
                for f in message.attachments:
                    files.append(await f.to_file())
            self.messages[message.id] = await hook.send(
                content=message.content,
                files=files,
                username=message.author.name,
                avatar_url=message.author.display_avatar.url,
                wait=True,
            )
        elif message.guild and message.guild.id == self.bot.log_guild_id and message.channel.category and message.channel.category.name == 'k3 dms':
            user = self.bot.get_user(int(message.channel.name))
            if user is not None:
                files = []
                if len(message.attachments) > 0:
                    for f in message.attachments:
                        files.append(await f.to_file())    
                try:
                    self.messages[message.id] = await user.send(
                        content=message.content, files=files
                    )
                except discord.Forbidden:
                    await message.channel.send('Cannot send messages to this user.')
            else:
                await message.channel.send('User no longer seen by bot')


    @commands.Cog.listener()
    async def on_message_edit(self, pre, message):
        if pre.author.bot: return
        elif not pre.guild:
            files = []
            if pre.id in self.messages:
                self.messages[message.id] = await self.messages[pre.id].edit(
                    content=message.content,
                    attachments=message.attachments,
                )
            elif pre.content != message.content:
                server = self.bot.get_guild(self.bot.log_guild_id)
                if server is None: return
                channel = discord.utils.get(server.text_channels, name=str(message.author.id))
                if channel is None:
                    cat = discord.utils.get(server.categories, name='k3 dms')
                    if cat is None: cat = await server.create_category('k3 dms')
                    try:
                        channel = await server.create_text_channel(name=str(message.author.id), category=cat)
                    except discord.Forbidden:
                        return
                hooks = await channel.webhooks()  # type: ignore
                if len(hooks) == 0:
                    hook = await channel.create_webhook(name=str(message.author.id))  # type: ignore
                else:
                    hook = hooks[0]
                    if len(message.attachments) > 0:
                        for f in message.attachments:
                            files.append(await f.to_file())
                self.messages[message.id] = await hook.send(
                    content=message.content,
                    files=files,
                    username=message.author.name,
                    avatar_url=message.author.display_avatar.url,
                    wait=True,
                    embed=discord.Embed(
                        title='Pre-edit', description=pre.content
                    )
                )
        elif message.guild and message.guild.id == self.bot.log_guild_id and message.channel.category and message.channel.category.name == 'k3 dms':
            try:
                self.messages[message.id] = await self.messages[pre.id].edit(
                    content=message.content, attachments=message.attachments
                )
            except KeyError:
                await message.channel.send('Cannot edit that message.')
            except discord.Forbidden:
                await message.channel.send('Cannot send messages to this user.')

    @commands.is_owner()
    @commands.command(
        name='redis',
        aliases=['r'],
        brief='Execute REDIS query',
        description='Execute REDIS query',
        usage='<query>',
        help='''
        > <query>: The query to be executed
        ''',
    )
    async def _redis(self, ctx, *args):
        res = await self.bot.redis.execute_command(*args)
        r = str(res)
        if len(r) < 1990:
            await ctx.channel.send('```\n' + r + '```')
        else:
            File = discord.File(filename='redis-{}.json'.format(type(res)), fp=BytesIO(pformat(res).encode()))
            await ctx.channel.send(file=File)

    @commands.is_owner()
    @commands.command(
        name='postgres',
        aliases=['post'],
        brief='Execute POSTGRES fetch query',
        description='Execute POSTGRES fetch query',
        usage='<query>',
        help='> <query>: The query to be executed',
        hidden=True
    )
    async def _post(self, ctx, command, *, string):
        try:
            if command == 'fetch':
                res = await self.bot.pool.fetch(string)
            elif command == 'fetchval':
                res = await self.bot.pool.fetchval(string)
            elif command == 'fetchrow':
                res = await self.bot.pool.fetchrow(string)
            else:
                res = await self.bot.pool.execute(string)
            if res is None:
                await ctx.send('Data not found')
            else:
                await ctx.send('{} | {}'.format(type(res), len(res)))
                await ctx.send(str(res))
        except discord.Forbidden:
            traceback.print_exc()
            try:
                print(str(res))  # type: ignore
            except UnboundLocalError:
                pass
            except Exception:
                traceback.print_exc()
        

async def setup(bot):
    await bot.add_cog(Admin(bot))