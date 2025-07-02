"""
Base feature class for the plugin system.
Provides a consistent interface for all bot features.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, Any, List
import discord

if TYPE_CHECKING:
    from .bot import BotCore

class BaseFeature(ABC):
    """
    Base class for all bot features.
    Features are self-contained modules that provide specific functionality.
    """

    def __init__(self, bot: 'BotCore'):
        self.bot = bot
        self.name = self.__class__.__name__.replace('Feature', '').lower()
        self.commands: Dict[str, Any] = {}
        self.listeners: List[str] = []

    @abstractmethod
    def register_commands(self) -> None:
        """Register all commands for this feature"""
        pass

    def register_listeners(self) -> None:
        """Register event listeners for this feature (optional)"""
        pass

    async def on_feature_load(self) -> None:
        """Called when the feature is loaded (optional)"""
        pass

    async def on_feature_unload(self) -> None:
        """Called when the feature is unloaded (optional)"""
        pass

    def _register_command(self, name: str, command_instance, description: str = None):
        """Helper method to register a command"""
        self.bot.tree.command(name=name, description=description or f"{name} command")(
            command_instance.execute
        )
        self.commands[name] = command_instance
        print(f"Registered command /{name} for feature {self.name}")

    def _register_listener(self, event_name: str, handler):
        """Helper method to register an event listener"""
        setattr(self.bot, event_name, handler)
        self.listeners.append(event_name)
        print(f"Registered listener {event_name} for feature {self.name}")

    def get_feature_info(self) -> Dict[str, Any]:
        """Get information about this feature"""
        return {
            'name': self.name,
            'class_name': self.__class__.__name__,
            'commands': list(self.commands.keys()),
            'listeners': self.listeners,
            'loaded': True
        }