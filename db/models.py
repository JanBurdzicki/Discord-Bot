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
