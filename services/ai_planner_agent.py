from typing import List
from db.models import UserProfile

class AIPlannerAgent:
    def __init__(self, openai_key: str):
        self.openai_key = openai_key
        self.prompt_templates = {}

    def suggest_times(self, users: List[UserProfile]) -> List[str]:
        # Call OpenAI API to get suggested times
        return []

