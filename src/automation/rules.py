"""
Rinox Sentinel - Automation Rule Engine
Define and evaluate conditional rules that trigger actions
"""

import logging
import asyncio
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("Rinox.Automation.Rules")


@dataclass
class Rule:
    name: str
    condition: Callable[..., bool]
    action: Callable[..., Any]
    priority: int = 0
    enabled: bool = True
    cooldown_seconds: int = 0
    description: str = ""

    def __post_init__(self):
        self._last_triggered: float = 0


class RuleEngine:
    """Evaluate and execute automation rules"""

    def __init__(self):
        self.rules: List[Rule] = []

    def add_rule(self, rule: Rule):
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"⚙️ Rule added: {rule.name}")

    def remove_rule(self, name: str):
        self.rules = [r for r in self.rules if r.name != name]

    async def evaluate(self, context: Dict[str, Any]) -> List[Rule]:
        """Evaluate all rules against context and return matched rules"""
        import time
        now = time.time()
        matched = []

        for rule in self.rules:
            if not rule.enabled:
                continue
            if rule.cooldown_seconds > 0 and \
               (now - rule._last_triggered) < rule.cooldown_seconds:
                continue

            try:
                result = rule.condition(context)
                if asyncio.iscoroutine(result):
                    result = await result
                if result:
                    matched.append(rule)
                    rule._last_triggered = now
            except Exception as e:
                logger.error(f"⚙️ Rule {rule.name} evaluation error: {e}")

        return matched

    async def execute(self, rules: List[Rule], context: Dict[str, Any]):
        """Execute a list of matched rules"""
        for rule in rules:
            try:
                result = rule.action(context)
                if asyncio.iscoroutine(result):
                    await result
                logger.info(f"⚙️ Rule executed: {rule.name}")
            except Exception as e:
                logger.error(f"⚙️ Rule {rule.name} execution error: {e}")

    def get_rules(self) -> List[Dict]:
        return [
            {
                "name": r.name,
                "enabled": r.enabled,
                "priority": r.priority,
                "description": r.description,
            }
            for r in self.rules
        ]


