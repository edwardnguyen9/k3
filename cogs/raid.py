import discord, asyncio
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional

from assets import raid, config
from classes.ui import Confirm

async def announce(bot, msg, god=None):
    role = 'raid' if god is None else god
    announcements = []
    for s in bot.guilds:
        try:
            raid_channel = s.get_channel(config.config[s.id]['channel']['announce:raid'])
            if raid_channel:
                r = s.get_role(config.config[s.id]['role'][f'announce:{role}']) if f'announce:{role}' in config.config[s.id]['role'] else None
                announcements.append(await raid_channel.send('{} {}'.format(r.mention if r else '', msg)))
                if god is not None:
                    if c:=s.get_channel(config.config[s.id]['channel']['announce:god']):
                        announcements.append(await c.send('{} {}'.format(r.mention if r else '', msg)))
        except discord.Forbidden:
            print(s)
        except KeyError:
            continue
    return announcements

class Raid(commands.GroupCog, group_name='raid'):
    def __init__(self, bot):
        self.bot = bot
        self.is_first_ready = True
        # Raid announcements
        self.announcements = []
        self.switch = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self.is_first_ready:
            await self.bot.loading()
            self.reset_announcements.start()
            print(self.__class__.__name__, 'is ready')
            self.is_first_ready = False

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild: return
        elif message.channel.id == 819497629439754271:
            if 'spawned' in message.content:
                await asyncio.sleep(600)
                if len(self.announcements) == 0:
                    msg = ' '.join([
                        raid.gods['none'][0],
                        raid.gods['none'][1],
                        raid.link.format(id=raid.gods['none'][2])
                    ])
                    self.announcements = await announce(self.bot, msg)
            elif 'Raid result' in message.content:
                self.announcements = []
                self.switch = False

    @tasks.loop(minutes=15)
    async def reset_announcements(self):
        if len(self.announcements) > 0:
            if self.switch:
                self.announcements = []
            self.switch = not self.switch

    @app_commands.command(name='announce')
    async def _app_announcements(self, interaction: discord.Interaction, hp: app_commands.Range[int, 0] = 0, god: Optional[str] = None):
        '''
        Send a raid announcement
        '''
        await interaction.response.defer(thinking=True, ephemeral=True)
        if len(self.announcements) > 0:
            view = Confirm('Sending new announcement', 'Deleting announcement')
            await interaction.followup.send('An announcement has already been sent. Would you like to send another announcement or delete the last one?', view=view)
            await view.wait()
            if view.value is None: return
            for i in self.announcements: await i.delete()
            if not view.value:
                self.announcements = []
                self.switch = False
                return
        else:
            await interaction.followup.send('Sending announcement')
        if god is None:
            msg = ' '.join([
                s for s in [
                    raid.gods['none'][0],
                    raid.hp.format(hp=hp) if hp else None,
                    raid.cash.format(cash=int(hp/4)),
                    raid.gods['none'][1],
                    raid.link.format(id=raid.gods['none'][2])
                ] if s is not None
            ])
            self.announcements = await announce(self.bot, msg)
        else:
            if god == 'eden' and hp == 0: hp = 15000
            msg = ' '.join([s for s in [
                raid.gods[god][0].format(number=hp),
                raid.hp.format(hp=hp) if not god in ['lyx', 'kvothe'] else None,
                raid.cash.format(cash=int(hp/4)) if god in ['jesus', 'eden', 'chamburr'] else None,
                raid.gods[god][1],
                raid.link.format(id=raid.gods[god][2])
            ] if s is not None])
            self.announcements = await announce(self.bot, msg, god)
        if len(self.announcements) > 0:
            await interaction.followup.send('Announcement sent to {} channels.'.format(len(self.announcements)))


async def setup(bot):
    await bot.add_cog(Raid(bot))