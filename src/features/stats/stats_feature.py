"""Statistics feature implementation."""
from src.core.base_feature import BaseFeature
from .commands.stats_commands import StatsCommand
import discord

class StatsFeature(BaseFeature):
    """Feature for tracking and displaying bot statistics."""

    def __init__(self, bot):
        super().__init__(bot)
        self.stats_cmd = StatsCommand()

    def register_commands(self):
        """Register the /stats slash command with proper signature."""

        @self.bot.tree.command(name="stats", description="Show bot statistics")
        async def stats_slash(interaction: discord.Interaction):
            await self.stats_cmd.execute(interaction)