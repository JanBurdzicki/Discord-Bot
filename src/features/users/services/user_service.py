"""
Core user service that handles all user-related operations.
Provides profile management, preferences, and role functionality.
"""

from typing import Optional, Any, Dict, List
import discord
from sqlalchemy.future import select

from src.database.session import AsyncSessionLocal
from ..models.user_models import UserProfile
from src.core.builders import EmbedBuilder

class UserService:
    """
    Core service for managing user profiles and preferences.
    Handles user data, preferences, and role management.
    """

    def __init__(self, bot: discord.Client):
        self.bot = bot

    async def init(self) -> None:
        """Initialize the user service"""
        pass

    async def cleanup(self) -> None:
        """Cleanup service resources"""
        pass

    # ========== User Profile Management ==========

    async def get_user(self, discord_id: int) -> Optional[UserProfile]:
        """Get user by Discord ID"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserProfile).where(UserProfile.discord_id == discord_id)
            )
            return result.scalar_one_or_none()

    async def ensure_user(
        self,
        discord_id: int,
        calendar_email: str = "",
        roles: Optional[List[str]] = None
    ) -> UserProfile:
        """Ensure user exists, create if necessary"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserProfile).where(UserProfile.discord_id == discord_id)
            )
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
            result = await session.execute(
                select(UserProfile).where(UserProfile.discord_id == discord_id)
            )
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

    # ========== Preference Management ==========

    async def set_preference(self, discord_id: int, key: str, value: Any) -> bool:
        """Set a specific preference key for user"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserProfile).where(UserProfile.discord_id == discord_id)
            )
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
            result = await session.execute(
                select(UserProfile).where(UserProfile.discord_id == discord_id)
            )
            user = result.scalar_one_or_none()

            if not user or not user.preferences or key not in user.preferences:
                return False

            del user.preferences[key]
            await session.commit()
            return True

    async def clear_preferences(self, discord_id: int) -> bool:
        """Clear all preferences for user"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserProfile).where(UserProfile.discord_id == discord_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                return False

            user.preferences = {}
            await session.commit()
            return True

    # ========== Role Management ==========

    async def update_roles(self, discord_id: int, roles: List[str]) -> bool:
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

    # ========== User Status ==========

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

    # ========== Discord Role Sync ==========

    async def sync_discord_roles(self, member: discord.Member, roles: List[str]) -> None:
        """Sync user roles with Discord server roles"""
        guild = member.guild

        # Remove all bot-managed roles first
        bot_roles = [role for role in member.roles if role.name in roles]
        await member.remove_roles(*bot_roles, reason="Role sync")

        # Add the new roles
        for role_name in roles:
            discord_role = discord.utils.get(guild.roles, name=role_name)
            if not discord_role:
                discord_role = await guild.create_role(name=role_name, reason="Created by bot")
            if discord_role not in member.roles:
                await member.add_roles(discord_role, reason="Role sync")

    # ========== Embed Builders ==========

    def build_user_status_embed(self, user: discord.Member, status: Dict[str, Any]) -> discord.Embed:
        """Build embed for user status display"""
        if not status['exists']:
            return EmbedBuilder()\
                .set_title("❌ User Not Found")\
                .set_description(f"{user.display_name} is not registered in the system.")\
                .set_color(0xff0000)\
                .add_field("💡 Tip", "Use any bot command to automatically create your profile!", inline=False)\
                .build()

        embed = EmbedBuilder()\
            .set_title(f"👤 User Status - {user.display_name}")\
            .set_color(0x3498db)\
            .add_field("📧 Calendar Email", status['calendar_email'], inline=True)\
            .add_field("🔧 Preferences", f"{status['preference_count']} set", inline=True)\
            .add_field("🏷️ Roles", f"{status['role_count']} assigned", inline=True)

        # Show roles if any
        if status['roles']:
            roles_text = ', '.join(status['roles'][:5])  # Show first 5 roles
            if len(status['roles']) > 5:
                roles_text += f" (+{len(status['roles']) - 5} more)"
            embed.add_field("📋 Your Roles", roles_text, inline=False)

        # Show some preferences if any
        if status['preferences']:
            prefs_preview = []
            for key, value in list(status['preferences'].items())[:3]:  # Show first 3
                prefs_preview.append(f"**{key}:** {str(value)[:50]}")
            if len(status['preferences']) > 3:
                prefs_preview.append(f"...and {len(status['preferences']) - 3} more")
            embed.add_field("⚙️ Preferences Preview", '\n'.join(prefs_preview), inline=False)

        return embed.build()

    def build_admin_user_info_embed(self, user: discord.Member, status: Dict[str, Any]) -> discord.Embed:
        """Build embed for admin user info display"""
        embed = EmbedBuilder()\
            .set_title(f"🔍 Admin User Info - {user.display_name}")\
            .set_color(0x3498db)

        if not status['exists']:
            embed.set_description("User is not registered in the system.")
            embed.set_color(0xff0000)
        else:
            embed.add_field("📧 Calendar Email", status['calendar_email'], inline=True)\
                .add_field("🔧 Preferences", str(status['preference_count']), inline=True)\
                .add_field("🏷️ Roles", str(status['role_count']), inline=True)

            if status['roles']:
                embed.add_field("📋 Assigned Roles", ', '.join(status['roles']), inline=False)

            if status['preferences']:
                prefs_text = ""
                for key, value in status['preferences'].items():
                    value_str = str(value)[:50]
                    prefs_text += f"**{key}:** {value_str}\n"
                embed.add_field("⚙️ All Preferences", prefs_text[:1024], inline=False)

        embed.add_field(
            "👤 Discord Info",
            f"**ID:** {user.id}\n**Created:** {user.created_at.strftime('%Y-%m-%d')}",
            inline=False
        )

        return embed.build()