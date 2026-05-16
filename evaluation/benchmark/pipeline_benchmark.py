"""
流程评测基准

对完整的评审流程进行系统性评测，包括：
- 并行评审阶段
- 辩论循环阶段
- 合并阶段
- 裁决阶段
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from logger import logger
from evaluation.metrics.pipeline_metrics import (
    PipelineMetrics,
    PipelineResult,
    StageMetrics,
    DebateMetrics,
    MergeMetrics,
    VerdictMetrics,
    ResourceMetrics,
)
from tools.diff_parser import DiffChunk
from tools.pr_parser import PRContext
from pipeline.parallel_review import ParallelReviewManager, ParallelReviewResult
from pipeline.debate_loop import run_debate_loop, DebateRecord
from pipeline.issue_merger import merge_similar_findings, MergeRecord
from pipeline.verdict import make_final_verdict, Verdict

_pipeline_logger = logger.get_logger("evaluation.benchmark.pipeline_benchmark")


@dataclass
class PipelineBenchmarkConfig:
    """流程评测配置"""

    max_debate_rounds: int = 3
    confidence_threshold: float = 0.6
    merge_similarity_threshold: float = 0.8
    parallel_timeout: int = 300
    track_resources: bool = True


@dataclass
class PipelineBenchmarkResult:
    """流程评测结果"""

    pipeline_id: str
    config: PipelineBenchmarkConfig
    start_time: datetime
    end_time: Optional[datetime] = None

    parallel_review_result: Optional[ParallelReviewResult] = None
    debate_records: List[DebateRecord] = field(default_factory=list)
    merge_records: List[MergeRecord] = field(default_factory=list)
    verdict: Optional[Verdict] = None

    pipeline_result: Optional[PipelineResult] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "pipeline_id": self.pipeline_id,
            "config": {
                "max_debate_rounds": self.config.max_debate_rounds,
                "confidence_threshold": self.config.confidence_threshold,
                "merge_similarity_threshold": self.config.merge_similarity_threshold,
            },
            "timing": {
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
            },
            "summary": {
                "total_findings": len(self.parallel_review_result.findings) if self.parallel_review_result else 0,
                "debated_findings": len(self.debate_records),
                "merged_groups": len(self.merge_records),
                "final_findings": len(self.verdict.findings) if self.verdict else 0,
            },
        }


class PipelineBenchmark:
    """流程评测基准

    对完整的评审流程进行系统性评测，包括：
    - 并行评审阶段：多评审者并行执行
    - 辩论循环阶段：质疑-辩护循环
    - 合并阶段：相似发现合并
    - 裁决阶段：最终裁决生成
    """

    def __init__(
        self,
        config: Optional[PipelineBenchmarkConfig] = None,
    ) -> None:
        self.config = config or PipelineBenchmarkConfig()
        self.metrics = PipelineMetrics()
        self._results: List[PipelineBenchmarkResult] = []

    @property
    def results(self) -> List[PipelineBenchmarkResult]:
        """获取所有评测结果"""
        return list(self._results)

    async def run_pipeline(
        self,
        reviewers: List[Any],
        prosecutor: Any,
        defender: Any,
        diff_chunks: List[DiffChunk],
        pr_context: Optional[PRContext] = None,
        diff_context: str = "",
    ) -> PipelineBenchmarkResult:
        """运行完整评审流程

        Args:
            reviewers: 评审者 Agent 列表
            prosecutor: 质疑者 Agent
            defender: 辩护者 Agent
            diff_chunks: Diff 块列表
            pr_context: PR 上下文（可选）
            diff_context: 代码变更上下文文本

        Returns:
            PipelineBenchmarkResult
        """
        pipeline_id = str(uuid.uuid4())[:8]
        start_time = datetime.now()

        result = PipelineBenchmarkResult(
            pipeline_id=pipeline_id,
            config=self.config,
            start_time=start_time,
        )

        pipeline_result = PipelineResult(
            pipeline_id=pipeline_id,
            start_time=start_time,
            end_time=start_time,
        )

        stage_metrics: List[StageMetrics] = []
        resource_metrics = ResourceMetrics()

        try:
            stage_start = datetime.now()

            parallel_manager = ParallelReviewManager(
                reviewers=reviewers,
                timeout=self.config.parallel_timeout,
            )

            if pr_context is None:
                pr_context = PRContext(title="", description="")

            parallel_result = await parallel_manager.run_all(diff_chunks, pr_context)
            result.parallel_review_result = parallel_result

            stage_end = datetime.now()
            stage_metrics.append(StageMetrics(
                stage_name="parallel_review",
                start_time=stage_start,
                end_time=stage_end,
                metadata={
                    "total_reviewers": parallel_result.total_reviewers,
                    "successful_reviewers": parallel_result.successful_reviewers,
                    "findings_count": len(parallel_result.findings),
                },
            ))

            if self.config.track_resources:
                resource_metrics.total_llm_calls += parallel_result.total_reviewers

            stage_start = datetime.now()

            debate_records = await run_debate_loop(
                findings=parallel_result.findings,
                prosecutor=prosecutor,
                defender=defender,
                diff_context=diff_context,
                max_rounds=self.config.max_debate_rounds,
                confidence_threshold=self.config.confidence_threshold,
            )
            result.debate_records = debate_records

            stage_end = datetime.now()
            stage_metrics.append(StageMetrics(
                stage_name="debate",
                start_time=stage_start,
                end_time=stage_end,
                metadata={
                    "total_findings": len(parallel_result.findings),
                    "debate_records": len(debate_records),
                },
            ))

            debate_metrics = self._extract_debate_metrics(debate_records)
            debate_metrics.duration_ms = (stage_end - stage_start).total_seconds() * 1000
            pipeline_result.debate_metrics = debate_metrics

            if self.config.track_resources:
                resource_metrics.total_llm_calls += len(debate_records) * 2 * self.config.max_debate_rounds

            stage_start = datetime.now()

            merge_records = merge_similar_findings(
                debate_records=debate_records,
                similarity_threshold=self.config.merge_similarity_threshold,
            )
            result.merge_records = merge_records

            stage_end = datetime.now()
            stage_metrics.append(StageMetrics(
                stage_name="merge",
                start_time=stage_start,
                end_time=stage_end,
                metadata={
                    "merged_groups": len(merge_records),
                },
            ))

            merge_metrics = self._extract_merge_metrics(merge_records, debate_records)
            merge_metrics.duration_ms = (stage_end - stage_start).total_seconds() * 1000
            pipeline_result.merge_metrics = merge_metrics

            stage_start = datetime.now()

            verdict = make_final_verdict(
                debate_records=debate_records,
                merge_records=merge_records,
            )
            result.verdict = verdict

            stage_end = datetime.now()
            stage_metrics.append(StageMetrics(
                stage_name="verdict",
                start_time=stage_start,
                end_time=stage_end,
                metadata={
                    "final_findings": len(verdict.findings),
                },
            ))

            verdict_metrics = self._extract_verdict_metrics(verdict)
            verdict_metrics.duration_ms = (stage_end - stage_start).total_seconds() * 1000
            pipeline_result.verdict_metrics = verdict_metrics

        except Exception as e:
            _pipeline_logger.error("流程评测失败: %s", e, exc_info=True)
            pipeline_result.success = False
            pipeline_result.error = str(e)

        end_time = datetime.now()
        result.end_time = end_time

        pipeline_result.end_time = end_time
        pipeline_result.stage_metrics = stage_metrics
        pipeline_result.resource_metrics = resource_metrics

        result.pipeline_result = pipeline_result

        self._results.append(result)
        self.metrics.record(pipeline_result)

        return result

    def _extract_debate_metrics(self, debate_records: List[DebateRecord]) -> DebateMetrics:
        """从辩论记录提取指标"""
        metrics = DebateMetrics()

        metrics.total_findings = len(debate_records)

        for record in debate_records:
            metrics.total_rounds += len(record.rounds)

            if record.final_status == "confirmed":
                metrics.confirmed_count += 1
            elif record.final_status == "dismissed":
                metrics.dismissed_count += 1

            for round_record in record.rounds:
                if round_record.challenge:
                    metrics.challenges_made += 1
                if round_record.defense:
                    metrics.defenses_made += 1

        metrics.calculate_rates()

        return metrics

    def _extract_merge_metrics(
        self,
        merge_records: List[MergeRecord],
        debate_records: List[DebateRecord],
    ) -> MergeMetrics:
        """从合并记录提取指标"""
        metrics = MergeMetrics()

        confirmed_count = sum(1 for r in debate_records if r.final_status == "confirmed")
        metrics.total_findings = confirmed_count
        metrics.merged_groups = len(merge_records)

        for record in merge_records:
            metrics.total_merged += len(record.merged_ids)

        metrics.calculate_rates()

        return metrics

    def _extract_verdict_metrics(self, verdict: Verdict) -> VerdictMetrics:
        """从裁决提取指标"""
        metrics = VerdictMetrics()

        metrics.total_findings = len(verdict.findings)
        metrics.dismissed_count = len(verdict.dismissed)
        metrics.merged_count = len(verdict.merged)

        for finding in verdict.findings:
            severity = finding.severity
            metrics.by_severity[severity] = metrics.by_severity.get(severity, 0) + 1

            category = finding.category
            metrics.by_category[category] = metrics.by_category.get(category, 0) + 1

        return metrics

    def get_summary(self) -> Dict[str, Any]:
        """获取评测汇总"""
        return self.metrics.get_summary()


def run_pipeline_benchmark(
    reviewers: List[Any],
    prosecutor: Any,
    defender: Any,
    diff_chunks: List[DiffChunk],
    pr_context: Optional[PRContext] = None,
    diff_context: str = "",
    config: Optional[PipelineBenchmarkConfig] = None,
) -> PipelineBenchmarkResult:
    """同步运行流程评测

    Args:
        reviewers: 评审者 Agent 列表
        prosecutor: 质疑者 Agent
        defender: 辩护者 Agent
        diff_chunks: Diff 块列表
        pr_context: PR 上下文（可选）
        diff_context: 代码变更上下文文本
        config: 评测配置（可选）

    Returns:
        PipelineBenchmarkResult
    """
    benchmark = PipelineBenchmark(config=config)

    async def _run():
        return await benchmark.run_pipeline(
            reviewers=reviewers,
            prosecutor=prosecutor,
            defender=defender,
            diff_chunks=diff_chunks,
            pr_context=pr_context,
            diff_context=diff_context,
        )

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _run())
            return future.result()
    else:
        return asyncio.run(_run())
