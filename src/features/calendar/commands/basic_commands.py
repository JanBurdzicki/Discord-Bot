from typing import Dict, Any, Optional
import discord
from datetime import datetime, timedelta
from src.core.base_command import BaseCommand
from src.core.validators import validate_required, validate_integer, validate_string_length
from src.core.builders import EmbedBuilder

class CalendarHelpCommand(BaseCommand):
    """Show calendar system help and instructions"""

    async def validate_input(self, interaction: discord.Interaction, **kwargs) -> Dict[str, Any]:
        return {"validated": True}

    async def check_permissions(self, interaction: discord.Interaction, **kwargs) -> bool:
        return True

    async def execute_command(self, interaction: discord.Interaction, calendar_service, **kwargs):
        embed = calendar_service.build_help_embed().build()
        await interaction.response.send_message(embed=embed, ephemeral=True)

class LinkUserCalendarCommand(BaseCommand):
    """Link user's personal Google Calendar"""

    async def validate_input(self, interaction: discord.Interaction, calendar_id: str = "", **kwargs) -> Dict[str, Any]:
        if not calendar_id.strip():
            return {
                "error": "Missing Calendar ID",
                "message": "You need to provide your Google Calendar ID to link it.",
                "show_instructions": True
            }

        calendar_service = self.container.get("calendar_service")
        if not calendar_service.validate_calendar_id(calendar_id):
            return {
                "error": "Invalid Calendar ID",
                "message": "Calendar ID should look like an email address (e.g., `example@gmail.com`)"
            }

        return {"calendar_id": calendar_id}

    async def check_permissions(self, interaction: discord.Interaction, **kwargs) -> bool:
        return True

    async def execute_command(self, interaction: discord.Interaction, calendar_service, calendar_id: str, **kwargs):
        success = await calendar_service.link_user_calendar(interaction.user.id, calendar_id)

        if success:
            embed = (EmbedBuilder()
                    .set_title("✅ Calendar Linked Successfully")
                    .set_description(f"Your Google Calendar has been linked!\n\n**Calendar ID:** `{calendar_id}`")
                    .set_color("green")
                    .add_field("What's Next?",
                              "• Admins can now add you to shared calendars\n• Your free/busy status will be visible to authorized users\n• You'll receive event invitations in your personal calendar",
                              inline=False))
        else:
            embed = (EmbedBuilder()
                    .set_title("❌ Error Linking Calendar")
                    .set_description("Failed to link calendar. Please try again.")
                    .set_color("red"))

        await interaction.response.send_message(embed=embed.build(), ephemeral=True)

    async def handle_validation_error(self, interaction: discord.Interaction, error_data: Dict[str, Any]):
        embed = (EmbedBuilder()
                .set_title(f"❌ {error_data['error']}")
                .set_description(error_data["message"])
                .set_color("red"))

        if error_data.get("show_instructions"):
            calendar_service = self.container.get("calendar_service")
            embed.add_field("📋 Instructions", calendar_service.CALENDAR_SHARING_INSTRUCTIONS, inline=False)

        await interaction.response.send_message(embed=embed.build(), ephemeral=True)

class CreateSharedCalendarCommand(BaseCommand):
    """Create a new shared calendar (Admin only)"""

    async def validate_input(self, interaction: discord.Interaction, calendar_name: str, description: str = "", **kwargs) -> Dict[str, Any]:
        calendar_name = validate_required(calendar_name, "Calendar name")
        calendar_name = validate_string_length(calendar_name, 1, 100, "Calendar name")
        description = validate_string_length(description, 0, 500, "Description")

        return {"calendar_name": calendar_name, "description": description}

    async def check_permissions(self, interaction: discord.Interaction, **kwargs) -> bool:
        return interaction.user.id == self.bot.owner_id

    async def get_permission_error(self, interaction: discord.Interaction) -> str:
        return "Only the server owner can create shared calendars."

    async def execute_command(self, interaction: discord.Interaction, calendar_service, calendar_name: str, description: str, **kwargs):
        existing_calendar = await calendar_service.get_calendar(calendar_name)
        if existing_calendar:
            embed = (EmbedBuilder()
                    .set_title("❌ Calendar Already Exists")
                    .set_description(f"A calendar named '{calendar_name}' already exists.")
                    .set_color("red"))
            await interaction.response.send_message(embed=embed.build(), ephemeral=True)
            return

        google_calendar_id = f"{calendar_name.lower().replace(' ', '_')}@{interaction.guild.name.lower()}.calendar"
        calendar = await calendar_service.create_calendar(
            name=calendar_name,
            creator_id=interaction.user.id,
            description=description,
            google_calendar_id=google_calendar_id
        )

        embed = calendar_service.build_calendar_success_embed(calendar).build()
        await interaction.response.send_message(embed=embed, ephemeral=True)