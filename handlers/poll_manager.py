from typing import Dict, List, Optional
from discord import Member

class Poll:
    def __init__(self, question: str, options: List[str], duration_seconds: int):
        self.question = question
        self.options = options
        self.votes: Dict[int, int] = {}  # user_id -> option index
        self.active = True
        # duration, start time, etc. can be added here

    def vote(self, user_id: int, option_index: int):
        if not self.active:
            raise Exception("Poll is closed.")
        if option_index < 0 or option_index >= len(self.options):
            raise Exception("Invalid option.")
        self.votes[user_id] = option_index

    def get_results(self) -> Dict[str, int]:
        results = {opt: 0 for opt in self.options}
        for vote in self.votes.values():
            results[self.options[vote]] += 1
        return results

class PollManager:
    def __init__(self):
        self.polls: Dict[str, Poll] = {}

    def create_poll(self, question: str, options: List[str], duration: int) -> str:
        poll_id = f"poll_{len(self.polls)+1}"
        self.polls[poll_id] = Poll(question, options, duration)
        return poll_id

    def vote(self, poll_id: str, user_id: int, choice: int):
        poll = self.polls.get(poll_id)
        if not poll:
            raise Exception("Poll not found.")
        poll.vote(user_id, choice)

    def get_results(self, poll_id: str) -> Optional[Dict[str, int]]:
        poll = self.polls.get(poll_id)
        if poll:
            return poll.get_results()
        return None

