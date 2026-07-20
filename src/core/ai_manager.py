"""
Rinox Sentinel - AI Manager
Multi-provider AI with fallback, load balancing, and caching
"""

import os
import time
import logging
import asyncio
from typing import Optional, Dict, Any, List, AsyncGenerator, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

if TYPE_CHECKING:
    from ..ai.router import AIRouter

import httpx
import openai

logger = logging.getLogger("Rinox.AI")


class AIStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class AIResponse:
    """Standardized AI response"""
    content: str
    provider: str
    model: str
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: int = 0
    confidence: float = 0.0
    success: bool = True
    error: Optional[str] = None
    streaming: bool = False


class AIProvider:
    """Base AI provider class"""
    
    def __init__(self, name: str, api_key: str, model: str,
                 base_url: Optional[str] = None, **kwargs):
        self.name = name
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.status = AIStatus.UNKNOWN
        self.last_error = None
        self.total_calls = 0
        self.failed_calls = 0
        self.avg_latency = 0
        self.client = None
        
    async def initialize(self):
        """Initialize the provider client"""
        pass
        
    async def chat(self, messages: List[Dict[str, str]], 
                   system_prompt: Optional[str] = None,
                   temperature: float = 0.3,
                   max_tokens: int = 4096,
                   stream: bool = False,
                   **kwargs) -> AIResponse:
        """Send a chat request"""
        raise NotImplementedError
        
    async def vision(self, image_url: str, prompt: str,
                    **kwargs) -> AIResponse:
        """Analyze an image"""
        raise NotImplementedError

    async def generate_image(self, prompt: str, size: str = "1024x1024",
                             **kwargs) -> AIResponse:
        """Generate an image from text prompt"""
        raise NotImplementedError

    async def test_connection(self) -> AIStatus:
        """Test provider connectivity"""
        raise NotImplementedError


class OpenAIProvider(AIProvider):
    """OpenAI provider"""
    
    async def initialize(self):
        self.client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url or "https://api.openai.com/v1"
        )
        
    async def chat(self, messages, system_prompt=None, temperature=0.3,
                  max_tokens=4096, stream=False, **kwargs):
        start = time.time()
        try:
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
                
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )
            
            latency = int((time.time() - start) * 1000)
            
            if stream:
                return AIResponse(
                    content="", provider=self.name, model=self.model,
                    latency_ms=latency, streaming=True
                )
                
            content = response.choices[0].message.content
            
            return AIResponse(
                content=content,
                provider=self.name,
                model=self.model,
                tokens_input=response.usage.prompt_tokens if response.usage else 0,
                tokens_output=response.usage.completion_tokens if response.usage else 0,
                latency_ms=latency,
                success=True
            )
            
        except Exception as e:
            self.last_error = str(e)
            self.failed_calls += 1
            return AIResponse(
                content="", provider=self.name, model=self.model,
                success=False, error=str(e)
            )
            
    async def vision(self, image_url: str, prompt: str, **kwargs):
        start = time.time()
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=4096
            )
            
            latency = int((time.time() - start) * 1000)
            content = response.choices[0].message.content
            
            return AIResponse(
                content=content,
                provider=self.name,
                model=self.model,
                tokens_input=response.usage.prompt_tokens if response.usage else 0,
                tokens_output=response.usage.completion_tokens if response.usage else 0,
                latency_ms=latency,
                success=True
            )
            
        except Exception as e:
            return AIResponse(
                content="", provider=self.name, model=self.model,
                success=False, error=str(e)
            )
            
    async def generate_image(self, prompt: str, size: str = "1024x1024", **kwargs):
        start = time.time()
        try:
            response = await self.client.images.generate(
                model=self.model,
                prompt=prompt,
                size=size,
                quality="standard",
                n=1
            )
            latency = int((time.time() - start) * 1000)
            image_url = response.data[0].url
            return AIResponse(
                content=image_url,
                provider=self.name,
                model=self.model,
                latency_ms=latency,
                success=True
            )
        except Exception as e:
            return AIResponse(
                content="", provider=self.name, model=self.model,
                success=False, error=str(e)
            )

    async def test_connection(self):
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )
            self.status = AIStatus.HEALTHY
            return self.status
        except Exception as e:
            self.status = AIStatus.DOWN
            self.last_error = str(e)
            return self.status


class AnthropicProvider(AIProvider):
    """Anthropic Claude provider"""
    
    async def initialize(self):
        import anthropic
        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        
    async def chat(self, messages, system_prompt=None, temperature=0.3,
                  max_tokens=4096, stream=False, **kwargs):
        start = time.time()
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "",
                messages=messages
            )
            
            latency = int((time.time() - start) * 1000)
            content = response.content[0].text if response.content else ""
            
            return AIResponse(
                content=content,
                provider=self.name,
                model=self.model,
                tokens_input=response.usage.input_tokens if response.usage else 0,
                tokens_output=response.usage.output_tokens if response.usage else 0,
                latency_ms=latency,
                success=True
            )
            
        except Exception as e:
            return AIResponse(
                content="", provider=self.name, model=self.model,
                success=False, error=str(e)
            )
            
    async def vision(self, image_url: str, prompt: str, **kwargs):
        start = time.time()
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image", "source": {"type": "url", "url": image_url}}
                    ]
                }]
            )
            
            latency = int((time.time() - start) * 1000)
            content = response.content[0].text if response.content else ""
            
            return AIResponse(
                content=content,
                provider=self.name,
                model=self.model,
                latency_ms=latency,
                success=True
            )
            
        except Exception as e:
            return AIResponse(
                content="", provider=self.name, model=self.model,
                success=False, error=str(e)
            )
            
    async def generate_image(self, prompt: str, size: str = "1024x1024", **kwargs):
        return AIResponse(
            content="Image generation not supported by Anthropic",
            provider=self.name, model=self.model,
            success=False, error="Image gen not supported"
        )

    async def test_connection(self):
        try:
            await self.client.messages.create(
                model=self.model,
                max_tokens=5,
                messages=[{"role": "user", "content": "Hi"}]
            )
            self.status = AIStatus.HEALTHY
            return self.status
        except Exception as e:
            self.status = AIStatus.DOWN
            self.last_error = str(e)
            return self.status


class GroqProvider(AIProvider):
    """Groq provider"""
    
    async def initialize(self):
        import groq
        self.client = groq.AsyncGroq(api_key=self.api_key)
        
    async def chat(self, messages, system_prompt=None, temperature=0.3,
                  max_tokens=4096, stream=False, **kwargs):
        start = time.time()
        try:
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
                
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )
            
            latency = int((time.time() - start) * 1000)
            content = response.choices[0].message.content
            
            return AIResponse(
                content=content,
                provider=self.name,
                model=self.model,
                tokens_input=response.usage.prompt_tokens if response.usage else 0,
                tokens_output=response.usage.completion_tokens if response.usage else 0,
                latency_ms=latency,
                success=True
            )
            
        except Exception as e:
            return AIResponse(
                content="", provider=self.name, model=self.model,
                success=False, error=str(e)
            )
            
    async def vision(self, image_url: str, prompt: str, **kwargs):
        return AIResponse(
            content="Vision not supported by Groq",
            provider=self.name, model=self.model,
            success=False, error="Vision not supported"
        )

    async def generate_image(self, prompt: str, size: str = "1024x1024", **kwargs):
        return AIResponse(
            content="Image generation not supported by Groq",
            provider=self.name, model=self.model,
            success=False, error="Image gen not supported"
        )
        
    async def test_connection(self):
        try:
            await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )
            self.status = AIStatus.HEALTHY
            return self.status
        except Exception as e:
            self.status = AIStatus.DOWN
            self.last_error = str(e)
            return self.status


class CustomProvider(AIProvider):
    """Custom/OpenAI-compatible provider"""
    
    async def initialize(self):
        self.client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
    async def chat(self, messages, system_prompt=None, temperature=0.3,
                  max_tokens=4096, stream=False, **kwargs):
        start = time.time()
        try:
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
                
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )
            
            latency = int((time.time() - start) * 1000)
            content = response.choices[0].message.content
            
            return AIResponse(
                content=content,
                provider=self.name,
                model=self.model,
                latency_ms=latency,
                success=True
            )
            
        except Exception as e:
            return AIResponse(
                content="", provider=self.name, model=self.model,
                success=False, error=str(e)
            )
            
    async def vision(self, image_url: str, prompt: str, **kwargs):
        start = time.time()
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=4096
            )
            
            latency = int((time.time() - start) * 1000)
            content = response.choices[0].message.content
            
            return AIResponse(
                content=content,
                provider=self.name,
                model=self.model,
                latency_ms=latency,
                success=True
            )
            
        except Exception as e:
            return AIResponse(
                content="", provider=self.name, model=self.model,
                success=False, error=str(e)
            )
            
    async def test_connection(self):
        try:
            await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )
            self.status = AIStatus.HEALTHY
            return self.status
        except Exception as e:
            self.status = AIStatus.DOWN
            self.last_error = str(e)
            return self.status


class GoogleProvider(AIProvider):
    """Google Gemini provider"""

    async def initialize(self):
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        self.client = genai

    async def chat(self, messages, system_prompt=None, temperature=0.3,
                   max_tokens=4096, stream=False, **kwargs):
        start = time.time()
        try:
            model = self.client.GenerativeModel(
                model_name=self.model,
                system_instruction=system_prompt
            )
            # Convert OpenAI format to Gemini format
            gemini_messages = []
            for msg in messages:
                gemini_messages.append({
                    "role": "user" if msg["role"] == "user" else "model",
                    "parts": [msg["content"]]
                })

            response = await model.generate_content_async(
                gemini_messages,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
            )

            latency = int((time.time() - start) * 1000)
            content = response.text

            return AIResponse(
                content=content,
                provider=self.name,
                model=self.model,
                latency_ms=latency,
                success=True
            )
        except Exception as e:
            return AIResponse(
                content="", provider=self.name, model=self.model,
                success=False, error=str(e)
            )

    async def vision(self, image_url: str, prompt: str, **kwargs):
        start = time.time()
        try:
            import httpx
            async with httpx.AsyncClient() as session:
                resp = await session.get(image_url)
                img_data = resp.content

            model = self.client.GenerativeModel(model_name=self.model)
            response = await model.generate_content_async([prompt, img_data])

            latency = int((time.time() - start) * 1000)
            return AIResponse(
                content=response.text,
                provider=self.name,
                model=self.model,
                latency_ms=latency,
                success=True
            )
        except Exception as e:
            return AIResponse(
                content="", provider=self.name, model=self.model,
                success=False, error=str(e)
            )

    async def generate_image(self, prompt: str, size: str = "1024x1024", **kwargs):
        return AIResponse(
            content="Image generation not supported by Google Gemini",
            provider=self.name, model=self.model,
            success=False, error="Image gen not supported"
        )

    async def test_connection(self):
        try:
            model = self.client.GenerativeModel(model_name=self.model)
            await model.generate_content_async("Hi")
            self.status = AIStatus.HEALTHY
            return self.status
        except Exception as e:
            self.status = AIStatus.DOWN
            self.last_error = str(e)
            return self.status


class OpenAICompatibleProvider(AIProvider):
    """Generic OpenAI-compatible provider (DeepSeek, Mistral, xAI, Cohere, Ollama)"""

    async def initialize(self):
        self.client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    async def chat(self, messages, system_prompt=None, temperature=0.3,
                   max_tokens=4096, stream=False, **kwargs):
        start = time.time()
        try:
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )

            latency = int((time.time() - start) * 1000)
            content = response.choices[0].message.content

            return AIResponse(
                content=content,
                provider=self.name,
                model=self.model,
                latency_ms=latency,
                success=True
            )
        except Exception as e:
            return AIResponse(
                content="", provider=self.name, model=self.model,
                success=False, error=str(e)
            )

    async def vision(self, image_url: str, prompt: str, **kwargs):
        return AIResponse(
            content="Vision not supported by this provider",
            provider=self.name, model=self.model,
            success=False, error="Vision not supported"
        )

    async def generate_image(self, prompt: str, size: str = "1024x1024", **kwargs):
        return AIResponse(
            content="Image generation not supported by this provider",
            provider=self.name, model=self.model,
            success=False, error="Image gen not supported"
        )

    async def test_connection(self):
        try:
            await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )
            self.status = AIStatus.HEALTHY
            return self.status
        except Exception as e:
            self.status = AIStatus.DOWN
            self.last_error = str(e)
            return self.status


class AIManager:
    """Manages multiple AI providers with failover"""
    
    PROVIDER_MAP = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "groq": GroqProvider,
        "google": GoogleProvider,
        "deepseek": OpenAICompatibleProvider,
        "mistral": OpenAICompatibleProvider,
        "xai": OpenAICompatibleProvider,
        "cohere": OpenAICompatibleProvider,
        "ollama": OpenAICompatibleProvider,
        "custom": CustomProvider,
    }
    
    def __init__(self, cache_manager=None):
        self.providers: Dict[str, AIProvider] = {}
        self.primary_provider: Optional[str] = None
        self.fallback_providers: List[str] = []
        self.cache = cache_manager
        self._initialized = False
        self._db = None
        
    async def load_providers(self):
        """Load all configured providers from environment"""
        # OpenAI
        if os.getenv("OPENAI_API_KEY"):
            provider = OpenAIProvider(
                name="openai",
                api_key=os.getenv("OPENAI_API_KEY"),
                model=os.getenv("OPENAI_MODEL", "gpt-4o")
            )
            await provider.initialize()
            self.providers["openai"] = provider
            logger.info("✅ OpenAI provider loaded")
            
        # Anthropic
        if os.getenv("ANTHROPIC_API_KEY"):
            provider = AnthropicProvider(
                name="anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
            )
            await provider.initialize()
            self.providers["anthropic"] = provider
            logger.info("✅ Anthropic provider loaded")
            
        # Groq
        if os.getenv("GROQ_API_KEY"):
            provider = GroqProvider(
                name="groq",
                api_key=os.getenv("GROQ_API_KEY"),
                model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
            )
            await provider.initialize()
            self.providers["groq"] = provider
            logger.info("✅ Groq provider loaded")
            
        # Google Gemini
        if os.getenv("GOOGLE_API_KEY"):
            provider = GoogleProvider(
                name="google",
                api_key=os.getenv("GOOGLE_API_KEY"),
                model=os.getenv("GOOGLE_MODEL", "gemini-1.5-pro")
            )
            await provider.initialize()
            self.providers["google"] = provider
            logger.info("✅ Google provider loaded")

        # DeepSeek (OpenAI-compatible)
        if os.getenv("DEEPSEEK_API_KEY"):
            provider = OpenAICompatibleProvider(
                name="deepseek",
                api_key=os.getenv("DEEPSEEK_API_KEY"),
                model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                base_url="https://api.deepseek.com/v1"
            )
            await provider.initialize()
            self.providers["deepseek"] = provider
            logger.info("✅ DeepSeek provider loaded")

        # Mistral
        if os.getenv("MISTRAL_API_KEY"):
            provider = OpenAICompatibleProvider(
                name="mistral",
                api_key=os.getenv("MISTRAL_API_KEY"),
                model=os.getenv("MISTRAL_MODEL", "mistral-large-latest"),
                base_url="https://api.mistral.ai/v1"
            )
            await provider.initialize()
            self.providers["mistral"] = provider
            logger.info("✅ Mistral provider loaded")

        # xAI (Grok)
        if os.getenv("XAI_API_KEY"):
            provider = OpenAICompatibleProvider(
                name="xai",
                api_key=os.getenv("XAI_API_KEY"),
                model=os.getenv("XAI_MODEL", "grok-2"),
                base_url="https://api.x.ai/v1"
            )
            await provider.initialize()
            self.providers["xai"] = provider
            logger.info("✅ xAI (Grok) provider loaded")

        # Cohere
        if os.getenv("COHERE_API_KEY"):
            provider = OpenAICompatibleProvider(
                name="cohere",
                api_key=os.getenv("COHERE_API_KEY"),
                model=os.getenv("COHERE_MODEL", "command-r-plus"),
                base_url="https://api.cohere.com/v1"
            )
            await provider.initialize()
            self.providers["cohere"] = provider
            logger.info("✅ Cohere provider loaded")

        # Ollama (local)
        if os.getenv("OLLAMA_API_KEY") or os.getenv("OLLAMA_BASE_URL"):
            provider = OpenAICompatibleProvider(
                name="ollama",
                api_key="ollama",
                model=os.getenv("OLLAMA_MODEL", "llama3.2"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            )
            await provider.initialize()
            self.providers["ollama"] = provider
            logger.info("✅ Ollama provider loaded")

        # Azure OpenAI
        if os.getenv("AZURE_OPENAI_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"):
            provider = OpenAICompatibleProvider(
                name="azure",
                api_key=os.getenv("AZURE_OPENAI_KEY"),
                model=os.getenv("AZURE_OPENAI_MODEL", "gpt-4o"),
                base_url=os.getenv("AZURE_OPENAI_ENDPOINT")
            )
            await provider.initialize()
            self.providers["azure"] = provider
            logger.info("✅ Azure OpenAI provider loaded")

        # Custom
        if os.getenv("CUSTOM_API_KEY") and os.getenv("CUSTOM_BASE_URL"):
            provider = CustomProvider(
                name="custom",
                api_key=os.getenv("CUSTOM_API_KEY"),
                model=os.getenv("CUSTOM_MODEL", "custom-model"),
                base_url=os.getenv("CUSTOM_BASE_URL")
            )
            await provider.initialize()
            self.providers["custom"] = provider
            logger.info("✅ Custom provider loaded")
            
        # Set primary
        if self.providers:
            self.primary_provider = list(self.providers.keys())[0]
            self.fallback_providers = list(self.providers.keys())[1:]
            logger.info(f"🎯 Primary: {self.primary_provider}, Fallbacks: {self.fallback_providers}")
            
        self._initialized = True

    async def load_provider_from_settings(self, provider_name: str, api_key: str,
                                           model: Optional[str] = None,
                                           base_url: Optional[str] = None):
        """Dynamically load a provider from guild settings (not env vars)"""
        if provider_name in self.providers:
            return
        PROVIDER_CONFIGS = {
            "openai":     (OpenAIProvider,           "gpt-4o",                              None),
            "anthropic":  (AnthropicProvider,        "claude-3-5-sonnet-20241022",         None),
            "groq":       (GroqProvider,             "llama-3.3-70b-versatile",            None),
            "google":     (GoogleProvider,           "gemini-1.5-pro",                     None),
            "deepseek":   (OpenAICompatibleProvider, "deepseek-chat",                      "https://api.deepseek.com/v1"),
            "mistral":    (OpenAICompatibleProvider, "mistral-large-latest",               "https://api.mistral.ai/v1"),
            "xai":        (OpenAICompatibleProvider, "grok-2",                             "https://api.x.ai/v1"),
            "cohere":     (OpenAICompatibleProvider, "command-r-plus",                     "https://api.cohere.com/v1"),
            "ollama":     (OpenAICompatibleProvider, "llama3.2",                           "http://localhost:11434/v1"),
            "azure":      (OpenAICompatibleProvider, "gpt-4o",                             None),
            "custom":     (CustomProvider,           "custom-model",                       None),
        }
        cfg = PROVIDER_CONFIGS.get(provider_name)
        if not cfg:
            logger.warning(f"No config known for provider '{provider_name}'")
            return
        provider_cls, default_model, default_url = cfg
        try:
            provider = provider_cls(
                name=provider_name,
                api_key=api_key,
                model=model or default_model,
                base_url=base_url or default_url or ""
            )
            await provider.initialize()
            self.providers[provider_name] = provider
            if not self.primary_provider:
                self.primary_provider = provider_name
            logger.info(f"✅ Provider '{provider_name}' loaded from guild settings")
        except Exception as e:
            logger.error(f"Failed to load provider '{provider_name}' from settings: {e}")

    async def chat(self, messages: List[Dict[str, str]], 
                   provider: Optional[str] = None,
                   system_prompt: Optional[str] = None,
                   temperature: float = 0.3,
                   max_tokens: int = 4096,
                   stream: bool = False,
                   use_cache: bool = True,
                   **kwargs) -> AIResponse:
        """Send chat request with failover"""
        
        # Check cache
        if use_cache and self.cache:
            import hashlib
            cache_key = hashlib.md5(
                str(messages).encode()
            ).hexdigest()
            cached = await self.cache.get_ai_response(
                cache_key, provider or self.primary_provider, "any"
            )
            if cached:
                logger.debug("🎯 Cache hit")
                return AIResponse(**cached)
        
        # Try providers in order
        providers_to_try = [provider] if provider else []
        if not providers_to_try:
            providers_to_try = [self.primary_provider] + self.fallback_providers
            
        for prov_name in providers_to_try:
            if prov_name not in self.providers:
                continue
                
            prov = self.providers[prov_name]
            response = await prov.chat(
                messages=messages,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )
            
            if response.success:
                prov.total_calls += 1
                # Cache successful response
                if use_cache and self.cache:
                    await self.cache.set_ai_response(
                        cache_key, prov_name, prov.model,
                        {
                            "content": response.content,
                            "provider": response.provider,
                            "model": response.model,
                            "success": True
                        }
                    )
                return response
            else:
                prov.failed_calls += 1
                logger.warning(f"⚠️ {prov_name} failed: {response.error}")
                
        # All providers failed
        return AIResponse(
            content="All AI providers are currently unavailable. Please try again later.",
            provider="none",
            model="none",
            success=False,
            error="All providers failed"
        )
        
    async def vision(self, image_url: str, prompt: str,
                    provider: Optional[str] = None,
                    **kwargs) -> AIResponse:
        """Analyze image with AI vision"""
        providers_to_try = [provider] if provider else []
        if not providers_to_try:
            providers_to_try = [self.primary_provider] + self.fallback_providers
            
        for prov_name in providers_to_try:
            if prov_name not in self.providers:
                continue
                
            prov = self.providers[prov_name]
            response = await prov.vision(image_url, prompt)
            
            if response.success:
                return response
            else:
                logger.warning(f"⚠️ {prov_name} vision failed: {response.error}")
                
        return AIResponse(
            content="Vision analysis unavailable",
            provider="none",
            model="none",
            success=False,
            error="All vision providers failed"
        )
        
    async def test_all(self) -> Dict[str, Dict]:
        """Test all providers"""
        results = {}
        for name, provider in self.providers.items():
            status = await provider.test_connection()
            results[name] = {
                "status": status.value,
                "model": provider.model,
                "total_calls": provider.total_calls,
                "failed_calls": provider.failed_calls,
                "last_error": provider.last_error
            }
        return results
        
    @property
    def router(self):
        """Get AI router (lazy-loaded)"""
        if not hasattr(self, '_router') or self._router is None:
            from ..ai.router import AIRouter
            self._router = AIRouter(self)
            if self._db:
                self._router.db = self._db
        return self._router

    def set_router_db(self, db):
        """Set database reference on router"""
        self._db = db
        if hasattr(self, '_router') and self._router:
            self._router.db = db

    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        return {
            name: {
                "status": prov.status.value,
                "model": prov.model,
                "total_calls": prov.total_calls,
                "failed_calls": prov.failed_calls,
                "last_error": prov.last_error
            }
            for name, prov in self.providers.items()
        }
