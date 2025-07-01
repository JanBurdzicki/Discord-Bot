import discord
from discord import app_commands
from datetime import datetime, timedelta
from typing import Optional, List
import asyncio

from services.reminder_manager import ReminderPriority, TriggerType

# ========== Template Commands ==========

async def create_reminder_template_command(
    interaction: discord.Interaction,
    name: str,
    message_template: str,
    priority: str = "informational",
    description: Optional[str] = None,
    ping_roles: Optional[str] = None,
    ping_users: Optional[str] = None
):
    """Create a new reminder template"""
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
        template = await interaction.client.reminder_manager.create_template(
            name=name,
            description=description or f"Template created by {interaction.user.display_name}",
            message_template=message_template,
            priority=priority_enum,
            creator_id=interaction.user.id,
            ping_roles=ping_role_ids,
            ping_users=ping_user_ids
        )

        embed = discord.Embed(
            title="✅ Reminder Template Created",
            description=f"Template **{name}** has been created successfully!",
            color=0x00ff00
        )
        embed.add_field(name="Priority", value=priority.title(), inline=True)
        embed.add_field(name="Message Preview", value=message_template[:100] + "..." if len(message_template) > 100 else message_template, inline=False)

        await interaction.response.send_message(embed=embed)

    except ValueError as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Unexpected error: {str(e)}", ephemeral=True)

async def list_reminder_templates_command(interaction: discord.Interaction, show_mine_only: bool = False):
    """List all reminder templates"""
    try:
        creator_id = interaction.user.id if show_mine_only else None
        templates = await interaction.client.reminder_manager.list_templates(creator_id)

        if not templates:
            await interaction.response.send_message("📝 No reminder templates found.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📋 Reminder Templates {'(Your Templates)' if show_mine_only else ''}",
            color=0x3498db
        )

        for template in templates[:10]:  # Limit to 10 templates
            creator = interaction.guild.get_member(template.created_by)
            creator_name = creator.display_name if creator else "Unknown"

            embed.add_field(
                name=f"🔖 {template.name}",
                value=f"**Priority:** {template.priority.title()}\n"
                      f"**Creator:** {creator_name}\n"
                      f"**Description:** {template.description or 'No description'}",
                inline=True
            )

        if len(templates) > 10:
            embed.set_footer(text=f"Showing 10 of {len(templates)} templates")

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

# ========== Poll Reminder Commands ==========

async def set_poll_reminder_command(
    interaction: discord.Interaction,
    poll_id: str,
    template_name: str,
    reminder_type: str = "time_before",
    minutes_before: Optional[int] = None,
    interval_minutes: Optional[int] = None,
    max_occurrences: Optional[int] = None,
    specific_time: Optional[str] = None
):
    """Set a reminder for a poll"""
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

        # Create the reminder
        reminder = await interaction.client.reminder_manager.create_poll_reminder(
            poll_id=poll_id,
            template_name=template_name,
            trigger_type=trigger_type,
            channel_id=interaction.channel.id,
            creator_id=interaction.user.id,
            **kwargs
        )

        embed = discord.Embed(
            title="⏰ Poll Reminder Set",
            description=f"Reminder created for poll `{poll_id}`",
            color=0x00ff00
        )
        embed.add_field(name="Template", value=template_name, inline=True)
        embed.add_field(name="Type", value=reminder_type.replace('_', ' ').title(), inline=True)
        embed.add_field(name="Reminder ID", value=reminder.reminder_id[:8], inline=True)

        if reminder.next_trigger:
            embed.add_field(name="Next Trigger", value=reminder.next_trigger.strftime("%Y-%m-%d %H:%M UTC"), inline=False)

        await interaction.response.send_message(embed=embed)

    except ValueError as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Unexpected error: {str(e)}", ephemeral=True)

# ========== Custom Reminder Commands ==========

async def set_custom_reminder_command(
    interaction: discord.Interaction,
    template_name: str,
    reminder_type: str = "specific_time",
    interval_minutes: Optional[int] = None,
    max_occurrences: Optional[int] = None,
    specific_time: Optional[str] = None,
    custom_data: Optional[str] = None
):
    """Set a custom reminder"""
    try:
        trigger_type = TriggerType(reminder_type)

        # Validate parameters
        if trigger_type == TriggerType.INTERVAL and not interval_minutes:
            await interaction.response.send_message("❌ `interval_minutes` is required for interval reminders.", ephemeral=True)
            return
        elif trigger_type == TriggerType.SPECIFIC_TIME and not specific_time:
            await interaction.response.send_message("❌ `specific_time` is required for specific_time reminders. Format: YYYY-MM-DD HH:MM", ephemeral=True)
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

        # Parse custom data
        custom_data_dict = {}
        if custom_data:
            try:
                # Simple key=value,key2=value2 format
                for pair in custom_data.split(','):
                    key, value = pair.split('=', 1)
                    custom_data_dict[key.strip()] = value.strip()
            except ValueError:
                await interaction.response.send_message("❌ Invalid custom_data format. Use: key=value,key2=value2", ephemeral=True)
                return

        # Create the reminder
        reminder = await interaction.client.reminder_manager.create_custom_reminder(
            template_name=template_name,
            channel_id=interaction.channel.id,
            trigger_type=trigger_type,
            creator_id=interaction.user.id,
            custom_data=custom_data_dict,
            **kwargs
        )

        embed = discord.Embed(
            title="🔔 Custom Reminder Set",
            description="Custom reminder created successfully!",
            color=0x00ff00
        )
        embed.add_field(name="Template", value=template_name, inline=True)
        embed.add_field(name="Type", value=reminder_type.replace('_', ' ').title(), inline=True)
        embed.add_field(name="Reminder ID", value=reminder.reminder_id[:8], inline=True)

        if reminder.next_trigger:
            embed.add_field(name="Next Trigger", value=reminder.next_trigger.strftime("%Y-%m-%d %H:%M UTC"), inline=False)

        await interaction.response.send_message(embed=embed)

    except ValueError as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Unexpected error: {str(e)}", ephemeral=True)

# ========== Management Commands ==========

async def list_my_reminders_command(interaction: discord.Interaction, show_inactive: bool = False):
    """List user's reminders"""
    try:
        is_active = None if show_inactive else True
        reminders = await interaction.client.reminder_manager.list_reminders(
            creator_id=interaction.user.id,
            is_active=is_active
        )

        if not reminders:
            await interaction.response.send_message("📝 No reminders found.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"⏰ Your Reminders {'(Including Inactive)' if show_inactive else '(Active Only)'}",
            color=0x3498db
        )

        for reminder in reminders[:10]:  # Limit to 10 reminders
            status = "🟢 Active" if reminder.is_active else "🔴 Inactive"
            next_trigger = reminder.next_trigger.strftime("%Y-%m-%d %H:%M UTC") if reminder.next_trigger else "N/A"

            embed.add_field(
                name=f"🔖 {reminder.reminder_id[:8]}",
                value=f"**Status:** {status}\n"
                      f"**Type:** {reminder.target_type.title()}\n"
                      f"**Target:** {reminder.target_id or 'Custom'}\n"
                      f"**Next:** {next_trigger}\n"
                      f"**Count:** {reminder.occurrence_count}",
                inline=True
            )

        if len(reminders) > 10:
            embed.set_footer(text=f"Showing 10 of {len(reminders)} reminders")

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

async def cancel_reminder_command(interaction: discord.Interaction, reminder_id: str):
    """Cancel a reminder"""
    try:
        success = await interaction.client.reminder_manager.cancel_reminder(reminder_id)

        if success:
            embed = discord.Embed(
                title="✅ Reminder Cancelled",
                description=f"Reminder `{reminder_id}` has been cancelled successfully.",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ Reminder Not Found",
                description=f"Could not find reminder with ID `{reminder_id}`.",
                color=0xff0000
            )

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

async def reminder_logs_command(interaction: discord.Interaction, reminder_id: str):
    """View reminder execution logs"""
    try:
        logs = await interaction.client.reminder_manager.get_reminder_logs(reminder_id)

        if not logs:
            await interaction.response.send_message(f"📝 No logs found for reminder `{reminder_id}`.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📊 Reminder Logs - {reminder_id[:8]}",
            color=0x3498db
        )

        for log in logs[:5]:  # Show last 5 logs
            status_emoji = "✅" if log.status == "sent" else "❌" if log.status == "failed" else "⏭️"

            embed.add_field(
                name=f"{status_emoji} {log.triggered_at.strftime('%Y-%m-%d %H:%M')}",
                value=f"**Status:** {log.status.title()}\n"
                      f"**Error:** {log.error_message or 'None'}\n"
                      f"**Message:** {(log.message_content[:50] + '...') if log.message_content and len(log.message_content) > 50 else log.message_content or 'N/A'}",
                inline=True
            )

        if len(logs) > 5:
            embed.set_footer(text=f"Showing 5 of {len(logs)} logs")

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

# ========== Quick Setup Commands ==========

async def quick_poll_reminders_command(
    interaction: discord.Interaction,
    poll_id: str,
    template_name: str = "poll_reminder",
    remind_times: str = "60,30,10"  # Minutes before expiry
):
    """Quickly set up multiple time-before reminders for a poll"""
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
                'type': 'time_before',
                'template': template_name,
                'minutes_before': minutes
            })

        # Set up reminders
        created_reminders = await interaction.client.reminder_manager.setup_poll_reminders(
            poll_id=poll_id,
            channel_id=interaction.channel.id,
            creator_id=interaction.user.id,
            reminders_config=configs
        )

        embed = discord.Embed(
            title="⚡ Quick Poll Reminders Set",
            description=f"Created {len(created_reminders)} reminders for poll `{poll_id}`",
            color=0x00ff00
        )

        reminder_list = []
        for i, reminder in enumerate(created_reminders):
            minutes = minutes_list[i]
            reminder_list.append(f"• {minutes} minutes before expiry")

        embed.add_field(name="Reminders Created", value="\n".join(reminder_list), inline=False)
        embed.add_field(name="Template Used", value=template_name, inline=True)

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
