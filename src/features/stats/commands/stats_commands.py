"""Statistics command implementations."""
from typing import Dict, Any
import discord
from collections import defaultdict
from sqlalchemy.future import select

from src.core.base_command import BaseCommand
from src.core.builders import EmbedBuilder
from src.database.models import Poll, Vote
from src.database.session import AsyncSessionLocal

class StatsCommand(BaseCommand):
    """Command to show voting and poll statistics."""

    async def validate_input(self, interaction: discord.Interaction, **kwargs) -> Dict[str, Any]:
        """No validation needed for stats command."""
        return {"validated": True}

    async def check_permissions(self, interaction: discord.Interaction, **kwargs) -> bool:
        """Anyone can view stats."""
        return True

    async def process_command(self, interaction: discord.Interaction, data: Dict[str, Any]) -> Dict[str, Any]:
        """Gather statistics and build an embed."""
        async with AsyncSessionLocal() as session:
            # Get poll statistics
            poll_result = await session.execute(select(Poll))
            polls = poll_result.scalars().all()

            # Get vote statistics
            vote_result = await session.execute(select(Vote))
            votes = vote_result.scalars().all()

        # Calculate stats
        total_polls = len(polls)
        total_votes = len(votes)

        # Top voters
        vote_counts = defaultdict(int)
        for vote in votes:
            vote_counts[vote.user_id] += 1
        top_voters = sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Top poll creators
        poll_counts = defaultdict(int)
        for poll in polls:
            poll_counts[poll.creator_id] += 1
        top_poll_creators = sorted(poll_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Build embed
        embed = EmbedBuilder()\
            .set_title("📊 Bot Statistics")\
            .set_color(discord.Color.gold())\
            .add_field("Total Polls Created", str(total_polls), inline=True)\
            .add_field("Total Votes Cast", str(total_votes), inline=True)

        if top_voters:
            top_voters_text = "\n".join(
                f"{idx+1}. <@{uid}>: {count} votes" for idx, (uid, count) in enumerate(top_voters)
            )
            embed.add_field("🏆 Top Voters", top_voters_text, inline=False)

        if top_poll_creators:
            top_creators_text = "\n".join(
                f"{idx+1}. <@{uid}>: {count} polls"
                for idx, (uid, count) in enumerate(top_poll_creators)
            )
            embed.add_field("👑 Top Poll Creators", top_creators_text, inline=False)

        active_polls = sum(1 for poll in polls if poll.is_active)
        embed.add_field("Active Polls", str(active_polls), inline=True)

        avg_votes = total_votes / total_polls if total_polls > 0 else 0
        embed.add_field("Average Votes/Poll", f"{avg_votes:.1f}", inline=True)

        await interaction.response.defer()
        return {"success": True, "embed": embed.build()}

    async def send_response(self, interaction: discord.Interaction, result: Dict[str, Any]) -> None:
        """Send statistics embed."""
        embed = result.get("embed")
        if embed:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to generate statistics.", ephemeral=True)