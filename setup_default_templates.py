#!/usr/bin/env python3
"""
Setup script to create default reminder templates.
Run this once after the bot is set up to create useful templates.
"""

import asyncio
from services.reminder_manager import ReminderManager, ReminderPriority
from utils.stats_module import StatsModule
import discord

# Mock client for initialization
class MockClient:
    def get_channel(self, channel_id):
        return None

async def create_default_templates():
    """Create default reminder templates"""

    # Initialize managers
    mock_client = MockClient()
    stats_module = StatsModule()
    reminder_manager = ReminderManager(mock_client, stats_module)

    # Default templates to create
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
            'name': 'deadline_reminder',
            'description': 'Project deadline reminder',
            'message_template': '⚠️ **DEADLINE APPROACHING**\n\n📝 **Task:** {task_title}\n⏰ **Due:** {due_date}\n📊 **Priority:** {task_priority}',
            'priority': ReminderPriority.VERY_URGENT,
            'creator_id': 0
        },
        {
            'name': 'daily_standup',
            'description': 'Daily standup meeting reminder',
            'message_template': '☀️ **Daily Standup Time!**\n\n🕘 Time for our daily sync-up\n📋 Share: What you did yesterday, what you\'re doing today, any blockers',
            'priority': ReminderPriority.INFORMATIONAL,
            'creator_id': 0
        },
        {
            'name': 'critical_alert',
            'description': 'Critical system alert template',
            'message_template': '🚨 **CRITICAL ALERT** 🚨\n\n{alert_message}\n\n⚠️ Immediate attention required!\n📞 Contact: {contact_info}',
            'priority': ReminderPriority.CRITICAL,
            'creator_id': 0
        },
        {
            'name': 'birthday_reminder',
            'description': 'Birthday celebration reminder',
            'message_template': '🎉 **Birthday Alert!** 🎂\n\n🎈 It\'s {person_name}\'s birthday today!\n🎁 Don\'t forget to wish them well!',
            'priority': ReminderPriority.INFORMATIONAL,
            'creator_id': 0
        }
    ]

    print("Creating default reminder templates...")

    for template_data in templates:
        try:
            # Check if template already exists
            existing = await reminder_manager.get_template(template_data['name'])
            if existing:
                print(f"✅ Template '{template_data['name']}' already exists, skipping")
                continue

            # Create the template
            template = await reminder_manager.create_template(
                name=template_data['name'],
                description=template_data['description'],
                message_template=template_data['message_template'],
                priority=template_data['priority'],
                creator_id=template_data['creator_id']
            )
            print(f"✅ Created template: {template_data['name']}")

        except Exception as e:
            print(f"❌ Failed to create template '{template_data['name']}': {e}")

    print("\nDefault templates setup complete!")
    print("\nCreated templates:")
    for template_data in templates:
        print(f"  • {template_data['name']} - {template_data['description']}")

    print("\nExample usage:")
    print("  /create_reminder_template poll_reminder \"📊 Vote in: {poll_title}\" urgent")
    print("  /set_poll_reminder abc123 poll_reminder time_before minutes_before:30")
    print("  /quick_poll_reminders abc123 poll_reminder 60,30,10")

if __name__ == "__main__":
    asyncio.run(create_default_templates())