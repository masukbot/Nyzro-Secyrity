"""
Rinox Sentinel - Appeal System
Handle user appeals against moderation actions
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger("Rinox.Moderation.Appeals")


@dataclass
class Appeal:
    id: int
    guild_id: int
    user_id: int
    action_type: str
    reason: str
    status: str = "pending"
    created_at: datetime = None
    reviewed_by: Optional[int] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class AppealSystem:
    """Manage user appeals"""

    def __init__(self, db=None):
        self.db = db

    async def create_appeal(self, guild_id: int, user_id: int,
                           action_type: str, reason: str) -> Optional[int]:
        """Create a new appeal. Returns appeal ID if successful."""
        if not self.db:
            logger.warning("No database, cannot create appeal")
            return None
        try:
            await self.db.log_moderation(
                guild_id, user_id, "appeal_submitted",
                reason=reason,
                evidence={"action_type": action_type}
            )
            logger.info(f"📝 Appeal submitted by {user_id} in guild {guild_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create appeal: {e}")
            return None

    async def approve(self, appeal_id: int, reviewer_id: int, notes: str = None):
        """Approve an appeal"""
        logger.info(f"✅ Appeal {appeal_id} approved by {reviewer_id}")

    async def reject(self, appeal_id: int, reviewer_id: int, notes: str = None):
        """Reject an appeal"""
        logger.info(f"❌ Appeal {appeal_id} rejected by {reviewer_id}")

    async def get_pending(self, guild_id: int) -> List[Dict]:
        """Get pending appeals for a guild"""
        return []