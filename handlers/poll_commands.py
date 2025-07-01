import discord
import uuid
from datetime import datetime, timedelta
from sqlalchemy.future import select
from db.session import AsyncSessionLocal
from db.models import Poll, Vote

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
            from sqlalchemy import delete
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
            stats_module.log_vote_action(user_id, poll_id)
            print(f"Synced votes for user {user_id}: options {valid_reactions}")
            return True

    except Exception as e:
        print(f"Error syncing reaction votes: {e}")
        return False


from utils.stats_module import StatsModule

# Initialize stats module
stats_module = StatsModule()

async def create_poll_command(interaction: discord.Interaction, question: str, options: str, duration: int = 5):
    poll_id = str(uuid.uuid4())
    opts = [opt.strip() for opt in options.split(",") if opt.strip()]

    # Validate options count (Discord reactions limit is 20)
    if len(opts) > 20:
        embed = discord.Embed(
            title="Too Many Options",
            description="Please limit your poll to 20 options or fewer. Use `/create_advanced_poll` for more complex polls.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Respond immediately to avoid timeout
    embed_response = discord.Embed(
        title="Creating Poll...",
        description=f"Setting up poll: {question}",
        color=discord.Color.yellow()
    )
    await interaction.response.send_message(embed=embed_response, ephemeral=True)

    # Save poll to database
    async with AsyncSessionLocal() as session:
        poll = Poll(
            poll_id=poll_id,
            question=question,
            options=",".join(opts),
            creator_id=interaction.user.id,
            channel_id=interaction.channel_id,
            is_active=True,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=duration)
        )
        session.add(poll)
        await session.commit()

    stats_module.log_poll_creation(interaction.user.id, poll_id)

    # Create poll embed
    embed = discord.Embed(title="📊 Poll", description=question, color=discord.Color.blue())
    embed.add_field(name="Poll ID", value=poll_id, inline=False)

    # Add options with emojis (use Unicode regional indicators for A-T)
    emoji_options = []
    for idx, opt in enumerate(opts):
        emoji = chr(0x1F1E6 + idx)  # 🇦 to 🇹

        emoji_options.append(emoji)
        embed.add_field(name=f"{emoji} {opt}", value="\u200b", inline=False)

    embed.add_field(name="Duration", value=f"{duration} minutes", inline=True)
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
    embed_final = discord.Embed(
        title="✅ Poll Created!",
        description=f"Poll '{question}' is now active!\n\n**Poll ID:** {poll_id}\n**Duration:** {duration} minutes\n\n**How to vote:**\n🔸 **Emoji reactions**: Your vote = all clicked emojis\n🔸 **Slash command**: `/vote_poll {poll_id} 1,2,3` sets your complete vote\n\n*Note: Both methods sync to the same vote database*",
        color=discord.Color.green()
    )
    await interaction.edit_original_response(embed=embed_final)

# --- Advanced Polls (StrawPoll API) ---
async def create_advanced_poll_command(interaction: discord.Interaction, question: str, options: str, multi: bool = False):
    opts = [opt.strip() for opt in options.split(",") if opt.strip()]
    poll_id = str(uuid.uuid4())

    # Validate options count
    if len(opts) > 50:  # Allow more options for advanced polls
        embed = discord.Embed(
            title="Too Many Options",
            description="Please limit your advanced poll to 50 options or fewer.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return


    # For demo purposes, we'll create a local advanced poll instead of using StrawPoll API
    # In production, you would integrate with StrawPoll API here
    async with AsyncSessionLocal() as session:
        poll = Poll(
            poll_id=poll_id,
            question=question,
            options=",".join(opts),
            creator_id=interaction.user.id,
            channel_id=interaction.channel_id,
            is_active=True,
            is_advanced=True,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)  # Advanced polls last longer
        )
        session.add(poll)
        await session.commit()

    stats_module.log_poll_creation(interaction.user.id, poll_id)
    embed = discord.Embed(title="🔮 Advanced Poll Created", description=f"**Question:** {question}", color=discord.Color.purple())
    embed.add_field(name="Poll ID", value=poll_id, inline=False)
    embed.add_field(name="Type", value="Advanced Poll (Command-based voting only)", inline=True)
    embed.add_field(name="Duration", value="7 days", inline=True)
    embed.add_field(name="Multiple Choice", value="Yes" if multi else "No", inline=True)

    # Show options in a nice format
    options_text = "\n".join([f"`{i+1}.` {opt}" for i, opt in enumerate(opts)])
    embed.add_field(name="Options", value=options_text, inline=False)
    embed.add_field(name="How to Vote", value=f"🔸 **Slash command**: `/vote_poll {poll_id} 1,3,5` sets your complete vote\n🔸 **Emoji reactions**: Your vote = all clicked emojis\n\n*Both methods sync to the same database*", inline=False)
    embed.set_footer(text=f"Created by {interaction.user.display_name}")

    await interaction.response.send_message(embed=embed, ephemeral=True)

async def vote_poll_command(interaction: discord.Interaction, poll_id: str, option_indexes: str):
    async with AsyncSessionLocal() as session:
        # Check if poll exists and is active
        result = await session.execute(select(Poll).where(Poll.poll_id == poll_id))
        poll = result.scalar_one_or_none()

        if not poll or not poll.is_active:
            embed = discord.Embed(title="Error", description="Poll not found or closed.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if poll has expired
        if poll.expires_at and datetime.utcnow() > poll.expires_at:
            poll.is_active = False
            await session.commit()
            embed = discord.Embed(title="Poll Expired", description="This poll has expired and is no longer accepting votes.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

                # Parse option indexes (support multiple votes)
        try:
            option_list = [int(x.strip()) for x in option_indexes.split(",") if x.strip()]
        except ValueError:
            embed = discord.Embed(title="Error", description="Invalid option format. Use comma-separated numbers (e.g., '1,3,5' or just '2').", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if option indexes are valid
        options = poll.options.split(",")
        invalid_options = [opt for opt in option_list if opt < 1 or opt > len(options)]
        if invalid_options:
            embed = discord.Embed(title="Error", description=f"Invalid options: {invalid_options}. Choose from 1-{len(options)}.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Remove duplicates and sort
        option_list = sorted(list(set(option_list)))

                # Get user's current votes to compare
        result = await session.execute(
            select(Vote).where(
                Vote.poll_id == poll_id,
                Vote.user_id == interaction.user.id
            )
        )
        current_votes = result.scalars().all()
        old_option_indexes = {vote.option_index for vote in current_votes}

        # Delete all existing votes for this user and poll
        from sqlalchemy import delete
        await session.execute(delete(Vote).where(Vote.poll_id == poll_id, Vote.user_id == interaction.user.id))

        # Add new votes based on specified options
        for option_index in option_list:
            vote = Vote(
                poll_id=poll_id,
                user_id=interaction.user.id,
                option_index=option_index - 1,
                voted_at=datetime.utcnow()
            )
            session.add(vote)

        await session.commit()

    stats_module.log_vote_action(interaction.user.id, poll_id)

    # Update emoji reactions on the original poll message
    try:
        channel = interaction.client.get_channel(poll.channel_id)
        if channel:
            # Find the poll message (look for recent messages with the poll_id)
            async for message in channel.history(limit=50):
                if message.embeds and poll_id in str(message.embeds[0].to_dict()):
                    user = interaction.client.get_user(interaction.user.id)
                    if user:
                        # Remove user's reactions for old votes that are no longer selected
                        for old_idx in old_option_indexes:
                            emoji = chr(0x1F1E6 + old_idx)  # 🇦 to 🇹
                            try:
                                await message.remove_reaction(emoji, user)
                            except:
                                pass
                    break
    except Exception as e:
        print(f"Could not update reactions: {e}")

    # Create response message
    selected_options = [options[idx - 1] for idx in option_list]
    if len(selected_options) == 1:
        action = f"✅ Your vote: **{selected_options[0]}**"
    else:
        action = f"✅ Your votes ({len(selected_options)}):\n" + "\n".join([f"• **{opt}**" for opt in selected_options])

    embed = discord.Embed(
        title="🗳️ Vote Set",
        description=f"{action}\n\nPoll: {poll.question}\n\n*Emoji reactions automatically cleaned up. Your vote is now synced.*",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)



async def poll_results_command(interaction: discord.Interaction, poll_id: str):
    async with AsyncSessionLocal() as session:
        # Get poll
        result = await session.execute(select(Poll).where(Poll.poll_id == poll_id))
        poll = result.scalar_one_or_none()

        if not poll:
            embed = discord.Embed(title="Error", description="Poll not found.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if poll has expired
        is_expired = poll.expires_at and datetime.utcnow() > poll.expires_at
        if is_expired and poll.is_active:
            poll.is_active = False
            await session.commit()

        # Get all votes for this poll
        result = await session.execute(select(Vote).where(Vote.poll_id == poll_id))
        votes = result.scalars().all()

        # Count votes (handle multiple votes per user for advanced polls)
        options = poll.options.split(",")
        counts = [0] * len(options)
        for vote in votes:
            if 0 <= vote.option_index < len(counts):
                counts[vote.option_index] += 1

        total_votes = sum(counts)

        # Determine poll status
        if is_expired or not poll.is_active:
            status = "🔒 Closed"
            color = discord.Color.red()
        else:
            status = "🟢 Active"
            color = discord.Color.green()

        embed = discord.Embed(title="📊 Poll Results", description=poll.question, color=color)
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Total Votes", value=str(total_votes), inline=True)
        embed.add_field(name="Poll ID", value=poll_id, inline=True)

        # Add results with percentages and bar visualization
        for idx, opt in enumerate(options):
            count = counts[idx]
            percentage = (count / total_votes * 100) if total_votes > 0 else 0

            # Create a simple text bar
            bar_length = 20
            filled_length = int(bar_length * count / max(counts)) if max(counts) > 0 else 0
            bar = "█" * filled_length + "░" * (bar_length - filled_length)

            emoji = chr(0x1F1E6 + idx)  # 🇦 to 🇹

            embed.add_field(
                name=f"{emoji} {opt}",
                value=f"`{bar}` {count} votes ({percentage:.1f}%)",
                inline=False
            )

        # Add chart if there are votes
        if total_votes > 0:
            try:
                # Create visualization with QuickChart
                chart_data = {
                    "type": "bar",
                    "data": {
                        "labels": [f"{opt[:20]}..." if len(opt) > 20 else opt for opt in options],
                        "datasets": [{
                            "label": "Votes",
                            "data": counts,
                            "backgroundColor": "rgba(54, 162, 235, 0.8)"
                        }]
                    },
                    "options": {
                        "responsive": True,
                        "scales": {
                            "y": {
                                "beginAtZero": True,
                                "ticks": {
                                    "stepSize": 1
                                }
                            }
                        }
                    }
                }
                import json
                import urllib.parse
                chart_url = f"https://quickchart.io/chart?c={urllib.parse.quote(json.dumps(chart_data))}"
                embed.set_image(url=chart_url)
            except:
                pass  # If chart fails, just show the text results

        # Add footer with creation info
        if poll.expires_at:
            time_info = f"Expires: {poll.expires_at.strftime('%Y-%m-%d %H:%M UTC')}"
        else:
            time_info = f"Created: {poll.created_at.strftime('%Y-%m-%d %H:%M UTC')}"
        embed.set_footer(text=time_info)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def list_polls_command(interaction: discord.Interaction):
    async with AsyncSessionLocal() as session:
        # Get active polls
        result = await session.execute(select(Poll).where(Poll.is_active == True))
        active_polls = result.scalars().all()

        # Get inactive polls
        result = await session.execute(select(Poll).where(Poll.is_active == False))
        inactive_polls = result.scalars().all()

        embed = discord.Embed(title="📊 All Polls", color=discord.Color.blue())

        # Active polls section
        if active_polls:
            active_desc = ""
            for poll in active_polls:
                poll_type = "🔮 Advanced" if poll.is_advanced else "📊 Simple"
                time_left = ""
                if poll.expires_at:
                    now = datetime.utcnow()
                    if poll.expires_at > now:
                        time_diff = poll.expires_at - now
                        hours = int(time_diff.total_seconds() // 3600)
                        minutes = int((time_diff.total_seconds() % 3600) // 60)
                        if hours > 0:
                            time_left = f" (⏰ {hours}h {minutes}m left)"
                        else:
                            time_left = f" (⏰ {minutes}m left)"

                active_desc += f"• `{poll.poll_id}` {poll_type} - {poll.question[:50]}{'...' if len(poll.question) > 50 else ''}{time_left}\n"

            embed.add_field(name="🟢 Active Polls", value=active_desc or "None", inline=False)
        else:
            embed.add_field(name="🟢 Active Polls", value="None", inline=False)

        # Inactive polls section
        if inactive_polls:
            inactive_desc = ""
            for poll in inactive_polls[:10]:  # Limit to last 10 inactive polls
                poll_type = "🔮 Advanced" if poll.is_advanced else "📊 Simple"
                closed_date = poll.expires_at.strftime("%m/%d %H:%M") if poll.expires_at else "Unknown"
                inactive_desc += f"• `{poll.poll_id}` {poll_type} - {poll.question[:50]}{'...' if len(poll.question) > 50 else ''} (Closed: {closed_date})\n"

            if len(inactive_polls) > 10:
                inactive_desc += f"\n... and {len(inactive_polls) - 10} more"

            embed.add_field(name="🔒 Inactive Polls", value=inactive_desc, inline=False)
        else:
            embed.add_field(name="🔒 Inactive Polls", value="None", inline=False)

        embed.add_field(name="Commands", value="• `/poll_results <poll_id>` - View results\n• `/vote_poll <poll_id> <options>` - Vote in poll", inline=False)
        embed.set_footer(text=f"Total: {len(active_polls)} active, {len(inactive_polls)} inactive")

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def delete_poll_command(interaction: discord.Interaction, poll_id: str):
    async with AsyncSessionLocal() as session:
        # Get poll
        result = await session.execute(select(Poll).where(Poll.poll_id == poll_id))
        poll = result.scalar_one_or_none()

        if not poll:
            embed = discord.Embed(title="Error", description="Poll not found.", color=discord.Color.red())
        elif poll.creator_id != interaction.user.id and interaction.user.id != interaction.guild.owner_id:
            embed = discord.Embed(title="Permission Denied", description="Only the poll creator or server owner can delete this poll.", color=discord.Color.red())
        else:
            # Delete all votes for this poll first
            from sqlalchemy import delete
            await session.execute(delete(Vote).where(Vote.poll_id == poll_id))
            # Delete the poll
            await session.delete(poll)
            await session.commit()
            embed = discord.Embed(title="Poll Deleted", description=f"Poll {poll_id} deleted.", color=discord.Color.green())

        await interaction.response.send_message(embed=embed, ephemeral=True)