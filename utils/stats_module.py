from db.models import UserProfile, Vote
from collections import defaultdict
from datetime import datetime

class StatsModule:
    def __init__(self):
        self.usage_logs = []  # List of dicts: {'user_id', 'action', 'details', 'timestamp'}
        self.votes = []  # List of Vote objects
        self.poll_creations = defaultdict(int)  # user_id -> count

    def log_usage(self, user_id: int, action: str, details: dict = None):
        self.usage_logs.append({
            'user_id': user_id,
            'action': action,
            'details': details or {},
            'timestamp': datetime.utcnow()
        })

    def log_vote(self, vote: Vote):
        self.votes.append(vote)
        self.log_usage(vote.user_id, 'vote', {'poll_id': vote.poll_id, 'option_index': vote.option_index})

    def log_poll_creation(self, user_id: int, poll_id: str):
        self.poll_creations[user_id] += 1
        self.log_usage(user_id, 'create_poll', {'poll_id': poll_id})

    def top_voters(self, n=5):
        count = defaultdict(int)
        for vote in self.votes:
            count[vote.user_id] += 1
        return sorted(count.items(), key=lambda x: x[1], reverse=True)[:n]

    def top_poll_creators(self, n=5):
        return sorted(self.poll_creations.items(), key=lambda x: x[1], reverse=True)[:n]

    def get_stats_summary(self):
        return {
            'total_votes': len(self.votes),
            'total_polls': sum(self.poll_creations.values()),
            'top_voters': self.top_voters(),
            'top_poll_creators': self.top_poll_creators(),
        }
