import discord
from discord import app_commands
from handlers.reminder_scheduler import ReminderScheduler
from services.calendar_service import CalendarService
from services.calendar_manager import CalendarManager
from services.rule_engine import RuleEngine
from services.ai_planner_agent import AIPlannerAgent
from services.reminder_manager import ReminderManager
from db.user_manager import UserManager
from utils.permission_manager import PermissionManager
from utils.stats_module import StatsModule
import os
from handlers.bot_commands import register_all_commands

class BotCore(discord.Client):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tree = app_commands.CommandTree(self)
        # Instantiate all managers/services
        self.user_manager = UserManager()
        self.permission_manager = PermissionManager()
        self.stats_module = StatsModule()
        self.reminder_scheduler = ReminderScheduler()
        self.reminder_manager = ReminderManager(self, self.stats_module)
        # CalendarService is initialized per-user when needed (not globally)
        self.calendar_manager = CalendarManager()
        self.rule_engine = RuleEngine()
        self.ai_planner_agent = AIPlannerAgent(openai_key=os.getenv('OPENAI_API_KEY', ''))
        self.owner_id = None

    async def setup_hook(self):
        """Called when the bot is starting up"""
        print("Syncing command tree with Discord...")
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")

        # Set owner ID
        if self.guilds:
            self.owner_id = self.guilds[0].owner_id
            self.permission_manager.set_owner(self.owner_id)

        # Force sync commands again if needed (useful for development)
        if os.getenv('FORCE_COMMAND_SYNC', '').lower() == 'true':
            print("Force syncing commands...")
            try:
                synced = await self.tree.sync()
                print(f"Force synced {len(synced)} command(s)")
            except Exception as e:
                print(f"Failed to force sync commands: {e}")

        # Start the reminder scheduler after the event loop is running
        await self.reminder_scheduler.start()

        # Start the reminder manager
        await self.reminder_manager.start()

        # Start poll expiration checker
        self.loop.create_task(self.check_expired_polls())

    async def on_raw_reaction_add(self, payload):
        """Handle reaction-based voting for polls"""
        # Ignore bot reactions
        if payload.user_id == self.user.id:
            return

        # Get the message
        channel = self.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except:
            return

        # Check if this is a poll message (contains poll ID in embed)
        if not message.embeds:
            return

        embed = message.embeds[0]
        if embed.title != "📊 Poll":
            return

        # Extract poll ID from embed
        poll_id = None
        for field in embed.fields:
            if field.name == "Poll ID":
                poll_id = field.value
                break

        if not poll_id:
            return

        # Map emoji to option index
        emoji = str(payload.emoji)
        option_index = None

        # Handle regional indicator emojis (🇦 to 🇹)
        # These are single unicode characters
        if len(emoji) == 1:
            char_code = ord(emoji)
            if 0x1F1E6 <= char_code <= 0x1F1F9:  # 🇦 to 🇹 (20 emojis)
                option_index = char_code - 0x1F1E6
                print(f"Detected reaction: {emoji} -> option {option_index}")

        if option_index is not None:
            # Import here to avoid circular imports
            from handlers.poll_commands import sync_reaction_votes
            success = await sync_reaction_votes(poll_id, payload.user_id, message)

    async def on_raw_reaction_remove(self, payload):
        """Handle reaction removal for polls"""
        # Ignore bot reactions
        if payload.user_id == self.user.id:
            return

        # Get the message
        channel = self.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except:
            return

        # Check if this is a poll message (contains poll ID in embed)
        if not message.embeds:
            return

        embed = message.embeds[0]
        if embed.title != "📊 Poll":
            return

        # Extract poll ID from embed
        poll_id = None
        for field in embed.fields:
            if field.name == "Poll ID":
                poll_id = field.value
                break

        if not poll_id:
            return

        # Map emoji to option index
        emoji = str(payload.emoji)
        option_index = None

        # Handle regional indicator emojis (🇦 to 🇹)
        if len(emoji) == 1:
            char_code = ord(emoji)
            if 0x1F1E6 <= char_code <= 0x1F1F9:  # 🇦 to 🇹 (20 emojis)
                option_index = char_code - 0x1F1E6
                print(f"Removed reaction: {emoji} -> option {option_index}")

        if option_index is not None:
            # Import here to avoid circular imports
            from handlers.poll_commands import sync_reaction_votes
            success = await sync_reaction_votes(poll_id, payload.user_id, message)

    async def check_expired_polls(self):
        """Background task to check and close expired polls"""
        import asyncio
        from datetime import datetime
        from sqlalchemy.future import select
        from db.session import AsyncSessionLocal
        from db.models import Poll

        while True:
            try:
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

                    # Close expired polls and send notifications
                    for poll in expired_polls:
                        poll.is_active = False
                        print(f"Closed expired poll: {poll.poll_id} - {poll.question}")

                        # Send expiration notification to the channel where poll was created
                        if poll.channel_id:
                            try:
                                channel = self.get_channel(poll.channel_id)
                                if channel and channel.permissions_for(channel.guild.me).send_messages:
                                    embed = discord.Embed(
                                        title="📊 Poll Expired",
                                        description=f"**Poll:** {poll.question}\n**ID:** {poll.poll_id}",
                                        color=discord.Color.orange()
                                    )
                                    embed.add_field(name="Status", value="🔒 Closed", inline=True)
                                    embed.add_field(name="View Results", value=f"`/poll_results {poll.poll_id}`", inline=True)
                                    await channel.send(embed=embed)
                            except Exception as e:
                                print(f"Could not send expiration notification for poll {poll.poll_id}: {e}")

                    if expired_polls:
                        await session.commit()

            except Exception as e:
                print(f"Error checking expired polls: {e}")

            # Check every minute
            await asyncio.sleep(60)

    async def manual_sync_commands(self, guild_id=None):
        """Manually sync commands with Discord"""
        try:
            if guild_id:
                # Sync to specific guild (faster for testing)
                guild = discord.Object(id=guild_id)
                synced = await self.tree.sync(guild=guild)
                print(f"Synced {len(synced)} command(s) to guild {guild_id}")
            else:
                # Global sync
                synced = await self.tree.sync()
                print(f"Synced {len(synced)} command(s) globally")
            return len(synced)
        except Exception as e:
            print(f"Failed to sync commands: {e}")
            return 0

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
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
