class UserProfile:
    def __init__(self, discord_id: int, calendar_email: str, preferences: dict = None, roles: list = None):
        self.discord_id = discord_id
        self.calendar_email = calendar_email
        self.preferences = preferences or {}
        self.roles = roles or []

class CalendarEvent:
    def __init__(self, event_id: str, title: str, start_time, end_time):
        self.event_id = event_id
        self.title = title
        self.start_time = start_time
        self.end_time = end_time

class UserToken:
    def __init__(self, discord_id: int, token_data: dict):
        self.discord_id = discord_id
        self.token_data = token_data

class Poll:
    def __init__(self, poll_id: str, question: str, options: list, creator_id: int, is_advanced: bool = False, external_id: str = None):
        self.poll_id = poll_id
        self.question = question
        self.options = options
        self.creator_id = creator_id
        self.is_advanced = is_advanced
        self.external_id = external_id  # For advanced polls (e.g., StrawPoll ID)
        self.votes = {}  # user_id -> option_index
        self.active = True

class Vote:
    def __init__(self, poll_id: str, user_id: int, option_index: int, timestamp):
        self.poll_id = poll_id
        self.user_id = user_id
        self.option_index = option_index
        self.timestamp = timestamp
