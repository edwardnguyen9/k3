from discord import app_commands
from discord.ext import commands

class SlashOnly(commands.CheckFailure):
    """ Exception raised for commands that have been moved to slash """
    def __str__(self):
        return 'This command is now a slash command.'

class InsufficientPermissions(commands.CheckFailure):
    '''
    Exception raised when user does not have the permission to use the command.
    '''
    def __init__(self, message=None):
        self.message = message or 'You don\'t have permission to use this command.'

    def __str__(self):
        return self.message

class InsufficientAppPermissions(app_commands.CommandInvokeError):
    '''
    Exception raised when user does not have the permission to use the command.
    '''
    def __init__(self, message=None):
        self.message = message or 'You don\'t have permission to use this command.'

    def __str__(self):
        return self.message

class CommandOnCooldown(commands.CommandInvokeError):
    '''
    Exception raised when the command is on cooldown.
    '''
    def __init__(self, cooldown):
        self.retry_after = cooldown

class AppCommandOnCooldown(app_commands.CommandInvokeError):
    '''
    Exception raised when the command is on cooldown.
    '''
    def __init__(self, cooldown):
        self.retry_after = cooldown

class NoChoice(commands.CommandInvokeError):
    '''
    Exception raised when no option is selected.
    '''
    def __str__(self):
        return 'You did not choose anything.'

class TooManyRequests(commands.CommandInvokeError):
    '''
    Exception raised when there are too many requests (Err. 429).
    '''
    def __str__(self):
        return 'Too many API requests have been made. Please try again in a few seconds.'

class TooManyAppRequests(app_commands.CommandInvokeError):
    '''
    Exception raised when there are too many requests (Err. 429).
    '''
    def __str__(self):
        return 'Too many API requests have been made. Please try again in a few seconds.'

class ApiYes(commands.CommandInvokeError):
    '''
    Exception raised when the API is available.
    '''
    def __str__(self):
        return 'The command is unavailable when the API is available.'

class ApiNo(commands.CommandInvokeError):
    '''
    Exception raised when the API is available.
    '''
    def __str__(self):
        return 'The command is unavailable when the API is unavailable.'

class ApiIsDead(commands.CommandInvokeError):
    '''
    Exception raised when the API is unavailable (Error 5xx).
    '''
    def __init__(self, status = None, ttl = None):
        self.status = status
        self.ttl = ttl

class ApiDisabled(commands.CommandInvokeError):
    '''
    Exception raised when API-related features are disabled.
    '''
    def __str__(self):
        return 'API-related features are disabled.'

class AppApiYes(app_commands.CommandInvokeError):
    '''
    Exception raised when the API is available.
    '''
    def __str__(self):
        return 'The command is unavailable when the API is available.'

class AppApiNo(app_commands.CommandInvokeError):
    '''
    Exception raised when the API is available.
    '''
    def __str__(self):
        return 'The command is unavailable when the API is unavailable.'

class AppApiIsDead(app_commands.CommandInvokeError):
    '''
    Exception raised when the API is unavailable (Error 5xx).
    '''
    def __init__(self, status = None, ttl = None):
        self.status = status
        self.ttl = ttl

class AppApiDisabled(app_commands.CommandInvokeError):
    '''
    Exception raised when API-related features are disabled.
    '''
    def __str__(self):
        return 'API-related features are disabled.'

class EventInProgress(app_commands.CommandInvokeError):
    '''
    Exception raised when another event is in progress.
    '''
    def __init__(self, evt):
        self.evt = evt

    def __str__(self):
        return 'Another {.evt} is already in progress. Please try again later.'.format(self)

class MissingRequiredArgument(commands.BadArgument):
    '''
    Exception raised when no argument is provided.
    '''
    def __init__(self, arguments: list):
        self.arguments = arguments

    def __str__(self):
        return 'You need to provide at least one of these values: {}'.format(', '.join(self.arguments))

class InvalidInput(commands.BadArgument):
    '''
    Exception raised when user is a dumb monkey.
    '''
    def __init__(self, name, input):
        self.name = name
        self.input = input

    def __str__(self):
        return 'Invalid value for `{0.name}`: ```\n{0.input}```'.format(self)

class InvalidArenaTarget(commands.BadArgument):
    '''
    Exception raised when picking the wrong arena target.
    '''
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

class OutOfRange(commands.BadArgument):
    '''
    Exception raised when the value is out of range.
    '''
    def __init__(self, value, name = 'Value', min = None, max = None, include = False):
        self.value = value
        self.name = name
        if min and max: self.message = 'needs to be between {} and {}'.format(min, max)
        elif min: self.message = '{} than `{}`'.format('cannot be less' if include else 'has to be greater', min)
        elif max: self.message = '{} than `{}`'.format('cannot be greater' if include else 'has to be less', max)
    
    def __str__(self):
        return '{0.name} out of range: `{0.value}`. It {0.message}.'.format(self)

class NoEmbedPage(ValueError):
    '''
    Exception raised when Paginator failed to generate any embed page
    '''
    def __str__(self):
        return 'Not enough data to generate an embed page.'

class DuplicatedInput(commands.BadArgument):
    '''
    Exception raised with duplicated input.
    '''
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message