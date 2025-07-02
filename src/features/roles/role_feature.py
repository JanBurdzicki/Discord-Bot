"""Role Management Feature"""

import discord
from discord import app_commands
from src.core.base_feature import BaseFeature
from .commands.role_commands import RoleCommands


class RoleFeature(BaseFeature):
    """Feature for managing Discord roles and permissions"""

    def __init__(self, bot):
        super().__init__(bot)
        # Use bot.services to get the service container
        self.commands = RoleCommands(bot, bot.services)

    async def setup(self):
        """Initialize the role management system"""
        pass

    async def cleanup(self):
        """Cleanup resources"""
        pass

    def register_commands(self):
        """Register all role management commands"""
        commands = [
            self.commands.create_role_command(),
            self.commands.delete_role_command(),
            self.commands.list_role_permissions_command(),
            self.commands.add_role_permission_command(),
            self.commands.remove_role_permission_command(),
            self.commands.list_role_members_command(),
            self.commands.add_user_to_role_command(),
            self.commands.remove_user_from_role_command(),
            self.commands.list_user_roles_command(),
            self.commands.list_all_roles_command(),
        ]

        for command in commands:
            self.bot.tree.add_command(command)