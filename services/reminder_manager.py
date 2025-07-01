import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.future import select
from sqlalchemy import delete

from db.session import AsyncSessionLocal
from db.models import Reminder, ReminderTemplate, ReminderLog, ReminderSubscription, Poll
from utils.stats_module import StatsModule

class ReminderPriority(Enum):
    INFORMATIONAL = "informational"
    URGENT = "urgent"
    VERY_URGENT = "very_urgent"
    CRITICAL = "critical"

class TriggerType(Enum):
    SPECIFIC_TIME = "specific_time"
    TIME_BEFORE = "time_before"
    INTERVAL = "interval"

class TargetType(Enum):
    POLL = "poll"
    EVENT = "event"
    CUSTOM = "custom"

class ReminderManager:
    def __init__(self, bot_client: discord.Client, stats_module: StatsModule):
        self.bot = bot_client
        self.stats_module = stats_module
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

    async def start(self):
        """Start the reminder scheduler"""
        if not self._started:
            self.scheduler.start()
            self._started = True
            # Schedule the reminder checker to run every minute
            self.scheduler.add_job(
                self._check_pending_reminders,
                'interval',
                minutes=1,
                id='reminder_checker'
            )
            await self._reschedule_existing_reminders()

    async def stop(self):
        """Stop the reminder scheduler"""
        if self._started:
            self.scheduler.shutdown()
            self._started = False

    # ========== Template Management ==========

    async def create_template(self, name: str, description: str, message_template: str,
                            priority: ReminderPriority, creator_id: int,
                            ping_roles: List[int] = None, ping_users: List[int] = None,
                            embed_color: str = None) -> ReminderTemplate:
        """Create a new reminder template"""
        async with AsyncSessionLocal() as session:
            # Convert hex color integer to hex string
            default_color = self.priority_configs[priority]['color']
            color_str = embed_color or f"#{default_color:06x}"

            template = ReminderTemplate(
                name=name,
                description=description,
                message_template=message_template,
                priority=priority.value,
                ping_roles=ping_roles or [],
                ping_users=ping_users or [],
                embed_color=color_str,
                created_by=creator_id
            )
            session.add(template)
            await session.commit()
            await session.refresh(template)
            return template

    async def get_template(self, template_name: str) -> Optional[ReminderTemplate]:
        """Get a template by name"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ReminderTemplate).where(ReminderTemplate.name == template_name)
            )
            return result.scalar_one_or_none()

    async def list_templates(self, creator_id: int = None) -> List[ReminderTemplate]:
        """List all templates, optionally filtered by creator"""
        async with AsyncSessionLocal() as session:
            query = select(ReminderTemplate)
            if creator_id:
                query = query.where(ReminderTemplate.created_by == creator_id)
            result = await session.execute(query)
            return result.scalars().all()

    # ========== Reminder Creation ==========

    async def create_poll_reminder(self, poll_id: str, template_name: str,
                                 trigger_type: TriggerType, channel_id: int,
                                 creator_id: int, **trigger_kwargs) -> Reminder:
        """Create a reminder for a poll"""
        return await self._create_reminder(
            template_name=template_name,
            target_type=TargetType.POLL,
            target_id=poll_id,
            channel_id=channel_id,
            trigger_type=trigger_type,
            creator_id=creator_id,
            **trigger_kwargs
        )

    async def create_event_reminder(self, event_id: str, template_name: str,
                                  trigger_type: TriggerType, channel_id: int,
                                  creator_id: int, **trigger_kwargs) -> Reminder:
        """Create a reminder for an event"""
        return await self._create_reminder(
            template_name=template_name,
            target_type=TargetType.EVENT,
            target_id=event_id,
            channel_id=channel_id,
            trigger_type=trigger_type,
            creator_id=creator_id,
            **trigger_kwargs
        )

    async def create_custom_reminder(self, template_name: str, channel_id: int,
                                   trigger_type: TriggerType, creator_id: int,
                                   custom_data: Dict[str, Any] = None,
                                   **trigger_kwargs) -> Reminder:
        """Create a custom reminder"""
        return await self._create_reminder(
            template_name=template_name,
            target_type=TargetType.CUSTOM,
            target_id=None,
            channel_id=channel_id,
            trigger_type=trigger_type,
            creator_id=creator_id,
            custom_data=custom_data or {},
            **trigger_kwargs
        )

    async def _create_reminder(self, template_name: str, target_type: TargetType,
                             channel_id: int, trigger_type: TriggerType,
                             creator_id: int, target_id: str = None,
                             custom_data: Dict[str, Any] = None,
                             **trigger_kwargs) -> Reminder:
        """Internal method to create a reminder"""

        # Get template
        template = await self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        async with AsyncSessionLocal() as session:
            reminder = Reminder(
                reminder_id=str(uuid.uuid4()),
                template_id=template.id,
                target_type=target_type.value,
                target_id=target_id,
                channel_id=channel_id,
                trigger_type=trigger_type.value,
                created_by=creator_id,
                custom_data=custom_data or {}
            )

            # Set trigger-specific fields
            if trigger_type == TriggerType.SPECIFIC_TIME:
                reminder.trigger_time = trigger_kwargs.get('trigger_time')
                reminder.next_trigger = reminder.trigger_time
            elif trigger_type == TriggerType.TIME_BEFORE:
                reminder.time_before_minutes = trigger_kwargs.get('minutes_before')
                # Calculate next trigger based on target
                await self._calculate_time_before_trigger(reminder)
            elif trigger_type == TriggerType.INTERVAL:
                reminder.interval_minutes = trigger_kwargs.get('interval_minutes')
                reminder.is_recurring = True
                reminder.max_occurrences = trigger_kwargs.get('max_occurrences')
                reminder.next_trigger = datetime.utcnow() + timedelta(minutes=reminder.interval_minutes)

            session.add(reminder)
            await session.commit()
            await session.refresh(reminder)

            # Schedule the reminder
            await self._schedule_reminder(reminder)

            return reminder

    async def _calculate_time_before_trigger(self, reminder: Reminder):
        """Calculate when to trigger a time_before reminder"""
        if reminder.target_type == TargetType.POLL.value and reminder.target_id:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Poll).where(Poll.poll_id == reminder.target_id)
                )
                poll = result.scalar_one_or_none()
                if poll and poll.expires_at:
                    trigger_time = poll.expires_at - timedelta(minutes=reminder.time_before_minutes)
                    if trigger_time > datetime.utcnow():
                        reminder.next_trigger = trigger_time

    # ========== Reminder Scheduling ==========

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

    async def _check_pending_reminders(self):
        """Check for any reminders that might have been missed"""
        try:
            async with AsyncSessionLocal() as session:
                now = datetime.utcnow()
                result = await session.execute(
                    select(Reminder).where(
                        Reminder.is_active == True,
                        Reminder.next_trigger <= now,
                        Reminder.next_trigger > now - timedelta(minutes=5)
                    )
                )
                missed_reminders = result.scalars().all()

                for reminder in missed_reminders:
                    await self._execute_reminder(reminder.reminder_id)
        except Exception as e:
            print(f"Error checking pending reminders: {e}")

    # ========== Reminder Execution ==========

    async def _execute_reminder(self, reminder_id: str):
        """Execute a reminder and send the message"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Reminder).where(Reminder.reminder_id == reminder_id)
            )
            reminder = result.scalar_one_or_none()

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

                # Send the reminder
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

                # Log success
                await self._log_reminder(reminder_id, 'sent', None, message_content['text'])
                self.stats_module.log_reminder_sent(reminder.created_by, reminder_id)

            except Exception as e:
                await self._log_reminder(reminder_id, 'failed', str(e))
                print(f"Error executing reminder {reminder_id}: {e}")

    async def _build_message_content(self, reminder: Reminder, template: ReminderTemplate) -> Dict[str, Any]:
        """Build the message content with template substitutions"""
        context = {
            'reminder_name': template.name,
            'current_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
        }

        # Add target-specific context
        if reminder.target_type == TargetType.POLL.value and reminder.target_id:
            context.update(await self._get_poll_context(reminder.target_id))
        elif reminder.target_type == TargetType.EVENT.value and reminder.target_id:
            context.update(await self._get_event_context(reminder.target_id))

        # Add custom data
        context.update(reminder.custom_data or {})

        # Substitute template
        try:
            message_text = template.message_template.format(**context)
        except KeyError as e:
            message_text = f"Template error: Missing variable {e}"

        return {
            'text': message_text,
            'context': context
        }

    async def _get_poll_context(self, poll_id: str) -> Dict[str, Any]:
        """Get context data for poll reminders"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Poll).where(Poll.poll_id == poll_id))
            poll = result.scalar_one_or_none()

            if not poll:
                return {'poll_title': 'Unknown Poll', 'time_left': 'Unknown'}

            time_left = 'Expired'
            if poll.expires_at and poll.expires_at > datetime.utcnow():
                delta = poll.expires_at - datetime.utcnow()
                hours = int(delta.total_seconds() // 3600)
                minutes = int((delta.total_seconds() % 3600) // 60)
                if hours > 0:
                    time_left = f"{hours}h {minutes}m"
                else:
                    time_left = f"{minutes}m"

            return {
                'poll_title': poll.question,
                'poll_id': poll.poll_id,
                'time_left': time_left,
                'poll_status': 'Active' if poll.is_active else 'Closed'
            }

    async def _get_event_context(self, event_id: str) -> Dict[str, Any]:
        """Get context data for event reminders"""
        # Implementation depends on your event model structure
        return {
            'event_title': f'Event {event_id}',
            'event_id': event_id
        }

    async def _create_reminder_embed(self, reminder: Reminder, template: ReminderTemplate,
                                   message_content: Dict[str, Any]) -> discord.Embed:
        """Create a Discord embed for the reminder"""
        priority = ReminderPriority(template.priority)
        config = self.priority_configs[priority]

        # Use template's custom color or default priority color
        embed_color = template.embed_color
        if embed_color.startswith('#'):
            # Convert hex string to integer for Discord.py
            embed_color = int(embed_color[1:], 16)
        else:
            # Fall back to priority config color
            embed_color = config['color']

        embed = discord.Embed(
            title=f"{config['emoji']} {template.name}",
            description=f"{config['urgent_indicator']}{message_content['text']}",
            color=embed_color,
            timestamp=datetime.utcnow()
        )

        # Add ping information if specified
        ping_text = []
        if template.ping_roles:
            ping_text.extend([f"<@&{role_id}>" for role_id in template.ping_roles])
        if template.ping_users:
            ping_text.extend([f"<@{user_id}>" for user_id in template.ping_users])

        if ping_text:
            embed.add_field(name="📢 Notifications", value=" ".join(ping_text), inline=False)

        embed.set_footer(text=f"Priority: {priority.value.title()} • Reminder ID: {reminder.reminder_id[:8]}")

        return embed

    async def _log_reminder(self, reminder_id: str, status: str, error_message: str = None,
                          message_content: str = None):
        """Log reminder execution"""
        async with AsyncSessionLocal() as session:
            log = ReminderLog(
                reminder_id=reminder_id,
                triggered_at=datetime.utcnow(),
                status=status,
                error_message=error_message,
                message_content=message_content
            )
            session.add(log)
            await session.commit()

    # ========== Management Methods ==========

    async def cancel_reminder(self, reminder_id: str) -> bool:
        """Cancel a specific reminder"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Reminder).where(Reminder.reminder_id == reminder_id)
            )
            reminder = result.scalar_one_or_none()

            if not reminder:
                return False

            reminder.is_active = False
            await session.commit()

            # Remove from scheduler
            try:
                self.scheduler.remove_job(f"reminder_{reminder_id}")
            except:
                pass

            return True

    async def list_reminders(self, creator_id: int = None, is_active: bool = None) -> List[Reminder]:
        """List reminders with optional filters"""
        async with AsyncSessionLocal() as session:
            query = select(Reminder)

            if creator_id:
                query = query.where(Reminder.created_by == creator_id)
            if is_active is not None:
                query = query.where(Reminder.is_active == is_active)

            result = await session.execute(query)
            return result.scalars().all()

    async def get_reminder_logs(self, reminder_id: str) -> List[ReminderLog]:
        """Get execution logs for a reminder"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ReminderLog).where(ReminderLog.reminder_id == reminder_id)
                .order_by(ReminderLog.triggered_at.desc())
            )
            return result.scalars().all()

    # ========== Convenience Methods for Poll Reminders ==========

    async def setup_poll_reminders(self, poll_id: str, channel_id: int, creator_id: int,
                                  reminders_config: List[Dict[str, Any]]):
        """Setup multiple reminders for a poll at once"""
        created_reminders = []

        for config in reminders_config:
            try:
                if config['type'] == 'time_before':
                    reminder = await self.create_poll_reminder(
                        poll_id=poll_id,
                        template_name=config['template'],
                        trigger_type=TriggerType.TIME_BEFORE,
                        channel_id=channel_id,
                        creator_id=creator_id,
                        minutes_before=config['minutes_before']
                    )
                elif config['type'] == 'interval':
                    reminder = await self.create_poll_reminder(
                        poll_id=poll_id,
                        template_name=config['template'],
                        trigger_type=TriggerType.INTERVAL,
                        channel_id=channel_id,
                        creator_id=creator_id,
                        interval_minutes=config['interval_minutes'],
                        max_occurrences=config.get('max_occurrences')
                    )
                created_reminders.append(reminder)
            except Exception as e:
                print(f"Failed to create reminder: {e}")

        return created_reminders