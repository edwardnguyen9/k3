import discord, json, asyncio
from discord import app_commands
from discord.ext import commands
from typing import Union, Optional

from bot.bot import Kiddo
from classes import battle
from classes.paginator import Paginator
from utils import errors, utils, embeds, checks

class Arena(commands.GroupCog, group_name='arena'):
    '''
    Arena commands
    '''
    def __init__(self, bot: Kiddo):
        self.bot = bot
        self.is_first_ready = True
        self.protected = True
        self.guild_id = 821988363308630068

    @commands.Cog.listener()
    async def on_ready(self):
        if self.is_first_ready:
            await self.bot.loading()
            print(self.__class__.__name__, 'is ready')
            self.is_first_ready = False

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        role_list = utils.get_role_ids('arena', self.bot.event_config)
        roles = [i[1] for i in role_list]
        for r in roles:
            if member.get_role(r):
                (
                    await self.bot.redis.pipeline(transaction=True)
                        .hdel('arena', str(r))
                        .hdel('falseprotection', str(r))  # type: ignore
                        .delete(f'a{r}')
                )
                break

    @checks.perms(False, guild=True)
    @commands.group(
        invoke_without_command=True,
        name='arena',
        brief='Get arena title holders',
        description='Get a list of arena titles and their holders',
        usage='',
        help='''
        - All title holders can auto-join raids, have access to citizen arrest and break out, and more
        - Title holders have a chance to be selected as a boss in Belthazor/Impostor raids
        - If you win a title, there's a "protection" period before you can be challenged:
        {arena}

        {arena_officer}
        Note: title holders don't activate protection periods when winning another title
        '''
    )
    async def _arena(self, ctx: commands.Context):
        await self._titles(ctx)

    @checks.perms(False, guild=True)
    @_arena.command(
        name='challenge',
        brief='Challenge a title holder',
        description='Challenge an arena title holder to a set of 5 raid battles',
        usage='<title>',
        help='''
        > <title>: The title you wish to challenge
        - A challenge match is a set of 5 raid battles, and the best of 3 wins
        - The challenger goes first in the first match, and the loser goes first in subsequent matches
        - If a challenger wins, they become the title holder of the arena they challenged
        - A title holder's stats are their stats during their challenge match, and changing race, class, weapons, or raidstats won't have any effect on them
        '''
    )
    async def _challenge(self, ctx: commands.Context, target: Union[discord.Role, discord.Member]):
        return await ctx.send(target.mention, allowed_mentions=discord.AllowedMentions.none())

    @checks.perms(False, guild=True)
    @_arena.command(
        name='history',
        brief='Get arena challenge history',
        description='Get the last 50 arena challenge results',
        usage='<fighter>',
        help='''
        > <fighter>: Only get results involving this fighter
        '''
    )
    async def _history(self, ctx: commands.Context, fighter: Optional[discord.Member] = None):
        await self._arena_history(ctx, fighter, 50)

    @checks.perms(guild=True)
    @app_commands.command(name='titles')
    async def _app_arena(self, interaction: discord.Interaction):
        '''
        Get a list of arena titles and their holders
        '''
        await self._titles(interaction)

    @checks.perms(guild=True)
    @app_commands.describe(target='The title or title holder')
    @app_commands.command(name='challenge')
    async def _app_challenge(self, interaction: discord.Interaction, target: Union[discord.Role, discord.Member]):
        '''
        Challenge an arena title holder
        '''
        await interaction.response.send_message(target.mention, ephemeral=True)

    @checks.perms(guild=True)
    @app_commands.describe(
        fighter='Only get challenges involving this player', limit='Max number of results'
    )
    @app_commands.command(name='history')
    async def _app_history(self, interaction: discord.Interaction, fighter: Optional[discord.Member] = None, limit: app_commands.Range[int, 5, 100] = 50):
        '''
        Get arena challenge history
        '''
        await self._arena_history(interaction, fighter, limit)

    async def _arena_history(self, ctx, fighter, limit):
        if isinstance(ctx, discord.Interaction):
            await ctx.response.defer(thinking=True)
            send_message = ctx.followup
        else:
            send_message = ctx
        if not ctx.guild: return
        f = None
        if fighter: f = str(fighter.id)
        br = await self.bot.redis.hget('ah', str(ctx.guild.id))
        if not br: return await send_message.send('No data available.')
        br = json.loads(br)[:limit]
        if f is not None: br = [i for i in br if f in i]
        await Paginator(
            title=f'{ctx.guild.name}\'s Last {len(br)} Arena Challenges',
            entries=br,
            length=5,
            xtraline=1
        ).paginate(ctx)

    async def _titles(self, ctx):
        if isinstance(ctx, discord.Interaction):
            await ctx.response.defer(thinking=True)
            author, send_message = ctx.user, ctx.followup
        else:
            author, send_message = ctx.author, ctx
        if ctx.guild is None: return
        elif ctx.guild.id != 821988363308630068: raise errors.InsufficientPermissions(ctx, 'This feature is only available in Guild Bill server.')
        role_list = utils.get_role_ids('arena', self.bot.event_config)
        roles = [ctx.guild.get_role(i[1]) for i in role_list]
        roles = [r for r in roles if r is not None]
        
        async with self.bot.redis.pipeline(transaction=True) as pipe:
            for i in role_list: pipe.ttl(f'a{i[1]}').hget('arena', i[1])  # type: ignore
            res = await pipe.execute()
        
        total = len(role_list)
        now = discord.utils.utcnow()
        cd = [int(i + now.timestamp()) for i in res[::2]]
        defenders = [(json.loads(i) if i is not None else None) for i in res[1::2]]
        
        content = []
        for i in range(total):
            content.append('\n'.join([
                x for x in [
                    '**Title:** {}'.format(roles[i].mention),
                    '**Protection period:** {}'.format(utils.get_timedelta(role_list[i][2])),
                    '**Holder:** <@{}>'.format(defenders[i]['id']) if defenders[i] is not None and ctx.guild.get_member(defenders[i]['id']) else None,  # type: ignore
                    '**Strength:** {:.1f}'.format( defenders[i]['dmg'] * defenders[i]['ratk'] + defenders[i]['amr'] * defenders[i]['rdef']) if defenders[i] is not None and ctx.guild.get_member(defenders[i]['id']) else None,  # type: ignore
                    'Available to claim <t:{}:R>'.format(cd[i]) if defenders[i] is not None and ctx.guild.get_member(defenders[i]['id']) and cd[i] > now.timestamp() else None  # type: ignore
                ] if x is not None
            ]))

        entries = utils.pager(content, 5, True)

        pages = []
        for i in entries:
            pages.append(
                discord.Embed(
                    title=f'{ctx.guild.name}\'s Arena Titles',
                    color=roles[0].color.value,
                    timestamp=now,
                    description='\n\n'.join(i)
                ).set_footer(
                    text='#{}'.format(self.bot.get_channel(self.bot.event_config['channels']['arena:battle'])), icon_url=author.display_avatar.url
                )
            )
        if len(pages) == 1:
            await send_message.send(embed=pages[0])
        else:
            return await Paginator(extras=pages).paginate(ctx)

    async def setup_challenge(self, ctx, target):
        # Hybrid
        if isinstance(ctx, discord.Interaction):
            await ctx.response.defer(thinking=True)
            author, send_message = ctx.user, ctx.followup
        else:
            author, send_message = ctx.author, ctx
        # This probably never happens with the hardcoding
        if ctx.guild is None: return
        if ctx.guild is None: return
        elif ctx.guild.id != 821988363308630068: raise errors.InsufficientPermissions(ctx, 'This feature is only available in Guild Bill server.')
        role_list = utils.get_role_ids('arena', self.bot.event_config)
        roles = [ctx.guild.get_role(i[1]) for i in role_list]
        # Check if target is valid and title has only one defender
        title = None
        if isinstance(target, discord.Member):
            for i in role_list:
                if (title:=target.get_role(i[1])) is not None: break
        elif target in roles: title = target
        if title is None:
            return await send_message.send('{.mention} is not a valid arena target'.format(target), allowed_mentions=discord.AllowedMentions.none())
        elif len(title.members) > 1:
            return await send_message.send('An error has occurred which resulted in {.mention} having more than one defender. Maybe a guild officer can help sort things out.'.format(title))
        elif author.get_role(title.id):  # type: ignore
            return await send_message.send('You already have that title')
        # In case arena channel got deleted somehow
        channel = self.bot.get_channel(self.bot.event_config['channels']['arena:battle'])
        if not channel or not isinstance(channel, discord.abc.Messageable): return await send_message.send('Unable to find arena channel')
        # Redirect to arena channel if challenging in another channel
        elif channel.id != ctx.channel.id: return await send_message.send('Head to {.mention} to fight {.mention}'.format(channel, target), allowed_mentions=discord.AllowedMentions.none())  # type: ignore
        # TODO: Set up offline stats fetching
        if not self.bot.api_available:
            return await send_message.send('Under construction')
        # Get cooldown
        async with self.bot.redis.pipeline(transaction=True) as pipe:
            cd = await pipe.ttl(f'acd{ctx.guild.id}').ttl(f'acd{author.id}').execute()  # type: ignore
        cd = max([i or 0 for i in cd])
        if cd > 0: raise errors.CommandOnCooldown(ctx, cd)
        self.protected = True
        # Cooldown multiplier
        multiplier = 1
        # Whether the title is claimable
        claimable = True
        swappable = challenger = None
        # Get title defender data
        defender = await self.bot.redis.hget('arena', str(title.id))
        defender = json.loads(defender) if defender else None
        # Get title data
        defender_title_info = discord.utils.find(lambda x: x[1] == title.id, role_list) or []
        # Check if challenger is officer and defender is not (for max officer count)
        officers = self.bot.event_config['raid']['boss']
        if author.id in officers and (len(title.members) == 0 or title.members[0].id not in officers):
            # Get all title holders
            holders = [i.members[0].id for i in roles if i is not None and len(i.members) == 1]
            # Get number of officers holding titles
            limit = self.bot.event_config['arenas'][self.bot.event_config['arenas']['arena']]['officer_limit']
            if (
                len(set(holders).intersection(officers)) >= limit[0] # If max officers reached
                or defender_title_info[2] > limit[1] # If title rank is higher than what officers can hold
            ): claimable = False
        challenger_title = None
        # If defender is still in the guild
        if defender and ctx.guild.get_member(defender['id']):
            # Check if challenger also has a title
            for challenger_title_info in role_list:
                if challenger_title:=author.get_role(challenger_title_info[1]):  # type: ignore
                    # Add 1h cooldown
                    multiplier += 1
                    res = json.loads(await self.bot.redis.hget('arena', str(challenger_title.id)) or 'null')
                    # Use cached data of title holders
                    challenger = battle.Fighter(
                        author, name=res['name'],
                        dmg=res['dmg'],
                        amr=res['amr'],
                        atkm=res['ratk'],
                        defm=res['rdef']
                    )
                    # Cannot take if challenger title is higher
                    if challenger_title_info[2] > defender_title_info[2]:
                        claimable = False
                        # Penalty for challenging lower tiers (day difference)
                        multiplier += (challenger_title_info[2] - defender_title_info[2])/86400
                    else:
                        # Disable protection period for same/lower tier challenges
                        self.protected = False
                        # Check if title is in the same tier
                        if challenger_title_info[2] == defender_title_info[2]:
                            # Swap titles
                            swappable = (challenger_title, title)
            
        else:
            for challenger_title_info in role_list:
                if challenger_title:=author.get_role(challenger_title_info[1]): break  # type: ignore
        protected = False
        if defender is not None:
            defender = battle.Fighter(
                title.members[0], name=defender['name'],
                dmg=defender['dmg'], amr=defender['amr'],
                atkm=defender['ratk'], defm=defender['rdef']
            )
            if challenger is None:
                if self.bot.api_available:
                    p = await self.bot.get_equipped(author.id, orgs=False)
                    d, a, rd, ra = p.fighter_data()
                    challenger = battle.Fighter(author, name=p.name, dmg=d, amr=a, atkm=rd, defm=ra)
                    if p.guild != 17555: claimable = False
                else:
                    # TODO: Set up offline stats fetching
                    return
            # Add 1h to challenger if not claimable
            cd = await self.bot.redis.ttl(f'a{title.id}')
            if cd > 0:
                claimable = False
                protected = True
            if not claimable: multiplier += 1
            async with self.bot.redis.pipeline(transaction=True) as pipe:
                (
                    await pipe.ttl(f'a{title.id}')
                        .set(f'acd{ctx.guild.id}', author.id, ex=1800)  # type: ignore
                        .set(f'acd{author.id}', title.id, ex=3600 * multiplier)
                        .execute()
                )
            logs, jumpurl = [], []
            opponents = [[defender, 0], [challenger, 0]]
            await send_message.send(f'{author.mention} challenged {defender.user.mention} for the title of {title.mention}!', allowed_mentions=discord.AllowedMentions.none())
            start = discord.utils.utcnow()
            # Fight until someone gets 3 wins
            while opponents[0][1] < 3 and opponents[1][1] < 3:
                start_message = await channel.send(f'**Battle #{len(logs) + 1}**')
                jumpurl.append(start_message.jump_url)
                opponents, log = await battle.raid_battle(opponents, channel, True)
                logs.append(log)
                await channel.send(f'The winner is: {opponents[0][0].user.mention}', allowed_mentions=discord.AllowedMentions.none())
                opponents[0][1] += 1
                await asyncio.sleep(2)
            timestamp = discord.utils.utcnow()
            report = {
                'mode': 'arena',
                'title': (title.name, title.id, title.color.value),
                'challenger': [challenger.user.id, challenger.dmg, challenger.amr, challenger.atkm, challenger.defm],
                'defender': [defender.user.id, defender.dmg, defender.amr, defender.atkm, defender.defm],
                'logs': logs,
                'urls': jumpurl,
                'timestamp': (start.timestamp(), timestamp.timestamp())
            }
            # Logs
            battle_result = '{defender} {defscore} - {atkscore} {attacker}'.format(
                defender=defender.user.mention,
                attacker=challenger.user.mention,
                defscore=opponents[0][1] if opponents[0][0].user.id == defender.user.id else opponents[1][1],
                atkscore=opponents[1][1] if opponents[0][0].user.id == defender.user.id else opponents[0][1]
            )
            br = await self.bot.redis.hget('ah', str(ctx.guild.id))
            br = [] if br is None else json.loads(br)
            br.insert(0, f'**{title.name}**\n{battle_result}')
            await self.bot.redis.hset('ah', str(ctx.guild.id), json.dumps(br))
            
            opponents = [i[0] for i in opponents]
            # If defended
            if opponents[0].user.id == defender.user.id:
                res = await self.bot.redis.hget('falseprotection', str(title.id))
                # If title would've been claimed
                if claimable and not protected:
                    fp = json.loads(res) if res is not None else []
                    # If user hasn't triggered the false protection period
                    if opponents[1].user.id not in fp:
                        fp.append(opponents[1].user.id)
                        # Trigger it
                        report['results'] = 'protected'
                        async with self.bot.redis.pipeline(transaction=True) as pipe:
                            pipe.hset('falseprotection', str(title.id), json.dumps(fp)).set(f'a{title.id}', json.dumps(defender.user.id), ex=21600)  # type: ignore
                            await pipe.execute()
                await channel.send(
                    '{.mention} successfully defended the title {.mention}'.format(
                        defender.user, title
                    ),
                    allowed_mentions=discord.AllowedMentions.none()
                )
            else:
                if protected:
                    await channel.send(
                        '{.mention} is under protection and cannot lose the title {.mention}'.format(
                        defender.user, title
                    ),
                        allowed_mentions=discord.AllowedMentions.none()
                    )
                if not claimable:
                    report['results'] = 'lost'
                    await self.lose_title(title, defender.user, challenger.user)
                    await channel.send(
                        'Although {.mention} failed to defend the title {.mention}, {.mention} cannot take the title.'.format(
                            defender.user, title, challenger.user
                        ),
                        allowed_mentions=discord.AllowedMentions.none()
                    )
                elif swappable:
                    report['results'] = (swappable[0].name, swappable[0].id)
                    await self.swap_titles(channel, list(swappable))
                else:
                    report['results'] = 'stole'
                    await self.lose_title(title, defender.user, challenger.user)
                    await self.win_title(channel, title, challenger, defender.user)
            embed = embeds.report(report)
            await self.bot.log_event('arena', embed=embed)
            await self.bot.redis.lpush('report:arena', json.dumps(report))
        elif not claimable:
            return send_message.send('You cannot take this title.')
        else:
            if not self.bot.api_available:
                # TODO: Set up offline stats fetching
                return
            else:
                p = await self.bot.get_equipped(author.id, orgs=False)
                d, a, rd, ra = p.fighter_data()
                if p.guild != 17555: return send_message.send('You cannot take this title.')
                challenger = battle.Fighter(author, name=p.name, dmg=d, amr=a, atkm=rd, defm=ra)
            self.protection = False
            if challenger_title: await self.bot.redis.hdel('arena', str(challenger_title.id))
            return await self.win_title(send_message, title, challenger, None)
            
    async def win_title(self, channel, title, challenger, defender):
        role_list = utils.get_role_ids('arena', self.bot.event_config)
        roles = [i[1] for i in role_list]
        member = challenger.user
        if member is None: return
        for r in roles:
            role = member.get_role(r)
            if role:
                await member.remove_roles(role, reason='Claim title')
                break
        data = {
            'id': challenger.user.id,
            'name': challenger.name,
            'dmg': challenger.dmg,
            'amr': challenger.amr,
            'ratk': challenger.atkm,
            'rdef': challenger.defm
        }
        # await self.bot.redis.hset('arena', str(title.id), json.dumps(data))
        await member.add_roles(title, reason='Claim title')
        await channel.send(
            ' '.join([i for i in [
                member.mention,
                'beat {.mention} and'.format(defender) if defender is not None else None,
                'claimed the title {.mention}'.format(title)
            ] if i is not None])
        )
        await member.send(' '.join([i for i in [
            'You', 'claimed' if defender is None else 'took', 'the title **{.name}**'.format(title), 'from {.mention}'.format(defender) if defender else None
        ] if i is not None]) + '.')
        async with self.bot.redis.pipeline(transaction=True) as pipe:
            pipe.hset('arena', str(title.id), json.dumps(data)).hdel('falseprotection', str(title.id))  # type: ignore
            if self.protected:
                t = discord.utils.find(lambda x: x[1] == title.id, role_list)
                pipe.set(f'a{title.id}', json.dumps(member.id), ex=int(t[2]))  # type: ignore
            else:
                pipe.set(f'a{title.id}', json.dumps(member.id), ex=900)  # type: ignore
            await pipe.execute()
                
    async def lose_title(self, title: discord.Role, defender: discord.Member, challenger):
        await defender.remove_roles(title, reason='Lost title')
        await self.bot.redis.pipeline(transaction=True).hdel('arena', str(title.id)).set(f'acd{defender.id}', 'lost', ex=3600*6).execute()  # type: ignore
        await defender.send('You lost the title **{.name}**{}.'.format(title, '' if challenger is None else f' to {challenger.mention}'))

    async def swap_titles(self, channel, swappable: 'list[discord.Role]'):
        w, l = swappable[0].members[0], swappable[1].members[0]
        await w.remove_roles(swappable[0], reason='Swap title')
        await l.remove_roles(swappable[1], reason='Swap title')
        await w.add_roles(swappable[1], reason='Swap title')
        await l.add_roles(swappable[0], reason='Swap title')
        async with self.bot.redis.pipeline(transaction=True) as pipe:
            t0, t1 = (await pipe.hget('arena', str(swappable[0].id)).hget('arena', str(swappable[1].id)).execute())  # type: ignore
            await pipe.hset('arena', mapping={str(swappable[0].id): t1, str(swappable[1].id): t0}).set(f'acd{l.id}', 'lost', ex=3600*2).execute().execute()  # type: ignore
        await w.send('You took the title **{.name}** from {.mention}.'.format(swappable[1], l))
        await l.send('{.mention} beat you and claimed the title **{.name}**, leaving **{.name}** for you.'.format(w, swappable[1], swappable[0]))
        await channel.send(
            '{.mention} took {.mention} from {.mention}, leaving them with {.mention}'.format(
                w, swappable[1], l, swappable[0]
            )
        )
        async with self.bot.redis.pipeline(transaction=True) as pipe:
            await (
                pipe
                .set('a{}'.format(swappable[1].id), w.id, ex=900)
                .set('a{}'.format(swappable[0].id), l.id, ex=900)  # type: ignore
                .execute()
            )
        

async def setup(bot):
    await bot.add_cog(Arena(bot))