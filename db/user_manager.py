from .models import UserProfile

class UserManager:
    def __init__(self):
        self.users = {}

    def get_user(self, discord_id: int) -> UserProfile:
        return self.users.get(discord_id)

    def ensure_user(self, discord_id: int, calendar_email: str = "", roles: list = None) -> UserProfile:
        if discord_id not in self.users:
            self.users[discord_id] = UserProfile(
                discord_id=discord_id,
                calendar_email=calendar_email,
                roles=roles or [],
            )
        return self.users[discord_id]

    def add_user(self, user: UserProfile):
        self.users[user.discord_id] = user

    def update_preferences(self, discord_id: int, prefs: dict):
        user = self.get_user(discord_id)
        if user:
            user.preferences.update(prefs)

    def update_roles(self, discord_id: int, roles: list):
        user = self.get_user(discord_id)
        if user:
            user.roles = roles

    def assign_roles(self, user: UserProfile):
        # Logic to assign roles based on activity, etc.
        pass
