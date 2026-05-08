"""
发现合并规则引擎

基于相似度算法对辩论后的评审发现进行聚类合并，
消除重复或高度重叠的发现，降低评审报告的噪声。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from logger import logger
from agents.reviewer import Finding
from pipeline.debate_loop import DebateRecord

_merger_logger = logger.get_logger("pipeline.issue_merger")

# 相似度权重
_W_FILE_PATH = 0.40
_W_LINE_RANGE = 0.30
_W_TITLE_TEXT = 0.20
_W_SEVERITY = 0.05
_W_ROLE = 0.05


@dataclass
class MergeRecord:
    """合并记录。

    记录一组相似发现的合并信息。
    """

    primary_id: str
    merged_ids: List[str] = field(default_factory=list)
    merge_reason: str = ""
    merged_finding: Finding | None = None


def compute_finding_similarity(f1: Finding, f2: Finding) -> float:
    """计算两个评审发现之间的相似度（0.0 ~ 1.0）。

    基于文件路径、行范围、标题文本、严重级别、评审维度
    五个维度加权计算。

    Args:
        f1: 第一个评审发现。
        f2: 第二个评审发现。

    Returns:
        相似度分数，0.0 表示完全不同，1.0 表示完全相同。
    """
    score = 0.0

    # 1. 文件路径
    same_file = bool(f1.file_path and f2.file_path and f1.file_path == f2.file_path)
    if same_file:
        score += _W_FILE_PATH

    # 2. 行范围重叠度 (Jaccard-like)，仅在相同文件中计算
    s1, e1 = f1.line_range
    s2, e2 = f2.line_range
    if same_file and s1 < e1 and s2 < e2:
        overlap_start = max(s1, s2)
        overlap_end = min(e1, e2)
        if overlap_start < overlap_end:
            union_start = min(s1, s2)
            union_end = max(e1, e2)
            union = union_end - union_start
            if union > 0:
                overlap = overlap_end - overlap_start
                score += _W_LINE_RANGE * (overlap / union)

    # 3. 标题文本相似度 (单词级 Jaccard)
    words1 = _tokenize(f1.title + " " + f1.description)
    words2 = _tokenize(f2.title + " " + f2.description)
    if words1 and words2:
        intersection = words1 & words2
        union = words1 | words2
        score += _W_TITLE_TEXT * (len(intersection) / len(union))

    # 4. 严重级别
    if f1.severity and f2.severity and f1.severity == f2.severity:
        score += _W_SEVERITY

    # 5. 评审维度
    if f1.role and f2.role and f1.role == f2.role:
        score += _W_ROLE

    return round(score, 4)


def _tokenize(text: str) -> Set[str]:
    """将文本分词为小写单词集合。"""
    import re
    words = re.findall(r"[a-zA-Z\u4e00-\u9fff0-9]+", text.lower())
    return set(words)


def _severity_rank(severity: str) -> int:
    """严重级别排序权重。"""
    return {"critical": 3, "important": 2, "minor": 1}.get(severity, 0)


def merge_similar_findings(
    debate_records: List[DebateRecord],
    similarity_threshold: float = 0.8,
) -> List[MergeRecord]:
    """对辩论后的评审发现进行相似度合并。

    采用贪心聚类策略：
    1. 按严重级别降序排序，确保更严重的问题作为主发现
    2. 依次比较每对发现，将相似度 >= 阈值的合为一组
    3. 同组中第一个设为 primary，其余设为 merged

    Args:
        debate_records: 辩论记录列表。
        similarity_threshold: 相似度阈值（默认 0.8）。

    Returns:
        合并记录列表。
    """
    if not debate_records:
        _merger_logger.info("空输入，跳过合并")
        return []

    confirmed = [
        r for r in debate_records
        if r.final_status == "confirmed"
    ]

    if not confirmed:
        _merger_logger.info("无 confirmed 发现，跳过合并")
        return []

    confirmed.sort(
        key=lambda r: _severity_rank(r.original_finding.severity),
        reverse=True,
    )

    merged_ids: Set[str] = set()
    merge_records: List[MergeRecord] = []

    for i, primary in enumerate(confirmed):
        if primary.finding_id in merged_ids:
            continue

        merged: List[str] = []
        for j in range(i + 1, len(confirmed)):
            other = confirmed[j]
            if other.finding_id in merged_ids:
                continue

            sim = compute_finding_similarity(
                primary.original_finding,
                other.original_finding,
            )

            if sim >= similarity_threshold:
                merged.append(other.finding_id)
                merged_ids.add(other.finding_id)

        if merged:
            merge_records.append(MergeRecord(
                primary_id=primary.finding_id,
                merged_ids=merged,
                merge_reason=f"相似度 >= {similarity_threshold}",
                merged_finding=primary.original_finding,
            ))

            _merger_logger.info(
                "合并: primary=%s merged=%s similarity=%.2f",
                primary.finding_id, merged, sim,
            )

    return merge_records
