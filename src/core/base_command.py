"""
Base command system using Template Method pattern.
Provides consistent command execution flow with extensible validation and response handling.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional, List
import discord
import traceback
from datetime import datetime

class PermissionLevel(Enum):
    """Permission levels for commands"""
    PUBLIC = "public"
    USER = "user"
    ADMIN = "admin"
    OWNER = "owner"

class CommandResult:
    """Wrapper for command execution results"""
    def __init__(self, success: bool = True, data: Any = None, message: str = "", error: str = ""):
        self.success = success
        self.data = data
        self.message = message
        self.error = error
        self.timestamp = datetime.utcnow()

class BaseCommand(ABC):
    """
    Base class for all bot commands using Template Method pattern.
    Defines the common execution flow while allowing subclasses to customize behavior.
    """

    def __init__(self, permission_level: PermissionLevel = PermissionLevel.PUBLIC, ephemeral: bool = False):
        self.permission_level = permission_level
        self.ephemeral = ephemeral
        self.command_name = self.__class__.__name__.replace('Command', '').lower()

    async def execute(self, interaction: discord.Interaction, **kwargs) -> None:
        """
        Template method - defines the common execution flow.
        This method should not be overridden by subclasses.
        """
        try:
            # Step 1: Pre-execution hook
            await self.pre_execute(interaction, **kwargs)

            # Step 2: Check permissions
            if not await self._check_permissions(interaction):
                return await self._send_permission_error(interaction)

            # Step 3: Validate input
            validation_result = await self.validate_input(interaction, **kwargs)
            if not validation_result.get('valid', True):
                return await self._send_validation_error(interaction, validation_result.get('errors', []))

            # Step 4: Process command (implemented by subclasses)
            result = await self.process_command(interaction, validation_result.get('data', kwargs))

            # Step 5: Send response
            await self.send_response(interaction, result)

            # Step 6: Post-execution hook
            await self.post_execute(interaction, result)

        except Exception as e:
            await self._handle_command_error(interaction, e)

    @abstractmethod
    async def process_command(self, interaction: discord.Interaction, data: Dict[str, Any]) -> CommandResult:
        """
        Subclasses implement the actual business logic here.
        Should return a CommandResult object.
        """
        pass

    async def validate_input(self, interaction: discord.Interaction, **kwargs) -> Dict[str, Any]:
        """
        Override this method for custom input validation.
        Should return a dict with 'valid', 'data', and optionally 'errors' keys.
        """
        return {'valid': True, 'data': kwargs}

    async def send_response(self, interaction: discord.Interaction, result: CommandResult) -> None:
        """
        Override this method for custom response handling.
        Default implementation sends a simple success/error embed.
        """
        from .builders import EmbedBuilder

        if result.success:
            embed = EmbedBuilder().success("Success", result.message or "Operation completed successfully").build()
        else:
            embed = EmbedBuilder().error("Error", result.error or "An error occurred").build()

        await interaction.response.send_message(embed=embed, ephemeral=self.ephemeral)

    async def pre_execute(self, interaction: discord.Interaction, **kwargs) -> None:
        """Hook called before command execution. Override for custom behavior."""
        pass

    async def post_execute(self, interaction: discord.Interaction, result: CommandResult) -> None:
        """Hook called after successful command execution. Override for custom behavior."""
        pass

    async def _check_permissions(self, interaction: discord.Interaction) -> bool:
        """Internal permission checking logic"""
        if self.permission_level == PermissionLevel.PUBLIC:
            return True
        elif self.permission_level == PermissionLevel.USER:
            # Basic user check - just needs to be in a guild
            return interaction.guild is not None
        elif self.permission_level == PermissionLevel.ADMIN:
            return interaction.user.guild_permissions.administrator
        elif self.permission_level == PermissionLevel.OWNER:
            return interaction.user.id == interaction.client.owner_id

        return False

    async def _send_permission_error(self, interaction: discord.Interaction) -> None:
        """Send standardized permission error"""
        from .builders import EmbedBuilder
        embed = EmbedBuilder().permission_denied().build()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _send_validation_error(self, interaction: discord.Interaction, errors: List[str]) -> None:
        """Send standardized validation error"""
        from .builders import EmbedBuilder
        error_text = "\n".join(f"• {error}" for error in errors)
        embed = EmbedBuilder().error("Validation Error", error_text).build()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _handle_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """Handle unexpected command errors"""
        from .builders import EmbedBuilder

        print(f"Error in command {self.command_name}: {str(error)}")
        print(traceback.format_exc())

        embed = EmbedBuilder().error(
            "Command Error",
            f"An unexpected error occurred while executing the command.\nError: {str(error)}"
        ).build()

        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            pass  # If we can't send the error message, just log it