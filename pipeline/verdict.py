"""
最终裁决逻辑

聚合辩论结果和合并记录，生成最终评审裁决。
包含最终发现列表、驳回列表、合并记录和评审总结。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from logger import logger
from agents.reviewer import Finding
from pipeline.debate_loop import DebateRecord
from pipeline.issue_merger import MergeRecord

_verdict_logger = logger.get_logger("pipeline.verdict")


@dataclass
class Verdict:
    """最终裁决结果。

    包含经过辩论和合并后的最终评审结论。
    """

    findings: List[Finding] = field(default_factory=list)
    """最终确认的发现列表（已去重合并）。"""

    dismissed: List[str] = field(default_factory=list)
    """被驳回的 finding_id 列表。"""

    merged: List[MergeRecord] = field(default_factory=list)
    """合并记录列表。"""

    summary: str = ""
    """评审总结文本。"""


def make_final_verdict(
    debate_records: List[DebateRecord],
    merge_records: List[MergeRecord],
) -> Verdict:
    """根据辩论记录和合并记录生成最终裁决。

    处理流程：
    1. 从辩论记录中提取所有 confirmed 和 dismissed 的发现
    2. 按合并记录去重（保留 primary，移除 merged）
    3. 生成包含统计信息的总结文本

    Args:
        debate_records: 辩论记录列表。
        merge_records: 合并记录列表。

    Returns:
        最终裁决结果。
    """
    _verdict_logger.info(
        "开始裁决: debate_records=%d merge_records=%d",
        len(debate_records), len(merge_records),
    )

    confirmed_findings: Dict[str, Finding] = {}
    dismissed_ids: List[str] = []

    for record in debate_records:
        if record.final_status == "confirmed":
            confirmed_findings[record.finding_id] = record.original_finding
        elif record.final_status == "dismissed":
            dismissed_ids.append(record.finding_id)

    # 应用合并：移除被 merged 的 finding，保留 primary
    merged_removed: Set[str] = set()
    for mr in merge_records:
        for merged_id in mr.merged_ids:
            merged_removed.add(merged_id)
            if merged_id in confirmed_findings:
                _verdict_logger.info(
                    "移除 merged finding: %s", merged_id,
                )

    final_findings = [
        f for fid, f in confirmed_findings.items()
        if fid not in merged_removed
    ]

    # 统计
    total_original = len(debate_records)
    total_confirmed = len(confirmed_findings)
    total_dismissed = len(dismissed_ids)
    total_merged = sum(len(mr.merged_ids) for mr in merge_records)
    total_final = len(final_findings)

    severity_counts: Dict[str, int] = {}
    for f in final_findings:
        severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1

    summary = (
        f"共审查 {total_original} 个发现，"
        f"其中 {total_confirmed} 个确认、{total_dismissed} 个驳回、"
        f"{total_merged} 个合并。"
        f"最终保留 {total_final} 个发现"
    )
    if severity_counts:
        parts = []
        for level in ("critical", "important", "minor"):
            if level in severity_counts:
                parts.append(f"{level}: {severity_counts[level]}")
        if parts:
            summary += f"（{', '.join(parts)}）"

    _verdict_logger.info(
        "裁决完成: original=%d confirmed=%d dismissed=%d merged=%d final=%d",
        total_original, total_confirmed, total_dismissed,
        total_merged, total_final,
    )

    return Verdict(
        findings=final_findings,
        dismissed=dismissed_ids,
        merged=merge_records,
        summary=summary,
    )
