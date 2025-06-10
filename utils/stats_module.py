from db.models import UserProfile

class StatsModule:
    def __init__(self):
        self.usage_logs = []

    def log_usage(self, user_id: int, command: str) -> None:
        self.usage_logs.append({'user_id': user_id, 'command': command})

    def top_participants(self) -> list:
        # Dummy implementation
        return []

    def get_stats_summary(self) -> dict:
        # Dummy implementation
        return {}
