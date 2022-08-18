class Tribute:
    def __init__(self, user):
        self.user = user
        self.food = 5
        self.canned = 0
        self.knife = 0
        self.clothes = 0
        self.kit = 0
        self.rifle = False
        self.explosive = 0
        self.wounded = 0
        self.annoyed = False
        self.relationship = dict()
        self.options = []

    def impression(self, user, action):
        key = str(user.id)
        value = 0
        if action == 'attack':
            value = -10
        elif action == 'annoy':
            value = -3
        elif action == 'ally':
            value = 5
        elif action == 'movie' or action == 'tod':
            value = 2
        elif action == 'group' or action == 'picnic' or action == 'silence':
            value = 3
        elif action == 'sleep' or action == 'dinner' or action == 'snuck':
            value = 5
        elif action == 'stargaze':
            value = 7
        elif action == 'kiss':
            value = 10
        if key not in self.relationship:
            self.relationship[key] = value
        else:
            self.relationship[key] += value
    
    def available_option(self, option: str, target = None):
        for o in self.options:
            if o.option.startswith(option):
                if o.target is None: return False
                if o.target is not None and target is not None and o.target.user.id == target.user.id:
                    return False
        return True

class ArenaChoice:
    def __init__(self, option: str, target = None):
        self.option = option
        self.target = target

class Field:
    def __init__(self):
        self.weather = 'clr'
        self.explosive = 0
        self.sniper = False
        self.day = 0
        self.no_deaths = 0
        self.wolf = 0
        self.mask = {'real': None, 'fake': None}