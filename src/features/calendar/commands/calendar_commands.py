from typing import Dict, Any, Optional
import discord
from discord import app_commands
from datetime import datetime, timedelta

from src.core.base_command import BaseCommand
from src.core.validators import validate_required, validate_integer, validate_string_length
from src.core.builders import EmbedBuilder

class CalendarHelpCommand(BaseCommand):
    """Show calendar system help and instructions"""

    async def validate_input(self, interaction: discord.Interaction, **kwargs) -> Dict[str, Any]:
        """No validation needed for help command"""
        return {"validated": True}

    async def check_permissions(self, interaction: discord.Interaction, **kwargs) -> bool:
        """Anyone can view help"""
        return True

    async def execute_command(self, interaction: discord.Interaction, calendar_service, **kwargs):
        """Show calendar help"""
        embed = calendar_service.build_help_embed().build()
        await interaction.response.send_message(embed=embed, ephemeral=True)

class LinkUserCalendarCommand(BaseCommand):
    """Link user's personal Google Calendar"""

    async def validate_input(self, interaction: discord.Interaction, calendar_id: str = "", **kwargs) -> Dict[str, Any]:
        """Validate calendar ID format"""
        if not calendar_id.strip():
            return {
                "error": "Missing Calendar ID",
                "message": "You need to provide your Google Calendar ID to link it.",
                "show_instructions": True
            }

        # Get calendar service for validation
        calendar_service = self.container.get("calendar_service")
        if not calendar_service.validate_calendar_id(calendar_id):
            return {
                "error": "Invalid Calendar ID",
                "message": "Calendar ID should look like an email address (e.g., `example@gmail.com`)"
            }

        return {"calendar_id": calendar_id}

    async def check_permissions(self, interaction: discord.Interaction, **kwargs) -> bool:
        """Anyone can link their personal calendar"""
        return True

    async def execute_command(self, interaction: discord.Interaction, calendar_service, calendar_id: str, **kwargs):
        """Link user's calendar"""
        success = await calendar_service.link_user_calendar(interaction.user.id, calendar_id)

        if success:
            embed = (EmbedBuilder()
                    .set_title("✅ Calendar Linked Successfully")
                    .set_description(f"Your Google Calendar has been linked!\n\n**Calendar ID:** `{calendar_id}`")
                    .set_color("green")
                    .add_field("What's Next?",
                              "• Admins can now add you to shared calendars\n• Your free/busy status will be visible to authorized users\n• You'll receive event invitations in your personal calendar",
                              inline=False))
        else:
            embed = (EmbedBuilder()
                    .set_title("❌ Error Linking Calendar")
                    .set_description("Failed to link calendar. Please try again.")
                    .set_color("red"))

        await interaction.response.send_message(embed=embed.build(), ephemeral=True)

    async def handle_validation_error(self, interaction: discord.Interaction, error_data: Dict[str, Any]):
        """Handle validation errors with custom instructions"""
        embed = (EmbedBuilder()
                .set_title(f"❌ {error_data['error']}")
                .set_description(error_data["message"])
                .set_color("red"))

        if error_data.get("show_instructions"):
            calendar_service = self.container.get("calendar_service")
            embed.add_field("📋 Instructions", calendar_service.CALENDAR_SHARING_INSTRUCTIONS, inline=False)

        await interaction.response.send_message(embed=embed.build(), ephemeral=True)

class CreateSharedCalendarCommand(BaseCommand):
    """Create a new shared calendar (Admin only)"""

    async def validate_input(self, interaction: discord.Interaction, calendar_name: str, description: str = "", **kwargs) -> Dict[str, Any]:
        """Validate calendar creation parameters"""
        calendar_name = validate_required(calendar_name, "Calendar name")
        calendar_name = validate_string_length(calendar_name, 1, 100, "Calendar name")
        description = validate_string_length(description, 0, 500, "Description")

        return {"calendar_name": calendar_name, "description": description}

    async def check_permissions(self, interaction: discord.Interaction, **kwargs) -> bool:
        """Only server owner can create shared calendars"""
        return interaction.user.id == self.bot.owner_id

    async def get_permission_error(self, interaction: discord.Interaction) -> str:
        """Custom permission error message"""
        return "Only the server owner can create shared calendars."

    async def execute_command(self, interaction: discord.Interaction, calendar_service, calendar_name: str, description: str, **kwargs):
        """Create shared calendar"""
        # Check if calendar already exists
        existing_calendar = await calendar_service.get_calendar(calendar_name)
        if existing_calendar:
            embed = (EmbedBuilder()
                    .set_title("❌ Calendar Already Exists")
                    .set_description(f"A calendar named '{calendar_name}' already exists.")
                    .set_color("red"))
            await interaction.response.send_message(embed=embed.build(), ephemeral=True)
            return

        # Create calendar
        google_calendar_id = f"{calendar_name.lower().replace(' ', '_')}@{interaction.guild.name.lower()}.calendar"
        calendar = await calendar_service.create_calendar(
            name=calendar_name,
            creator_id=interaction.user.id,
            description=description,
            google_calendar_id=google_calendar_id
        )

        embed = calendar_service.build_calendar_success_embed(calendar).build()
        await interaction.response.send_message(embed=embed, ephemeral=True)

class AddCalendarUsersCommand(BaseCommand):
    """Add users to shared calendar with specific permissions (Admin only)"""

    async def validate_input(self, interaction: discord.Interaction, calendar_name: str, permission: str,
                           roles: str = "", users: str = "", **kwargs) -> Dict[str, Any]:
        calendar_name = validate_required(calendar_name, "Calendar name")
        permission = validate_required(permission, "Permission level")

        calendar_service = self.container.get("calendar_service")
        if not calendar_service.validate_permission_level(permission):
            return {
                "error": "Invalid Permission",
                "message": f"Permission must be one of: reader, writer, owner"
            }

        if not roles.strip() and not users.strip():
            return {
                "error": "Missing Users or Roles",
                "message": "You must specify either roles or users to add to the calendar."
            }

        return {
            "calendar_name": calendar_name,
            "permission": permission.lower(),
            "roles": roles,
            "users": users
        }

    async def check_permissions(self, interaction: discord.Interaction, **kwargs) -> bool:
        return interaction.user.id == self.bot.owner_id

    async def get_permission_error(self, interaction: discord.Interaction) -> str:
        return "Only the server owner can manage calendar permissions."

    async def execute_command(self, interaction: discord.Interaction, calendar_service,
                            calendar_name: str, permission: str, roles: str, users: str, **kwargs):
        calendar = await calendar_service.get_calendar(calendar_name)
        if not calendar:
            embed = (EmbedBuilder()
                    .set_title("❌ Calendar Not Found")
                    .set_description(f"No calendar named '{calendar_name}' exists.")
                    .set_color("red"))
            await interaction.response.send_message(embed=embed.build(), ephemeral=True)
            return

        guild = interaction.guild
        added_users = []

        if roles.strip():
            role_names = [r.strip() for r in roles.split(",") if r.strip()]
            role_added_users = await calendar_service.add_users_by_roles(
                calendar.id, role_names, permission, interaction.user.id, guild.members
            )
            added_users.extend([guild.get_member(user_id) for user_id in role_added_users if guild.get_member(user_id)])

        if users.strip():
            for member in guild.members:
                if (f"@{member.display_name}" in users or
                    f"@{member.name}" in users or
                    str(member.id) in users or
                    member.mention in users):
                    success = await calendar_service.add_permission(
                        calendar.id, member.id, permission, interaction.user.id
                    )
                    if success and member not in added_users:
                        added_users.append(member)

        if not added_users:
            embed = (EmbedBuilder()
                    .set_title("❌ No Users Found")
                    .set_description("No valid users or roles were found to add to the calendar.")
                    .set_color("red"))
            await interaction.response.send_message(embed=embed.build(), ephemeral=True)
            return

        invitation_count = 0
        for user in added_users:
            try:
                embed_invite = (EmbedBuilder()
                               .set_title("📅 Calendar Invitation")
                               .set_description(f"You've been added to the shared calendar: **{calendar_name}**")
                               .set_color("blue")
                               .add_field("🔐 Permission Level", permission.title(), inline=True)
                               .add_field("🏠 Server", guild.name, inline=True)
                               .add_field("📋 What You Can Do",
                                         "• View calendar events\n• Receive event notifications\n• Use calendar commands" +
                                         ("\n• Create and edit events" if permission in ["writer", "owner"] else "") +
                                         ("\n• Manage calendar users" if permission == "owner" else ""),
                                         inline=False))

                await user.send(embed=embed_invite.build())
                invitation_count += 1
            except:
                pass

        user_list = ", ".join([user.display_name for user in added_users[:10]])
        if len(added_users) > 10:
            user_list += f" and {len(added_users) - 10} more..."

        embed = (EmbedBuilder()
                .set_title("✅ Users Added to Calendar")
                .set_description(f"Successfully added {len(added_users)} users to calendar **{calendar_name}**")
                .set_color("green")
                .add_field("🔐 Permission Level", permission.title(), inline=True)
                .add_field("📧 Invitations Sent", f"{invitation_count}/{len(added_users)}", inline=True)
                .add_field("👥 Added Users", user_list, inline=False))

        await interaction.response.send_message(embed=embed.build(), ephemeral=True)

class ListCalendarUsersCommand(BaseCommand):
    """List users with access to a shared calendar"""

    async def validate_input(self, interaction: discord.Interaction, calendar_name: str, **kwargs) -> Dict[str, Any]:
        calendar_name = validate_required(calendar_name, "Calendar name")
        return {"calendar_name": calendar_name}

    async def check_permissions(self, interaction: discord.Interaction, **kwargs) -> bool:
        return True

    async def execute_command(self, interaction: discord.Interaction, calendar_service, calendar_name: str, **kwargs):
        calendar = await calendar_service.get_calendar(calendar_name)
        if not calendar:
            embed = (EmbedBuilder()
                    .set_title("❌ Calendar Not Found")
                    .set_description(f"No calendar named '{calendar_name}' exists.")
                    .set_color("red"))
            await interaction.response.send_message(embed=embed.build(), ephemeral=True)
            return

        permissions = await calendar_service.get_calendar_users(calendar.id)
        embed = calendar_service.build_users_list_embed(calendar_name, permissions, interaction.guild).build()
        await interaction.response.send_message(embed=embed, ephemeral=True)

class RemoveCalendarUsersCommand(BaseCommand):
    """Remove users from shared calendar (Admin only)"""

    async def validate_input(self, interaction: discord.Interaction, calendar_name: str,
                           roles: str = "", users: str = "", **kwargs) -> Dict[str, Any]:
        calendar_name = validate_required(calendar_name, "Calendar name")

        if not roles.strip() and not users.strip():
            return {
                "error": "Missing Users or Roles",
                "message": "You must specify either roles or users to remove from the calendar."
            }

        return {"calendar_name": calendar_name, "roles": roles, "users": users}

    async def check_permissions(self, interaction: discord.Interaction, **kwargs) -> bool:
        return interaction.user.id == self.bot.owner_id

    async def get_permission_error(self, interaction: discord.Interaction) -> str:
        return "Only the server owner can manage calendar permissions."

    async def execute_command(self, interaction: discord.Interaction, calendar_service,
                            calendar_name: str, roles: str, users: str, **kwargs):
        calendar = await calendar_service.get_calendar(calendar_name)
        if not calendar:
            embed = (EmbedBuilder()
                    .set_title("❌ Calendar Not Found")
                    .set_description(f"No calendar named '{calendar_name}' exists.")
                    .set_color("red"))
            await interaction.response.send_message(embed=embed.build(), ephemeral=True)
            return

        guild = interaction.guild
        removed_users = []

        if roles.strip():
            role_names = [r.strip() for r in roles.split(",") if r.strip()]
            role_removed_users = await calendar_service.remove_users_by_roles(
                calendar.id, role_names, guild.members
            )
            removed_users.extend([guild.get_member(user_id) for user_id in role_removed_users if guild.get_member(user_id)])

        if users.strip():
            for member in guild.members:
                if (f"@{member.display_name}" in users or
                    f"@{member.name}" in users or
                    str(member.id) in users or
                    member.mention in users):
                    success = await calendar_service.remove_permission(calendar.id, member.id)
                    if success and member not in removed_users:
                        removed_users.append(member)

        if not removed_users:
            embed = (EmbedBuilder()
                    .set_title("❌ No Users Found")
                    .set_description("No valid users or roles were found to remove from the calendar.")
                    .set_color("red"))
            await interaction.response.send_message(embed=embed.build(), ephemeral=True)
            return

        user_list = ", ".join([user.display_name for user in removed_users[:10]])
        if len(removed_users) > 10:
            user_list += f" and {len(removed_users) - 10} more..."

        embed = (EmbedBuilder()
                .set_title("✅ Users Removed from Calendar")
                .set_description(f"Successfully removed {len(removed_users)} users from calendar **{calendar_name}**")
                .set_color("green")
                .add_field("👥 Removed Users", user_list, inline=False))

        await interaction.response.send_message(embed=embed.build(), ephemeral=True)

class AddEventCommand(BaseCommand):
    """Create a new event in shared calendar"""

    async def validate_input(self, interaction: discord.Interaction, calendar_name: str, event_name: str,
                           start_time: str, end_time: str, location: str = "", description: str = "",
                           roles: str = "", **kwargs) -> Dict[str, Any]:
        """Validate event creation parameters"""
        calendar_name = validate_required(calendar_name, "Calendar name")
        event_name = validate_required(event_name, "Event name")
        event_name = validate_string_length(event_name, 1, 200, "Event name")
        start_time = validate_required(start_time, "Start time")
        end_time = validate_required(end_time, "End time")

        calendar_service = self.container.get("calendar_service")

        # Parse start time
        start_dt = calendar_service.validate_datetime_format(start_time)
        if not start_dt:
            return {
                "error": "Invalid Start Time",
                "message": "Start time format should be: YYYY-MM-DD HH:MM\nExample: 2024-01-15 14:30"
            }

        # Parse end time
        end_dt = calendar_service.validate_datetime_format(end_time)
        if not end_dt:
            return {
                "error": "Invalid End Time",
                "message": "End time format should be: YYYY-MM-DD HH:MM\nExample: 2024-01-15 16:30"
            }

        # Validate time order
        if start_dt >= end_dt:
            return {
                "error": "Invalid Time Range",
                "message": "Start time must be before end time."
            }

        return {
            "calendar_name": calendar_name,
            "event_name": event_name,
            "start_time": start_dt,
            "end_time": end_dt,
            "location": validate_string_length(location, 0, 500, "Location"),
            "description": validate_string_length(description, 0, 1000, "Description"),
            "roles": roles
        }

    async def check_permissions(self, interaction: discord.Interaction, calendar_name: str, **kwargs) -> bool:
        """Check if user has write permission for the calendar"""
        calendar_service = self.container.get("calendar_service")
        calendar = await calendar_service.get_calendar(calendar_name)
        if not calendar:
            return False
        return await calendar_service.has_permission(calendar.id, interaction.user.id, "writer")

    async def get_permission_error(self, interaction: discord.Interaction) -> str:
        """Custom permission error message"""
        return "You need writer or owner permission to create events in this calendar."

    async def execute_command(self, interaction: discord.Interaction, calendar_service,
                            calendar_name: str, event_name: str, start_time: datetime, end_time: datetime,
                            location: str, description: str, roles: str, **kwargs):
        """Create event"""
        # Get the calendar (validation already checked it exists)
        calendar = await calendar_service.get_calendar(calendar_name)

        # Create the event
        event = await calendar_service.create_event(
            calendar_id=calendar.id,
            title=event_name,
            start_time=start_time,
            end_time=end_time,
            created_by=interaction.user.id,
            description=description,
            location=location
        )

        embed = (EmbedBuilder()
                .set_title("✅ Event Created")
                .set_description(f"Successfully created event: **{event_name}**")
                .set_color("green")
                .add_field("📅 Calendar", calendar_name, inline=True)
                .add_field("🆔 Event ID", str(event.id), inline=True)
                .add_field("🕐 Start Time", start_time.strftime("%Y-%m-%d %H:%M"), inline=True)
                .add_field("🕑 End Time", end_time.strftime("%Y-%m-%d %H:%M"), inline=True))

        if location:
            embed.add_field("📍 Location", location, inline=True)

        if description:
            embed.add_field("📝 Description", description[:200] + ("..." if len(description) > 200 else ""), inline=False)

        await interaction.response.send_message(embed=embed.build(), ephemeral=True)

class ListEventsCommand(BaseCommand):
    """List upcoming events in shared calendar"""

    async def validate_input(self, interaction: discord.Interaction, calendar_name: str, days_ahead: int = 7, **kwargs) -> Dict[str, Any]:
        """Validate event listing parameters"""
        calendar_name = validate_required(calendar_name, "Calendar name")
        days_ahead = validate_integer(days_ahead, min_val=1, max_val=365, field_name="Days ahead")

        return {"calendar_name": calendar_name, "days_ahead": days_ahead}

    async def check_permissions(self, interaction: discord.Interaction, calendar_name: str, **kwargs) -> bool:
        """Check if user has read permission for the calendar"""
        calendar_service = self.container.get("calendar_service")
        calendar = await calendar_service.get_calendar(calendar_name)
        if not calendar:
            return False
        return await calendar_service.has_permission(calendar.id, interaction.user.id, "reader")

    async def get_permission_error(self, interaction: discord.Interaction) -> str:
        """Custom permission error message"""
        return "You don't have permission to view events in this calendar."

    async def execute_command(self, interaction: discord.Interaction, calendar_service,
                            calendar_name: str, days_ahead: int, **kwargs):
        """List events"""
        # Get the calendar (validation already checked it exists)
        calendar = await calendar_service.get_calendar(calendar_name)

        # Get events for the specified period
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days_ahead)
        events = await calendar_service.get_calendar_events(calendar.id, start_date, end_date)

        embed = (EmbedBuilder()
                .set_title(f"📅 Upcoming Events - {calendar_name}")
                .set_description(f"Events in the next {days_ahead} days")
                .set_color("blue"))

        if not events:
            embed.add_field("📭 No Events", f"No events scheduled in the next {days_ahead} days.", inline=False)
        else:
            for i, event in enumerate(events[:10]):  # Limit to 10 events
                event_info = f"🕐 {event.start_time.strftime('%Y-%m-%d %H:%M')} - {event.end_time.strftime('%H:%M')}"
                if event.location:
                    event_info += f"\n📍 {event.location}"
                if event.description:
                    event_info += f"\n📝 {event.description[:100]}{'...' if len(event.description) > 100 else ''}"

                embed.add_field(f"🎯 {event.title} (ID: {event.id})", event_info, inline=False)

            if len(events) > 10:
                embed.add_field("📋 More Events", f"And {len(events) - 10} more events...", inline=False)

        embed.add_field("📊 Summary", f"**{len(events)}** events found", inline=True)
        embed.add_field("📅 Date Range", f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", inline=True)

        await interaction.response.send_message(embed=embed.build(), ephemeral=True)

class UpdateEventCommand(BaseCommand):
    """Update an existing event in shared calendar"""

    async def validate_input(self, interaction: discord.Interaction, calendar_name: str, event_id: str,
                           event_name: str = "", start_time: str = "", end_time: str = "",
                           location: str = "", description: str = "", **kwargs) -> Dict[str, Any]:
        """Validate event update parameters"""
        calendar_name = validate_required(calendar_name, "Calendar name")
        event_id = validate_required(event_id, "Event ID")

        try:
            event_id_int = validate_integer(int(event_id), min_val=1, field_name="Event ID")
        except ValueError:
            return {"error": "Invalid Event ID", "message": "Event ID must be a number."}

        updates = {}
        calendar_service = self.container.get("calendar_service")

        if event_name:
            updates["title"] = validate_string_length(event_name, 1, 200, "Event name")

        if start_time:
            start_dt = calendar_service.validate_datetime_format(start_time)
            if not start_dt:
                return {
                    "error": "Invalid Start Time",
                    "message": "Start time format should be: YYYY-MM-DD HH:MM"
                }
            updates["start_time"] = start_dt

        if end_time:
            end_dt = calendar_service.validate_datetime_format(end_time)
            if not end_dt:
                return {
                    "error": "Invalid End Time",
                    "message": "End time format should be: YYYY-MM-DD HH:MM"
                }
            updates["end_time"] = end_dt

        # Validate time order if both are provided
        if "start_time" in updates and "end_time" in updates:
            if updates["start_time"] >= updates["end_time"]:
                return {
                    "error": "Invalid Time Range",
                    "message": "Start time must be before end time."
                }

        if location is not None:
            updates["location"] = validate_string_length(location, 0, 500, "Location")

        if description is not None:
            updates["description"] = validate_string_length(description, 0, 1000, "Description")

        if not updates:
            return {
                "error": "No Updates Provided",
                "message": "You must provide at least one field to update."
            }

        return {
            "calendar_name": calendar_name,
            "event_id": event_id_int,
            "updates": updates
        }

    async def check_permissions(self, interaction: discord.Interaction, calendar_name: str, **kwargs) -> bool:
        """Check if user has write permission for the calendar"""
        calendar_service = self.container.get("calendar_service")
        calendar = await calendar_service.get_calendar(calendar_name)
        if not calendar:
            return False
        return await calendar_service.has_permission(calendar.id, interaction.user.id, "writer")

    async def get_permission_error(self, interaction: discord.Interaction) -> str:
        """Custom permission error message"""
        return "You need writer or owner permission to update events in this calendar."

    async def execute_command(self, interaction: discord.Interaction, calendar_service,
                            calendar_name: str, event_id: int, updates: Dict[str, Any], **kwargs):
        """Update event"""
        # Get the event
        event = await calendar_service.get_event(event_id)
        if not event:
            embed = (EmbedBuilder()
                    .set_title("❌ Event Not Found")
                    .set_description(f"No event found with ID: {event_id}")
                    .set_color("red"))
            await interaction.response.send_message(embed=embed.build(), ephemeral=True)
            return

        # Update the event
        success = await calendar_service.update_event(event_id, **updates)

        if success:
            embed = (EmbedBuilder()
                    .set_title("✅ Event Updated")
                    .set_description(f"Successfully updated event: **{event.title}**")
                    .set_color("green")
                    .add_field("📅 Calendar", calendar_name, inline=True)
                    .add_field("🆔 Event ID", str(event_id), inline=True))

            # Show what was updated
            update_info = []
            for key, value in updates.items():
                if key == "start_time" or key == "end_time":
                    update_info.append(f"• {key.replace('_', ' ').title()}: {value.strftime('%Y-%m-%d %H:%M')}")
                else:
                    update_info.append(f"• {key.replace('_', ' ').title()}: {value}")

            if update_info:
                embed.add_field("📝 Updated Fields", "\n".join(update_info), inline=False)
        else:
            embed = (EmbedBuilder()
                    .set_title("❌ Update Failed")
                    .set_description("Failed to update the event.")
                    .set_color("red"))

        await interaction.response.send_message(embed=embed.build(), ephemeral=True)

class DeleteEventCommand(BaseCommand):
    """Delete an event from shared calendar"""

    async def validate_input(self, interaction: discord.Interaction, calendar_name: str, event_id: str, **kwargs) -> Dict[str, Any]:
        """Validate event deletion parameters"""
        calendar_name = validate_required(calendar_name, "Calendar name")
        event_id = validate_required(event_id, "Event ID")

        try:
            event_id_int = validate_integer(int(event_id), min_val=1, field_name="Event ID")
        except ValueError:
            return {"error": "Invalid Event ID", "message": "Event ID must be a number."}

        return {"calendar_name": calendar_name, "event_id": event_id_int}

    async def check_permissions(self, interaction: discord.Interaction, calendar_name: str, **kwargs) -> bool:
        """Check if user has write permission for the calendar"""
        calendar_service = self.container.get("calendar_service")
        calendar = await calendar_service.get_calendar(calendar_name)
        if not calendar:
            return False
        return await calendar_service.has_permission(calendar.id, interaction.user.id, "writer")

    async def get_permission_error(self, interaction: discord.Interaction) -> str:
        """Custom permission error message"""
        return "You need writer or owner permission to delete events from this calendar."

    async def execute_command(self, interaction: discord.Interaction, calendar_service,
                            calendar_name: str, event_id: int, **kwargs):
        """Delete event"""
        # Get the event first
        event = await calendar_service.get_event(event_id)
        if not event:
            embed = (EmbedBuilder()
                    .set_title("❌ Event Not Found")
                    .set_description(f"No event found with ID: {event_id}")
                    .set_color("red"))
            await interaction.response.send_message(embed=embed.build(), ephemeral=True)
            return

        # Delete the event
        success = await calendar_service.delete_event(event_id)

        if success:
            embed = (EmbedBuilder()
                    .set_title("✅ Event Deleted")
                    .set_description(f"Successfully deleted event: **{event.title}**")
                    .set_color("green")
                    .add_field("📅 Calendar", calendar_name, inline=True)
                    .add_field("🆔 Event ID", str(event_id), inline=True)
                    .add_field("ℹ️ Note", "Event has been removed from all associated personal calendars", inline=False))
        else:
            embed = (EmbedBuilder()
                    .set_title("❌ Deletion Failed")
                    .set_description("Failed to delete the event.")
                    .set_color("red"))

        await interaction.response.send_message(embed=embed.build(), ephemeral=True)

class VisualizeDayCommand(BaseCommand):
    """Visualize a specific day's schedule"""

    async def validate_input(self, interaction: discord.Interaction, calendar_name: str, date: str,
                           start_hour: int = 8, end_hour: int = 18, **kwargs) -> Dict[str, Any]:
        """Validate day visualization parameters"""
        calendar_name = validate_required(calendar_name, "Calendar name")
        date = validate_required(date, "Date")

        calendar_service = self.container.get("calendar_service")
        target_date = calendar_service.validate_date_format(date)
        if not target_date:
            return {
                "error": "Invalid Date Format",
                "message": "Please use format: `YYYY-MM-DD`\n\nExample: `2024-01-15`"
            }

        # Validate hours
        start_hour = validate_integer(start_hour, min_val=0, max_val=23, field_name="Start hour")
        end_hour = validate_integer(end_hour, min_val=0, max_val=23, field_name="End hour")

        if start_hour >= end_hour:
            return {
                "error": "Invalid Hours",
                "message": "Start hour must be less than end hour."
            }

        return {
            "calendar_name": calendar_name,
            "target_date": target_date.date(),
            "start_hour": start_hour,
            "end_hour": end_hour
        }

    async def check_permissions(self, interaction: discord.Interaction, calendar_name: str, **kwargs) -> bool:
        """Check if user has read permission for the calendar"""
        calendar_service = self.container.get("calendar_service")
        calendar = await calendar_service.get_calendar(calendar_name)
        if not calendar:
            return False
        return await calendar_service.has_permission(calendar.id, interaction.user.id, "reader")

    async def get_permission_error(self, interaction: discord.Interaction) -> str:
        """Custom permission error message"""
        return "You don't have permission to view events in this calendar."

    async def execute_command(self, interaction: discord.Interaction, calendar_service,
                            calendar_name: str, target_date, start_hour: int, end_hour: int, **kwargs):
        """Visualize day schedule"""
        # Get the calendar (validation already checked it exists)
        calendar = await calendar_service.get_calendar(calendar_name)

        # Get events for the day
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = datetime.combine(target_date, datetime.max.time())
        events = await calendar_service.get_calendar_events(calendar.id, day_start, day_end)

        # Create day visualization
        embed = (EmbedBuilder()
                .set_title(f"📅 {calendar_name} - {target_date.strftime('%A, %B %d, %Y')}")
                .set_color("blue"))

        # Create hourly schedule
        schedule_lines = []
        for hour in range(start_hour, end_hour + 1):
            hour_str = f"{hour:02d}:00"

            # Check for events at this hour
            events_at_hour = []
            for event in events:
                event_start_hour = event.start_time.hour
                event_end_hour = event.end_time.hour
                if event_start_hour <= hour < event_end_hour or (hour == event_start_hour):
                    events_at_hour.append(event)

            if events_at_hour:
                for event in events_at_hour:
                    schedule_lines.append(f"**{hour_str}** 📍 **{event.title}** ({event.start_time.strftime('%H:%M')}-{event.end_time.strftime('%H:%M')})")
                    if event.location:
                        schedule_lines.append(f"        📍 {event.location}")
            else:
                schedule_lines.append(f"{hour_str} ⬜ *Free*")

        # Split into chunks if too long
        schedule_text = "\n".join(schedule_lines)
        if len(schedule_text) > 1024:
            # Split the schedule into multiple fields
            chunks = []
            current_chunk = ""

            for line in schedule_lines:
                if len(current_chunk) + len(line) > 1020:
                    chunks.append(current_chunk)
                    current_chunk = line + '\n'
                else:
                    current_chunk += line + '\n'

            if current_chunk:
                chunks.append(current_chunk)

            for i, chunk in enumerate(chunks):
                field_name = "📅 Schedule" if i == 0 else f"📅 Schedule (cont. {i+1})"
                embed.add_field(field_name, chunk, inline=False)
        else:
            embed.add_field("📅 Schedule", schedule_text, inline=False)

        # Add summary
        total_events = len(events)
        embed.add_field("📊 Summary", f"**{total_events}** events scheduled", inline=True)
        embed.add_field("🕐 Time Range", f"{start_hour:02d}:00 - {end_hour:02d}:00", inline=True)

        await interaction.response.send_message(embed=embed.build(), ephemeral=True)


class FindFreeSlotsCommand(BaseCommand):
    """Find free time slots in user's personal calendar"""

    async def validate_input(self, interaction: discord.Interaction, start: str, end: str, duration: int = 30, **kwargs) -> Dict[str, Any]:
        """Validate input parameters"""
        # Validate required fields
        start = validate_required(start, "Start time")
        end = validate_required(end, "End time")
        duration = validate_integer(duration, 1, 480, "Duration")  # 1 minute to 8 hours

        # Parse and validate datetime strings
        try:
            start_dt = datetime.fromisoformat(start.replace('T', ' '))
        except ValueError:
            return {
                "error": "Invalid Start Time",
                "message": "Start time must be in format: YYYY-MM-DD HH:MM"
            }

        try:
            end_dt = datetime.fromisoformat(end.replace('T', ' '))
        except ValueError:
            return {
                "error": "Invalid End Time",
                "message": "End time must be in format: YYYY-MM-DD HH:MM"
            }

        # Validate time range
        if start_dt >= end_dt:
            return {
                "error": "Invalid Time Range",
                "message": "Start time must be before end time"
            }

        # Validate duration fits in time range
        time_range_minutes = (end_dt - start_dt).total_seconds() / 60
        if duration > time_range_minutes:
            return {
                "error": "Duration Too Long",
                "message": f"Duration ({duration} minutes) is longer than the time range ({int(time_range_minutes)} minutes)"
            }

        return {
            "start_dt": start_dt,
            "end_dt": end_dt,
            "duration": duration
        }

    async def check_permissions(self, interaction: discord.Interaction, **kwargs) -> bool:
        """Anyone can check their own free slots"""
        return True

    async def execute_command(self, interaction: discord.Interaction, calendar_service,
                            start_dt: datetime, end_dt: datetime, duration: int, **kwargs):
        """Find and display free time slots"""
        try:
            # Check if user has linked their calendar
            user_calendar = await calendar_service.get_user_calendar(interaction.user.id)
            if not user_calendar:
                embed = (EmbedBuilder()
                        .set_title("❌ Calendar Not Linked")
                        .set_description("You must link your Google Calendar first using `/link_user_calendar`")
                        .set_color("red")
                        .add_field("How to Link Calendar", calendar_service.CALENDAR_SHARING_INSTRUCTIONS, inline=False))
                await interaction.response.send_message(embed=embed.build(), ephemeral=True)
                return

            # Get busy times from user's calendar
            busy_times = await calendar_service.get_user_busy_times(interaction.user.id, start_dt, end_dt)

            # Find free slots
            free_slots = []
            current = start_dt

            while current + timedelta(minutes=duration) <= end_dt:
                slot_end = current + timedelta(minutes=duration)
                is_free = True

                # Check if this slot conflicts with any busy time
                for busy_start, busy_end in busy_times:
                    if not (slot_end <= busy_start or current >= busy_end):
                        is_free = False
                        break

                if is_free:
                    free_slots.append(current.strftime('%Y-%m-%d %H:%M'))

                current += timedelta(minutes=duration)

            # Build response embed
            if not free_slots:
                embed = (EmbedBuilder()
                        .set_title("📅 No Free Slots Found")
                        .set_description(f"No free {duration}-minute slots found between {start_dt.strftime('%Y-%m-%d %H:%M')} and {end_dt.strftime('%Y-%m-%d %H:%M')}")
                        .set_color("orange"))
            else:
                slot_list = "\n".join([f"• {slot}" for slot in free_slots[:20]])  # Limit to 20 slots
                if len(free_slots) > 20:
                    slot_list += f"\n... and {len(free_slots) - 20} more slots"

                embed = (EmbedBuilder()
                        .set_title("✅ Free Time Slots Found")
                        .set_description(f"Found {len(free_slots)} free {duration}-minute slots:")
                        .add_field("Available Slots", slot_list, inline=False)
                        .set_color("green"))

            await interaction.response.send_message(embed=embed.build(), ephemeral=True)

        except Exception as e:
            embed = (EmbedBuilder()
                    .set_title("❌ Error Finding Free Slots")
                    .set_description(f"An error occurred while checking your calendar: {str(e)}")
                    .set_color("red"))
            await interaction.response.send_message(embed=embed.build(), ephemeral=True)


class VisualizePeriodCommand(BaseCommand):
    """Visualize calendar events over a period of time"""

    async def validate_input(self, interaction: discord.Interaction, calendar_name: str,
                           start_date: str, end_date: str, **kwargs) -> Dict[str, Any]:
        """Validate input parameters"""
        calendar_name = validate_required(calendar_name, "Calendar name")
        start_date = validate_required(start_date, "Start date")
        end_date = validate_required(end_date, "End date")

        # Parse dates
        try:
            start_dt = datetime.fromisoformat(start_date)
        except ValueError:
            return {
                "error": "Invalid Start Date",
                "message": "Start date must be in format: YYYY-MM-DD"
            }

        try:
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            return {
                "error": "Invalid End Date",
                "message": "End date must be in format: YYYY-MM-DD"
            }

        # Validate date range
        if start_dt >= end_dt:
            return {
                "error": "Invalid Date Range",
                "message": "Start date must be before end date"
            }

        # Limit period to reasonable range (e.g., 30 days)
        if (end_dt - start_dt).days > 30:
            return {
                "error": "Period Too Long",
                "message": "Maximum period is 30 days. Please choose a shorter time range."
            }

        return {
            "calendar_name": calendar_name,
            "start_dt": start_dt,
            "end_dt": end_dt
        }

    async def check_permissions(self, interaction: discord.Interaction, calendar_name: str, **kwargs) -> bool:
        """Check if user has read access to the calendar"""
        calendar_service = self.container.get("calendar_service")
        return await calendar_service.has_calendar_permission(interaction.user.id, calendar_name, "reader")

    async def get_permission_error(self, interaction: discord.Interaction) -> str:
        return "You don't have permission to view this calendar."

    async def execute_command(self, interaction: discord.Interaction, calendar_service,
                            calendar_name: str, start_dt: datetime, end_dt: datetime, **kwargs):
        """Generate period visualization"""
        # Get calendar
        calendar = await calendar_service.get_calendar(calendar_name)
        if not calendar:
            embed = (EmbedBuilder()
                    .set_title("❌ Calendar Not Found")
                    .set_description(f"No calendar named '{calendar_name}' exists.")
                    .set_color("red"))
            await interaction.response.send_message(embed=embed.build(), ephemeral=True)
            return

        # Get events in the period
        events = await calendar_service.get_events_in_period(calendar.id, start_dt, end_dt)

        # Build period visualization embed
        embed = calendar_service.build_period_visualization_embed(calendar, start_dt, end_dt, events).build()
        await interaction.response.send_message(embed=embed, ephemeral=True)