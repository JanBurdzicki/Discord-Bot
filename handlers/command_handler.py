from typing import Callable, Dict, Optional, Any
import discord
from utils.permission_manager import PermissionManager
from handlers.custom_command_manager import CustomCommandManager
from db.user_manager import UserManager
from db.models import UserProfile
from handlers.bot_commands import register_all_commands

class CommandHandler:
    def __init__(self, permission_manager: PermissionManager, custom_command_manager: CustomCommandManager, user_manager: UserManager):
        self.commands: Dict[str, Callable[[discord.Message], Any]] = {}
        self.permission_manager = permission_manager
        self.custom_command_manager = custom_command_manager
        self.user_manager = user_manager
        register_all_commands(self)

    def register(self, name: str, func: Callable[[discord.Message], Any]):
        self.commands[name] = func

    async def execute(self, message: discord.Message, bot_instance=None):
        if not message.content.startswith('/'):
            return
        # Patch message with a reference to the bot instance for command access
        try:
            setattr(message, '_bot', bot_instance)
        except Exception:
            pass
        command_name, *args = message.content[1:].split()
        if command_name in self.commands:
            # Fetch UserProfile from UserManager
            user_profile = self.user_manager.get_user(message.author.id)
            if not user_profile:
                # Create a default UserProfile if not found
                user_profile = UserProfile(
                    discord_id=message.author.id,
                    calendar_email="",
                    roles=[role.name for role in getattr(message.author, 'roles', [])],
                )
                self.user_manager.users[message.author.id] = user_profile
            # Check permissions
            if not self.permission_manager.can_execute(user_profile, command_name):
                await message.channel.send("You do not have permission to run this command.")
                return
            await self.commands[command_name](message)
        else:
            # check custom commands
            custom_cmd = self.custom_command_manager.get_command(command_name)
            if custom_cmd:
                # Here you can safely exec custom_cmd or eval after sandboxing (simplified)
                await message.channel.send(f"Custom command `{command_name}` executed.")
            else:
                await message.channel.send("Unknown command.")
