"""
ReviewerAgent 评测基准

对 ReviewerAgent 进行系统性评测，计算多维度指标。
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

from evaluation.datasets.schemas import SyntheticTestCase, IssueCategory
from evaluation.metrics import (
    StabilityMetric,
    StabilityResult,
    LatencyMetric,
    LatencyResult,
    ToolCallMetric,
    ToolCallRecord,
    FindingJudge,
    BatchEvaluationResult,
)


@dataclass
class BenchmarkConfig:
    """评测配置"""

    n_runs: int = 3
    temperature: float = 0.0
    categories: Optional[List[IssueCategory]] = None
    max_cases_per_category: Optional[int] = None
    judge_model: str = "qwen-max"
    timeout_seconds: int = 60


@dataclass
class TestCaseResult:
    """单个测试用例评测结果"""

    test_case_id: str
    test_case_name: str
    category: IssueCategory
    difficulty: str

    finding_recall: float = 0.0
    finding_precision: float = 0.0
    finding_f1: float = 0.0

    latency_ms: float = 0.0
    tool_calls: int = 0
    tool_success_rate: float = 0.0

    stability_score: float = 0.0

    detected_issues: int = 0
    expected_issues: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """评测总结果"""

    agent_name: str
    agent_role: str
    config: BenchmarkConfig
    start_time: datetime
    end_time: Optional[datetime] = None

    total_cases: int = 0
    successful_cases: int = 0
    failed_cases: int = 0

    avg_recall: float = 0.0
    avg_precision: float = 0.0
    avg_f1: float = 0.0

    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0

    avg_stability: float = 0.0
    avg_tool_success_rate: float = 0.0

    category_results: Dict[str, Dict[str, float]] = field(default_factory=dict)
    case_results: List[TestCaseResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "config": {
                "n_runs": self.config.n_runs,
                "temperature": self.config.temperature,
                "judge_model": self.config.judge_model,
            },
            "timing": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "duration_seconds": (
                    (self.end_time - self.start_time).total_seconds()
                    if self.end_time else None
                ),
            },
            "summary": {
                "total_cases": self.total_cases,
                "successful_cases": self.successful_cases,
                "failed_cases": self.failed_cases,
                "avg_recall": self.avg_recall,
                "avg_precision": self.avg_precision,
                "avg_f1": self.avg_f1,
                "avg_latency_ms": self.avg_latency_ms,
                "p50_latency_ms": self.p50_latency_ms,
                "p95_latency_ms": self.p95_latency_ms,
                "p99_latency_ms": self.p99_latency_ms,
                "avg_stability": self.avg_stability,
                "avg_tool_success_rate": self.avg_tool_success_rate,
            },
            "category_results": self.category_results,
        }


class ReviewerBenchmark:
    """ReviewerAgent 评测基准

    对 ReviewerAgent 进行系统性评测，包括：
    - Finding 检出准确率（召回率/精确率/F1）
    - 响应延迟（P50/P95/P99）
    - 输出稳定性
    - 工具调用成功率
    """

    def __init__(
        self,
        config: Optional[BenchmarkConfig] = None,
        test_cases: Optional[List[SyntheticTestCase]] = None,
    ):
        self.config = config or BenchmarkConfig()
        self.test_cases = test_cases or []

        self.stability_metric = StabilityMetric(
            n_runs=self.config.n_runs,
            temperature=self.config.temperature,
        )
        self.latency_metric = LatencyMetric()
        self.tool_metric = ToolCallMetric()
        self.finding_judge = FindingJudge(model_name=self.config.judge_model)

    def load_test_cases(
        self,
        categories: Optional[List[IssueCategory]] = None,
        max_per_category: Optional[int] = None,
    ) -> None:
        """加载测试用例

        Args:
            categories: 要加载的类别列表，None 表示加载全部
            max_per_category: 每类最大数量，None 表示不限制
        """
        from evaluation.datasets import (
            get_security_test_cases,
            get_performance_test_cases,
            get_logic_test_cases,
            get_style_test_cases,
        )

        all_cases = []
        case_loaders = {
            IssueCategory.SECURITY: get_security_test_cases,
            IssueCategory.PERFORMANCE: get_performance_test_cases,
            IssueCategory.LOGIC: get_logic_test_cases,
            IssueCategory.STYLE: get_style_test_cases,
        }

        target_categories = categories or list(case_loaders.keys())

        for category in target_categories:
            if category in case_loaders:
                cases = case_loaders[category]()
                if max_per_category:
                    cases = cases[:max_per_category]
                all_cases.extend(cases)

        self.test_cases = all_cases

    async def run_single_case(
        self,
        test_case: SyntheticTestCase,
        agent_factory: Callable[[], Any],
    ) -> TestCaseResult:
        """运行单个测试用例评测

        Args:
            test_case: 测试用例
            agent_factory: Agent 工厂函数，用于创建新的 Agent 实例

        Returns:
            测试用例评测结果
        """
        result = TestCaseResult(
            test_case_id=test_case.id,
            test_case_name=test_case.name,
            category=test_case.category,
            difficulty=test_case.difficulty,
            expected_issues=len(test_case.injected_issues),
        )

        try:
            agent = agent_factory()
            result.metadata["agent_name"] = agent.name
            result.metadata["agent_role"] = getattr(agent, "role", "unknown")

            all_findings = []
            all_latencies = []
            all_tool_calls = []

            for run_idx in range(self.config.n_runs):
                start_time = time.time()

                try:
                    review_result = await asyncio.wait_for(
                        self._run_agent_review(agent, test_case),
                        timeout=self.config.timeout_seconds,
                    )

                    end_time = time.time()
                    latency_ms = (end_time - start_time) * 1000

                    all_findings.append(review_result.get("findings", []))
                    all_latencies.append(latency_ms)
                    all_tool_calls.extend(review_result.get("tool_calls", []))

                except asyncio.TimeoutError:
                    result.error = f"Timeout after {self.config.timeout_seconds}s"
                    break

            if not result.error:
                latency_records = [
                    LatencyResult(
                        start_time=0.0,
                        end_time=lat / 1000.0,
                        total_latency_ms=lat,
                    )
                    for lat in all_latencies
                ]
                for rec in latency_records:
                    self.latency_metric.record(rec)

                percentiles = self.latency_metric.calculate_percentiles()
                result.latency_ms = sum(all_latencies) / len(all_latencies) if all_latencies else 0.0

                tool_analysis = self.tool_metric.analyze(all_tool_calls)
                result.tool_calls = tool_analysis.total_calls
                result.tool_success_rate = (
                    tool_analysis.successful_calls / tool_analysis.total_calls
                    if tool_analysis.total_calls > 0 else 0.0
                )

                stability_results = [
                    StabilityResult(findings=findings)
                    for findings in all_findings
                ]
                result.stability_score = self.stability_metric.calculate_structural_consistency(
                    stability_results
                )

                final_findings = all_findings[0] if all_findings else []
                judge_result = await self._evaluate_findings(
                    final_findings,
                    test_case.injected_issues,
                )

                result.finding_recall = judge_result.recall
                result.finding_precision = judge_result.precision
                result.finding_f1 = judge_result.f1_score
                result.true_positives = judge_result.true_positives
                result.false_positives = judge_result.false_positives
                result.false_negatives = judge_result.false_negatives
                result.detected_issues = judge_result.true_positives

        except Exception as e:
            result.error = str(e)

        return result

    async def _run_agent_review(
        self,
        agent: Any,
        test_case: SyntheticTestCase,
    ) -> Dict[str, Any]:
        """运行 Agent 评审

        Args:
            agent: ReviewerAgent 实例
            test_case: 测试用例

        Returns:
            包含 findings 和 tool_calls 的字典
        """
        from tools.diff_parser import DiffChunk
        from tools.pr_parser import PRContext

        diff_chunks = [
            DiffChunk(
                file_path=chunk.file_path,
                old_start=chunk.old_start,
                old_count=chunk.old_count,
                new_start=chunk.new_start,
                new_count=chunk.new_count,
                additions=chunk.additions,
                deletions=chunk.deletions,
                context=chunk.context if hasattr(chunk, "context") else "",
                language=chunk.language if hasattr(chunk, "language") else "",
            )
            for chunk in test_case.diff_chunks
        ]

        pr_context = PRContext(
            title=f"Test: {test_case.name}",
            description=test_case.diff_chunks[0].context if test_case.diff_chunks else "",
        )

        try:
            if hasattr(agent, "review"):
                findings = await agent.review(diff_chunks, pr_context)
            elif hasattr(agent, "__call__"):
                findings = agent(diff_chunks, pr_context)
            else:
                findings = []

            if hasattr(findings, "findings"):
                findings = findings.findings

            findings_list = []
            for f in findings:
                if hasattr(f, "model_dump"):
                    findings_list.append(f.model_dump())
                elif hasattr(f, "to_dict"):
                    findings_list.append(f.to_dict())
                elif isinstance(f, dict):
                    findings_list.append(f)
                else:
                    findings_list.append({"title": str(f)})

            return {
                "findings": findings_list,
                "tool_calls": [],
            }

        except Exception as e:
            return {
                "findings": [],
                "tool_calls": [],
                "error": str(e),
            }

    async def _evaluate_findings(
        self,
        findings: List[Dict[str, Any]],
        ground_truth: List[Any],
    ) -> BatchEvaluationResult:
        """评估 Finding 质量

        Args:
            findings: Agent 输出的 Finding 列表
            ground_truth: Ground Truth 问题列表

        Returns:
            批量评估结果
        """
        gt_list = []
        for issue in ground_truth:
            gt_list.append({
                "title": issue.title,
                "severity": issue.severity,
                "category": issue.category.value if hasattr(issue.category, "value") else str(issue.category),
                "hints": issue.detection_hints,
            })

        return await self.finding_judge.evaluate_batch(findings, gt_list)

    async def run_benchmark(
        self,
        agent_factory: Callable[[], Any],
        agent_name: str = "ReviewerAgent",
        agent_role: str = "reviewer",
    ) -> BenchmarkResult:
        """运行完整评测

        Args:
            agent_factory: Agent 工厂函数
            agent_name: Agent 名称
            agent_role: Agent 角色

        Returns:
            评测总结果
        """
        result = BenchmarkResult(
            agent_name=agent_name,
            agent_role=agent_role,
            config=self.config,
            start_time=datetime.now(),
        )

        if not self.test_cases:
            self.load_test_cases(
                categories=self.config.categories,
                max_per_category=self.config.max_cases_per_category,
            )

        result.total_cases = len(self.test_cases)

        for test_case in self.test_cases:
            case_result = await self.run_single_case(test_case, agent_factory)
            result.case_results.append(case_result)

            if case_result.error:
                result.failed_cases += 1
            else:
                result.successful_cases += 1

        if result.case_results:
            successful_results = [r for r in result.case_results if not r.error]

            if successful_results:
                result.avg_recall = sum(r.finding_recall for r in successful_results) / len(successful_results)
                result.avg_precision = sum(r.finding_precision for r in successful_results) / len(successful_results)
                result.avg_f1 = sum(r.finding_f1 for r in successful_results) / len(successful_results)
                result.avg_latency_ms = sum(r.latency_ms for r in successful_results) / len(successful_results)
                result.avg_stability = sum(r.stability_score for r in successful_results) / len(successful_results)
                result.avg_tool_success_rate = sum(r.tool_success_rate for r in successful_results) / len(successful_results)

                percentiles = self.latency_metric.calculate_percentiles()
                result.p50_latency_ms = percentiles.get("p50", 0.0)
                result.p95_latency_ms = percentiles.get("p95", 0.0)
                result.p99_latency_ms = percentiles.get("p99", 0.0)

                category_data: Dict[str, List[TestCaseResult]] = {}
                for cr in successful_results:
                    cat = cr.category.value
                    if cat not in category_data:
                        category_data[cat] = []
                    category_data[cat].append(cr)

                for cat, cases in category_data.items():
                    result.category_results[cat] = {
                        "count": len(cases),
                        "avg_recall": sum(c.finding_recall for c in cases) / len(cases),
                        "avg_precision": sum(c.finding_precision for c in cases) / len(cases),
                        "avg_f1": sum(c.finding_f1 for c in cases) / len(cases),
                        "avg_latency_ms": sum(c.latency_ms for c in cases) / len(cases),
                    }

        result.end_time = datetime.now()
        return result

    def run_benchmark_sync(
        self,
        agent_factory: Callable[[], Any],
        agent_name: str = "ReviewerAgent",
        agent_role: str = "reviewer",
    ) -> BenchmarkResult:
        """同步运行完整评测

        Args:
            agent_factory: Agent 工厂函数
            agent_name: Agent 名称
            agent_role: Agent 角色

        Returns:
            评测总结果
        """
        return asyncio.run(
            self.run_benchmark(agent_factory, agent_name, agent_role)
        )
