"""
Rinox Sentinel - Moderation Actions
Queue and execute moderation actions
"""

import logging
import asyncio
import discord
import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("Rinox.Moderation.Actions")


class ActionType(Enum):
    WARN = "warn"
    MUTE = "mute"
    TIMEOUT = "timeout"
    KICK = "kick"
    BAN = "ban"
    DELETE = "delete"
    LOCK_CHANNEL = "lock_channel"
    DM_USER = "dm_user"
    NOTIFY_STAFF = "notify_staff"


@dataclass
class ModAction:
    """A single moderation action to execute"""
    action_type: ActionType
    guild_id: int
    user_id: int
    moderator_id: Optional[int] = None
    reason: str = ""
    duration: Optional[int] = None
    metadata: Dict[str, Any] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


class ActionQueue:
    """Queue and execute moderation actions sequentially"""

    def __init__(self, bot=None):
        self.bot = bot
        self.queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None

    async def enqueue(self, action: ModAction):
        await self.queue.put(action)
        logger.info(f"📋 Action queued: {action.action_type.value} for user {action.user_id}")

    async def start(self):
        self._worker_task = asyncio.create_task(self._worker())

    async def stop(self):
        if self._worker_task:
            self._worker_task.cancel()
            self._worker_task = None

    async def _worker(self):
        while True:
            action: ModAction = await self.queue.get()
            try:
                await self._execute(action)
            except Exception as e:
                logger.error(f"❌ Failed to execute action {action.action_type}: {e}")
            self.queue.task_done()

    async def _execute(self, action: ModAction):
        """Execute a single moderation action"""
        if not self.bot:
            logger.warning("No bot reference, action not executed")
            return

        guild = self.bot.get_guild(action.guild_id)
        if not guild:
            logger.warning(f"Guild {action.guild_id} not found")
            return

        member = guild.get_member(action.user_id)

        if action.action_type == ActionType.WARN and self.bot.db:
            await self.bot.db.add_warning(
                action.guild_id, action.user_id,
                action.reason, action.moderator_id
            )
            logger.info(f"⚠️ Warning issued to {action.user_id}")

        elif action.action_type == ActionType.KICK and member:
            await member.kick(reason=action.reason)
            logger.info(f"👢 Kicked {action.user_id}")

        elif action.action_type == ActionType.BAN and member:
            await member.ban(reason=action.reason)
            logger.info(f"🔨 Banned {action.user_id}")

        elif action.action_type == ActionType.MUTE and member:
            until = discord.utils.utcnow() + datetime.timedelta(seconds=action.duration or 3600)
            await member.timeout(until, reason=action.reason)
            logger.info(f"🔇 Muted {action.user_id}")

        elif action.action_type == ActionType.DELETE:
            channel_id = action.metadata.get("channel_id")
            message_id = action.metadata.get("message_id")
            if channel_id and message_id:
                channel = guild.get_channel(channel_id)
                if channel:
                    try:
                        msg = await channel.fetch_message(message_id)
                        await msg.delete()
                        logger.info(f"🗑️ Deleted message {message_id}")
                    except:
                        pass

        logger.info(f"✅ Action executed: {action.action_type.value}")