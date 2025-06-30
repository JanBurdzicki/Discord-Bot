import discord

async def help_command(interaction: discord.Interaction):
    """Comprehensive help command with all bot functionality organized by category"""
    embed = discord.Embed(
        title="🤖 Discord Bot - Command Reference",
        description="Complete list of available commands organized by category",
        color=discord.Color.blue()
    )

    # Personal Calendar Setup
    embed.add_field(
        name="👤 Personal Calendar Setup",
        value="• `/calendar_help` - Show Google Calendar sharing instructions\n• `/link_user_calendar <calendar_id>` - Link your personal Google Calendar\n• `/find_free_slots <start> <end> [duration]` - Find free time slots\n• `/reserve_slot <title> <start> <end>` - Reserve time in your calendar",
        inline=False
    )

    # Admin Calendar Management
    embed.add_field(
        name="🔧 Admin Calendar Management (Owner Only)",
        value="• `/create_shared_calendar <name> [description]` - Create shared calendar\n• `/add_calendar_users <calendar> <permission> [roles] [users]` - Add users with permissions\n• `/list_calendar_users <calendar>` - List calendar access permissions\n• `/remove_calendar_users <calendar> [roles] [users]` - Remove user access",
        inline=False
    )

    # Event Management
    embed.add_field(
        name="📅 Event Management",
        value="• `/add_event <calendar> <name> <start> <end> [location] [description] [roles]` - Create event\n• `/list_events <calendar> [days_ahead]` - List upcoming events\n• `/update_event <calendar> <event_id> [name] [start] [end] [location] [description]` - Update event\n• `/delete_event <calendar> <event_id>` - Delete event\n• `/visualize_day <calendar> <date> [start_hour] [end_hour]` - Show day schedule",
        inline=False
    )

    # Poll System
    embed.add_field(
        name="📊 Poll System",
        value="• `/create_poll <question> <options> <duration>` - Create simple poll (reactions)\n• `/create_advanced_poll <question> <options> [multi]` - Create advanced poll (StrawPoll)\n• `/vote_poll <poll_id> <option_indexes>` - Vote in a poll\n• `/poll_results <poll_id>` - Show poll results with visualization\n• `/list_polls` - List all active polls\n• `/delete_poll <poll_id>` - Delete a poll",
        inline=False
    )

    # Role Management
    embed.add_field(
        name="🛡️ Role Management (Owner Only)",
        value="• `/create_role <role_name> [commands]` - Create new role with permissions\n• `/delete_role <role_name>` - Delete role and update related data\n• `/list_role_permissions <role_name>` - List role permissions\n• `/add_role_permission <role_name> <command>` - Add command permission to role\n• `/remove_role_permission <role_name> <command>` - Remove command permission\n• `/list_role_members <role_name>` - List people with given role\n• `/add_user_to_role <user> <role_name>` - Add user to role\n• `/remove_user_from_role <user> <role_name>` - Remove user from role\n• `/list_user_roles <user>` - List user's roles\n• `/list_all_roles` - List all server roles with details",
        inline=False
    )

    # User Management
    embed.add_field(
        name="👥 User Management",
        value="• `/add_user <user> <email>` - Add user with email\n• `/update_roles <user> <roles>` - Update user roles\n• `/update_preferences <key> <value>` - Update your preferences",
        inline=False
    )

    # Utilities
    embed.add_field(
        name="🔧 Utilities",
        value="• `/remind` - Set a reminder for yourself\n• `/stats` - Show voting and poll statistics\n• `/help` - Show this help message",
        inline=False
    )

    # Permission Levels Info
    embed.add_field(
        name="🔐 Calendar Permission Levels",
        value="• **Owner** - Full access (create, edit, delete, manage users)\n• **Writer** - Can create and edit events\n• **Reader** - Can only view events",
        inline=False
    )

    # Usage Notes
    embed.add_field(
        name="📋 Usage Notes",
        value="• Commands marked with **(Owner Only)** require server owner permissions\n• Date format: `YYYY-MM-DD HH:MM` (e.g., `2024-01-15 14:30`)\n• Use `/calendar_help` for detailed Google Calendar setup instructions\n• Multiple values: Use comma separation (e.g., `role1,role2,role3`)",
        inline=False
    )

    embed.set_footer(text="💡 Tip: Use Tab completion for command parameters and role names!")

    await interaction.response.send_message(embed=embed, ephemeral=True)

