from datetime import datetime

class AvailabilityTracker:
    def __init__(self):
        self.attendance_log = {}

    def record_attendance(self, user_id: int, date: datetime) -> None:
        if user_id not in self.attendance_log:
            self.attendance_log[user_id] = []
        self.attendance_log[user_id].append(date)

    def get_availability(self, user_id: int) -> float:
        # Return a dummy float for now
        return float(len(self.attendance_log.get(user_id, [])))

    def get_inactive_users(self) -> list:
        # Return users with no attendance
        return [uid for uid, log in self.attendance_log.items() if not log]
