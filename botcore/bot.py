import discord
from discord import app_commands
from handlers.poll_manager import PollManager
from handlers.reminder_scheduler import ReminderScheduler
from handlers.custom_command_manager import CustomCommandManager
from services.calendar_service import CalendarService
from services.rule_engine import RuleEngine
from services.ai_planner_agent import AIPlannerAgent
from db.user_manager import UserManager
from db.availability_tracker import AvailabilityTracker
from utils.permission_manager import PermissionManager
from utils.stats_module import StatsModule
import os
from datetime import datetime, timedelta
from handlers.bot_commands import register_all_commands

class BotCore(discord.Client):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tree = app_commands.CommandTree(self)
        # Instantiate all managers/services
        self.user_manager = UserManager()
        self.availability_tracker = AvailabilityTracker()
        self.permission_manager = PermissionManager()
        self.stats_module = StatsModule()
        self.custom_command_manager = CustomCommandManager()
        self.poll_manager = PollManager()
        self.reminder_scheduler = ReminderScheduler()
        self.calendar_service = CalendarService()
        self.rule_engine = RuleEngine()
        self.ai_planner_agent = AIPlannerAgent(openai_key=os.getenv('OPENAI_API_KEY', ''))
        self.owner_id = None

    async def setup_hook(self):
        await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")
        # Start the reminder scheduler after the event loop is running
        await self.reminder_scheduler.start()
        if self.guilds:
            self.owner_id = self.guilds[0].owner_id
            self.permission_manager.set_owner(self.owner_id)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = BotCore(intents=intents)

# Register all slash commands
register_all_commands(bot)

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        raise RuntimeError('DISCORD_BOT_TOKEN environment variable not set.')
    bot.run(token)
