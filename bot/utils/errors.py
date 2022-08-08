from humanize import precisedelta

class KiddoException(Exception):
    """ Main Kiddo exception class """
    def __init__(self, ctx):
        self.context = ctx

class SlashOnly(KiddoException):
    """ Exception raised for commands that have been moved to slash """
    def __init__(self, ctx):
        self.context = ctx

    def __str__(self):
        return 'This command is now a slash command.'

class InsufficientPermissions(KiddoException):
    '''
    Exception raised when user does not have the permission to use the command.
    '''
    def __init__(self, ctx, message=None):
        self.context = ctx
        self.message = message or 'You don\'t have permission to use this command.'

    def __str__(self):
        return self.message

class CommandOnCooldown(KiddoException):
    '''
    Exception raised when the command is on cooldown.
    '''
    def __init__(self, ctx, cooldown):
        self.context = ctx
        self.retry_after = cooldown

    def __str__(self):
        return '`{}` will be available in {}.'.format(self.context.command.qualified_name, precisedelta(self.retry_after))

class NoChoice(KiddoException):
    '''
    Exception raised when no option is selected.
    '''
    def __init__(self, ctx):
        self.context = ctx

    def __str__(self):
        return 'You did not choose anything.'

class TooManyRequests(KiddoException):
    '''
    Exception raised when there are too many requests (Err. 429).
    '''
    def __init__(self, ctx):
        self.context = ctx

    def __str__(self):
        return 'Too many API requests have been made. Please try again in a few seconds.'

class ApiYes(KiddoException):
    '''
    Exception raised when the API is available.
    '''
    def __init__(self, ctx):
        self.context = ctx

    def __str__(self):
        return '`{}` can only be used when the API is unavailable.'

class ApiNo(KiddoException):
    '''
    Exception raised when the API is unavailable.
    '''
    def __init__(self, ctx):
        self.context = ctx

    def __str__(self):
        return '`{}` can only be used when the API is available.'

class ApiIsDead(KiddoException):
    '''
    Exception raised when the API is unavailable (Error 5xx).
    '''
    def __init__(self, ctx, status = None, ttl = None):
        self.context = ctx
        self.status = status
        self.ttl = ttl

class ApiDisabled(KiddoException):
    '''
    Exception raised when API-related features are disabled.
    '''
    def __init__(self, ctx):
        self.context = ctx

    def __str__(self):
        return 'API-related features are disabled.'

class EventInProgress(KiddoException):
    '''
    Exception raised when another event is in progress.
    '''
    def __init__(self, ctx, evt):
        self.context = ctx
        self.evt = evt

    def __str__(self):
        return 'Another {.evt} is already in progress. Please try again later.'.format(self)

class MissingRequiredArgument(KiddoException):
    '''
    Exception raised when no argument is provided.
    '''
    def __init__(self, ctx, arguments: list):
        self.context = ctx
        self.arguments = arguments

    def __str__(self):
        return 'You need to provide at least one of these values: {}'.format(', '.join(self.arguments))

class InvalidInput(KiddoException):
    '''
    Exception raised when user is a dumb monkey.
    '''
    def __init__(self, ctx, name, input):
        self.context = ctx
        self.name = name
        self.input = input

    def __str__(self):
        return 'Invalid value for `{0.name}`: ```\n{0.input}```'.format(self)

class InvalidArenaTarget(KiddoException):
    '''
    Exception raised when picking the wrong arena target.
    '''
    def __init__(self, ctx, message):
        self.context = ctx
        self.message = message

    def __str__(self):
        return self.message

class OutOfRange(KiddoException):
    '''
    Exception raised when the value is out of range.
    '''
    def __init__(self, ctx, value, name = 'Value', min = None, max = None, include = False):
        self.context = ctx
        self.value = value
        self.name = name
        if min and max: self.message = 'needs to be between {} and {}'.format(min, max)
        elif min: self.message = '{} than `{}`'.format('cannot be less' if include else 'has to be greater', min)
        elif max: self.message = '{} than `{}`'.format('cannot be greater' if include else 'has to be less', max)
    
    def __str__(self):
        return '{0.name} out of range: `{0.value}`. It {0.message}.'.format(self)

class NoEmbedPage(KiddoException):
    '''
    Exception raised when Paginator failed to generate any embed page
    '''
    def __init__(self, ctx):
        self.context = ctx

    def __str__(self):
        return 'Not enough data to generate an embed page.'

class DuplicatedInput(KiddoException):
    '''
    Exception raised with duplicated input.
    '''
    def __init__(self, ctx, message):
        self.context = ctx
        self.message = message

    def __str__(self):
        return self.message