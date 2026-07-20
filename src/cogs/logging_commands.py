"""
Rinox Sentinel - Logging Commands
"""

import discord
from discord import app_commands
from discord.ext import commands

from ..ui.embeds import RinoxEmbed


class LoggingCommands(commands.Cog):
    """Logging configuration commands"""
    
    def __init__(self, bot):
        self.bot = bot
        
    log_group = app_commands.Group(name="log", description="📝 Configure logging options")
    
    @log_group.command(name="set-channel", description="📍 Set the channel where security & moderation events are logged")
    @app_commands.describe(channel="The text channel to send logs to")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the logging channel"""
        await interaction.response.defer(ephemeral=True)
        
        # Check bot permissions in that channel
        permissions = channel.permissions_for(interaction.guild.me)
        if not (permissions.send_messages and permissions.embed_links):
            embed = RinoxEmbed.error(
                f"I don't have permission to send messages or embed links in {channel.mention}. Please grant these permissions first.",
                "❌ Missing Permissions"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
            
        await self.bot.db.update_guild_settings(
            interaction.guild_id,
            log_channel_id=channel.id
        )
        
        embed = RinoxEmbed.success(
            f"All security, moderation, and system events will now be logged to {channel.mention}.",
            "📝 Logging Channel Configured"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Send a welcome/test message to that channel
        test_embed = RinoxEmbed.success(
            f"🛡️ **Rinox Sentinel** logging has been enabled in this channel by {interaction.user.mention}.",
            "🔒 System Log Initialized"
        )
        await channel.send(embed=test_embed)

    @log_group.command(name="show", description="🔍 View the current logging configuration")
    @app_commands.checks.has_permissions(administrator=True)
    async def show(self, interaction: discord.Interaction):
        """Show current logging configuration"""
        await interaction.response.defer(ephemeral=True)
        
        settings = await self.bot.db.get_guild_settings(interaction.guild_id)
        log_channel_id = settings.get("log_channel_id") if settings else None
        
        embed = RinoxEmbed.create(
            title="📝 Logging Configuration",
            color=RinoxEmbed.INFO
        )
        
        if log_channel_id:
            channel = interaction.guild.get_channel(log_channel_id)
            channel_text = channel.mention if channel else f"Deleted Channel (`{log_channel_id}`)"
            status = "🟢 Enabled"
        else:
            channel_text = "Not Configured"
            status = "🔴 Disabled"
            
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Target Channel", value=channel_text, inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @log_group.command(name="remove", description="❌ Disable logging entirely")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove(self, interaction: discord.Interaction):
        """Disable logging"""
        await interaction.response.defer(ephemeral=True)
        
        await self.bot.db.update_guild_settings(
            interaction.guild_id,
            log_channel_id=None
        )
        
        embed = RinoxEmbed.success(
            "Logging has been completely disabled.",
            "📝 Logging Disabled"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(LoggingCommands(bot))
