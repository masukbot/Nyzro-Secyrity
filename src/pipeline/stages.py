"""
Rinox Sentinel - Pipeline Stages
Individual processing stages for the security pipeline
"""

from typing import List, Optional, Any
from dataclasses import dataclass


@dataclass
class StageResult:
    """Result from a single pipeline stage"""
    risk_score: Optional[int] = None
    confidence: Optional[float] = None
    issues: List[str] = None
    data: dict = None
    abort: bool = False

    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.data is None:
            self.data = {}


class Stage:
    """Base pipeline stage"""

    def __init__(self, name: str):
        self.name = name

    async def execute(self, context: Any) -> StageResult:
        raise NotImplementedError