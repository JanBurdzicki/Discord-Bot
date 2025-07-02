"""
Discord commands for the user management system.
Provides commands for managing user profiles, preferences, and roles.
"""

from typing import Optional, List
import discord
from discord import app_commands
import json

from ..services.user_service import UserService
from src.core.base_command import BaseCommand
from src.core.builders import EmbedBuilder
from src.shared.views import ConfirmationView

class UserCommands:
    """
    Commands for managing users and preferences.
    Provides user-facing commands for all user management functionality.
    """

    def __init__(self, user_service: UserService):
        self.service = user_service
        self._setup_commands()

    def _setup_commands(self):
        """Set up all user commands"""
        self.commands = [
            self.user_status_command(),
            self.set_preference_command(),
            self.get_preference_command(),
            self.remove_preference_command(),
            self.list_preferences_command(),
            self.clear_preferences_command(),
            self.update_calendar_email_command(),
            self.manage_user_role_command(),
            self.user_admin_info_command(),
            self.update_roles_command()
        ]

    def get_all_commands(self) -> List[app_commands.Command]:
        """Get all user commands"""
        return self.commands

    # ========== User Status Commands ==========

    def user_status_command(self) -> app_commands.Command:
        """Command to check user status and preferences"""
        @app_commands.command(name="user_status", description="Check your current user status and preferences")
        @app_commands.describe(user="User to check (admin only)")
        async def command(interaction: discord.Interaction, user: Optional[discord.Member] = None):
            try:
                target_user = user or interaction.user
                # Only allow admins to check others' status
                if user and interaction.user != user and not interaction.user.guild_permissions.administrator:
                    await interaction.response.send_message("❌ You can only check your own status.", ephemeral=True)
                    return

                status = await self.service.get_user_status(target_user.id)
                embed = self.service.build_user_status_embed(target_user, status)
                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

        return command

    # ========== Preference Commands ==========

    def set_preference_command(self) -> app_commands.Command:
        """Command to set a user preference"""
        @app_commands.command(name="set_preference", description="Set a preference value")
        @app_commands.describe(key="Preference key", value="Preference value")
        async def command(interaction: discord.Interaction, key: str, value: str):
            try:
                # Try to parse value as JSON for complex types
                try:
                    parsed_value = json.loads(value)
                except json.JSONDecodeError:
                    # If not valid JSON, keep as string
                    parsed_value = value

                success = await self.service.set_preference(interaction.user.id, key, parsed_value)

                if success:
                    embed = EmbedBuilder()\
                        .set_title("✅ Preference Set")\
                        .set_description(f"Successfully set preference `{key}`")\
                        .set_color(0x00ff00)\
                        .add_field("Key", key, inline=True)\
                        .add_field("Value", str(parsed_value)[:100], inline=True)\
                        .build()
                else:
                    embed = EmbedBuilder()\
                        .set_title("❌ Failed to Set Preference")\
                        .set_description("Could not set the preference. Please try again.")\
                        .set_color(0xff0000)\
                        .build()

                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

        return command

    def get_preference_command(self) -> app_commands.Command:
        """Command to get a user preference"""
        @app_commands.command(name="get_preference", description="Get a preference value")
        @app_commands.describe(key="Preference key")
        async def command(interaction: discord.Interaction, key: str):
            try:
                value = await self.service.get_preference(interaction.user.id, key)

                if value is not None:
                    embed = EmbedBuilder()\
                        .set_title("⚙️ Preference Value")\
                        .set_description(f"Value for preference `{key}`")\
                        .set_color(0x3498db)\
                        .add_field("Key", key, inline=True)\
                        .add_field("Value", str(value)[:1000], inline=True)\
                        .build()
                else:
                    embed = EmbedBuilder()\
                        .set_title("❌ Preference Not Found")\
                        .set_description(f"No value found for preference `{key}`")\
                        .set_color(0xff0000)\
                        .build()

                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

        return command

    def remove_preference_command(self) -> app_commands.Command:
        """Command to remove a user preference"""
        @app_commands.command(name="remove_preference", description="Remove a preference")
        @app_commands.describe(key="Preference key")
        async def command(interaction: discord.Interaction, key: str):
            try:
                success = await self.service.remove_preference(interaction.user.id, key)

                if success:
                    embed = EmbedBuilder()\
                        .set_title("✅ Preference Removed")\
                        .set_description(f"Successfully removed preference `{key}`")\
                        .set_color(0x00ff00)\
                        .build()
                else:
                    embed = EmbedBuilder()\
                        .set_title("❌ Preference Not Found")\
                        .set_description(f"No preference found for key `{key}`")\
                        .set_color(0xff0000)\
                        .build()

                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

        return command

    def list_preferences_command(self) -> app_commands.Command:
        """Command to list all user preferences"""
        @app_commands.command(name="list_preferences", description="List all your preferences")
        async def command(interaction: discord.Interaction):
            try:
                status = await self.service.get_user_status(interaction.user.id)
                preferences = status['preferences']

                if not preferences:
                    embed = EmbedBuilder()\
                        .set_title("📋 Your Preferences")\
                        .set_description("You have no preferences set.")\
                        .set_color(0x95a5a6)\
                        .build()
                else:
                    embed = EmbedBuilder()\
                        .set_title("📋 Your Preferences")\
                        .set_description(f"You have {len(preferences)} preferences set.")\
                        .set_color(0x3498db)

                    # Split preferences into chunks if needed
                    chunks = []
                    current_chunk = []
                    current_length = 0

                    for key, value in preferences.items():
                        line = f"**{key}:** {str(value)[:100]}"
                        if current_length + len(line) > 1000:
                            chunks.append('\n'.join(current_chunk))
                            current_chunk = [line]
                            current_length = len(line)
                        else:
                            current_chunk.append(line)
                            current_length += len(line) + 1

                    if current_chunk:
                        chunks.append('\n'.join(current_chunk))

                    # Add chunks as fields
                    for i, chunk in enumerate(chunks):
                        field_name = "Preferences" if i == 0 else f"Preferences (cont. {i+1})"
                        embed.add_field(field_name, chunk, inline=False)

                    embed = embed.build()

                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

        return command

    def clear_preferences_command(self) -> app_commands.Command:
        """Command to clear all user preferences"""
        @app_commands.command(name="clear_preferences", description="Clear all your preferences")
        async def command(interaction: discord.Interaction):
            try:
                # Create confirmation view
                view = ConfirmationView()
                embed = EmbedBuilder()\
                    .set_title("⚠️ Confirm Clear Preferences")\
                    .set_description("Are you sure you want to clear ALL your preferences?\n\n**This action cannot be undone!**")\
                    .set_color(0xe74c3c)\
                    .build()

                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

                # Wait for user interaction
                await view.wait()

                if view.confirmed:
                    success = await self.service.clear_preferences(interaction.user.id)

                    if success:
                        embed = EmbedBuilder()\
                            .set_title("✅ Preferences Cleared")\
                            .set_description("All your preferences have been cleared successfully.")\
                            .set_color(0x00ff00)\
                            .build()
                    else:
                        embed = EmbedBuilder()\
                            .set_title("❌ Clear Failed")\
                            .set_description("Could not clear preferences. You might not have any set.")\
                            .set_color(0xff0000)\
                            .build()

                    await interaction.edit_original_response(embed=embed, view=None)
                else:
                    embed = EmbedBuilder()\
                        .set_title("❌ Cancelled")\
                        .set_description("Preference clearing was cancelled.")\
                        .set_color(0x95a5a6)\
                        .build()
                    await interaction.edit_original_response(embed=embed, view=None)

            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

        return command

    # ========== User Info Commands ==========

    def update_calendar_email_command(self) -> app_commands.Command:
        """Command to update user's calendar email"""
        @app_commands.command(name="update_calendar_email", description="Update your calendar email")
        @app_commands.describe(email="Your email address")
        async def command(interaction: discord.Interaction, email: str):
            try:
                success = await self.service.update_user_info(interaction.user.id, calendar_email=email)

                if success:
                    embed = EmbedBuilder()\
                        .set_title("✅ Calendar Email Updated")\
                        .set_description("Your calendar email has been updated successfully.")\
                        .set_color(0x00ff00)\
                        .add_field("New Email", email, inline=True)\
                        .build()
                else:
                    embed = EmbedBuilder()\
                        .set_title("❌ Update Failed")\
                        .set_description("Could not update your calendar email. Please try again.")\
                        .set_color(0xff0000)\
                        .build()

                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

        return command

    # ========== Role Management Commands ==========

    def manage_user_role_command(self) -> app_commands.Command:
        """Command to manage user roles (Admin only)"""
        @app_commands.command(name="manage_user_role", description="Add or remove a role from a user (Admin only)")
        @app_commands.describe(
            user="User to manage",
            role="Role name",
            action="Add or remove"
        )
        @app_commands.choices(action=[
            app_commands.Choice(name="add", value="add"),
            app_commands.Choice(name="remove", value="remove")
        ])
        async def command(
            interaction: discord.Interaction,
            user: discord.Member,
            role: str,
            action: app_commands.Choice[str] = "add"
        ):
            try:
                # Check if user has admin permissions
                if not interaction.user.guild_permissions.administrator:
                    await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
                    return

                if action.value == "add":
                    success = await self.service.add_role(user.id, role)
                    action_text = "added to" if success else "already assigned to"
                else:  # remove
                    success = await self.service.remove_role(user.id, role)
                    action_text = "removed from" if success else "was not assigned to"

                # Sync with Discord roles
                if success:
                    status = await self.service.get_user_status(user.id)
                    await self.service.sync_discord_roles(user, status['roles'])

                embed = EmbedBuilder()\
                    .set_title(f"✅ Role {'Added' if action.value == 'add' else 'Removed'}")\
                    .set_description(f"Role `{role}` has been {action_text} {user.display_name}")\
                    .set_color(0x00ff00 if success else 0xf39c12)\
                    .build()

                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

        return command

    def user_admin_info_command(self) -> app_commands.Command:
        """Command to get detailed user information (Admin only)"""
        @app_commands.command(name="user_admin_info", description="Get detailed user information (Admin only)")
        @app_commands.describe(user="User to check")
        async def command(interaction: discord.Interaction, user: discord.Member):
            try:
                # Check if user has admin permissions
                if not interaction.user.guild_permissions.administrator:
                    await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
                    return

                status = await self.service.get_user_status(user.id)
                embed = self.service.build_admin_user_info_embed(user, status)
                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

        return command

    def update_roles_command(self) -> app_commands.Command:
        """Command to update user roles (legacy function)"""
        @app_commands.command(name="update_roles", description="Update roles for a user")
        @app_commands.describe(user="User to update", roles="Comma-separated roles")
        async def command(interaction: discord.Interaction, user: discord.Member, roles: str):
            try:
                role_list = [r.strip() for r in roles.split(",") if r.strip()]
                await self.service.update_roles(user.id, role_list)

                # Sync with Discord roles
                await self.service.sync_discord_roles(user, role_list)

                embed = EmbedBuilder()\
                    .set_title("✅ Roles Updated")\
                    .set_description(f"Updated roles for <@{user.id}>: {roles}")\
                    .set_color(0x00ff00)\
                    .build()

                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

        return command

# ========== Individual Command Classes ==========

class UserStatusCommand(BaseCommand):
    """Command to check user status and preferences"""

    def __init__(self, bot, services):
        super().__init__(bot, services)
        self.service = services.get("user_service")

    async def handle(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        try:
            # Determine target user
            target_user = user if user else interaction.user

            # Check if user is checking another user (admin only)
            if user and user != interaction.user:
                if not interaction.user.guild_permissions.administrator:
                    await interaction.response.send_message("❌ You need administrator permissions to check other users.", ephemeral=True)
                    return

            status = await self.service.get_user_status(target_user.id)

            embed = EmbedBuilder()\
                .set_title(f"👤 User Status: {target_user.display_name}")\
                .set_color(0x3498db)

            if status['exists']:
                embed.add_field("Profile Status", "✅ Active", inline=True)
                embed.add_field("Calendar Email", status['calendar_email'], inline=True)
                embed.add_field("Preferences", f"{status['preference_count']} set", inline=True)
                embed.add_field("Roles", f"{status['role_count']} assigned", inline=True)

                if status['roles']:
                    roles_text = ', '.join(status['roles'][:5])
                    if len(status['roles']) > 5:
                        roles_text += f" (+{len(status['roles'])-5} more)"
                    embed.add_field("Role List", roles_text, inline=False)
            else:
                embed.add_field("Profile Status", "❌ Not Found", inline=True)
                embed.set_description("User profile has not been created yet.")

            await interaction.response.send_message(embed=embed.build(), ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class SetPreferenceCommand(BaseCommand):
    """Command to set a user preference"""

    def __init__(self, bot, services):
        super().__init__(bot, services)
        self.service = services.get("user_service")

    async def handle(self, interaction: discord.Interaction, key: str, value: str):
        try:
            # Try to parse value as JSON for complex types
            try:
                parsed_value = json.loads(value)
            except json.JSONDecodeError:
                # If not valid JSON, keep as string
                parsed_value = value

            success = await self.service.set_preference(interaction.user.id, key, parsed_value)

            if success:
                embed = EmbedBuilder()\
                    .set_title("✅ Preference Set")\
                    .set_description(f"Successfully set preference `{key}`")\
                    .set_color(0x00ff00)\
                    .add_field("Key", key, inline=True)\
                    .add_field("Value", str(parsed_value)[:100], inline=True)\
                    .build()
            else:
                embed = EmbedBuilder()\
                    .set_title("❌ Failed to Set Preference")\
                    .set_description("Could not set the preference. Please try again.")\
                    .set_color(0xff0000)\
                    .build()

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class GetPreferenceCommand(BaseCommand):
    """Command to get a user preference"""

    def __init__(self, bot, services):
        super().__init__(bot, services)
        self.service = services.get("user_service")

    async def handle(self, interaction: discord.Interaction, key: str):
        try:
            value = await self.service.get_preference(interaction.user.id, key)

            if value is not None:
                embed = EmbedBuilder()\
                    .set_title("📋 Preference Value")\
                    .set_color(0x3498db)\
                    .add_field("Key", key, inline=True)\
                    .add_field("Value", str(value)[:500], inline=False)\
                    .build()
            else:
                embed = EmbedBuilder()\
                    .set_title("❌ Preference Not Found")\
                    .set_description(f"No preference found for key `{key}`")\
                    .set_color(0xff0000)\
                    .build()

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class RemovePreferenceCommand(BaseCommand):
    """Command to remove a user preference"""

    def __init__(self, bot, services):
        super().__init__(bot, services)
        self.service = services.get("user_service")

    async def handle(self, interaction: discord.Interaction, key: str):
        try:
            success = await self.service.remove_preference(interaction.user.id, key)

            if success:
                embed = EmbedBuilder()\
                    .set_title("✅ Preference Removed")\
                    .set_description(f"Successfully removed preference `{key}`")\
                    .set_color(0x00ff00)\
                    .build()
            else:
                embed = EmbedBuilder()\
                    .set_title("❌ Preference Not Found")\
                    .set_description(f"No preference found for key `{key}`")\
                    .set_color(0xff0000)\
                    .build()

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class ListPreferencesCommand(BaseCommand):
    """Command to list all user preferences"""

    def __init__(self, bot, services):
        super().__init__(bot, services)
        self.service = services.get("user_service")

    async def handle(self, interaction: discord.Interaction):
        try:
            status = await self.service.get_user_status(interaction.user.id)
            preferences = status.get('preferences', {})

            embed = EmbedBuilder()\
                .set_title(f"📋 Your Preferences ({len(preferences)} total)")\
                .set_color(0x3498db)

            if not preferences:
                embed.set_description("You haven't set any preferences yet.\nUse `/set_preference` to add some!")
            else:
                # Split preferences into chunks to avoid embed limits
                items = list(preferences.items())
                chunks = []
                current_chunk = []
                current_length = 0

                for key, value in items:
                    line = f"**{key}:** {str(value)[:100]}"
                    if current_length + len(line) > 1000:
                        chunks.append('\n'.join(current_chunk))
                        current_chunk = [line]
                        current_length = len(line)
                    else:
                        current_chunk.append(line)
                        current_length += len(line) + 1

                if current_chunk:
                    chunks.append('\n'.join(current_chunk))

                # Add chunks as fields
                for i, chunk in enumerate(chunks):
                    field_name = "Preferences" if i == 0 else f"Preferences (cont. {i+1})"
                    embed.add_field(field_name, chunk, inline=False)

            await interaction.response.send_message(embed=embed.build(), ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class ClearPreferencesCommand(BaseCommand):
    """Command to clear all user preferences"""

    def __init__(self, bot, services):
        super().__init__(bot, services)
        self.service = services.get("user_service")

    async def handle(self, interaction: discord.Interaction):
        try:
            # Create confirmation view
            from src.shared.views import ConfirmationView
            view = ConfirmationView()
            embed = EmbedBuilder()\
                .set_title("⚠️ Confirm Clear Preferences")\
                .set_description("Are you sure you want to clear ALL your preferences?\n\n**This action cannot be undone!**")\
                .set_color(0xe74c3c)\
                .build()

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

            # Wait for user interaction
            await view.wait()

            if view.confirmed:
                success = await self.service.clear_preferences(interaction.user.id)

                if success:
                    embed = EmbedBuilder()\
                        .set_title("✅ Preferences Cleared")\
                        .set_description("All your preferences have been cleared successfully.")\
                        .set_color(0x00ff00)\
                        .build()
                else:
                    embed = EmbedBuilder()\
                        .set_title("❌ Clear Failed")\
                        .set_description("Could not clear preferences. You might not have any set.")\
                        .set_color(0xff0000)\
                        .build()

                await interaction.edit_original_response(embed=embed, view=None)
            else:
                embed = EmbedBuilder()\
                    .set_title("❌ Cancelled")\
                    .set_description("Preference clearing was cancelled.")\
                    .set_color(0x95a5a6)\
                    .build()
                await interaction.edit_original_response(embed=embed, view=None)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class UpdateCalendarEmailCommand(BaseCommand):
    """Command to update user's calendar email"""

    def __init__(self, bot, services):
        super().__init__(bot, services)
        self.service = services.get("user_service")

    async def handle(self, interaction: discord.Interaction, email: str):
        try:
            success = await self.service.update_user_info(interaction.user.id, calendar_email=email)

            if success:
                embed = EmbedBuilder()\
                    .set_title("✅ Calendar Email Updated")\
                    .set_description("Your calendar email has been updated successfully.")\
                    .set_color(0x00ff00)\
                    .add_field("New Email", email, inline=True)\
                    .build()
            else:
                embed = EmbedBuilder()\
                    .set_title("❌ Update Failed")\
                    .set_description("Could not update your calendar email. Please try again.")\
                    .set_color(0xff0000)\
                    .build()

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class ManageUserRoleCommand(BaseCommand):
    """Command to manage user roles (Admin only)"""

    def __init__(self, bot, services):
        super().__init__(bot, services)
        self.service = services.get("user_service")

    async def handle(self, interaction: discord.Interaction, user: discord.Member, role: str, action: str = "add"):
        try:
            # Check if user has admin permissions
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
                return

            if action == "add":
                success = await self.service.add_role(user.id, role)
                action_text = "added to" if success else "already assigned to"
            else:  # remove
                success = await self.service.remove_role(user.id, role)
                action_text = "removed from" if success else "was not assigned to"

            # Sync with Discord roles
            if success:
                status = await self.service.get_user_status(user.id)
                await self.service.sync_discord_roles(user, status['roles'])

            embed = EmbedBuilder()\
                .set_title(f"✅ Role {'Added' if action == 'add' else 'Removed'}")\
                .set_description(f"Role `{role}` has been {action_text} {user.display_name}")\
                .set_color(0x00ff00 if success else 0xf39c12)\
                .build()

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class UserAdminInfoCommand(BaseCommand):
    """Command to get detailed user information (Admin only)"""

    def __init__(self, bot, services):
        super().__init__(bot, services)
        self.service = services.get("user_service")

    async def handle(self, interaction: discord.Interaction, user: discord.Member):
        try:
            # Check if user has admin permissions
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
                return

            status = await self.service.get_user_status(user.id)

            embed = EmbedBuilder()\
                .set_title(f"🔍 Admin Info: {user.display_name}")\
                .set_color(0xe74c3c)

            embed.add_field("Discord ID", str(user.id), inline=True)
            embed.add_field("Profile Exists", "✅ Yes" if status['exists'] else "❌ No", inline=True)
            embed.add_field("Account Created", user.created_at.strftime("%Y-%m-%d"), inline=True)

            if status['exists']:
                embed.add_field("Calendar Email", status['calendar_email'], inline=True)
                embed.add_field("Preferences", f"{status['preference_count']} set", inline=True)
                embed.add_field("Roles", f"{status['role_count']} assigned", inline=True)

                if status['roles']:
                    roles_text = ', '.join(status['roles'])
                    embed.add_field("Role List", roles_text[:1000], inline=False)

                if status['preferences']:
                    prefs_text = json.dumps(status['preferences'], indent=2)[:1000]
                    embed.add_field("Preferences", f"```json\n{prefs_text}\n```", inline=False)

            await interaction.response.send_message(embed=embed.build(), ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class UpdateRolesCommand(BaseCommand):
    """Update roles for a user (Admin only)"""

    def __init__(self, bot, services):
        super().__init__(bot, services)
        self.service = services.get("user_service")

    async def handle(self, interaction: discord.Interaction, user: discord.Member, roles: str):
        """Handle update roles command"""
        try:
            # Check admin permissions
            if not interaction.user.guild_permissions.administrator:
                embed = (EmbedBuilder()
                        .set_title("❌ Permission Denied")
                        .set_description("You need administrator permissions to update user roles.")
                        .set_color("red")
                        .build())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Parse roles
            role_list = [role.strip() for role in roles.split(",") if role.strip()]

            if not role_list:
                embed = (EmbedBuilder()
                        .set_title("❌ Invalid Input")
                        .set_description("Please provide a comma-separated list of roles.")
                        .set_color("red")
                        .build())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Update roles
            success = await self.service.update_roles(user.id, role_list)

            if success:
                embed = (EmbedBuilder()
                        .set_title("✅ Roles Updated")
                        .set_description(f"Successfully updated roles for {user.display_name}")
                        .add_field("User", user.mention, inline=True)
                        .add_field("New Roles", ", ".join(role_list), inline=True)
                        .set_color("green")
                        .build())
            else:
                embed = (EmbedBuilder()
                        .set_title("❌ Update Failed")
                        .set_description("Failed to update user roles. Please try again.")
                        .set_color("red")
                        .build())

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            embed = (EmbedBuilder()
                    .set_title("❌ Error")
                    .set_description(f"An error occurred: {str(e)}")
                    .set_color("red")
                    .build())
            await interaction.response.send_message(embed=embed, ephemeral=True)