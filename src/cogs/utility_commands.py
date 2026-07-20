"""
Rinox Sentinel - Utility Commands
"""

import discord
from discord import app_commands
from discord.ext import commands

from ..ui.embeds import RinoxEmbed


class UtilityCommands(commands.Cog):
    """Utility commands"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="ping", description="🏓 Check Bot Latency")
    async def ping(self, interaction: discord.Interaction):
        """Check latency"""
        latency = self.bot.latency * 1000
        embed = RinoxEmbed.success(
            f"**Bot Latency:** `{latency:.1f}ms`",
            "🏓 Pong!"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(UtilityCommands(bot))
