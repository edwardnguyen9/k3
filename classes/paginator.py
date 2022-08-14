import discord, asyncio

from random import getrandbits

from utils.errors import NoEmbedPage
from utils.utils import pager


class Paginator:

    __slots__ = (
        "text",
        "entries",
        "extras",
        "title",
        "description",
        "color",
        "footer",
        "length",
        "prepend",
        "append",
        "fmt",
        "timeout",
        "ordered",
        "controls",
        "controller",
        "pages",
        "current",
        "previous",
        "eof",
        "base",
        "names",
        "parser",
        "codeblock",
        'private',
        'timestamp',
        'customnav',
        'xtraline'
    )

    def __init__(self, **kwargs):
        self.text = kwargs.get("text", None)
        self.entries = kwargs.get("entries", None)
        self.extras = kwargs.get("extras", None)

        self.title = kwargs.get("title", None)
        self.description = kwargs.get("description", None)
        self.color = kwargs.get("color", getrandbits(24))
        self.footer = kwargs.get("footer", None)

        self.length = kwargs.get("length", 10)
        self.prepend = kwargs.get("prepend", "")
        self.append = kwargs.get("append", "")
        self.fmt = kwargs.get("fmt", "")
        self.timeout = kwargs.get("timeout", 90)
        self.ordered = kwargs.get("ordered", False)
        self.parser = kwargs.get("parser", None)
        self.codeblock = kwargs.get("codeblock", False)
        self.private = kwargs.get("private", True)
        self.timestamp = kwargs.get("timestamp", None)
        self.xtraline = kwargs.get("xtraline", 0)

        self.customnav = kwargs.get("customnav", None)

        self.controller = None
        self.pages = []
        self.names = []
        self.base = None

        self.current = 0
        self.previous = 0
        self.eof = 0

        self.controls = {
            "\u23ee": float(0),
            "\u25c0": int(-1), 
            "\u23f9": "stop", 
            "\u25b6": int(+1),
            "\u23ed": float(0),
            "🔢": "get"
        }

    async def indexer(self, ctx, ctrl):
        if isinstance(ctx, discord.Interaction):
            author = ctx.user
            bot = ctx.client
            message_sending = ctx.followup
        else:
            author = ctx.author
            bot = ctx.bot
            message_sending = ctx
        if ctrl == "stop":
            bot.loop.create_task(self.stop_controller(self.base))

        elif ctrl == "get":
            if self.customnav is not None:
                jumpto = await self.customnav(ctx)
                if jumpto is not None: self.current = int(jumpto)
            else:
                def valid(msg):
                    if msg.guild and msg.channel.id == ctx.channel.id and msg.author.id == author.id and msg.content.isdecimal():  # type: ignore
                        pg = int(msg.content) - 1
                        return pg >= int(self.controls["\u23ee"]) and pg <= int(self.controls["\u23ed"])
                    return False

                prompt = await message_sending.send('Select a page between {}-{}'.format(int(self.controls["\u23ee"])+1, int(self.controls["\u23ed"])+1))
                try:
                    jumpto = await bot.wait_for('message', check=valid, timeout=15)
                except asyncio.TimeoutError:
                    await prompt.delete()  # type: ignore
                    return await message_sending.send('You did not enter a valid page.')
                await prompt.delete()  # type: ignore
                self.current = int(jumpto.content) - 1
                await jumpto.delete()

        elif isinstance(ctrl, int):
            self.current += ctrl
            if self.current > self.eof or self.current < 0:
                self.current -= ctrl
        else:
            self.current = int(ctrl)

    async def reaction_controller(self, ctx):
        if isinstance(ctx, discord.Interaction):
            author = ctx.user
            bot = ctx.client
            message_sending = ctx.followup
        else:
            author = ctx.author
            bot = ctx.bot
            message_sending = ctx
        if self.base is None:
            self.base = await message_sending.send(content=self.text, embed=self.pages[0])  # type: ignore
        else:
            await self.base.edit(content=self.text, embed=self.pages[0])

        if len(self.pages) == 1 and self.private:
            await self.base.add_reaction("\u23f9")  # type: ignore
        elif len(self.pages) > 1:
            for reaction in self.controls:
                if not self.private and reaction == "\u23f9": continue
                try:
                    await self.base.add_reaction(reaction)  # type: ignore
                except discord.HTTPException:
                    return

        def check(r, u):
            if str(r) not in self.controls.keys():
                return False
            elif u.id == bot.user.id or r.message.id != self.base.id:  # type: ignore
                return False
            elif u.id == bot.owner.id:  # type: ignore
                return True
            elif self.private and u.id != author.id:
                return False
            return True

        while True:
            try:
                react, user = await bot.wait_for(
                    "reaction_add", check=check, timeout=self.timeout
                )
            except asyncio.TimeoutError:
                if self.private:
                    return bot.loop.create_task(self.stop_controller(self.base))
                else:
                    for reaction in self.controls:
                        try:
                            await self.base.remove_reaction(reaction, bot.user)  # type: ignore
                        except discord.HTTPException:
                            pass
                    return

            control = self.controls.get(str(react))

            try:
                await self.base.remove_reaction(react, user)  # type: ignore
            except discord.HTTPException:
                pass

            self.previous = self.current
            await self.indexer(ctx, control)

            if self.previous == self.current:
                continue

            try:
                await self.base.edit(content=self.text, embed=self.pages[self.current])  # type: ignore
            except KeyError:
                pass

    async def stop_controller(self, message):
        try:
            await message.edit(content=message.content or '\u200b', embed=None)
        except discord.HTTPException as e:
            print(e)
            pass
        try:
            await message.clear_reactions()
        except discord.Forbidden:
            reactions = [r for r in message.reactions]
            for r in reactions: await message.remove_reaction(r, message.author)
        except discord.HTTPException:
            pass

        try:
            self.controller.cancel()  # type: ignore
        except Exception:
            pass

    def formmater(self, chunk):
        if self.parser:
            for i in range(len(chunk)):
                chunk[i] = self.parser(chunk[i])
        description = '```c\n{}```' if self.codeblock else '{}'
        lb = '\n' + self.xtraline * '\n'
        return description.format(
            lb.join(
                f"{self.prepend}{self.fmt}{value}{self.fmt[::-1]}{self.append}"
                for value in chunk
            )
        )

    async def paginate(self, ctx, base = None):
        self.base = base
        if isinstance(ctx, discord.Interaction):
            author = ctx.user
            bot = ctx.client
        else:
            author = ctx.author
            bot = ctx.bot
        if self.extras:
            for p in self.extras:
                if isinstance(p,discord.Embed):
                    if hasattr(p, 'footer'):
                        if len(self.extras) > 1:
                            if not p.footer and not self.footer:
                                p.set_footer(text='Page {}/{}'.format(self.extras.index(p) + 1, len(self.extras)), icon_url=author.display_avatar.url)
                            else:
                                p.set_footer(text=(p.footer.text if p.footer else self.footer) + ' | Page {}/{}'.format(self.extras.index(p) + 1, len(self.extras)), icon_url=(p.footer.icon_url or ctx.display_avatar.url))  # type: ignore
                        elif len(self.extras) == 1:
                            p.set_footer(text=p.footer.text if p.footer else self.footer, icon_url=p.footer.icon_url if p.footer and p.footer.icon_url else author.display_avatar.url)
                    if hasattr(p, 'timestamp'):
                        if not p.timestamp:
                            p.timestamp = self.timestamp or discord.utils.utcnow()
                    self.pages.append(p)

        if self.entries:
            chunks = [c for c in pager(self.entries, self.length)]

            for index, chunk in enumerate(chunks):
                page = discord.Embed(
                    title=f"{self.title} - {index + 1}/{len(chunks)}", color=self.color
                )
                page.set_footer(text=f'Page {index + 1}/{len(chunks)}', icon_url=author.display_avatar.url)
                page.description = self.formmater(chunk)
                page.timestamp = self.timestamp or discord.utils.utcnow()
                if hasattr(self, "footer"):
                    if self.footer:
                        page.set_footer(text=self.footer, icon_url=author.display_avatar.url)
                    else:
                        page.title = self.title
                self.pages.append(page)

        if not self.pages:
            raise NoEmbedPage(ctx)

        self.eof = float(len(self.pages) - 1)
        self.controls["\u23ed"] = self.eof
        self.controller = bot.loop.create_task(self.reaction_controller(ctx))