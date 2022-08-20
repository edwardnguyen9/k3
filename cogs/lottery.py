import discord, json, datetime, re
from random import getrandbits, choice, sample
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional
from asyncio import sleep

from bot.bot import Kiddo
from classes.paginator import Paginator
from utils import utils, checks, embeds

class Lottery(commands.GroupCog, group_name='lottery'):
    def __init__(self, bot: Kiddo):
        self.bot = bot
        self.is_first_ready = True
        self.booth = None
        self.announcement = None
        self.role = None
        self.tickets = {}
        self.lottery = {}
        self.author = None

    @commands.Cog.listener()
    async def on_ready(self):
        if self.is_first_ready:
            await self.bot.loading()
            self.announcement = self.bot.get_channel(self.bot.event_config['channels']['lottery:announce'])
            self.booth = self.bot.get_channel(self.bot.event_config['channels']['lottery'])
            self.role = self.booth.guild.get_role(self.bot.event_config['roles']['lottery'])  # type: ignore
            res = await self.bot.redis.pipeline(transaction=True).hgetall('lottery:config').hgetall('lottery:tickets').execute()  # type: ignore
            for i in res[0]:
                self.lottery[i] = json.loads(res[0][i])
            if res[1]:
                for i in res[1]:
                    self.tickets[int(i)] = json.loads(res[1][i])
            self.delete_lottery_history.start()
            print(self.__class__.__name__, 'is ready')
            self.is_first_ready = False

    @tasks.loop(minutes=1)
    async def delete_lottery_history(self):
        if self.lottery and not self.author and self.lottery['timestamp'][1] + 43200 < discord.utils.utcnow():
            self.lottery = {}
            self.tickets = {}

    @checks.perms(False, guild=True)
    @commands.group(
        name='lottery',
        brief='Get lottery tickets',
        description='Get all lottery ticket information',
        invoke_without_command=True
        
    )
    async def _lottery(self, ctx: commands.Context):
        await self.get_tickets(ctx, ctx.bot.user)

    @checks.perms(False, guild=True)
    @_lottery.command(
        name='tickets',
        brief='Get a user\'s lottery tickets',
        description='Get all lottery tickets that belong to a user (or all free tickets if no user provided)',
        usage='[user]',
        help='''
        > [user]: The user whose tickets you want to get (leave empty for free tickets)
        '''
    )
    async def _tickets(self, ctx: commands.Context, user: Optional[discord.User] = None):
        await self.get_tickets(ctx, user)

    @checks.perms(guild=True)
    @app_commands.describe(user='The user whose tickets you want to get')
    @app_commands.command(name='tickets')
    async def _app_tickets(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        '''
        Get all lottery tickets that belong to a user
        '''
        await self.get_tickets(interaction, user)

    @checks.perms(guild=True, mod=True)
    @app_commands.describe(
        tickets='Total ticket amount', _max='Max number of tickets a member can have', price='Ticket price', tax='Guild tax'
    )
    @app_commands.rename(
        _max='max_per_user'
    )
    @app_commands.command(name='start')
    async def _app_start(
        self, interaction: discord.Interaction,
        tickets: Optional[app_commands.Range[int, 50]] = None, _max: Optional[app_commands.Range[int, 5]] = None,
        price: Optional[app_commands.Range[int, 50]] = None,
        tax: Optional[app_commands.Range[float, 0, 100]] = None
    ):
        '''
        Start a guild lottery
        '''
        await interaction.response.defer(thinking=True)
        if self.author: return await interaction.followup.send('A lottery is already in progress')
        self.author = interaction.user
        self.lottery = {
            'mode': 'lottery',
            'author': interaction.user.id,
            'tickets': tickets or self.bot.event_config['lottery']['tickets'],
            'max': _max or self.bot.event_config['lottery']['max'],
            'price': price or self.bot.event_config['lottery']['price'],
            'tax': tax or self.bot.event_config['lottery']['tax'],
            'timestamp': discord.utils.utcnow().timestamp(),
        }
        for i in range(self.lottery['tickets']):
            self.tickets[str(i+1)] = 0
        await self.bot.redis.pipeline(transaction=True).hset('lottery:config', mapping=self.lottery).hset('lottery:tickets', mapping=self.tickets).execute()  # type: ignore
        await interaction.followup.send('Starting a lottery')
        await self.update()

    @checks.perms(guild=True, mod=True)
    @app_commands.describe(
        action='The action to take (give or remove tickets)',
        user='The user to affect',
        tickets='The tickets to add/remove'
    )
    @app_commands.choices(
        action=[app_commands.Choice(name=i.title(), value=i) for i in ['give', 'remove']]
    )
    @app_commands.command(name='manage')
    async def _app_manage(self, interaction: discord.Interaction, action: str, user: discord.User, tickets: str):
        '''
        Give or remove lottery tickets
        '''
        await interaction.response.defer(thinking=True)
        if not self.author: return interaction.followup.send('There is no lottery running...')
        ticket_list = self.parse_tickets(tickets.replace(';', ',').replace(', ', ' ').replace(',', ' ').split(' '))
        if action == 'give':
            res = self.check_validity(user.id, ticket_list)
            if res is None:
                return await interaction.followup.send('{.mention} cannot buy more than {:,d} tickets in total.'.format(user, self.lottery['max']))
            msg = 'Invalid inputs ignored. ' if (len(res) < len(tickets)) else ''
            if len(res) == 0:
                msg += 'No valid ticket found.'
                return await interaction.followup.send(msg)
            else:
                for i in res: self.tickets[str(i)] = user.id
                m_tickets = [i for i in self.tickets if self.tickets[i] == user.id]
                listing = '\n'.join([
                    '```js',
                    '\n'.join(' '.join([
                        i.rjust(3) for i in entry
                    ]) for entry in utils.pager(m_tickets, 6, True)),
                    '```'
                ])
                await self.update()
                await interaction.followup.send(
                    '\n'.join([
                        'Gave {} tickets to {}'.format(len(res), user.mention),
                        'Current ticets: {}/{}'.format(len(m_tickets), self.lottery['max']),
                        listing,
                        '*Tickets left: {}/{}*'.format(
                            len([i for i in self.tickets if self.tickets[i] == 0]), len(self.tickets)
                        )
                    ])
                )
        elif action == 'remove':
            m_tickets = [i for i in self.tickets if self.tickets[i] == user.id]
            remove = [str(i) for i in ticket_list if str(i) in m_tickets]
            for i in remove: self.tickets[i] = 0
            remove.sort()
            listing = '\n'.join([
                '```js',
                '\n'.join(' '.join([
                    i.rjust(3) for i in entry
                ]) for entry in utils.pager(remove, 6, True)),
                '```'
            ])
            await self.update()
            await interaction.followup.send(
                'Removed {} tickets from {}: {}'.format(
                    len(remove), user.mention, listing
                )
            )

    @checks.perms(guild=True, mod=True)
    @app_commands.command(name='end')
    async def _app_end(self, interaction: discord.Interaction):
        '''
        End the guild lottery
        '''
        await interaction.response.defer(thinking=True)
        if not self.author: return interaction.followup.send('There is no lottery running...')
        await interaction.followup.send('Ending the lottery...')
        countdown = await self.announcement.send(f'{self.role.mention} Drawing winning number in 5...')  # type: ignore
        for i in range(4):
            await sleep(1)
            await countdown.edit(content=f'{self.role.mention} Drawing winning number in {4 - i}...')  # type: ignore
        await sleep(1)
        await countdown.edit(content=f'{self.role.mention} Drawing winning number...', delete_after = 600)  # type: ignore
        await sleep(2)
        timestamp = discord.utils.utcnow()
        self.lottery.update({
            'timestamp': (self.lottery['start'], timestamp.timestamp()),
            'tickets': dict(self.tickets),
            'winner': choice([i for i in self.lottery]),
        })
        sold = len([i for i in self.tickets if self.tickets[i]])
        embed = discord.Embed(
            title='Lottery results',
            description='The winning number is: **{}**'.format(self.lottery['winner']),
            timestamp=timestamp,
            color=0xFF0000
        )
        if self.tickets[self.lottery['winner']]:
            embed.color = 0x00FF00
            embed.add_field(
                name='Winner', value='<@{}>'.format(self.tickets[self.lottery['winner']])
            ).add_field(
                name='Tax', value='{:,.0f}'.format(sold * self.lottery['tax'] * self.lottery['price'])
            ).add_field(
                name='Prize', value='{:,.0f}'.format(sold * (1 - self.lottery['tax']) * self.lottery['price'])
            )
        embed.add_field(
            name='Tickets sold', value='{}/{}'.format(sold, len(self.tickets))
        ).add_field(
            name='Price per ticket', value='{:,d}'.format(self.lottery['price'])
        ).add_field(
            name='Total', value='${:,d}'.format(sold * self.lottery['price'])
        )
        await self.announcement.send(  # type: ignore
            '\n'.join([i for i in [
                'Congratulations!' if self.tickets[self.lottery['winner']] else None,
                'The jackpout number is **{}**!',
                '<@{}> won **${:,.0f}**!!!'.format(
                    self.tickets[self.lottery['winner']], sold * (1 - self.lottery['tax']) * self.lottery['price']
                ) if self.tickets[self.lottery['winner']] else 'Unfortunately, nobody bought it. Better luck next time.'
            ] if i is not None]),
            embed=embed
        )
        await self.clear()

    async def get_tickets(self, ctx, user):
        if isinstance(ctx, discord.Interaction):
            await ctx.response.defer(thinking=True)
            send_message = ctx.followup
        else:
            send_message = ctx
        if not self.tickets: return send_message.send('Data not available')
        if user and user == self.bot.user.id:  # type: ignore
            tickets = [(k, v) for k, v in self.tickets.items()]
        else:
            tickets = [(k, v) for k, v in self.tickets.items() if v == (0 if user is None else user.id)]
        await Paginator(
            entries=tickets,
            parser=lambda x: '{} - {}'.format(x[0], 'Available' if x[1] == 0 else '<@{}>'.format(x[1])),
            title='Lottery tickets',
            footer=self.author,
            timeout=60,
            color=getrandbits(24)
        ).paginate(ctx)

    async def update(self):
        bought = len([i for i in self.lottery.values() if i != 0])
        embed = discord.Embed(
            title='{} started a lottery'.format(self.author.display_name),  # type: ignore
            description='\n'.join([
                'There are {:,d} tickets in total. The price is **${:,d}** per ticket, and each person cannot buy more than {:,d} tickets.'.format(
                    self.lottery['tickets'], self.lottery['price'], self.lottery['max']
                ),
                'The winner gets {:,.2%} of the tickets sold, and the rest will go to our guild funds.'.format(1-self.lottery['tax']),
                'Give your money to <@{}> and pick your lottery numbers. First come first served.'.format(self.lottery['author']),
                'You can see which tickets are available with `bea lottery tickets`.'
            ]),
            timestamp=datetime.datetime.fromtimestamp(self.lottery['timestamp'], tz=datetime.timezone.utc),
            color=0x42aaf5
        ).set_author(name=self.author, icon_url=self.author.display_avatar.url).set_footer(  # type: ignore
            text='Tickets bought: {:,d}/{:,d} | Total rewards: ${:,.0f}'.format(
                bought, len(self.tickets), (1-self.lottery['tax']) * bought * self.lottery['price']
            )
        )
        if 'message' in self.lottery:
            await self.announcement.get_partial_message(self.lottery['message']).edit(content=self.role.mentioned, embed=embed)  #type: ignore
        else:
            message = await self.announcement.send(content=self.role.mentioned, embed=embed)  #type: ignore
            self.lottery['message'] = message.id
            await self.bot.redis.hset('lottery:config', 'message', message.id)

    def check_validity(self, uid, tickets):
        free_tickets = [int(i) for i in self.tickets if self.tickets[i] == 0]
        user_tickets = [int(i) for i in self.tickets if self.tickets[i] == uid]
        buyable = [i for i in tickets if i in free_tickets]
        if len(buyable) + len(user_tickets) > self.lottery['max']: return None
        buyable.sort()
        return buyable

    def parse_tickets(self, tickets):
        buys = []
        free_tickets = [int(i) for i in self.tickets if self.tickets[i] == 0]
        for arg in tickets:
            arg = arg.lower()
            if arg.startswith('first'):
                if arg[5:].isdecimal():
                    buys += free_tickets[:int(arg[5:])]
            elif arg.startswith('last'):
                if arg[4:].isdecimal():
                    buys += free_tickets[(0-int(arg[4:])):]
            elif arg.startswith('random'):
                if arg[6:].isdecimal():
                    buys += sample(free_tickets, k=int(arg[6:]))
            elif arg.find('-') > 0:
                res = re.findall('(\d+)-(\d+)', arg)[0]  # type: ignore
                if res[0] and res[1]:
                    for i in range(int(res[0]) - 1, int(res[1])):
                        buys.append(i)
            elif arg.isdecimal():
                buys.append(int(arg) - 1)
            free_tickets = list(set(free_tickets) - set(buys))
        return buys

    async def clear(self):
        if self.lottery:
            embed = embeds.report(self.lottery)
            await self.bot.log_event('lottery', embed=embed)
            await self.bot.redis.lpush('report:lottery', json.dumps(self.lottery))
        self.author = None

async def setup(bot):
    await bot.add_cog(Lottery(bot))