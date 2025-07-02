from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta
import re
import logging
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import discord

from src.database.session import AsyncSessionLocal
from src.database.models import SharedCalendar, CalendarPermission, CalendarEvent, EventAttendee, UserProfile
from src.core.builders import EmbedBuilder

logger = logging.getLogger(__name__)

class CalendarService:
    """Unified calendar service handling both database operations and Google Calendar integration"""

    # Calendar sharing instructions constant
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

    def __init__(self, bot):
        self.bot = bot

    # Validation methods
    def validate_calendar_id(self, calendar_id: str) -> bool:
        """Validate calendar ID format"""
        return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', calendar_id))

    def validate_permission_level(self, permission: str) -> bool:
        """Validate permission level"""
        return permission.lower() in ["reader", "writer", "owner"]

    def validate_date_format(self, date_str: str) -> Optional[datetime]:
        """Validate and parse date format"""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None

    def validate_datetime_format(self, datetime_str: str) -> Optional[datetime]:
        """Validate and parse datetime format"""
        formats = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%dT%H:%M:%S"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue
        return None

    # Calendar management methods
    async def create_calendar(self, name: str, creator_id: int, description: str = "", google_calendar_id: str = "") -> SharedCalendar:
        """Create a new shared calendar"""
        async with AsyncSessionLocal() as session:
            calendar = SharedCalendar(
                name=name,
                description=description,
                google_calendar_id=google_calendar_id,
                created_by=creator_id
            )
            session.add(calendar)
            await session.commit()
            await session.refresh(calendar)

            # Add creator as owner
            await self.add_permission(calendar.id, creator_id, "owner", creator_id)
            return calendar

    async def get_calendar(self, calendar_name: str) -> Optional[SharedCalendar]:
        """Get calendar by name"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SharedCalendar)
                .options(selectinload(SharedCalendar.permissions))
                .where(SharedCalendar.name == calendar_name)
            )
            return result.scalar_one_or_none()

    async def get_calendar_by_id(self, calendar_id: int) -> Optional[SharedCalendar]:
        """Get calendar by ID"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SharedCalendar)
                .options(selectinload(SharedCalendar.permissions))
                .where(SharedCalendar.id == calendar_id)
            )
            return result.scalar_one_or_none()

    async def delete_calendar(self, calendar_name: str, user_id: int) -> bool:
        """Delete a calendar (only owner can delete)"""
        calendar = await self.get_calendar(calendar_name)
        if not calendar or not await self.has_permission(calendar.id, user_id, "owner"):
            return False

        async with AsyncSessionLocal() as session:
            await session.delete(calendar)
            await session.commit()
            return True

    # Permission management methods
    async def add_permission(self, calendar_id: int, user_id: int, permission_level: str, granted_by: int) -> bool:
        """Add or update permission for a user"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(CalendarPermission)
                .where(CalendarPermission.calendar_id == calendar_id)
                .where(CalendarPermission.user_id == user_id)
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.permission_level = permission_level
                existing.granted_by = granted_by
                existing.granted_at = datetime.utcnow()
            else:
                permission = CalendarPermission(
                    calendar_id=calendar_id,
                    user_id=user_id,
                    permission_level=permission_level,
                    granted_by=granted_by
                )
                session.add(permission)

            await session.commit()
            return True

    async def remove_permission(self, calendar_id: int, user_id: int) -> bool:
        """Remove permission for a user"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(CalendarPermission)
                .where(CalendarPermission.calendar_id == calendar_id)
                .where(CalendarPermission.user_id == user_id)
            )
            permission = result.scalar_one_or_none()

            if permission:
                await session.delete(permission)
                await session.commit()
                return True
            return False

    async def has_permission(self, calendar_id: int, user_id: int, required_level: str = "reader") -> bool:
        """Check if user has required permission level"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(CalendarPermission)
                .where(CalendarPermission.calendar_id == calendar_id)
                .where(CalendarPermission.user_id == user_id)
            )
            permission = result.scalar_one_or_none()

            if not permission:
                return False

            # Permission hierarchy: owner > writer > reader
            levels = {"reader": 1, "writer": 2, "owner": 3}
            user_level = levels.get(permission.permission_level, 0)
            required_level_value = levels.get(required_level, 0)

            return user_level >= required_level_value

    async def get_calendar_users(self, calendar_id: int) -> List[CalendarPermission]:
        """Get all users with permissions for a calendar"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(CalendarPermission)
                .where(CalendarPermission.calendar_id == calendar_id)
                .order_by(CalendarPermission.permission_level.desc())
            )
            return result.scalars().all()

    async def get_user_calendars(self, user_id: int) -> List[Tuple[SharedCalendar, str]]:
        """Get all calendars a user has access to with their permission level"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SharedCalendar, CalendarPermission.permission_level)
                .join(CalendarPermission)
                .where(CalendarPermission.user_id == user_id)
                .order_by(SharedCalendar.name)
            )
            return result.all()

    async def add_users_by_roles(self, calendar_id: int, role_names: List[str], permission_level: str,
                                granted_by: int, guild_members) -> List[int]:
        """Add users to calendar by their Discord roles"""
        added_users = []

        for member in guild_members:
            member_roles = [r.name.lower() for r in member.roles]
            if any(role_name.lower() in member_roles for role_name in role_names):
                success = await self.add_permission(calendar_id, member.id, permission_level, granted_by)
                if success:
                    added_users.append(member.id)

        return added_users

    async def remove_users_by_roles(self, calendar_id: int, role_names: List[str], guild_members) -> List[int]:
        """Remove users from calendar by their Discord roles"""
        removed_users = []

        for member in guild_members:
            member_roles = [r.name.lower() for r in member.roles]
            if any(role_name.lower() in member_roles for role_name in role_names):
                success = await self.remove_permission(calendar_id, member.id)
                if success:
                    removed_users.append(member.id)

        return removed_users

    # Event management methods
    async def create_event(self, calendar_id: int, title: str, start_time: datetime, end_time: datetime,
                          created_by: int, description: str = "", location: str = "",
                          google_event_id: str = "") -> CalendarEvent:
        """Create a new event in a calendar"""
        async with AsyncSessionLocal() as session:
            event = CalendarEvent(
                calendar_id=calendar_id,
                title=title,
                description=description,
                location=location,
                start_time=start_time,
                end_time=end_time,
                created_by=created_by,
                google_event_id=google_event_id
            )
            session.add(event)
            await session.commit()
            await session.refresh(event)
            return event

    async def get_event(self, event_id: int) -> Optional[CalendarEvent]:
        """Get event by ID"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(CalendarEvent)
                .options(selectinload(CalendarEvent.attendees))
                .where(CalendarEvent.id == event_id)
            )
            return result.scalar_one_or_none()

    async def get_calendar_events(self, calendar_id: int, start_date: datetime = None,
                                 end_date: datetime = None) -> List[CalendarEvent]:
        """Get events for a calendar within date range"""
        async with AsyncSessionLocal() as session:
            query = select(CalendarEvent).where(CalendarEvent.calendar_id == calendar_id)

            if start_date:
                query = query.where(CalendarEvent.end_time >= start_date)
            if end_date:
                query = query.where(CalendarEvent.start_time <= end_date)

            query = query.order_by(CalendarEvent.start_time)
            result = await session.execute(query)
            return result.scalars().all()

    async def update_event(self, event_id: int, **kwargs) -> bool:
        """Update an event"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(CalendarEvent).where(CalendarEvent.id == event_id)
            )
            event = result.scalar_one_or_none()

            if not event:
                return False

            # Update allowed fields
            for key, value in kwargs.items():
                if hasattr(event, key) and value is not None:
                    setattr(event, key, value)

            await session.commit()
            return True

    async def delete_event(self, event_id: int) -> bool:
        """Delete an event"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(CalendarEvent).where(CalendarEvent.id == event_id)
            )
            event = result.scalar_one_or_none()

            if event:
                await session.delete(event)
                await session.commit()
                return True
            return False

    # User calendar linking
    async def link_user_calendar(self, user_id: int, calendar_id: str) -> bool:
        """Link user's personal Google Calendar"""
        if not self.validate_calendar_id(calendar_id):
            return False

        async with AsyncSessionLocal() as session:
            # Get or create user profile
            user_profile = await self.bot.user_manager.get_user(user_id)
            if not user_profile:
                user_profile = await self.bot.user_manager.ensure_user(user_id, calendar_email=calendar_id)
            else:
                user_profile.calendar_email = calendar_id
                await session.commit()
            return True

    # Embed builders for consistent responses
    def build_help_embed(self) -> EmbedBuilder:
        """Build help embed with calendar instructions"""
        return (EmbedBuilder()
                .set_title("📅 Calendar System Help")
                .set_description(self.CALENDAR_SHARING_INSTRUCTIONS)
                .set_color("blue")
                .add_field("👤 Personal Calendar Commands",
                          "• `/link_user_calendar <calendar_id>` - Link your Google Calendar\n• `/calendar_help` - Show this help",
                          inline=False)
                .add_field("🔧 Admin Calendar Management",
                          "• `/create_shared_calendar <name> [description]` - Create shared calendar\n• `/add_calendar_users <calendar> <permission> [roles] [users]` - Add users\n• `/list_calendar_users <calendar>` - List calendar access\n• `/remove_calendar_users <calendar> [roles] [users]` - Remove users",
                          inline=False)
                .add_field("📅 Event Management",
                          "• `/add_event <calendar> <name> <start> <end> [location] [description] [roles]` - Create event\n• `/list_events <calendar> [days_ahead]` - List upcoming events\n• `/update_event <calendar> <event_id> [name] [start] [end] [location] [description]` - Update event\n• `/delete_event <calendar> <event_id>` - Delete event",
                          inline=False)
                .add_field("📊 Calendar Visualization",
                          "• `/visualize_day <calendar> <date> [start_hour] [end_hour]` - Show day schedule",
                          inline=False)
                .add_field("🔐 Permission Levels",
                          "• **Owner** - Full access (create, edit, delete, manage users)\n• **Writer** - Can create and edit events\n• **Reader** - Can only view events",
                          inline=False))

    def build_calendar_success_embed(self, calendar: SharedCalendar) -> EmbedBuilder:
        """Build successful calendar creation embed"""
        return (EmbedBuilder()
                .set_title("✅ Shared Calendar Created")
                .set_description(f"Successfully created shared calendar: **{calendar.name}**")
                .set_color("green")
                .add_field("📅 Calendar ID", str(calendar.id), inline=True)
                .add_field("📝 Description", calendar.description or "No description", inline=True)
                .add_field("🔐 Permissions", "Admin (Owner): Full access", inline=False)
                .add_field("📋 Next Steps",
                          "• Use `/add_calendar_users` to add users with permissions\n• Use `/list_calendar_users` to view current access\n• Use `/add_event` to create events",
                          inline=False))

    def build_users_list_embed(self, calendar_name: str, permissions: List[CalendarPermission], guild) -> EmbedBuilder:
        """Build embed showing calendar users"""
        embed = (EmbedBuilder()
                .set_title(f"👥 Users with access to: {calendar_name}")
                .set_color("blue"))

        # Group by permission level
        owners, writers, readers = [], [], []

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
            embed.add_field("🔑 Owners (Full Access)", "\n".join([f"• {name}" for name in owners]), inline=False)
        if writers:
            embed.add_field("✏️ Writers (Can Edit)", "\n".join([f"• {name}" for name in writers]), inline=False)
        if readers:
            embed.add_field("👁️ Readers (View Only)", "\n".join([f"• {name}" for name in readers]), inline=False)

        if not (owners or writers or readers):
            embed.add_field("❌ No Users", "No users have been granted access to this calendar.", inline=False)

        embed.add_field("📋 Management Commands",
                       "• `/add_calendar_users` - Add users with permissions\n• `/remove_calendar_users` - Remove user access",
                       inline=False)

        return embed