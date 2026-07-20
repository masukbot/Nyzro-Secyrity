"""
Rinox Sentinel - AI Route Commands
Manage per-feature AI provider chains, channel AI modes
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Dict

from ..ui.embeds import RinoxEmbed


class AIRouteCommands(commands.Cog):
    """AI routing and channel mode configuration"""

    FEATURES = [
        app_commands.Choice(name="Chat", value="chat"),
        app_commands.Choice(name="Moderation", value="moderation"),
        app_commands.Choice(name="Translate", value="translate"),
        app_commands.Choice(name="Summarize", value="summarize"),
        app_commands.Choice(name="Vision", value="vision"),
        app_commands.Choice(name="Image Generation", value="image_gen"),
    ]

    PROVIDERS = [
        app_commands.Choice(name="OpenAI", value="openai"),
        app_commands.Choice(name="Anthropic", value="anthropic"),
        app_commands.Choice(name="Google Gemini", value="google"),
        app_commands.Choice(name="Groq", value="groq"),
        app_commands.Choice(name="DeepSeek", value="deepseek"),
        app_commands.Choice(name="Mistral", value="mistral"),
        app_commands.Choice(name="xAI (Grok)", value="xai"),
        app_commands.Choice(name="Cohere", value="cohere"),
        app_commands.Choice(name="Ollama", value="ollama"),
        app_commands.Choice(name="Azure OpenAI", value="azure"),
        app_commands.Choice(name="Custom", value="custom"),
    ]

    CHANNEL_FEATURES = [
        app_commands.Choice(name="💬 Chat — AI replies to every message", value="chat"),
        app_commands.Choice(name="🌍 Translate — auto-translate messages", value="translate"),
        app_commands.Choice(name="📝 Summarize — auto-summarize conversations", value="summarize"),
        app_commands.Choice(name="🖼️ Vision — AI analyzes images", value="vision"),
        app_commands.Choice(name="🎨 Image Gen — text-to-image generation", value="image_gen"),
        app_commands.Choice(name="🛡️ Moderation — AI content moderation", value="moderation"),
    ]

    TARGET_LANGS = [
        app_commands.Choice(name="🌐 Auto — match user's language", value="auto"),
        app_commands.Choice(name="English", value="english"),
        app_commands.Choice(name="Bengali / বাংলা", value="bengali"),
        app_commands.Choice(name="Hindi / हिन्दी", value="hindi"),
        app_commands.Choice(name="Spanish / Español", value="spanish"),
        app_commands.Choice(name="French / Français", value="french"),
        app_commands.Choice(name="German / Deutsch", value="german"),
        app_commands.Choice(name="Arabic / العربية", value="arabic"),
        app_commands.Choice(name="Chinese / 中文", value="chinese"),
        app_commands.Choice(name="Japanese / 日本語", value="japanese"),
        app_commands.Choice(name="Russian / Русский", value="russian"),
        app_commands.Choice(name="Portuguese / Português", value="portuguese"),
        app_commands.Choice(name="Urdu / اردو", value="urdu"),
    ]

    def __init__(self, bot):
        self.bot = bot
        self._cooldowns: Dict[str, float] = {}

    ai_group = app_commands.Group(name="ai", description="AI Router and Channel Mode Configuration")

    # ========================
    # AI ROUTE MANAGEMENT
    # ========================

    @ai_group.command(name="route-set", description="Set per-feature AI provider (for chat, moderation, vision, etc.)")
    @app_commands.describe(
        feature="Feature to configure",
        provider="AI provider for this feature",
        model="Model name (e.g., gpt-4o, claude-3-5-sonnet)",
        priority="Priority (0=primary, 1=first fallback, etc.)",
        max_daily="Daily request limit (0=unlimited)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def route_set(self, interaction: discord.Interaction,
                        feature: app_commands.Choice[str],
                        provider: app_commands.Choice[str],
                        model: Optional[str] = None,
                        priority: app_commands.Range[int, 0, 10] = 0,
                        max_daily: app_commands.Range[int, 0, 100000] = 0):
        await interaction.response.defer(ephemeral=True)

        await self.bot.db.set_feature_provider(
            interaction.guild_id,
            feature.value,
            provider.value,
            model,
            priority,
            max_daily
        )
        self.bot.ai.router.invalidate_cache(interaction.guild_id, feature.value)

        model_text = f"`{model}`" if model else "default"
        embed = RinoxEmbed.success(
            f"**Feature:** `{feature.name}`\n"
            f"**Provider:** `{provider.name}`\n"
            f"**Model:** {model_text}\n"
            f"**Priority:** `{priority}`\n"
            f"**Daily Limit:** `{'Unlimited' if max_daily == 0 else max_daily}`",
            "Route Configured"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @ai_group.command(name="route-remove", description="Remove a provider from a feature's chain")
    @app_commands.describe(
        feature="Feature to modify",
        provider="Provider to remove"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def route_remove(self, interaction: discord.Interaction,
                           feature: app_commands.Choice[str],
                           provider: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)

        await self.bot.db.remove_feature_provider(
            interaction.guild_id, feature.value, provider.value
        )
        self.bot.ai.router.invalidate_cache(interaction.guild_id, feature.value)

        embed = RinoxEmbed.success(
            f"Removed `{provider.name}` from `{feature.name}` chain.",
            "Provider Removed"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @ai_group.command(name="route-list", description="Show all feature provider chains")
    @app_commands.describe(feature="Filter by feature (optional)")
    @app_commands.checks.has_permissions(administrator=True)
    async def route_list(self, interaction: discord.Interaction,
                         feature: Optional[str] = None):
        await interaction.response.defer(ephemeral=True)

        configs = await self.bot.db.get_all_feature_configs(interaction.guild_id)

        if not configs:
            embed = RinoxEmbed.info("No custom routes configured. Default routing will be used.", "AI Routes")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        embed = RinoxEmbed.create(
            title="AI Provider Routes",
            color=RinoxEmbed.INFO
        )

        features_to_show = [feature] if feature else list(configs.keys())
        for feat in features_to_show:
            if feat not in configs:
                continue
            providers_text = ""
            for p in configs[feat]:
                model_text = f" ({p['model']})" if p.get("model") else ""
                status = "ACTIVE" if p.get("enabled") else "DISABLED"
                daily = f" [{p['daily_used']}/{p['max_daily']}]" if p.get("max_daily", 0) > 0 else ""
                providers_text += f"{status} `#{p['priority']}` **{p['provider']}**{model_text}{daily}\n"

            embed.add_field(
                name=f"{feat.upper()}",
                value=providers_text or "`No providers configured`",
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @ai_group.command(name="route-test", description="Test a feature's provider chain")
    @app_commands.describe(feature="Feature to test")
    @app_commands.checks.has_permissions(administrator=True)
    async def route_test(self, interaction: discord.Interaction,
                         feature: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)

        embed = RinoxEmbed.loading(f"Testing {feature.name} routing...")
        msg = await interaction.followup.send(embed=embed, ephemeral=True)

        response = await self.bot.ai.router.route(
            interaction.guild_id,
            feature.value,
            messages=[{"role": "user", "content": "Say 'okay' if you are working."}],
            max_tokens=10,
            temperature=0.1
        )

        embed = RinoxEmbed.create(
            title=f"{feature.name} Route Test",
            color=RinoxEmbed.SUCCESS if response.success else RinoxEmbed.DANGER
        )

        embed.add_field(name="Status", value="Success" if response.success else "Failed", inline=True)
        embed.add_field(name="Provider", value=f"`{response.provider}`", inline=True)
        embed.add_field(name="Model", value=f"`{response.model}`", inline=True)
        embed.add_field(name="Latency", value=f"`{response.latency_ms}ms`", inline=True)
        embed.add_field(name="Response", value=response.content[:200] if response.success else response.error, inline=False)

        await msg.edit(embed=embed)

    @ai_group.command(name="route-reset-credits", description="Reset daily usage counter for a provider")
    @app_commands.describe(
        feature="Feature",
        provider="Provider to reset"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def route_reset_credits(self, interaction: discord.Interaction,
                                   feature: app_commands.Choice[str],
                                   provider: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)

        await self.bot.db.reset_daily_usage(
            interaction.guild_id, feature.value, provider.value
        )
        self.bot.ai.router.invalidate_cache(interaction.guild_id, feature.value)

        embed = RinoxEmbed.success(
            f"Daily usage reset for `{provider.name}` on `{feature.name}`.",
            "Credits Reset"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ========================
    # CHANNEL AI MODES
    # ========================

    async def provider_autocomplete(self, interaction: discord.Interaction, current: str):
        """Show only providers that are actually configured (loaded in AI Manager)"""
        guild_settings = await self.bot.db.get_guild_settings(interaction.guild_id) or {}
        default_provider = guild_settings.get("ai_provider", "openai")

        configured = set(self.bot.ai.providers.keys())
        # Always include the guild default even if not loaded yet
        if default_provider not in configured and default_provider:
            configured.add(default_provider)

        choices = []
        for name, value in [
            ("OpenAI", "openai"), ("Anthropic", "anthropic"), ("Google", "google"),
            ("Groq", "groq"), ("DeepSeek", "deepseek"), ("Mistral", "mistral"),
            ("xAI", "xai"), ("Cohere", "cohere"), ("Ollama", "ollama"),
            ("Azure OpenAI", "azure"), ("Custom", "custom"),
        ]:
            if value in configured and (not current or current.lower() in value.lower() or current.lower() in name.lower()):
                label = f"{name}" + (" ⭐" if value == default_provider else "")
                choices.append(app_commands.Choice(name=label, value=value))

        return choices[:25]

    async def model_autocomplete(self, interaction: discord.Interaction, current: str):
        """Suggest model from guild defaults"""
        guild_settings = await self.bot.db.get_guild_settings(interaction.guild_id) or {}
        default_model = guild_settings.get("ai_model", "gpt-4o")

        if not current or current.lower() in default_model.lower():
            return [app_commands.Choice(name=f"{default_model} ⭐ (default)", value=default_model)]
        return [app_commands.Choice(name=current, value=current)]

    @ai_group.command(name="channel-set", description="Set AI mode for a channel (auto-process messages)")
    @app_commands.describe(
        channel="Channel to configure",
        feature="AI feature to activate in this channel",
        provider="AI provider (only shows configured providers)",
        model="Model name (defaults to provider default if omitted)",
        target_lang="Target language (auto = match user's language)",
        custom_instructions="Custom system prompt for this channel's AI",
        cooldown="Seconds between messages per user (0 = no cooldown)"
    )
    @app_commands.choices(feature=CHANNEL_FEATURES)
    @app_commands.choices(target_lang=TARGET_LANGS)
    @app_commands.autocomplete(provider=provider_autocomplete)
    @app_commands.autocomplete(model=model_autocomplete)
    @app_commands.checks.has_permissions(administrator=True)
    async def channel_set(self, interaction: discord.Interaction,
                          channel: discord.TextChannel,
                          feature: app_commands.Choice[str],
                          provider: Optional[str] = None,
                          model: Optional[str] = None,
                          target_lang: Optional[app_commands.Choice[str]] = None,
                          custom_instructions: Optional[str] = None,
                          cooldown: Optional[app_commands.Range[int, 0, 300]] = None):
        await interaction.response.defer(ephemeral=True)

        # Fetch guild default settings
        settings = await self.bot.db.get_guild_settings(interaction.guild_id)
        default_provider = (settings or {}).get("ai_provider", "openai")
        default_model = (settings or {}).get("ai_model", "gpt-4o")

        use_provider = provider or default_provider
        use_model = model or default_model

        config = {}
        if feature.value in ("translate", "chat") and target_lang:
            config["target_lang"] = target_lang.value
        if custom_instructions:
            config["custom_instructions"] = custom_instructions
        if cooldown is not None and cooldown > 0:
            config["cooldown"] = cooldown

        config["provider"] = use_provider
        config["model"] = use_model

        # Auto-configure route only if provider was explicitly given
        if provider:
            await self.bot.db.set_feature_provider(
                interaction.guild_id,
                feature.value,
                use_provider,
                use_model,
                0,
                0
            )
            self.bot.ai.router.invalidate_cache(interaction.guild_id, feature.value)

        await self.bot.db.set_channel_ai_mode(
            interaction.guild_id, channel.id, feature.value, config
        )

        msg = (
            f"**Channel:** {channel.mention}\n"
            f"**Mode:** `{feature.name}`\n"
            f"**Provider:** `{use_provider}`\n"
            f"**Model:** `{use_model}`"
        )
        if custom_instructions:
            msg += f"\n**Custom:** `{custom_instructions[:50]}{'...' if len(custom_instructions) > 50 else ''}`"
        if target_lang:
            msg += f"\n**Language:** `{'Auto' if target_lang.value == 'auto' else target_lang.name}`"
        if cooldown:
            msg += f"\n**Cooldown:** `{cooldown}s`"
        if not provider:
            msg += "\n\n📌 *Using guild default provider (⭐). Set a custom one with `/provider`.*"

        embed = RinoxEmbed.success(msg, "Channel AI Mode Active")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @ai_group.command(name="channel-remove", description="Remove AI mode from a channel")
    @app_commands.describe(channel="Channel to remove AI mode from")
    @app_commands.checks.has_permissions(administrator=True)
    async def channel_remove(self, interaction: discord.Interaction,
                             channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        await self.bot.db.remove_channel_ai_mode(interaction.guild_id, channel.id)

        embed = RinoxEmbed.success(
            f"AI mode removed from {channel.mention}.",
            "Channel Mode Removed"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @ai_group.command(name="channel-list", description="List all channels with AI modes")
    @app_commands.checks.has_permissions(administrator=True)
    async def channel_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        modes = await self.bot.db.get_all_channel_ai_modes(interaction.guild_id)

        if not modes:
            embed = RinoxEmbed.info("No AI mode channels configured.", "Channel AI Modes")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        embed = RinoxEmbed.create(
            title="Channel AI Modes",
            color=RinoxEmbed.INFO
        )

        for m in modes:
            channel = interaction.guild.get_channel(m["channel_id"])
            ch_name = channel.mention if channel else f"`{m['channel_id']}`"
            cfg = m.get("config", {}) or {}
            if isinstance(cfg, str):
                import json
                cfg = json.loads(cfg) if cfg else {}
            parts = [f"**Mode:** `{m['feature']}`"]
            if cfg.get("provider"):
                parts.append(f"**Provider:** `{cfg['provider']}`")
            if cfg.get("model"):
                parts.append(f"**Model:** `{cfg['model']}`")
            if cfg.get("target_lang"):
                parts.append(f"**Lang:** `{cfg['target_lang']}`")
            if cfg.get("custom_instructions"):
                ci = cfg["custom_instructions"]
                parts.append(f"**Prompt:** `{ci[:40]}{'...' if len(ci) > 40 else ''}`")
            if cfg.get("cooldown"):
                parts.append(f"**⏳ Cooldown:** `{cfg['cooldown']}s`")
            embed.add_field(
                name=f"{ch_name}",
                value=" | ".join(parts),
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AIRouteCommands(bot))
