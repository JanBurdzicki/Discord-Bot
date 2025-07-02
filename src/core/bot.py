"""
Main bot core with plugin system and dependency injection.
Combines feature-based architecture with OOP patterns.
"""

import discord
from discord import app_commands
from typing import Dict, Type, Any, List
import os
import asyncio
from datetime import datetime

from .service_container import ServiceContainer
from .base_feature import BaseFeature

class BotCore(discord.Client):
    """
    Enhanced bot core with:
    - Plugin system for features
    - Dependency injection container
    - Centralized service management
    - Auto-discovery of features
    """

    def __init__(self, **kwargs):
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        kwargs.setdefault('intents', intents)

        super().__init__(**kwargs)

        # Core systems
        self.tree = app_commands.CommandTree(self)
        self.services = ServiceContainer()
        self.features: Dict[str, BaseFeature] = {}

        # Bot configuration
        self.owner_id = None
        self.start_time = None

        # Initialize services
        self._setup_services()

    def _setup_services(self):
        """Initialize and register core services"""
        # Register database services
        from src.database.session import AsyncSessionLocal
        self.services.register_singleton(AsyncSessionLocal, AsyncSessionLocal)

        # Register managers from existing codebase
        from src.database.user_manager import UserManager
        from src.services.calendar_manager import CalendarManager
        from src.services.reminder_manager import ReminderManager
        from src.utils.permission_manager import PermissionManager
        from src.utils.stats_module import StatsModule

        # Create instances
        user_manager = UserManager()
        calendar_manager = CalendarManager()
        permission_manager = PermissionManager()
        stats_module = StatsModule()
        reminder_manager = ReminderManager(self, stats_module)

        # Register as singletons
        self.services.register_singleton(UserManager, user_manager)
        self.services.register_singleton(CalendarManager, calendar_manager)
        self.services.register_singleton(ReminderManager, reminder_manager)
        self.services.register_singleton(PermissionManager, permission_manager)
        self.services.register_singleton(StatsModule, stats_module)

        # Also register by string name for easier access
        # self.services.register_singleton('StatsModule', stats_module)

        # Legacy compatibility - add services as attributes
        self.user_manager = user_manager
        self.calendar_manager = calendar_manager
        self.reminder_manager = reminder_manager
        self.permission_manager = permission_manager
        self.stats_module = stats_module

    def register_feature(self, feature_class: Type[BaseFeature]) -> None:
        """Register a feature (plugin)"""
        try:
            feature = feature_class(self)
            feature.register_commands()
            feature.register_listeners()
            self.features[feature.name] = feature
            print(f"✅ Registered feature: {feature.name}")
        except Exception as e:
            print(f"❌ Failed to register feature {feature_class.__name__}: {str(e)}")

    async def unregister_feature(self, feature_name: str) -> bool:
        """Unregister a feature"""
        if feature_name not in self.features:
            return False

        feature = self.features[feature_name]
        await feature.on_feature_unload()
        del self.features[feature_name]
        print(f"🔄 Unregistered feature: {feature_name}")
        return True

    async def setup_hook(self):
        """Called when the bot is starting up"""
        print("🚀 Setting up bot...")
        self.start_time = datetime.utcnow()

        # Auto-discover and register features
        await self._register_all_features()

        # Sync command tree
        print("🔄 Syncing command tree with Discord...")
        try:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"❌ Failed to sync commands: {e}")

        # Initialize features
        for feature in self.features.values():
            await feature.on_feature_load()

        print("✅ Bot setup complete!")

    async def _register_all_features(self):
        """Auto-discover and register all features"""
        try:
            # Import all feature classes
            from src.features.calendar import CalendarFeature
            from src.features.polls import PollFeature
            from src.features.reminders import ReminderFeature
            from src.features.users import UserFeature
            from src.features.help import HelpFeature
            from src.features.stats import StatsFeature
            from src.features.roles import RoleFeature

            # Register features
            self.register_feature(CalendarFeature)
            self.register_feature(PollFeature)
            self.register_feature(ReminderFeature)
            self.register_feature(UserFeature)
            self.register_feature(HelpFeature)
            self.register_feature(StatsFeature)
            self.register_feature(RoleFeature)

        except ImportError as e:
            print(f"⚠️ Could not import all features: {e}")
            print("Some features may not be available yet.")

    async def on_ready(self):
        """Called when the bot is ready"""
        print(f"🤖 {self.user} is ready!")
        print(f"📊 Loaded {len(self.features)} features")
        print(f"🎯 Registered {len(self.tree.get_commands())} commands")

        # Set owner ID
        if not self.owner_id:
            app_info = await self.application_info()
            self.owner_id = app_info.owner.id
            print(f"👑 Bot owner: {app_info.owner}")

        # Start background tasks
        asyncio.create_task(self._background_tasks())

    async def _background_tasks(self):
        """Run background tasks"""
        try:
            # Start reminder manager scheduler
            if hasattr(self.reminder_manager, 'start_scheduler'):
                await self.reminder_manager.start_scheduler()

            # Check for expired polls
            asyncio.create_task(self._poll_expiry_checker())

        except Exception as e:
            print(f"⚠️ Error in background tasks: {e}")

    async def _poll_expiry_checker(self):
        """Background task to check and close expired polls"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                from datetime import datetime
                from sqlalchemy.future import select
                from src.database.session import AsyncSessionLocal
                from src.database.models import Poll

                async with AsyncSessionLocal() as session:
                    # Find active polls that have expired
                    now = datetime.utcnow()
                    result = await session.execute(
                        select(Poll).where(
                            Poll.is_active == True,
                            Poll.expires_at <= now
                        )
                    )
                    expired_polls = result.scalars().all()

                    # Close expired polls
                    for poll in expired_polls:
                        poll.is_active = False
                        await session.commit()

                        # Send expiry notification
                        channel = self.get_channel(poll.channel_id)
                        if channel:
                            await channel.send(f"📊 Poll '{poll.question}' has expired!")

            except Exception as e:
                print(f"⚠️ Error checking poll expiry: {e}")

    def get_feature(self, name: str) -> BaseFeature:
        """Get a feature by name"""
        return self.features.get(name)

    def get_service(self, service_type: Type):
        """Get a service by type"""
        return self.services.get(service_type)

    def get_bot_info(self) -> Dict[str, Any]:
        """Get information about the bot"""
        return {
            'name': self.user.name if self.user else None,
            'id': self.user.id if self.user else None,
            'owner_id': self.owner_id,
            'uptime': (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0,
            'features': len(self.features),
            'commands': len(self.tree.get_commands())
        }

    async def close(self):
        """Clean up before shutdown"""
        print("🔄 Shutting down bot...")

        # Unregister all features
        for feature_name in list(self.features.keys()):
            await self.unregister_feature(feature_name)

        # Close database connections
        if hasattr(self, 'db_pool'):
            await self.db_pool.close()

        await super().close()
        print("✅ Bot shutdown complete!")

def create_bot(**kwargs) -> BotCore:
    """Create a new bot instance"""
    return BotCore(**kwargs)

async def run_bot(token: str = None):
    """Run the bot"""
    # Create bot instance
    bot = create_bot()

    # Get token from environment if not provided
    if not token:
        token = os.getenv('DISCORD_BOT_TOKEN')
        if not token:
            raise ValueError("No Discord token provided")

    # Run the bot
    await bot.start(token)