"""
评测系统集成测试

测试目标：
1. 端到端评测流程
2. 报告生成
3. 完整工作流验证
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import os

from evaluation import (
    ReviewerBenchmark,
    BenchmarkConfig,
    BenchmarkResult,
    TestCaseResult,
)
from evaluation.reporter import MDReporter, HTMLReporter
from evaluation.datasets.schemas import IssueCategory


class TestEvaluationIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_benchmark_workflow(self):
        """测试：完整评测工作流"""
        config = BenchmarkConfig(
            n_runs=1,
            categories=[IssueCategory.SECURITY],
            max_cases_per_category=2,
        )
        benchmark = ReviewerBenchmark(config=config)

        mock_agent = MagicMock()
        mock_agent.name = "TestReviewer"
        mock_agent.role = "security"
        mock_findings = MagicMock()
        mock_findings.findings = []
        mock_agent.review = AsyncMock(return_value=mock_findings)

        agent_factory = lambda: mock_agent

        result = await benchmark.run_benchmark(
            agent_factory,
            agent_name="TestReviewer",
            agent_role="security",
        )

        assert result is not None
        assert result.agent_name == "TestReviewer"
        assert result.total_cases == 2
        assert result.end_time is not None

    @pytest.mark.asyncio
    async def test_benchmark_with_report_generation(self):
        """测试：评测 + 报告生成"""
        config = BenchmarkConfig(
            n_runs=1,
            categories=[IssueCategory.SECURITY],
            max_cases_per_category=1,
        )
        benchmark = ReviewerBenchmark(config=config)

        mock_agent = MagicMock()
        mock_agent.name = "TestReviewer"
        mock_agent.role = "security"
        mock_findings = MagicMock()
        mock_findings.findings = []
        mock_agent.review = AsyncMock(return_value=mock_findings)

        agent_factory = lambda: mock_agent

        result = await benchmark.run_benchmark(
            agent_factory,
            agent_name="TestReviewer",
            agent_role="security",
        )

        md_reporter = MDReporter()
        md_report = md_reporter.generate(result)

        assert "# 智能体评测报告" in md_report
        assert "TestReviewer" in md_report

        html_reporter = HTMLReporter()
        html_report = html_reporter.generate(result)

        assert "<!DOCTYPE html>" in html_report
        assert "TestReviewer" in html_report

    def test_benchmark_sync_workflow(self):
        """测试：同步评测工作流"""
        config = BenchmarkConfig(
            n_runs=1,
            categories=[IssueCategory.PERFORMANCE],
            max_cases_per_category=1,
        )
        benchmark = ReviewerBenchmark(config=config)

        mock_agent = MagicMock()
        mock_agent.name = "PerfReviewer"
        mock_agent.role = "performance"
        mock_findings = MagicMock()
        mock_findings.findings = []
        mock_agent.review = AsyncMock(return_value=mock_findings)

        agent_factory = lambda: mock_agent

        result = benchmark.run_benchmark_sync(
            agent_factory,
            agent_name="PerfReviewer",
            agent_role="performance",
        )

        assert result is not None
        assert result.agent_name == "PerfReviewer"
        assert result.total_cases == 1

    def test_report_save_workflow(self):
        """测试：报告保存工作流"""
        result = BenchmarkResult(
            agent_name="TestAgent",
            agent_role="reviewer",
            config=BenchmarkConfig(n_runs=3),
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_cases=10,
            successful_cases=9,
            failed_cases=1,
            avg_recall=0.85,
            avg_precision=0.90,
            avg_f1=0.87,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = os.path.join(tmpdir, "report.md")
            html_path = os.path.join(tmpdir, "report.html")

            md_reporter = MDReporter()
            md_reporter.save(result, md_path)

            html_reporter = HTMLReporter()
            html_reporter.save(result, html_path)

            assert os.path.exists(md_path)
            assert os.path.exists(html_path)

            with open(md_path, "r", encoding="utf-8") as f:
                md_content = f.read()
            assert "智能体评测报告" in md_content

            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            assert "<!DOCTYPE html>" in html_content

    def test_load_all_test_cases(self):
        """测试：加载所有测试用例"""
        benchmark = ReviewerBenchmark()
        benchmark.load_test_cases()

        assert len(benchmark.test_cases) == 100

        categories = set(c.category for c in benchmark.test_cases)
        assert IssueCategory.SECURITY in categories
        assert IssueCategory.PERFORMANCE in categories
        assert IssueCategory.LOGIC in categories
        assert IssueCategory.STYLE in categories

    def test_load_specific_categories(self):
        """测试：加载特定类别测试用例"""
        benchmark = ReviewerBenchmark()
        benchmark.load_test_cases(
            categories=[IssueCategory.SECURITY, IssueCategory.LOGIC]
        )

        assert len(benchmark.test_cases) == 55

        categories = set(c.category for c in benchmark.test_cases)
        assert categories == {IssueCategory.SECURITY, IssueCategory.LOGIC}

    def test_benchmark_result_serialization(self):
        """测试：评测结果序列化"""
        result = BenchmarkResult(
            agent_name="TestAgent",
            agent_role="reviewer",
            config=BenchmarkConfig(n_runs=3, temperature=0.0, judge_model="qwen-max"),
            start_time=datetime(2026, 5, 16, 10, 0, 0),
            end_time=datetime(2026, 5, 16, 10, 5, 0),
            total_cases=10,
            successful_cases=9,
            failed_cases=1,
            avg_recall=0.85,
            avg_precision=0.90,
            avg_f1=0.87,
        )

        result_dict = result.to_dict()

        assert result_dict["agent_name"] == "TestAgent"
        assert result_dict["agent_role"] == "reviewer"
        assert result_dict["summary"]["total_cases"] == 10
        assert result_dict["summary"]["avg_recall"] == 0.85

    @pytest.mark.asyncio
    async def test_multiple_runs_stability(self):
        """测试：多次运行稳定性测试"""
        config = BenchmarkConfig(
            n_runs=3,
            categories=[IssueCategory.SECURITY],
            max_cases_per_category=1,
        )
        benchmark = ReviewerBenchmark(config=config)

        call_count = [0]

        def create_agent():
            mock_agent = MagicMock()
            mock_agent.name = "StableAgent"
            mock_agent.role = "security"
            mock_findings = MagicMock()
            mock_findings.findings = []
            mock_agent.review = AsyncMock(return_value=mock_findings)
            return mock_agent

        result = await benchmark.run_benchmark(
            create_agent,
            agent_name="StableAgent",
            agent_role="security",
        )

        assert result is not None
        assert result.total_cases == 1


class TestEvaluationMetrics:
    """评测指标集成测试"""

    def test_stability_metric_integration(self):
        """测试：稳定性指标集成"""
        from evaluation.metrics import StabilityMetric, StabilityResult

        metric = StabilityMetric(n_runs=3)

        results = [
            StabilityResult(findings=[{"title": "Issue 1"}]),
            StabilityResult(findings=[{"title": "Issue 1"}]),
            StabilityResult(findings=[{"title": "Issue 1"}]),
        ]

        score = metric.calculate_structural_consistency(results)
        assert score >= 0.0
        assert score <= 1.0

    def test_latency_metric_integration(self):
        """测试：延迟指标集成"""
        from evaluation.metrics import LatencyMetric, LatencyResult

        metric = LatencyMetric()

        for lat in [100, 150, 200, 250, 300]:
            metric.record(LatencyResult(
                start_time=0.0,
                end_time=lat / 1000.0,
                total_latency_ms=lat,
            ))

        percentiles = metric.calculate_percentiles()

        assert "p50" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles

    def test_tool_call_metric_integration(self):
        """测试：工具调用指标集成"""
        from evaluation.metrics import ToolCallMetric, ToolCallRecord

        metric = ToolCallMetric()

        trajectory = [
            ToolCallRecord(tool_name="git_diff", parameters={}, success=True),
            ToolCallRecord(tool_name="read_file", parameters={}, success=True),
            ToolCallRecord(tool_name="run_tests", parameters={}, success=False),
        ]

        analysis = metric.analyze(trajectory)

        assert analysis.total_calls == 3
        assert analysis.successful_calls == 2
        assert analysis.failed_calls == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
