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
        
    @app_commands.command(name="report", description="📈 Generate Report")
    @app_commands.checks.has_permissions(administrator=True)
    async def report(self, interaction: discord.Interaction):
        """Generate security report"""
        await interaction.response.defer(ephemeral=True)
        
        embed = RinoxEmbed.create(
            title="📈 Security Report",
            description="Generating report...",
            color=RinoxEmbed.PREMIUM
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AnalyticsCommands(bot))
