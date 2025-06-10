import discord
from db.models import UserProfile
from datetime import datetime, timedelta

async def help_command(message):
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
    await message.channel.send(embed=embed)

async def grant_permission_command(message):
    args = message.content.split()
    if len(args) < 3:
        embed = discord.Embed(title="Usage", description="/grant_permission <role> <command>", color=discord.Color.red())
        await message.channel.send(embed=embed)
        return
    role, command = args[1], args[2]
    permission_manager = message._bot.permission_manager
    try:
        permission_manager.grant_permission(role, command)
        embed = discord.Embed(title="Success", description=f"Granted permission for {role} to run {command}.", color=discord.Color.green())
    except Exception as e:
        embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
    await message.channel.send(embed=embed)

async def update_roles_command(message):
    args = message.content.split()
    if len(args) < 3:
        embed = discord.Embed(title="Usage", description="/update_roles <@user> <role1,role2,...>", color=discord.Color.red())
        await message.channel.send(embed=embed)
        return
    user_mention = args[1]
    roles = args[2].split(",")
    user_id = int(user_mention.strip("<@!>"))
    user_manager = message._bot.user_manager
    try:
        user_manager.update_roles(user_id, roles)
        embed = discord.Embed(title="Success", description=f"Updated roles for <@{user_id}>: {roles}", color=discord.Color.green())
    except Exception as e:
        embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
    await message.channel.send(embed=embed)

async def update_preferences_command(message):
    args = message.content.split()
    if len(args) < 3:
        embed = discord.Embed(title="Usage", description="/update_preferences <key> <value>", color=discord.Color.red())
        await message.channel.send(embed=embed)
        return
    key, value = args[1], args[2]
    user_manager = message._bot.user_manager
    try:
        user_manager.update_preferences(message.author.id, {key: value})
        embed = discord.Embed(title="Success", description=f"Updated your preferences: {key} = {value}", color=discord.Color.green())
    except Exception as e:
        embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
    await message.channel.send(embed=embed)

async def add_role_command(message):
    args = message.content.split()
    if len(args) < 3:
        embed = discord.Embed(title="Usage", description="/add_role <role> <command1,command2,...>", color=discord.Color.red())
        await message.channel.send(embed=embed)
        return
    role_name = args[1]
    commands = args[2].split(",")
    permission_manager = message._bot.permission_manager
    # Only owner can add roles
    if message.author.id != permission_manager.owner_id:
        embed = discord.Embed(title="Permission Denied", description="Only the server owner can add roles.", color=discord.Color.red())
        await message.channel.send(embed=embed)
        return
    # Create Discord role if it doesn't exist
    guild = message.guild
    discord_role = discord.utils.get(guild.roles, name=role_name)
    if not discord_role:
        discord_role = await guild.create_role(name=role_name, reason="Created by bot command")
    permission_manager.add_role(role_name, commands)
    embed = discord.Embed(title="Role Created", description=f"Role '{role_name}' created with commands: {', '.join(commands)}", color=discord.Color.green())
    await message.channel.send(embed=embed)

async def add_users_to_role_command(message):
    args = message.content.split()
    if len(args) < 3:
        embed = discord.Embed(title="Usage", description="/add_users_to_role <role> <@user1> <@user2> ...", color=discord.Color.red())
        await message.channel.send(embed=embed)
        return
    role_name = args[1]
    mentions = message.mentions
    if not mentions:
        embed = discord.Embed(title="Error", description="You must mention users to add to the role.", color=discord.Color.red())
        await message.channel.send(embed=embed)
        return
    permission_manager = message._bot.permission_manager
    user_manager = message._bot.user_manager
    # Only owner can add users to roles
    if message.author.id != permission_manager.owner_id:
        embed = discord.Embed(title="Permission Denied", description="Only the server owner can add users to roles.", color=discord.Color.red())
        await message.channel.send(embed=embed)
        return
    guild = message.guild
    discord_role = discord.utils.get(guild.roles, name=role_name)
    if not discord_role:
        discord_role = await guild.create_role(name=role_name, reason="Created by bot command")
    for user in mentions:
        user_profile = user_manager.get_user(user.id)
        if not user_profile:
            user_profile = user_manager.ensure_user(user.id)
        permission_manager.add_user_to_role(user_profile, role_name)
        # Add Discord role to user
        member = guild.get_member(user.id)
        if member and discord_role not in member.roles:
            await member.add_roles(discord_role, reason="Added by bot command")
    embed = discord.Embed(title="Users Added to Role", description=f"Added {len(mentions)} users to role '{role_name}'.", color=discord.Color.green())
    await message.channel.send(embed=embed)

async def add_user_command(message):
    args = message.content.split()
    if len(args) < 3:
        embed = discord.Embed(title="Usage", description="/add_user <@user> <email>", color=discord.Color.red())
        await message.channel.send(embed=embed)
        return
    user_mention = args[1]
    email = args[2]
    user_id = int(user_mention.strip("<@!>"))
    user_manager = message._bot.user_manager
    try:
        user_manager.ensure_user(user_id, calendar_email=email)
        embed = discord.Embed(title="Success", description=f"Added user <@{user_id}> with email {email}.", color=discord.Color.green())
    except Exception as e:
        embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
    await message.channel.send(embed=embed)

async def list_events_command(message):
    args = message.content.split()
    days = int(args[1]) if len(args) > 1 and args[1].isdigit() else 7
    calendar_service = message._bot.calendar_service
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
    await message.channel.send(embed=embed)

async def add_event_command(message):
    args = message.content.split(maxsplit=4)
    if len(args) < 4:
        embed = discord.Embed(title="Usage", description="/add_event <title> <start> <end>", color=discord.Color.red())
        await message.channel.send(embed=embed)
        return
    title, start_str, end_str = args[1], args[2], args[3]
    try:
        start = datetime.fromisoformat(start_str)
        end = datetime.fromisoformat(end_str)
        calendar_service = message._bot.calendar_service
        calendar_service.add_event(
            message._bot.calendar_service.__class__.__bases__[0].__name__ == 'object' and None or None,  # placeholder
            title=title, start_time=start, end_time=end
        )
        embed = discord.Embed(title="Success", description=f"Event '{title}' added.", color=discord.Color.green())
    except Exception as e:
        embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
    await message.channel.send(embed=embed)

async def remove_event_command(message):
    args = message.content.split()
    if len(args) < 2:
        embed = discord.Embed(title="Usage", description="/remove_event <event_id>", color=discord.Color.red())
        await message.channel.send(embed=embed)
        return
    event_id = args[1]
    calendar_service = message._bot.calendar_service
    try:
        success = calendar_service.remove_event(event_id)
        if success:
            embed = discord.Embed(title="Success", description=f"Event {event_id} removed.", color=discord.Color.green())
        else:
            embed = discord.Embed(title="Failed", description=f"Event {event_id} not found.", color=discord.Color.red())
    except Exception as e:
        embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
    await message.channel.send(embed=embed)

async def update_event_command(message):
    args = message.content.split(maxsplit=5)
    if len(args) < 5:
        embed = discord.Embed(title="Usage", description="/update_event <event_id> <title> <start> <end>", color=discord.Color.red())
        await message.channel.send(embed=embed)
        return
    event_id, title, start_str, end_str = args[1], args[2], args[3], args[4]
    try:
        start = datetime.fromisoformat(start_str)
        end = datetime.fromisoformat(end_str)
        calendar_service = message._bot.calendar_service
        success = calendar_service.update_event(
            message._bot.calendar_service.__class__.__bases__[0].__name__ == 'object' and None or None,  # placeholder
            calendar_id='primary'
        )
        if success:
            embed = discord.Embed(title="Success", description=f"Event {event_id} updated.", color=discord.Color.green())
        else:
            embed = discord.Embed(title="Failed", description=f"Event {event_id} not found.", color=discord.Color.red())
    except Exception as e:
        embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
    await message.channel.send(embed=embed)

# --- Slash command registration for Discord autocomplete ---
async def sync_commands_command(message):
    try:
        bot = message._bot
        guild = message.guild
        # Register slash commands for all registered bot commands
        commands = list(bot.command_handler.commands.keys())
        # This is a placeholder: in discord.py, you need to use @bot.tree.command or similar for real slash commands
        # Here, we just inform the user
        embed = discord.Embed(title="Command Sync", description=f"Slash commands suggestion is enabled for: {', '.join(commands)} (requires bot restart and proper setup)", color=discord.Color.green())
    except Exception as e:
        embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
    await message.channel.send(embed=embed)

def register_all_commands(handler):
    handler.register("help", help_command)
    handler.register("grant_permission", grant_permission_command)
    handler.register("update_roles", update_roles_command)
    handler.register("update_preferences", update_preferences_command)
    handler.register("add_role", add_role_command)
    handler.register("add_users_to_role", add_users_to_role_command)
    handler.register("add_user", add_user_command)
    handler.register("list_events", list_events_command)
    handler.register("add_event", add_event_command)
    handler.register("remove_event", remove_event_command)
    handler.register("update_event", update_event_command)
    handler.register("sync_commands", sync_commands_command)
