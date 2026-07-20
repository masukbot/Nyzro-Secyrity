"""
Rinox Sentinel - Pipeline Processor
Orchestrates multi-stage processing of messages and content
"""

import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from .stages import Stage, StageResult

logger = logging.getLogger("Rinox.Pipeline")


@dataclass
class PipelineContext:
    """Context passed through all pipeline stages"""
    guild_id: int
    user_id: int
    channel_id: int
    message_id: Optional[int] = None
    content: str = ""
    attachment_urls: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, StageResult] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Final result from the pipeline"""
    risk_score: int
    threat_level: int
    confidence: float
    issues: List[str]
    actions: List[str]
    stages_run: List[str]
    processing_time_ms: int
    context: PipelineContext


class PipelineProcessor:
    """Process content through multiple stages"""

    def __init__(self):
        self.stages: List[Stage] = []

    def add_stage(self, stage: Stage):
        self.stages.append(stage)
        logger.info(f"🔬 Pipeline stage added: {stage.name}")

    def insert_stage(self, index: int, stage: Stage):
        self.stages.insert(index, stage)

    def remove_stage(self, name: str):
        self.stages = [s for s in self.stages if s.name != name]

    async def process(self, context: PipelineContext) -> PipelineResult:
        """Run all stages in order"""
        start_time = time.time()
        all_issues = []
        total_risk = 0
        min_confidence = 1.0
        stages_run = []

        for stage in self.stages:
            try:
                result = await stage.execute(context)
                context.results[stage.name] = result
                stages_run.append(stage.name)

                if result.risk_score is not None:
                    total_risk = max(total_risk, result.risk_score)
                if result.confidence is not None:
                    min_confidence = min(min_confidence, result.confidence)
                if result.issues:
                    all_issues.extend(result.issues)

                if result.abort:
                    logger.debug(f"🔬 Pipeline aborted at stage: {stage.name}")
                    break

            except Exception as e:
                logger.error(f"🔬 Pipeline stage {stage.name} failed: {e}")
                stages_run.append(f"{stage.name}(failed)")

        total_risk = min(total_risk, 100)

        if total_risk >= 81:
            threat_level = 4
        elif total_risk >= 61:
            threat_level = 3
        elif total_risk >= 41:
            threat_level = 2
        elif total_risk >= 21:
            threat_level = 1
        else:
            threat_level = 0

        processing_time = int((time.time() - start_time) * 1000)

        return PipelineResult(
            risk_score=total_risk,
            threat_level=threat_level,
            confidence=min_confidence,
            issues=all_issues,
            actions=[],  # Determined by caller
            stages_run=stages_run,
            processing_time_ms=processing_time,
            context=context
        )

    def reset(self):
        self.stages.clear()