import discord
from collections import defaultdict
from sqlalchemy.future import select
from db.session import AsyncSessionLocal
from db.models import Poll, Vote

async def stats_command(interaction: discord.Interaction):
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

        # Build description
        desc = f"Total Votes: {total_votes}\nTotal Polls: {total_polls}\n"
        if top_voters:
            desc += "Top Voters:\n" + "\n".join([f"<@{uid}>: {count}" for uid, count in top_voters])
        if top_poll_creators:
            desc += "\nTop Poll Creators:\n" + "\n".join([f"<@{uid}>: {count}" for uid, count in top_poll_creators])

        embed = discord.Embed(title="Stats", description=desc, color=discord.Color.gold())
        await interaction.response.send_message(embed=embed, ephemeral=True)
