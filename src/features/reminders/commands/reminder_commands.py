"""
Discord commands for the reminder system.
Provides commands for managing templates and reminders.
"""

from typing import Optional, List
import discord
from discord import app_commands

from ..services.reminder_service import ReminderService, ReminderPriority, TriggerType
from src.core.base_command import BaseCommand
from src.core.builders import EmbedBuilder
from datetime import datetime

class ReminderCommands:
    """
    Commands for managing reminders and templates.
    Provides user-facing commands for all reminder functionality.
    """

    def __init__(self, reminder_service: ReminderService):
        self.service = reminder_service
        self._setup_commands()

    def _setup_commands(self):
        """Set up all reminder commands"""
        self.commands = [
            self.create_template_command(),
            self.list_templates_command(),
            self.set_poll_reminder_command(),
            self.set_custom_reminder_command(),
            self.quick_poll_reminders_command(),
            self.list_reminders_command(),
            self.cancel_reminder_command()
        ]

    def get_all_commands(self) -> List[app_commands.Command]:
        """Get all reminder commands"""
        return self.commands

    # ========== Template Commands ==========

    def create_template_command(self) -> app_commands.Command:
        """Command to create a new reminder template"""
        @app_commands.command(name="create_reminder_template", description="Create a new reminder template")
        @app_commands.describe(
            name="Template name",
            message_template="Message template with {variables}",
            priority="Priority level",
            description="Template description",
            ping_roles="Role IDs to ping (comma-separated)",
            ping_users="User IDs to ping (comma-separated)"
        )
        @app_commands.choices(priority=[
            app_commands.Choice(name=p.value.title(), value=p.value)
            for p in ReminderPriority
        ])
        async def command(
            interaction: discord.Interaction,
            name: str,
            message_template: str,
            priority: app_commands.Choice[str] = "informational",
            description: Optional[str] = None,
            ping_roles: Optional[str] = None,
            ping_users: Optional[str] = None
        ):
            try:
                # Parse priority
                priority_enum = ReminderPriority(priority.value if hasattr(priority, 'value') else priority)

                # Parse ping lists
                ping_role_ids = []
                ping_user_ids = []

                if ping_roles:
                    try:
                        ping_role_ids = [int(x.strip()) for x in ping_roles.split(',')]
                    except ValueError:
                        await interaction.response.send_message("❌ Invalid role IDs format. Use comma-separated numbers.", ephemeral=True)
                        return

                if ping_users:
                    try:
                        ping_user_ids = [int(x.strip()) for x in ping_users.split(',')]
                    except ValueError:
                        await interaction.response.send_message("❌ Invalid user IDs format. Use comma-separated numbers.", ephemeral=True)
                        return

                # Create template
                template = await self.service.create_template(
                    name=name,
                    description=description or f"Template created by {interaction.user.display_name}",
                    message_template=message_template,
                    priority=priority_enum,
                    creator_id=interaction.user.id,
                    ping_roles=ping_role_ids,
                    ping_users=ping_user_ids
                )

                embed = EmbedBuilder()\
                    .set_title("✅ Reminder Template Created")\
                    .set_description(f"Template **{name}** has been created successfully!")\
                    .set_color(0x00ff00)\
                    .add_field("Message Template", message_template, inline=False)\
                    .add_field("Priority", priority_enum.value.title(), inline=True)\
                    .add_field("Created By", interaction.user.display_name, inline=True)\
                    .build()

                await interaction.response.send_message(embed=embed)

            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

        return command

    def list_templates_command(self) -> app_commands.Command:
        """Command to list available reminder templates"""
        @app_commands.command(name="list_reminder_templates", description="List all available reminder templates")
        @app_commands.describe(show_mine_only="Show only your templates")
        async def command(interaction: discord.Interaction, show_mine_only: bool = False):
            try:
                templates = await self.service.list_templates(
                    creator_id=interaction.user.id if show_mine_only else None
                )

                if not templates:
                    await interaction.response.send_message("📝 No templates found.", ephemeral=True)
                    return

                embed = EmbedBuilder()\
                    .set_title(f"📋 Reminder Templates {'(Your Templates)' if show_mine_only else ''}")\
                    .set_color(0x3498db)

                for template in templates:
                    embed.add_field(
                        f"📝 {template.name}",
                        f"**Priority:** {template.priority.title()}\n"
                        f"**Description:** {template.description}\n"
                        f"**Created By:** <@{template.created_by}>",
                        inline=True
                    )

                await interaction.response.send_message(embed=embed.build())

            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

        return command

    # ========== Reminder Commands ==========

    def set_poll_reminder_command(self) -> app_commands.Command:
        """Command to set a reminder for a poll"""
        @app_commands.command(name="set_poll_reminder", description="Set a reminder for a poll")
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
            app_commands.Choice(name=t.value.replace('_', ' ').title(), value=t.value)
            for t in TriggerType
        ])
        async def command(
            interaction: discord.Interaction,
            poll_id: str,
            template_name: str,
            reminder_type: app_commands.Choice[str] = "time_before",
            minutes_before: Optional[int] = None,
            interval_minutes: Optional[int] = None,
            max_occurrences: Optional[int] = None,
            specific_time: Optional[str] = None
        ):
            try:
                trigger_type = TriggerType(reminder_type.value if hasattr(reminder_type, 'value') else reminder_type)

                # Validate parameters based on reminder type
                if trigger_type == TriggerType.TIME_BEFORE and not minutes_before:
                    await interaction.response.send_message("❌ `minutes_before` is required for time_before reminders.", ephemeral=True)
                    return
                elif trigger_type == TriggerType.INTERVAL and not interval_minutes:
                    await interaction.response.send_message("❌ `interval_minutes` is required for interval reminders.", ephemeral=True)
                    return
                elif trigger_type == TriggerType.SPECIFIC_TIME and not specific_time:
                    await interaction.response.send_message("❌ `specific_time` is required for specific_time reminders. Format: YYYY-MM-DD HH:MM", ephemeral=True)
                    return

                kwargs = {}
                if minutes_before:
                    kwargs['minutes_before'] = minutes_before
                if interval_minutes:
                    kwargs['interval_minutes'] = interval_minutes
                if max_occurrences:
                    kwargs['max_occurrences'] = max_occurrences
                if specific_time:
                    try:
                        kwargs['trigger_time'] = datetime.strptime(specific_time, "%Y-%m-%d %H:%M")
                    except ValueError:
                        await interaction.response.send_message("❌ Invalid time format. Use: YYYY-MM-DD HH:MM", ephemeral=True)
                        return

                reminder = await self.service.create_reminder(
                    template_name=template_name,
                    channel_id=interaction.channel.id,
                    creator_id=interaction.user.id,
                    trigger_type=trigger_type,
                    target_type="poll",
                    target_id=poll_id,
                    **kwargs
                )

                embed = EmbedBuilder()\
                    .set_title("⏰ Poll Reminder Set")\
                    .set_description(f"Reminder created for poll `{poll_id}`")\
                    .set_color(0x00ff00)\
                    .add_field("Template", template_name, inline=True)\
                    .add_field("Type", trigger_type.value.replace('_', ' ').title(), inline=True)\
                    .add_field("Next Trigger", reminder.next_trigger.strftime("%Y-%m-%d %H:%M UTC") if reminder.next_trigger else "Not scheduled", inline=False)\
                    .build()

                await interaction.response.send_message(embed=embed)

            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

        return command

    def set_custom_reminder_command(self) -> app_commands.Command:
        """Command to set a custom reminder"""
        @app_commands.command(name="set_custom_reminder", description="Set a custom reminder")
        @app_commands.describe(
            template_name="Template name",
            reminder_type="Type of reminder",
            interval_minutes="Minutes between reminders",
            max_occurrences="Max recurring reminders",
            specific_time="Specific time (YYYY-MM-DD HH:MM)",
            custom_data="Custom data (key=value,key2=value2)"
        )
        @app_commands.choices(reminder_type=[
            app_commands.Choice(name=t.value.replace('_', ' ').title(), value=t.value)
            for t in [TriggerType.INTERVAL, TriggerType.SPECIFIC_TIME]
        ])
        async def command(
            interaction: discord.Interaction,
            template_name: str,
            reminder_type: app_commands.Choice[str] = "specific_time",
            interval_minutes: Optional[int] = None,
            max_occurrences: Optional[int] = None,
            specific_time: Optional[str] = None,
            custom_data: Optional[str] = None
        ):
            try:
                trigger_type = TriggerType(reminder_type.value if hasattr(reminder_type, 'value') else reminder_type)

                # Validate parameters
                if trigger_type == TriggerType.INTERVAL and not interval_minutes:
                    await interaction.response.send_message("❌ `interval_minutes` is required for interval reminders.", ephemeral=True)
                    return
                elif trigger_type == TriggerType.SPECIFIC_TIME and not specific_time:
                    await interaction.response.send_message("❌ `specific_time` is required for specific_time reminders. Format: YYYY-MM-DD HH:MM", ephemeral=True)
                    return

                # Parse custom data
                custom_data_dict = {}
                if custom_data:
                    try:
                        pairs = [pair.strip().split('=') for pair in custom_data.split(',')]
                        custom_data_dict = {k.strip(): v.strip() for k, v in pairs}
                    except ValueError:
                        await interaction.response.send_message("❌ Invalid custom data format. Use: key=value,key2=value2", ephemeral=True)
                        return

                kwargs = {}
                if interval_minutes:
                    kwargs['interval_minutes'] = interval_minutes
                if max_occurrences:
                    kwargs['max_occurrences'] = max_occurrences
                if specific_time:
                    try:
                        kwargs['trigger_time'] = datetime.strptime(specific_time, "%Y-%m-%d %H:%M")
                    except ValueError:
                        await interaction.response.send_message("❌ Invalid time format. Use: YYYY-MM-DD HH:MM", ephemeral=True)
                        return

                reminder = await self.service.create_reminder(
                    template_name=template_name,
                    channel_id=interaction.channel.id,
                    creator_id=interaction.user.id,
                    trigger_type=trigger_type,
                    custom_data=custom_data_dict,
                    **kwargs
                )

                embed = EmbedBuilder()\
                    .set_title("⏰ Custom Reminder Set")\
                    .set_description("Custom reminder created successfully!")\
                    .set_color(0x00ff00)\
                    .add_field("Template", template_name, inline=True)\
                    .add_field("Type", trigger_type.value.replace('_', ' ').title(), inline=True)\
                    .add_field("Next Trigger", reminder.next_trigger.strftime("%Y-%m-%d %H:%M UTC") if reminder.next_trigger else "Not scheduled", inline=False)\
                    .build()

                await interaction.response.send_message(embed=embed)

            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

        return command

    def quick_poll_reminders_command(self) -> app_commands.Command:
        """Command to quickly set up multiple poll reminders"""
        @app_commands.command(name="quick_poll_reminders", description="Set up common poll reminders quickly")
        @app_commands.describe(
            poll_id="Poll ID",
            template_name="Template name",
            remind_times="Minutes before expiry (comma-separated)"
        )
        async def command(
            interaction: discord.Interaction,
            poll_id: str,
            template_name: str = "poll_reminder",
            remind_times: str = "60,30,10"
        ):
            try:
                # Parse remind times
                try:
                    minutes_list = [int(x.strip()) for x in remind_times.split(',')]
                except ValueError:
                    await interaction.response.send_message("❌ Invalid remind_times format. Use comma-separated minutes like: 60,30,10", ephemeral=True)
                    return

                # Create reminder configs
                configs = []
                for minutes in minutes_list:
                    configs.append({
                        'type': TriggerType.TIME_BEFORE,
                        'minutes_before': minutes
                    })

                # Set up reminders
                created_reminders = []
                for config in configs:
                    reminder = await self.service.create_reminder(
                        template_name=template_name,
                        channel_id=interaction.channel.id,
                        creator_id=interaction.user.id,
                        trigger_type=config['type'],
                        target_type="poll",
                        target_id=poll_id,
                        minutes_before=config['minutes_before']
                    )
                    created_reminders.append(reminder)

                embed = EmbedBuilder()\
                    .set_title("⚡ Quick Poll Reminders Set")\
                    .set_description(f"Created {len(created_reminders)} reminders for poll `{poll_id}`")\
                    .set_color(0x00ff00)

                reminder_list = []
                for i, reminder in enumerate(created_reminders):
                    minutes = minutes_list[i]
                    reminder_list.append(f"• {minutes} minutes before expiry")

                embed.add_field("Reminders Created", "\n".join(reminder_list), inline=False)
                embed.add_field("Template Used", template_name, inline=True)

                await interaction.response.send_message(embed=embed.build())

            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

        return command

    def list_reminders_command(self) -> app_commands.Command:
        """Command to list user's reminders"""
        @app_commands.command(name="list_reminders", description="List your active reminders")
        @app_commands.describe(show_inactive="Include inactive reminders")
        async def command(interaction: discord.Interaction, show_inactive: bool = False):
            try:
                reminders = await self.service.list_reminders(
                    creator_id=interaction.user.id,
                    is_active=None if show_inactive else True
                )

                if not reminders:
                    await interaction.response.send_message("📝 No reminders found.", ephemeral=True)
                    return

                embed = EmbedBuilder()\
                    .set_title(f"⏰ Your Reminders {'(Including Inactive)' if show_inactive else '(Active Only)'}")\
                    .set_color(0x3498db)

                for reminder in reminders[:10]:  # Limit to 10 reminders
                    status = "🟢 Active" if reminder.is_active else "🔴 Inactive"
                    next_trigger = reminder.next_trigger.strftime("%Y-%m-%d %H:%M UTC") if reminder.next_trigger else "N/A"

                    embed.add_field(
                        f"🔖 {reminder.reminder_id[:8]}",
                        f"**Status:** {status}\n"
                        f"**Type:** {reminder.target_type.title() if reminder.target_type else 'Custom'}\n"
                        f"**Target:** {reminder.target_id or 'N/A'}\n"
                        f"**Next:** {next_trigger}\n"
                        f"**Count:** {reminder.occurrence_count}",
                        inline=True
                    )

                if len(reminders) > 10:
                    embed.set_footer(f"Showing 10 of {len(reminders)} reminders")

                await interaction.response.send_message(embed=embed.build())

            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

        return command

    def cancel_reminder_command(self) -> app_commands.Command:
        """Command to cancel an active reminder"""
        @app_commands.command(name="cancel_reminder", description="Cancel an active reminder")
        @app_commands.describe(reminder_id="ID of the reminder to cancel")
        async def command(interaction: discord.Interaction, reminder_id: str):
            try:
                success = await self.service.cancel_reminder(reminder_id)

                if success:
                    embed = EmbedBuilder()\
                        .set_title("✅ Reminder Cancelled")\
                        .set_description(f"Reminder `{reminder_id}` has been cancelled.")\
                        .set_color(0x00ff00)\
                        .build()

                    await interaction.response.send_message(embed=embed)
                else:
                    await interaction.response.send_message("❌ Reminder not found or already inactive.", ephemeral=True)

            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

        return command

# ========== Individual Command Classes ==========

class CreateTemplateCommand(BaseCommand):
    """Command to create a new reminder template"""

    def __init__(self, bot, services):
        super().__init__(bot, services)
        self.service = services.get("reminder_service")

    async def handle(self, interaction: discord.Interaction, name: str, message_template: str,
                    priority: str = "informational", description: Optional[str] = None,
                    ping_roles: Optional[str] = None, ping_users: Optional[str] = None):
        try:
            # Parse priority
            priority_enum = ReminderPriority(priority)

            # Parse ping lists
            ping_role_ids = []
            ping_user_ids = []

            if ping_roles:
                try:
                    ping_role_ids = [int(x.strip()) for x in ping_roles.split(',')]
                except ValueError:
                    await interaction.response.send_message("❌ Invalid role IDs format. Use comma-separated numbers.", ephemeral=True)
                    return

            if ping_users:
                try:
                    ping_user_ids = [int(x.strip()) for x in ping_users.split(',')]
                except ValueError:
                    await interaction.response.send_message("❌ Invalid user IDs format. Use comma-separated numbers.", ephemeral=True)
                    return

            # Create template
            template = await self.service.create_template(
                name=name,
                description=description or f"Template created by {interaction.user.display_name}",
                message_template=message_template,
                priority=priority_enum,
                creator_id=interaction.user.id,
                ping_roles=ping_role_ids,
                ping_users=ping_user_ids
            )

            embed = EmbedBuilder()\
                .set_title("✅ Reminder Template Created")\
                .set_description(f"Template **{name}** has been created successfully!")\
                .set_color(0x00ff00)\
                .add_field("Message Template", message_template, inline=False)\
                .add_field("Priority", priority_enum.value.title(), inline=True)\
                .add_field("Created By", interaction.user.display_name, inline=True)\
                .build()

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class ListTemplatesCommand(BaseCommand):
    """Command to list available reminder templates"""

    def __init__(self, bot, services):
        super().__init__(bot, services)
        self.service = services.get("reminder_service")

    async def handle(self, interaction: discord.Interaction, show_mine_only: bool = False):
        try:
            templates = await self.service.list_templates(
                creator_id=interaction.user.id if show_mine_only else None
            )

            if not templates:
                await interaction.response.send_message("📝 No templates found.", ephemeral=True)
                return

            embed = EmbedBuilder()\
                .set_title(f"📋 Reminder Templates {'(Your Templates)' if show_mine_only else ''}")\
                .set_color(0x3498db)

            for template in templates:
                embed.add_field(
                    f"📝 {template.name}",
                    f"**Priority:** {template.priority.title()}\n"
                    f"**Description:** {template.description}\n"
                    f"**Created By:** <@{template.created_by}>",
                    inline=True
                )

            await interaction.response.send_message(embed=embed.build())

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class SetPollReminderCommand(BaseCommand):
    """Command to set a reminder for a poll"""

    def __init__(self, bot, services):
        super().__init__(bot, services)
        self.service = services.get("reminder_service")

    async def handle(self, interaction: discord.Interaction, poll_id: str, template_name: str,
                    reminder_type: str = "time_before", minutes_before: Optional[int] = None,
                    interval_minutes: Optional[int] = None, max_occurrences: Optional[int] = None,
                    specific_time: Optional[str] = None):
        try:
            trigger_type = TriggerType(reminder_type)

            # Validate parameters based on reminder type
            if trigger_type == TriggerType.TIME_BEFORE and not minutes_before:
                await interaction.response.send_message("❌ `minutes_before` is required for time_before reminders.", ephemeral=True)
                return
            elif trigger_type == TriggerType.INTERVAL and not interval_minutes:
                await interaction.response.send_message("❌ `interval_minutes` is required for interval reminders.", ephemeral=True)
                return
            elif trigger_type == TriggerType.SPECIFIC_TIME and not specific_time:
                await interaction.response.send_message("❌ `specific_time` is required for specific_time reminders. Format: YYYY-MM-DD HH:MM", ephemeral=True)
                return

            kwargs = {}
            if minutes_before:
                kwargs['minutes_before'] = minutes_before
            if interval_minutes:
                kwargs['interval_minutes'] = interval_minutes
            if max_occurrences:
                kwargs['max_occurrences'] = max_occurrences
            if specific_time:
                try:
                    kwargs['trigger_time'] = datetime.strptime(specific_time, "%Y-%m-%d %H:%M")
                except ValueError:
                    await interaction.response.send_message("❌ Invalid time format. Use: YYYY-MM-DD HH:MM", ephemeral=True)
                    return

            reminder = await self.service.create_reminder(
                template_name=template_name,
                channel_id=interaction.channel.id,
                creator_id=interaction.user.id,
                trigger_type=trigger_type,
                target_type="poll",
                target_id=poll_id,
                **kwargs
            )

            embed = EmbedBuilder()\
                .set_title("⏰ Poll Reminder Set")\
                .set_description(f"Reminder created for poll `{poll_id}`")\
                .set_color(0x00ff00)\
                .add_field("Template", template_name, inline=True)\
                .add_field("Type", trigger_type.value.replace('_', ' ').title(), inline=True)\
                .add_field("Next Trigger", reminder.next_trigger.strftime("%Y-%m-%d %H:%M UTC") if reminder.next_trigger else "Not scheduled", inline=False)\
                .build()

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class SetCustomReminderCommand(BaseCommand):
    """Command to set a custom reminder"""

    def __init__(self, bot, services):
        super().__init__(bot, services)
        self.service = services.get("reminder_service")

    async def handle(self, interaction: discord.Interaction, template_name: str,
                    reminder_type: str = "specific_time", interval_minutes: Optional[int] = None,
                    max_occurrences: Optional[int] = None, specific_time: Optional[str] = None,
                    custom_data: Optional[str] = None):
        try:
            trigger_type = TriggerType(reminder_type)

            # Validate parameters
            if trigger_type == TriggerType.INTERVAL and not interval_minutes:
                await interaction.response.send_message("❌ `interval_minutes` is required for interval reminders.", ephemeral=True)
                return
            elif trigger_type == TriggerType.SPECIFIC_TIME and not specific_time:
                await interaction.response.send_message("❌ `specific_time` is required for specific_time reminders. Format: YYYY-MM-DD HH:MM", ephemeral=True)
                return

            # Parse custom data
            custom_data_dict = {}
            if custom_data:
                try:
                    pairs = [pair.strip().split('=') for pair in custom_data.split(',')]
                    custom_data_dict = {k.strip(): v.strip() for k, v in pairs}
                except ValueError:
                    await interaction.response.send_message("❌ Invalid custom data format. Use: key=value,key2=value2", ephemeral=True)
                    return

            kwargs = {}
            if interval_minutes:
                kwargs['interval_minutes'] = interval_minutes
            if max_occurrences:
                kwargs['max_occurrences'] = max_occurrences
            if specific_time:
                try:
                    kwargs['trigger_time'] = datetime.strptime(specific_time, "%Y-%m-%d %H:%M")
                except ValueError:
                    await interaction.response.send_message("❌ Invalid time format. Use: YYYY-MM-DD HH:MM", ephemeral=True)
                    return

            reminder = await self.service.create_reminder(
                template_name=template_name,
                channel_id=interaction.channel.id,
                creator_id=interaction.user.id,
                trigger_type=trigger_type,
                custom_data=custom_data_dict,
                **kwargs
            )

            embed = EmbedBuilder()\
                .set_title("⏰ Custom Reminder Set")\
                .set_description("Custom reminder created successfully!")\
                .set_color(0x00ff00)\
                .add_field("Template", template_name, inline=True)\
                .add_field("Type", trigger_type.value.replace('_', ' ').title(), inline=True)\
                .add_field("Next Trigger", reminder.next_trigger.strftime("%Y-%m-%d %H:%M UTC") if reminder.next_trigger else "Not scheduled", inline=False)\
                .build()

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class QuickPollRemindersCommand(BaseCommand):
    """Command to quickly set up multiple poll reminders"""

    def __init__(self, bot, services):
        super().__init__(bot, services)
        self.service = services.get("reminder_service")

    async def handle(self, interaction: discord.Interaction, poll_id: str,
                    template_name: str = "poll_reminder", remind_times: str = "60,30,10"):
        try:
            # Parse remind times
            try:
                minutes_list = [int(x.strip()) for x in remind_times.split(',')]
            except ValueError:
                await interaction.response.send_message("❌ Invalid remind_times format. Use comma-separated minutes like: 60,30,10", ephemeral=True)
                return

            # Set up reminders
            created_reminders = []
            for minutes in minutes_list:
                reminder = await self.service.create_reminder(
                    template_name=template_name,
                    channel_id=interaction.channel.id,
                    creator_id=interaction.user.id,
                    trigger_type=TriggerType.TIME_BEFORE,
                    target_type="poll",
                    target_id=poll_id,
                    minutes_before=minutes
                )
                created_reminders.append(reminder)

            embed = EmbedBuilder()\
                .set_title("⚡ Quick Poll Reminders Set")\
                .set_description(f"Created {len(created_reminders)} reminders for poll `{poll_id}`")\
                .set_color(0x00ff00)

            reminder_list = []
            for i, reminder in enumerate(created_reminders):
                minutes = minutes_list[i]
                reminder_list.append(f"• {minutes} minutes before expiry")

            embed.add_field("Reminders Created", "\n".join(reminder_list), inline=False)
            embed.add_field("Template Used", template_name, inline=True)

            await interaction.response.send_message(embed=embed.build())

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class ListRemindersCommand(BaseCommand):
    """Command to list user's reminders"""

    def __init__(self, bot, services):
        super().__init__(bot, services)
        self.service = services.get("reminder_service")

    async def handle(self, interaction: discord.Interaction, show_inactive: bool = False):
        try:
            reminders = await self.service.list_reminders(
                creator_id=interaction.user.id,
                is_active=None if show_inactive else True
            )

            if not reminders:
                await interaction.response.send_message("📝 No reminders found.", ephemeral=True)
                return

            embed = EmbedBuilder()\
                .set_title(f"⏰ Your Reminders {'(Including Inactive)' if show_inactive else '(Active Only)'}")\
                .set_color(0x3498db)

            for reminder in reminders[:10]:  # Limit to 10 reminders
                status = "🟢 Active" if reminder.is_active else "🔴 Inactive"
                next_trigger = reminder.next_trigger.strftime("%Y-%m-%d %H:%M UTC") if reminder.next_trigger else "N/A"

                embed.add_field(
                    f"🔖 {reminder.reminder_id[:8]}",
                    f"**Status:** {status}\n"
                    f"**Type:** {reminder.target_type.title() if reminder.target_type else 'Custom'}\n"
                    f"**Target:** {reminder.target_id or 'N/A'}\n"
                    f"**Next:** {next_trigger}\n"
                    f"**Count:** {reminder.occurrence_count}",
                    inline=True
                )

            if len(reminders) > 10:
                embed.set_footer(f"Showing 10 of {len(reminders)} reminders")

            await interaction.response.send_message(embed=embed.build())

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class CancelReminderCommand(BaseCommand):
    """Command to cancel an active reminder"""

    def __init__(self, bot, services):
        super().__init__(bot, services)
        self.service = services.get("reminder_service")

    async def handle(self, interaction: discord.Interaction, reminder_id: str):
        try:
            success = await self.service.cancel_reminder(reminder_id)

            if success:
                embed = EmbedBuilder()\
                    .set_title("✅ Reminder Cancelled")\
                    .set_description(f"Reminder `{reminder_id}` has been cancelled.")\
                    .set_color(0x00ff00)\
                    .build()

                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("❌ Reminder not found or already inactive.", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class ReminderLogsCommand(BaseCommand):
    """Command to view execution logs for a reminder"""

    def __init__(self, bot, services):
        super().__init__(bot, services)
        self.service = services.get("reminder_service")

    async def handle(self, interaction: discord.Interaction, reminder_id: str):
        try:
            # Get reminder to check ownership
            reminder = await self.service.get_reminder(reminder_id)
            if not reminder:
                await interaction.response.send_message("❌ Reminder not found.", ephemeral=True)
                return

            # Check if user owns the reminder or is admin
            if reminder.creator_id != interaction.user.id and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ You can only view logs for your own reminders.", ephemeral=True)
                return

            # Get logs
            logs = await self.service.get_reminder_logs(reminder_id)

            if not logs:
                embed = (EmbedBuilder()
                        .set_title("📋 Reminder Logs")
                        .set_description(f"No execution logs found for reminder `{reminder_id[:8]}`")
                        .set_color("orange")
                        .build())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            embed = (EmbedBuilder()
                    .set_title("📋 Reminder Execution Logs")
                    .set_description(f"Execution history for reminder `{reminder_id[:8]}`")
                    .set_color("blue"))

            # Add log entries (limit to latest 10)
            for i, log in enumerate(logs[:10]):
                status_emoji = "✅" if log.success else "❌"
                embed.add_field(
                    f"{status_emoji} Execution #{i+1}",
                    f"**Time:** {log.executed_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"**Status:** {'Success' if log.success else 'Failed'}\n"
                    f"**Details:** {log.details[:100]}{'...' if len(log.details) > 100 else ''}",
                    inline=True
                )

            if len(logs) > 10:
                embed.set_footer(f"Showing latest 10 of {len(logs)} executions")

            embed.add_field(
                "📊 Summary",
                f"**Total Executions:** {len(logs)}\n"
                f"**Successful:** {sum(1 for log in logs if log.success)}\n"
                f"**Failed:** {sum(1 for log in logs if not log.success)}",
                inline=False
            )

            await interaction.response.send_message(embed=embed.build(), ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)