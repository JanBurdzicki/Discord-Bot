import discord

async def add_user_command(interaction: discord.Interaction, user: discord.Member, email: str):
    # Get bot instance from interaction
    bot = interaction.client
    try:
        await bot.user_manager.ensure_user(user.id, calendar_email=email)
        embed = discord.Embed(title="Success", description=f"Added user <@{user.id}> with email {email}.", color=discord.Color.green())
    except Exception as e:
        embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def update_roles_command(interaction: discord.Interaction, user: discord.Member, roles: str):
    # Get bot instance from interaction
    bot = interaction.client
    try:
        role_list = [r.strip() for r in roles.split(",") if r.strip()]
        await bot.user_manager.update_roles(user.id, role_list)

        # Also update Discord roles
        guild = interaction.guild
        member = guild.get_member(user.id)
        if member:
            # Remove all bot-managed roles first
            bot_roles = [role for role in member.roles if role.name in role_list]
            # Add the new roles
            for role_name in role_list:
                discord_role = discord.utils.get(guild.roles, name=role_name)
                if not discord_role:
                    discord_role = await guild.create_role(name=role_name, reason="Created by bot command")
                if discord_role not in member.roles:
                    await member.add_roles(discord_role, reason="Updated by bot command")

        embed = discord.Embed(title="Success", description=f"Updated roles for <@{user.id}>: {roles}", color=discord.Color.green())
    except Exception as e:
        embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def update_preferences_command(interaction: discord.Interaction, key: str, value: str):
    # Get bot instance from interaction
    bot = interaction.client
    try:
        await bot.user_manager.update_preferences(interaction.user.id, {key: value})
        embed = discord.Embed(title="Success", description=f"Updated your preferences: {key} = {value}", color=discord.Color.green())
    except Exception as e:
        embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
    await interaction.response.send_message(embed=embed, ephemeral=True)
