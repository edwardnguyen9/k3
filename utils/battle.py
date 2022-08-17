import discord

from assets import idle, config
from classes.profile import Profile
from classes.battle import Fighter


async def background_fetch(bot, mode, registered, waitlist, disqualified, message, private, guildlist, *, tier = None, belthazor_prev = {}):
    if len(waitlist) > 0:
        user = bot.get_user(waitlist[0])
        # raid_building = int(await bot.redis.get('raidbuilding'))
        # u_id = waitlist[count]
        # count += 1
        # fetched_user = await bot.fetch_user(u_id)
        fighter = await bot.get_equipped(str(user.id), orgs=False)
        if not fighter:
            waitlist.remove(user.id)
            disqualified.append(user.id)
            await bot.log_event('tourney' if 'tourney' in mode else 'raid', message=f'{user} disqualified from the {mode} in {message.guild.name}')
            try:
                await user.send('Unable to fetch your character.')
            except discord.Forbidden:
                pass
        else:
            # server = await redis.get_server_cfg(bot, message.guild)
            if private and fighter.guild not in guildlist:
                waitlist.remove(user.id)
                disqualified.append(user.id)
                await bot.log_event('tourney' if 'tourney' in mode else 'raid', message=f'{user} disqualified from the {mode} in {message.guild.name}')
                try:
                    await user.send('Guests cannot join this event.', delete_after=300)
                except discord.Forbidden:
                    pass
            elif tier is None:
                bonus = (
                    0.3 if ('belthazor' in mode.lower() and user.id == belthazor_prev['lucky'])
                    else 0.1 if ('belthazor' in mode.lower() and user.id in belthazor_prev['survivors']) 
                    else 0
                )
                fighter.raidstats = [i + bonus for i in fighter.raidstats]
                stats = fighter.fighter_data('fistfight' not in mode)
                participant = Fighter(
                    user=user,
                    dmg=stats[0],
                    amr=stats[1],
                    atkm=stats[2],
                    defm=stats[3],)
                if 'city' in mode.lower(): participant.hp = 250
                waitlist.remove(user.id)
                registered[user.id] = participant
                try:
                    await user.send(
                        'You joined the {type} in **{server}**.\nYour stats have been recorded, and any modification will not change them now.'.format(
                            type = mode,
                            server = message.guild.name
                        )
                    )
                except discord.Forbidden:
                    pass
                await bot.log_event('tourney' if 'tourney' in mode else 'raid', message=f'{user} joined the {mode} in {message.guild.name}')
            else:
            # elif (
            #     'tourney' not in config.config[message.guild.id]['misc']
            #     or (t:=discord.utils.find(lambda x: x[1] == tier, config.config[message.guild.id]['misc']['tourney']['tiers']))[0] is None
            #     or fighter.level <= t[0]
            # ):
                stats = fighter.fighter_data('fistfight' not in mode)
                participant = Fighter(
                    user=user,
                    dmg=stats[0],
                    amr=stats[1],
                    atkm=stats[2],
                    defm=stats[3],)
                registered[user.id] = participant
                waitlist.remove(user.id)
                try:
                    await user.send(
                        'You joined the {type} in **{server}**.\nYour stats have been recorded, and any modification will not change them now.'.format(
                            type = mode,
                            server = message.guild.name
                        )
                    )
                except discord.Forbidden:
                    pass
                await bot.log_event('tourney' if 'tourney' in mode else 'raid', message=f'{user} joined the {mode} in {message.guild.name}')
            # else:
            #     count -= 1
            #     waitlist.remove(u_id)
            #     disqualified.append(u_id)
            #     await message.remove_reaction('\u2694', fetched_user)
            #     try:
            #         await fetched_user.send('You do not meet the level requirement.', delete_after=300)
            #     except discord.Forbidden:
            #         pass
            #     await log_event(bot, 'tourney' if 'tourney' in mode else 'raid', message=f'{fetched_user} disqualified from the {mode} in {message.guild.name}')

