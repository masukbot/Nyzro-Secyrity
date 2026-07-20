"""
Rinox Sentinel - Moderation Commands
/warn, /mute, /timeout, /kick, /ban, /history
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta

from ..ui.embeds import RinoxEmbed


class ModerationCommands(commands.Cog):
    """Moderation commands"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="warn", description="⚠️ Warn a User")
    @app_commands.describe(
        user="User to warn",
        reason="Reason for warning",
        weight="Warning weight (1-5)"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warn(self, interaction: discord.Interaction,
                  user: discord.Member,
                  reason: str,
                  weight: app_commands.Range[int, 1, 5] = 1):
        """Warn a user"""
        await interaction.response.defer(ephemeral=True)
        
        await self.bot.db.add_warning(
            interaction.guild_id,
            user.id,
            reason,
            interaction.user.id,
            weight
        )
        
        # DM user
        try:
            embed = RinoxEmbed.warning(
                f"You have been warned in **{interaction.guild.name}**\n"
                f"**Reason:** {reason}\n"
                f"**Weight:** {weight}",
                "⚠️ Warning"
            )
            await user.send(embed=embed)
        except:
            pass
            
        embed = RinoxEmbed.success(
            f"**User:** {user.mention}\n"
            f"**Reason:** {reason}\n"
            f"**Weight:** {weight}",
            "⚠️ User Warned"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    @app_commands.command(name="mute", description="🔇 Mute a User")
    @app_commands.describe(
        user="User to mute",
        duration="Duration in minutes",
        reason="Reason"
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction,
                  user: discord.Member,
                  duration: app_commands.Range[int, 1, 40320],
                  reason: str = "No reason provided"):
        """Mute a user"""
        await interaction.response.defer(ephemeral=True)
        
        # Apply timeout
        until = discord.utils.utcnow() + timedelta(minutes=duration)
        await user.timeout(until, reason=reason)
        
        embed = RinoxEmbed.success(
            f"**User:** {user.mention}\n"
            f"**Duration:** {duration} minutes\n"
            f"**Reason:** {reason}",
            "🔇 User Muted"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    @app_commands.command(name="kick", description="👢 Kick a User")
    @app_commands.describe(
        user="User to kick",
        reason="Reason"
    )
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction,
                  user: discord.Member,
                  reason: str = "No reason provided"):
        """Kick a user"""
        await interaction.response.defer(ephemeral=True)
        
        await user.kick(reason=reason)
        
        embed = RinoxEmbed.success(
            f"**User:** {user.mention}\n"
            f"**Reason:** {reason}",
            "👢 User Kicked"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    @app_commands.command(name="ban", description="🔨 Ban a User")
    @app_commands.describe(
        user="User to ban",
        reason="Reason",
        delete_days="Delete message history (days)"
    )
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction,
                 user: discord.Member,
                 reason: str = "No reason provided",
                 delete_days: app_commands.Range[int, 0, 7] = 0):
        """Ban a user"""
        await interaction.response.defer(ephemeral=True)
        
        await user.ban(reason=reason, delete_message_days=delete_days)
        
        embed = RinoxEmbed.success(
            f"**User:** {user.mention}\n"
            f"**Reason:** {reason}\n"
            f"**Deleted:** {delete_days} days of messages",
            "🔨 User Banned"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    @app_commands.command(name="history", description="📋 View User History")
    @app_commands.describe(user="User to check")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def history(self, interaction: discord.Interaction,
                    user: discord.Member):
        """View user moderation history"""
        await interaction.response.defer(ephemeral=True)
        
        warnings = await self.bot.db.get_warnings(interaction.guild_id, user.id)
        
        embed = RinoxEmbed.create(
            title=f"📋 History for {user.name}",
            color=RinoxEmbed.INFO
        )
        
        embed.add_field(
            name="⚠️ Active Warnings",
            value=str(len(warnings)),
            inline=True
        )
        
        if warnings:
            warn_text = "\n".join([
                f"• {w['reason']} (Weight: {w['weight']})"
                for w in warnings[:5]
            ])
            embed.add_field(
                name="Recent Warnings",
                value=warn_text,
                inline=False
            )
            
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ModerationCommands(bot))
