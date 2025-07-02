"""
Shared Discord UI views and components
"""

import discord
from typing import Optional, Callable, Any

class ConfirmationView(discord.ui.View):
    """
    A simple confirmation view with Yes/No buttons
    """

    def __init__(self, *, timeout: float = 60.0, user_id: Optional[int] = None):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.value: Optional[bool] = None
        self.on_confirm: Optional[Callable] = None
        self.on_cancel: Optional[Callable] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the original user to interact"""
        if self.user_id and interaction.user.id != self.user_id:
            await interaction.response.send_message("This confirmation is not for you.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm button callback"""
        self.value = True
        if self.on_confirm:
            await self.on_confirm(interaction)
        else:
            await interaction.response.send_message("Confirmed!", ephemeral=True)
        self.stop()

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel button callback"""
        self.value = False
        if self.on_cancel:
            await self.on_cancel(interaction)
        else:
            await interaction.response.send_message("Cancelled.", ephemeral=True)
        self.stop()

    async def on_timeout(self):
        """Called when the view times out"""
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        self.value = None