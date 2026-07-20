"""
Rinox Sentinel - Auto Clean Task
Periodically deletes messages past their TTL in configured channels
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict

import discord

logger = logging.getLogger("Rinox.AutoClean")


class AutoCleanTask:
    """Background task that deletes expired messages from auto-clean channels"""

    def __init__(self, bot):
        self.bot = bot

    async def run(self):
        """Run one clean cycle — called every 60 seconds from bot loop"""
        try:
            configs = await self.bot.db.get_all_auto_clean()
            if not configs:
                return

            for cfg in configs:
                await self._clean_channel(cfg)
        except Exception as e:
            logger.error(f"Auto-clean cycle error: {e}")

    async def _clean_channel(self, cfg: Dict):
        """Delete expired messages in a single channel"""
        guild_id = cfg.get("guild_id")
        channel_id = cfg.get("channel_id")
        delay = cfg.get("delay_seconds", 300)
        filter_type = cfg.get("filter_type", "all")

        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        cutoff = discord.utils.utcnow() - timedelta(seconds=delay)

        # Determine bulk delete limit: max 100, and can't delete >14 day old
        min_age_cutoff = discord.utils.utcnow() - timedelta(days=13, hours=23)
        bulk_cutoff = max(cutoff, min_age_cutoff)

        try:
            to_delete = []
            async for msg in channel.history(limit=100, before=cutoff, oldest_first=False):
                if msg.created_at > bulk_cutoff:
                    to_delete.append(msg)
                elif msg.created_at <= bulk_cutoff:
                    # Single delete for older messages
                    try:
                        await msg.delete()
                    except discord.NotFound:
                        pass
                    except discord.Forbidden:
                        logger.warning(f"No permission to delete message in #{channel.name}")
                        break

                if len(to_delete) >= 100:
                    break

            if to_delete:
                if len(to_delete) == 1:
                    await to_delete[0].delete()
                else:
                    await channel.delete_messages(to_delete)
                logger.info(f"🧹 Auto-clean: deleted {len(to_delete)} msgs in #{channel.name} (delay={delay}s, filter={filter_type})")

        except discord.Forbidden:
            logger.warning(f"🧹 No permission to read/delete in #{channel.name}")
        except discord.HTTPException as e:
            logger.error(f"🧹 HTTP error cleaning #{channel.name}: {e}")
        except Exception as e:
            logger.error(f"🧹 Error cleaning #{channel.name}: {e}")