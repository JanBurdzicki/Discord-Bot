"""
Response builders using Builder pattern.
Provides fluent interface for creating Discord embeds and responses.
"""

import discord
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

class EmbedBuilder:
    """
    Builder for Discord embeds with fluent interface.
    Provides consistent styling and common patterns.
    """

    def __init__(self):
        self.embed = discord.Embed()
        self._color_set = False

    def success(self, title: str, description: str = "") -> 'EmbedBuilder':
        """Create a success embed (green)"""
        self.embed.title = f"✅ {title}"
        self.embed.description = description
        self.embed.color = discord.Color.green()
        self._color_set = True
        return self

    def error(self, title: str, description: str = "") -> 'EmbedBuilder':
        """Create an error embed (red)"""
        self.embed.title = f"❌ {title}"
        self.embed.description = description
        self.embed.color = discord.Color.red()
        self._color_set = True
        return self

    def warning(self, title: str, description: str = "") -> 'EmbedBuilder':
        """Create a warning embed (orange)"""
        self.embed.title = f"⚠️ {title}"
        self.embed.description = description
        self.embed.color = discord.Color.orange()
        self._color_set = True
        return self

    def info(self, title: str, description: str = "") -> 'EmbedBuilder':
        """Create an info embed (blue)"""
        self.embed.title = f"ℹ️ {title}"
        self.embed.description = description
        self.embed.color = discord.Color.blue()
        self._color_set = True
        return self

    def custom(self, title: str, description: str = "", color: discord.Color = None) -> 'EmbedBuilder':
        """Create a custom embed"""
        self.embed.title = title
        self.embed.description = description
        if color:
            self.embed.color = color
            self._color_set = True
        return self

    # Common preset methods
    def permission_denied(self) -> 'EmbedBuilder':
        """Standard permission denied embed"""
        return self.error("Permission Denied", "You don't have permission to use this command.")

    def not_found(self, item_type: str) -> 'EmbedBuilder':
        """Standard not found embed"""
        return self.error(f"{item_type} Not Found", f"The requested {item_type.lower()} could not be found.")

    def validation_error(self, errors: List[str]) -> 'EmbedBuilder':
        """Standard validation error embed"""
        error_text = "\n".join(f"• {error}" for error in errors)
        return self.error("Validation Error", error_text)

    def loading(self, message: str = "Processing...") -> 'EmbedBuilder':
        """Loading embed"""
        return self.info("Loading", f"🔄 {message}")

    # Fluent interface methods
    def set_title(self, title: str) -> 'EmbedBuilder':
        """Set the embed title"""
        self.embed.title = title
        return self

    def set_description(self, description: str) -> 'EmbedBuilder':
        """Set the embed description"""
        self.embed.description = description
        return self

    def set_color(self, color: Union[discord.Color, int, str]) -> 'EmbedBuilder':
        """Set the embed color"""
        if isinstance(color, str):
            self.embed.color = discord.Color(int(color.replace('#', ''), 16))
        else:
            self.embed.color = color
        self._color_set = True
        return self

    def add_field(self, name: str, value: str, inline: bool = False) -> 'EmbedBuilder':
        """Add a field to the embed"""
        self.embed.add_field(name=name, value=value, inline=inline)
        return self

    def add_fields(self, fields: List[Dict[str, Any]]) -> 'EmbedBuilder':
        """Add multiple fields at once"""
        for field in fields:
            self.embed.add_field(**field)
        return self

    def set_footer(self, text: str, icon_url: Optional[str] = None) -> 'EmbedBuilder':
        """Set the embed footer"""
        self.embed.set_footer(text=text, icon_url=icon_url)
        return self

    def set_author(self, name: str, icon_url: Optional[str] = None, url: Optional[str] = None) -> 'EmbedBuilder':
        """Set the embed author"""
        self.embed.set_author(name=name, icon_url=icon_url, url=url)
        return self

    def set_thumbnail(self, url: str) -> 'EmbedBuilder':
        """Set the embed thumbnail"""
        self.embed.set_thumbnail(url=url)
        return self

    def set_image(self, url: str) -> 'EmbedBuilder':
        """Set the embed image"""
        self.embed.set_image(url=url)
        return self

    def set_timestamp(self, timestamp: datetime = None) -> 'EmbedBuilder':
        """Set the embed timestamp"""
        self.embed.timestamp = timestamp or datetime.utcnow()
        return self

    def build(self) -> discord.Embed:
        """Build and return the final embed"""
        # Set default color if none was set
        if not self._color_set:
            self.embed.color = discord.Color.blurple()

        return self.embed

class ResponseBuilder:
    """
    Builder for complex Discord responses with embeds, components, and files.
    """

    def __init__(self):
        self.content: Optional[str] = None
        self.embed: Optional[discord.Embed] = None
        self.embeds: List[discord.Embed] = []
        self.view: Optional[discord.ui.View] = None
        self.files: List[discord.File] = []
        self.ephemeral: bool = False
        self.delete_after: Optional[float] = None

    def set_content(self, content: str) -> 'ResponseBuilder':
        """Set the response content"""
        self.content = content
        return self

    def set_embed(self, embed: discord.Embed) -> 'ResponseBuilder':
        """Set a single embed"""
        self.embed = embed
        return self

    def add_embed(self, embed: discord.Embed) -> 'ResponseBuilder':
        """Add an embed to the embeds list"""
        self.embeds.append(embed)
        return self

    def set_view(self, view: discord.ui.View) -> 'ResponseBuilder':
        """Set the view (buttons, select menus, etc.)"""
        self.view = view
        return self

    def add_file(self, file: discord.File) -> 'ResponseBuilder':
        """Add a file attachment"""
        self.files.append(file)
        return self

    def set_ephemeral(self, ephemeral: bool = True) -> 'ResponseBuilder':
        """Set whether the response should be ephemeral"""
        self.ephemeral = ephemeral
        return self

    def set_delete_after(self, seconds: float) -> 'ResponseBuilder':
        """Set auto-delete timer"""
        self.delete_after = seconds
        return self

    def build_kwargs(self) -> Dict[str, Any]:
        """Build the kwargs dict for Discord response methods"""
        kwargs = {}

        if self.content:
            kwargs['content'] = self.content

        if self.embed:
            kwargs['embed'] = self.embed
        elif self.embeds:
            kwargs['embeds'] = self.embeds

        if self.view:
            kwargs['view'] = self.view

        if self.files:
            kwargs['files'] = self.files

        kwargs['ephemeral'] = self.ephemeral

        if self.delete_after:
            kwargs['delete_after'] = self.delete_after

        return kwargs

    async def send(self, interaction: discord.Interaction) -> None:
        """Send the response"""
        kwargs = self.build_kwargs()

        if interaction.response.is_done():
            await interaction.followup.send(**kwargs)
        else:
            await interaction.response.send_message(**kwargs)

class PaginatedEmbedBuilder:
    """
    Builder for paginated embeds that can be split across multiple pages.
    """

    def __init__(self, max_fields_per_page: int = 25, max_chars_per_page: int = 6000):
        self.pages: List[EmbedBuilder] = []
        self.current_page = EmbedBuilder()
        self.max_fields_per_page = max_fields_per_page
        self.max_chars_per_page = max_chars_per_page
        self.field_count = 0
        self.char_count = 0

    def add_field(self, name: str, value: str, inline: bool = False) -> 'PaginatedEmbedBuilder':
        """Add a field, creating new page if necessary"""
        field_chars = len(name) + len(value)

        if (self.field_count >= self.max_fields_per_page or
            self.char_count + field_chars > self.max_chars_per_page):
            self._new_page()

        self.current_page.add_field(name, value, inline)
        self.field_count += 1
        self.char_count += field_chars

        return self

    def set_base_embed(self, title: str, description: str = "", color: discord.Color = None) -> 'PaginatedEmbedBuilder':
        """Set the base template for all pages"""
        self.base_title = title
        self.base_description = description
        self.base_color = color
        self.current_page.custom(title, description, color)
        return self

    def _new_page(self):
        """Create a new page"""
        if self.field_count > 0:  # Only add if current page has content
            self.pages.append(self.current_page)

        self.current_page = EmbedBuilder()
        if hasattr(self, 'base_title'):
            page_num = len(self.pages) + 2
            title = f"{self.base_title} (Page {page_num})"
            self.current_page.custom(title, self.base_description, self.base_color)

        self.field_count = 0
        self.char_count = 0

    def build(self) -> List[discord.Embed]:
        """Build and return all pages"""
        if self.field_count > 0:  # Add the last page if it has content
            self.pages.append(self.current_page)

        # Update first page title if multiple pages
        if len(self.pages) > 1 and hasattr(self, 'base_title'):
            first_embed = self.pages[0].build()
            first_embed.title = f"{self.base_title} (Page 1 of {len(self.pages)})"

            # Update other page titles
            for i, page in enumerate(self.pages[1:], 2):
                embed = page.build()
                embed.title = f"{self.base_title} (Page {i} of {len(self.pages)})"

        return [page.build() for page in self.pages]