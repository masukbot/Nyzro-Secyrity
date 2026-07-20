"""
Rinox Sentinel - AI Features Commands
AI Chat, Translate, Summarize, Imagine, Vision
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from ..ui.embeds import RinoxEmbed


class AIFeaturesCommands(commands.Cog):
    """AI-powered feature commands with auto-routing"""

    def __init__(self, bot):
        self.bot = bot

    # ========================
    # AI CHAT
    # ========================
    @app_commands.command(name="chat", description="💬 Chat with AI")
    @app_commands.describe(
        message="Your message for the AI",
        system="Optional system prompt to set AI behavior"
    )
    async def chat(self, interaction: discord.Interaction, message: str, system: Optional[str] = None):
        """Chat with AI through the routed provider chain"""
        await interaction.response.defer()

        async with interaction.channel.typing():
            response = await self.bot.ai.router.route_chat(
                interaction.guild_id,
                messages=[{"role": "user", "content": message}],
                system_prompt=system or "You are a helpful assistant."
            )

            if response.success:
                embed = RinoxEmbed.create(
                    title="💬 AI Response",
                    description=response.content[:2000],
                    color=RinoxEmbed.INFO
                )
                embed.set_footer(text=f"via {response.provider}/{response.model} • {response.latency_ms}ms")
                await interaction.followup.send(embed=embed)
            else:
                embed = RinoxEmbed.error(
                    f"AI request failed: {response.error[:200]}",
                    "❌ Chat Error"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

    # ========================
    # TRANSLATE
    # ========================
    @app_commands.command(name="translate", description="🌍 Translate text to another language")
    @app_commands.describe(
        text="Text to translate",
        target_lang="Target language (e.g., english, bengali, spanish, french)",
    )
    async def translate(self, interaction: discord.Interaction,
                        text: str,
                        target_lang: str = "english"):
        """Translate text using AI"""
        await interaction.response.defer()

        async with interaction.channel.typing():
            response = await self.bot.ai.router.route_translate(
                interaction.guild_id,
                text,
                target_lang=target_lang
            )

            if response.success:
                embed = RinoxEmbed.create(
                    title=f"🌍 Translation → {target_lang.title()}",
                    color=RinoxEmbed.SUCCESS
                )
                embed.add_field(name="📝 Original", value=text[:500], inline=False)
                embed.add_field(name="✅ Translated", value=response.content[:2000], inline=False)
                embed.set_footer(text=f"via {response.provider} • {response.latency_ms}ms")
                await interaction.followup.send(embed=embed)
            else:
                embed = RinoxEmbed.error(f"Translation failed: {response.error[:200]}", "❌ Error")
                await interaction.followup.send(embed=embed, ephemeral=True)

    # ========================
    # SUMMARIZE
    # ========================
    @app_commands.command(name="summarize", description="📝 Summarize recent messages in a channel")
    @app_commands.describe(
        channel="Channel to summarize (default: current)",
        count="Number of recent messages to summarize (max 100)",
    )
    async def summarize(self, interaction: discord.Interaction,
                        channel: Optional[discord.TextChannel] = None,
                        count: app_commands.Range[int, 5, 100] = 30):
        """Summarize recent channel messages"""
        await interaction.response.defer()

        target = channel or interaction.channel
        async with target.typing():
            # Collect messages
            messages_text = []
            async for msg in target.history(limit=count):
                timestamp = msg.created_at.strftime("%H:%M")
                if not msg.author.bot:
                    messages_text.append(f"[{timestamp}] {msg.author.name}: {msg.content}")

            if not messages_text:
                embed = RinoxEmbed.info("No messages to summarize.", "📝 Summary")
                await interaction.followup.send(embed=embed)
                return

            conversation = "\n".join(reversed(messages_text))

            response = await self.bot.ai.router.route_summarize(
                interaction.guild_id,
                conversation
            )

            if response.success:
                embed = RinoxEmbed.create(
                    title=f"📝 Summary of #{target.name}",
                    description=response.content[:2000],
                    color=RinoxEmbed.INFO
                )
                embed.add_field(
                    name="📊 Stats",
                    value=f"Messages analyzed: `{len(messages_text)}`",
                    inline=False
                )
                embed.set_footer(text=f"via {response.provider}/{response.model} • {response.latency_ms}ms")
                await interaction.followup.send(embed=embed)
            else:
                embed = RinoxEmbed.error(f"Summarization failed: {response.error[:200]}", "❌ Error")
                await interaction.followup.send(embed=embed, ephemeral=True)

    # ========================
    # IMAGINE (AI Image Generation)
    # ========================
    @app_commands.command(name="imagine", description="🎨 Generate an image from text description")
    @app_commands.describe(
        prompt="Description of the image you want to generate",
        size="Image size",
    )
    @app_commands.choices(size=[
        app_commands.Choice(name="Square (1024x1024)", value="1024x1024"),
        app_commands.Choice(name="Wide (1792x1024)", value="1792x1024"),
        app_commands.Choice(name="Tall (1024x1792)", value="1024x1792"),
    ])
    async def imagine(self, interaction: discord.Interaction,
                      prompt: str,
                      size: app_commands.Choice[str] = "1024x1024"):
        """Generate an AI image"""
        await interaction.response.defer()

        async with interaction.channel.typing():
            response = await self.bot.ai.router.route_image_gen(
                interaction.guild_id,
                prompt,
                size=size.value if isinstance(size, app_commands.Choice) else size
            )

            if response.success and response.content:
                embed = RinoxEmbed.create(
                    title="🎨 Generated Image",
                    description=f"**Prompt:** {prompt[:500]}",
                    color=RinoxEmbed.PREMIUM
                )
                embed.set_image(url=response.content)
                embed.set_footer(text=f"via {response.provider}/{response.model} • {response.latency_ms}ms")
                await interaction.followup.send(embed=embed)
            else:
                embed = RinoxEmbed.error(
                    f"Image generation failed: {response.error[:200]}",
                    "❌ Generation Error"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

    # ========================
    # AI CUSTOM
    # ========================
    @app_commands.command(name="ai-prompt", description="Send a custom AI prompt")
    @app_commands.describe(
        prompt="Your prompt or question",
        system="Optional system prompt",
        temperature="Creativity level (0.0=precise, 1.0=creative)",
    )
    async def ai_custom(self, interaction: discord.Interaction,
                       prompt: str,
                       system: Optional[str] = None,
                       temperature: app_commands.Range[float, 0.0, 2.0] = 0.7):
        """Custom AI prompt with full control"""
        await interaction.response.defer()

        async with interaction.channel.typing():
            response = await self.bot.ai.router.route_chat(
                interaction.guild_id,
                messages=[{"role": "user", "content": prompt}],
                system_prompt=system or "You are a helpful AI assistant.",
                temperature=temperature
            )

            if response.success:
                embed = RinoxEmbed.create(
                    title="🤖 AI Response",
                    description=response.content[:2000],
                    color=RinoxEmbed.INFO
                )
                embed.set_footer(text=f"via {response.provider}/{response.model} • temp={temperature} • {response.latency_ms}ms")
                await interaction.followup.send(embed=embed)
            else:
                embed = RinoxEmbed.error(f"AI request failed: {response.error[:200]}", "❌ Error")
                await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AIFeaturesCommands(bot))