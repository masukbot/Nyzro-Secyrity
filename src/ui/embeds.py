"""
Rinox Sentinel - Discord UI Embeds
Premium dashboard-style embeds with progress bars, risk meters, etc.
"""

import discord
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..core.config import BotConfig, ThreatLevel


class RinoxEmbed:
    """Base embed builder"""
    
    PRIMARY = 0x5865F2
    SUCCESS = 0x57F287
    WARNING = 0xFEE75C
    DANGER = 0xED4245
    INFO = 0xEB459E
    NEUTRAL = 0x95A5A6
    PREMIUM = 0xFAA61A
    
    @classmethod
    def create(cls, title: str = None, description: str = None,
               color: int = PRIMARY, **kwargs) -> discord.Embed:
        """Create a styled embed"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(
            text=f"🛡️ Rinox Sentinel v{BotConfig.VERSION}",
            icon_url="https://cdn.discordapp.com/emojis/943450712046141510.png"
        )
        return embed
        
    @classmethod
    def dashboard(cls, guild_name: str, settings: Dict) -> discord.Embed:
        """Main dashboard embed"""
        embed = cls.create(
            title="━━━━━━━━━━━━━━━━━━━━━━",
            description="",
            color=cls.PRIMARY
        )
        
        embed.add_field(
            name="🛡️ Rinox Sentinel",
            value="**Server Protected**",
            inline=False
        )
        
        provider = settings.get("ai_provider", "Not Set").title()
        model = settings.get("ai_model", "N/A")
        vision = "✅ Enabled" if settings.get("vision_enabled") else "❌ Disabled"
        ocr = "✅ Enabled" if settings.get("ocr_enabled") else "❌ Disabled"
        
        embed.add_field(
            name="\u200b",
            value=f"**AI Provider:** `{provider}`\n"
                  f"**Model:** `{model}`\n"
                  f"**Vision:** {vision}\n"
                  f"**OCR:** {ocr}",
            inline=False
        )
        
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━",
            value="",
            inline=False
        )
        
        # Module status
        modules = [
            ("🤖", "AI Settings", settings.get("ai_provider") is not None),
            ("🔒", "Security", True),
            ("🛡️", "Moderation", True),
            ("📝", "Logging", settings.get("log_channel_id") is not None),
            ("⚙️", "Automation", True),
            ("🔧", "Utilities", True),
        ]
        
        module_text = ""
        for emoji, name, enabled in modules:
            status = "🟢" if enabled else "🔴"
            module_text += f"{status} {emoji} **{name}**\n"
            
        embed.add_field(
            name="\u200b",
            value=module_text,
            inline=False
        )
        
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━",
            value="Use the buttons below to configure",
            inline=False
        )
        
        return embed
        
    @classmethod
    def risk_meter(cls, risk_score: int, title: str = "Risk Analysis") -> discord.Embed:
        """Create a risk meter embed"""
        # Determine color and emoji
        if risk_score >= 81:
            color = cls.DANGER
            emoji = "🔴"
            label = "CRITICAL"
        elif risk_score >= 61:
            color = cls.DANGER
            emoji = "🟠"
            label = "HIGH"
        elif risk_score >= 41:
            color = cls.WARNING
            emoji = "🟡"
            label = "MEDIUM"
        elif risk_score >= 21:
            color = cls.WARNING
            emoji = "🟡"
            label = "LOW"
        else:
            color = cls.SUCCESS
            emoji = "🟢"
            label = "SAFE"
            
        # Progress bar
        filled = int(risk_score / 100 * 20)
        empty = 20 - filled
        bar = "█" * filled + "░" * empty
        
        embed = cls.create(
            title=f"{emoji} {title}",
            color=color
        )
        
        embed.add_field(
            name=f"Risk Score: {risk_score}/100",
            value=f"`{bar}`\n**Threat Level: {label}**",
            inline=False
        )
        
        return embed
        
    @classmethod
    def scan_result(cls, result: Any) -> discord.Embed:
        """Create scan result embed"""
        embed = cls.risk_meter(result.risk_score, "Security Scan Result")
        
        # Scan type
        embed.add_field(
            name="📋 Scan Type",
            value=f"`{result.scan_type.value.upper()}`",
            inline=True
        )
        
        # Confidence
        confidence_pct = int(result.confidence * 100)
        embed.add_field(
            name="🎯 AI Confidence",
            value=f"`{confidence_pct}%`",
            inline=True
        )
        
        # Processing time
        embed.add_field(
            name="⚡ Processing Time",
            value=f"`{result.processing_time_ms}ms`",
            inline=True
        )
        
        # Pipeline stages
        stages_text = " → ".join(result.pipeline_stages)
        embed.add_field(
            name="🔬 Pipeline",
            value=f"`{stages_text}`",
            inline=False
        )
        
        # Detected issues
        if result.detected_issues:
            issues_text = "\n".join([f"⚠️ {issue}" for issue in result.detected_issues[:10]])
            embed.add_field(
                name=f"🚨 Detected Issues ({len(result.detected_issues)})",
                value=issues_text,
                inline=False
            )
            
        # Actions
        if result.actions:
            actions_text = ", ".join([a.value.upper() for a in result.actions])
            embed.add_field(
                name="⚡ Actions",
                value=f"`{actions_text}`",
                inline=False
            )
            
        return embed
        
    @classmethod
    def ai_status(cls, provider_status: Dict) -> discord.Embed:
        """AI provider status embed"""
        embed = cls.create(
            title="🤖 AI Provider Status",
            color=cls.INFO
        )
        
        for name, status in provider_status.items():
            status_emoji = {
                "healthy": "🟢",
                "degraded": "🟡",
                "down": "🔴",
                "unknown": "⚪"
            }.get(status["status"], "⚪")
            
            value = (
                f"{status_emoji} **Status:** `{status['status'].upper()}`\n"
                f"📦 **Model:** `{status['model']}`\n"
                f"📊 **Calls:** `{status['total_calls']}` | ❌ `{status['failed_calls']}`"
            )
            
            if status["last_error"]:
                value += f"\n⚠️ **Error:** `{status['last_error'][:50]}`"
                
            embed.add_field(
                name=f"🔹 {name.title()}",
                value=value,
                inline=False
            )
            
        return embed
        
    @classmethod
    def moderation_log(cls, action: str, user: str, moderator: str,
                      reason: str, duration: str = None) -> discord.Embed:
        """Moderation action log embed"""
        action_colors = {
            "warn": cls.WARNING,
            "mute": cls.WARNING,
            "timeout": cls.WARNING,
            "kick": cls.DANGER,
            "ban": cls.DANGER,
            "unban": cls.SUCCESS,
        }
        
        embed = cls.create(
            title=f"🛡️ Moderation: {action.upper()}",
            color=action_colors.get(action.lower(), cls.NEUTRAL)
        )
        
        embed.add_field(name="👤 User", value=user, inline=True)
        embed.add_field(name="🛡️ Moderator", value=moderator, inline=True)
        if duration:
            embed.add_field(name="⏱️ Duration", value=duration, inline=True)
        embed.add_field(name="📝 Reason", value=reason or "No reason provided", inline=False)
        
        return embed
        
    @classmethod
    def analytics(cls, data: Dict) -> discord.Embed:
        """Analytics embed"""
        embed = cls.create(
            title="📊 Server Analytics",
            color=cls.PREMIUM
        )
        
        embed.add_field(
            name="📨 Messages Scanned",
            value=f"`{data.get('messages_scanned', 0):,}`",
            inline=True
        )
        embed.add_field(
            name="🚨 Threats Detected",
            value=f"`{data.get('threats_detected', 0):,}`",
            inline=True
        )
        embed.add_field(
            name="⚡ Actions Taken",
            value=f"`{data.get('actions_taken', 0):,}`",
            inline=True
        )
        embed.add_field(
            name="🤖 AI Calls",
            value=f"`{data.get('ai_calls', 0):,}`",
            inline=True
        )
        embed.add_field(
            name="✅ Accuracy",
            value=f"`{100 - data.get('false_positives', 0)}%`",
            inline=True
        )
        embed.add_field(
            name="📈 Avg Risk",
            value=f"`{data.get('avg_risk_score', 0):.1f}`",
            inline=True
        )
        
        return embed
        
    @classmethod
    def error(cls, error_message: str, title: str = "❌ Error") -> discord.Embed:
        """Error embed"""
        return cls.create(
            title=title,
            description=error_message,
            color=cls.DANGER
        )

    @classmethod
    def warning(cls, error_message: str, title: str = "⚠️ Warning") -> discord.Embed:
        """Warning embed"""
        return cls.create(
            title=title,
            description=error_message,
            color=cls.WARNING
        )
        
    @classmethod
    def success(cls, message: str, title: str = "✅ Success") -> discord.Embed:
        """Success embed"""
        return cls.create(
            title=title,
            description=message,
            color=cls.SUCCESS
        )
        
    @classmethod
    def info(cls, message: str, title: str = "ℹ️ Info") -> discord.Embed:
        """Info embed"""
        return cls.create(
            title=title,
            description=message,
            color=cls.INFO
        )
        
    @classmethod
    def loading(cls, message: str = "Processing...") -> discord.Embed:
        """Loading embed"""
        embed = cls.create(
            title="⏳ Please Wait",
            description=f"{message}\n\n`░░░░░░░░░░░░░░░░░░░░` 0%",
            color=cls.NEUTRAL
        )
        return embed
        
    @classmethod
    def progress_bar(cls, percent: int, width: int = 20) -> str:
        """Generate a progress bar string"""
        filled = int(percent / 100 * width)
        empty = width - filled
        return "█" * filled + "░" * empty
