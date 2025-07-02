import discord
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import re
from sqlalchemy.future import select
from db.session import AsyncSessionLocal
from db.models import UserProfile
from services.calendar_service import CalendarService
from services.calendar_manager import CalendarManager

# Calendar sharing instructions
CALENDAR_SHARING_INSTRUCTIONS = """
**📅 How to Share Your Google Calendar as Free/Busy Reader:**

1. **Open Google Calendar** (calendar.google.com)
2. **Find your calendar** in the left sidebar
3. **Click the 3 dots** next to your calendar name
4. **Select "Settings and sharing"**
5. **Scroll to "Share with specific people"**
6. **Click "Add people"**
7. **Enter the bot's email**: `your-bot@gmail.com`
8. **Set permission to "See only free/busy (hide details)"**
9. **Click "Send"**

**📋 Alternative - Share via URL:**
1. In "Settings and sharing"
2. Go to "Access permissions"
3. Check "Make available to public"
4. Set to "See only free/busy (hide details)"
5. Copy the **Calendar ID** (looks like: `example@gmail.com`)
6. Use `/link_user_calendar <calendar_id>` command

**🔗 Need help?** Contact an admin or use `/calendar_help` for more info.
"""

async def calendar_help_command(interaction: discord.Interaction):
    """Show instructions for calendar sharing and available commands"""
    embed = discord.Embed(
        title="📅 Calendar System Help",
        description=CALENDAR_SHARING_INSTRUCTIONS,
        color=discord.Color.blue()
    )

    # Personal Calendar Commands
    embed.add_field(
        name="👤 Personal Calendar Commands",
        value="• `/link_user_calendar <calendar_id>` - Link your Google Calendar\n• `/calendar_help` - Show this help",
        inline=False
    )

    # Admin Calendar Management
    embed.add_field(
        name="🔧 Admin Calendar Management",
        value="• `/create_shared_calendar <name> [description]` - Create shared calendar\n• `/add_calendar_users <calendar> <permission> [roles] [users]` - Add users\n• `/list_calendar_users <calendar>` - List calendar access\n• `/remove_calendar_users <calendar> [roles] [users]` - Remove users",
        inline=False
    )

    # Event Management
    embed.add_field(
        name="📅 Event Management",
        value="• `/add_event <calendar> <name> <start> <end> [location] [description] [roles]` - Create event\n• `/list_events <calendar> [days_ahead]` - List upcoming events\n• `/update_event <calendar> <event_id> [name] [start] [end] [location] [description]` - Update event\n• `/delete_event <calendar> <event_id>` - Delete event",
        inline=False
    )

    # Calendar Visualization
    embed.add_field(
        name="📊 Calendar Visualization",
        value="• `/visualize_day <calendar> <date> [start_hour] [end_hour]` - Show day schedule",
        inline=False
    )

    # Permission Levels
    embed.add_field(
        name="🔐 Permission Levels",
        value="• **Owner** - Full access (create, edit, delete, manage users)\n• **Writer** - Can create and edit events\n• **Reader** - Can only view events",
        inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

async def link_user_calendar_command(interaction: discord.Interaction, calendar_id: str = ""):
    """Link user's personal Google Calendar"""
    if not calendar_id.strip():
        # Show instructions if no calendar_id provided
        embed = discord.Embed(
            title="❌ Missing Calendar ID",
            description="You need to provide your Google Calendar ID to link it.",
            color=discord.Color.red()
        )
        embed.add_field(
            name="📋 Instructions",
            value=CALENDAR_SHARING_INSTRUCTIONS,
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    bot = interaction.client

    try:
        # Validate calendar ID format (basic email-like format)
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', calendar_id):
            embed = discord.Embed(
                title="❌ Invalid Calendar ID",
                description="Calendar ID should look like an email address (e.g., `example@gmail.com`)",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Update user profile with calendar ID
        async with AsyncSessionLocal() as session:
            user_profile = await bot.user_manager.get_user(interaction.user.id)
            if not user_profile:
                user_profile = await bot.user_manager.ensure_user(interaction.user.id, calendar_email=calendar_id)
            else:
                user_profile.calendar_email = calendar_id
                await session.commit()

        embed = discord.Embed(
            title="✅ Calendar Linked Successfully",
            description=f"Your Google Calendar has been linked!\n\n**Calendar ID:** `{calendar_id}`",
            color=discord.Color.green()
        )
        embed.add_field(
            name="What's Next?",
            value="• Admins can now add you to shared calendars\n• Your free/busy status will be visible to authorized users\n• You'll receive event invitations in your personal calendar",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="❌ Error Linking Calendar",
            description=f"Failed to link calendar: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def create_shared_calendar_command(interaction: discord.Interaction, calendar_name: str, description: str = ""):
    """Create a shared calendar (Admin only)"""
    bot = interaction.client

    # Only server owner can create shared calendars
    if interaction.user.id != bot.owner_id:
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="Only the server owner can create shared calendars.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        # Check if calendar already exists
        existing_calendar = await bot.calendar_manager.get_calendar(calendar_name)
        if existing_calendar:
            embed = discord.Embed(
                title="❌ Calendar Already Exists",
                description=f"A calendar named '{calendar_name}' already exists.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Create calendar using CalendarManager
        calendar = await bot.calendar_manager.create_calendar(
            name=calendar_name,
            creator_id=interaction.user.id,
            description=description,
            google_calendar_id=f"{calendar_name.lower().replace(' ', '_')}@{interaction.guild.name.lower()}.calendar"
        )

        embed = discord.Embed(
            title="✅ Shared Calendar Created",
            description=f"Successfully created shared calendar: **{calendar_name}**",
            color=discord.Color.green()
        )
        embed.add_field(name="📅 Calendar ID", value=str(calendar.id), inline=True)
        embed.add_field(name="📝 Description", value=description or "No description", inline=True)
        embed.add_field(name="🔐 Permissions", value="Admin (Owner): Full access", inline=False)
        embed.add_field(
            name="📋 Next Steps",
            value="• Use `/add_calendar_users` to add users with permissions\n• Use `/list_calendar_users` to view current access\n• Use `/add_event` to create events",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="❌ Error Creating Calendar",
            description=f"Failed to create calendar: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def add_calendar_users_command(interaction: discord.Interaction, calendar_name: str, permission: str, roles: str = "", users: str = ""):
    """Add users to shared calendar with specific permissions (Admin only)"""
    bot = interaction.client

    # Only server owner can manage calendar permissions
    if interaction.user.id != bot.owner_id:
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="Only the server owner can manage calendar permissions.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Validate permission level
    valid_permissions = ["reader", "writer", "owner"]
    if permission.lower() not in valid_permissions:
        embed = discord.Embed(
            title="❌ Invalid Permission",
            description=f"Permission must be one of: {', '.join(valid_permissions)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if not roles.strip() and not users.strip():
        embed = discord.Embed(
            title="❌ Missing Users or Roles",
            description="You must specify either roles or users to add to the calendar.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        # Get the calendar
        calendar = await bot.calendar_manager.get_calendar(calendar_name)
        if not calendar:
            embed = discord.Embed(
                title="❌ Calendar Not Found",
                description=f"No calendar named '{calendar_name}' exists.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        guild = interaction.guild
        added_users = []

        # Process roles
        if roles.strip():
            role_names = [r.strip() for r in roles.split(",") if r.strip()]
            role_added_users = await bot.calendar_manager.add_users_by_roles(
                calendar.id, role_names, permission, interaction.user.id, guild.members
            )
            added_users.extend([guild.get_member(user_id) for user_id in role_added_users if guild.get_member(user_id)])

        # Process individual users
        if users.strip():
            for member in guild.members:
                if (f"@{member.display_name}" in users or
                    f"@{member.name}" in users or
                    str(member.id) in users or
                    member.mention in users):
                    success = await bot.calendar_manager.add_permission(
                        calendar.id, member.id, permission, interaction.user.id
                    )
                    if success and member not in added_users:
                        added_users.append(member)

        if not added_users:
            embed = discord.Embed(
                title="❌ No Users Found",
                description="No valid users or roles were found to add to the calendar.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Send invitation messages to users
        invitation_count = 0
        for user in added_users:
            try:
                # Send DM invitation
                embed_invite = discord.Embed(
                    title="📅 Calendar Invitation",
                    description=f"You've been added to the shared calendar: **{calendar_name}**",
                    color=discord.Color.blue()
                )
                embed_invite.add_field(name="🔐 Permission Level", value=permission.title(), inline=True)
                embed_invite.add_field(name="🏠 Server", value=guild.name, inline=True)
                embed_invite.add_field(
                    name="📋 What You Can Do",
                    value="• View calendar events\n• Receive event notifications\n• Use calendar commands" +
                          ("\n• Create and edit events" if permission in ["writer", "owner"] else "") +
                          ("\n• Manage calendar users" if permission == "owner" else ""),
                    inline=False
                )

                await user.send(embed=embed_invite)
                invitation_count += 1
            except:
                # If DM fails, continue with others
                pass

        embed = discord.Embed(
            title="✅ Users Added to Calendar",
            description=f"Successfully added {len(added_users)} users to calendar **{calendar_name}**",
            color=discord.Color.green()
        )
        embed.add_field(name="🔐 Permission Level", value=permission.title(), inline=True)
        embed.add_field(name="📧 Invitations Sent", value=f"{invitation_count}/{len(added_users)}", inline=True)

        user_list = ", ".join([user.display_name for user in added_users[:10]])
        if len(added_users) > 10:
            user_list += f" and {len(added_users) - 10} more..."
        embed.add_field(name="👥 Added Users", value=user_list, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="❌ Error Adding Users",
            description=f"Failed to add users to calendar: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def list_calendar_users_command(interaction: discord.Interaction, calendar_name: str):
    """List users with access to a shared calendar"""
    bot = interaction.client

    try:
        # Get the calendar
        calendar = await bot.calendar_manager.get_calendar(calendar_name)
        if not calendar:
            embed = discord.Embed(
                title="❌ Calendar Not Found",
                description=f"No calendar named '{calendar_name}' exists.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Get users with permissions
        permissions = await bot.calendar_manager.get_calendar_users(calendar.id)

        embed = discord.Embed(
            title=f"👥 Users with access to: {calendar_name}",
            color=discord.Color.blue()
        )

        # Group by permission level
        owners = []
        writers = []
        readers = []

        guild = interaction.guild
        for perm in permissions:
            member = guild.get_member(perm.user_id)
            if member:
                if perm.permission_level == "owner":
                    owners.append(member.display_name)
                elif perm.permission_level == "writer":
                    writers.append(member.display_name)
                else:
                    readers.append(member.display_name)

        if owners:
            embed.add_field(
                name="🔑 Owners (Full Access)",
                value="\n".join([f"• {name}" for name in owners]),
                inline=False
            )

        if writers:
            embed.add_field(
                name="✏️ Writers (Can Edit)",
                value="\n".join([f"• {name}" for name in writers]),
                inline=False
            )

        if readers:
            embed.add_field(
                name="👁️ Readers (View Only)",
                value="\n".join([f"• {name}" for name in readers]),
                inline=False
            )

        if not (owners or writers or readers):
            embed.add_field(
                name="❌ No Users",
                value="No users have been granted access to this calendar.",
                inline=False
            )

        embed.add_field(
            name="📋 Management Commands",
            value="• `/add_calendar_users` - Add users with permissions\n• `/remove_calendar_users` - Remove user access",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="❌ Error Listing Users",
            description=f"Failed to list calendar users: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def remove_calendar_users_command(interaction: discord.Interaction, calendar_name: str, roles: str = "", users: str = ""):
    """Remove users from shared calendar (Admin only)"""
    bot = interaction.client

    # Only server owner can manage calendar permissions
    if interaction.user.id != bot.owner_id:
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="Only the server owner can manage calendar permissions.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if not roles.strip() and not users.strip():
        embed = discord.Embed(
            title="❌ Missing Users or Roles",
            description="You must specify either roles or users to remove from the calendar.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        # Get the calendar
        calendar = await bot.calendar_manager.get_calendar(calendar_name)
        if not calendar:
            embed = discord.Embed(
                title="❌ Calendar Not Found",
                description=f"No calendar named '{calendar_name}' exists.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        guild = interaction.guild
        removed_users = []

        # Process roles
        if roles.strip():
            role_names = [r.strip() for r in roles.split(",") if r.strip()]
            role_removed_users = await bot.calendar_manager.remove_users_by_roles(
                calendar.id, role_names, guild.members
            )
            removed_users.extend([guild.get_member(user_id) for user_id in role_removed_users if guild.get_member(user_id)])

        # Process individual users
        if users.strip():
            for member in guild.members:
                if (f"@{member.display_name}" in users or
                    f"@{member.name}" in users or
                    str(member.id) in users or
                    member.mention in users):
                    success = await bot.calendar_manager.remove_permission(calendar.id, member.id)
                    if success and member not in removed_users:
                        removed_users.append(member)

        embed = discord.Embed(
            title="✅ Users Removed from Calendar",
            description=f"Successfully removed {len(removed_users)} users from calendar **{calendar_name}**",
            color=discord.Color.green()
        )

        if removed_users:
            user_list = ", ".join([user.display_name for user in removed_users[:10]])
            if len(removed_users) > 10:
                user_list += f" and {len(removed_users) - 10} more..."
            embed.add_field(name="👥 Removed Users", value=user_list, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="❌ Error Removing Users",
            description=f"Failed to remove users from calendar: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def add_event_command(interaction: discord.Interaction, calendar_name: str, event_name: str, start_time: str, end_time: str, location: str = "", description: str = "", roles: str = ""):
    """Add event to shared calendar"""
    bot = interaction.client

    try:
        # Get the calendar
        calendar = await bot.calendar_manager.get_calendar(calendar_name)
        if not calendar:
            embed = discord.Embed(
                title="❌ Calendar Not Found",
                description=f"No calendar named '{calendar_name}' exists.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if user has write permission
        if not await bot.calendar_manager.has_permission(calendar.id, interaction.user.id, "writer"):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need writer or owner permission to add events to this calendar.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Parse datetime strings
        try:
            start_dt = datetime.fromisoformat(start_time.replace('T', ' '))
            end_dt = datetime.fromisoformat(end_time.replace('T', ' '))
        except ValueError:
            embed = discord.Embed(
                title="❌ Invalid Date Format",
                description="Please use format: `YYYY-MM-DD HH:MM` or `YYYY-MM-DDTHH:MM`\n\nExample: `2024-01-15 14:30` or `2024-01-15T14:30`",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if end_dt <= start_dt:
            embed = discord.Embed(
                title="❌ Invalid Time Range",
                description="End time must be after start time.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Create event
        event = await bot.calendar_manager.create_event(
            calendar_id=calendar.id,
            title=event_name,
            start_time=start_dt,
            end_time=end_dt,
            created_by=interaction.user.id,
            description=description,
            location=location
        )

        embed = discord.Embed(
            title="✅ Event Created",
            description=f"Successfully created event: **{event_name}**",
            color=discord.Color.green()
        )
        embed.add_field(name="📅 Calendar", value=calendar_name, inline=True)
        embed.add_field(name="🆔 Event ID", value=str(event.id), inline=True)
        embed.add_field(name="🕐 Start", value=start_dt.strftime("%Y-%m-%d %H:%M"), inline=True)
        embed.add_field(name="🕐 End", value=end_dt.strftime("%Y-%m-%d %H:%M"), inline=True)

        if location:
            embed.add_field(name="📍 Location", value=location, inline=True)
        if description:
            embed.add_field(name="📝 Description", value=description, inline=False)

        # Add attendees by roles if specified
        if roles.strip():
            guild = interaction.guild
            role_names = [r.strip() for r in roles.split(",") if r.strip()]
            attendee_count = 0
            personal_calendar_syncs = 0

            for role_name in role_names:
                discord_role = discord.utils.get(guild.roles, name=role_name)
                if discord_role:
                    for member in discord_role.members:
                        success = await bot.calendar_manager.add_event_attendee(
                            event.id, member.id, role_name
                        )
                        if success:
                            attendee_count += 1

            # Check how many users have the event synced to personal calendars
            sync_results = await bot.calendar_manager.sync_event_to_personal_calendars(event.id)
            personal_calendar_syncs = sum(1 for synced in sync_results.values() if synced)

            embed.add_field(name="👥 Attendees Added", value=f"{attendee_count} users from roles: {roles}", inline=False)

            if personal_calendar_syncs > 0:
                embed.add_field(
                    name="📅 Personal Calendar Sync",
                    value=f"✅ {personal_calendar_syncs}/{attendee_count} users have the event synced to their personal calendars",
                    inline=False
                )
            elif attendee_count > 0:
                embed.add_field(
                    name="📅 Personal Calendar Sync",
                    value="⚠️ Users need to link their Google calendars with `/link_user_calendar` to receive events",
                    inline=False
                )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="❌ Error Creating Event",
            description=f"Failed to create event: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def list_events_command(interaction: discord.Interaction, calendar_name: str, days_ahead: int = 7):
    """List upcoming events in a calendar"""
    bot = interaction.client

    try:
        # Get the calendar
        calendar = await bot.calendar_manager.get_calendar(calendar_name)
        if not calendar:
            embed = discord.Embed(
                title="❌ Calendar Not Found",
                description=f"No calendar named '{calendar_name}' exists.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if user has read permission
        if not await bot.calendar_manager.has_permission(calendar.id, interaction.user.id, "reader"):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to view events in this calendar.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        now = datetime.now()
        end_date = now + timedelta(days=days_ahead)

        events = await bot.calendar_manager.get_calendar_events(
            calendar.id, start_date=now, end_date=end_date
        )

        embed = discord.Embed(
            title=f"📅 Upcoming Events: {calendar_name}",
            description=f"Events from {now.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            color=discord.Color.blue()
        )

        if events:
            for i, event in enumerate(events[:10], 1):
                event_info = f"🕐 {event.start_time.strftime('%Y-%m-%d %H:%M')} - {event.end_time.strftime('%H:%M')}"
                if event.location:
                    event_info += f"\n📍 {event.location}"
                if event.description:
                    event_info += f"\n📝 {event.description[:100]}{'...' if len(event.description) > 100 else ''}"
                event_info += f"\n🆔 ID: {event.id}"
                embed.add_field(name=f"{i}. {event.title}", value=event_info, inline=False)
        else:
            embed.add_field(name="❌ No Events", value="No events found in the specified time range.", inline=False)

        embed.add_field(
            name="📋 Commands",
            value="• `/add_event` - Create new event\n• `/update_event` - Modify event\n• `/delete_event` - Remove event\n• `/visualize_day` - Day view",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="❌ Error Listing Events",
            description=f"Failed to list events: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def update_event_command(interaction: discord.Interaction, calendar_name: str, event_id: str, event_name: str = "", start_time: str = "", end_time: str = "", location: str = "", description: str = ""):
    """Update an existing event"""
    bot = interaction.client

    try:
        event_id_int = int(event_id)
    except ValueError:
        embed = discord.Embed(
            title="❌ Invalid Event ID",
            description="Event ID must be a number.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if not any([event_name, start_time, end_time, location, description]):
        embed = discord.Embed(
            title="❌ No Changes Specified",
            description="You must specify at least one field to update.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        # Get the event
        event = await bot.calendar_manager.get_event(event_id_int)
        if not event:
            embed = discord.Embed(
                title="❌ Event Not Found",
                description=f"No event found with ID: {event_id}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if user has write permission
        if not await bot.calendar_manager.has_permission(event.calendar_id, interaction.user.id, "writer"):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need writer or owner permission to update events in this calendar.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Prepare update data
        update_data = {}
        if event_name:
            update_data['title'] = event_name
        if start_time:
            try:
                update_data['start_time'] = datetime.fromisoformat(start_time.replace('T', ' '))
            except ValueError:
                embed = discord.Embed(
                    title="❌ Invalid Start Time Format",
                    description="Please use format: `YYYY-MM-DD HH:MM`",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        if end_time:
            try:
                update_data['end_time'] = datetime.fromisoformat(end_time.replace('T', ' '))
            except ValueError:
                embed = discord.Embed(
                    title="❌ Invalid End Time Format",
                    description="Please use format: `YYYY-MM-DD HH:MM`",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        if location:
            update_data['location'] = location
        if description:
            update_data['description'] = description

        # Update the event
        success = await bot.calendar_manager.update_event(event_id_int, **update_data)

        if success:
            embed = discord.Embed(
                title="✅ Event Updated",
                description=f"Successfully updated event: **{event.title}**",
                color=discord.Color.green()
            )
            embed.add_field(name="📅 Calendar", value=calendar_name, inline=True)
            embed.add_field(name="🆔 Event ID", value=event_id, inline=True)

            changes = []
            for field, value in update_data.items():
                if field == 'start_time' or field == 'end_time':
                    changes.append(f"{field.replace('_', ' ').title()}: {value.strftime('%Y-%m-%d %H:%M')}")
                else:
                    changes.append(f"{field.replace('_', ' ').title()}: {value}")

            embed.add_field(name="🔄 Changes Made", value="\n".join(changes), inline=False)
        else:
            embed = discord.Embed(
                title="❌ Update Failed",
                description="Failed to update the event.",
                color=discord.Color.red()
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="❌ Error Updating Event",
            description=f"Failed to update event: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def delete_event_command(interaction: discord.Interaction, calendar_name: str, event_id: str):
    """Delete an event from the calendar"""
    bot = interaction.client

    try:
        event_id_int = int(event_id)
    except ValueError:
        embed = discord.Embed(
            title="❌ Invalid Event ID",
            description="Event ID must be a number.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        # Get the event
        event = await bot.calendar_manager.get_event(event_id_int)
        if not event:
            embed = discord.Embed(
                title="❌ Event Not Found",
                description=f"No event found with ID: {event_id}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if user has write permission
        if not await bot.calendar_manager.has_permission(event.calendar_id, interaction.user.id, "writer"):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need writer or owner permission to delete events from this calendar.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Delete the event
        success = await bot.calendar_manager.delete_event(event_id_int)

        if success:
            embed = discord.Embed(
                title="✅ Event Deleted",
                description=f"Successfully deleted event: **{event.title}**",
                color=discord.Color.green()
            )
            embed.add_field(name="📅 Calendar", value=calendar_name, inline=True)
            embed.add_field(name="🆔 Event ID", value=event_id, inline=True)
            embed.add_field(name="ℹ️ Note", value="Event has been removed from all associated personal calendars", inline=False)
        else:
            embed = discord.Embed(
                title="❌ Deletion Failed",
                description="Failed to delete the event.",
                color=discord.Color.red()
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="❌ Error Deleting Event",
            description=f"Failed to delete event: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def visualize_day_command(interaction: discord.Interaction, calendar_name: str, date: str, start_hour: int = 8, end_hour: int = 18):
    """Visualize a specific day with events in a nice format"""
    bot = interaction.client

    try:
        # Get the calendar
        calendar = await bot.calendar_manager.get_calendar(calendar_name)
        if not calendar:
            embed = discord.Embed(
                title="❌ Calendar Not Found",
                description=f"No calendar named '{calendar_name}' exists.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if user has read permission
        if not await bot.calendar_manager.has_permission(calendar.id, interaction.user.id, "reader"):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to view events in this calendar.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Parse date
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            embed = discord.Embed(
                title="❌ Invalid Date Format",
                description="Please use format: `YYYY-MM-DD`\n\nExample: `2024-01-15`",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Validate hours
        if start_hour < 0 or start_hour > 23 or end_hour < 0 or end_hour > 23 or start_hour >= end_hour:
            embed = discord.Embed(
                title="❌ Invalid Hours",
                description="Hours must be between 0-23 and start_hour must be less than end_hour.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Get events for the day
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = datetime.combine(target_date, datetime.max.time())

        events = await bot.calendar_manager.get_calendar_events(
            calendar.id, start_date=day_start, end_date=day_end
        )

        # Create day visualization
        embed = discord.Embed(
            title=f"📅 {calendar_name} - {target_date.strftime('%A, %B %d, %Y')}",
            color=discord.Color.blue()
        )

        # Create hourly schedule
        schedule_text = ""
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
                    schedule_text += f"**{hour_str}** 📍 **{event.title}** ({event.start_time.strftime('%H:%M')}-{event.end_time.strftime('%H:%M')})\n"
                    if event.location:
                        schedule_text += f"        📍 {event.location}\n"
            else:
                schedule_text += f"{hour_str} ⬜ *Free*\n"

        # Split into chunks if too long
        if len(schedule_text) > 1024:
            # Split the schedule into multiple fields
            chunks = []
            current_chunk = ""
            lines = schedule_text.split('\n')

            for line in lines:
                if len(current_chunk) + len(line) > 1020:
                    chunks.append(current_chunk)
                    current_chunk = line + '\n'
                else:
                    current_chunk += line + '\n'

            if current_chunk:
                chunks.append(current_chunk)

            for i, chunk in enumerate(chunks):
                field_name = "📅 Schedule" if i == 0 else f"📅 Schedule (cont. {i+1})"
                embed.add_field(name=field_name, value=chunk, inline=False)
        else:
            embed.add_field(name="📅 Schedule", value=schedule_text, inline=False)

        # Add summary
        total_events = len(events)
        busy_hours = len([e for e in events])
        embed.add_field(name="📊 Summary", value=f"**{total_events}** events scheduled\n**{busy_hours}** busy periods", inline=True)
        embed.add_field(name="🕐 Time Range", value=f"{start_hour:02d}:00 - {end_hour:02d}:00", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="❌ Error Visualizing Day",
            description=f"Failed to visualize day: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
