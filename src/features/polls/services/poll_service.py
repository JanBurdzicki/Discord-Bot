"""
Poll service containing business logic for poll operations.
Handles poll creation, voting, and management.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import discord
from sqlalchemy.future import select
from sqlalchemy import delete

from src.database.session import AsyncSessionLocal
from src.database.models import Poll, Vote
from src.core.service_container import service
from src.core.base_command import CommandResult

@service()
class PollService:
    """Service for managing polls and votes."""

    def __init__(self):
        self.option_emojis = [chr(0x1F1E6 + i) for i in range(20)]  # 🇦 to 🇹

    async def create_poll(self,
                         question: str,
                         options: List[str],
                         creator_id: int,
                         channel_id: int,
                         duration_minutes: Optional[int] = None,
                         allow_multiple: bool = True) -> CommandResult:
        """Create a new poll with the given options."""
        try:
            # Validate options count
            if len(options) > 20:
                return CommandResult(
                    success=False,
                    error="Polls are limited to 20 options maximum"
                )

            # Calculate expiration
            expires_at = None
            if duration_minutes:
                expires_at = datetime.utcnow() + timedelta(minutes=duration_minutes)

            async with AsyncSessionLocal() as session:
                poll = Poll(
                    question=question,
                    options=",".join(options),
                    creator_id=creator_id,
                    channel_id=channel_id,
                    is_active=True,
                    allow_multiple_votes=allow_multiple,
                    created_at=datetime.utcnow(),
                    expires_at=expires_at
                )

                session.add(poll)
                await session.commit()
                await session.refresh(poll)

                return CommandResult(
                    success=True,
                    data={"poll": poll},
                    message=f"Poll created successfully!"
                )

        except Exception as e:
            return CommandResult(
                success=False,
                error=f"Failed to create poll: {str(e)}"
            )

    async def vote(self,
                   poll_id: str,
                   user_id: int,
                   option_indexes: List[int]) -> CommandResult:
        """Record a user's vote for specific options in a poll."""
        try:
            async with AsyncSessionLocal() as session:
                # Get poll
                result = await session.execute(select(Poll).where(Poll.poll_id == poll_id))
                poll = result.scalar_one_or_none()

                if not poll:
                    return CommandResult(success=False, error="Poll not found")

                if not poll.is_active:
                    return CommandResult(success=False, error="Poll is closed")

                if poll.expires_at and datetime.utcnow() > poll.expires_at:
                    poll.is_active = False
                    await session.commit()
                    return CommandResult(success=False, error="Poll has expired")

                # Validate option indexes
                options = poll.options.split(",")
                invalid_options = [idx for idx in option_indexes if idx < 0 or idx >= len(options)]
                if invalid_options:
                    return CommandResult(
                        success=False,
                        error=f"Invalid option indexes: {invalid_options}"
                    )

                # Check multiple vote restriction
                if not poll.allow_multiple_votes and len(option_indexes) > 1:
                    return CommandResult(
                        success=False,
                        error="This poll only allows voting for one option"
                    )

                # Remove existing votes
                await session.execute(
                    delete(Vote).where(
                        Vote.poll_id == poll_id,
                        Vote.user_id == user_id
                    )
                )

                # Add new votes
                for option_index in option_indexes:
                    vote = Vote(
                        poll_id=poll_id,
                        user_id=user_id,
                        option_index=option_index,
                        voted_at=datetime.utcnow()
                    )
                    session.add(vote)

                await session.commit()

                return CommandResult(
                    success=True,
                    data={
                        "poll": poll,
                        "voted_options": option_indexes
                    },
                    message=f"Vote recorded for {len(option_indexes)} option(s)!"
                )

        except Exception as e:
            return CommandResult(
                success=False,
                error=f"Failed to vote: {str(e)}"
            )

    async def get_results(self, poll_id: str) -> CommandResult:
        """Get detailed results for a poll."""
        try:
            async with AsyncSessionLocal() as session:
                # Get poll
                result = await session.execute(select(Poll).where(Poll.poll_id == poll_id))
                poll = result.scalar_one_or_none()

                if not poll:
                    return CommandResult(success=False, error="Poll not found")

                # Get all votes
                votes_result = await session.execute(select(Vote).where(Vote.poll_id == poll_id))
                votes = votes_result.scalars().all()

                # Calculate results
                options = poll.options.split(",")
                vote_counts = {i: 0 for i in range(len(options))}
                voter_details = {i: [] for i in range(len(options))}

                for vote in votes:
                    vote_counts[vote.option_index] += 1
                    voter_details[vote.option_index].append(vote.user_id)

                total_votes = len(set(vote.user_id for vote in votes))

                results_data = {
                    "poll": poll,
                    "vote_counts": vote_counts,
                    "voter_details": voter_details,
                    "total_votes": total_votes,
                    "total_vote_instances": len(votes)
                }

                return CommandResult(
                    success=True,
                    data=results_data,
                    message="Poll results retrieved successfully"
                )

        except Exception as e:
            return CommandResult(
                success=False,
                error=f"Failed to get results: {str(e)}"
            )

    async def list_active_polls(self, guild_id: Optional[int] = None) -> CommandResult:
        """List all active polls, optionally filtered by guild ID."""
        try:
            async with AsyncSessionLocal() as session:
                # Build query for active polls
                query = select(Poll).where(Poll.is_active == True)

                # Add guild filter if provided
                if guild_id is not None:
                    query = query.where(Poll.guild_id == guild_id)

                # Execute query
                result = await session.execute(query)
                polls = result.scalars().all()

                # Check for expired polls and update their status
                now = datetime.utcnow()
                active_polls = []
                for poll in polls:
                    if poll.expires_at and now > poll.expires_at:
                        poll.is_active = False
                        await session.commit()
                    else:
                        active_polls.append(poll)

                return CommandResult(
                    success=True,
                    data={"polls": active_polls},
                    message=f"Found {len(active_polls)} active polls"
                )

        except Exception as e:
            return CommandResult(
                success=False,
                error=f"Failed to list active polls: {str(e)}"
            )

    async def delete_poll(self, poll_id: str, user_id: int, is_admin: bool = False) -> CommandResult:
        """Delete a poll and all its votes."""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(Poll).where(Poll.poll_id == poll_id))
                poll = result.scalar_one_or_none()

                if not poll:
                    return CommandResult(success=False, error="Poll not found")

                # Check permissions
                if not is_admin and poll.creator_id != user_id:
                    return CommandResult(
                        success=False,
                        error="Only the poll creator or administrators can delete polls"
                    )

                # Delete votes first (foreign key constraint)
                await session.execute(delete(Vote).where(Vote.poll_id == poll_id))

                # Delete poll
                await session.delete(poll)
                await session.commit()

                return CommandResult(
                    success=True,
                    message=f"Poll and all votes have been deleted"
                )

        except Exception as e:
            return CommandResult(
                success=False,
                error=f"Failed to delete poll: {str(e)}"
            )

    def create_poll_embed(self, poll: Poll, vote_counts: Optional[Dict[int, int]] = None) -> discord.Embed:
        """Create a Discord embed for displaying a poll."""
        embed = discord.Embed(
            title=f"📊 {poll.question}",
            color=discord.Color.blue(),
            timestamp=poll.created_at
        )

        # Add options with emojis
        options = poll.options.split(",")
        options_text = ""
        for i, option in enumerate(options):
            emoji = self.option_emojis[i]
            count = vote_counts.get(i, 0) if vote_counts else 0
            options_text += f"{emoji} {option}"
            if vote_counts:
                options_text += f" ({count} votes)"
            options_text += "\n"

        embed.add_field(name="Options", value=options_text, inline=False)

        # Add metadata
        embed.add_field(name="Poll ID", value=poll.poll_id, inline=True)
        embed.add_field(
            name="Multiple Votes",
            value="✅" if poll.allow_multiple_votes else "❌",
            inline=True
        )

        if poll.expires_at:
            embed.add_field(
                name="Expires",
                value=f"<t:{int(poll.expires_at.timestamp())}:R>",
                inline=True
            )

        embed.set_footer(text=f"Created by user ID: {poll.creator_id}")
        return embed