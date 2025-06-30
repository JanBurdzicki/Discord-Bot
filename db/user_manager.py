import asyncio
from sqlalchemy.future import select
from .models import UserProfile
from .session import AsyncSessionLocal

class UserManager:
    def __init__(self):
        pass

    async def get_user(self, discord_id: int) -> UserProfile:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(UserProfile).where(UserProfile.discord_id == discord_id))
            return result.scalar_one_or_none()

    async def ensure_user(self, discord_id: int, calendar_email: str = "", roles: list = None) -> UserProfile:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(UserProfile).where(UserProfile.discord_id == discord_id))
            user = result.scalar_one_or_none()

            if not user:
                user = UserProfile(
                    discord_id=discord_id,
                    calendar_email=calendar_email,
                    roles=roles or [],
                    preferences={}
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)

            return user

    async def add_user(self, user: UserProfile):
        async with AsyncSessionLocal() as session:
            session.add(user)
            await session.commit()

    async def update_preferences(self, discord_id: int, prefs: dict):
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(UserProfile).where(UserProfile.discord_id == discord_id))
            user = result.scalar_one_or_none()

            if not user:
                user = UserProfile(discord_id=discord_id, preferences=prefs, roles=[])
                session.add(user)
            else:
                if not user.preferences:
                    user.preferences = {}
                user.preferences.update(prefs)

            await session.commit()

    async def update_roles(self, discord_id: int, roles: list):
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(UserProfile).where(UserProfile.discord_id == discord_id))
            user = result.scalar_one_or_none()

            if not user:
                user = UserProfile(discord_id=discord_id, roles=roles, preferences={})
                session.add(user)
            else:
                user.roles = roles

            await session.commit()

    async def assign_roles(self, user: UserProfile):
        # Logic to assign roles based on activity, etc.
        pass
