import asyncio
from sqlalchemy.future import select
from .models import UserProfile
from .session import AsyncSessionLocal
from typing import Optional, Any, Dict

class UserManager:
    def __init__(self):
        pass

    async def get_user(self, discord_id: int) -> Optional[UserProfile]:
        """Get user by Discord ID"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(UserProfile).where(UserProfile.discord_id == discord_id))
            return result.scalar_one_or_none()

    async def ensure_user(self, discord_id: int, calendar_email: str = "", roles: list = None) -> UserProfile:
        """Ensure user exists, create if necessary"""
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

    async def update_user_info(self, discord_id: int, **kwargs) -> bool:
        """Update user information (calendar_email, roles, etc.)"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(UserProfile).where(UserProfile.discord_id == discord_id))
            user = result.scalar_one_or_none()

            if not user:
                return False

            # Update allowed fields
            allowed_fields = ['calendar_email', 'roles']
            for field, value in kwargs.items():
                if field in allowed_fields and hasattr(user, field):
                    setattr(user, field, value)

            await session.commit()
            return True

    async def set_preference(self, discord_id: int, key: str, value: Any) -> bool:
        """Set a specific preference key for user"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(UserProfile).where(UserProfile.discord_id == discord_id))
            user = result.scalar_one_or_none()

            if not user:
                # Create user if doesn't exist
                user = UserProfile(discord_id=discord_id, preferences={key: value}, roles=[])
                session.add(user)
            else:
                if not user.preferences:
                    user.preferences = {}
                user.preferences[key] = value

            await session.commit()
            return True

    async def get_preference(self, discord_id: int, key: str, default: Any = None) -> Any:
        """Get a specific preference value for user"""
        user = await self.get_user(discord_id)
        if not user or not user.preferences:
            return default
        return user.preferences.get(key, default)

    async def remove_preference(self, discord_id: int, key: str) -> bool:
        """Remove a specific preference key for user"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(UserProfile).where(UserProfile.discord_id == discord_id))
            user = result.scalar_one_or_none()

            if not user or not user.preferences or key not in user.preferences:
                return False

            del user.preferences[key]
            await session.commit()
            return True

    async def get_user_status(self, discord_id: int) -> Dict[str, Any]:
        """Get complete user status including preferences, roles, etc."""
        user = await self.get_user(discord_id)
        if not user:
            return {
                'exists': False,
                'discord_id': discord_id,
                'calendar_email': None,
                'roles': [],
                'preferences': {},
                'preference_count': 0
            }

        return {
            'exists': True,
            'discord_id': user.discord_id,
            'calendar_email': user.calendar_email or 'Not set',
            'roles': user.roles or [],
            'preferences': user.preferences or {},
            'preference_count': len(user.preferences or {}),
            'role_count': len(user.roles or [])
        }

    async def has_preference(self, discord_id: int, key: str) -> bool:
        """Check if user has a specific preference set"""
        user = await self.get_user(discord_id)
        return user and user.preferences and key in user.preferences

    async def update_roles(self, discord_id: int, roles: list) -> bool:
        """Update user roles"""
        return await self.update_user_info(discord_id, roles=roles)

    async def add_role(self, discord_id: int, role: str) -> bool:
        """Add a single role to user"""
        user = await self.get_user(discord_id)
        if not user:
            await self.ensure_user(discord_id, roles=[role])
            return True

        if not user.roles:
            user.roles = []

        if role not in user.roles:
            user.roles.append(role)
            return await self.update_user_info(discord_id, roles=user.roles)
        return False

    async def remove_role(self, discord_id: int, role: str) -> bool:
        """Remove a single role from user"""
        user = await self.get_user(discord_id)
        if not user or not user.roles or role not in user.roles:
            return False

        user.roles.remove(role)
        return await self.update_user_info(discord_id, roles=user.roles)

    async def clear_preferences(self, discord_id: int) -> bool:
        """Clear all preferences for user"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(UserProfile).where(UserProfile.discord_id == discord_id))
            user = result.scalar_one_or_none()

            if not user:
                return False

            user.preferences = {}
            await session.commit()
            return True
