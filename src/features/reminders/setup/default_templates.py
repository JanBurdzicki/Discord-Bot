"""
Script to create default reminder templates.
Run this after database initialization to set up common templates.
"""

from typing import List, Dict, Any
from ..services.reminder_service import ReminderService, ReminderPriority

async def create_default_templates(reminder_service: ReminderService) -> None:
    """Create default reminder templates"""

    # Default templates configuration
    templates = [
        {
            'name': 'poll_reminder',
            'description': 'Standard poll reminder template',
            'message_template': '⏰ Don\'t forget to vote in the poll: **{poll_title}**\n\n🕒 Time left: {time_left}\n📊 Poll ID: {poll_id}',
            'priority': ReminderPriority.URGENT,
            'creator_id': 0  # System created
        },
        {
            'name': 'poll_urgent',
            'description': 'Urgent poll reminder for final calls',
            'message_template': '🚨 **FINAL CALL** - Poll closing soon!\n\n📊 **Poll:** {poll_title}\n⏰ **Time left:** {time_left}\n\n👉 Vote now: Poll ID `{poll_id}`',
            'priority': ReminderPriority.VERY_URGENT,
            'creator_id': 0
        },
        {
            'name': 'event_reminder',
            'description': 'General event reminder template',
            'message_template': '📅 Upcoming event: **{event_title}**\n\n🕒 Starting soon!\n🆔 Event ID: {event_id}',
            'priority': ReminderPriority.INFORMATIONAL,
            'creator_id': 0
        },
        {
            'name': 'meeting_reminder',
            'description': 'Meeting reminder template',
            'message_template': '🤝 Meeting reminder: **{meeting_title}**\n\n📅 **Time:** {meeting_time}\n📍 **Location:** {meeting_location}\n📋 **Agenda:** {meeting_agenda}',
            'priority': ReminderPriority.URGENT,
            'creator_id': 0
        },
        {
            'name': 'task_reminder',
            'description': 'Task deadline reminder template',
            'message_template': '📋 Task reminder: **{task_title}**\n\n⏰ Deadline: {deadline}\n📝 Description: {description}\n👤 Assigned to: {assigned_to}',
            'priority': ReminderPriority.URGENT,
            'creator_id': 0
        }
    ]

    # Create each template
    for template_config in templates:
        try:
            await reminder_service.create_template(**template_config)
            print(f"✅ Created template: {template_config['name']}")
        except Exception as e:
            print(f"❌ Failed to create template {template_config['name']}: {str(e)}")

    print("\n✨ Default templates setup complete!")