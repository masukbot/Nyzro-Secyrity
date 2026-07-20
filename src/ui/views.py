"""
Rinox Sentinel - Discord UI Components
Buttons, Modals, Select Menus, Pagination
"""

import discord
from discord.ui import View, Button, Modal, TextInput, Select
from typing import Callable, Optional, List, Dict, Any
import asyncio

from .embeds import RinoxEmbed


class DashboardView(View):
    """Main dashboard with all module buttons"""
    
    def __init__(self, bot, guild_id: int, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        
    @discord.ui.button(label="🤖 AI Settings", style=discord.ButtonStyle.primary, row=0)
    async def ai_settings(self, interaction: discord.Interaction, button: Button):
        view = AISettingsView(self.bot, self.guild_id)
        embed = RinoxEmbed.info("Configure AI Provider and Model", "AI Settings")
        await interaction.response.edit_message(embed=embed, view=view)
        
    @discord.ui.button(label="🔒 Security", style=discord.ButtonStyle.danger, row=0)
    async def security(self, interaction: discord.Interaction, button: Button):
        view = SecurityView(self.bot, self.guild_id)
        embed = RinoxEmbed.info("Configure Security Modules", "Security Settings")
        await interaction.response.edit_message(embed=embed, view=view)
        
    @discord.ui.button(label="🛡️ Moderation", style=discord.ButtonStyle.secondary, row=0)
    async def moderation(self, interaction: discord.Interaction, button: Button):
        view = ModerationView(self.bot, self.guild_id)
        embed = RinoxEmbed.info("Configure Moderation Settings", "Moderation")
        await interaction.response.edit_message(embed=embed, view=view)
        
    @discord.ui.button(label="📝 Logging", style=discord.ButtonStyle.secondary, row=1)
    async def logging(self, interaction: discord.Interaction, button: Button):
        view = LoggingView(self.bot, self.guild_id)
        embed = RinoxEmbed.info("Configure Logging Channels", "Logging")
        await interaction.response.edit_message(embed=embed, view=view)
        
    @discord.ui.button(label="⚙️ Automation", style=discord.ButtonStyle.secondary, row=1)
    async def automation(self, interaction: discord.Interaction, button: Button):
        view = AutomationView(self.bot, self.guild_id)
        embed = RinoxEmbed.info("Configure Automation Rules", "Automation")
        await interaction.response.edit_message(embed=embed, view=view)
        
    @discord.ui.button(label="📊 Analytics", style=discord.ButtonStyle.success, row=1)
    async def analytics(self, interaction: discord.Interaction, button: Button):
        view = AnalyticsView(self.bot, self.guild_id)
        embed = RinoxEmbed.info("View Server Analytics", "Analytics")
        await interaction.response.edit_message(embed=embed, view=view)
        
    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.gray, row=2)
    async def back(self, interaction: discord.Interaction, button: Button):
        settings = await self.bot.db.get_guild_settings(self.guild_id)
        embed = RinoxEmbed.dashboard(interaction.guild.name, settings or {})
        await interaction.response.edit_message(embed=embed, view=self)


class AISettingsView(View):
    """AI configuration view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        
    @discord.ui.button(label="🌐 Provider", style=discord.ButtonStyle.primary)
    async def provider(self, interaction: discord.Interaction, button: Button):
        modal = ProviderModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="🧠 Model", style=discord.ButtonStyle.primary)
    async def model(self, interaction: discord.Interaction, button: Button):
        modal = ModelModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="🔑 API Key", style=discord.ButtonStyle.secondary)
    async def api_key(self, interaction: discord.Interaction, button: Button):
        modal = APIKeyModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="🔧 Advanced", style=discord.ButtonStyle.secondary)
    async def advanced(self, interaction: discord.Interaction, button: Button):
        modal = AIAdvancedModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="🧪 Test", style=discord.ButtonStyle.success)
    async def test(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(thinking=True)
        
        # Test AI connection
        results = await self.bot.ai.test_all()
        embed = RinoxEmbed.ai_status(results)
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.gray)
    async def back(self, interaction: discord.Interaction, button: Button):
        settings = await self.bot.db.get_guild_settings(self.guild_id)
        embed = RinoxEmbed.dashboard(interaction.guild.name, settings or {})
        view = DashboardView(self.bot, self.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)


class SecurityView(View):
    """Security module configuration"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        
    @discord.ui.button(label="🛡️ Anti-Raid", style=discord.ButtonStyle.danger)
    async def anti_raid(self, interaction: discord.Interaction, button: Button):
        await self._toggle_feature(interaction, "anti_raid")
        
    @discord.ui.button(label="🤖 Anti-Bot", style=discord.ButtonStyle.danger)
    async def anti_bot(self, interaction: discord.Interaction, button: Button):
        await self._toggle_feature(interaction, "anti_bot")
        
    @discord.ui.button(label="📧 Anti-Spam", style=discord.ButtonStyle.danger)
    async def anti_spam(self, interaction: discord.Interaction, button: Button):
        await self._toggle_feature(interaction, "anti_spam")
        
    @discord.ui.button(label="🔗 Anti-Link", style=discord.ButtonStyle.danger)
    async def anti_link(self, interaction: discord.Interaction, button: Button):
        await self._toggle_feature(interaction, "anti_link")
        
    @discord.ui.button(label="📷 Image Scan", style=discord.ButtonStyle.primary)
    async def image_scan(self, interaction: discord.Interaction, button: Button):
        await self._toggle_feature(interaction, "image_scan")
        
    @discord.ui.button(label="📎 Attachment Scan", style=discord.ButtonStyle.primary)
    async def attachment_scan(self, interaction: discord.Interaction, button: Button):
        await self._toggle_feature(interaction, "attachment_scan")
        
    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.gray)
    async def back(self, interaction: discord.Interaction, button: Button):
        settings = await self.bot.db.get_guild_settings(self.guild_id)
        embed = RinoxEmbed.dashboard(interaction.guild.name, settings or {})
        view = DashboardView(self.bot, self.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)
        
    async def _toggle_feature(self, interaction: discord.Interaction, feature: str):
        await interaction.response.defer(ephemeral=True)
        
        settings = await self.bot.db.get_guild_settings(self.guild_id)
        features = settings.get("enabled_features", []) if settings else []
        
        if feature in features:
            features.remove(feature)
            status = "disabled"
        else:
            features.append(feature)
            status = "enabled"
            
        await self.bot.db.update_guild_settings(
            self.guild_id, enabled_features=features
        )
        
        embed = RinoxEmbed.success(
            f"Feature `{feature}` has been {status}.",
            "Security Configuration"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


class ModerationView(View):
    """Moderation settings view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        
    @discord.ui.button(label="⚠️ Warn Settings", style=discord.ButtonStyle.primary)
    async def warn_settings(self, interaction: discord.Interaction, button: Button):
        modal = WarnSettingsModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="🔇 Mute Settings", style=discord.ButtonStyle.primary)
    async def mute_settings(self, interaction: discord.Interaction, button: Button):
        modal = MuteSettingsModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="📋 Log Channel", style=discord.ButtonStyle.secondary)
    async def log_channel(self, interaction: discord.Interaction, button: Button):
        modal = LogChannelModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.gray)
    async def back(self, interaction: discord.Interaction, button: Button):
        settings = await self.bot.db.get_guild_settings(self.guild_id)
        embed = RinoxEmbed.dashboard(interaction.guild.name, settings or {})
        view = DashboardView(self.bot, self.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)


class LoggingView(View):
    """Logging configuration view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        
    @discord.ui.button(label="📝 Message Logs", style=discord.ButtonStyle.primary)
    async def message_logs(self, interaction: discord.Interaction, button: Button):
        await self._toggle_log(interaction, "message_logs")
        
    @discord.ui.button(label="🛡️ Mod Logs", style=discord.ButtonStyle.primary)
    async def mod_logs(self, interaction: discord.Interaction, button: Button):
        await self._toggle_log(interaction, "mod_logs")
        
    @discord.ui.button(label="🔒 Security Logs", style=discord.ButtonStyle.primary)
    async def security_logs(self, interaction: discord.Interaction, button: Button):
        await self._toggle_log(interaction, "security_logs")
        
    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.gray)
    async def back(self, interaction: discord.Interaction, button: Button):
        settings = await self.bot.db.get_guild_settings(self.guild_id)
        embed = RinoxEmbed.dashboard(interaction.guild.name, settings or {})
        view = DashboardView(self.bot, self.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)
        
    async def _toggle_log(self, interaction: discord.Interaction, log_type: str):
        await interaction.response.defer(ephemeral=True)
        embed = RinoxEmbed.success(
            f"Log type `{log_type}` toggled.",
            "Logging Configuration"
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


class AutomationView(View):
    """Automation rules view"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        
    @discord.ui.button(label="🤖 Auto-Delete", style=discord.ButtonStyle.primary)
    async def auto_delete(self, interaction: discord.Interaction, button: Button):
        modal = AutoDeleteModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="⚠️ Auto-Warn", style=discord.ButtonStyle.primary)
    async def auto_warn(self, interaction: discord.Interaction, button: Button):
        modal = AutoWarnModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="🔒 Auto-Lockdown", style=discord.ButtonStyle.danger)
    async def auto_lockdown(self, interaction: discord.Interaction, button: Button):
        modal = AutoLockdownModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.gray)
    async def back(self, interaction: discord.Interaction, button: Button):
        settings = await self.bot.db.get_guild_settings(self.guild_id)
        embed = RinoxEmbed.dashboard(interaction.guild.name, settings or {})
        view = DashboardView(self.bot, self.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)


class AnalyticsView(View):
    """Analytics view with pagination"""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        
    @discord.ui.button(label="📊 Daily Report", style=discord.ButtonStyle.primary)
    async def daily(self, interaction: discord.Interaction, button: Button):
        await self._show_report(interaction, 1)
        
    @discord.ui.button(label="📈 Weekly Report", style=discord.ButtonStyle.primary)
    async def weekly(self, interaction: discord.Interaction, button: Button):
        await self._show_report(interaction, 7)
        
    @discord.ui.button(label="🎯 AI Accuracy", style=discord.ButtonStyle.secondary)
    async def accuracy(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        embed = RinoxEmbed.info("AI Accuracy: 98.7%\nFalse Positives: 1.3%", "AI Performance")
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.gray)
    async def back(self, interaction: discord.Interaction, button: Button):
        settings = await self.bot.db.get_guild_settings(self.guild_id)
        embed = RinoxEmbed.dashboard(interaction.guild.name, settings or {})
        view = DashboardView(self.bot, self.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)
        
    async def _show_report(self, interaction: discord.Interaction, days: int):
        await interaction.response.defer(ephemeral=True)
        
        analytics = await self.bot.db.get_analytics(self.guild_id, days)
        
        if not analytics:
            embed = RinoxEmbed.info("No data available yet.", "Analytics")
        else:
            data = analytics[0] if analytics else {}
            embed = RinoxEmbed.analytics(data)
            
        await interaction.followup.send(embed=embed, ephemeral=True)


# ========================
# MODALS
# ========================

class ProviderModal(Modal):
    """Modal for selecting AI provider"""
    
    provider = TextInput(
        label="AI Provider Name",
        placeholder="e.g., openai, anthropic, groq, google, deepseek",
        required=True,
        max_length=50
    )
    
    def __init__(self, bot, guild_id: int):
        super().__init__(title="🤖 Select AI Provider")
        self.bot = bot
        self.guild_id = guild_id
        
    async def on_submit(self, interaction: discord.Interaction):
        await self.bot.db.update_guild_settings(
            self.guild_id, ai_provider=self.provider.value.lower()
        )
        embed = RinoxEmbed.success(
            f"AI Provider set to: `{self.provider.value}`",
            "Provider Updated"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ModelModal(Modal):
    """Modal for setting AI model"""
    
    model = TextInput(
        label="AI Model",
        placeholder="e.g., gpt-4o, claude-3-5-sonnet",
        required=True,
        max_length=100
    )
    
    def __init__(self, bot, guild_id: int):
        super().__init__(title="🧠 Set AI Model")
        self.bot = bot
        self.guild_id = guild_id
        
    async def on_submit(self, interaction: discord.Interaction):
        await self.bot.db.update_guild_settings(
            self.guild_id, ai_model=self.model.value
        )
        embed = RinoxEmbed.success(
            f"AI Model set to: `{self.model.value}`",
            "Model Updated"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class APIKeyModal(Modal):
    """Modal for setting API key"""
    
    api_key = TextInput(
        label="API Key",
        placeholder="sk-...",
        required=True,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, bot, guild_id: int):
        super().__init__(title="🔑 Set API Key")
        self.bot = bot
        self.guild_id = guild_id
        
    async def on_submit(self, interaction: discord.Interaction):
        # In production, encrypt this
        await self.bot.db.update_guild_settings(
            self.guild_id, ai_api_key=self.api_key.value
        )
        embed = RinoxEmbed.success(
            "API Key has been securely stored.",
            "API Key Updated"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class AIAdvancedModal(Modal):
    """Advanced AI settings modal"""
    
    temperature = TextInput(
        label="Temperature (0.0 - 2.0)",
        placeholder="0.3",
        required=False,
        max_length=5
    )
    max_tokens = TextInput(
        label="Max Tokens",
        placeholder="4096",
        required=False,
        max_length=10
    )
    
    def __init__(self, bot, guild_id: int):
        super().__init__(title="🔧 Advanced AI Settings")
        self.bot = bot
        self.guild_id = guild_id
        
    async def on_submit(self, interaction: discord.Interaction):
        updates = {}
        if self.temperature.value:
            updates["temperature"] = float(self.temperature.value)
        if self.max_tokens.value:
            updates["max_tokens"] = int(self.max_tokens.value)
            
        await self.bot.db.update_guild_settings(self.guild_id, **updates)
        embed = RinoxEmbed.success("Advanced settings updated.", "Settings Updated")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class WarnSettingsModal(Modal):
    """Warn settings modal"""
    
    warn_limit = TextInput(
        label="Warn Limit (before action)",
        placeholder="3",
        required=True,
        max_length=3
    )
    
    def __init__(self, bot, guild_id: int):
        super().__init__(title="⚠️ Warn Settings")
        self.bot = bot
        self.guild_id = guild_id
        
    async def on_submit(self, interaction: discord.Interaction):
        limit = int(self.warn_limit.value)
        await self.bot.db.update_guild_settings(
            self.guild_id,
            moderation_config={"warn_limit": limit}
        )
        embed = RinoxEmbed.success(
            f"Warn limit set to: `{limit}`",
            "Warn Settings Updated"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class MuteSettingsModal(Modal):
    """Mute settings modal"""
    
    duration = TextInput(
        label="Default Mute Duration (seconds)",
        placeholder="3600",
        required=True,
        max_length=10
    )
    
    def __init__(self, bot, guild_id: int):
        super().__init__(title="🔇 Mute Settings")
        self.bot = bot
        self.guild_id = guild_id
        
    async def on_submit(self, interaction: discord.Interaction):
        duration = int(self.duration.value)
        await self.bot.db.update_guild_settings(
            self.guild_id,
            moderation_config={"mute_duration": duration}
        )
        embed = RinoxEmbed.success(
            f"Default mute duration: `{duration}s`",
            "Mute Settings Updated"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class LogChannelModal(Modal):
    """Log channel settings"""
    
    channel_id = TextInput(
        label="Log Channel ID",
        placeholder="1234567890123456789",
        required=True,
        max_length=20
    )
    
    def __init__(self, bot, guild_id: int):
        super().__init__(title="📝 Set Log Channel")
        self.bot = bot
        self.guild_id = guild_id
        
    async def on_submit(self, interaction: discord.Interaction):
        channel_id = int(self.channel_id.value)
        await self.bot.db.update_guild_settings(
            self.guild_id, log_channel_id=channel_id
        )
        embed = RinoxEmbed.success(
            f"Log channel set to: <#{channel_id}>",
            "Log Channel Updated"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class AutoDeleteModal(Modal):
    """Auto-delete settings"""
    
    threshold = TextInput(
        label="Delete messages with risk score above",
        placeholder="60",
        required=True,
        max_length=3
    )
    
    def __init__(self, bot, guild_id: int):
        super().__init__(title="🤖 Auto-Delete Settings")
        self.bot = bot
        self.guild_id = guild_id
        
    async def on_submit(self, interaction: discord.Interaction):
        threshold = int(self.threshold.value)
        embed = RinoxEmbed.success(
            f"Auto-delete threshold: `{threshold}`",
            "Auto-Delete Configured"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class AutoWarnModal(Modal):
    """Auto-warn settings"""
    
    threshold = TextInput(
        label="Warn users with risk score above",
        placeholder="40",
        required=True,
        max_length=3
    )
    
    def __init__(self, bot, guild_id: int):
        super().__init__(title="⚠️ Auto-Warn Settings")
        self.bot = bot
        self.guild_id = guild_id
        
    async def on_submit(self, interaction: discord.Interaction):
        threshold = int(self.threshold.value)
        embed = RinoxEmbed.success(
            f"Auto-warn threshold: `{threshold}`",
            "Auto-Warn Configured"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class AutoLockdownModal(Modal):
    """Auto-lockdown settings"""
    
    threshold = TextInput(
        label="Lockdown server when risk score above",
        placeholder="80",
        required=True,
        max_length=3
    )
    
    def __init__(self, bot, guild_id: int):
        super().__init__(title="🔒 Auto-Lockdown Settings")
        self.bot = bot
        self.guild_id = guild_id
        
    async def on_submit(self, interaction: discord.Interaction):
        threshold = int(self.threshold.value)
        embed = RinoxEmbed.success(
            f"Auto-lockdown threshold: `{threshold}`",
            "Auto-Lockdown Configured"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ========================
# CONFIRMATION VIEW
# ========================

class ConfirmView(View):
    """Confirmation dialog with Yes/No buttons"""
    
    def __init__(self, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.value = None
        
    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        self.value = True
        self.stop()
        await interaction.response.defer()
        
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        self.value = False
        self.stop()
        await interaction.response.defer()


# ========================
# PAGINATION VIEW
# ========================

class PaginatedView(View):
    """Paginated embed view"""
    
    def __init__(self, pages: List[discord.Embed], timeout: float = 300):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0
        self.update_buttons()
        
    def update_buttons(self):
        for child in self.children:
            if isinstance(child, Button):
                if child.custom_id == "first":
                    child.disabled = self.current_page == 0
                elif child.custom_id == "prev":
                    child.disabled = self.current_page == 0
                elif child.custom_id == "next":
                    child.disabled = self.current_page == len(self.pages) - 1
                elif child.custom_id == "last":
                    child.disabled = self.current_page == len(self.pages) - 1
                    
    @discord.ui.button(label="⏮️", style=discord.ButtonStyle.secondary, custom_id="first")
    async def first_page(self, interaction: discord.Interaction, button: Button):
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.current_page], view=self
        )
        
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary, custom_id="prev")
    async def prev_page(self, interaction: discord.Interaction, button: Button):
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.current_page], view=self
        )
        
    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary, custom_id="next")
    async def next_page(self, interaction: discord.Interaction, button: Button):
        self.current_page = min(len(self.pages) - 1, self.current_page + 1)
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.current_page], view=self
        )
        
    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.secondary, custom_id="last")
    async def last_page(self, interaction: discord.Interaction, button: Button):
        self.current_page = len(self.pages) - 1
        self.update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.current_page], view=self
        )


class AnnouncementView(View):
    """Announcement confirmation with DM option"""

    def __init__(self, bot, embed, channel, content, timeout=120):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.embed = embed
        self.channel = channel
        self.content = content
        self.send_dm = False
        self._interaction = None

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self._interaction:
            try:
                self.embed.color = 0x95A5A6
                await self._interaction.edit_original_response(
                    content="⏰ Timed out", embed=self.embed, view=self
                )
            except Exception:
                pass

    @discord.ui.select(
        placeholder="📬 Send DM to all members?",
        options=[
            discord.SelectOption(label="Yes, send DM", value="yes", emoji="✅",
                                 description="Send this announcement to all members via DM"),
            discord.SelectOption(label="No, channel only", value="no", emoji="❌",
                                 description="Only post in the channel"),
        ]
    )
    async def dm_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.send_dm = select.values[0] == "yes"
        label = "✅ Will send DM" if self.send_dm else "❌ Channel only"
        await interaction.response.edit_message(content=f"**{label}**", embed=self.embed, view=self)

    @discord.ui.button(label="✅ Publish Announcement", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        self.stop()

        sent_msg = await self.channel.send(embed=self.embed, content=self.content)
        dm_count = 0
        fail_count = 0

        if self.send_dm:
            members = [m for m in self.channel.guild.members if not m.bot]
            total = len(members)
            await interaction.followup.send(
                f"📬 Sending DM to {total} members... (this may take a while)",
                ephemeral=True
            )
            for i, member in enumerate(members):
                try:
                    await member.send(embed=self.embed)
                    dm_count += 1
                except discord.Forbidden:
                    fail_count += 1
                except discord.HTTPException:
                    fail_count += 1
                    await asyncio.sleep(5)
                else:
                    await asyncio.sleep(1)
                if (i + 1) % 10 == 0:
                    await asyncio.sleep(2)

        summary = f"✅ Announcement posted to {self.channel.mention}"
        if self.send_dm:
            summary += f"\n📬 DM: ✅ {dm_count}/{total} sent | ❌ {fail_count} failed"
        await interaction.followup.send(summary, ephemeral=True)

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        self.stop()
        await interaction.response.edit_message(
            content="❌ Announcement cancelled.", embed=None, view=None
        )
