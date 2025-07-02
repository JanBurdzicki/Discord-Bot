"""Help command implementations."""
from typing import Dict, Any
import discord
from src.core.base_command import BaseCommand
from src.core.builders import EmbedBuilder

class HelpCommand(BaseCommand):
    """Command to show all bot commands and documentation."""

    async def validate_input(self, interaction: discord.Interaction, **kwargs) -> Dict[str, Any]:
        """No validation needed for help command."""
        return {"validated": True}

    async def check_permissions(self, interaction: discord.Interaction, **kwargs) -> bool:
        """Anyone can view help."""
        return True

    async def process_command(self, interaction: discord.Interaction, data: Dict[str, Any]) -> Dict[str, Any]:
        """Build the help embed and return it as result data."""
        embed = EmbedBuilder()\
            .set_title("🤖 Discord Bot - Command Reference")\
            .set_description("Complete list of available commands organized by category")\
            .set_color(discord.Color.blue())

        # Personal Calendar Setup
        embed.add_field(
            "👤 Personal Calendar Setup",
            "• `/calendar_help` - Show Google Calendar sharing instructions\n"
            "• `/link_user_calendar <calendar_id>` - Link your personal Google Calendar\n"
            "• `/find_free_slots <start> <end> [duration]` - Find free time slots in your calendar",
            inline=False
        )

        # Admin Calendar Management
        embed.add_field(
            "🔧 Admin Calendar Management (Owner Only)",
            "• `/create_shared_calendar <name> [description]` - Create shared calendar\n"
            "• `/add_calendar_users <calendar> <permission> [roles] [users]` - Add users with permissions\n"
            "• `/list_calendar_users <calendar>` - List calendar access permissions\n"
            "• `/remove_calendar_users <calendar> [roles] [users]` - Remove user access",
            inline=False
        )

        # Event Management
        embed.add_field(
            "📅 Event Management",
            "• `/add_event <calendar> <name> <start> <end> [location] [description] [roles]` - Create event\n"
            "• `/list_events <calendar> [days_ahead]` - List upcoming events\n"
            "• `/update_event <calendar> <event_id> [name] [start] [end] [location] [description]` - Update event\n"
            "• `/delete_event <calendar> <event_id>` - Delete event\n"
            "• `/visualize_day <calendar> <date> [start_hour] [end_hour]` - Show day schedule\n"
            "• `/visualize_period <calendar> <start_date> <end_date>` - Show period schedule",
            inline=False
        )

        # Poll System
        embed.add_field(
            "📊 Poll System",
            "• `/create_poll <question> <options> <duration>` - Create simple poll (reactions)\n"
            "• `/create_advanced_poll <question> <options> [multi]` - Create advanced poll (StrawPoll)\n"
            "• `/vote_poll <poll_id> <option_indexes>` - Vote in a poll\n"
            "• `/poll_results <poll_id>` - Show poll results with visualization\n"
            "• `/list_polls` - List all active polls\n"
            "• `/delete_poll <poll_id>` - Delete a poll",
            inline=False
        )

        # Reminder System
        embed.add_field(
            "⏰ Reminder System",
            "• `/create_reminder_template <name> <message> [priority]` - Create reminder template\n"
            "• `/list_reminder_templates [show_mine_only]` - List available templates\n"
            "• `/set_poll_reminder <poll_id> <template> [type]` - Set poll reminder\n"
            "• `/set_custom_reminder <template> <type> [params]` - Set custom reminder\n"
            "• `/quick_poll_reminders <poll_id> [template] [times]` - Quick poll setup\n"
            "• `/list_reminders [show_inactive]` - List your reminders\n"
            "• `/cancel_reminder <reminder_id>` - Cancel a reminder\n"
            "• `/reminder_logs <reminder_id>` - View reminder execution logs",
            inline=False
        )

        # User Management
        embed.add_field(
            "👥 User Management",
            "• `/user_status [user]` - Check user status and preferences\n"
            "• `/set_preference <key> <value>` - Set a preference\n"
            "• `/get_preference <key>` - Get a preference value\n"
            "• `/remove_preference <key>` - Remove a preference\n"
            "• `/list_preferences` - List all your preferences\n"
            "• `/clear_preferences` - Clear all preferences\n"
            "• `/update_calendar_email <email>` - Update calendar email\n"
            "• `/manage_user_role <user> <role> <action>` - Manage user roles (Admin)\n"
            "• `/update_roles <user> <roles>` - Update user roles (Admin)",
            inline=False
        )

        # Role Management
        embed.add_field(
            "🛡️ Role Management (Owner Only)",
            "• `/create_role <role_name> [commands]` - Create new role with permissions\n"
            "• `/delete_role <role_name>` - Delete role and update related data\n"
            "• `/list_role_permissions <role_name>` - List role permissions\n"
            "• `/add_role_permission <role_name> <command>` - Add command permission to role\n"
            "• `/remove_role_permission <role_name> <command>` - Remove command permission\n"
            "• `/list_role_members <role_name>` - List people with given role\n"
            "• `/add_user_to_role <user> <role_name>` - Add user to role\n"
            "• `/remove_user_from_role <user> <role_name>` - Remove user from role\n"
            "• `/list_user_roles <user>` - List user's roles\n"
            "• `/list_all_roles` - List all server roles with details",
            inline=False
        )

        # Utilities
        embed.add_field(
            "🔧 Utilities",
            "• `/stats` - Show bot statistics\n"
            "• `/help` - Show this help message",
            inline=False
        )

        # Permission Levels Info
        embed.add_field(
            "🔐 Calendar Permission Levels",
            "• **Owner** - Full access (create, edit, delete, manage users)\n"
            "• **Writer** - Can create and edit events\n"
            "• **Reader** - Can only view events",
            inline=False
        )

        # Usage Notes
        embed.add_field(
            "📋 Usage Notes",
            "• Commands marked with **(Admin/Owner Only)** require special permissions\n"
            "• Date format: `YYYY-MM-DD HH:MM` (e.g., `2024-01-15 14:30`)\n"
            "• Use `/calendar_help` for detailed Google Calendar setup instructions\n"
            "• Multiple values: Use comma separation (e.g., `role1,role2,role3`)\n"
            "• Some advanced features may be under development",
            inline=False
        )

        embed.set_footer(text="💡 Tip: Use Tab completion for command parameters and role names!")

        await interaction.response.defer()
        return {"success": True, "embed": embed.build()}

    async def send_response(self, interaction: discord.Interaction, result: Dict[str, Any]) -> None:
        """Send the generated help embed to the user."""
        embed = result.get("embed")
        if embed:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to generate help information.", ephemeral=True)