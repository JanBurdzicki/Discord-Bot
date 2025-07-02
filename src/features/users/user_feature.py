"""User feature implementation."""
import discord
from discord import app_commands
from typing import Optional
import json
from ...core.base_feature import BaseFeature
from .services.user_service import UserService

# Import all user command classes
from .commands.user_commands import (
    UserStatusCommand,
    SetPreferenceCommand,
    GetPreferenceCommand,
    RemovePreferenceCommand,
    ListPreferencesCommand,
    ClearPreferencesCommand,
    UpdateCalendarEmailCommand,
    ManageUserRoleCommand,
    UserAdminInfoCommand,
    UpdateRolesCommand
)

class UserFeature(BaseFeature):
    """Feature for managing user profiles and settings."""

    name = "user"

    def __init__(self, bot):
        super().__init__(bot)
        self.user_service = UserService(bot)

        # Register user service in container
        bot.services.register_singleton("user_service", self.user_service)

    def register_commands(self):
        """Register all user management commands."""

        # User Status Command
        @self.bot.tree.command(name="user_status", description="Check your current user status and preferences")
        @app_commands.describe(user="User to check (admin only)")
        async def user_status(interaction: discord.Interaction, user: Optional[discord.Member] = None):
            command = UserStatusCommand(self.bot, self.bot.services)
            await command.handle(interaction, user=user)

        # Set Preference Command
        @self.bot.tree.command(name="set_preference", description="Set a preference value")
        @app_commands.describe(key="Preference key", value="Preference value")
        async def set_preference(interaction: discord.Interaction, key: str, value: str):
            command = SetPreferenceCommand(self.bot, self.bot.services)
            await command.handle(interaction, key=key, value=value)

        # Get Preference Command
        @self.bot.tree.command(name="get_preference", description="Get a preference value")
        @app_commands.describe(key="Preference key")
        async def get_preference(interaction: discord.Interaction, key: str):
            command = GetPreferenceCommand(self.bot, self.bot.services)
            await command.handle(interaction, key=key)

        # Remove Preference Command
        @self.bot.tree.command(name="remove_preference", description="Remove a preference")
        @app_commands.describe(key="Preference key")
        async def remove_preference(interaction: discord.Interaction, key: str):
            command = RemovePreferenceCommand(self.bot, self.bot.services)
            await command.handle(interaction, key=key)

        # List Preferences Command
        @self.bot.tree.command(name="list_preferences", description="List all your preferences")
        async def list_preferences(interaction: discord.Interaction):
            command = ListPreferencesCommand(self.bot, self.bot.services)
            await command.handle(interaction)

        # Clear Preferences Command
        @self.bot.tree.command(name="clear_preferences", description="Clear all your preferences")
        async def clear_preferences(interaction: discord.Interaction):
            command = ClearPreferencesCommand(self.bot, self.bot.services)
            await command.handle(interaction)

        # Update Calendar Email Command
        @self.bot.tree.command(name="update_calendar_email", description="Update your calendar email address")
        @app_commands.describe(email="Your Google Calendar email address")
        async def update_calendar_email(interaction: discord.Interaction, email: str):
            command = UpdateCalendarEmailCommand(self.bot, self.bot.services)
            await command.handle(interaction, email=email)

        # Manage User Role Command (Admin only)
        @self.bot.tree.command(name="manage_user_role", description="Add or remove a role from a user (Admin only)")
        @app_commands.describe(
            user="User to manage",
            role="Role name",
            action="Action to take"
        )
        @app_commands.choices(action=[
            app_commands.Choice(name="Add", value="add"),
            app_commands.Choice(name="Remove", value="remove")
        ])
        async def manage_user_role(
            interaction: discord.Interaction,
            user: discord.Member,
            role: str,
            action: app_commands.Choice[str] = "add"
        ):
            command = ManageUserRoleCommand(self.bot, self.bot.services)
            action_value = action.value if hasattr(action, 'value') else action
            await command.handle(interaction, user=user, role=role, action=action_value)

        # User Admin Info Command (Admin only)
        @self.bot.tree.command(name="user_admin_info", description="Get detailed user information (Admin only)")
        @app_commands.describe(user="User to get info for")
        async def user_admin_info(interaction: discord.Interaction, user: discord.Member):
            command = UserAdminInfoCommand(self.bot, self.bot.services)
            await command.handle(interaction, user=user)

        # Update Roles Command (Admin only)
        @self.bot.tree.command(name="update_roles", description="Update roles for a user (Admin only)")
        @app_commands.describe(user="User to update", roles="Comma-separated role names")
        async def update_roles(interaction: discord.Interaction, user: discord.Member, roles: str):
            command = UpdateRolesCommand(self.bot, self.bot.services)
            await command.handle(interaction, user=user, roles=roles)

    def register_listeners(self):
        """Register user-related event listeners."""

        @self.bot.event
        async def on_member_join(member):
            """Handle new member joining - create user profile"""
            await self.user_service.ensure_user(member.id)

        @self.bot.event
        async def on_member_update(before, after):
            """Handle member updates - sync roles if needed"""
            if before.roles != after.roles:
                # Update user roles in database
                role_names = [role.name for role in after.roles if not role.is_default()]
                await self.user_service.update_roles(after.id, role_names)

    async def on_feature_load(self):
        """Called when the feature is loaded"""
        print(f"👤 User feature loaded with {len(self.bot.tree.get_commands())} commands")

    async def on_feature_unload(self):
        """Called when the feature is unloaded"""
        print("👤 User feature unloaded")