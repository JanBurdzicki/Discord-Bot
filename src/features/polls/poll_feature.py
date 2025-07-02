"""Poll feature implementation."""
import discord
from discord.ext import commands
from discord import app_commands
from src.core.base_feature import BaseFeature
from .commands.poll_commands import (
    CreatePollCommand, CreateAdvancedPollCommand, VotePollCommand,
    PollResultsCommand, ListPollsCommand, DeletePollCommand
)

class PollFeature(BaseFeature):
    """Feature for creating and managing polls."""

    def __init__(self, bot):
        super().__init__(bot)
        # Initialize command instances
        self.create_poll_cmd = CreatePollCommand()
        self.create_advanced_poll_cmd = CreateAdvancedPollCommand()
        self.vote_poll_cmd = VotePollCommand()
        self.poll_results_cmd = PollResultsCommand()
        self.list_polls_cmd = ListPollsCommand()
        self.delete_poll_cmd = DeletePollCommand()

    def register_commands(self):
        """Register poll commands."""

        @self.bot.tree.command(name="create_poll", description="Create a new poll with emoji reactions")
        @app_commands.describe(
            question="The poll question",
            options="Comma-separated options (max 20)",
            duration="Duration in minutes (default: 60)"
        )
        async def create_poll(interaction: discord.Interaction, question: str, options: str, duration: int = 60):
            """Create a new poll."""
            await self.create_poll_cmd.execute(interaction, question=question, options=options, duration=duration)

        @self.bot.tree.command(name="create_advanced_poll", description="Create an advanced poll with more options")
        @app_commands.describe(
            question="The poll question",
            options="Comma-separated options (max 50)",
            multi="Allow multiple votes per user"
        )
        async def create_advanced_poll(interaction: discord.Interaction, question: str, options: str, multi: bool = False):
            """Create an advanced poll."""
            await self.create_advanced_poll_cmd.execute(interaction, question=question, options=options, multi=multi)

        @self.bot.tree.command(name="vote_poll", description="Vote in a poll")
        @app_commands.describe(
            poll_id="The poll ID",
            option_indexes="Option numbers (e.g. '1,3,5' for multiple or '2' for single)"
        )
        async def vote_poll(interaction: discord.Interaction, poll_id: str, option_indexes: str):
            """Vote in a poll."""
            await self.vote_poll_cmd.execute(interaction, poll_id=poll_id, option_indexes=option_indexes)

        @self.bot.tree.command(name="poll_results", description="Show poll results")
        @app_commands.describe(poll_id="The poll ID")
        async def poll_results(interaction: discord.Interaction, poll_id: str):
            """Show poll results."""
            await self.poll_results_cmd.execute(interaction, poll_id=poll_id)

        @self.bot.tree.command(name="list_polls", description="List all active polls")
        async def list_polls(interaction: discord.Interaction):
            """List all active polls."""
            await self.list_polls_cmd.execute(interaction)

        @self.bot.tree.command(name="delete_poll", description="Delete a poll (creator or admin only)")
        @app_commands.describe(poll_id="The poll ID")
        async def delete_poll(interaction: discord.Interaction, poll_id: str):
            """Delete a poll."""
            await self.delete_poll_cmd.execute(interaction, poll_id=poll_id)