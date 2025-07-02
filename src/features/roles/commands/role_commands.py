"""Role Management Commands"""

import discord
from discord import app_commands
from typing import Dict, Any, List
from src.core.builders import EmbedBuilder


class RoleCommands:
    """Container for all role management commands"""

    def __init__(self, bot, container):
        self.bot = bot
        self.container = container

    # ========== Create Role Command ==========

    def create_role_command(self) -> app_commands.Command:
        """Create a new role with optional command permissions (Owner only)"""
        @app_commands.command(name="create_role", description="Create a new role with optional command permissions")
        @app_commands.describe(
            role_name="Name of the role to create",
            commands="Comma-separated list of commands (optional)"
        )
        async def command(interaction: discord.Interaction, role_name: str, commands: str = ""):
            try:
                # Only server owner can create roles
                if interaction.user.id != self.bot.owner_id:
                    embed = EmbedBuilder()\
                        .set_title("❌ Permission Denied")\
                        .set_description("Only the server owner can create roles.")\
                        .set_color(0xff0000)\
                        .build()
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                guild = interaction.guild

                # Check if role already exists in Discord
                existing_role = discord.utils.get(guild.roles, name=role_name)
                if existing_role:
                    embed = EmbedBuilder()\
                        .set_title("❌ Role Already Exists")\
                        .set_description(f"Role '{role_name}' already exists in this server.")\
                        .set_color(0xff0000)\
                        .build()
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Create Discord role
                discord_role = await guild.create_role(name=role_name, reason="Created by bot command")

                # Parse and validate commands
                command_list = []
                if commands.strip():
                    command_list = [cmd.strip() for cmd in commands.split(",") if cmd.strip()]

                # Add role to permission manager (if available)
                try:
                    permission_manager = self.container.get("permission_manager")
                    if permission_manager:
                        permission_manager.add_role(role_name, command_list)
                except:
                    pass  # Permission manager might not be available

                embed = EmbedBuilder()\
                    .set_title("✅ Role Created")\
                    .set_description(f"Successfully created role **{role_name}**")\
                    .set_color(0x00ff00)\
                    .add_field("Discord Role ID", str(discord_role.id), True)\
                    .add_field("Commands", ", ".join(command_list) if command_list else "None", True)\
                    .add_field("Members", "0", True)\
                    .build()

                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                embed = EmbedBuilder()\
                    .set_title("❌ Error")\
                    .set_description(f"Failed to create role: {str(e)}")\
                    .set_color(0xff0000)\
                    .build()
                await interaction.response.send_message(embed=embed, ephemeral=True)

        return command

    # ========== Delete Role Command ==========

    def delete_role_command(self) -> app_commands.Command:
        """Delete a role and update all related data (Owner only)"""
        @app_commands.command(name="delete_role", description="Delete a role and update all related data")
        @app_commands.describe(role_name="Name of the role to delete")
        async def command(interaction: discord.Interaction, role_name: str):
            try:
                # Only server owner can delete roles
                if interaction.user.id != self.bot.owner_id:
                    embed = EmbedBuilder()\
                        .set_title("❌ Permission Denied")\
                        .set_description("Only the server owner can delete roles.")\
                        .set_color(0xff0000)\
                        .build()
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                guild = interaction.guild
                discord_role = discord.utils.get(guild.roles, name=role_name)

                if not discord_role:
                    embed = EmbedBuilder()\
                        .set_title("❌ Role Not Found")\
                        .set_description(f"Role '{role_name}' not found in this server.")\
                        .set_color(0xff0000)\
                        .build()
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Count members with this role
                member_count = len(discord_role.members)

                # Remove role from all users in database
                updated_users = 0
                try:
                    user_service = self.container.get("user_service")
                    if user_service:
                        updated_users = await user_service.remove_role_from_all_users(role_name)
                except:
                    pass

                # Remove role from Discord users
                for member in discord_role.members:
                    try:
                        await member.remove_roles(discord_role, reason="Role deleted by bot command")
                    except:
                        pass

                # Remove role from permission manager
                try:
                    permission_manager = self.container.get("permission_manager")
                    if permission_manager:
                        permission_manager.remove_role(role_name)
                except:
                    pass

                # Delete Discord role
                await discord_role.delete(reason="Deleted by bot command")

                embed = EmbedBuilder()\
                    .set_title("✅ Role Deleted")\
                    .set_description(f"Successfully deleted role **{role_name}**")\
                    .set_color(0x00ff00)\
                    .add_field("Database Users Updated", str(updated_users), True)\
                    .add_field("Discord Members", str(member_count), True)\
                    .build()

                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                embed = EmbedBuilder()\
                    .set_title("❌ Error")\
                    .set_description(f"Failed to delete role: {str(e)}")\
                    .set_color(0xff0000)\
                    .build()
                await interaction.response.send_message(embed=embed, ephemeral=True)

        return command

    # ========== List Role Permissions Command ==========

    def list_role_permissions_command(self) -> app_commands.Command:
        """List permissions/commands for a specific role"""
        @app_commands.command(name="list_role_permissions", description="List permissions/commands for a specific role")
        @app_commands.describe(role_name="Name of the role")
        async def command(interaction: discord.Interaction, role_name: str):
            try:
                # Check if role exists
                guild = interaction.guild
                discord_role = discord.utils.get(guild.roles, name=role_name)

                if not discord_role:
                    embed = EmbedBuilder()\
                        .set_title("❌ Role Not Found")\
                        .set_description(f"Role '{role_name}' not found in this server.")\
                        .set_color(0xff0000)\
                        .build()
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Get permissions from permission manager
                permissions = []
                try:
                    permission_manager = self.container.get("permission_manager")
                    if permission_manager:
                        permissions = permission_manager.get_role_permissions(role_name)
                except:
                    pass

                embed = EmbedBuilder()\
                    .set_title(f"🔐 Permissions for {role_name}")\
                    .set_color(0x0099ff)\
                    .add_field("Discord Role ID", str(discord_role.id), True)\
                    .add_field("Members", str(len(discord_role.members)), True)\
                    .add_field("Color", str(discord_role.color), True)

                if permissions:
                    permission_list = "\n".join([f"• `{perm}`" for perm in permissions])
                    embed.add_field("Allowed Commands", permission_list, False)
                else:
                    embed.add_field("Allowed Commands", "No specific permissions set", False)

                embed.add_field(
                    "Management Commands",
                    "• `/add_role_permission` - Add command permission\n• `/remove_role_permission` - Remove command permission",
                    False
                )

                await interaction.response.send_message(embed=embed.build(), ephemeral=True)

            except Exception as e:
                embed = EmbedBuilder()\
                    .set_title("❌ Error")\
                    .set_description(f"Failed to get role permissions: {str(e)}")\
                    .set_color(0xff0000)\
                    .build()
                await interaction.response.send_message(embed=embed, ephemeral=True)

        return command

    # ========== Add Role Permission Command ==========

    def add_role_permission_command(self) -> app_commands.Command:
        """Add a command permission to a role (Owner only)"""
        @app_commands.command(name="add_role_permission", description="Add a command permission to a role")
        @app_commands.describe(
            role_name="Name of the role",
            command="Command to allow"
        )
        async def command(interaction: discord.Interaction, role_name: str, command: str):
            try:
                # Only server owner can modify permissions
                if interaction.user.id != self.bot.owner_id:
                    embed = EmbedBuilder()\
                        .set_title("❌ Permission Denied")\
                        .set_description("Only the server owner can modify role permissions.")\
                        .set_color(0xff0000)\
                        .build()
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Check if role exists
                guild = interaction.guild
                discord_role = discord.utils.get(guild.roles, name=role_name)

                if not discord_role:
                    embed = EmbedBuilder()\
                        .set_title("❌ Role Not Found")\
                        .set_description(f"Role '{role_name}' not found in this server.")\
                        .set_color(0xff0000)\
                        .build()
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Add permission
                try:
                    permission_manager = self.container.get("permission_manager")
                    if permission_manager:
                        permission_manager.grant_permission(role_name, command)
                except:
                    pass

                embed = EmbedBuilder()\
                    .set_title("✅ Permission Added")\
                    .set_description(f"Added command `{command}` to role **{role_name}**")\
                    .set_color(0x00ff00)

                # Show updated permissions
                try:
                    permission_manager = self.container.get("permission_manager")
                    if permission_manager:
                        permissions = permission_manager.get_role_permissions(role_name)
                        if permissions:
                            embed.add_field("All Permissions", ", ".join(permissions), False)
                except:
                    pass

                await interaction.response.send_message(embed=embed.build(), ephemeral=True)

            except Exception as e:
                embed = EmbedBuilder()\
                    .set_title("❌ Error")\
                    .set_description(f"Failed to add permission: {str(e)}")\
                    .set_color(0xff0000)\
                    .build()
                await interaction.response.send_message(embed=embed, ephemeral=True)

        return command

    # ========== Remove Role Permission Command ==========

    def remove_role_permission_command(self) -> app_commands.Command:
        """Remove a command permission from a role (Owner only)"""
        @app_commands.command(name="remove_role_permission", description="Remove a command permission from a role")
        @app_commands.describe(
            role_name="Name of the role",
            command="Command to remove"
        )
        async def command(interaction: discord.Interaction, role_name: str, command: str):
            try:
                # Only server owner can modify permissions
                if interaction.user.id != self.bot.owner_id:
                    embed = EmbedBuilder()\
                        .set_title("❌ Permission Denied")\
                        .set_description("Only the server owner can modify role permissions.")\
                        .set_color(0xff0000)\
                        .build()
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Check if role exists
                guild = interaction.guild
                discord_role = discord.utils.get(guild.roles, name=role_name)

                if not discord_role:
                    embed = EmbedBuilder()\
                        .set_title("❌ Role Not Found")\
                        .set_description(f"Role '{role_name}' not found in this server.")\
                        .set_color(0xff0000)\
                        .build()
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Remove permission
                success = False
                try:
                    permission_manager = self.container.get("permission_manager")
                    if permission_manager:
                        success = permission_manager.revoke_permission(role_name, command)
                except:
                    pass

                if success:
                    embed = EmbedBuilder()\
                        .set_title("✅ Permission Removed")\
                        .set_description(f"Removed command `{command}` from role **{role_name}**")\
                        .set_color(0x00ff00)
                else:
                    embed = EmbedBuilder()\
                        .set_title("❌ Permission Not Found")\
                        .set_description(f"Role **{role_name}** doesn't have permission for `{command}`")\
                        .set_color(0xf39c12)

                # Show updated permissions
                try:
                    permission_manager = self.container.get("permission_manager")
                    if permission_manager:
                        permissions = permission_manager.get_role_permissions(role_name)
                        if permissions:
                            embed.add_field("Remaining Permissions", ", ".join(permissions), False)
                        else:
                            embed.add_field("Remaining Permissions", "None", False)
                except:
                    pass

                await interaction.response.send_message(embed=embed.build(), ephemeral=True)

            except Exception as e:
                embed = EmbedBuilder()\
                    .set_title("❌ Error")\
                    .set_description(f"Failed to remove permission: {str(e)}")\
                    .set_color(0xff0000)\
                    .build()
                await interaction.response.send_message(embed=embed, ephemeral=True)

        return command

    # ========== List Role Members Command ==========

    def list_role_members_command(self) -> app_commands.Command:
        """List all members with a specific role"""
        @app_commands.command(name="list_role_members", description="List all members with a specific role")
        @app_commands.describe(role_name="Name of the role")
        async def command(interaction: discord.Interaction, role_name: str):
            try:
                guild = interaction.guild
                discord_role = discord.utils.get(guild.roles, name=role_name)

                if not discord_role:
                    embed = EmbedBuilder()\
                        .set_title("❌ Role Not Found")\
                        .set_description(f"Role '{role_name}' not found in this server.")\
                        .set_color(0xff0000)\
                        .build()
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                members = discord_role.members

                embed = EmbedBuilder()\
                    .set_title(f"👥 Members with role {role_name}")\
                    .set_description(f"Total members: {len(members)}")\
                    .set_color(0x0099ff)\
                    .add_field("Role ID", str(discord_role.id), True)\
                    .add_field("Role Color", str(discord_role.color), True)

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
                        embed.add_field(field_name, chunk, False)
                else:
                    embed.add_field("Members", "No members have this role", False)

                await interaction.response.send_message(embed=embed.build(), ephemeral=True)

            except Exception as e:
                embed = EmbedBuilder()\
                    .set_title("❌ Error")\
                    .set_description(f"Failed to list role members: {str(e)}")\
                    .set_color(0xff0000)\
                    .build()
                await interaction.response.send_message(embed=embed, ephemeral=True)

        return command

    # ========== Add User to Role Command ==========

    def add_user_to_role_command(self) -> app_commands.Command:
        """Add a user to a specific role (Owner only)"""
        @app_commands.command(name="add_user_to_role", description="Add a user to a specific role")
        @app_commands.describe(
            user="User to add to role",
            role_name="Name of the role"
        )
        async def command(interaction: discord.Interaction, user: discord.Member, role_name: str):
            try:
                # Only server owner can modify role membership
                if interaction.user.id != self.bot.owner_id:
                    embed = EmbedBuilder()\
                        .set_title("❌ Permission Denied")\
                        .set_description("Only the server owner can modify role membership.")\
                        .set_color(0xff0000)\
                        .build()
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                guild = interaction.guild
                discord_role = discord.utils.get(guild.roles, name=role_name)

                if not discord_role:
                    embed = EmbedBuilder()\
                        .set_title("❌ Role Not Found")\
                        .set_description(f"Role '{role_name}' not found in this server.")\
                        .set_color(0xff0000)\
                        .build()
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Check if user already has the role
                if discord_role in user.roles:
                    embed = EmbedBuilder()\
                        .set_title("❌ User Already Has Role")\
                        .set_description(f"{user.display_name} already has the role **{role_name}**")\
                        .set_color(0xf39c12)\
                        .build()
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Add Discord role
                await user.add_roles(discord_role, reason="Added by bot command")

                # Update database
                try:
                    user_service = self.container.get("user_service")
                    if user_service:
                        await user_service.add_role(user.id, role_name)
                except:
                    pass

                embed = EmbedBuilder()\
                    .set_title("✅ Role Added")\
                    .set_description(f"Added role **{role_name}** to {user.display_name}")\
                    .set_color(0x00ff00)\
                    .add_field("User", f"{user.display_name} (`{user.id}`)", True)\
                    .add_field("Role", f"{role_name} (`{discord_role.id}`)", True)\
                    .build()

                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                embed = EmbedBuilder()\
                    .set_title("❌ Error")\
                    .set_description(f"Failed to add user to role: {str(e)}")\
                    .set_color(0xff0000)\
                    .build()
                await interaction.response.send_message(embed=embed, ephemeral=True)

        return command

    # ========== Remove User from Role Command ==========

    def remove_user_from_role_command(self) -> app_commands.Command:
        """Remove a user from a specific role (Owner only)"""
        @app_commands.command(name="remove_user_from_role", description="Remove a user from a specific role")
        @app_commands.describe(
            user="User to remove from role",
            role_name="Name of the role"
        )
        async def command(interaction: discord.Interaction, user: discord.Member, role_name: str):
            try:
                # Only server owner can modify role membership
                if interaction.user.id != self.bot.owner_id:
                    embed = EmbedBuilder()\
                        .set_title("❌ Permission Denied")\
                        .set_description("Only the server owner can modify role membership.")\
                        .set_color(0xff0000)\
                        .build()
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                guild = interaction.guild
                discord_role = discord.utils.get(guild.roles, name=role_name)

                if not discord_role:
                    embed = EmbedBuilder()\
                        .set_title("❌ Role Not Found")\
                        .set_description(f"Role '{role_name}' not found in this server.")\
                        .set_color(0xff0000)\
                        .build()
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Check if user has the role
                if discord_role not in user.roles:
                    embed = EmbedBuilder()\
                        .set_title("❌ User Doesn't Have Role")\
                        .set_description(f"{user.display_name} doesn't have the role **{role_name}**")\
                        .set_color(0xf39c12)\
                        .build()
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Remove Discord role
                await user.remove_roles(discord_role, reason="Removed by bot command")

                # Update database
                try:
                    user_service = self.container.get("user_service")
                    if user_service:
                        await user_service.remove_role(user.id, role_name)
                except:
                    pass

                embed = EmbedBuilder()\
                    .set_title("✅ Role Removed")\
                    .set_description(f"Removed role **{role_name}** from {user.display_name}")\
                    .set_color(0x00ff00)\
                    .add_field("User", f"{user.display_name} (`{user.id}`)", True)\
                    .add_field("Role", f"{role_name} (`{discord_role.id}`)", True)\
                    .build()

                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                embed = EmbedBuilder()\
                    .set_title("❌ Error")\
                    .set_description(f"Failed to remove user from role: {str(e)}")\
                    .set_color(0xff0000)\
                    .build()
                await interaction.response.send_message(embed=embed, ephemeral=True)

        return command

    # ========== List User Roles Command ==========

    def list_user_roles_command(self) -> app_commands.Command:
        """List all roles for a specific user"""
        @app_commands.command(name="list_user_roles", description="List all roles for a specific user")
        @app_commands.describe(user="User to check roles for")
        async def command(interaction: discord.Interaction, user: discord.Member):
            try:
                # Get Discord roles (excluding @everyone)
                discord_roles = [role for role in user.roles if role.name != "@everyone"]

                # Get database roles
                db_roles = []
                try:
                    user_service = self.container.get("user_service")
                    if user_service:
                        user_status = await user_service.get_user_status(user.id)
                        db_roles = user_status.get('roles', [])
                except:
                    pass

                embed = EmbedBuilder()\
                    .set_title(f"🎭 Roles for {user.display_name}")\
                    .set_description(f"Discord roles: {len(discord_roles)} | Database roles: {len(db_roles)}")\
                    .set_color(0x0099ff)\
                    .add_field("User ID", str(user.id), True)\
                    .add_field("Account Created", user.created_at.strftime("%Y-%m-%d"), True)

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
                        embed.add_field(field_name, chunk, False)
                else:
                    embed.add_field("Discord Roles", "No roles assigned", False)

                if db_roles:
                    embed.add_field("Database Roles", ", ".join(db_roles), False)
                else:
                    embed.add_field("Database Roles", "No roles in database", False)

                embed.add_field(
                    "Management Commands",
                    "• `/add_user_to_role` - Add role to user\n• `/remove_user_from_role` - Remove role from user",
                    False
                )

                await interaction.response.send_message(embed=embed.build(), ephemeral=True)

            except Exception as e:
                embed = EmbedBuilder()\
                    .set_title("❌ Error")\
                    .set_description(f"Failed to list user roles: {str(e)}")\
                    .set_color(0xff0000)\
                    .build()
                await interaction.response.send_message(embed=embed, ephemeral=True)

        return command

    # ========== List All Roles Command ==========

    def list_all_roles_command(self) -> app_commands.Command:
        """List all roles in the server with their details"""
        @app_commands.command(name="list_all_roles", description="List all roles in the server with their details")
        async def command(interaction: discord.Interaction):
            try:
                guild = interaction.guild

                # Get all Discord roles (excluding @everyone)
                discord_roles = [role for role in guild.roles if role.name != "@everyone"]

                # Sort roles by position (highest first)
                discord_roles.sort(key=lambda r: r.position, reverse=True)

                embed = EmbedBuilder()\
                    .set_title("🎭 All Server Roles")\
                    .set_description(f"Total roles: {len(discord_roles)}")\
                    .set_color(0x0099ff)

                if not discord_roles:
                    embed.add_field("No Roles", "No custom roles found in this server", False)
                    await interaction.response.send_message(embed=embed.build(), ephemeral=True)
                    return

                # Split roles into chunks to avoid embed limits
                role_chunks = []
                current_chunk = []
                current_length = 0

                for role in discord_roles:
                    # Get bot permissions for this role
                    bot_permissions = []
                    perm_count = 0
                    try:
                        permission_manager = self.container.get("permission_manager")
                        if permission_manager:
                            bot_permissions = permission_manager.get_role_permissions(role.name)
                            perm_count = len(bot_permissions)
                    except:
                        pass

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
                    embed.add_field(field_name, chunk, False)

                # Add management commands info
                embed.add_field(
                    "📋 Management Commands",
                    "• `/create_role` - Create new role\n• `/delete_role` - Delete role\n• `/list_role_permissions` - View role permissions\n• `/list_role_members` - View role members\n• `/list_user_roles` - View user's roles",
                    False
                )

                await interaction.response.send_message(embed=embed.build(), ephemeral=True)

            except Exception as e:
                embed = EmbedBuilder()\
                    .set_title("❌ Error")\
                    .set_description(f"Failed to list roles: {str(e)}")\
                    .set_color(0xff0000)\
                    .build()
                await interaction.response.send_message(embed=embed, ephemeral=True)

        return command
