import discord
from discord import app_commands
from db.models import UserProfile
from datetime import datetime, timedelta

# --- Autocomplete helpers ---
async def command_autocomplete(interaction: discord.Interaction, current: str):
    commands = ["help", "grant_permission", "update_roles", "update_preferences", "add_role", "add_users_to_role", "add_user", "list_events", "add_event", "remove_event", "update_event", "remind"]
    return [app_commands.Choice(name=cmd, value=cmd) for cmd in commands if current.lower() in cmd.lower()]

async def role_autocomplete(interaction: discord.Interaction, current: str):
    roles = [role.name for role in interaction.guild.roles]
    return [app_commands.Choice(name=role, value=role) for role in roles if current.lower() in role.lower()]

# --- Slash Commands Registration ---
def register_all_commands(bot):
    tree = bot.tree

    @tree.command(name="help", description="Show all bot commands")
    async def help_command(interaction: discord.Interaction):
        commands = [
            "/grant_permission <role> <command>",
            "/update_roles <@user> <role1,role2,...>",
            "/update_preferences <key> <value>",
            "/add_role <role> <command1,command2,...>",
            "/add_users_to_role <role> <@user1> <@user2> ...",
            "/add_user <@user> <email>",
            "/list_events [days]",
            "/add_event <title> <start> <end>",
            "/remove_event <event_id>",
            "/update_event <event_id> <title> <start> <end>",
            "/remind",
        ]
        embed = discord.Embed(title="Available Commands", description="\n".join(commands), color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="grant_permission", description="Grant a command to a role")
    @app_commands.describe(role="Role to grant", command="Command to grant")
    @app_commands.autocomplete(command=command_autocomplete, role=role_autocomplete)
    async def grant_permission_command(interaction: discord.Interaction, role: str, command: str):
        if interaction.user.id != bot.owner_id:
            embed = discord.Embed(title="Permission Denied", description="Only the server owner can grant permissions.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        bot.permission_manager.grant_permission(role, command)
        embed = discord.Embed(title="Success", description=f"Granted permission for {role} to run {command}.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="add_role", description="Create a new role and assign commands to it")
    @app_commands.describe(role="Role name", commands="Comma-separated commands")
    async def add_role_command(interaction: discord.Interaction, role: str, commands: str):
        if interaction.user.id != bot.owner_id:
            embed = discord.Embed(title="Permission Denied", description="Only the server owner can add roles.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        guild = interaction.guild
        discord_role = discord.utils.get(guild.roles, name=role)
        if not discord_role:
            discord_role = await guild.create_role(name=role, reason="Created by bot command")
        bot.permission_manager.add_role(role, commands.split(","))
        embed = discord.Embed(title="Role Created", description=f"Role '{role}' created with commands: {commands}", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="add_users_to_role", description="Add users to a role")
    @app_commands.describe(role="Role name", users="Users to add")
    @app_commands.autocomplete(role=role_autocomplete)
    async def add_users_to_role_command(interaction: discord.Interaction, role: str, users: str):
        if interaction.user.id != bot.owner_id:
            embed = discord.Embed(title="Permission Denied", description="Only the server owner can add users to roles.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        guild = interaction.guild
        discord_role = discord.utils.get(guild.roles, name=role)
        if not discord_role:
            discord_role = await guild.create_role(name=role, reason="Created by bot command")
        mentions = [m for m in interaction.guild.members if f"@{m.display_name}" in users or f"@{m.name}" in users]
        for user in mentions:
            user_profile = bot.user_manager.get_user(user.id)
            if not user_profile:
                user_profile = bot.user_manager.ensure_user(user.id)
            bot.permission_manager.add_user_to_role(user_profile, role)
            if discord_role not in user.roles:
                await user.add_roles(discord_role, reason="Added by bot command")
        embed = discord.Embed(title="Users Added to Role", description=f"Added {len(mentions)} users to role '{role}'.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="add_user", description="Add a user with email")
    @app_commands.describe(user="User to add", email="User's email")
    async def add_user_command(interaction: discord.Interaction, user: discord.Member, email: str):
        try:
            bot.user_manager.ensure_user(user.id, calendar_email=email)
            embed = discord.Embed(title="Success", description=f"Added user <@{user.id}> with email {email}.", color=discord.Color.green())
        except Exception as e:
            embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="update_roles", description="Update roles for a user")
    @app_commands.describe(user="User to update", roles="Comma-separated roles")
    async def update_roles_command(interaction: discord.Interaction, user: discord.Member, roles: str):
        try:
            bot.user_manager.update_roles(user.id, roles.split(","))
            embed = discord.Embed(title="Success", description=f"Updated roles for <@{user.id}>: {roles}", color=discord.Color.green())
        except Exception as e:
            embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="update_preferences", description="Update your preferences")
    @app_commands.describe(key="Preference key", value="Preference value")
    async def update_preferences_command(interaction: discord.Interaction, key: str, value: str):
        try:
            bot.user_manager.update_preferences(interaction.user.id, {key: value})
            embed = discord.Embed(title="Success", description=f"Updated your preferences: {key} = {value}", color=discord.Color.green())
        except Exception as e:
            embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="list_events", description="List calendar events")
    @app_commands.describe(days="Number of days to look ahead")
    async def list_events_command(interaction: discord.Interaction, days: int = 7):
        calendar_service = bot.calendar_service
        now = datetime.utcnow()
        time_min = now
        time_max = now + timedelta(days=days)
        try:
            events = calendar_service.list_events(time_min=time_min, time_max=time_max)
            if not events:
                embed = discord.Embed(title="No Events", description=f"No events found in the next {days} days.", color=discord.Color.orange())
            else:
                lines = [f"{e.event_id}: {e.title} ({e.start_time} - {e.end_time})" for e in events]
                embed = discord.Embed(title="Upcoming Events", description="\n".join(lines), color=discord.Color.blue())
        except Exception as e:
            embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="add_event", description="Add a calendar event")
    @app_commands.describe(title="Event title", start="Start time (YYYY-MM-DDTHH:MM)", end="End time (YYYY-MM-DDTHH:MM)")
    async def add_event_command(interaction: discord.Interaction, title: str, start: str, end: str):
        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            bot.calendar_service.add_event(
                bot.calendar_service.__class__.__bases__[0].__name__ == 'object' and None or None,  # placeholder
                title=title, start_time=start_dt, end_time=end_dt
            )
            embed = discord.Embed(title="Success", description=f"Event '{title}' added.", color=discord.Color.green())
        except Exception as e:
            embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="remove_event", description="Remove a calendar event")
    @app_commands.describe(event_id="Event ID")
    async def remove_event_command(interaction: discord.Interaction, event_id: str):
        try:
            success = bot.calendar_service.remove_event(event_id)
            if success:
                embed = discord.Embed(title="Success", description=f"Event {event_id} removed.", color=discord.Color.green())
            else:
                embed = discord.Embed(title="Failed", description=f"Event {event_id} not found.", color=discord.Color.red())
        except Exception as e:
            embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="update_event", description="Update a calendar event")
    @app_commands.describe(event_id="Event ID", title="Event title", start="Start time (YYYY-MM-DDTHH:MM)", end="End time (YYYY-MM-DDTHH:MM)")
    async def update_event_command(interaction: discord.Interaction, event_id: str, title: str, start: str, end: str):
        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            success = bot.calendar_service.update_event(
                bot.calendar_service.__class__.__bases__[0].__name__ == 'object' and None or None,  # placeholder
                calendar_id='primary'
            )
            if success:
                embed = discord.Embed(title="Success", description=f"Event {event_id} updated.", color=discord.Color.green())
            else:
                embed = discord.Embed(title="Failed", description=f"Event {event_id} not found.", color=discord.Color.red())
        except Exception as e:
            embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="remind", description="Set a reminder for yourself in 10 seconds")
    async def remind_command(interaction: discord.Interaction):
        async def send_reminder():
            await interaction.followup.send(f"Reminder for {interaction.user.mention}!", ephemeral=True)
        run_time = datetime.now() + timedelta(seconds=10)
        def job_wrapper():
            bot.loop.create_task(send_reminder())
        bot.reminder_scheduler.schedule(job_wrapper, run_time)
        embed = discord.Embed(title="Reminder Set", description="Reminder set for 10 seconds from now!", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)
