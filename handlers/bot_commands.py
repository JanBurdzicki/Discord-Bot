import discord
from discord import app_commands
from handlers.reminder_commands import remind_command
from handlers.stat_commands import stats_command
from handlers.calendar_management import (
    calendar_help_command, link_user_calendar_command, create_shared_calendar_command,
    add_calendar_users_command, list_calendar_users_command, remove_calendar_users_command,
    add_event_command, list_events_command, update_event_command, delete_event_command,
    visualize_day_command
)
from handlers.calendar_commands import find_free_slots_command, reserve_slot_command
from handlers.poll_commands import create_poll_command, create_advanced_poll_command, vote_poll_command, poll_results_command, list_polls_command, delete_poll_command
from handlers.user_commands import add_user_command, update_roles_command, update_preferences_command

from handlers.help_commands import help_command
from handlers.role_management import (
    create_role_command, delete_role_command, list_role_permissions_command,
    add_role_permission_command, remove_role_permission_command, list_role_members_command,
    add_user_to_role_command, remove_user_from_role_command, list_user_roles_command,
    list_all_roles_command
)

# --- Autocomplete helpers ---
async def command_autocomplete(interaction: discord.Interaction, current: str):
    commands = ["help", "update_roles", "update_preferences", "add_user", "remind", "create_poll", "create_advanced_poll", "vote_poll", "poll_results", "list_polls", "delete_poll", "create_role", "delete_role", "list_role_permissions", "add_role_permission", "remove_role_permission", "list_role_members", "add_user_to_role", "remove_user_from_role", "list_user_roles", "list_all_roles", "calendar_help", "link_user_calendar", "create_shared_calendar", "add_calendar_users", "list_calendar_users", "remove_calendar_users", "add_event", "list_events", "update_event", "delete_event", "visualize_day", "find_free_slots", "reserve_slot", "sync_commands"]
    return [app_commands.Choice(name=cmd, value=cmd) for cmd in commands if current.lower() in cmd.lower()]

async def role_autocomplete(interaction: discord.Interaction, current: str):
    roles = [role.name for role in interaction.guild.roles]
    return [app_commands.Choice(name=role, value=role) for role in roles if current.lower() in role.lower()]


# --- Slash Commands Registration ---
def register_all_commands(bot):
    tree = bot.tree

    @tree.command(name="help", description="Show all bot commands")
    async def help_slash(interaction: discord.Interaction):
        await help_command(interaction)

    @tree.command(name="stats", description="Show voting and poll stats")
    async def stats_slash(interaction: discord.Interaction):
        await stats_command(interaction)

    # User management commands
    @tree.command(name="update_roles", description="Update roles for a user")
    @app_commands.describe(user="User to update", roles="Comma-separated roles")
    async def update_roles_slash(interaction: discord.Interaction, user: discord.Member, roles: str):
        await update_roles_command(interaction, user, roles)

    @tree.command(name="update_preferences", description="Update your preferences")
    @app_commands.describe(key="Preference key", value="Preference value")
    async def update_preferences_slash(interaction: discord.Interaction, key: str, value: str):
        await update_preferences_command(interaction, key, value)

    @tree.command(name="add_user", description="Add a user with email")
    @app_commands.describe(user="User to add", email="User's email")
    async def add_user_slash(interaction: discord.Interaction, user: discord.Member, email: str):
        await add_user_command(interaction, user, email)



    # Reminder command
    @tree.command(name="remind", description="Set a reminder for yourself in 10 seconds")
    async def remind_slash(interaction: discord.Interaction):
        await remind_command(interaction)

    # Calendar Management Commands
    @tree.command(name="calendar_help", description="Show calendar setup instructions")
    async def calendar_help_slash(interaction: discord.Interaction):
        await calendar_help_command(interaction)

    @tree.command(name="link_user_calendar", description="Link your personal Google Calendar")
    @app_commands.describe(calendar_id="Your Google Calendar ID (email format)")
    async def link_user_calendar_slash(interaction: discord.Interaction, calendar_id: str = ""):
        await link_user_calendar_command(interaction, calendar_id)

    @tree.command(name="create_shared_calendar", description="Create a shared calendar (Admin only)")
    @app_commands.describe(calendar_name="Name of the calendar", description="Optional description")
    async def create_shared_calendar_slash(interaction: discord.Interaction, calendar_name: str, description: str = ""):
        await create_shared_calendar_command(interaction, calendar_name, description)

    @tree.command(name="add_calendar_users", description="Add users to shared calendar (Admin only)")
    @app_commands.describe(calendar_name="Calendar name", permission="Permission level (reader/writer/owner)", roles="Comma-separated roles", users="Comma-separated users")
    async def add_calendar_users_slash(interaction: discord.Interaction, calendar_name: str, permission: str, roles: str = "", users: str = ""):
        await add_calendar_users_command(interaction, calendar_name, permission, roles, users)

    @tree.command(name="list_calendar_users", description="List users with access to a calendar")
    @app_commands.describe(calendar_name="Calendar name")
    async def list_calendar_users_slash(interaction: discord.Interaction, calendar_name: str):
        await list_calendar_users_command(interaction, calendar_name)

    @tree.command(name="remove_calendar_users", description="Remove users from shared calendar (Admin only)")
    @app_commands.describe(calendar_name="Calendar name", roles="Comma-separated roles", users="Comma-separated users")
    async def remove_calendar_users_slash(interaction: discord.Interaction, calendar_name: str, roles: str = "", users: str = ""):
        await remove_calendar_users_command(interaction, calendar_name, roles, users)

    # Event Management Commands
    @tree.command(name="add_event", description="Add event to shared calendar")
    @app_commands.describe(calendar_name="Calendar name", event_name="Event name", start_time="Start (YYYY-MM-DD HH:MM)", end_time="End (YYYY-MM-DD HH:MM)", location="Location (optional)", description="Description (optional)", roles="Roles to assign (optional)")
    async def add_event_slash(interaction: discord.Interaction, calendar_name: str, event_name: str, start_time: str, end_time: str, location: str = "", description: str = "", roles: str = ""):
        await add_event_command(interaction, calendar_name, event_name, start_time, end_time, location, description, roles)

    @tree.command(name="list_events", description="List events in a calendar")
    @app_commands.describe(calendar_name="Calendar name", days_ahead="Days to look ahead")
    async def list_events_slash(interaction: discord.Interaction, calendar_name: str, days_ahead: int = 7):
        await list_events_command(interaction, calendar_name, days_ahead)

    @tree.command(name="update_event", description="Update an existing event")
    @app_commands.describe(calendar_name="Calendar name", event_id="Event ID", event_name="New name (optional)", start_time="New start (optional)", end_time="New end (optional)", location="New location (optional)", description="New description (optional)")
    async def update_event_slash(interaction: discord.Interaction, calendar_name: str, event_id: str, event_name: str = "", start_time: str = "", end_time: str = "", location: str = "", description: str = ""):
        await update_event_command(interaction, calendar_name, event_id, event_name, start_time, end_time, location, description)

    @tree.command(name="delete_event", description="Delete an event from calendar")
    @app_commands.describe(calendar_name="Calendar name", event_id="Event ID")
    async def delete_event_slash(interaction: discord.Interaction, calendar_name: str, event_id: str):
        await delete_event_command(interaction, calendar_name, event_id)

    @tree.command(name="visualize_day", description="Visualize a day with events")
    @app_commands.describe(calendar_name="Calendar name", date="Date (YYYY-MM-DD)", start_hour="Start hour (0-23)", end_hour="End hour (0-23)")
    async def visualize_day_slash(interaction: discord.Interaction, calendar_name: str, date: str, start_hour: int = 8, end_hour: int = 18):
        await visualize_day_command(interaction, calendar_name, date, start_hour, end_hour)

    # Poll commands
    @tree.command(name="create_poll", description="Create a simple poll (reactions)")
    @app_commands.describe(question="Poll question", options="Comma-separated options", duration="Duration in minutes")
    async def create_poll_slash(interaction: discord.Interaction, question: str, options: str, duration: int = 60):
        await create_poll_command(interaction, question, options, duration)

    @tree.command(name="create_advanced_poll", description="Create an advanced poll (StrawPoll)")
    @app_commands.describe(question="Poll question", options="Comma-separated options", multi="Allow multiple answers?")
    async def create_advanced_poll_slash(interaction: discord.Interaction, question: str, options: str, multi: bool = False):
        await create_advanced_poll_command(interaction, question, options, multi)

    @tree.command(name="vote_poll", description="Vote in a poll")
    @app_commands.describe(poll_id="Poll ID", option_indexes="Option number(s) - single: '2' or multiple: '1,3,5'")
    async def vote_poll_slash(interaction: discord.Interaction, poll_id: str, option_indexes: str):
        await vote_poll_command(interaction, poll_id, option_indexes)

    @tree.command(name="poll_results", description="Show poll results with visualization")
    @app_commands.describe(poll_id="Poll ID")
    async def poll_results_slash(interaction: discord.Interaction, poll_id: str):
        await poll_results_command(interaction, poll_id)

    @tree.command(name="list_polls", description="List all active polls")
    async def list_polls_slash(interaction: discord.Interaction):
        await list_polls_command(interaction)

    @tree.command(name="delete_poll", description="Delete a poll")
    @app_commands.describe(poll_id="Poll ID")
    async def delete_poll_slash(interaction: discord.Interaction, poll_id: str):
        await delete_poll_command(interaction, poll_id)

    # Role Management Commands
    @tree.command(name="create_role", description="Create a new role with optional commands (Owner only)")
    @app_commands.describe(role_name="Name of the role to create", commands="Comma-separated commands (optional)")
    async def create_role_slash(interaction: discord.Interaction, role_name: str, commands: str = ""):
        await create_role_command(interaction, role_name, commands)

    @tree.command(name="delete_role", description="Delete a role and update all related data (Owner only)")
    @app_commands.describe(role_name="Name of the role to delete")
    @app_commands.autocomplete(role_name=role_autocomplete)
    async def delete_role_slash(interaction: discord.Interaction, role_name: str):
        await delete_role_command(interaction, role_name)

    @tree.command(name="list_role_permissions", description="List permissions/commands for a specific role")
    @app_commands.describe(role_name="Name of the role")
    @app_commands.autocomplete(role_name=role_autocomplete)
    async def list_role_permissions_slash(interaction: discord.Interaction, role_name: str):
        await list_role_permissions_command(interaction, role_name)

    @tree.command(name="add_role_permission", description="Add a command permission to a role (Owner only)")
    @app_commands.describe(role_name="Name of the role", command="Command to allow")
    @app_commands.autocomplete(role_name=role_autocomplete, command=command_autocomplete)
    async def add_role_permission_slash(interaction: discord.Interaction, role_name: str, command: str):
        await add_role_permission_command(interaction, role_name, command)

    @tree.command(name="remove_role_permission", description="Remove a command permission from a role (Owner only)")
    @app_commands.describe(role_name="Name of the role", command="Command to remove")
    @app_commands.autocomplete(role_name=role_autocomplete, command=command_autocomplete)
    async def remove_role_permission_slash(interaction: discord.Interaction, role_name: str, command: str):
        await remove_role_permission_command(interaction, role_name, command)

    @tree.command(name="list_role_members", description="List all people with a given role")
    @app_commands.describe(role_name="Name of the role")
    @app_commands.autocomplete(role_name=role_autocomplete)
    async def list_role_members_slash(interaction: discord.Interaction, role_name: str):
        await list_role_members_command(interaction, role_name)

    @tree.command(name="add_user_to_role", description="Add a user to a specific role (Owner only)")
    @app_commands.describe(user="User to add to role", role_name="Name of the role")
    @app_commands.autocomplete(role_name=role_autocomplete)
    async def add_user_to_role_slash(interaction: discord.Interaction, user: discord.Member, role_name: str):
        await add_user_to_role_command(interaction, user, role_name)

    @tree.command(name="remove_user_from_role", description="Remove a user from a specific role (Owner only)")
    @app_commands.describe(user="User to remove from role", role_name="Name of the role")
    @app_commands.autocomplete(role_name=role_autocomplete)
    async def remove_user_from_role_slash(interaction: discord.Interaction, user: discord.Member, role_name: str):
        await remove_user_from_role_command(interaction, user, role_name)

    @tree.command(name="list_user_roles", description="List all roles for a specific user")
    @app_commands.describe(user="User to check roles for")
    async def list_user_roles_slash(interaction: discord.Interaction, user: discord.Member):
        await list_user_roles_command(interaction, user)

    @tree.command(name="list_all_roles", description="List all roles in the server with details")
    async def list_all_roles_slash(interaction: discord.Interaction):
        await list_all_roles_command(interaction)

    # Free/Busy and Calendar Slot Commands
    @tree.command(name="find_free_slots", description="Find free time slots in your calendar")
    @app_commands.describe(start="Start date/time (YYYY-MM-DD HH:MM)", end="End date/time (YYYY-MM-DD HH:MM)", duration="Duration in minutes")
    async def find_free_slots_slash(interaction: discord.Interaction, start: str, end: str, duration: int = 30):
        await find_free_slots_command(interaction, start, end, duration)

    @tree.command(name="reserve_slot", description="Reserve a time slot in your calendar")
    @app_commands.describe(title="Event title", start="Start date/time (YYYY-MM-DD HH:MM)", end="End date/time (YYYY-MM-DD HH:MM)")
    async def reserve_slot_slash(interaction: discord.Interaction, title: str, start: str, end: str):
        await reserve_slot_command(interaction, title, start, end)

    # Admin Commands
    @tree.command(name="sync_commands", description="Manually sync bot commands with Discord (Owner only)")
    @app_commands.describe(guild_only="Sync to current server only (faster for testing)")
    async def sync_commands_slash(interaction: discord.Interaction, guild_only: bool = False):
        # Only bot owner can sync commands
        if interaction.user.id != bot.owner_id:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="Only the bot owner can sync commands.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            if guild_only and interaction.guild:
                synced_count = await bot.manual_sync_commands(interaction.guild.id)
                embed = discord.Embed(
                    title="✅ Commands Synced (Guild)",
                    description=f"Successfully synced {synced_count} commands to this server.\n\nCommands should appear immediately in this server.",
                    color=discord.Color.green()
                )
            else:
                synced_count = await bot.manual_sync_commands()
                embed = discord.Embed(
                    title="✅ Commands Synced (Global)",
                    description=f"Successfully synced {synced_count} commands globally.\n\n⚠️ It may take up to 1 hour for commands to appear in all servers.",
                    color=discord.Color.green()
                )

            embed.add_field(name="📋 New Commands", value="• `/find_free_slots` - Find free time slots\n• `/reserve_slot` - Reserve calendar time\n• `/sync_commands` - This command", inline=False)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Sync Failed",
                description=f"Failed to sync commands: {str(e)}",
                color=discord.Color.red()
            )

        await interaction.followup.send(embed=embed, ephemeral=True)
