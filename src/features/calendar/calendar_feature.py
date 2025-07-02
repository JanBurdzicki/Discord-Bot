"""Calendar feature implementation."""
import discord
from discord import app_commands
from ...core.base_feature import BaseFeature
from .services.calendar_service import CalendarService

# Import all calendar command classes
from .commands.calendar_commands import (
    CalendarHelpCommand,
    LinkUserCalendarCommand,
    CreateSharedCalendarCommand,
    AddCalendarUsersCommand,
    ListCalendarUsersCommand,
    RemoveCalendarUsersCommand,
    AddEventCommand,
    ListEventsCommand,
    UpdateEventCommand,
    DeleteEventCommand,
    VisualizeDayCommand,
    FindFreeSlotsCommand,
    VisualizePeriodCommand
)

class CalendarFeature(BaseFeature):
    """Feature for managing shared calendars and events."""

    name = "calendar"

    def __init__(self, bot):
        super().__init__(bot)
        self.calendar_service = CalendarService(bot)

        # Register calendar service in container
        bot.services.register_singleton("calendar_service", self.calendar_service)

    def register_commands(self):
        """Register all calendar commands."""

        # Calendar Help Command
        @self.bot.tree.command(name="calendar_help", description="Show calendar system help and instructions")
        async def calendar_help(interaction: discord.Interaction):
            command = CalendarHelpCommand(self.bot, self.bot.services)
            await command.handle(interaction)

        # Link User Calendar Command
        @self.bot.tree.command(name="link_user_calendar", description="Link your personal Google Calendar")
        @app_commands.describe(
            calendar_id="Your Google Calendar ID (looks like email@gmail.com)"
        )
        async def link_user_calendar(interaction: discord.Interaction, calendar_id: str = ""):
            command = LinkUserCalendarCommand(self.bot, self.bot.services)
            await command.handle(interaction, calendar_id=calendar_id)

        # Create Shared Calendar Command
        @self.bot.tree.command(name="create_shared_calendar", description="Create a new shared calendar (Owner only)")
        @app_commands.describe(
            calendar_name="Name for the shared calendar",
            description="Optional description for the calendar"
        )
        async def create_shared_calendar(interaction: discord.Interaction, calendar_name: str, description: str = ""):
            command = CreateSharedCalendarCommand(self.bot, self.bot.services)
            await command.handle(interaction, calendar_name=calendar_name, description=description)

        # Add Calendar Users Command
        @self.bot.tree.command(name="add_calendar_users", description="Add users to shared calendar (Owner only)")
        @app_commands.describe(
            calendar_name="Name of the calendar",
            permission="Permission level (reader/writer/owner)",
            roles="Comma-separated role names (optional)",
            users="Comma-separated user mentions or names (optional)"
        )
        async def add_calendar_users(interaction: discord.Interaction, calendar_name: str, permission: str, roles: str = "", users: str = ""):
            command = AddCalendarUsersCommand(self.bot, self.bot.services)
            await command.handle(interaction, calendar_name=calendar_name, permission=permission, roles=roles, users=users)

        # List Calendar Users Command
        @self.bot.tree.command(name="list_calendar_users", description="List users with access to a calendar")
        @app_commands.describe(
            calendar_name="Name of the calendar"
        )
        async def list_calendar_users(interaction: discord.Interaction, calendar_name: str):
            command = ListCalendarUsersCommand(self.bot, self.bot.services)
            await command.handle(interaction, calendar_name=calendar_name)

        # Remove Calendar Users Command
        @self.bot.tree.command(name="remove_calendar_users", description="Remove users from shared calendar (Owner only)")
        @app_commands.describe(
            calendar_name="Name of the calendar",
            roles="Comma-separated role names (optional)",
            users="Comma-separated user mentions or names (optional)"
        )
        async def remove_calendar_users(interaction: discord.Interaction, calendar_name: str, roles: str = "", users: str = ""):
            command = RemoveCalendarUsersCommand(self.bot, self.bot.services)
            await command.handle(interaction, calendar_name=calendar_name, roles=roles, users=users)

        # Add Event Command
        @self.bot.tree.command(name="add_event", description="Add event to shared calendar")
        @app_commands.describe(
            calendar_name="Name of the calendar",
            event_name="Name of the event",
            start_time="Start time (YYYY-MM-DD HH:MM)",
            end_time="End time (YYYY-MM-DD HH:MM)",
            location="Event location (optional)",
            description="Event description (optional)",
            roles="Roles to assign to event (optional)"
        )
        async def add_event(interaction: discord.Interaction, calendar_name: str, event_name: str, start_time: str, end_time: str, location: str = "", description: str = "", roles: str = ""):
            command = AddEventCommand(self.bot, self.bot.services)
            await command.handle(interaction, calendar_name=calendar_name, event_name=event_name, start_time=start_time, end_time=end_time, location=location, description=description, roles=roles)

        # List Events Command
        @self.bot.tree.command(name="list_events", description="List upcoming events in calendar")
        @app_commands.describe(
            calendar_name="Name of the calendar",
            days_ahead="Number of days to look ahead (default: 7)"
        )
        async def list_events(interaction: discord.Interaction, calendar_name: str, days_ahead: int = 7):
            command = ListEventsCommand(self.bot, self.bot.services)
            await command.handle(interaction, calendar_name=calendar_name, days_ahead=days_ahead)

        # Update Event Command
        @self.bot.tree.command(name="update_event", description="Update an existing event")
        @app_commands.describe(
            calendar_name="Name of the calendar",
            event_id="ID of the event to update",
            event_name="New event name (optional)",
            start_time="New start time (YYYY-MM-DD HH:MM) (optional)",
            end_time="New end time (YYYY-MM-DD HH:MM) (optional)",
            location="New location (optional)",
            description="New description (optional)"
        )
        async def update_event(interaction: discord.Interaction, calendar_name: str, event_id: str, event_name: str = "", start_time: str = "", end_time: str = "", location: str = "", description: str = ""):
            command = UpdateEventCommand(self.bot, self.bot.services)
            await command.handle(interaction, calendar_name=calendar_name, event_id=event_id, event_name=event_name, start_time=start_time, end_time=end_time, location=location, description=description)

        # Delete Event Command
        @self.bot.tree.command(name="delete_event", description="Delete an event from calendar")
        @app_commands.describe(
            calendar_name="Name of the calendar",
            event_id="ID of the event to delete"
        )
        async def delete_event(interaction: discord.Interaction, calendar_name: str, event_id: str):
            command = DeleteEventCommand(self.bot, self.bot.services)
            await command.handle(interaction, calendar_name=calendar_name, event_id=event_id)

        # Visualize Day Command
        @self.bot.tree.command(name="visualize_day", description="Show daily schedule visualization")
        @app_commands.describe(
            calendar_name="Name of the calendar",
            date="Date to visualize (YYYY-MM-DD)",
            start_hour="Start hour for visualization (default: 8)",
            end_hour="End hour for visualization (default: 18)"
        )
        async def visualize_day(interaction: discord.Interaction, calendar_name: str, date: str, start_hour: int = 8, end_hour: int = 18):
            command = VisualizeDayCommand(self.bot, self.bot.services)
            await command.handle(interaction, calendar_name=calendar_name, date=date, start_hour=start_hour, end_hour=end_hour)

        # Find Free Slots Command
        @self.bot.tree.command(name="find_free_slots", description="Find free time slots in your personal calendar")
        @app_commands.describe(
            start="Start time (YYYY-MM-DD HH:MM)",
            end="End time (YYYY-MM-DD HH:MM)",
            duration="Duration in minutes (default: 30)"
        )
        async def find_free_slots(interaction: discord.Interaction, start: str, end: str, duration: int = 30):
            command = FindFreeSlotsCommand(self.bot, self.bot.services)
            await command.handle(interaction, start=start, end=end, duration=duration)

        # Visualize Period Command
        @self.bot.tree.command(name="visualize_period", description="Show calendar schedule over a period of time")
        @app_commands.describe(
            calendar_name="Name of the calendar",
            start_date="Start date (YYYY-MM-DD)",
            end_date="End date (YYYY-MM-DD)"
        )
        async def visualize_period(interaction: discord.Interaction, calendar_name: str, start_date: str, end_date: str):
            command = VisualizePeriodCommand(self.bot, self.bot.services)
            await command.handle(interaction, calendar_name=calendar_name, start_date=start_date, end_date=end_date)

    def register_listeners(self):
        """Register calendar-related event listeners."""

        @self.bot.event
        async def on_calendar_event_created(event):
            """Handle calendar event creation notifications"""
            # Could implement notifications for calendar events
            pass

        @self.bot.event
        async def on_calendar_permission_changed(calendar_id, user_id, permission):
            """Handle calendar permission changes"""
            # Could implement permission change notifications
            pass

    async def on_feature_load(self):
        """Called when the feature is loaded"""
        print(f"📅 Calendar feature loaded with {len(self.bot.tree.get_commands())} commands")

    async def on_feature_unload(self):
        """Called when the feature is unloaded"""
        print("📅 Calendar feature unloaded")