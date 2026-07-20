"""
Rinox Sentinel - AI Provider Registry
Dynamic provider discovery and management
"""

import logging
from typing import Dict, Optional, Type

logger = logging.getLogger("Rinox.AI.Registry")


class ProviderRegistry:
    """Registry for AI providers, allows dynamic registration"""

    _providers: Dict[str, Type] = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register a provider class"""
        def wrapper(provider_cls):
            cls._providers[name] = provider_cls
            logger.debug(f"Registered AI provider: {name}")
            return provider_cls
        return wrapper

    @classmethod
    def get(cls, name: str) -> Optional[Type]:
        return cls._providers.get(name)

    @classmethod
    def list(cls) -> Dict[str, Type]:
        return dict(cls._providers)

    @classmethod
    def discover(cls):
        """Import all provider modules to trigger registration"""
        try:
            from ..core.ai_manager import (
                OpenAIProvider, AnthropicProvider, GroqProvider,
                GoogleProvider, OpenAICompatibleProvider, CustomProvider
            )
            cls._providers["openai"] = OpenAIProvider
            cls._providers["anthropic"] = AnthropicProvider
            cls._providers["groq"] = GroqProvider
            cls._providers["google"] = GoogleProvider
            cls._providers["deepseek"] = OpenAICompatibleProvider
            cls._providers["mistral"] = OpenAICompatibleProvider
            cls._providers["xai"] = OpenAICompatibleProvider
            cls._providers["cohere"] = OpenAICompatibleProvider
            cls._providers["ollama"] = OpenAICompatibleProvider
            cls._providers["custom"] = CustomProvider
            cls._providers["openai_compatible"] = OpenAICompatibleProvider
        except ImportError as e:
            logger.warning(f"Could not discover providers: {e}")