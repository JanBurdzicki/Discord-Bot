import discord
from datetime import datetime, timedelta
from sqlalchemy.future import select
from db.session import AsyncSessionLocal
from db.models import UserToken
from services.calendar_service import CalendarService
import os
from dotenv import load_dotenv

load_dotenv()
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI')
OAUTH2_URL = "https://accounts.google.com/o/oauth2/v2/auth"
SCOPES = "https://www.googleapis.com/auth/calendar"

async def link_calendar_command(interaction: discord.Interaction):
    state = str(interaction.user.id)
    url = f"{OAUTH2_URL}?client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&response_type=code&scope={SCOPES}&access_type=offline&state={state}"
    try:
        await interaction.user.send(f"Click this link to link your Google Calendar: {url}")
        embed = discord.Embed(title="Check your DMs!", description="A link to link your Google Calendar has been sent.", color=discord.Color.green())
    except Exception:
        embed = discord.Embed(title="Error", description="Could not send DM. Please enable DMs from server members.", color=discord.Color.red())
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def delete_calendar_token_command(interaction: discord.Interaction):
    user_id = interaction.user.id
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserToken).where(UserToken.discord_id == user_id))
        token = result.scalar_one_or_none()
        if token:
            await session.delete(token)
            await session.commit()
            embed = discord.Embed(title="Token Deleted", description="Your Google Calendar token has been deleted.", color=discord.Color.green())
        else:
            embed = discord.Embed(title="No Token", description="No Google Calendar token found.", color=discord.Color.orange())
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def update_calendar_token_command(interaction: discord.Interaction):
    await link_calendar_command(interaction)

async def find_free_slots_command(interaction: discord.Interaction, start: str, end: str, duration: int = 30):
    # Only the requesting user sees the results
    users = [interaction.user] + list(interaction.user.mentioned_in(interaction.channel.history(limit=10)))
    # For demo, just use the command author
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    async with AsyncSessionLocal() as session:
        # Get tokens for all users
        result = await session.execute(select(UserToken).where(UserToken.discord_id == interaction.user.id))
        token = result.scalar_one_or_none()
        if not token:
            embed = discord.Embed(title="Error", description="You must link your Google Calendar first.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        # For demo, just check the requesting user's calendar
        cal = CalendarService(token.token_data)
        busy = cal.get_freebusy(interaction.user.name, start_dt, end_dt)
        # Find free slots
        slots = []
        current = start_dt
        while current + timedelta(minutes=duration) <= end_dt:
            slot_busy = False
            for b in busy:
                busy_start = datetime.fromisoformat(b['start'][:-1])
                busy_end = datetime.fromisoformat(b['end'][:-1])
                if not (current + timedelta(minutes=duration) <= busy_start or current >= busy_end):
                    slot_busy = True
                    break
            if not slot_busy:
                slots.append(current.strftime('%Y-%m-%d %H:%M'))
            current += timedelta(minutes=duration)
        if not slots:
            embed = discord.Embed(title="No Free Slots", description="No common free slots found.", color=discord.Color.orange())
        else:
            embed = discord.Embed(title="Free Slots", description="\n".join(slots), color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def reserve_slot_command(interaction: discord.Interaction, title: str, start: str, end: str):
    user_id = interaction.user.id
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserToken).where(UserToken.discord_id == user_id))
        token = result.scalar_one_or_none()
        if not token:
            embed = discord.Embed(title="Error", description="You must link your Google Calendar first.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        cal = CalendarService(token.token_data)
        event_id = cal.create_event(interaction.user.name, title, start_dt, end_dt)
        embed = discord.Embed(title="Event Reserved", description=f"Event '{title}' reserved in your calendar.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)
