import discord
from discord import app_commands
from db.models import UserProfile, Poll, Vote, UserToken
from datetime import datetime, timedelta
import uuid
import requests

# --- Autocomplete helpers ---
async def command_autocomplete(interaction: discord.Interaction, current: str):
    commands = ["help", "grant_permission", "update_roles", "update_preferences", "add_role", "add_users_to_role", "add_user", "list_events", "add_event", "remove_event", "update_event", "remind", "create_poll", "create_advanced_poll", "vote_poll", "poll_results", "list_polls", "delete_poll", "link_calendar", "delete_calendar_token", "update_calendar_token"]
    return [app_commands.Choice(name=cmd, value=cmd) for cmd in commands if current.lower() in cmd.lower()]

async def role_autocomplete(interaction: discord.Interaction, current: str):
    roles = [role.name for role in interaction.guild.roles]
    return [app_commands.Choice(name=role, value=role) for role in roles if current.lower() in role.lower()]

# --- Google Calendar OAuth2 Placeholders ---
OAUTH2_URL = "https://accounts.google.com/o/oauth2/v2/auth"
CLIENT_ID = "YOUR_CLIENT_ID"
REDIRECT_URI = "YOUR_REDIRECT_URI"
SCOPES = "https://www.googleapis.com/auth/calendar"

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
            "/link_calendar",
            "/delete_calendar_token",
            "/update_calendar_token",
            "/create_poll <question> <options> <duration>",
            "/create_advanced_poll <question> <options> <multi>",
            "/vote_poll <poll_id> <option_index>",
            "/poll_results <poll_id>",
            "/list_polls",
            "/delete_poll <poll_id>",
            "/stats",
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

    @tree.command(name="link_calendar", description="Link your Google Calendar account")
    async def link_calendar_command(interaction: discord.Interaction):
        # Generate a unique state for the user
        state = str(uuid.uuid4())
        # Build the OAuth2 URL (placeholder)
        url = f"{OAUTH2_URL}?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope={SCOPES}&access_type=offline&state={state}"
        try:
            await interaction.user.send(f"Click this link to link your Google Calendar: {url}")
            embed = discord.Embed(title="Check your DMs!", description="A link to link your Google Calendar has been sent.", color=discord.Color.green())
        except Exception:
            embed = discord.Embed(title="Error", description="Could not send DM. Please enable DMs from server members.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="delete_calendar_token", description="Delete your Google Calendar token")
    async def delete_calendar_token_command(interaction: discord.Interaction):
        user_id = interaction.user.id
        if hasattr(bot, 'user_tokens') and user_id in bot.user_tokens:
            del bot.user_tokens[user_id]
            embed = discord.Embed(title="Token Deleted", description="Your Google Calendar token has been deleted.", color=discord.Color.green())
        else:
            embed = discord.Embed(title="No Token", description="No Google Calendar token found.", color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="update_calendar_token", description="Update your Google Calendar token")
    async def update_calendar_token_command(interaction: discord.Interaction):
        # For demo, just call link_calendar again
        await link_calendar_command(interaction)

    # --- Simple Polls ---
    if not hasattr(bot, 'polls'):
        bot.polls = {}
    if not hasattr(bot, 'user_tokens'):
        bot.user_tokens = {}

    @tree.command(name="create_poll", description="Create a simple poll (reactions)")
    @app_commands.describe(question="Poll question", options="Comma-separated options", duration="Duration in minutes")
    async def create_poll_command(interaction: discord.Interaction, question: str, options: str, duration: int = 5):
        poll_id = str(uuid.uuid4())
        opts = [opt.strip() for opt in options.split(",") if opt.strip()]
        poll = Poll(poll_id, question, opts, interaction.user.id)
        bot.polls[poll_id] = poll
        bot.stats_module.log_poll_creation(interaction.user.id, poll_id)
        embed = discord.Embed(title="Poll Created", description=question, color=discord.Color.blue())
        for idx, opt in enumerate(opts):
            embed.add_field(name=f"{chr(0x1F1E6+idx)}", value=opt, inline=False)
        msg = await interaction.channel.send(embed=embed)
        for idx in range(len(opts)):
            await msg.add_reaction(chr(0x1F1E6+idx))
        embed2 = discord.Embed(title="Poll Active!", description=f"Poll ID: {poll_id}\nVote by reacting below! Ends in {duration} minutes.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed2, ephemeral=True)
        # Schedule poll close (not persistent across restarts)
        async def close_poll():
            await discord.utils.sleep_until(datetime.utcnow() + timedelta(minutes=duration))
            poll.active = False
            await interaction.channel.send(f"Poll {poll_id} closed!")
        bot.loop.create_task(close_poll())

    # --- Advanced Polls (StrawPoll API) ---
    @tree.command(name="create_advanced_poll", description="Create an advanced poll (StrawPoll)")
    @app_commands.describe(question="Poll question", options="Comma-separated options", multi="Allow multiple answers?")
    async def create_advanced_poll_command(interaction: discord.Interaction, question: str, options: str, multi: bool = False):
        opts = [opt.strip() for opt in options.split(",") if opt.strip()]
        # StrawPoll API (placeholder, no API key required for demo)
        data = {"title": question, "options": opts, "multi": multi}
        resp = requests.post("https://strawpoll.com/api/poll", json=data)
        if resp.status_code == 200:
            poll_data = resp.json()
            poll_id = poll_data.get("id")
            url = poll_data.get("url", f"https://strawpoll.com/{poll_id}")
            poll = Poll(poll_id, question, opts, interaction.user.id, is_advanced=True, external_id=poll_id)
            bot.polls[poll_id] = poll
            bot.stats_module.log_poll_creation(interaction.user.id, poll_id)
            embed = discord.Embed(title="Advanced Poll Created", description=f"[Vote here]({url})", color=discord.Color.purple())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(title="Error", description="Failed to create StrawPoll.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="vote_poll", description="Vote in a simple poll")
    @app_commands.describe(poll_id="Poll ID", option_index="Option number (starting from 1)")
    async def vote_poll_command(interaction: discord.Interaction, poll_id: str, option_index: int):
        poll = bot.polls.get(poll_id)
        if not poll or not poll.active:
            embed = discord.Embed(title="Error", description="Poll not found or closed.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        poll.votes[interaction.user.id] = option_index - 1
        vote = Vote(poll_id, interaction.user.id, option_index - 1, datetime.utcnow())
        bot.stats_module.log_vote(vote)
        embed = discord.Embed(title="Vote Registered", description=f"You voted for option {option_index} in poll {poll_id}.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="poll_results", description="Show poll results with visualization")
    @app_commands.describe(poll_id="Poll ID")
    async def poll_results_command(interaction: discord.Interaction, poll_id: str):
        poll = bot.polls.get(poll_id)
        if not poll:
            embed = discord.Embed(title="Error", description="Poll not found.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        # Count votes
        counts = [0] * len(poll.options)
        for v in poll.votes.values():
            if 0 <= v < len(counts):
                counts[v] += 1
        # Visualization with QuickChart
        chart_url = f"https://quickchart.io/chart?c={{type:'bar',data:{{labels:{poll.options},datasets:[{{label:'Votes',data:{counts}}}]}}}}"
        embed = discord.Embed(title="Poll Results", description=poll.question, color=discord.Color.blue())
        for idx, opt in enumerate(poll.options):
            embed.add_field(name=opt, value=f"{counts[idx]} votes", inline=False)
        embed.set_image(url=chart_url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="list_polls", description="List all active polls")
    async def list_polls_command(interaction: discord.Interaction):
        active_polls = [p for p in bot.polls.values() if p.active]
        if not active_polls:
            embed = discord.Embed(title="No Active Polls", color=discord.Color.orange())
        else:
            desc = "\n".join([f"ID: {p.poll_id} | Q: {p.question}" for p in active_polls])
            embed = discord.Embed(title="Active Polls", description=desc, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="delete_poll", description="Delete a poll")
    @app_commands.describe(poll_id="Poll ID")
    async def delete_poll_command(interaction: discord.Interaction, poll_id: str):
        poll = bot.polls.get(poll_id)
        if not poll:
            embed = discord.Embed(title="Error", description="Poll not found.", color=discord.Color.red())
        elif poll.creator_id != interaction.user.id and interaction.user.id != bot.owner_id:
            embed = discord.Embed(title="Permission Denied", description="Only the poll creator or server owner can delete this poll.", color=discord.Color.red())
        else:
            del bot.polls[poll_id]
            embed = discord.Embed(title="Poll Deleted", description=f"Poll {poll_id} deleted.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="stats", description="Show voting and poll stats")
    async def stats_command(interaction: discord.Interaction):
        stats = bot.stats_module.get_stats_summary()
        desc = f"Total Votes: {stats['total_votes']}\nTotal Polls: {stats['total_polls']}\n"
        desc += "Top Voters:\n" + "\n".join([f"<@{uid}>: {count}" for uid, count in stats['top_voters']])
        desc += "\nTop Poll Creators:\n" + "\n".join([f"<@{uid}>: {count}" for uid, count in stats['top_poll_creators']])
        embed = discord.Embed(title="Stats", description=desc, color=discord.Color.gold())
        await interaction.response.send_message(embed=embed, ephemeral=True)
