import discord
from discord import app_commands
from sqlalchemy.future import select
from db.session import AsyncSessionLocal
from db.models import UserProfile

async def create_role_command(interaction: discord.Interaction, role_name: str, commands: str = ""):
    """Create a new role with optional commands"""
    bot = interaction.client

    # Only server owner can create roles
    if interaction.user.id != bot.owner_id:
        embed = discord.Embed(
            title="Permission Denied",
            description="Only the server owner can create roles.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        guild = interaction.guild

        # Check if role already exists in Discord
        existing_role = discord.utils.get(guild.roles, name=role_name)
        if existing_role:
            embed = discord.Embed(
                title="Role Already Exists",
                description=f"Role '{role_name}' already exists in this server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Create Discord role
        discord_role = await guild.create_role(name=role_name, reason="Created by bot command")

        # Parse and validate commands
        command_list = []
        if commands.strip():
            command_list = [cmd.strip() for cmd in commands.split(",") if cmd.strip()]

        # Add role to bot's permission system
        bot.permission_manager.add_role(role_name, command_list)

        embed = discord.Embed(
            title="✅ Role Created",
            description=f"Successfully created role **{role_name}**",
            color=discord.Color.green()
        )
        embed.add_field(name="Discord Role ID", value=str(discord_role.id), inline=True)
        embed.add_field(name="Commands", value=", ".join(command_list) if command_list else "None", inline=True)
        embed.add_field(name="Members", value="0", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Failed to create role: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def delete_role_command(interaction: discord.Interaction, role_name: str):
    """Delete a role and update all related data"""
    bot = interaction.client

    # Only server owner can delete roles
    if interaction.user.id != bot.owner_id:
        embed = discord.Embed(
            title="Permission Denied",
            description="Only the server owner can delete roles.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        guild = interaction.guild
        discord_role = discord.utils.get(guild.roles, name=role_name)

        if not discord_role:
            embed = discord.Embed(
                title="Role Not Found",
                description=f"Role '{role_name}' not found in this server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Count members with this role
        member_count = len(discord_role.members)

        # Remove role from all users in database
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(UserProfile))
            users = result.scalars().all()

            updated_users = 0
            for user in users:
                if user.roles and role_name in user.roles:
                    user.roles.remove(role_name)
                    updated_users += 1

            await session.commit()

        # Remove role from Discord users
        for member in discord_role.members:
            try:
                await member.remove_roles(discord_role, reason="Role deleted by bot command")
            except:
                pass

        # Remove role from bot's permission system
        bot.permission_manager.remove_role(role_name)

        # Delete Discord role
        await discord_role.delete(reason="Deleted by bot command")

        embed = discord.Embed(
            title="✅ Role Deleted",
            description=f"Successfully deleted role **{role_name}**",
            color=discord.Color.green()
        )
        embed.add_field(name="Members Updated", value=str(updated_users), inline=True)
        embed.add_field(name="Discord Members", value=str(member_count), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Failed to delete role: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def list_role_permissions_command(interaction: discord.Interaction, role_name: str):
    """List permissions/commands for a specific role"""
    bot = interaction.client

    try:
        # Check if role exists
        guild = interaction.guild
        discord_role = discord.utils.get(guild.roles, name=role_name)

        if not discord_role:
            embed = discord.Embed(
                title="Role Not Found",
                description=f"Role '{role_name}' not found in this server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Get permissions from bot's permission manager
        permissions = bot.permission_manager.get_role_permissions(role_name)

        embed = discord.Embed(
            title=f"🔐 Permissions for {role_name}",
            color=discord.Color.blue()
        )

        embed.add_field(name="Discord Role ID", value=str(discord_role.id), inline=True)
        embed.add_field(name="Members", value=str(len(discord_role.members)), inline=True)
        embed.add_field(name="Color", value=str(discord_role.color), inline=True)

        if permissions:
            permission_list = "\n".join([f"• `{perm}`" for perm in permissions])
            embed.add_field(name="Allowed Commands", value=permission_list, inline=False)
        else:
            embed.add_field(name="Allowed Commands", value="No specific permissions set", inline=False)

        embed.add_field(
            name="Management Commands",
            value="• `/add_role_permission` - Add command permission\n• `/remove_role_permission` - Remove command permission",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Failed to get role permissions: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def add_role_permission_command(interaction: discord.Interaction, role_name: str, command: str):
    """Add a command permission to a role"""
    bot = interaction.client

    # Only server owner can modify permissions
    if interaction.user.id != bot.owner_id:
        embed = discord.Embed(
            title="Permission Denied",
            description="Only the server owner can modify role permissions.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        # Check if role exists
        guild = interaction.guild
        discord_role = discord.utils.get(guild.roles, name=role_name)

        if not discord_role:
            embed = discord.Embed(
                title="Role Not Found",
                description=f"Role '{role_name}' not found in this server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Add permission
        bot.permission_manager.grant_permission(role_name, command)

        embed = discord.Embed(
            title="✅ Permission Added",
            description=f"Added command `{command}` to role **{role_name}**",
            color=discord.Color.green()
        )

        # Show updated permissions
        permissions = bot.permission_manager.get_role_permissions(role_name)
        if permissions:
            embed.add_field(name="All Permissions", value=", ".join(permissions), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Failed to add permission: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def remove_role_permission_command(interaction: discord.Interaction, role_name: str, command: str):
    """Remove a command permission from a role"""
    bot = interaction.client

    # Only server owner can modify permissions
    if interaction.user.id != bot.owner_id:
        embed = discord.Embed(
            title="Permission Denied",
            description="Only the server owner can modify role permissions.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        # Check if role exists
        guild = interaction.guild
        discord_role = discord.utils.get(guild.roles, name=role_name)

        if not discord_role:
            embed = discord.Embed(
                title="Role Not Found",
                description=f"Role '{role_name}' not found in this server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Remove permission
        success = bot.permission_manager.revoke_permission(role_name, command)

        if success:
            embed = discord.Embed(
                title="✅ Permission Removed",
                description=f"Removed command `{command}` from role **{role_name}**",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="Permission Not Found",
                description=f"Role **{role_name}** doesn't have permission for `{command}`",
                color=discord.Color.orange()
            )

        # Show updated permissions
        permissions = bot.permission_manager.get_role_permissions(role_name)
        if permissions:
            embed.add_field(name="Remaining Permissions", value=", ".join(permissions), inline=False)
        else:
            embed.add_field(name="Remaining Permissions", value="None", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Failed to remove permission: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def list_role_members_command(interaction: discord.Interaction, role_name: str):
    """List all people with a given role"""
    try:
        guild = interaction.guild
        discord_role = discord.utils.get(guild.roles, name=role_name)

        if not discord_role:
            embed = discord.Embed(
                title="Role Not Found",
                description=f"Role '{role_name}' not found in this server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        members = discord_role.members

        embed = discord.Embed(
            title=f"👥 Members with role: {role_name}",
            color=discord_role.color or discord.Color.blue()
        )

        embed.add_field(name="Total Members", value=str(len(members)), inline=True)
        embed.add_field(name="Role ID", value=str(discord_role.id), inline=True)
        embed.add_field(name="Created", value=discord_role.created_at.strftime("%Y-%m-%d"), inline=True)

        if members:
            # Split members into chunks to avoid embed limits
            member_chunks = []
            current_chunk = []
            current_length = 0

            for member in members:
                member_line = f"• {member.display_name} (`{member.id}`)"
                if current_length + len(member_line) > 1000:
                    member_chunks.append("\n".join(current_chunk))
                    current_chunk = [member_line]
                    current_length = len(member_line)
                else:
                    current_chunk.append(member_line)
                    current_length += len(member_line) + 1

            if current_chunk:
                member_chunks.append("\n".join(current_chunk))

            # Add member chunks as fields
            for i, chunk in enumerate(member_chunks):
                field_name = "Members" if i == 0 else f"Members (cont. {i+1})"
                embed.add_field(name=field_name, value=chunk, inline=False)
        else:
            embed.add_field(name="Members", value="No members have this role", inline=False)

        embed.add_field(
            name="Management Commands",
            value="• `/add_user_to_role` - Add user to role\n• `/remove_user_from_role` - Remove user from role",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Failed to list role members: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def add_user_to_role_command(interaction: discord.Interaction, user: discord.Member, role_name: str):
    """Add a user to a specific role"""
    bot = interaction.client

    # Only server owner can modify role membership
    if interaction.user.id != bot.owner_id:
        embed = discord.Embed(
            title="Permission Denied",
            description="Only the server owner can modify role membership.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        guild = interaction.guild
        discord_role = discord.utils.get(guild.roles, name=role_name)

        if not discord_role:
            embed = discord.Embed(
                title="Role Not Found",
                description=f"Role '{role_name}' not found in this server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if user already has the role
        if discord_role in user.roles:
            embed = discord.Embed(
                title="User Already Has Role",
                description=f"{user.display_name} already has the role **{role_name}**",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Add Discord role
        await user.add_roles(discord_role, reason="Added by bot command")

        # Update database
        user_profile = await bot.user_manager.get_user(user.id)
        if not user_profile:
            user_profile = await bot.user_manager.ensure_user(user.id)

        if not user_profile.roles:
            user_profile.roles = []

        if role_name not in user_profile.roles:
            user_profile.roles.append(role_name)
            await bot.user_manager.update_roles(user.id, user_profile.roles)

        embed = discord.Embed(
            title="✅ User Added to Role",
            description=f"Successfully added {user.display_name} to role **{role_name}**",
            color=discord.Color.green()
        )
        embed.add_field(name="User", value=f"{user.display_name} (`{user.id}`)", inline=True)
        embed.add_field(name="Role", value=role_name, inline=True)
        embed.add_field(name="Total Role Members", value=str(len(discord_role.members)), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Failed to add user to role: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def remove_user_from_role_command(interaction: discord.Interaction, user: discord.Member, role_name: str):
    """Remove a user from a specific role"""
    bot = interaction.client

    # Only server owner can modify role membership
    if interaction.user.id != bot.owner_id:
        embed = discord.Embed(
            title="Permission Denied",
            description="Only the server owner can modify role membership.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        guild = interaction.guild
        discord_role = discord.utils.get(guild.roles, name=role_name)

        if not discord_role:
            embed = discord.Embed(
                title="Role Not Found",
                description=f"Role '{role_name}' not found in this server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if user has the role
        if discord_role not in user.roles:
            embed = discord.Embed(
                title="User Doesn't Have Role",
                description=f"{user.display_name} doesn't have the role **{role_name}**",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Remove Discord role
        await user.remove_roles(discord_role, reason="Removed by bot command")

        # Update database
        user_profile = await bot.user_manager.get_user(user.id)
        if user_profile and user_profile.roles and role_name in user_profile.roles:
            user_profile.roles.remove(role_name)
            await bot.user_manager.update_roles(user.id, user_profile.roles)

        embed = discord.Embed(
            title="✅ User Removed from Role",
            description=f"Successfully removed {user.display_name} from role **{role_name}**",
            color=discord.Color.green()
        )
        embed.add_field(name="User", value=f"{user.display_name} (`{user.id}`)", inline=True)
        embed.add_field(name="Role", value=role_name, inline=True)
        embed.add_field(name="Total Role Members", value=str(len(discord_role.members)), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Failed to remove user from role: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def list_user_roles_command(interaction: discord.Interaction, user: discord.Member):
    """List all roles for a specific user"""
    bot = interaction.client

    try:
        # Get Discord roles
        discord_roles = [role for role in user.roles if role.name != "@everyone"]

        # Get database roles
        user_profile = await bot.user_manager.get_user(user.id)
        db_roles = user_profile.roles if user_profile and user_profile.roles else []

        embed = discord.Embed(
            title=f"🎭 Roles for {user.display_name}",
            color=user.color or discord.Color.blue()
        )

        embed.add_field(name="User ID", value=str(user.id), inline=True)
        embed.add_field(name="Joined Server", value=user.joined_at.strftime("%Y-%m-%d") if user.joined_at else "Unknown", inline=True)
        embed.add_field(name="Total Discord Roles", value=str(len(discord_roles)), inline=True)

        if discord_roles:
            discord_role_list = []
            for role in sorted(discord_roles, key=lambda r: r.position, reverse=True):
                discord_role_list.append(f"• **{role.name}** (`{role.id}`)")

            # Split into chunks if too long
            role_chunks = []
            current_chunk = []
            current_length = 0

            for role_line in discord_role_list:
                if current_length + len(role_line) > 1000:
                    role_chunks.append("\n".join(current_chunk))
                    current_chunk = [role_line]
                    current_length = len(role_line)
                else:
                    current_chunk.append(role_line)
                    current_length += len(role_line) + 1

            if current_chunk:
                role_chunks.append("\n".join(current_chunk))

            # Add role chunks as fields
            for i, chunk in enumerate(role_chunks):
                field_name = "Discord Roles" if i == 0 else f"Discord Roles (cont. {i+1})"
                embed.add_field(name=field_name, value=chunk, inline=False)
        else:
            embed.add_field(name="Discord Roles", value="No roles assigned", inline=False)

        if db_roles:
            embed.add_field(name="Database Roles", value=", ".join(db_roles), inline=False)
        else:
            embed.add_field(name="Database Roles", value="No roles in database", inline=False)

        embed.add_field(
            name="Management Commands",
            value="• `/add_user_to_role` - Add role to user\n• `/remove_user_from_role` - Remove role from user",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Failed to list user roles: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def list_all_roles_command(interaction: discord.Interaction):
    """List all roles in the server with their details"""
    try:
        guild = interaction.guild
        bot = interaction.client

        # Get all Discord roles (excluding @everyone)
        discord_roles = [role for role in guild.roles if role.name != "@everyone"]

        # Sort roles by position (highest first)
        discord_roles.sort(key=lambda r: r.position, reverse=True)

        embed = discord.Embed(
            title="🎭 All Server Roles",
            description=f"Total roles: {len(discord_roles)}",
            color=discord.Color.blue()
        )

        if not discord_roles:
            embed.add_field(name="No Roles", value="No custom roles found in this server", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Split roles into chunks to avoid embed limits
        role_chunks = []
        current_chunk = []
        current_length = 0

        for role in discord_roles:
            # Get bot permissions for this role
            bot_permissions = bot.permission_manager.get_role_permissions(role.name)
            perm_count = len(bot_permissions)

            role_line = f"• **{role.name}** (`{role.id}`) - {len(role.members)} members"
            if perm_count > 0:
                role_line += f" - {perm_count} bot permissions"

            if current_length + len(role_line) > 1000:
                role_chunks.append("\n".join(current_chunk))
                current_chunk = [role_line]
                current_length = len(role_line)
            else:
                current_chunk.append(role_line)
                current_length += len(role_line) + 1

        if current_chunk:
            role_chunks.append("\n".join(current_chunk))

        # Add role chunks as fields
        for i, chunk in enumerate(role_chunks):
            field_name = "Roles" if i == 0 else f"Roles (cont. {i+1})"
            embed.add_field(name=field_name, value=chunk, inline=False)

        # Add management commands info
        embed.add_field(
            name="📋 Management Commands",
            value="• `/create_role` - Create new role\n• `/delete_role` - Delete role\n• `/list_role_permissions` - View role permissions\n• `/list_role_members` - View role members\n• `/list_user_roles` - View user's roles",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Failed to list roles: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)