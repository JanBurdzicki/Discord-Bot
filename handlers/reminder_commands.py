import discord
from datetime import datetime, timedelta

async def remind_command(interaction: discord.Interaction):
    # Get bot instance from interaction
    bot = interaction.client
    async def send_reminder():
        await interaction.followup.send(f"Reminder for {interaction.user.mention}!", ephemeral=True)
    run_time = datetime.now() + timedelta(seconds=10)
    def job_wrapper():
        bot.loop.create_task(send_reminder())
    bot.reminder_scheduler.schedule(job_wrapper, run_time)
    embed = discord.Embed(title="Reminder Set", description="Reminder set for 10 seconds from now!", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)
