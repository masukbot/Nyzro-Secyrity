"""
Rinox Sentinel - Analytics Commands
/analytics, /report
"""

import discord
from discord import app_commands
from discord.ext import commands

from ..ui.embeds import RinoxEmbed


class AnalyticsCommands(commands.Cog):
    """Analytics and reporting"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="analytics", description="📊 View Server Analytics")
    @app_commands.describe(days="Number of days (1-30)")
    @app_commands.checks.has_permissions(administrator=True)
    async def analytics(self, interaction: discord.Interaction,
                       days: app_commands.Range[int, 1, 30] = 7):
        """View analytics"""
        await interaction.response.defer(ephemeral=True)
        
        data = await self.bot.db.get_analytics(interaction.guild_id, days)
        
        if not data:
            embed = RinoxEmbed.info("No analytics data available yet.", "📊 Analytics")
        else:
            embed = RinoxEmbed.analytics(data[0])
            
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    @app_commands.command(name="report", description="📈 Generate Security Report")
    @app_commands.checks.has_permissions(administrator=True)
    async def report(self, interaction: discord.Interaction):
        """Generate security report"""
        await interaction.response.defer(ephemeral=True)
        
        analytics = await self.bot.db.get_analytics(interaction.guild_id, 30)
        
        if not analytics:
            embed = RinoxEmbed.info("No data available yet to generate a report.", "📈 Security Report")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        total_scanned = sum(a.get("messages_scanned", 0) for a in analytics)
        total_threats = sum(a.get("threats_detected", 0) for a in analytics)
        total_actions = sum(a.get("actions_taken", 0) for a in analytics)
        total_fp = sum(a.get("false_positives", 0) for a in analytics)
        avg_risk = sum(a.get("avg_risk_score", 0) for a in analytics) / len(analytics) if analytics else 0
        
        embed = RinoxEmbed.create(
            title=f"📈 Security Report — Last 30 Days",
            color=RinoxEmbed.PREMIUM
        )
        embed.add_field(name="📝 Messages Scanned", value=f"`{total_scanned}`", inline=True)
        embed.add_field(name="⚠️ Threats Detected", value=f"`{total_threats}`", inline=True)
        embed.add_field(name="⚡ Actions Taken", value=f"`{total_actions}`", inline=True)
        embed.add_field(name="🎯 False Positives", value=f"`{total_fp}`", inline=True)
        embed.add_field(name="📊 Avg Risk Score", value=f"`{avg_risk:.1f}/100`", inline=True)
        embed.add_field(name="✅ Accuracy", value=f"`{((total_scanned - total_fp) / total_scanned * 100):.1f}%`" if total_scanned > 0 else "N/A", inline=True)
        embed.set_footer(text=f"{interaction.guild.name} • Generated {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AnalyticsCommands(bot))
