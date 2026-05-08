"""
辩论循环引擎

协调质疑者和辩护者 agent 对评审发现进行结构化辩论，
根据辩论结果确定各发现的最终状态（confirmed / dismissed）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from logger import logger
from agents.prosecutor import ProsecutorAgent, Challenge
from agents.defender import DefenderAgent, Defense
from agents.reviewer import Finding

_debate_logger = logger.get_logger("pipeline.debate_loop")


@dataclass
class DebateRound:
    """单轮辩论记录。

    包含一轮中质疑者的质疑和辩护者的辩护。
    """

    round_number: int
    challenge: Challenge | None = None
    defense: Defense | None = None
    rebuttal: str | None = None


@dataclass
class DebateRecord:
    """单个评审发现的完整辩论记录。

    包含原始发现、多轮辩论历史以及最终状态。
    """

    finding_id: str
    original_finding: Finding
    rounds: List[DebateRound] = field(default_factory=list)
    final_status: str = "pending"
    merged_into: str | None = None


async def run_debate_loop(
    findings: List[Finding],
    prosecutor: ProsecutorAgent,
    defender: DefenderAgent,
    diff_context: str,
    max_rounds: int = 3,
    confidence_threshold: float = 0.6,
) -> List[DebateRecord]:
    """对评审发现列表执行辩论循环。

    每个发现依次经历多轮质疑-辩护，每轮后评估置信度，
    达到阈值则提前终止，否则继续至最大轮次。
    最终状态由辩护结果决定。

    Args:
        findings: 待辩论的评审发现列表。
        prosecutor: 质疑者 Agent。
        defender: 辩护者 Agent。
        diff_context: 代码变更上下文文本。
        max_rounds: 每个发现的最大辩论轮次（默认 3）。
        confidence_threshold: 置信度阈值，达到后提前终止（默认 0.6）。

    Returns:
        辩论记录列表，每个发现对应一条记录。
    """
    records: List[DebateRecord] = []

    if not findings:
        _debate_logger.info("无评审发现，跳过辩论循环")
        return records

    _debate_logger.info(
        "辩论循环启动: findings=%d max_rounds=%d threshold=%.2f",
        len(findings), max_rounds, confidence_threshold,
    )

    for finding in findings:
        rounds: List[DebateRound] = []
        final_stands = True

        _debate_logger.info(
            "开始辩论: finding_id=%s title=%s",
            finding.id, finding.title,
        )

        for round_num in range(1, max_rounds + 1):
            challenge = await prosecutor.challenge(finding)
            defense = await defender.defend(finding, challenge, diff_context)

            round_record = DebateRound(
                round_number=round_num,
                challenge=challenge,
                defense=defense,
                rebuttal=None,
            )
            rounds.append(round_record)
            final_stands = defense.finding_stands

            confidence = (
                defense.revised_confidence
                if defense.revised_confidence is not None
                else challenge.confidence
            )

            _debate_logger.info(
                "辩论轮次: finding_id=%s round=%d stands=%s confidence=%.2f",
                finding.id, round_num, final_stands, confidence,
            )

            if confidence >= confidence_threshold:
                _debate_logger.info(
                    "置信度达到阈值，提前终止: finding_id=%s confidence=%.2f",
                    finding.id, confidence,
                )
                break

        status = "confirmed" if final_stands else "dismissed"

        _debate_logger.info(
            "辩论完成: finding_id=%s status=%s rounds=%d",
            finding.id, status, len(rounds),
        )

        records.append(DebateRecord(
            finding_id=finding.id,
            original_finding=finding,
            rounds=rounds,
            final_status=status,
            merged_into=None,
        ))

    return records
