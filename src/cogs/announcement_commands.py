"""
Rinox Sentinel - Advanced Announcement Commands
Professional announcements with DM, YouTube embeds, and type-based styling
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import re

from ..ui.embeds import RinoxEmbed
from ..ui.views import AnnouncementView


ANNOUNCEMENT_TYPES = {
    "general": {"emoji": "📢", "color": RinoxEmbed.PRIMARY, "title_prefix": "Announcement"},
    "product": {"emoji": "🛍️", "color": RinoxEmbed.PREMIUM, "title_prefix": "Product"},
    "youtube": {"emoji": "🎬", "color": 0xFF0000, "title_prefix": "Video"},
    "event":   {"emoji": "📅", "color": RinoxEmbed.SUCCESS, "title_prefix": "Event"},
    "urgent":  {"emoji": "🚨", "color": RinoxEmbed.DANGER, "title_prefix": "URGENT"},
}


def parse_hex_color(value: str) -> Optional[int]:
    if not value:
        return None
    hex_str = value.lstrip("#").strip()
    if re.match(r"^[0-9a-fA-F]{6}$", hex_str):
        return int(hex_str, 16)
    return None


def extract_youtube_id(url: str) -> Optional[str]:
    patterns = [
        r"(?:youtube\.com/watch\?v=)([\w-]+)",
        r"(?:youtu\.be/)([\w-]+)",
        r"(?:youtube\.com/embed/)([\w-]+)",
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


class AnnouncementCommands(commands.Cog):
    """Advanced announcement system"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="announcement", description="📢 Send a professional announcement")
    @app_commands.describe(
        title="Announcement title",
        message="Main announcement content",
        type="Announcement style",
        channel="Target channel (default: current)",
        youtube_url="YouTube video URL to embed",
        image_url="Image URL to include",
        color="Embed color (hex, e.g. #5865F2)",
        ping_role="Role to ping",
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="📢 General", value="general"),
        app_commands.Choice(name="🛍️ Product", value="product"),
        app_commands.Choice(name="🎬 YouTube", value="youtube"),
        app_commands.Choice(name="📅 Event", value="event"),
        app_commands.Choice(name="🚨 Urgent", value="urgent"),
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def announcement(
        self,
        interaction: discord.Interaction,
        title: str,
        message: str,
        type: app_commands.Choice[str] = "general",
        channel: Optional[discord.TextChannel] = None,
        youtube_url: Optional[str] = None,
        image_url: Optional[str] = None,
        color: Optional[str] = None,
        ping_role: Optional[discord.Role] = None,
    ):
        target = channel or interaction.channel
        ann_type = ANNOUNCEMENT_TYPES.get(type.value if isinstance(type, app_commands.Choice) else type, ANNOUNCEMENT_TYPES["general"])

        embed_color = parse_hex_color(color) or ann_type["color"]
        prefix = ann_type["title_prefix"]

        embed = discord.Embed(
            title=f"{ann_type['emoji']} {prefix}: {title}",
            description=message,
            color=embed_color,
            timestamp=discord.utils.utcnow(),
        )

        embed.set_author(
            name=interaction.guild.name,
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
        )

        embed.add_field(
            name="Posted by",
            value=interaction.user.mention,
            inline=True,
        )
        embed.add_field(
            name="Channel",
            value=target.mention,
            inline=True,
        )

        if ping_role:
            embed.add_field(
                name="Ping",
                value=ping_role.mention,
                inline=True,
            )

        if image_url:
            embed.set_image(url=image_url)

        footer_text = f"🛡️ Rinox Sentinel"
        if interaction.guild:
            footer_text += f" • {interaction.guild.name}"
        embed.set_footer(text=footer_text)

        content = ping_role.mention if ping_role else None

        # YouTube: add video embed and link
        if youtube_url:
            video_id = extract_youtube_id(youtube_url)
            if video_id:
                embed.add_field(
                    name="🎬 YouTube Video",
                    value=f"[▶️ Watch on YouTube]({youtube_url})",
                    inline=False,
                )
                embed.set_image(url=f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg")

        view = AnnouncementView(self.bot, embed, target, content)
        await interaction.response.send_message(
            content="📋 **Preview your announcement:**\n*Use the dropdown to choose DM option, then Confirm to publish.*",
            embed=embed,
            view=view,
            ephemeral=True,
        )
        view._interaction = interaction


async def setup(bot):
    await bot.add_cog(AnnouncementCommands(bot))
