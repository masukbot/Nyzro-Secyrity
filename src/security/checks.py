"""
Rinox Sentinel - Security Checks
Extensible security check system
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger("Rinox.Security.Checks")


@dataclass
class CheckResult:
    check_name: str
    passed: bool
    risk_score: int
    details: str = ""
    confidence: float = 1.0


class SecurityCheck:
    """Base class for a security check"""

    def __init__(self, name: str):
        self.name = name

    async def run(self, context: Dict[str, Any]) -> CheckResult:
        raise NotImplementedError


class SecurityChecker:
    """Run multiple security checks and aggregate results"""

    def __init__(self):
        self.checks: List[SecurityCheck] = []

    def add_check(self, check: SecurityCheck):
        self.checks.append(check)
        logger.info(f"🔒 Security check added: {check.name}")

    async def run_all(self, context: Dict[str, Any]) -> List[CheckResult]:
        results = []
        for check in self.checks:
            try:
                result = await check.run(context)
                results.append(result)
            except Exception as e:
                logger.error(f"🔒 Check {check.name} failed: {e}")
                results.append(CheckResult(
                    check_name=check.name, passed=False,
                    risk_score=0, details=f"Error: {e}"
                ))
        return results

    def get_total_risk(self, results: List[CheckResult]) -> int:
        return min(sum(r.risk_score for r in results if not r.passed), 100)