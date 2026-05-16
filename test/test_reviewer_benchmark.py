"""
验证 ReviewerBenchmark 实现

测试目标：
1. 正确初始化 Benchmark
2. 正确加载测试用例
3. 正确运行评测
4. 正确计算指标
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from evaluation.benchmark import (
    ReviewerBenchmark,
    BenchmarkConfig,
    BenchmarkResult,
    TestCaseResult,
)
from evaluation.datasets.schemas import (
    SyntheticTestCase,
    DiffChunkSchema,
    InjectedIssue,
    IssueCategory,
)


class TestBenchmarkConfig:
    """测试 BenchmarkConfig"""

    def test_default_config(self):
        """测试：默认配置"""
        config = BenchmarkConfig()

        assert config.n_runs == 3
        assert config.temperature == 0.0
        assert config.categories is None
        assert config.max_cases_per_category is None
        assert config.judge_model == "qwen-max"
        assert config.timeout_seconds == 60

    def test_custom_config(self):
        """测试：自定义配置"""
        config = BenchmarkConfig(
            n_runs=5,
            temperature=0.1,
            categories=[IssueCategory.SECURITY],
            max_cases_per_category=10,
            judge_model="gpt-4",
            timeout_seconds=120,
        )

        assert config.n_runs == 5
        assert config.temperature == 0.1
        assert config.categories == [IssueCategory.SECURITY]
        assert config.max_cases_per_category == 10
        assert config.judge_model == "gpt-4"
        assert config.timeout_seconds == 120


class TestTestCaseResult:
    """测试 TestCaseResult"""

    def test_default_result(self):
        """测试：默认结果"""
        result = TestCaseResult(
            test_case_id="TEST-001",
            test_case_name="测试用例",
            category=IssueCategory.SECURITY,
            difficulty="easy",
        )

        assert result.test_case_id == "TEST-001"
        assert result.finding_recall == 0.0
        assert result.finding_precision == 0.0
        assert result.finding_f1 == 0.0
        assert result.error is None

    def test_result_with_values(self):
        """测试：带值的结果"""
        result = TestCaseResult(
            test_case_id="TEST-001",
            test_case_name="测试用例",
            category=IssueCategory.SECURITY,
            difficulty="easy",
            finding_recall=0.8,
            finding_precision=0.9,
            finding_f1=0.85,
            latency_ms=150.0,
            stability_score=0.95,
        )

        assert result.finding_recall == 0.8
        assert result.finding_precision == 0.9
        assert result.finding_f1 == 0.85
        assert result.latency_ms == 150.0
        assert result.stability_score == 0.95


class TestBenchmarkResult:
    """测试 BenchmarkResult"""

    def test_to_dict(self):
        """测试：转换为字典"""
        config = BenchmarkConfig(n_runs=3)
        result = BenchmarkResult(
            agent_name="TestAgent",
            agent_role="reviewer",
            config=config,
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
        assert result_dict["summary"]["avg_precision"] == 0.90
        assert result_dict["summary"]["avg_f1"] == 0.87


class TestReviewerBenchmark:
    """测试 ReviewerBenchmark"""

    def test_init_default(self):
        """测试：默认初始化"""
        benchmark = ReviewerBenchmark()

        assert benchmark.config.n_runs == 3
        assert benchmark.test_cases == []
        assert benchmark.stability_metric is not None
        assert benchmark.latency_metric is not None
        assert benchmark.tool_metric is not None
        assert benchmark.finding_judge is not None

    def test_init_with_config(self):
        """测试：带配置初始化"""
        config = BenchmarkConfig(n_runs=5, temperature=0.1)
        benchmark = ReviewerBenchmark(config=config)

        assert benchmark.config.n_runs == 5
        assert benchmark.config.temperature == 0.1

    def test_load_test_cases_all(self):
        """测试：加载所有测试用例"""
        benchmark = ReviewerBenchmark()
        benchmark.load_test_cases()

        assert len(benchmark.test_cases) > 0
        assert len(benchmark.test_cases) == 100

    def test_load_test_cases_single_category(self):
        """测试：加载单个类别测试用例"""
        benchmark = ReviewerBenchmark()
        benchmark.load_test_cases(categories=[IssueCategory.SECURITY])

        assert len(benchmark.test_cases) == 30
        assert all(c.category == IssueCategory.SECURITY for c in benchmark.test_cases)

    def test_load_test_cases_with_limit(self):
        """测试：限制每类数量"""
        benchmark = ReviewerBenchmark()
        benchmark.load_test_cases(max_per_category=5)

        assert len(benchmark.test_cases) == 20

    @pytest.mark.asyncio
    async def test_run_single_case(self):
        """测试：运行单个测试用例"""
        test_case = SyntheticTestCase(
            id="TEST-001",
            name="测试用例",
            category=IssueCategory.SECURITY,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="test.py",
                    language="python",
                    old_start=1,
                    old_count=1,
                    new_start=1,
                    new_count=2,
                    additions=["print('hello')"],
                    context="测试上下文",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="high",
                    title="测试问题",
                    description="这是一个测试问题描述",
                    file_path="test.py",
                    line_range=(1, 5),
                    detection_hints=["test"],
                )
            ],
        )

        benchmark = ReviewerBenchmark(config=BenchmarkConfig(n_runs=1))

        mock_agent = MagicMock()
        mock_agent.name = "TestAgent"
        mock_agent.role = "security"
        mock_findings = MagicMock()
        mock_findings.findings = []
        mock_agent.review = AsyncMock(return_value=mock_findings)

        agent_factory = lambda: mock_agent

        result = await benchmark.run_single_case(test_case, agent_factory)

        assert result.test_case_id == "TEST-001"
        assert result.category == IssueCategory.SECURITY
        assert result.error is None

    @pytest.mark.asyncio
    async def test_run_benchmark(self):
        """测试：运行完整评测"""
        config = BenchmarkConfig(
            n_runs=1,
            categories=[IssueCategory.SECURITY],
            max_cases_per_category=2,
        )
        benchmark = ReviewerBenchmark(config=config)

        mock_agent = MagicMock()
        mock_agent.name = "TestAgent"
        mock_agent.role = "security"
        mock_findings = MagicMock()
        mock_findings.findings = []
        mock_agent.review = AsyncMock(return_value=mock_findings)

        agent_factory = lambda: mock_agent

        result = await benchmark.run_benchmark(
            agent_factory,
            agent_name="TestAgent",
            agent_role="security",
        )

        assert result.agent_name == "TestAgent"
        assert result.agent_role == "security"
        assert result.total_cases == 2
        assert result.successful_cases == 2
        assert result.failed_cases == 0
        assert result.end_time is not None

    def test_run_benchmark_sync(self):
        """测试：同步运行评测"""
        config = BenchmarkConfig(
            n_runs=1,
            categories=[IssueCategory.SECURITY],
            max_cases_per_category=1,
        )
        benchmark = ReviewerBenchmark(config=config)

        mock_agent = MagicMock()
        mock_agent.name = "TestAgent"
        mock_agent.role = "security"
        mock_findings = MagicMock()
        mock_findings.findings = []
        mock_agent.review = AsyncMock(return_value=mock_findings)

        agent_factory = lambda: mock_agent

        result = benchmark.run_benchmark_sync(
            agent_factory,
            agent_name="TestAgent",
            agent_role="security",
        )

        assert result.agent_name == "TestAgent"
        assert result.total_cases == 1


class TestBenchmarkMetrics:
    """测试评测指标计算"""

    def test_category_results(self):
        """测试：分类结果统计"""
        config = BenchmarkConfig(n_runs=1)
        result = BenchmarkResult(
            agent_name="TestAgent",
            agent_role="reviewer",
            config=config,
            start_time=datetime.now(),
        )

        result.case_results = [
            TestCaseResult(
                test_case_id="SEC-001",
                test_case_name="安全测试",
                category=IssueCategory.SECURITY,
                difficulty="easy",
                finding_recall=0.8,
                finding_precision=0.9,
                finding_f1=0.85,
                latency_ms=100.0,
            ),
            TestCaseResult(
                test_case_id="SEC-002",
                test_case_name="安全测试2",
                category=IssueCategory.SECURITY,
                difficulty="medium",
                finding_recall=0.7,
                finding_precision=0.8,
                finding_f1=0.75,
                latency_ms=150.0,
            ),
        ]

        result.successful_cases = 2
        result.avg_recall = 0.75
        result.avg_precision = 0.85
        result.avg_f1 = 0.80

        assert len(result.case_results) == 2
        assert result.avg_recall == 0.75

    def test_latency_percentiles(self):
        """测试：延迟百分位数"""
        from evaluation.metrics import LatencyMetric, LatencyResult

        metric = LatencyMetric()

        for lat in [100, 150, 200, 250, 300, 350, 400, 450, 500, 1000]:
            metric.record(LatencyResult(
                start_time=0.0,
                end_time=lat / 1000.0,
                total_latency_ms=lat,
            ))

        percentiles = metric.calculate_percentiles()

        assert "p50" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles
        assert 300 <= percentiles["p50"] <= 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
