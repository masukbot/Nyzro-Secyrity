"""
Rinox Sentinel - Auto-Clean Commands
Configure automatic message deletion in channels
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from ..ui.embeds import RinoxEmbed


class AutoCleanCommands(commands.Cog):
    """Auto-clean configuration"""

    def __init__(self, bot):
        self.bot = bot

    autoclean = app_commands.Group(name="autoclean", description="🧹 Auto message deletion settings")

    @autoclean.command(name="set", description="Auto-delete messages after a delay")
    @app_commands.describe(
        channel="Channel to enable auto-clean in",
        delay="Delay before deletion (e.g., 30s, 5m, 1h, 1d)",
        filter_type="What type of messages to delete"
    )
    @app_commands.choices(filter_type=[
        app_commands.Choice(name="All Messages", value="all"),
        app_commands.Choice(name="Images Only", value="images"),
        app_commands.Choice(name="Links Only", value="links"),
        app_commands.Choice(name="Files Only", value="files"),
        app_commands.Choice(name="Text Only", value="text"),
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def set(self, interaction: discord.Interaction,
                  channel: discord.TextChannel,
                  delay: str,
                  filter_type: app_commands.Choice[str] = "all"):
        """Set auto-clean for a channel"""
        await interaction.response.defer(ephemeral=True)

        seconds = self._parse_duration(delay)
        if seconds is None:
            embed = RinoxEmbed.error(
                "Invalid duration format. Use numbers with s/m/h/d (e.g., 30s, 5m, 1h, 1d).",
                "❌ Invalid Duration"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if seconds < 5:
            embed = RinoxEmbed.error("Minimum delay is 5 seconds.", "❌ Too Short")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        filter_val = filter_type.value if isinstance(filter_type, app_commands.Choice) else filter_type

        await self.bot.db.set_auto_clean(
            interaction.guild_id, channel.id, seconds, filter_val
        )

        embed = RinoxEmbed.success(
            f"**Channel:** {channel.mention}\n"
            f"**Delay:** `{delay}` ({seconds}s)\n"
            f"**Filter:** `{filter_val}`\n"
            f"Messages in this channel will be **automatically deleted** after `{delay}`.",
            "🧹 Auto-Clean Enabled"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @autoclean.command(name="remove", description="Disable auto-clean for a channel")
    @app_commands.describe(channel="Channel to disable auto-clean in")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Remove auto-clean from channel"""
        await interaction.response.defer(ephemeral=True)

        await self.bot.db.remove_auto_clean(interaction.guild_id, channel.id)

        embed = RinoxEmbed.success(
            f"Auto-clean disabled for {channel.mention}.",
            "🧹 Auto-Clean Removed"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @autoclean.command(name="list", description="Show all auto-clean configurations")
    @app_commands.checks.has_permissions(administrator=True)
    async def list(self, interaction: discord.Interaction):
        """List all auto-clean channels"""
        await interaction.response.defer(ephemeral=True)

        configs = await self.bot.db.get_all_auto_clean(interaction.guild_id)

        if not configs:
            embed = RinoxEmbed.info(
                "No auto-clean channels configured.\n"
                "Use `/autoclean set #channel 5m` to add one.",
                "🧹 Auto-Clean"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        embed = RinoxEmbed.create(
            title="🧹 Auto-Clean Configuration",
            color=RinoxEmbed.INFO
        )

        for cfg in configs:
            channel = interaction.guild.get_channel(cfg["channel_id"])
            ch_name = channel.mention if channel else f"`{cfg['channel_id']}`"
            delay = cfg.get("delay_seconds", 0)
            delay_str = self._format_duration(delay) if delay else "?"
            filter_str = cfg.get("filter_type", "all")
            embed.add_field(
                name=f"{ch_name}",
                value=f"**Delay:** `{delay_str}`\n**Filter:** `{filter_str}`",
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @autoclean.command(name="whitelist", description="Add/remove users/roles exempt from auto-clean")
    @app_commands.describe(
        channel="Channel",
        action="Add or remove from whitelist",
        user="User to whitelist",
        role="Role to whitelist"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove"),
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def whitelist(self, interaction: discord.Interaction,
                         channel: discord.TextChannel,
                         action: app_commands.Choice[str],
                         user: Optional[discord.Member] = None,
                         role: Optional[discord.Role] = None):
        """Manage whitelist for auto-clean"""
        await interaction.response.defer(ephemeral=True)

        cfg = await self.bot.db.get_auto_clean(interaction.guild_id, channel.id)
        if not cfg:
            embed = RinoxEmbed.error(
                f"No auto-clean configured for {channel.mention}. Set it up first with `/autoclean set`.",
                "❌ Not Configured"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        whitelist_roles = cfg.get("whitelist_roles") or []
        whitelist_users = cfg.get("whitelist_users") or []
        is_add = action.value == "add"
        entity = ""

        if user:
            uid = user.id
            if is_add and uid not in whitelist_users:
                whitelist_users.append(uid)
            elif not is_add and uid in whitelist_users:
                whitelist_users.remove(uid)
            entity = user.mention
        elif role:
            rid = role.id
            if is_add and rid not in whitelist_roles:
                whitelist_roles.append(rid)
            elif not is_add and rid in whitelist_roles:
                whitelist_roles.remove(rid)
            entity = role.mention

        await self.bot.db.set_auto_clean(
            interaction.guild_id, channel.id,
            cfg["delay_seconds"],
            cfg.get("filter_type", "all"),
            whitelist_roles, whitelist_users
        )

        verb = "Added to" if is_add else "Removed from"
        embed = RinoxEmbed.success(
            f"{verb} whitelist: {entity}",
            "🧹 Whitelist Updated"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    def _parse_duration(self, text: str) -> Optional[int]:
        """Parse duration string like 30s, 5m, 1h, 1d into seconds"""
        import re
        total = 0
        patterns = [
            (r'(\d+)\s*d', 86400),
            (r'(\d+)\s*h', 3600),
            (r'(\d+)\s*m', 60),
            (r'(\d+)\s*s', 1),
        ]
        for pattern, multiplier in patterns:
            match = re.search(pattern, text.lower())
            if match:
                total += int(match.group(1)) * multiplier
        return total if total > 0 else None

    def _format_duration(self, seconds: int) -> str:
        parts = []
        days, seconds = divmod(seconds, 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        if days: parts.append(f"{days}d")
        if hours: parts.append(f"{hours}h")
        if minutes: parts.append(f"{minutes}m")
        if seconds or not parts: parts.append(f"{seconds}s")
        return " ".join(parts)


async def setup(bot):
    await bot.add_cog(AutoCleanCommands(bot))