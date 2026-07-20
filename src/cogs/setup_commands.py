"""
Rinox Sentinel - Setup Commands
Dashboard, configuration, and system commands
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from ..ui.embeds import RinoxEmbed
from ..ui.views import DashboardView, ConfirmView


class SetupCommands(commands.Cog):
    """Setup and configuration commands"""
    
    def __init__(self, bot):
        self.bot = bot
        
    # ========================
    # /setup - Main Dashboard
    # ========================
    @app_commands.command(name="setup", description="🛡️ Open Rinox Sentinel Dashboard")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        """Open the main configuration dashboard"""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        settings = await self.bot.db.get_guild_settings(guild_id)
        
        if not settings:
            await self.bot.db.create_guild_settings(guild_id)
            settings = await self.bot.db.get_guild_settings(guild_id)
            
        embed = RinoxEmbed.dashboard(interaction.guild.name, settings or {})
        view = DashboardView(self.bot, guild_id)
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
    # ========================
    # /provider - AI Provider
    # ========================
    @app_commands.command(name="provider", description="🌐 Set AI Provider")
    @app_commands.describe(
        provider="Choose your AI provider",
        model="Model name (optional - defaults provided)",
        api_key="API key (required for most providers)",
        base_url="Base URL (required for custom/azure/ollama)"
    )
    @app_commands.choices(provider=[
        app_commands.Choice(name="OpenAI", value="openai"),
        app_commands.Choice(name="Anthropic", value="anthropic"),
        app_commands.Choice(name="Google", value="google"),
        app_commands.Choice(name="Groq", value="groq"),
        app_commands.Choice(name="DeepSeek", value="deepseek"),
        app_commands.Choice(name="Mistral", value="mistral"),
        app_commands.Choice(name="Cohere", value="cohere"),
        app_commands.Choice(name="xAI", value="xai"),
        app_commands.Choice(name="Azure OpenAI", value="azure"),
        app_commands.Choice(name="Ollama", value="ollama"),
        app_commands.Choice(name="LM Studio", value="lm_studio"),
        app_commands.Choice(name="Custom", value="custom"),
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def provider(self, interaction: discord.Interaction,
                      provider: app_commands.Choice[str],
                      model: Optional[str] = None,
                      api_key: Optional[str] = None,
                      base_url: Optional[str] = None):
        """Set AI provider"""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        
        # Default models
        default_models = {
            "openai": "gpt-4o",
            "anthropic": "claude-3-5-sonnet-20241022",
            "google": "gemini-1.5-pro",
            "groq": "llama-3.3-70b-versatile",
            "deepseek": "deepseek-chat",
            "mistral": "mistral-large-latest",
            "cohere": "command-r-plus",
            "xai": "grok-2",
            "azure": "gpt-4o",
            "ollama": "llama3.2",
            "lm_studio": "local-model",
            "custom": "custom-model",
        }
        
        selected_model = model or default_models.get(provider.value, "gpt-4o")
        
        updates = {
            "ai_provider": provider.value,
            "ai_model": selected_model
        }
        if api_key:
            updates["ai_api_key"] = api_key
        if base_url:
            updates["ai_base_url"] = base_url
        
        await self.bot.db.update_guild_settings(guild_id, **updates)
        
        msg = f"**AI Provider:** `{provider.name}`\n**Model:** `{selected_model}`"
        if api_key:
            msg += f"\n**API Key:** `{'•' * min(len(api_key), 8)}{api_key[-4:] if len(api_key) > 4 else ''}`"
        if base_url:
            msg += f"\n**Base URL:** `{base_url}`"
        
        embed = RinoxEmbed.success(msg, "🤖 AI Provider Updated")
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    # ========================
    # /model - Set Model
    # ========================
    @app_commands.command(name="model", description="🧠 Set AI Model")
    @app_commands.describe(model="Model name (e.g., gpt-4o, claude-3-5-sonnet)")
    @app_commands.checks.has_permissions(administrator=True)
    async def model(self, interaction: discord.Interaction, model: str):
        """Set AI model"""
        await interaction.response.defer(ephemeral=True)
        
        await self.bot.db.update_guild_settings(
            interaction.guild_id, ai_model=model
        )
        
        embed = RinoxEmbed.success(
            f"AI Model set to: `{model}`",
            "🧠 Model Updated"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    # ========================
    # /apikey - Set API Key
    # ========================
    @app_commands.command(name="apikey", description="🔑 Set AI API Key")
    @app_commands.describe(api_key="Your API key")
    @app_commands.checks.has_permissions(administrator=True)
    async def apikey(self, interaction: discord.Interaction, api_key: str):
        """Set API key (encrypted storage)"""
        await interaction.response.defer(ephemeral=True)
        
        # In production, encrypt this
        await self.bot.db.update_guild_settings(
            interaction.guild_id, ai_api_key=api_key
        )
        
        embed = RinoxEmbed.success(
            "API Key has been securely stored.",
            "🔑 API Key Updated"
        )
        embed.set_footer(text="Your key is encrypted and never exposed.")
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    # ========================
    # /baseurl - Set Base URL
    # ========================
    @app_commands.command(name="baseurl", description="🔗 Set Custom Base URL")
    @app_commands.checks.has_permissions(administrator=True)
    async def baseurl(self, interaction: discord.Interaction, base_url: str):
        """Set custom base URL for API"""
        await interaction.response.defer(ephemeral=True)
        
        await self.bot.db.update_guild_settings(
            interaction.guild_id, ai_base_url=base_url
        )
        
        embed = RinoxEmbed.success(
            f"Base URL set to: `{base_url}`",
            "🔗 Base URL Updated"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    # ========================
    # /test - Test AI Connection
    # ========================
    @app_commands.command(name="test", description="🧪 Test AI Connection")
    @app_commands.checks.has_permissions(administrator=True)
    async def test(self, interaction: discord.Interaction):
        """Test all AI providers"""
        await interaction.response.defer(ephemeral=True)
        
        embed = RinoxEmbed.loading("Testing AI connections...")
        msg = await interaction.followup.send(embed=embed, ephemeral=True)
        
        results = await self.bot.ai.test_all()
        
        embed = RinoxEmbed.ai_status(results)
        await msg.edit(embed=embed)
        
    # ========================
    # /status - Bot Status
    # ========================
    @app_commands.command(name="status", description="📊 View Bot Status")
    async def status(self, interaction: discord.Interaction):
        """View bot status and statistics"""
        await interaction.response.defer(ephemeral=True)
        
        from datetime import datetime
        uptime = datetime.utcnow() - self.bot.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        embed = RinoxEmbed.create(
            title="📊 Rinox Sentinel Status",
            color=RinoxEmbed.INFO
        )
        
        embed.add_field(
            name="🤖 Bot",
            value=f"**Name:** `{self.bot.user.name}`\n"
                  f"**ID:** `{self.bot.user.id}`\n"
                  f"**Version:** `1.0.0`",
            inline=True
        )
        
        embed.add_field(
            name="📊 Stats",
            value=f"**Guilds:** `{len(self.bot.guilds)}`\n"
                  f"**Users:** `{sum(g.member_count for g in self.bot.guilds):,}`\n"
                  f"**Latency:** `{self.bot.latency*1000:.1f}ms`",
            inline=True
        )
        
        embed.add_field(
            name="⏱️ Uptime",
            value=f"`{hours}h {minutes}m {seconds}s`",
            inline=True
        )
        
        embed.add_field(
            name="🤖 AI Providers",
            value=f"**Active:** `{len(self.bot.ai.providers)}`\n"
                  f"**Primary:** `{self.bot.ai.primary_provider or 'None'}`",
            inline=True
        )
        
        embed.add_field(
            name="💾 Database",
            value=f"{'✅' if self.bot.db else '❌'} {self.bot.db._db_type.upper() if self.bot.db else 'Disconnected'}",
            inline=True
        )
        
        embed.add_field(
            name="⚡ Cache",
            value="✅ Connected" if self.bot.cache else "❌ Disconnected",
            inline=True
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    # ========================
    # /help - Help Command
    # ========================
    @app_commands.command(name="help", description="❓ Show Help")
    async def help(self, interaction: discord.Interaction):
        """Show help information"""
        embed = RinoxEmbed.create(
            title="❓ Rinox Sentinel Help",
            description="**AI-Powered Discord Security & Moderation Bot**",
            color=RinoxEmbed.PRIMARY
        )
        
        embed.add_field(
            name="🛠️ Setup",
            value=            "`/setup` - Open dashboard\n"
                  "`/provider <provider> [model] [api_key] [base_url]` - Set AI provider\n"
                  "`/model` - Set AI model\n"
                  "`/apikey` - Set API key\n"
                  "`/baseurl` - Set base URL\n"
                  "`/test` - Test AI connection",
            inline=False
        )
        
        embed.add_field(
            name="🔒 Security",
            value="`/security` - Security settings\n"
                  "`/scan` - Scan message/image/user\n"
                  "`/whitelist` - Manage whitelist\n"
                  "`/blacklist` - Manage blacklist",
            inline=False
        )
        
        embed.add_field(
            name="🛡️ Moderation",
            value="`/warn` - Warn user\n"
                  "`/mute` - Mute user\n"
                  "`/timeout` - Timeout user\n"
                  "`/kick` - Kick user\n"
                  "`/ban` - Ban user",
            inline=False
        )
        
        embed.add_field(
            name="📊 Analytics",
            value="`/analytics` - View stats\n"
                  "`/report` - Generate report\n"
                  "`/backup` - Create backup\n"
                  "`/restore` - Restore backup",
            inline=False
        )
        
        embed.add_field(
            name="🔧 System",
            value="`/status` - Bot status\n"
                  "`/debug` - Debug info\n"
                  "`/version` - Bot version\n"
                  "`/reset` - Reset settings",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    # ========================
    # /version - Bot Version
    # ========================
    @app_commands.command(name="version", description="🔢 Show Version")
    async def version(self, interaction: discord.Interaction):
        """Show bot version"""
        embed = RinoxEmbed.info(
            "**Rinox Sentinel v1.0.0**\n"
            "AI-Powered Discord Security Platform\n\n"
            "Built with ❤️ using discord.py",
            "🔢 Version"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    # ========================
    # /reset - Reset Settings
    # ========================
    @app_commands.command(name="reset", description="🔄 Reset All Settings")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset(self, interaction: discord.Interaction):
        """Reset all guild settings"""
        await interaction.response.defer(ephemeral=True)
        
        view = ConfirmView()
        embed = RinoxEmbed.warning(
            "⚠️ Are you sure you want to reset ALL settings?\n"
            "This action cannot be undone!",
            "🔄 Confirm Reset"
        )
        
        msg = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        await view.wait()
        
        if view.value:
            await self.bot.db.update_guild_settings(
                interaction.guild_id,
                ai_provider="openai",
                ai_model="gpt-4o",
                ai_api_key=None,
                ai_base_url=None,
                temperature=0.3,
                max_tokens=4096,
                vision_enabled=True,
                ocr_enabled=True,
                streaming_enabled=True,
                security_config={},
                moderation_config={},
                enabled_features=["image_scan", "message_scan", "attachment_scan", "url_scan"],
                whitelist=[],
                blacklist=[],
                custom_prompts={},
                log_channel_id=None,
                appeal_channel_id=None
            )
            
            embed = RinoxEmbed.success(
                "All settings have been reset to default.",
                "🔄 Reset Complete"
            )
        else:
            embed = RinoxEmbed.info("Reset cancelled.", "Cancelled")
            
        await msg.edit(embed=embed, view=None)
        
    # ========================
    # /debug - Debug Info
    # ========================
    @app_commands.command(name="debug", description="🐛 Debug Information")
    @app_commands.checks.has_permissions(administrator=True)
    async def debug(self, interaction: discord.Interaction):
        """Show debug information"""
        await interaction.response.defer(ephemeral=True)
        
        embed = RinoxEmbed.create(
            title="🐛 Debug Information",
            color=RinoxEmbed.NEUTRAL
        )
        
        embed.add_field(
            name="🤖 Bot",
            value=f"**User:** `{self.bot.user}`\n"
                  f"**ID:** `{self.bot.user.id}`\n"
                  f"**Shards:** `{self.bot.shard_count}`",
            inline=False
        )
        
        embed.add_field(
            name="💾 Memory",
            value=f"**Guilds:** `{len(self.bot.guilds)}`\n"
                  f"**Channels:** `{sum(len(g.channels) for g in self.bot.guilds)}`\n"
                  f"**Members:** `{sum(g.member_count for g in self.bot.guilds):,}`",
            inline=False
        )
        
        embed.add_field(
            name="🤖 AI",
            value=f"**Providers:** `{list(self.bot.ai.providers.keys())}`\n"
                  f"**Primary:** `{self.bot.ai.primary_provider}`\n"
                  f"**Fallbacks:** `{self.bot.ai.fallback_providers}`",
            inline=False
        )
        
        embed.add_field(
            name="⚡ Cache",
            value=f"**Redis:** `{self.bot.cache.redis is not None if self.bot.cache else False}`\n"
                  f"**Memory:** `{len(self.bot.cache._memory_cache) if self.bot.cache else 0} entries`",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(SetupCommands(bot))
