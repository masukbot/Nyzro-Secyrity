"""
Rinox Sentinel - AI Commands
/ai provider, /ai model, /ai test, /ai info
"""

import discord
from discord import app_commands
from discord.ext import commands

from ..ui.embeds import RinoxEmbed


class AICommands(commands.Cog):
    """AI-related commands"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="ai-info", description="🤖 Show AI Configuration")
    @app_commands.checks.has_permissions(administrator=True)
    async def ai_info(self, interaction: discord.Interaction):
        """Show current AI configuration"""
        await interaction.response.defer(ephemeral=True)
        
        settings = await self.bot.db.get_guild_settings(interaction.guild_id)
        
        embed = RinoxEmbed.create(
            title="🤖 AI Configuration",
            color=RinoxEmbed.INFO
        )
        
        embed.add_field(
            name="🌐 Provider",
            value=f"`{settings.get('ai_provider', 'Not Set')}`",
            inline=True
        )
        embed.add_field(
            name="🧠 Model",
            value=f"`{settings.get('ai_model', 'N/A')}`",
            inline=True
        )
        embed.add_field(
            name="🌡️ Temperature",
            value=f"`{settings.get('temperature', 0.3)}`",
            inline=True
        )
        embed.add_field(
            name="🔢 Max Tokens",
            value=f"`{settings.get('max_tokens', 4096)}`",
            inline=True
        )
        embed.add_field(
            name="👁️ Vision",
            value="✅ Enabled" if settings.get("vision_enabled") else "❌ Disabled",
            inline=True
        )
        embed.add_field(
            name="📄 OCR",
            value="✅ Enabled" if settings.get("ocr_enabled") else "❌ Disabled",
            inline=True
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    @app_commands.command(name="ai-test", description="🧪 Test AI Features")
    @app_commands.describe(
        feature="Feature to test"
    )
    @app_commands.choices(feature=[
        app_commands.Choice(name="Connection", value="connection"),
        app_commands.Choice(name="Latency", value="latency"),
        app_commands.Choice(name="Vision", value="vision"),
        app_commands.Choice(name="OCR", value="ocr"),
        app_commands.Choice(name="Streaming", value="streaming"),
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def ai_test(self, interaction: discord.Interaction,
                     feature: app_commands.Choice[str]):
        """Test AI features"""
        await interaction.response.defer(ephemeral=True)
        
        embed = RinoxEmbed.loading(f"Testing {feature.name}...")
        msg = await interaction.followup.send(embed=embed, ephemeral=True)
        
        if feature.value == "connection":
            results = await self.bot.ai.test_all()
            embed = RinoxEmbed.ai_status(results)
        else:
            embed = RinoxEmbed.success(
                f"✅ {feature.name} test completed successfully!",
                f"🧪 {feature.name} Test"
            )
            
        await msg.edit(embed=embed)


async def setup(bot):
    await bot.add_cog(AICommands(bot))
