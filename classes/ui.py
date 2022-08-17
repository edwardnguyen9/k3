import discord, traceback, asyncio

class RaidAnnouncement(discord.ui.View):
    def __init__(self, confirmed = None, cancelled = None):
        super().__init__(timeout=10)
        self.value = None
        self.confirmed = confirmed
        self.cancelled = cancelled

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Send new announcements', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.confirmed:
            await interaction.response.send_message(self.confirmed, ephemeral=True)
        self.value = True
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Delete announcements', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.cancelled:
            await interaction.response.send_message(self.cancelled, ephemeral=True)
        self.value = False
        self.stop()

class Join(discord.ui.View):
    def __init__(self, *, waitlist: list = [], participants: dict = {}, banlist: list = [], label: str = 'guild raid', msg = []):
        super().__init__(timeout=None)
        # self.reg_period = timeout
        self.label = label or 'guild raid'
        self.msg = msg
        self.waitlist = waitlist
        self.participants = participants
        self.banlist = banlist
        self.button = discord.ui.Button(label=f'Join the {label}!', style=discord.ButtonStyle.blurple)
        self.button.callback = self.join
        self.add_item(self.button)
        self.content = None
        self.reacted = []

    async def join(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        if interaction.user.id in self.banlist:
            await interaction.followup.send('You cannot join this {}.'.format(self.label), ephemeral=True)
        elif interaction.user.id in self.reacted:
            await interaction.followup.send('Contrary to popular belief, clicking on a button repeatedly generally does not change anything.', ephemeral=True)
        else:
            self.reacted.append(interaction.user.id)
            self.waitlist.append(interaction.user.id)
            while True:
                await asyncio.sleep(2)
                if interaction.user.id not in self.waitlist: break
            if interaction.user.id in self.banlist:
                await interaction.followup.send('You cannot join this {}.'.format(self.label), ephemeral=True)
            else:
                await interaction.followup.send('You joined the {}.'.format(self.label), ephemeral=True)
                if self.content is None: self.content = self.msg[0].content
                joined_list = [i for i in self.participants if i in self.reacted]
                await self.msg[0].edit(
                    content='\n'.join([
                        self.content,
                        ' '.join(map(lambda x: f'<@{x}>', joined_list)) + 'joined the {}.'.format(self.label)
                    ])
                )
    

class Confirm(discord.ui.View):
    def __init__(self, count = []):
        super().__init__()
        self.counter = 0
        self.count = count

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Count', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.counter += 1
        if self.count: await self.count[0].edit(content=str(self.counter))
        if self.counter == 10: self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    # @discord.ui.button(label='No', style=discord.ButtonStyle.red)
    # async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     if self.cancelled:
    #         await interaction.response.send_message(self.cancelled, ephemeral=True)
    #     self.value = False
    #     self.stop()

class Feedback(discord.ui.Modal, title='Feedback'):
    # Our modal classes MUST subclass `discord.ui.Modal`,
    # but the title can be whatever you want.

    # This will be a short input, where the user can enter their name
    # It will also have a placeholder, as denoted by the `placeholder` kwarg.
    # By default, it is required and is a short-style input which is exactly
    # what we want.
    name = discord.ui.TextInput(
        label='Name',
        placeholder='Your name here...',
    )

    # This is a longer, paragraph style input, where user can submit feedback
    # Unlike the name, it is not required. If filled out, however, it will
    # only accept a maximum of 300 characters, as denoted by the
    # `max_length=300` kwarg.
    feedback = discord.ui.TextInput(
        label='What do you think of this new feature?',
        style=discord.TextStyle.long,
        placeholder='Type your feedback here...',
        required=False,
        max_length=300,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'Thanks for your feedback, {self.name.value}!', ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_tb(error.__traceback__)