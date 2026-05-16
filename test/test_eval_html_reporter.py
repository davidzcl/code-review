"""
验证评测报告 HTML 生成器

测试目标：
1. 正确生成 HTML 头部
2. 正确生成摘要区域
3. 正确生成指标区域
4. 正确生成详细结果
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from evaluation.reporter import HTMLReporter
from evaluation.benchmark import (
    BenchmarkResult,
    BenchmarkConfig,
    TestCaseResult,
)
from evaluation.datasets.schemas import IssueCategory


class TestHTMLReporter:
    """测试 HTMLReporter"""

    def test_init(self):
        """测试：初始化"""
        reporter = HTMLReporter(title="测试报告")

        assert reporter.title == "测试报告"

    def test_generate_html_header(self):
        """测试：生成 HTML 头部"""
        reporter = HTMLReporter()
        header = reporter._generate_html_header()

        assert "<!DOCTYPE html>" in header
        assert "<html" in header
        assert "<style>" in header
        assert "font-family" in header

    def test_generate_header_section(self):
        """测试：生成头部区域"""
        reporter = HTMLReporter()
        result = BenchmarkResult(
            agent_name="TestAgent",
            agent_role="reviewer",
            config=BenchmarkConfig(),
            start_time=datetime(2026, 5, 16, 10, 0, 0),
            end_time=datetime(2026, 5, 16, 10, 5, 0),
        )

        section = reporter._generate_header_section(result)

        assert "智能体评测报告" in section
        assert "TestAgent" in section
        assert "2026-05-16" in section

    def test_generate_summary_section(self):
        """测试：生成摘要区域"""
        reporter = HTMLReporter()
        result = BenchmarkResult(
            agent_name="TestAgent",
            agent_role="reviewer",
            config=BenchmarkConfig(),
            start_time=datetime.now(),
            total_cases=10,
            successful_cases=9,
            failed_cases=1,
        )

        section = reporter._generate_summary_section(result)

        assert "评测摘要" in section
        assert "10" in section
        assert "9" in section
        assert "90.0%" in section

    def test_generate_metrics_section(self):
        """测试：生成指标区域"""
        reporter = HTMLReporter()
        result = BenchmarkResult(
            agent_name="TestAgent",
            agent_role="reviewer",
            config=BenchmarkConfig(),
            start_time=datetime.now(),
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

        section = reporter._generate_metrics_section(result)

        assert "核心指标" in section
        assert "85.00%" in section
        assert "90.00%" in section
        assert "150.00ms" in section

    def test_generate_category_section(self):
        """测试：生成分类统计区域"""
        reporter = HTMLReporter()
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
            },
        )

        section = reporter._generate_category_section(result)

        assert "分类统计" in section
        assert "security" in section
        assert "80.00%" in section

    def test_generate_details_section(self):
        """测试：生成详细结果区域"""
        reporter = HTMLReporter()
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

        section = reporter._generate_details_section(result)

        assert "成功用例" in section
        assert "失败用例" in section
        assert "SEC-001" in section
        assert "SEC-002" in section

    def test_generate_full_report(self):
        """测试：生成完整报告"""
        reporter = HTMLReporter(title="测试报告")
        result = BenchmarkResult(
            agent_name="TestAgent",
            agent_role="reviewer",
            config=BenchmarkConfig(n_runs=3),
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

        assert "<!DOCTYPE html>" in report
        assert "</html>" in report
        assert "TestAgent" in report
        assert "评测摘要" in report
        assert "核心指标" in report

    def test_save_report(self, tmp_path):
        """测试：保存报告到文件"""
        reporter = HTMLReporter()
        result = BenchmarkResult(
            agent_name="TestAgent",
            agent_role="reviewer",
            config=BenchmarkConfig(),
            start_time=datetime.now(),
            total_cases=1,
            successful_cases=1,
            failed_cases=0,
        )

        file_path = str(tmp_path / "test_report.html")
        reporter.save(result, file_path)

        import os
        assert os.path.exists(file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "<!DOCTYPE html>" in content
        assert "TestAgent" in content


class TestGenerateHTMLReport:
    """测试便捷函数"""

    def test_generate_html_report(self):
        """测试：生成报告便捷函数"""
        from evaluation.reporter.html_reporter import generate_html_report

        result = BenchmarkResult(
            agent_name="TestAgent",
            agent_role="reviewer",
            config=BenchmarkConfig(),
            start_time=datetime.now(),
            total_cases=1,
            successful_cases=1,
            failed_cases=0,
        )

        report = generate_html_report(result, title="自定义报告")

        assert "<!DOCTYPE html>" in report
        assert "自定义报告" in report

    def test_generate_and_save(self, tmp_path):
        """测试：生成并保存报告"""
        from evaluation.reporter.html_reporter import generate_html_report

        result = BenchmarkResult(
            agent_name="TestAgent",
            agent_role="reviewer",
            config=BenchmarkConfig(),
            start_time=datetime.now(),
            total_cases=1,
            successful_cases=1,
            failed_cases=0,
        )

        file_path = str(tmp_path / "output_report.html")
        report = generate_html_report(result, output_path=file_path)

        import os
        assert os.path.exists(file_path)
        assert len(report) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
