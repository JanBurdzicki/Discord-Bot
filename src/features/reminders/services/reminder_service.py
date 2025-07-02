"""
Core reminder service that handles all reminder-related operations.
Provides template management, scheduling, and notification functionality.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.database.models import Reminder, ReminderTemplate, ReminderLog
from src.database.session import AsyncSessionLocal
from src.core.builders import EmbedBuilder

class ReminderPriority(Enum):
    """Priority levels for reminders"""
    INFORMATIONAL = "informational"
    URGENT = "urgent"
    VERY_URGENT = "very_urgent"
    CRITICAL = "critical"

class TriggerType(Enum):
    """Types of reminder triggers"""
    TIME_BEFORE = "time_before"
    INTERVAL = "interval"
    SPECIFIC_TIME = "specific_time"

class ReminderService:
    """
    Core service for managing reminders and templates.
    Handles scheduling, notifications, and template management.
    """

    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self._started = False

        # Priority configurations
        self.priority_configs = {
            ReminderPriority.INFORMATIONAL: {
                'color': 0x3498db,  # Blue
                'emoji': '💙',
                'urgent_indicator': ''
            },
            ReminderPriority.URGENT: {
                'color': 0xf39c12,  # Orange
                'emoji': '⚠️',
                'urgent_indicator': '**[URGENT]** '
            },
            ReminderPriority.VERY_URGENT: {
                'color': 0xe74c3c,  # Red
                'emoji': '🚨',
                'urgent_indicator': '**[VERY URGENT]** '
            },
            ReminderPriority.CRITICAL: {
                'color': 0x8e44ad,  # Purple
                'emoji': '🔥',
                'urgent_indicator': '**[CRITICAL]** '
            }
        }

    async def init(self) -> None:
        """Initialize the reminder service"""
        if not self._started:
            self.scheduler.start()
            self._started = True
            # Schedule the reminder checker
            self.scheduler.add_job(
                self._check_pending_reminders,
                'interval',
                minutes=1,
                id='reminder_checker'
            )
            await self._reschedule_existing_reminders()

    async def cleanup(self) -> None:
        """Cleanup service resources"""
        if self._started:
            self.scheduler.shutdown()
            self._started = False

    # ========== Template Management ==========

    async def create_template(
        self,
        name: str,
        message_template: str,
        priority: ReminderPriority,
        creator_id: int,
        description: Optional[str] = None,
        ping_roles: Optional[List[int]] = None,
        ping_users: Optional[List[int]] = None,
        embed_color: Optional[str] = None
    ) -> ReminderTemplate:
        """Create a new reminder template"""
        async with AsyncSessionLocal() as session:
            template = ReminderTemplate(
                name=name,
                description=description or f"Template created by user {creator_id}",
                message_template=message_template,
                priority=priority.value,
                created_by=creator_id,
                ping_roles=ping_roles or [],
                ping_users=ping_users or [],
                embed_color=embed_color or "#3498db"
            )
            session.add(template)
            await session.commit()
            return template

    async def get_template(self, name: str) -> Optional[ReminderTemplate]:
        """Get a template by name"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ReminderTemplate).where(ReminderTemplate.name == name)
            )
            return result.scalar_one_or_none()

    async def list_templates(self, creator_id: Optional[int] = None) -> List[ReminderTemplate]:
        """List available templates"""
        async with AsyncSessionLocal() as session:
            query = select(ReminderTemplate)
            if creator_id is not None:
                query = query.where(ReminderTemplate.created_by == creator_id)
            result = await session.execute(query)
            return result.scalars().all()

    # ========== Reminder Management ==========

    async def create_reminder(
        self,
        template_name: str,
        channel_id: int,
        creator_id: int,
        trigger_type: TriggerType,
        target_id: Optional[str] = None,
        custom_data: Optional[Dict[str, Any]] = None,
        **trigger_kwargs
    ) -> Reminder:
        """Create a new reminder"""
        async with AsyncSessionLocal() as session:
            # Get template
            template = await self.get_template(template_name)
            if not template:
                raise ValueError(f"Template '{template_name}' not found")

            # Create reminder
            reminder = Reminder(
                reminder_id=str(uuid.uuid4()),
                template_id=template.id,
                channel_id=channel_id,
                creator_id=creator_id,
                target_id=target_id,
                trigger_type=trigger_type.value,
                custom_data=custom_data or {},
                is_active=True,
                **trigger_kwargs
            )

            # Set next trigger time
            await self._calculate_next_trigger(reminder)

            session.add(reminder)
            await session.commit()

            # Schedule the reminder
            if reminder.next_trigger:
                await self._schedule_reminder(reminder)

            return reminder

    async def list_reminders(
        self,
        creator_id: Optional[int] = None,
        is_active: Optional[bool] = None
    ) -> List[Reminder]:
        """List reminders with optional filters"""
        async with AsyncSessionLocal() as session:
            query = select(Reminder)
            if creator_id is not None:
                query = query.where(Reminder.creator_id == creator_id)
            if is_active is not None:
                query = query.where(Reminder.is_active == is_active)
            result = await session.execute(query)
            return result.scalars().all()

    async def cancel_reminder(self, reminder_id: str) -> bool:
        """Cancel an active reminder"""
        async with AsyncSessionLocal() as session:
            reminder = await session.get(Reminder, reminder_id)
            if not reminder:
                return False

            reminder.is_active = False
            await session.commit()

            # Remove from scheduler
            job_id = f"reminder_{reminder_id}"
            self.scheduler.remove_job(job_id)

            return True

    # ========== Reminder Execution ==========

    async def _check_pending_reminders(self):
        """Check and execute pending reminders"""
        async with AsyncSessionLocal() as session:
            now = datetime.utcnow()
            query = select(Reminder).where(
                Reminder.is_active == True,
                Reminder.next_trigger <= now
            )
            result = await session.execute(query)
            reminders = result.scalars().all()

            for reminder in reminders:
                await self._execute_reminder(reminder.reminder_id)

    async def _execute_reminder(self, reminder_id: str):
        """Execute a reminder and send notification"""
        async with AsyncSessionLocal() as session:
            reminder = await session.get(Reminder, reminder_id)
            if not reminder or not reminder.is_active:
                return

            try:
                # Get template
                template = await session.get(ReminderTemplate, reminder.template_id)
                if not template:
                    await self._log_reminder(reminder_id, 'failed', 'Template not found')
                    return

                # Build message content
                message_content = await self._build_message_content(reminder, template)

                # Get channel
                channel = self.bot.get_channel(reminder.channel_id)
                if not channel:
                    await self._log_reminder(reminder_id, 'failed', 'Channel not found')
                    return

                # Create embed
                embed = await self._create_reminder_embed(reminder, template, message_content)

                # Send reminder
                await channel.send(embed=embed)

                # Update reminder status
                reminder.last_triggered = datetime.utcnow()
                reminder.occurrence_count += 1

                # Schedule next occurrence if recurring
                if reminder.is_recurring:
                    if not reminder.max_occurrences or reminder.occurrence_count < reminder.max_occurrences:
                        reminder.next_trigger = datetime.utcnow() + timedelta(minutes=reminder.interval_minutes)
                        await self._schedule_reminder(reminder)
                    else:
                        reminder.is_active = False
                else:
                    reminder.is_active = False

                await session.commit()
                await self._log_reminder(reminder_id, 'success')

            except Exception as e:
                await self._log_reminder(reminder_id, 'failed', str(e))
                raise

    # ========== Helper Methods ==========

    async def _calculate_next_trigger(self, reminder: Reminder):
        """Calculate the next trigger time for a reminder"""
        trigger_type = TriggerType(reminder.trigger_type)

        if trigger_type == TriggerType.SPECIFIC_TIME:
            reminder.next_trigger = reminder.trigger_time

        elif trigger_type == TriggerType.INTERVAL:
            reminder.next_trigger = datetime.utcnow() + timedelta(minutes=reminder.interval_minutes)
            reminder.is_recurring = True

        elif trigger_type == TriggerType.TIME_BEFORE:
            if reminder.target_type == "poll" and reminder.target_id:
                async with AsyncSessionLocal() as session:
                    poll = await session.get(Poll, reminder.target_id)
                    if poll and poll.expires_at:
                        reminder.next_trigger = poll.expires_at - timedelta(minutes=reminder.time_before_minutes)

    async def _schedule_reminder(self, reminder: Reminder):
        """Schedule a reminder with the scheduler"""
        if not reminder.next_trigger or reminder.next_trigger <= datetime.utcnow():
            return

        job_id = f"reminder_{reminder.reminder_id}"
        self.scheduler.add_job(
            self._execute_reminder,
            'date',
            run_date=reminder.next_trigger,
            args=[reminder.reminder_id],
            id=job_id,
            replace_existing=True
        )

    async def _reschedule_existing_reminders(self):
        """Reschedule all active reminders on startup"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Reminder).where(
                    Reminder.is_active == True,
                    Reminder.next_trigger > datetime.utcnow()
                )
            )
            reminders = result.scalars().all()

            for reminder in reminders:
                await self._schedule_reminder(reminder)

    async def _build_message_content(self, reminder: Reminder, template: ReminderTemplate) -> Dict[str, Any]:
        """Build the message content with template variables"""
        content = {
            'text': template.message_template
        }

        # Replace variables based on reminder type
        if reminder.target_type == "poll" and reminder.target_id:
            async with AsyncSessionLocal() as session:
                poll = await session.get(Poll, reminder.target_id)
                if poll:
                    content['text'] = content['text'].format(
                        poll_id=poll.poll_id,
                        poll_title=poll.title,
                        time_left=self._format_time_left(poll.expires_at)
                    )

        # Replace custom variables
        if reminder.custom_data:
            content['text'] = content['text'].format(**reminder.custom_data)

        return content

    async def _create_reminder_embed(self, reminder: Reminder, template: ReminderTemplate, message_content: Dict[str, Any]) -> discord.Embed:
        """Create a Discord embed for the reminder"""
        priority = ReminderPriority(template.priority)
        config = self.priority_configs[priority]

        embed = EmbedBuilder()\
            .set_title(f"{config['emoji']} {template.name}")\
            .set_description(f"{config['urgent_indicator']}{message_content['text']}")\
            .set_color(template.embed_color or config['color'])\
            .set_timestamp(datetime.utcnow())

        # Add ping information
        ping_text = []
        if template.ping_roles:
            ping_text.extend([f"<@&{role_id}>" for role_id in template.ping_roles])
        if template.ping_users:
            ping_text.extend([f"<@{user_id}>" for user_id in template.ping_users])

        if ping_text:
            embed.add_field("📢 Notifications", " ".join(ping_text), inline=False)

        embed.set_footer(f"Priority: {priority.value.title()} • Reminder ID: {reminder.reminder_id[:8]}")

        return embed.build()

    async def _log_reminder(self, reminder_id: str, status: str, error: Optional[str] = None):
        """Log reminder execution status"""
        async with AsyncSessionLocal() as session:
            log = ReminderLog(
                reminder_id=reminder_id,
                status=status,
                error_message=error,
                timestamp=datetime.utcnow()
            )
            session.add(log)
            await session.commit()

    def _format_time_left(self, target_time: datetime) -> str:
        """Format time left until target time"""
        if not target_time:
            return "unknown"

        delta = target_time - datetime.utcnow()

        if delta.total_seconds() < 0:
            return "expired"

        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60

        if delta.days > 0:
            return f"{delta.days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"