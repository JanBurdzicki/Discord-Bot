import discord
from handlers.command_handler import CommandHandler
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
import asyncio
from dotenv import load_dotenv

load_dotenv()


class BotCore(discord.Client):
    def __init__(
        self,
        *,
        command_handler: CommandHandler,
        calendar_service: CalendarService,
        reminder_scheduler: ReminderScheduler,
        user_manager: UserManager,
        ai_planner_agent: AIPlannerAgent,
        poll_manager: PollManager,
        rule_engine: RuleEngine,
        permission_manager: PermissionManager,
        stats_module: StatsModule,
        custom_command_manager: CustomCommandManager,
        **options
    ):
        super().__init__(**options)
        self.command_handler = command_handler
        self.calendar_service = calendar_service
        self.reminder_scheduler = reminder_scheduler
        self.user_manager = user_manager
        self.ai_planner_agent = ai_planner_agent
        self.poll_manager = poll_manager
        self.rule_engine = rule_engine
        self.permission_manager = permission_manager
        self.stats_module = stats_module
        self.custom_command_manager = custom_command_manager

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")
        # Start the reminder scheduler after the event loop is running
        await self.reminder_scheduler.start()
        # Set the server owner as the PermissionManager owner_id
        if self.guilds:
            owner_id = self.guilds[0].owner_id
            self.permission_manager.set_owner(owner_id)

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        await self.command_handler.execute(message, bot_instance=self)

    def run_bot(self, token: str):
        self.run(token)


def main():
    # Instantiate all managers/services
    user_manager = UserManager()
    availability_tracker = AvailabilityTracker()
    permission_manager = PermissionManager()
    stats_module = StatsModule()
    custom_command_manager = CustomCommandManager()
    poll_manager = PollManager()
    reminder_scheduler = ReminderScheduler()
    calendar_service = CalendarService()
    rule_engine = RuleEngine()
    ai_planner_agent = AIPlannerAgent(openai_key=os.getenv('OPENAI_API_KEY', ''))

    # Command handler needs permission and custom command managers
    command_handler = CommandHandler(permission_manager, custom_command_manager, user_manager)

    intents = discord.Intents.default()
    intents.message_content = True

    # Instantiate the bot core
    bot = BotCore(
        intents=intents,
        command_handler=command_handler,
        calendar_service=calendar_service,
        reminder_scheduler=reminder_scheduler,
        user_manager=user_manager,
        ai_planner_agent=ai_planner_agent,
        poll_manager=poll_manager,
        rule_engine=rule_engine,
        permission_manager=permission_manager,
        stats_module=stats_module,
        custom_command_manager=custom_command_manager
    )

    # Run the bot
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        raise RuntimeError('DISCORD_BOT_TOKEN environment variable not set.')
    bot.run_bot(token)

if __name__ == "__main__":
    main()
