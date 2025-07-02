"""Reminder feature implementation."""
import discord
from discord import app_commands
from typing import Optional
from ...core.base_feature import BaseFeature
from .services.reminder_service import ReminderService, ReminderPriority, TriggerType

# Import all reminder command classes
from .commands.reminder_commands import (
    CreateTemplateCommand,
    ListTemplatesCommand,
    SetPollReminderCommand,
    SetCustomReminderCommand,
    QuickPollRemindersCommand,
    ListRemindersCommand,
    CancelReminderCommand,
    ReminderLogsCommand
)

class ReminderFeature(BaseFeature):
    """Feature for setting up and managing reminders."""

    name = "reminder"

    def __init__(self, bot):
        super().__init__(bot)
        self.reminder_service = ReminderService(bot)

        # Register reminder service in container
        bot.services.register_singleton("reminder_service", self.reminder_service)

    def register_commands(self):
        """Register all reminder commands."""

        # Create Reminder Template Command
        @self.bot.tree.command(name="create_reminder_template", description="Create a new reminder template")
        @app_commands.describe(
            name="Template name",
            message_template="Message template with {variables}",
            priority="Priority level",
            description="Template description",
            ping_roles="Role IDs to ping (comma-separated)",
            ping_users="User IDs to ping (comma-separated)"
        )
        @app_commands.choices(priority=[
            app_commands.Choice(name="Informational", value="informational"),
            app_commands.Choice(name="Urgent", value="urgent"),
            app_commands.Choice(name="Very Urgent", value="very_urgent"),
            app_commands.Choice(name="Critical", value="critical")
        ])
        async def create_reminder_template(
            interaction: discord.Interaction,
            name: str,
            message_template: str,
            priority: app_commands.Choice[str] = "informational",
            description: Optional[str] = None,
            ping_roles: Optional[str] = None,
            ping_users: Optional[str] = None
        ):
            command = CreateTemplateCommand(self.bot, self.bot.services)
            priority_value = priority.value if hasattr(priority, 'value') else priority
            await command.handle(interaction, name=name, message_template=message_template,
                               priority=priority_value, description=description,
                               ping_roles=ping_roles, ping_users=ping_users)

        # List Reminder Templates Command
        @self.bot.tree.command(name="list_reminder_templates", description="List all available reminder templates")
        @app_commands.describe(show_mine_only="Show only your templates")
        async def list_reminder_templates(interaction: discord.Interaction, show_mine_only: bool = False):
            command = ListTemplatesCommand(self.bot, self.bot.services)
            await command.handle(interaction, show_mine_only=show_mine_only)

        # Set Poll Reminder Command
        @self.bot.tree.command(name="set_poll_reminder", description="Set a reminder for a poll")
        @app_commands.describe(
            poll_id="Poll ID",
            template_name="Template name",
            reminder_type="Type of reminder",
            minutes_before="Minutes before expiry",
            interval_minutes="Minutes between reminders",
            max_occurrences="Max recurring reminders",
            specific_time="Specific time (YYYY-MM-DD HH:MM)"
        )
        @app_commands.choices(reminder_type=[
            app_commands.Choice(name="Time Before", value="time_before"),
            app_commands.Choice(name="Interval", value="interval"),
            app_commands.Choice(name="Specific Time", value="specific_time")
        ])
        async def set_poll_reminder(
            interaction: discord.Interaction,
            poll_id: str,
            template_name: str,
            reminder_type: app_commands.Choice[str] = "time_before",
            minutes_before: Optional[int] = None,
            interval_minutes: Optional[int] = None,
            max_occurrences: Optional[int] = None,
            specific_time: Optional[str] = None
        ):
            command = SetPollReminderCommand(self.bot, self.bot.services)
            reminder_type_value = reminder_type.value if hasattr(reminder_type, 'value') else reminder_type
            await command.handle(interaction, poll_id=poll_id, template_name=template_name,
                               reminder_type=reminder_type_value, minutes_before=minutes_before,
                               interval_minutes=interval_minutes, max_occurrences=max_occurrences,
                               specific_time=specific_time)

        # Set Custom Reminder Command
        @self.bot.tree.command(name="set_custom_reminder", description="Set a custom reminder")
        @app_commands.describe(
            template_name="Template name",
            reminder_type="Type of reminder",
            interval_minutes="Minutes between reminders",
            max_occurrences="Max recurring reminders",
            specific_time="Specific time (YYYY-MM-DD HH:MM)",
            custom_data="Custom data (key=value,key2=value2)"
        )
        @app_commands.choices(reminder_type=[
            app_commands.Choice(name="Interval", value="interval"),
            app_commands.Choice(name="Specific Time", value="specific_time")
        ])
        async def set_custom_reminder(
            interaction: discord.Interaction,
            template_name: str,
            reminder_type: app_commands.Choice[str] = "specific_time",
            interval_minutes: Optional[int] = None,
            max_occurrences: Optional[int] = None,
            specific_time: Optional[str] = None,
            custom_data: Optional[str] = None
        ):
            command = SetCustomReminderCommand(self.bot, self.bot.services)
            reminder_type_value = reminder_type.value if hasattr(reminder_type, 'value') else reminder_type
            await command.handle(interaction, template_name=template_name, reminder_type=reminder_type_value,
                               interval_minutes=interval_minutes, max_occurrences=max_occurrences,
                               specific_time=specific_time, custom_data=custom_data)

        # Quick Poll Reminders Command
        @self.bot.tree.command(name="quick_poll_reminders", description="Set up common poll reminders quickly")
        @app_commands.describe(
            poll_id="Poll ID",
            template_name="Template name",
            remind_times="Minutes before expiry (comma-separated)"
        )
        async def quick_poll_reminders(
            interaction: discord.Interaction,
            poll_id: str,
            template_name: str = "poll_reminder",
            remind_times: str = "60,30,10"
        ):
            command = QuickPollRemindersCommand(self.bot, self.bot.services)
            await command.handle(interaction, poll_id=poll_id, template_name=template_name,
                               remind_times=remind_times)

        # List Reminders Command
        @self.bot.tree.command(name="list_reminders", description="List your active reminders")
        @app_commands.describe(show_inactive="Include inactive reminders")
        async def list_reminders(interaction: discord.Interaction, show_inactive: bool = False):
            command = ListRemindersCommand(self.bot, self.bot.services)
            await command.handle(interaction, show_inactive=show_inactive)

        # Cancel Reminder Command
        @self.bot.tree.command(name="cancel_reminder", description="Cancel an active reminder")
        @app_commands.describe(reminder_id="ID of the reminder to cancel")
        async def cancel_reminder(interaction: discord.Interaction, reminder_id: str):
            command = CancelReminderCommand(self.bot, self.bot.services)
            await command.handle(interaction, reminder_id=reminder_id)

        # Reminder Logs Command
        @self.bot.tree.command(name="reminder_logs", description="View execution logs for a reminder")
        @app_commands.describe(reminder_id="ID of the reminder to view logs for")
        async def reminder_logs(interaction: discord.Interaction, reminder_id: str):
            command = ReminderLogsCommand(self.bot, self.bot.services)
            await command.handle(interaction, reminder_id=reminder_id)

    def register_listeners(self):
        """Register reminder-related event listeners."""

        @self.bot.event
        async def on_reminder_triggered(reminder):
            """Handle reminder notifications"""
            # Could implement reminder notification processing
            pass

        @self.bot.event
        async def on_reminder_created(reminder):
            """Handle reminder creation events"""
            # Could implement reminder creation notifications
            pass

    async def on_feature_load(self):
        """Called when the feature is loaded"""
        print(f"⏰ Reminder feature loaded with {len(self.bot.tree.get_commands())} commands")

    async def on_feature_unload(self):
        """Called when the feature is unloaded"""
        print("⏰ Reminder feature unloaded")