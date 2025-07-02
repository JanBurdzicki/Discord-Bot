import discord
from typing import Optional, Any
import json

# ========== User Information Commands ==========

async def user_status_command(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    """Show user status and preferences"""
    try:
        target_user = user or interaction.user
        # Only allow admins to check others' status
        if user and interaction.user != user and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You can only check your own status.", ephemeral=True)
            return

        status = await interaction.client.user_manager.get_user_status(target_user.id)

        if not status['exists']:
            embed = discord.Embed(
                title="❌ User Not Found",
                description=f"{target_user.display_name} is not registered in the system.",
                color=0xff0000
            )
            embed.add_field(name="💡 Tip", value="Use any bot command to automatically create your profile!", inline=False)
        else:
            embed = discord.Embed(
                title=f"👤 User Status - {target_user.display_name}",
                color=0x3498db
            )

            embed.add_field(name="📧 Calendar Email", value=status['calendar_email'], inline=True)
            embed.add_field(name="🔧 Preferences", value=f"{status['preference_count']} set", inline=True)
            embed.add_field(name="🏷️ Roles", value=f"{status['role_count']} assigned", inline=True)

            # Show roles if any
            if status['roles']:
                roles_text = ', '.join(status['roles'][:5])  # Show first 5 roles
                if len(status['roles']) > 5:
                    roles_text += f" (+{len(status['roles']) - 5} more)"
                embed.add_field(name="📋 Your Roles", value=roles_text, inline=False)

            # Show some preferences if any
            if status['preferences']:
                prefs_preview = []
                for key, value in list(status['preferences'].items())[:3]:  # Show first 3
                    prefs_preview.append(f"**{key}:** {str(value)[:50]}")
                if len(status['preferences']) > 3:
                    prefs_preview.append(f"...and {len(status['preferences']) - 3} more")
                embed.add_field(name="⚙️ Preferences Preview", value='\n'.join(prefs_preview), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

# ========== Preference Management Commands ==========

async def set_preference_command(interaction: discord.Interaction, key: str, value: str):
    """Set a user preference"""
    try:
        # Try to parse value as JSON for complex types
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            # If not valid JSON, keep as string
            parsed_value = value

        success = await interaction.client.user_manager.set_preference(interaction.user.id, key, parsed_value)

        if success:
            embed = discord.Embed(
                title="✅ Preference Set",
                description=f"Successfully set preference `{key}`",
                color=0x00ff00
            )
            embed.add_field(name="Key", value=key, inline=True)
            embed.add_field(name="Value", value=str(parsed_value)[:100], inline=True)
        else:
            embed = discord.Embed(
                title="❌ Failed to Set Preference",
                description="Could not set the preference. Please try again.",
                color=0xff0000
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

async def get_preference_command(interaction: discord.Interaction, key: str):
    """Get a user preference"""
    try:
        value = await interaction.client.user_manager.get_preference(interaction.user.id, key)

        if value is None:
            embed = discord.Embed(
                title="❌ Preference Not Found",
                description=f"No preference found for key `{key}`",
                color=0xff0000
            )
        else:
            embed = discord.Embed(
                title="✅ Preference Value",
                color=0x3498db
            )
            embed.add_field(name="Key", value=key, inline=True)
            embed.add_field(name="Value", value=str(value), inline=True)
            embed.add_field(name="Type", value=type(value).__name__, inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

async def remove_preference_command(interaction: discord.Interaction, key: str):
    """Remove a user preference"""
    try:
        success = await interaction.client.user_manager.remove_preference(interaction.user.id, key)

        if success:
            embed = discord.Embed(
                title="✅ Preference Removed",
                description=f"Successfully removed preference `{key}`",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ Preference Not Found",
                description=f"No preference found for key `{key}`",
                color=0xff0000
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

async def list_preferences_command(interaction: discord.Interaction):
    """List all user preferences"""
    try:
        status = await interaction.client.user_manager.get_user_status(interaction.user.id)

        if not status['exists'] or not status['preferences']:
            embed = discord.Embed(
                title="📝 No Preferences",
                description="You don't have any preferences set yet.",
                color=0x95a5a6
            )
            embed.add_field(name="💡 Tip", value="Use `/set_preference` to add preferences!", inline=False)
        else:
            embed = discord.Embed(
                title="⚙️ Your Preferences",
                description=f"You have {len(status['preferences'])} preferences set",
                color=0x3498db
            )

            # Show preferences (limit to avoid message being too long)
            prefs_shown = 0
            for key, value in status['preferences'].items():
                if prefs_shown >= 10:  # Limit to 10 preferences per message
                    break

                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:97] + "..."

                embed.add_field(
                    name=f"🔑 {key}",
                    value=f"**Type:** {type(value).__name__}\n**Value:** {value_str}",
                    inline=True
                )
                prefs_shown += 1

            if len(status['preferences']) > 10:
                embed.set_footer(text=f"Showing 10 of {len(status['preferences'])} preferences")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

async def clear_preferences_command(interaction: discord.Interaction):
    """Clear all user preferences with confirmation"""
    try:
        # Create confirmation view
        view = ConfirmationView()
        embed = discord.Embed(
            title="⚠️ Confirm Clear Preferences",
            description="Are you sure you want to clear ALL your preferences?\n\n**This action cannot be undone!**",
            color=0xe74c3c
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        # Wait for user interaction
        await view.wait()

        if view.confirmed:
            success = await interaction.client.user_manager.clear_preferences(interaction.user.id)

            if success:
                embed = discord.Embed(
                    title="✅ Preferences Cleared",
                    description="All your preferences have been cleared successfully.",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="❌ Clear Failed",
                    description="Could not clear preferences. You might not have any set.",
                    color=0xff0000
                )

            await interaction.edit_original_response(embed=embed, view=None)
        else:
            embed = discord.Embed(
                title="❌ Cancelled",
                description="Preference clearing was cancelled.",
                color=0x95a5a6
            )
            await interaction.edit_original_response(embed=embed, view=None)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

# ========== User Info Management Commands ==========

async def update_calendar_email_command(interaction: discord.Interaction, email: str):
    """Update user's calendar email"""
    try:
        # Basic email validation
        if '@' not in email or '.' not in email:
            await interaction.response.send_message("❌ Please provide a valid email address.", ephemeral=True)
            return

        success = await interaction.client.user_manager.update_user_info(interaction.user.id, calendar_email=email)

        if success:
            embed = discord.Embed(
                title="✅ Calendar Email Updated",
                description=f"Your calendar email has been updated to: {email}",
                color=0x00ff00
            )
        else:
            # User doesn't exist, create them
            await interaction.client.user_manager.ensure_user(interaction.user.id, calendar_email=email)
            embed = discord.Embed(
                title="✅ Profile Created & Email Set",
                description=f"Created your profile and set calendar email to: {email}",
                color=0x00ff00
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

# ========== Admin Commands ==========

async def manage_user_role_command(
    interaction: discord.Interaction,
    user: discord.Member,
    role: str,
    action: str = "add"
):
    """Manage user roles (Admin only)"""
    try:
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return

        if action == "add":
            success = await interaction.client.user_manager.add_role(user.id, role)
            action_text = "added to" if success else "already assigned to"
        else:  # remove
            success = await interaction.client.user_manager.remove_role(user.id, role)
            action_text = "removed from" if success else "was not assigned to"

        embed = discord.Embed(
            title=f"✅ Role {'Added' if action == 'add' else 'Removed'}",
            description=f"Role `{role}` has been {action_text} {user.display_name}",
            color=0x00ff00 if success else 0xf39c12
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

async def user_admin_info_command(interaction: discord.Interaction, user: discord.Member):
    """Get detailed user information (Admin only)"""
    try:
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return

        status = await interaction.client.user_manager.get_user_status(user.id)

        embed = discord.Embed(
            title=f"🔍 Admin User Info - {user.display_name}",
            color=0x3498db
        )

        if not status['exists']:
            embed.description = "User is not registered in the system."
            embed.color = 0xff0000
        else:
            embed.add_field(name="📧 Calendar Email", value=status['calendar_email'], inline=True)
            embed.add_field(name="🔧 Preferences", value=str(status['preference_count']), inline=True)
            embed.add_field(name="🏷️ Roles", value=str(status['role_count']), inline=True)

            if status['roles']:
                embed.add_field(name="📋 Assigned Roles", value=', '.join(status['roles']), inline=False)

            if status['preferences']:
                prefs_text = ""
                for key, value in status['preferences'].items():
                    value_str = str(value)[:50]
                    prefs_text += f"**{key}:** {value_str}\n"
                embed.add_field(name="⚙️ All Preferences", value=prefs_text[:1024], inline=False)

        embed.add_field(name="👤 Discord Info",
                      value=f"**ID:** {user.id}\n**Created:** {user.created_at.strftime('%Y-%m-%d')}",
                      inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

# ========== Legacy Commands (for backward compatibility) ==========

async def add_user_command(interaction: discord.Interaction, user: discord.Member, email: str):
    """Add a user with email (legacy function)"""
    try:
        await interaction.client.user_manager.ensure_user(user.id, calendar_email=email)
        embed = discord.Embed(title="Success", description=f"Added user <@{user.id}> with email {email}.", color=discord.Color.green())
    except Exception as e:
        embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def update_roles_command(interaction: discord.Interaction, user: discord.Member, roles: str):
    """Update roles for a user (legacy function)"""
    try:
        role_list = [r.strip() for r in roles.split(",") if r.strip()]
        await interaction.client.user_manager.update_roles(user.id, role_list)

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


# ========== UI Components ==========

class ConfirmationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30.0)
        self.confirmed = False

    @discord.ui.button(label="Yes, Clear All", style=discord.ButtonStyle.danger)
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.confirmed = True
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.confirmed = False
        self.stop()
