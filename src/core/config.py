"""
Rinox Sentinel - Bot Configuration
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import os


class AIProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OPENROUTER = "openrouter"
    GROQ = "groq"
    DEEPSEEK = "deepseek"
    XAI = "xai"
    MISTRAL = "mistral"
    COHERE = "cohere"
    AZURE = "azure"
    OLLAMA = "ollama"
    LM_STUDIO = "lm_studio"
    CUSTOM = "custom"


class ThreatLevel(Enum):
    SAFE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AIConfig:
    """AI Provider Configuration"""
    provider: AIProvider = AIProvider.OPENAI
    model: str = "gpt-4o"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    endpoint: Optional[str] = None
    vision_endpoint: Optional[str] = None
    embedding_endpoint: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout: int = 30
    streaming: bool = True
    vision_enabled: bool = True
    ocr_enabled: bool = True


@dataclass
class SecurityConfig:
    """Security Module Configuration"""
    anti_raid: bool = True
    anti_nuke: bool = True
    anti_spam: bool = True
    anti_link: bool = True
    anti_invite: bool = True
    anti_token_grabber: bool = True
    anti_malware: bool = True
    anti_webhook: bool = True
    anti_bot_attack: bool = True
    anti_fake_account: bool = True
    anti_alt_account: bool = True
    anti_emoji_spam: bool = True
    anti_sticker_spam: bool = True
    anti_voice_spam: bool = True
    
    # Thresholds
    spam_threshold: int = 5
    mention_threshold: int = 5
    raid_threshold: int = 10
    join_rate_limit: int = 10


@dataclass
class ModerationConfig:
    """Moderation Configuration"""
    warn_limit: int = 3
    mute_duration: int = 3600  # seconds
    timeout_duration: int = 3600
    tempban_duration: int = 86400
    auto_delete_spam: bool = True
    auto_warn_spam: bool = True
    auto_timeout_repeat: bool = True
    log_channel: Optional[int] = None
    appeal_channel: Optional[int] = None


@dataclass
class GuildSettings:
    """Per-guild settings"""
    guild_id: int
    ai_config: AIConfig = field(default_factory=AIConfig)
    security_config: SecurityConfig = field(default_factory=SecurityConfig)
    moderation_config: ModerationConfig = field(default_factory=ModerationConfig)
    enabled_features: List[str] = field(default_factory=lambda: [
        "image_scan", "message_scan", "attachment_scan", "url_scan"
    ])
    whitelist: List[int] = field(default_factory=list)
    blacklist: List[int] = field(default_factory=list)
    custom_prompts: Dict[str, str] = field(default_factory=dict)
    language: str = "en"
    premium: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class BotConfig:
    """Global bot configuration"""
    
    VERSION = "1.0.0"
    NAME = "Rinox Sentinel"
    EMOJI = "🛡️"
    
    # Color scheme
    COLORS = {
        "primary": 0x5865F2,      # Discord blurple
        "success": 0x57F287,      # Green
        "warning": 0xFEE75C,       # Yellow
        "danger": 0xED4245,        # Red
        "info": 0xEB459E,          # Pink
        "neutral": 0x95A5A6,       # Gray
        "premium": 0xFAA61A,       # Gold
    }
    
    # Threat level colors
    THREAT_COLORS = {
        ThreatLevel.SAFE: 0x57F287,
        ThreatLevel.LOW: 0xFEE75C,
        ThreatLevel.MEDIUM: 0xFAA61A,
        ThreatLevel.HIGH: 0xED4245,
        ThreatLevel.CRITICAL: 0x8B0000,
    }
    
    # Default models per provider
    DEFAULT_MODELS = {
        AIProvider.OPENAI: "gpt-4o",
        AIProvider.ANTHROPIC: "claude-3-5-sonnet-20241022",
        AIProvider.GOOGLE: "gemini-1.5-pro",
        AIProvider.GROQ: "llama-3.3-70b-versatile",
        AIProvider.DEEPSEEK: "deepseek-chat",
        AIProvider.MISTRAL: "mistral-large-latest",
        AIProvider.COHERE: "command-r-plus",
        AIProvider.XAI: "grok-2",
        AIProvider.AZURE: "gpt-4o",
        AIProvider.OLLAMA: "llama3.2",
        AIProvider.LM_STUDIO: "local-model",
    }
    
    # Supported file types for scanning
    DANGEROUS_EXTENSIONS = [
        ".exe", ".scr", ".bat", ".cmd", ".sh", ".dll",
        ".js", ".vbs", ".ps1", ".wsf", ".hta", ".jar",
        ".apk", ".ipa", ".msi", ".dmg", ".pkg",
        ".zip", ".rar", ".7z", ".tar", ".gz",
    ]
    
    OFFICE_EXTENSIONS = [
        ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".pdf", ".rtf", ".odt", ".ods", ".odp",
    ]
    
    # Risk score thresholds
    RISK_THRESHOLDS = {
        "safe": (0, 20),
        "low": (21, 40),
        "medium": (41, 60),
        "high": (61, 80),
        "critical": (81, 100),
    }
