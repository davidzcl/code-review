"""
验证评测报告 MD 生成器

测试目标：
1. 正确生成报告头部
2. 正确生成评测摘要
3. 正确生成分类统计
4. 正确生成详细结果
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from evaluation.reporter import MDReporter
from evaluation.benchmark import (
    BenchmarkResult,
    BenchmarkConfig,
    TestCaseResult,
)
from evaluation.datasets.schemas import IssueCategory


class TestMDReporter:
    """测试 MDReporter"""

    def test_init(self):
        """测试：初始化"""
        reporter = MDReporter(title="测试报告")

        assert reporter.title == "测试报告"

    def test_generate_header(self):
        """测试：生成报告头部"""
        reporter = MDReporter()
        result = BenchmarkResult(
            agent_name="TestAgent",
            agent_role="reviewer",
            config=BenchmarkConfig(n_runs=3, temperature=0.0),
            start_time=datetime(2026, 5, 16, 10, 0, 0),
            end_time=datetime(2026, 5, 16, 10, 5, 0),
        )

        header = reporter._generate_header(result)

        assert "# 智能体评测报告" in header
        assert "TestAgent" in header
        assert "reviewer" in header
        assert "2026-05-16" in header

    def test_generate_summary(self):
        """测试：生成评测摘要"""
        reporter = MDReporter()
        result = BenchmarkResult(
            agent_name="TestAgent",
            agent_role="reviewer",
            config=BenchmarkConfig(n_runs=3),
            start_time=datetime.now(),
            total_cases=10,
            successful_cases=9,
            failed_cases=1,
            avg_recall=0.85,
            avg_precision=0.90,
            avg_f1=0.87,
            avg_latency_ms=150.0,
            p50_latency_ms=140.0,
            p95_latency_ms=200.0,
            p99_latency_ms=250.0,
            avg_stability=0.95,
            avg_tool_success_rate=0.98,
        )

        summary = reporter._generate_summary(result)

        assert "评测摘要" in summary
        assert "10" in summary
        assert "9" in summary
        assert "85.00%" in summary
        assert "90.00%" in summary
        assert "150.00ms" in summary

    def test_generate_category_results(self):
        """测试：生成分类统计"""
        reporter = MDReporter()
        result = BenchmarkResult(
            agent_name="TestAgent",
            agent_role="reviewer",
            config=BenchmarkConfig(),
            start_time=datetime.now(),
            category_results={
                "security": {
                    "count": 5,
                    "avg_recall": 0.80,
                    "avg_precision": 0.85,
                    "avg_f1": 0.82,
                    "avg_latency_ms": 120.0,
                },
                "performance": {
                    "count": 5,
                    "avg_recall": 0.90,
                    "avg_precision": 0.95,
                    "avg_f1": 0.92,
                    "avg_latency_ms": 180.0,
                },
            },
        )

        category_section = reporter._generate_category_results(result)

        assert "分类统计" in category_section
        assert "security" in category_section
        assert "performance" in category_section
        assert "80.00%" in category_section
        assert "90.00%" in category_section

    def test_generate_detailed_results(self):
        """测试：生成详细结果"""
        reporter = MDReporter()
        result = BenchmarkResult(
            agent_name="TestAgent",
            agent_role="reviewer",
            config=BenchmarkConfig(),
            start_time=datetime.now(),
            case_results=[
                TestCaseResult(
                    test_case_id="SEC-001",
                    test_case_name="SQL注入测试",
                    category=IssueCategory.SECURITY,
                    difficulty="easy",
                    finding_recall=0.8,
                    finding_precision=0.9,
                    finding_f1=0.85,
                    latency_ms=100.0,
                    stability_score=0.95,
                ),
                TestCaseResult(
                    test_case_id="SEC-002",
                    test_case_name="XSS测试",
                    category=IssueCategory.SECURITY,
                    difficulty="medium",
                    error="Timeout error",
                ),
            ],
        )

        detailed = reporter._generate_detailed_results(result)

        assert "详细测试用例结果" in detailed
        assert "成功用例" in detailed
        assert "失败用例" in detailed
        assert "SEC-001" in detailed
        assert "SEC-002" in detailed
        assert "Timeout error" in detailed

    def test_generate_full_report(self):
        """测试：生成完整报告"""
        reporter = MDReporter(title="测试报告")
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
            avg_latency_ms=150.0,
            p50_latency_ms=140.0,
            p95_latency_ms=200.0,
            p99_latency_ms=250.0,
            avg_stability=0.95,
            avg_tool_success_rate=0.98,
            category_results={
                "security": {
                    "count": 5,
                    "avg_recall": 0.80,
                    "avg_precision": 0.85,
                    "avg_f1": 0.82,
                    "avg_latency_ms": 120.0,
                },
            },
            case_results=[
                TestCaseResult(
                    test_case_id="SEC-001",
                    test_case_name="SQL注入测试",
                    category=IssueCategory.SECURITY,
                    difficulty="easy",
                    finding_recall=0.8,
                    finding_precision=0.9,
                    finding_f1=0.85,
                    latency_ms=100.0,
                    stability_score=0.95,
                ),
            ],
        )

        report = reporter.generate(result)

        assert "# 测试报告" in report
        assert "TestAgent" in report
        assert "评测摘要" in report
        assert "分类统计" in report
        assert "详细测试用例结果" in report
        assert "配置信息" in report

    def test_save_report(self, tmp_path):
        """测试：保存报告到文件"""
        reporter = MDReporter()
        result = BenchmarkResult(
            agent_name="TestAgent",
            agent_role="reviewer",
            config=BenchmarkConfig(),
            start_time=datetime.now(),
            total_cases=1,
            successful_cases=1,
            failed_cases=0,
        )

        file_path = str(tmp_path / "test_report.md")
        reporter.save(result, file_path)

        import os
        assert os.path.exists(file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "智能体评测报告" in content
        assert "TestAgent" in content


class TestGenerateBenchmarkReport:
    """测试便捷函数"""

    def test_generate_benchmark_report(self):
        """测试：生成报告便捷函数"""
        from evaluation.reporter.md_reporter import generate_benchmark_report

        result = BenchmarkResult(
            agent_name="TestAgent",
            agent_role="reviewer",
            config=BenchmarkConfig(),
            start_time=datetime.now(),
            total_cases=1,
            successful_cases=1,
            failed_cases=0,
        )

        report = generate_benchmark_report(result, title="自定义报告")

        assert "# 自定义报告" in report

    def test_generate_and_save(self, tmp_path):
        """测试：生成并保存报告"""
        from evaluation.reporter.md_reporter import generate_benchmark_report

        result = BenchmarkResult(
            agent_name="TestAgent",
            agent_role="reviewer",
            config=BenchmarkConfig(),
            start_time=datetime.now(),
            total_cases=1,
            successful_cases=1,
            failed_cases=0,
        )

        file_path = str(tmp_path / "output_report.md")
        report = generate_benchmark_report(result, output_path=file_path)

        import os
        assert os.path.exists(file_path)
        assert len(report) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
