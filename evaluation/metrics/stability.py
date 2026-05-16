"""
输出稳定性评测指标

计算智能体多次运行结果的一致性分数。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class StabilityResult:
    """单次运行结果"""

    findings: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class StabilityMetric:
    """稳定性评测指标

    计算多次运行结果的一致性分数，包括：
    - 结构一致性：字段值一致性
    - 严重级别分布 KL 散度
    - 综合稳定性评分

    参数:
        n_runs: 重复运行次数（默认 3）
        temperature: 稳定性测试时的 temperature（默认 0.0）
    """

    SMOOTH_EPSILON = 1e-10

    def __init__(self, n_runs: int = 3, temperature: float = 0.0):
        self.n_runs = n_runs
        self.temperature = temperature

    def calculate_structural_consistency(
        self, results: List[StabilityResult]
    ) -> float:
        """计算结构一致性

        基于字段值一致性计算分数。
        比较每次运行的 findings 中字段值是否相同。

        Args:
            results: 多次运行的结果列表

        Returns:
            结构一致性分数 (0.0-1.0)
        """
        if not results:
            return 0.0

        if len(results) == 1:
            return 1.0

        all_findings_empty = all(len(r.findings) == 0 for r in results)
        if all_findings_empty:
            return 1.0

        key_fields = ["title", "severity", "file_path"]

        consistency_scores = []
        ref_result = results[0]

        for result in results[1:]:
            if len(result.findings) != len(ref_result.findings):
                consistency_scores.append(0.0)
                continue

            if len(ref_result.findings) == 0:
                consistency_scores.append(1.0)
                continue

            finding_scores = []
            for ref_finding, finding in zip(ref_result.findings, result.findings):
                field_matches = 0
                field_total = 0

                for key in key_fields:
                    if key in ref_finding or key in finding:
                        field_total += 1
                        if ref_finding.get(key) == finding.get(key):
                            field_matches += 1

                if field_total > 0:
                    finding_scores.append(field_matches / field_total)
                else:
                    finding_scores.append(1.0)

            consistency_scores.append(sum(finding_scores) / len(finding_scores))

        if not consistency_scores:
            return 1.0

        return sum(consistency_scores) / len(consistency_scores)

    def _smooth_distribution(
        self, dist: Dict[str, float], all_keys: set
    ) -> Dict[str, float]:
        """平滑分布，避免 0 值导致的 KL 散度问题

        Args:
            dist: 原始分布
            all_keys: 所有可能的 key

        Returns:
            平滑后的分布
        """
        smoothed = {}
        total = sum(dist.values())

        if total == 0:
            return {k: 1.0 / len(all_keys) for k in all_keys}

        for k in all_keys:
            smoothed[k] = (dist.get(k, 0) + self.SMOOTH_EPSILON) / (
                total + len(all_keys) * self.SMOOTH_EPSILON
            )

        return smoothed

    def calculate_severity_kl_divergence(
        self, results: List[StabilityResult]
    ) -> float:
        """计算严重级别分布 KL 散度

        KL 散度衡量两个概率分布的差异。
        比较每次运行的严重级别分布与参考分布的差异。

        Args:
            results: 多次运行的结果列表

        Returns:
            KL 散度值 (>= 0)
        """
        if not results or len(results) < 2:
            return 0.0

        severity_counts: List[Counter] = []
        for result in results:
            severities = [f.get("severity", "unknown") for f in result.findings]
            severity_counts.append(Counter(severities))

        if not any(severity_counts):
            return 0.0

        all_severities = set()
        for counter in severity_counts:
            all_severities.update(counter.keys())

        if not all_severities:
            return 0.0

        distributions = []
        for counter in severity_counts:
            total = sum(counter.values())
            raw_dist = {s: counter.get(s, 0) / total if total > 0 else 0 for s in all_severities}
            smoothed_dist = self._smooth_distribution(raw_dist, all_severities)
            distributions.append(smoothed_dist)

        ref_dist = distributions[0]
        kl_divergences = []

        for dist in distributions[1:]:
            kl = 0.0
            for s in all_severities:
                p = ref_dist.get(s, self.SMOOTH_EPSILON)
                q = dist.get(s, self.SMOOTH_EPSILON)
                kl += p * np.log(p / q)
            kl_divergences.append(max(0.0, kl))

        return sum(kl_divergences) / len(kl_divergences) if kl_divergences else 0.0

    def calculate_overall_stability(self, results: List[StabilityResult]) -> float:
        """计算综合稳定性评分

        综合结构一致性和严重级别分布一致性。

        Args:
            results: 多次运行的结果列表

        Returns:
            综合稳定性评分 (0.0-1.0)
        """
        if not results:
            return 0.0

        if len(results) == 1:
            return 1.0

        structural = self.calculate_structural_consistency(results)
        kl_div = self.calculate_severity_kl_divergence(results)

        kl_penalty = min(1.0, kl_div)
        severity_score = 1.0 - kl_penalty

        overall = 0.7 * structural + 0.3 * severity_score
        return max(0.0, min(1.0, overall))
