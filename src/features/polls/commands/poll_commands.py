"""
Poll command implementations for the Discord bot.
Provides complete poll functionality including creation, voting, and management.
"""

import discord
import uuid
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.future import select
from sqlalchemy import delete

from src.core.base_command import BaseCommand
from src.core.builders import EmbedBuilder
from src.database.session import AsyncSessionLocal
from src.database.models import Poll, Vote
from src.core.decorators import requires_permission
from src.core.validators import validate_poll_options, validate_poll_duration


async def sync_reaction_votes(poll_id: str, user_id: int, message) -> bool:
    """Sync user's votes based on their current emoji reactions on the poll message. Returns True if successful."""
    try:
        async with AsyncSessionLocal() as session:
            # Check if poll exists and is active
            result = await session.execute(select(Poll).where(Poll.poll_id == poll_id))
            poll = result.scalar_one_or_none()

            if not poll or not poll.is_active:
                return False

            # Check if poll has expired
            if poll.expires_at and datetime.utcnow() > poll.expires_at:
                poll.is_active = False
                await session.commit()
                return False

            # Get all user's current reactions on this message
            user_reactions = []
            for reaction in message.reactions:
                emoji_str = str(reaction.emoji)
                # Check if this is a poll emoji (🇦 to 🇹) and if user reacted to it
                if len(emoji_str) == 1:
                    char_code = ord(emoji_str)
                    if 0x1F1E6 <= char_code <= 0x1F1F9:  # 🇦 to 🇹
                        option_index = char_code - 0x1F1E6
                        # Check if this user has reacted to this emoji
                        async for user in reaction.users():
                            if user.id == user_id:
                                user_reactions.append(option_index)
                                break

            # Validate option indexes
            options = poll.options.split(",")
            valid_reactions = [idx for idx in user_reactions if 0 <= idx < len(options)]

            print(f"User {user_id} reactions: {valid_reactions}")

            # Delete all existing votes for this user and poll
            await session.execute(delete(Vote).where(Vote.poll_id == poll_id, Vote.user_id == user_id))

            # Add new votes based on current reactions
            for option_index in valid_reactions:
                vote = Vote(
                    poll_id=poll_id,
                    user_id=user_id,
                    option_index=option_index,
                    voted_at=datetime.utcnow()
                )
                session.add(vote)

            await session.commit()
            print(f"Synced votes for user {user_id}: options {valid_reactions}")
            return True

    except Exception as e:
        print(f"Error syncing reaction votes: {e}")
        return False


class CreatePollCommand(BaseCommand):
    """Command to create a basic poll with emoji reactions"""

    async def process_command(self, interaction: discord.Interaction, data: dict) -> dict:
        question = data['question']
        options = data['options']
        duration = data.get('duration', 60)

        poll_id = str(uuid.uuid4())
        opts = [opt.strip() for opt in options.split(",") if opt.strip()]

        # Validate options count (Discord reactions limit is 20)
        if len(opts) > 20:
            return {
                'success': False,
                'error': 'Too many options. Please limit your poll to 20 options or fewer.'
            }

        # Save poll to database
        async with AsyncSessionLocal() as session:
            poll = Poll(
                poll_id=poll_id,
                question=question,
                options=",".join(opts),
                creator_id=interaction.user.id,
                guild_id=interaction.guild.id,
                channel_id=interaction.channel.id,
                is_active=True,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(minutes=duration)
            )
            session.add(poll)
            await session.commit()

        # Get stats module and log creation
        stats_module = interaction.client.services.get('StatsModule')
        if stats_module:
            stats_module.log_poll_creation(interaction.user.id, poll_id)

        return {
            'success': True,
            'poll_id': poll_id,
            'question': question,
            'options': opts,
            'duration': duration
        }

    async def send_response(self, interaction: discord.Interaction, result: dict) -> None:
        if not result['success']:
            embed = EmbedBuilder().error("Poll Creation Failed", result.get('error', 'Unknown error')).build()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Respond immediately to avoid timeout
        embed_response = EmbedBuilder().info("Creating Poll...", f"Setting up poll: {result['question']}").build()
        await interaction.response.send_message(embed=embed_response, ephemeral=True)

        # Create poll embed
        embed = EmbedBuilder().info("📊 Poll", result['question']).build()
        embed.add_field(name="Poll ID", value=result['poll_id'], inline=False)

        # Add options with emojis
        emoji_options = []
        for idx, opt in enumerate(result['options']):
            emoji = chr(0x1F1E6 + idx)  # 🇦 to 🇹
            emoji_options.append(emoji)
            embed.add_field(name=f"{emoji} {opt}", value="\u200b", inline=False)

        embed.add_field(name="Duration", value=f"{result['duration']} minutes", inline=True)
        embed.add_field(name="How to Vote", value="🔸 **Emoji reactions**: Your vote = clicked emojis\n🔸 **Slash command**: `/vote_poll` sets complete vote\n• Both methods are synchronized", inline=True)
        embed.set_footer(text=f"Created by {interaction.user.display_name}")

        # Send poll message and add reactions
        msg = await interaction.channel.send(embed=embed)
        for emoji in emoji_options:
            try:
                await msg.add_reaction(emoji)
            except:
                pass  # Skip if emoji fails

        # Update the response
        embed_final = EmbedBuilder().success("Poll Created!",
            f"Poll '{result['question']}' is now active!\n\n**Poll ID:** {result['poll_id']}\n**Duration:** {result['duration']} minutes").build()
        await interaction.edit_original_response(embed=embed_final)


class CreateAdvancedPollCommand(BaseCommand):
    """Command to create an advanced poll with more options"""

    async def process_command(self, interaction: discord.Interaction, data: dict) -> dict:
        question = data['question']
        options = data['options']
        multi = data.get('multi', False)

        opts = [opt.strip() for opt in options.split(",") if opt.strip()]
        poll_id = str(uuid.uuid4())

        # Validate options count
        if len(opts) > 50:
            return {
                'success': False,
                'error': 'Please limit your advanced poll to 50 options or fewer.'
            }

        # Create advanced poll in database
        async with AsyncSessionLocal() as session:
            poll = Poll(
                poll_id=poll_id,
                question=question,
                options=",".join(opts),
                creator_id=interaction.user.id,
                guild_id=interaction.guild.id,
                channel_id=interaction.channel.id,
                is_active=True,
                is_advanced=True,
                allow_multiple_votes=multi,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=7)  # Advanced polls last longer
            )
            session.add(poll)
            await session.commit()

        stats_module = interaction.client.services.get('StatsModule')
        if stats_module:
            stats_module.log_poll_creation(interaction.user.id, poll_id)

        return {
            'success': True,
            'poll_id': poll_id,
            'question': question,
            'options': opts,
            'multi': multi
        }

    async def send_response(self, interaction: discord.Interaction, result: dict) -> None:
        if not result['success']:
            embed = EmbedBuilder().error("Advanced Poll Creation Failed", result.get('error', 'Unknown error')).build()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = EmbedBuilder().info("🔮 Advanced Poll Created", f"**Question:** {result['question']}").build()
        embed.add_field(name="Poll ID", value=result['poll_id'], inline=False)
        embed.add_field(name="Type", value="Advanced Poll (Command-based voting only)", inline=True)
        embed.add_field(name="Duration", value="7 days", inline=True)
        embed.add_field(name="Multiple Choice", value="Yes" if result['multi'] else "No", inline=True)

        # Show options in a nice format
        options_text = "\n".join([f"`{i+1}.` {opt}" for i, opt in enumerate(result['options'])])
        embed.add_field(name="Options", value=options_text, inline=False)
        embed.add_field(name="How to Vote", value=f"🔸 **Slash command**: `/vote_poll {result['poll_id']} 1,3,5` sets your complete vote\n🔸 **Emoji reactions**: Your vote = all clicked emojis\n\n*Both methods sync to the same database*", inline=False)
        embed.set_footer(text=f"Created by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed, ephemeral=True)


class VotePollCommand(BaseCommand):
    """Command to vote on a poll"""

    async def process_command(self, interaction: discord.Interaction, data: dict) -> dict:
        poll_id = data['poll_id']
        option_indexes = data['option_indexes']

        async with AsyncSessionLocal() as session:
            # Check if poll exists and is active
            result = await session.execute(select(Poll).where(Poll.poll_id == poll_id))
            poll = result.scalar_one_or_none()

            if not poll:
                return {'success': False, 'error': f'Poll with ID {poll_id} not found.'}

            if not poll.is_active:
                return {'success': False, 'error': 'This poll is no longer active.'}

            # Check if poll has expired
            if poll.expires_at and datetime.utcnow() > poll.expires_at:
                poll.is_active = False
                await session.commit()
                return {'success': False, 'error': 'This poll has expired.'}

            # Parse option indexes
            try:
                option_list = [int(x.strip()) - 1 for x in option_indexes.split(",")]
            except ValueError:
                return {'success': False, 'error': 'Invalid option format. Use numbers like: 1,3,5'}

            # Validate option indexes
            options = poll.options.split(",")
            invalid_options = [idx for idx in option_list if idx < 0 or idx >= len(options)]
            if invalid_options:
                return {'success': False, 'error': f'Invalid option numbers. Valid range: 1-{len(options)}'}

            # Delete existing votes for this user and poll
            await session.execute(delete(Vote).where(Vote.poll_id == poll_id, Vote.user_id == interaction.user.id))

            # Add new votes
            for option_index in option_list:
                vote = Vote(
                    poll_id=poll_id,
                    user_id=interaction.user.id,
                    option_index=option_index,
                    voted_at=datetime.utcnow()
                )
                session.add(vote)

            await session.commit()

            stats_module = interaction.client.services.get('StatsModule')
            if stats_module:
                stats_module.log_vote_action(interaction.user.id, poll_id)

            return {
                'success': True,
                'poll_question': poll.question,
                'voted_options': [options[idx] for idx in option_list]
            }

    async def send_response(self, interaction: discord.Interaction, result: dict) -> None:
        if not result['success']:
            embed = EmbedBuilder().error("Vote Failed", result.get('error', 'Unknown error')).build()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        voted_options_text = "\n".join(f"• {opt}" for opt in result['voted_options'])
        embed = EmbedBuilder().success("Vote Recorded!",
            f"Your vote has been recorded for:\n**{result['poll_question']}**\n\nYour selected options:\n{voted_options_text}").build()
        await interaction.response.send_message(embed=embed, ephemeral=True)


class PollResultsCommand(BaseCommand):
    """Command to show poll results"""

    async def process_command(self, interaction: discord.Interaction, data: dict) -> dict:
        poll_id = data['poll_id']

        async with AsyncSessionLocal() as session:
            # Get poll
            result = await session.execute(select(Poll).where(Poll.poll_id == poll_id))
            poll = result.scalar_one_or_none()

            if not poll:
                return {'success': False, 'error': f'Poll with ID {poll_id} not found.'}

            # Get all votes
            votes_result = await session.execute(select(Vote).where(Vote.poll_id == poll_id))
            votes = votes_result.scalars().all()

            options = poll.options.split(",")
            vote_counts = [0] * len(options)
            total_voters = set()

            for vote in votes:
                if 0 <= vote.option_index < len(options):
                    vote_counts[vote.option_index] += 1
                    total_voters.add(vote.user_id)

            return {
                'success': True,
                'poll': poll,
                'options': options,
                'vote_counts': vote_counts,
                'total_voters': len(total_voters),
                'total_votes': len(votes)
            }

    async def send_response(self, interaction: discord.Interaction, result: dict) -> None:
        if not result['success']:
            embed = EmbedBuilder().error("Poll Results Failed", result.get('error', 'Unknown error')).build()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        poll = result['poll']
        embed = EmbedBuilder().info(f"📊 Poll Results: {poll.question}", "").build()
        embed.add_field(name="Poll ID", value=poll.poll_id, inline=True)
        embed.add_field(name="Status", value="🟢 Active" if poll.is_active else "🔴 Inactive", inline=True)
        embed.add_field(name="Total Voters", value=str(result['total_voters']), inline=True)

        # Add results for each option
        max_votes = max(result['vote_counts']) if result['vote_counts'] else 0
        for i, (option, count) in enumerate(zip(result['options'], result['vote_counts'])):
            emoji = chr(0x1F1E6 + i) if i < 20 else f"{i+1}."
            percentage = (count / result['total_votes'] * 100) if result['total_votes'] > 0 else 0

            # Create visual bar
            bar_length = int(percentage / 5) if max_votes > 0 else 0
            bar = "█" * bar_length + "░" * (20 - bar_length)

            embed.add_field(
                name=f"{emoji} {option}",
                value=f"{bar} {count} votes ({percentage:.1f}%)",
                inline=False
            )

        if poll.expires_at:
            if datetime.utcnow() > poll.expires_at:
                embed.add_field(name="⏰ Status", value="Expired", inline=True)
            else:
                time_left = poll.expires_at - datetime.utcnow()
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                embed.add_field(name="⏰ Time Left", value=f"{time_left.days}d {hours}h {minutes}m", inline=True)

        creator = interaction.guild.get_member(poll.creator_id)
        embed.set_footer(text=f"Created by {creator.display_name if creator else 'Unknown'}")

        await interaction.response.send_message(embed=embed)


class ListPollsCommand(BaseCommand):
    """Command to list all active polls"""

    async def process_command(self, interaction: discord.Interaction, data: dict) -> dict:
        async with AsyncSessionLocal() as session:
            # Get all active polls in this guild
            result = await session.execute(
                select(Poll).where(
                    Poll.guild_id == interaction.guild.id,
                    Poll.is_active == True
                ).order_by(Poll.created_at.desc())
            )
            polls = result.scalars().all()

            return {
                'success': True,
                'polls': polls
            }

    async def send_response(self, interaction: discord.Interaction, result: dict) -> None:
        if not result['success']:
            embed = EmbedBuilder().error("List Polls Failed", result.get('error', 'Unknown error')).build()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        polls = result['polls']

        if not polls:
            embed = EmbedBuilder().info("📊 Active Polls", "No active polls found in this server.").build()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = EmbedBuilder().info("📊 Active Polls", f"Found {len(polls)} active poll(s)").build()

        for poll in polls[:10]:  # Limit to 10 polls
            creator = interaction.guild.get_member(poll.creator_id)
            creator_name = creator.display_name if creator else "Unknown"

            poll_type = "🔮 Advanced" if poll.is_advanced else "📊 Basic"
            time_left = ""
            if poll.expires_at:
                if datetime.utcnow() > poll.expires_at:
                    time_left = "⏰ Expired"
                else:
                    delta = poll.expires_at - datetime.utcnow()
                    hours, remainder = divmod(delta.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    time_left = f"⏰ {delta.days}d {hours}h {minutes}m left"

            embed.add_field(
                name=f"{poll_type} {poll.question[:50]}{'...' if len(poll.question) > 50 else ''}",
                value=f"**ID:** `{poll.poll_id}`\n**Creator:** {creator_name}\n{time_left}",
                inline=True
            )

        if len(polls) > 10:
            embed.set_footer(text=f"Showing 10 of {len(polls)} active polls")

        await interaction.response.send_message(embed=embed)


class DeletePollCommand(BaseCommand):
    """Command to delete a poll"""

    async def process_command(self, interaction: discord.Interaction, data: dict) -> dict:
        poll_id = data['poll_id']

        async with AsyncSessionLocal() as session:
            # Get poll
            result = await session.execute(select(Poll).where(Poll.poll_id == poll_id))
            poll = result.scalar_one_or_none()

            if not poll:
                return {'success': False, 'error': f'Poll with ID {poll_id} not found.'}

            # Check permissions - only creator or admin can delete
            if poll.creator_id != interaction.user.id and interaction.user.id != interaction.client.owner_id:
                return {'success': False, 'error': 'Only the poll creator or bot owner can delete this poll.'}

            # Delete the poll (cascade will delete votes)
            await session.delete(poll)
            await session.commit()

            return {
                'success': True,
                'poll_question': poll.question
            }

    async def send_response(self, interaction: discord.Interaction, result: dict) -> None:
        if not result['success']:
            embed = EmbedBuilder().error("Delete Poll Failed", result.get('error', 'Unknown error')).build()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = EmbedBuilder().success("Poll Deleted", f"Successfully deleted poll: **{result['poll_question']}**").build()
        await interaction.response.send_message(embed=embed, ephemeral=True)