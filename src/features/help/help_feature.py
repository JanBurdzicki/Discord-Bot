"""Help feature implementation."""
from src.core.base_feature import BaseFeature
from .commands.help_commands import HelpCommand
import discord

class HelpFeature(BaseFeature):
    """Feature for displaying help and command documentation."""

    def __init__(self, bot):
        super().__init__(bot)
        self.help_cmd = HelpCommand()

    def register_commands(self):
        """Register the /help slash command with proper signature."""

        @self.bot.tree.command(name="help", description="Show the bot help menu")
        async def help_slash(interaction: discord.Interaction):
            await self.help_cmd.execute(interaction)