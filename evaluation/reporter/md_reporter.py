"""
评测报告 Markdown 生成器

将 BenchmarkResult 转换为结构化的 Markdown 报告。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from evaluation.benchmark import BenchmarkResult, TestCaseResult


class MDReporter:
    """Markdown 报告生成器

    将评测结果转换为 Markdown 格式的报告，包括：
    - 评测摘要
    - 分类统计
    - 详细测试用例结果
    """

    def __init__(self, title: str = "智能体评测报告"):
        self.title = title

    def generate(self, result: BenchmarkResult) -> str:
        """生成 Markdown 报告

        Args:
            result: 评测结果

        Returns:
            Markdown 格式的报告字符串
        """
        sections = [
            self._generate_header(result),
            self._generate_summary(result),
            self._generate_category_results(result),
            self._generate_detailed_results(result),
            self._generate_footer(result),
        ]

        return "\n\n".join(sections)

    def _generate_header(self, result: BenchmarkResult) -> str:
        """生成报告头部"""
        lines = [
            f"# {self.title}",
            "",
            f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## 基本信息",
            "",
            f"| 项目 | 值 |",
            f"|------|-----|",
            f"| Agent 名称 | {result.agent_name} |",
            f"| Agent 角色 | {result.agent_role} |",
            f"| 评测时间 | {result.start_time.strftime('%Y-%m-%d %H:%M:%S')} |",
            f"| 运行次数 | {result.config.n_runs} |",
            f"| Temperature | {result.config.temperature} |",
            f"| Judge 模型 | {result.config.judge_model} |",
        ]

        if result.end_time:
            duration = (result.end_time - result.start_time).total_seconds()
            lines.append(f"| 持续时间 | {duration:.2f}s |")

        return "\n".join(lines)

    def _generate_summary(self, result: BenchmarkResult) -> str:
        """生成评测摘要"""
        lines = [
            "---",
            "",
            "## 评测摘要",
            "",
            "### 测试用例统计",
            "",
            f"| 指标 | 值 |",
            f"|------|-----|",
            f"| 总用例数 | {result.total_cases} |",
            f"| 成功用例数 | {result.successful_cases} |",
            f"| 失败用例数 | {result.failed_cases} |",
            f"| 成功率 | {result.successful_cases / result.total_cases * 100:.1f}% |" if result.total_cases > 0 else "| 成功率 | N/A |",
            "",
            "### 核心指标",
            "",
            f"| 指标 | 值 |",
            f"|------|-----|",
            f"| 平均召回率 | {result.avg_recall:.2%} |",
            f"| 平均精确率 | {result.avg_precision:.2%} |",
            f"| 平均 F1 分数 | {result.avg_f1:.2%} |",
            f"| 平均稳定性 | {result.avg_stability:.2%} |",
            f"| 工具调用成功率 | {result.avg_tool_success_rate:.2%} |",
            "",
            "### 响应延迟",
            "",
            f"| 指标 | 值 |",
            f"|------|-----|",
            f"| 平均延迟 | {result.avg_latency_ms:.2f}ms |",
            f"| P50 延迟 | {result.p50_latency_ms:.2f}ms |",
            f"| P95 延迟 | {result.p95_latency_ms:.2f}ms |",
            f"| P99 延迟 | {result.p99_latency_ms:.2f}ms |",
        ]

        return "\n".join(lines)

    def _generate_category_results(self, result: BenchmarkResult) -> str:
        """生成分类统计"""
        if not result.category_results:
            return ""

        lines = [
            "---",
            "",
            "## 分类统计",
            "",
            "| 类别 | 用例数 | 平均召回率 | 平均精确率 | 平均 F1 | 平均延迟 |",
            "|------|--------|------------|------------|---------|----------|",
        ]

        for category, stats in result.category_results.items():
            lines.append(
                f"| {category} | {stats['count']} | "
                f"{stats['avg_recall']:.2%} | "
                f"{stats['avg_precision']:.2%} | "
                f"{stats['avg_f1']:.2%} | "
                f"{stats['avg_latency_ms']:.2f}ms |"
            )

        return "\n".join(lines)

    def _generate_detailed_results(self, result: BenchmarkResult) -> str:
        """生成详细测试用例结果"""
        if not result.case_results:
            return ""

        lines = [
            "---",
            "",
            "## 详细测试用例结果",
            "",
        ]

        successful_cases = [r for r in result.case_results if not r.error]
        failed_cases = [r for r in result.case_results if r.error]

        if successful_cases:
            lines.extend([
                "### 成功用例",
                "",
                "| ID | 名称 | 类别 | 难度 | 召回率 | 精确率 | F1 | 延迟 | 稳定性 |",
                "|----|------|------|------|--------|--------|-----|------|--------|",
            ])

            for case in successful_cases[:20]:
                lines.append(
                    f"| {case.test_case_id} | {case.test_case_name} | "
                    f"{case.category.value} | {case.difficulty} | "
                    f"{case.finding_recall:.2%} | {case.finding_precision:.2%} | "
                    f"{case.finding_f1:.2%} | {case.latency_ms:.2f}ms | "
                    f"{case.stability_score:.2%} |"
                )

            if len(successful_cases) > 20:
                lines.append(f"\n> 仅显示前 20 条，共 {len(successful_cases)} 条成功用例")

        if failed_cases:
            lines.extend([
                "",
                "### 失败用例",
                "",
                "| ID | 名称 | 类别 | 错误信息 |",
                "|----|------|------|----------|",
            ])

            for case in failed_cases:
                error_msg = case.error[:50] + "..." if case.error and len(case.error) > 50 else case.error
                lines.append(
                    f"| {case.test_case_id} | {case.test_case_name} | "
                    f"{case.category.value} | {error_msg} |"
                )

        return "\n".join(lines)

    def _generate_footer(self, result: BenchmarkResult) -> str:
        """生成报告尾部"""
        lines = [
            "---",
            "",
            "## 配置信息",
            "",
            "```json",
            f"{result.to_dict()}",
            "```",
            "",
            "---",
            "",
            f"*报告由智能体评测系统自动生成*",
        ]

        return "\n".join(lines)

    def save(self, result: BenchmarkResult, file_path: str) -> None:
        """保存报告到文件

        Args:
            result: 评测结果
            file_path: 文件路径
        """
        content = self.generate(result)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)


def generate_benchmark_report(
    result: BenchmarkResult,
    title: str = "智能体评测报告",
    output_path: Optional[str] = None,
) -> str:
    """生成评测报告的便捷函数

    Args:
        result: 评测结果
        title: 报告标题
        output_path: 输出文件路径（可选）

    Returns:
        Markdown 格式的报告字符串
    """
    reporter = MDReporter(title=title)
    report = reporter.generate(result)

    if output_path:
        reporter.save(result, output_path)

    return report
