from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from db.session import AsyncSessionLocal
from db.models import SharedCalendar, CalendarPermission, CalendarEvent, EventAttendee, UserProfile
from datetime import datetime
from typing import List, Optional, Dict, Tuple
import discord

class CalendarManager:
    """Manages shared calendars, permissions, and events"""

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
        async with AsyncSessionLocal() as session:
            calendar = await self.get_calendar(calendar_name)
            if not calendar:
                return False

            # Check if user is owner
            if not await self.has_permission(calendar.id, user_id, "owner"):
                return False

            await session.delete(calendar)
            await session.commit()
            return True

    async def add_permission(self, calendar_id: int, user_id: int, permission_level: str, granted_by: int) -> bool:
        """Add or update permission for a user"""
        async with AsyncSessionLocal() as session:
            # Check if permission already exists
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

            # Update fields that were provided
            for field, value in kwargs.items():
                if hasattr(event, field) and value is not None:
                    setattr(event, field, value)

            event.updated_at = datetime.utcnow()
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

    async def add_event_attendee(self, event_id: int, user_id: int, role_name: str = "") -> bool:
        """Add attendee to an event and sync to their personal calendar"""
        async with AsyncSessionLocal() as session:
            # Check if already attending
            result = await session.execute(
                select(EventAttendee)
                .where(EventAttendee.event_id == event_id)
                .where(EventAttendee.user_id == user_id)
            )
            existing = result.scalar_one_or_none()

            if existing:
                return False  # Already attending

            # Get the event details
            event_result = await session.execute(
                select(CalendarEvent).where(CalendarEvent.id == event_id)
            )
            event = event_result.scalar_one_or_none()
            if not event:
                return False

            # Get user's calendar email
            user_result = await session.execute(
                select(UserProfile).where(UserProfile.discord_id == user_id)
            )
            user_profile = user_result.scalar_one_or_none()

            attendee = EventAttendee(
                event_id=event_id,
                user_id=user_id,
                role_name=role_name
            )
            session.add(attendee)

            # Try to sync to user's personal calendar
            personal_calendar_synced = False
            if user_profile and user_profile.calendar_email:
                try:
                    # Get user's token for Google Calendar access
                    from db.models import UserToken
                    token_result = await session.execute(
                        select(UserToken).where(UserToken.discord_id == user_id)
                    )
                    user_token = token_result.scalar_one_or_none()

                    if user_token:
                        from services.calendar_service import CalendarService
                        calendar_service = CalendarService(user_token.token_data)

                        # Add event to user's personal calendar
                        personal_calendar_synced = calendar_service.add_event_to_user_calendar(
                            user_profile.calendar_email,
                            f"[Shared] {event.title}",
                            event.start_time,
                            event.end_time,
                            f"Event from shared calendar. {event.description}",
                            event.location
                        )
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to sync event to user {user_id} personal calendar: {str(e)}")

            await session.commit()
            return True

    async def remove_event_attendee(self, event_id: int, user_id: int) -> bool:
        """Remove attendee from an event"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(EventAttendee)
                .where(EventAttendee.event_id == event_id)
                .where(EventAttendee.user_id == user_id)
            )
            attendee = result.scalar_one_or_none()

            if attendee:
                await session.delete(attendee)
                await session.commit()
                return True
            return False

    async def get_event_attendees(self, event_id: int) -> List[EventAttendee]:
        """Get all attendees for an event"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(EventAttendee)
                .where(EventAttendee.event_id == event_id)
                .order_by(EventAttendee.added_at)
            )
            return result.scalars().all()

    async def add_users_by_roles(self, calendar_id: int, role_names: List[str], permission_level: str,
                                granted_by: int, guild_members) -> List[int]:
        """Add users to calendar by their Discord roles"""
        added_users = []

        for member in guild_members:
            user_roles = [role.name for role in member.roles]
            if any(role_name in user_roles for role_name in role_names):
                success = await self.add_permission(calendar_id, member.id, permission_level, granted_by)
                if success:
                    added_users.append(member.id)

        return added_users

    async def remove_users_by_roles(self, calendar_id: int, role_names: List[str], guild_members) -> List[int]:
        """Remove users from calendar by their Discord roles"""
        removed_users = []

        for member in guild_members:
            user_roles = [role.name for role in member.roles]
            if any(role_name in user_roles for role_name in role_names):
                success = await self.remove_permission(calendar_id, member.id)
                if success:
                    removed_users.append(member.id)

        return removed_users

    async def sync_event_to_personal_calendars(self, event_id: int) -> Dict[int, bool]:
        """Sync an event to all attendees' personal calendars"""
        results = {}

        async with AsyncSessionLocal() as session:
            # Get event and all attendees
            event_result = await session.execute(
                select(CalendarEvent)
                .options(selectinload(CalendarEvent.attendees))
                .where(CalendarEvent.id == event_id)
            )
            event = event_result.scalar_one_or_none()

            if not event:
                return results

            for attendee in event.attendees:
                # Get user's calendar info
                user_result = await session.execute(
                    select(UserProfile).where(UserProfile.discord_id == attendee.user_id)
                )
                user_profile = user_result.scalar_one_or_none()

                if user_profile and user_profile.calendar_email:
                    try:
                        # Get user's token
                        from db.models import UserToken
                        token_result = await session.execute(
                            select(UserToken).where(UserToken.discord_id == attendee.user_id)
                        )
                        user_token = token_result.scalar_one_or_none()

                        if user_token:
                            from services.calendar_service import CalendarService
                            calendar_service = CalendarService(user_token.token_data)

                            # Sync to personal calendar
                            success = calendar_service.add_event_to_user_calendar(
                                user_profile.calendar_email,
                                f"[Shared] {event.title}",
                                event.start_time,
                                event.end_time,
                                f"Event from shared calendar. {event.description}",
                                event.location
                            )
                            results[attendee.user_id] = success
                        else:
                            results[attendee.user_id] = False
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Failed to sync event to user {attendee.user_id} personal calendar: {str(e)}")
                        results[attendee.user_id] = False
                else:
                    results[attendee.user_id] = False

        return results

    async def notify_user_calendar_access(self, user_id: int, calendar_name: str, permission_level: str, bot) -> bool:
        """Send notification to user about calendar access"""
        try:
            user = await bot.fetch_user(user_id)
            if user:
                embed = discord.Embed(
                    title="📅 Calendar Access Granted",
                    description=f"You've been granted access to the shared calendar: **{calendar_name}**",
                    color=discord.Color.green()
                )
                embed.add_field(name="🔐 Permission Level", value=permission_level.title(), inline=True)
                embed.add_field(name="📋 Available Commands", value="• `/list_events` - View events\n• `/add_event` - Create events (Writer+)\n• `/visualize_day` - Day view", inline=False)

                await user.send(embed=embed)
                return True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to notify user {user_id}: {str(e)}")
        return False