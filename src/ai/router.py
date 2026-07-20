"""
Rinox Sentinel - AI Router
Route AI requests to feature-specific provider chains with fallback + daily credit tracking
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..core.ai_manager import AIResponse

logger = logging.getLogger("Rinox.AI.Router")


@dataclass
class RouteConfig:
    """Configuration for a single provider in a feature chain"""
    provider: str
    model: Optional[str] = None
    priority: int = 0
    max_daily: int = 0
    daily_used: int = 0


class AIRouter:
    """
    Routes AI requests per-feature with automatic fallback.

    Example config for "chat" feature:
        [0] openai/gpt-4o (max 100/day)
        [1] anthropic/claude-3-5 (max 50/day)
        [2] google/gemini-1.5-pro (no limit)
    """

    def __init__(self, ai_manager, db=None):
        self.ai = ai_manager
        self.db = db
        self._cache: Dict[str, List[RouteConfig]] = {}

    async def get_providers(self, guild_id: int, feature: str) -> List[RouteConfig]:
        """Get ordered list of providers for a feature (cached)"""
        cache_key = f"{guild_id}:{feature}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if self.db:
            rows = await self.db.get_feature_providers(guild_id, feature)
            configs = []
            for r in rows:
                configs.append(RouteConfig(
                    provider=r.get("provider"),
                    model=r.get("model"),
                    priority=r.get("priority", 0),
                    max_daily=r.get("max_daily", 0),
                    daily_used=r.get("daily_used", 0),
                ))
            self._cache[cache_key] = configs
            return configs

        return []

    def invalidate_cache(self, guild_id: int = None, feature: str = None):
        """Clear route cache"""
        if guild_id and feature:
            self._cache.pop(f"{guild_id}:{feature}", None)
        elif guild_id:
            keys = [k for k in self._cache if k.startswith(f"{guild_id}:")]
            for k in keys:
                self._cache.pop(k, None)
        else:
            self._cache.clear()

    async def route(self, guild_id: int, feature: str,
                    messages: List[Dict[str, str]],
                    system_prompt: Optional[str] = None,
                    temperature: float = 0.3,
                    max_tokens: int = 4096,
                    **kwargs) -> AIResponse:
        """
        Route an AI request through the feature's provider chain.

        Tries providers in priority order.
        Falls back to next if:
          - Provider is not loaded in AIManager
          - Provider returns error
          - Daily credit cap reached
        """
        providers = await self.get_providers(guild_id, feature)

        if not providers:
            providers = [RouteConfig(
                provider=self.ai.primary_provider or "openai",
                model=None
            )]

        last_error = None
        for cfg in providers:
            if cfg.provider not in self.ai.providers:
                logger.debug(f"Router: provider {cfg.provider} not loaded, skipping")
                continue

            # Check daily cap
            if cfg.max_daily > 0 and cfg.daily_used >= cfg.max_daily:
                logger.info(f"Router: {cfg.provider} daily cap reached ({cfg.daily_used}/{cfg.max_daily})")
                continue

            prov = self.ai.providers[cfg.provider]
            model = cfg.model or prov.model

            response = await prov.chat(
                messages=messages,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            if response.success:
                response.provider = cfg.provider
                response.model = model

                # Track usage
                if self.db and cfg.max_daily > 0:
                    used, limit = await self.db.increment_daily_usage(
                        guild_id, feature, cfg.provider
                    )
                    cfg.daily_used = used

                logger.info(f"Router: {feature} → {cfg.provider}/{model} (latency: {response.latency_ms}ms)")
                return response
            else:
                last_error = response.error
                logger.warning(f"Router: {cfg.provider} failed for {feature}: {response.error}")

        return AIResponse(
            content=f"All providers for '{feature}' failed. Last error: {last_error}",
            provider="router",
            model="none",
            success=False,
            error=f"All providers for feature '{feature}' failed"
        )

    async def route_chat(self, guild_id: int, messages: List[Dict[str, str]],
                          system_prompt: Optional[str] = None, **kwargs) -> AIResponse:
        """Shortcut: route to 'chat' feature"""
        return await self.route(guild_id, "chat", messages, system_prompt, **kwargs)

    async def route_moderation(self, guild_id: int, content: str, **kwargs) -> AIResponse:
        """Shortcut: route to 'moderation' feature"""
        messages = [{"role": "user", "content": content}]
        return await self.route(guild_id, "moderation", messages,
                                 system_prompt="You analyze content for toxicity and threats.", **kwargs)

    async def route_translate(self, guild_id: int, text: str,
                               target_lang: str = "english", **kwargs) -> AIResponse:
        """Shortcut: route to 'translate' feature"""
        messages = [{"role": "user", "content": text}]
        prompt = f"Translate the following text to {target_lang}. Respond only with the translation."
        return await self.route(guild_id, "translate", messages, system_prompt=prompt, **kwargs)

    async def route_summarize(self, guild_id: int, text: str, **kwargs) -> AIResponse:
        """Shortcut: route to 'summarize' feature"""
        messages = [{"role": "user", "content": text}]
        prompt = "Summarize the following conversation concisely. Focus on key points."
        return await self.route(guild_id, "summarize", messages, system_prompt=prompt, **kwargs)

    async def route_vision(self, guild_id: int, image_url: str, prompt: str, **kwargs) -> AIResponse:
        """Shortcut: route to 'vision' feature"""
        providers = await self.get_providers(guild_id, "vision")

        if not providers:
            return await self.ai.vision(image_url, prompt, **kwargs)

        for cfg in providers:
            if cfg.provider not in self.ai.providers:
                continue
            prov = self.ai.providers[cfg.provider]
            response = await prov.vision(image_url, prompt, **kwargs)
            if response.success:
                return response

        return AIResponse(content="Vision analysis unavailable", provider="none",
                          model="none", success=False, error="All vision providers failed")

    async def route_image_gen(self, guild_id: int, prompt: str, size: str = "1024x1024",
                               **kwargs) -> AIResponse:
        """Route image generation request through 'image_gen' feature chain"""
        providers = await self.get_providers(guild_id, "image_gen")

        if not providers:
            # Default to OpenAI if no config
            if "openai" in self.ai.providers:
                prov = self.ai.providers["openai"]
                return await prov.generate_image(prompt, size, **kwargs)
            return AIResponse(content="No image generation provider available", provider="none",
                              model="none", success=False, error="No provider")

        for cfg in providers:
            if cfg.provider not in self.ai.providers:
                continue

            # Check daily cap
            if cfg.max_daily > 0 and cfg.daily_used >= cfg.max_daily:
                continue

            prov = self.ai.providers[cfg.provider]
            response = await prov.generate_image(prompt, size, **kwargs)

            if response.success:
                response.provider = cfg.provider
                response.model = cfg.model or prov.model

                if self.db and cfg.max_daily > 0:
                    used, limit = await self.db.increment_daily_usage(
                        guild_id, "image_gen", cfg.provider
                    )
                    cfg.daily_used = used

                return response

        return AIResponse(content="All image generation providers failed", provider="none",
                          model="none", success=False, error="All image gen providers failed")