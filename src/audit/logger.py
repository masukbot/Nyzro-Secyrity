"""
Rinox Sentinel - Audit Logger
Structured logging for security events, moderation actions, and system events
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger("Rinox.Audit")


class AuditLogger:
    """Structured audit trail logger"""

    def __init__(self, db=None):
        self.db = db

    async def log(self, guild_id: int, event_type: str, **kwargs):
        """Log an audit event"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "guild_id": guild_id,
            "event_type": event_type,
            **kwargs
        }

        # Log to file
        logger.info(json.dumps(entry, default=str))

        # Log to database if available
        if self.db and hasattr(self.db, 'log_security_event'):
            try:
                await self.db.log_security_event(
                    guild_id, event_type,
                    **kwargs
                )
            except Exception as e:
                logger.warning(f"Failed to log to database: {e}")

    async def moderation(self, guild_id: int, action: str, user_id: int,
                        moderator_id: int, reason: str = None, **kwargs):
        """Log a moderation action"""
        await self.log(
            guild_id, f"moderation:{action}",
            user_id=user_id,
            moderator_id=moderator_id,
            reason=reason,
            **kwargs
        )

    async def security(self, guild_id: int, event: str, **kwargs):
        """Log a security event"""
        await self.log(guild_id, f"security:{event}", **kwargs)

    async def config_change(self, guild_id: int, changed_by: int,
                          changes: Dict[str, Any]):
        """Log a configuration change"""
        await self.log(
            guild_id, "config:update",
            changed_by=changed_by,
            changes=changes
        )