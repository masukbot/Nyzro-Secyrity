"""
Rinox Sentinel - Task Scheduler
Schedule and manage periodic tasks
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger("Rinox.Automation.Scheduler")


@dataclass
class ScheduledTask:
    name: str
    callback: Callable
    interval_hours: int
    guild_id: int
    last_run: Optional[datetime] = None
    enabled: bool = True


class Scheduler:
    """Manage scheduled tasks"""

    def __init__(self, bot=None):
        self.bot = bot
        self.tasks: Dict[str, ScheduledTask] = {}
        self._loop_task: Optional[asyncio.Task] = None

    def add_task(self, name: str, callback: Callable, interval_hours: int,
                 guild_id: int = 0):
        self.tasks[name] = ScheduledTask(
            name=name, callback=callback,
            interval_hours=interval_hours, guild_id=guild_id
        )
        logger.info(f"📅 Scheduled task added: {name} (every {interval_hours}h)")

    def remove_task(self, name: str):
        self.tasks.pop(name, None)
        logger.info(f"📅 Scheduled task removed: {name}")

    async def start(self):
        self._loop_task = asyncio.create_task(self._loop())

    async def stop(self):
        if self._loop_task:
            self._loop_task.cancel()
            self._loop_task = None

    async def _loop(self):
        while True:
            now = datetime.utcnow()
            for name, task in list(self.tasks.items()):
                if not task.enabled:
                    continue
                if task.last_run is None or \
                   (now - task.last_run) >= timedelta(hours=task.interval_hours):
                    try:
                        if asyncio.iscoroutinefunction(task.callback):
                            await task.callback(task.guild_id)
                        else:
                            task.callback(task.guild_id)
                        task.last_run = now
                        logger.debug(f"📅 Executed scheduled task: {name}")
                    except Exception as e:
                        logger.error(f"📅 Task {name} failed: {e}")
            await asyncio.sleep(60)