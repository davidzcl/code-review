"""
流程评测指标

定义评审流程（Pipeline）的多维度评测指标，包括：
- 各阶段延迟
- 辩论效果
- 合并质量
- 最终裁决质量
- 资源消耗
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class StageMetrics:
    """单阶段指标"""

    stage_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.duration_ms == 0.0:
            delta = self.end_time - self.start_time
            self.duration_ms = delta.total_seconds() * 1000


@dataclass
class DebateMetrics:
    """辩论循环指标"""

    total_findings: int = 0
    total_rounds: int = 0
    avg_rounds_per_finding: float = 0.0
    confirmed_count: int = 0
    dismissed_count: int = 0
    confirmation_rate: float = 0.0
    dismissal_rate: float = 0.0
    challenges_made: int = 0
    defenses_made: int = 0
    avg_challenge_length: float = 0.0
    avg_defense_length: float = 0.0
    duration_ms: float = 0.0

    def calculate_rates(self):
        """计算确认率和驳回率"""
        if self.total_findings > 0:
            self.confirmation_rate = self.confirmed_count / self.total_findings
            self.dismissal_rate = self.dismissed_count / self.total_findings
            self.avg_rounds_per_finding = self.total_rounds / self.total_findings


@dataclass
class MergeMetrics:
    """合并指标"""

    total_findings: int = 0
    merged_groups: int = 0
    total_merged: int = 0
    merge_rate: float = 0.0
    avg_group_size: float = 0.0
    similarity_scores: List[float] = field(default_factory=list)
    avg_similarity: float = 0.0
    duration_ms: float = 0.0

    def calculate_rates(self):
        """计算合并率"""
        if self.total_findings > 0:
            self.merge_rate = self.total_merged / self.total_findings
        if self.merged_groups > 0:
            self.avg_group_size = self.total_merged / self.merged_groups
        if self.similarity_scores:
            self.avg_similarity = np.mean(self.similarity_scores)


@dataclass
class VerdictMetrics:
    """裁决指标"""

    total_findings: int = 0
    by_severity: Dict[str, int] = field(default_factory=dict)
    by_category: Dict[str, int] = field(default_factory=dict)
    by_reviewer: Dict[str, int] = field(default_factory=dict)
    dismissed_count: int = 0
    merged_count: int = 0
    unique_findings: int = 0
    duration_ms: float = 0.0


@dataclass
class ResourceMetrics:
    """资源消耗指标"""

    total_llm_calls: int = 0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    avg_tokens_per_call: float = 0.0
    peak_concurrency: int = 0
    avg_concurrency: float = 0.0
    by_agent: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def calculate_averages(self):
        """计算平均值"""
        if self.total_llm_calls > 0:
            self.avg_tokens_per_call = self.total_tokens / self.total_llm_calls


@dataclass
class PipelineResult:
    """流程评测结果"""

    pipeline_id: str
    start_time: datetime
    end_time: datetime
    total_duration_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None

    parallel_review_metrics: Optional[StageMetrics] = None
    debate_metrics: Optional[DebateMetrics] = None
    merge_metrics: Optional[MergeMetrics] = None
    verdict_metrics: Optional[VerdictMetrics] = None
    resource_metrics: Optional[ResourceMetrics] = None

    stage_metrics: List[StageMetrics] = field(default_factory=list)

    finding_recall: float = 0.0
    finding_precision: float = 0.0
    finding_f1: float = 0.0

    def __post_init__(self):
        if self.total_duration_ms == 0.0:
            delta = self.end_time - self.start_time
            self.total_duration_ms = delta.total_seconds() * 1000

    def get_stage_duration(self, stage_name: str) -> Optional[float]:
        """获取指定阶段的耗时"""
        for stage in self.stage_metrics:
            if stage.stage_name == stage_name:
                return stage.duration_ms
        return None

    def get_stage_breakdown(self) -> Dict[str, float]:
        """获取各阶段耗时占比"""
        if not self.stage_metrics or self.total_duration_ms == 0:
            return {}

        breakdown = {}
        for stage in self.stage_metrics:
            percentage = (stage.duration_ms / self.total_duration_ms) * 100
            breakdown[stage.stage_name] = percentage

        return breakdown

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "pipeline_id": self.pipeline_id,
            "timing": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "total_duration_ms": self.total_duration_ms,
            },
            "success": self.success,
            "error": self.error,
            "stages": {
                stage.stage_name: {
                    "duration_ms": stage.duration_ms,
                    "success": stage.success,
                }
                for stage in self.stage_metrics
            },
            "debate": {
                "total_findings": self.debate_metrics.total_findings if self.debate_metrics else 0,
                "confirmed_count": self.debate_metrics.confirmed_count if self.debate_metrics else 0,
                "dismissed_count": self.debate_metrics.dismissed_count if self.debate_metrics else 0,
                "confirmation_rate": self.debate_metrics.confirmation_rate if self.debate_metrics else 0.0,
            },
            "merge": {
                "merge_rate": self.merge_metrics.merge_rate if self.merge_metrics else 0.0,
                "avg_similarity": self.merge_metrics.avg_similarity if self.merge_metrics else 0.0,
            },
            "verdict": {
                "total_findings": self.verdict_metrics.total_findings if self.verdict_metrics else 0,
                "by_severity": self.verdict_metrics.by_severity if self.verdict_metrics else {},
            },
            "resources": {
                "total_llm_calls": self.resource_metrics.total_llm_calls if self.resource_metrics else 0,
                "total_tokens": self.resource_metrics.total_tokens if self.resource_metrics else 0,
            },
            "quality": {
                "finding_recall": self.finding_recall,
                "finding_precision": self.finding_precision,
                "finding_f1": self.finding_f1,
            },
        }


class PipelineMetrics:
    """流程评测指标计算器

    计算评审流程的多维度指标：
    - 各阶段延迟
    - 辩论效果
    - 合并质量
    - 资源消耗
    """

    def __init__(self):
        self.results: List[PipelineResult] = []

    def record(self, result: PipelineResult) -> None:
        """记录评测结果"""
        self.results.append(result)

    def calculate_stage_statistics(self) -> Dict[str, Dict[str, float]]:
        """计算各阶段统计信息"""
        if not self.results:
            return {}

        stage_data: Dict[str, List[float]] = {}

        for result in self.results:
            for stage in result.stage_metrics:
                if stage.stage_name not in stage_data:
                    stage_data[stage.stage_name] = []
                stage_data[stage.stage_name].append(stage.duration_ms)

        statistics = {}
        for stage_name, durations in stage_data.items():
            if durations:
                statistics[stage_name] = {
                    "count": len(durations),
                    "avg_ms": np.mean(durations),
                    "min_ms": np.min(durations),
                    "max_ms": np.max(durations),
                    "p50_ms": np.percentile(durations, 50),
                    "p95_ms": np.percentile(durations, 95),
                    "p99_ms": np.percentile(durations, 99),
                }

        return statistics

    def calculate_debate_statistics(self) -> Dict[str, float]:
        """计算辩论统计信息"""
        debate_data = [r.debate_metrics for r in self.results if r.debate_metrics]

        if not debate_data:
            return {}

        return {
            "total_findings": sum(d.total_findings for d in debate_data),
            "avg_rounds": np.mean([d.avg_rounds_per_finding for d in debate_data]),
            "avg_confirmation_rate": np.mean([d.confirmation_rate for d in debate_data]),
            "avg_dismissal_rate": np.mean([d.dismissal_rate for d in debate_data]),
            "avg_duration_ms": np.mean([d.duration_ms for d in debate_data]),
        }

    def calculate_merge_statistics(self) -> Dict[str, float]:
        """计算合并统计信息"""
        merge_data = [r.merge_metrics for r in self.results if r.merge_metrics]

        if not merge_data:
            return {}

        avg_similarities = [d.avg_similarity for d in merge_data if d.avg_similarity > 0]

        return {
            "total_merged": sum(d.total_merged for d in merge_data),
            "avg_merge_rate": np.mean([d.merge_rate for d in merge_data]),
            "avg_similarity": np.mean(avg_similarities) if avg_similarities else 0.0,
            "avg_duration_ms": np.mean([d.duration_ms for d in merge_data]),
        }

    def calculate_resource_statistics(self) -> Dict[str, float]:
        """计算资源消耗统计"""
        resource_data = [r.resource_metrics for r in self.results if r.resource_metrics]

        if not resource_data:
            return {}

        avg_tokens_list = [d.avg_tokens_per_call for d in resource_data if d.avg_tokens_per_call > 0]

        return {
            "total_llm_calls": sum(d.total_llm_calls for d in resource_data),
            "total_tokens": sum(d.total_tokens for d in resource_data),
            "avg_tokens_per_call": np.mean(avg_tokens_list) if avg_tokens_list else 0.0,
            "avg_peak_concurrency": np.mean([d.peak_concurrency for d in resource_data]),
        }

    def calculate_quality_statistics(self) -> Dict[str, float]:
        """计算质量统计"""
        if not self.results:
            return {}

        return {
            "avg_recall": np.mean([r.finding_recall for r in self.results]),
            "avg_precision": np.mean([r.finding_precision for r in self.results]),
            "avg_f1": np.mean([r.finding_f1 for r in self.results]),
            "success_rate": sum(1 for r in self.results if r.success) / len(self.results),
        }

    def calculate_latency_percentiles(self) -> Dict[str, float]:
        """计算延迟百分位数"""
        if not self.results:
            return {}

        durations = [r.total_duration_ms for r in self.results]

        return {
            "avg_ms": np.mean(durations),
            "min_ms": np.min(durations),
            "max_ms": np.max(durations),
            "p50_ms": np.percentile(durations, 50),
            "p95_ms": np.percentile(durations, 95),
            "p99_ms": np.percentile(durations, 99),
        }

    def get_summary(self) -> Dict[str, Any]:
        """获取汇总报告"""
        return {
            "total_runs": len(self.results),
            "successful_runs": sum(1 for r in self.results if r.success),
            "failed_runs": sum(1 for r in self.results if not r.success),
            "latency": self.calculate_latency_percentiles(),
            "stages": self.calculate_stage_statistics(),
            "debate": self.calculate_debate_statistics(),
            "merge": self.calculate_merge_statistics(),
            "resources": self.calculate_resource_statistics(),
            "quality": self.calculate_quality_statistics(),
        }
