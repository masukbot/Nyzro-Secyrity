"""
Rinox Sentinel - Event Listeners
Message scanning, member join, channel AI modes, auto-clean
"""

import discord
from discord.ext import commands
from datetime import timedelta, datetime
from typing import Dict
import time

from ..ui.embeds import RinoxEmbed


class Events(commands.Cog):
    """Event listeners for security and AI features"""

    def __init__(self, bot):
        self.bot = bot
        self._settings_cache = {}
        self._cache_ttl = 30
        self._cooldowns: Dict[str, float] = {}
        self._join_tracker: Dict[int, list] = {}  # guild_id -> [timestamp, ...]

    async def _get_settings(self, guild_id: int):
        """Cached guild settings lookup"""
        now = datetime.utcnow()
        cached = self._settings_cache.get(guild_id)
        if cached and (now - cached["time"]).seconds < self._cache_ttl:
            return cached["data"]
        data = await self.bot.db.get_guild_settings(guild_id)
        self._settings_cache[guild_id] = {"data": data, "time": now}
        return data

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return

        # === STAGE 1: Channel AI Mode (independent of guild settings) ===
        await self._process_channel_ai_mode(message)

        # === STAGE 2: Security Scanning (needs guild settings) ===
        settings = await self._get_settings(message.guild.id)
        if not settings:
            return
        await self._process_security_scan(message, settings)

    async def _check_cooldown(self, guild_id: int, channel_id: int, user_id: int, cooldown: int) -> bool:
        """Returns True if user is allowed to send"""
        key = f"{guild_id}_{channel_id}_{user_id}"
        now = time.time()
        last = self._cooldowns.get(key, 0)
        if now - last < cooldown:
            return False
        self._cooldowns[key] = now
        return True

    async def _process_channel_ai_mode(self, message: discord.Message):
        """Auto-process message based on channel AI mode"""
        try:
            mode = await self.bot.db.get_channel_ai_mode(
                message.guild.id, message.channel.id
            )
        except Exception:
            return

        if not mode:
            return

        feature = mode.get("feature")
        config = mode.get("config", {}) or {}
        if isinstance(config, str):
            import json
            config = json.loads(config) if config else {}
        content = message.content
        custom_instructions = config.get("custom_instructions")
        cooldown_sec = config.get("cooldown", 0)

        # Cooldown check
        if cooldown_sec > 0:
            allowed = await self._check_cooldown(
                message.guild.id, message.channel.id, message.author.id, cooldown_sec
            )
            if not allowed:
                return

        # Auto-language: inject instruction into system prompt
        target_lang = config.get("target_lang")
        if target_lang == "auto":
            auto_lang_instruction = (
                "Detect the user's language from their message and respond in the SAME language. "
                "If they write in Bengali, reply in Bengali. If they write in English, reply in English."
            )
            custom_instructions = (
                f"{auto_lang_instruction}\n\n{custom_instructions}"
                if custom_instructions else auto_lang_instruction
            )

        async with message.channel.typing():
            try:
                if feature == "chat":
                    if not content:
                        return
                    response = await self.bot.ai.router.route_chat(
                        message.guild.id,
                        messages=[{"role": "user", "content": content}],
                        system_prompt=custom_instructions,
                    )
                    if response.success:
                        await message.reply(response.content[:2000])
                    else:
                        await message.reply(f"⚠️ {response.error[:200]}")
                        self.bot.logger.warning(f"Chat AI error: {response.error}")

                elif feature == "translate":
                    if not content:
                        return
                    target = target_lang if target_lang and target_lang != "auto" else "english"
                    response = await self.bot.ai.router.route_translate(
                        message.guild.id, content, target_lang=target,
                        system_prompt=custom_instructions,
                    )
                    if response.success:
                        await message.reply(response.content[:2000])
                    else:
                        await message.reply(f"⚠️ {response.error[:200]}")

                elif feature == "summarize":
                    if not content:
                        return
                    recent = []
                    async for msg in message.channel.history(limit=20, before=message):
                        if not msg.author.bot:
                            recent.append(f"{msg.author.name}: {msg.content}")
                    recent_text = "\n".join(reversed(recent)) + f"\n\n[New] {message.author.name}: {content}"
                    response = await self.bot.ai.router.route_summarize(
                        message.guild.id, recent_text,
                        system_prompt=custom_instructions,
                    )
                    if response.success:
                        await message.reply(f"📝 **Summary:**\n{response.content[:2000]}")
                    else:
                        await message.reply(f"⚠️ {response.error[:200]}")

                elif feature == "vision":
                    if not message.attachments:
                        await message.reply("🖼️ Please attach an image for vision analysis.")
                        return
                    img_url = message.attachments[0].url
                    prompt = custom_instructions or "Describe this image in detail."
                    response = await self.bot.ai.router.route_vision(
                        message.guild.id, img_url, prompt
                    )
                    if response.success:
                        await message.reply(response.content[:2000])
                    else:
                        err = response.error or "Vision analysis failed"
                        if "image input" in err.lower() or "image" in err.lower():
                            await message.reply("🖼️ This AI model doesn't support image analysis. Try a different provider (e.g., OpenAI, Google Gemini) or use a vision-capable model.")
                        else:
                            await message.reply(f"⚠️ {err[:200]}")
                        self.bot.logger.warning(f"Vision error: {err}")

                elif feature == "image_gen":
                    if not content:
                        return
                    response = await self.bot.ai.router.route_image_gen(
                        message.guild.id, content,
                        system_prompt=custom_instructions,
                    )
                    if response.success and response.content:
                        embed = discord.Embed(
                            title="🎨 Generated Image",
                            description=f"**Prompt:** {content[:500]}",
                            color=0x9B59B6
                        )
                        embed.set_image(url=response.content)
                        await message.reply(embed=embed)
                    else:
                        await message.reply(f"⚠️ {response.error[:200] if hasattr(response, 'error') and response.error else 'Image generation failed'}")

                elif feature == "moderation":
                    if not content:
                        return
                    response = await self.bot.ai.router.route_moderation(
                        message.guild.id, content,
                        system_prompt=custom_instructions,
                    )
                    if response.success:
                        if response.content and "❌" not in response.content:
                            await message.reply(f"✅ Content looks safe.")
                        else:
                            await message.reply(response.content[:2000])
                    else:
                        await message.reply(f"⚠️ {response.error[:200]}")

            except Exception as e:
                self.bot.logger.error(f"Channel AI mode error: {e}")
                try:
                    await message.reply(f"❌ AI processing error: {str(e)[:100]}")
                except Exception:
                    pass

    async def _process_security_scan(self, message: discord.Message, settings: dict):
        """Scan message for security threats"""
        features = settings.get("enabled_features", [])
        if "message_scan" not in features:
            return

        # Check individual security module toggles
        sec_config = settings.get("security_config") or {}
        if isinstance(sec_config, str):
            import json
            sec_config = json.loads(sec_config) if sec_config else {}

        # Respect toggle-module settings: if anti_spam is explicitly disabled, skip
        anti_spam_enabled = sec_config.get("anti_spam", True)
        anti_link_enabled = sec_config.get("anti_link", True)
        if not anti_spam_enabled and not anti_link_enabled:
            # If both are off, only run AI-based checks (if message_scan is on)
            pass  # Still scan — individual modules checked inside scan_message

        result = await self.bot.security.scan_message(message, settings)

        if result.is_threat:
            await self.bot.db.log_security_event(
                message.guild.id,
                "message_scan",
                user_id=message.author.id,
                channel_id=message.channel.id,
                message_id=message.id,
                content=message.content[:500],
                threat_level=result.threat_level,
                risk_score=result.risk_score,
                ai_confidence=result.confidence,
                action_taken=",".join([a.value for a in result.actions]),
                evidence=result.evidence
            )

            for action in result.actions:
                if action.value == "delete":
                    try:
                        await message.delete()
                    except:
                        pass
                elif action.value == "warn":
                    await self.bot.db.add_warning(
                        message.guild.id,
                        message.author.id,
                        f"Auto-detected threat (Risk: {result.risk_score})"
                    )
                elif action.value == "timeout":
                    try:
                        await message.author.timeout(
                            discord.utils.utcnow() + timedelta(minutes=10),
                            reason=f"Rinox Security: Risk {result.risk_score}"
                        )
                    except:
                        pass

            log_channel_id = settings.get("log_channel_id")
            if log_channel_id:
                log_channel = message.guild.get_channel(log_channel_id)
                if log_channel:
                    embed = RinoxEmbed.scan_result(result)
                    embed.add_field(
                        name="👤 Author",
                        value=f"{message.author.mention} (`{message.author.id}`)",
                        inline=False
                    )
                    embed.add_field(
                        name="🔗 Message",
                        value=f"[Jump to message]({message.jump_url})",
                        inline=False
                    )
                    await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Scan new members — anti-raid + user scan"""
        settings = await self.bot.db.get_guild_settings(member.guild.id)
        if not settings:
            return

        sec_config = settings.get("security_config") or {}
        if isinstance(sec_config, str):
            import json
            sec_config = json.loads(sec_config) if sec_config else {}

        # === Anti-Raid: track joins in 60s window ===
        anti_raid = sec_config.get("anti_raid", True)
        if anti_raid:
            now = time.time()
            guild_tracker = self._join_tracker.setdefault(member.guild.id, [])
            guild_tracker.append(now)
            # Keep only last 60 seconds
            self._join_tracker[member.guild.id] = [t for t in guild_tracker if now - t < 60]
            join_count = len(self._join_tracker[member.guild.id])

            raid_threshold = 5  # more than 5 joins in 60s = raid
            if join_count > raid_threshold:
                try:
                    await member.kick(reason=f"Rinox Anti-Raid: {join_count} joins in 60s")
                    await self.bot.db.log_security_event(
                        member.guild.id, "raid_detected",
                        user_id=member.id,
                        threat_level=3,
                        risk_score=80,
                        action_taken="kick",
                        evidence=f"Anti-raid: {join_count} joins in 60 seconds"
                    )
                except:
                    pass
                return  # Don't proceed with user scan if kicked

        # === User Scan ===
        result = await self.bot.security.scan_user(member, settings)

        if result.risk_score > 50:
            await self.bot.db.log_security_event(
                member.guild.id,
                "user_join",
                user_id=member.id,
                threat_level=result.threat_level,
                risk_score=result.risk_score,
                action_taken="log",
                evidence=result.evidence
            )

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Detect suspicious account changes — alt detection"""
        if before.guild is None or before.guild.id is None:
            return
        before_avatar = before.avatar if hasattr(before, 'avatar') else None
        after_avatar = after.avatar if hasattr(after, 'avatar') else None
        if before_avatar == after_avatar and before.name == after.name:
            return

        settings = await self._get_settings(after.guild.id)
        if not settings:
            return

        sec_config = settings.get("security_config") or {}
        if isinstance(sec_config, str):
            import json
            try: sec_config = json.loads(sec_config) if sec_config else {}
            except: sec_config = {}

        if not sec_config.get("anti_raid", True):
            return

        # Check account age
        age_days = (discord.utils.utcnow() - after.created_at).days
        if age_days < 7:
            await self.bot.db.log_security_event(
                after.guild.id, "alt_account",
                user_id=after.id,
                threat_level=2,
                risk_score=60,
                action_taken="log",
                evidence=f"Account age: {age_days} days (threshold: 7)"
            )

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """Anti-nuke: auto-delete channels created by non-admin users"""
        settings = await self._get_settings(channel.guild.id)
        if not settings:
            return

        sec_config = settings.get("security_config") or {}
        if isinstance(sec_config, str):
            import json
            try: sec_config = json.loads(sec_config) if sec_config else {}
            except: sec_config = {}

        if not sec_config.get("anti_nuke", True):
            return

        # Fetch audit log to find who created the channel
        try:
            async for entry in channel.guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_create):
                if entry.target.id == channel.id:
                    creator = entry.user
                    if creator and not creator.guild_permissions.administrator:
                        await channel.delete(reason=f"Rinox Anti-Nuke: created by {creator} (not admin)")
                        await self.bot.db.log_security_event(
                            channel.guild.id, "anti_nuke",
                            user_id=creator.id,
                            threat_level=3,
                            risk_score=80,
                            action_taken="channel_delete",
                            evidence=f"Deleted channel #{channel.name} created by non-admin"
                        )
                    break
        except:
            pass

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Log deleted messages"""
        if message.author.bot:
            return
        if not message.guild:
            return
        settings = await self._get_settings(message.guild.id)
        if not settings or not settings.get("log_channel_id"):
            return

        log_channel = message.guild.get_channel(settings["log_channel_id"])
        if not log_channel:
            return

        embed = discord.Embed(
            title="🗑️ Message Deleted",
            color=0xED4245,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Author", value=message.author.mention, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        if message.content:
            embed.add_field(name="Content", value=message.content[:1000], inline=False)
        if message.attachments:
            embed.add_field(
                name="Attachments",
                value="\n".join([a.url for a in message.attachments])[:1000],
                inline=False
            )
        embed.set_footer(text=f"User ID: {message.author.id}")
        await log_channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Events(bot))