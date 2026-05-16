"""
评测报告 HTML 生成器

将 BenchmarkResult 转换为结构化的 HTML 报告，带样式美化。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from evaluation.benchmark import BenchmarkResult, TestCaseResult


class HTMLReporter:
    """HTML 报告生成器

    将评测结果转换为 HTML 格式的报告，包括：
    - 评测摘要
    - 分类统计
    - 详细测试用例结果
    - 交互式图表（可选）
    """

    def __init__(self, title: str = "智能体评测报告"):
        self.title = title

    def generate(self, result: BenchmarkResult) -> str:
        """生成 HTML 报告

        Args:
            result: 评测结果

        Returns:
            HTML 格式的报告字符串
        """
        sections = [
            self._generate_html_header(),
            self._generate_body(result),
            self._generate_html_footer(),
        ]

        return "\n".join(sections)

    def _generate_html_header(self) -> str:
        """生成 HTML 头部"""
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>智能体评测报告</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }
        .header p {
            opacity: 0.9;
        }
        .content {
            padding: 30px;
        }
        .section {
            margin-bottom: 30px;
        }
        .section-title {
            font-size: 1.5em;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .info-card {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid #667eea;
        }
        .info-card h3 {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 10px;
        }
        .info-card .value {
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }
        .metric-card {
            text-align: center;
        }
        .metric-card .value {
            color: #667eea;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f8f9fa;
            font-weight: 600;
            color: #333;
        }
        tr:hover {
            background-color: #f8f9fa;
        }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 500;
        }
        .badge-success {
            background-color: #d4edda;
            color: #155724;
        }
        .badge-danger {
            background-color: #f8d7da;
            color: #721c24;
        }
        .badge-warning {
            background-color: #fff3cd;
            color: #856404;
        }
        .progress-bar {
            width: 100%;
            height: 8px;
            background-color: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s ease;
        }
        .footer {
            background-color: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }
        .chart-container {
            margin: 20px 0;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 8px;
        }
    </style>
</head>"""

    def _generate_body(self, result: BenchmarkResult) -> str:
        """生成 HTML 主体"""
        sections = [
            self._generate_header_section(result),
            self._generate_summary_section(result),
            self._generate_metrics_section(result),
            self._generate_category_section(result),
            self._generate_details_section(result),
        ]

        return f"""<body>
    <div class="container">
        {"".join(sections)}
        {self._generate_footer_section()}
    </div>
</body>"""

    def _generate_header_section(self, result: BenchmarkResult) -> str:
        """生成头部区域"""
        duration = ""
        if result.end_time:
            duration = f" · 耗时 {(result.end_time - result.start_time).total_seconds():.2f}s"

        return f"""<div class="header">
    <h1>{self.title}</h1>
    <p>{result.agent_name} ({result.agent_role}) · {result.start_time.strftime('%Y-%m-%d %H:%M:%S')}{duration}</p>
</div>
<div class="content">"""

    def _generate_summary_section(self, result: BenchmarkResult) -> str:
        """生成摘要区域"""
        success_rate = result.successful_cases / result.total_cases * 100 if result.total_cases > 0 else 0

        return f"""<div class="section">
    <h2 class="section-title">📊 评测摘要</h2>
    <div class="info-grid">
        <div class="info-card">
            <h3>总用例数</h3>
            <div class="value">{result.total_cases}</div>
        </div>
        <div class="info-card">
            <h3>成功用例</h3>
            <div class="value" style="color: #28a745;">{result.successful_cases}</div>
        </div>
        <div class="info-card">
            <h3>失败用例</h3>
            <div class="value" style="color: #dc3545;">{result.failed_cases}</div>
        </div>
        <div class="info-card">
            <h3>成功率</h3>
            <div class="value">{success_rate:.1f}%</div>
            <div class="progress-bar" style="margin-top: 10px;">
                <div class="progress-fill" style="width: {success_rate}%;"></div>
            </div>
        </div>
    </div>
</div>"""

    def _generate_metrics_section(self, result: BenchmarkResult) -> str:
        """生成核心指标区域"""
        return f"""<div class="section">
    <h2 class="section-title">🎯 核心指标</h2>
    <div class="info-grid">
        <div class="info-card metric-card">
            <h3>平均召回率</h3>
            <div class="value">{result.avg_recall:.2%}</div>
        </div>
        <div class="info-card metric-card">
            <h3>平均精确率</h3>
            <div class="value">{result.avg_precision:.2%}</div>
        </div>
        <div class="info-card metric-card">
            <h3>平均 F1 分数</h3>
            <div class="value">{result.avg_f1:.2%}</div>
        </div>
        <div class="info-card metric-card">
            <h3>平均稳定性</h3>
            <div class="value">{result.avg_stability:.2%}</div>
        </div>
        <div class="info-card metric-card">
            <h3>工具调用成功率</h3>
            <div class="value">{result.avg_tool_success_rate:.2%}</div>
        </div>
        <div class="info-card metric-card">
            <h3>平均延迟</h3>
            <div class="value">{result.avg_latency_ms:.2f}ms</div>
        </div>
    </div>
    <div class="info-grid">
        <div class="info-card">
            <h3>延迟分布</h3>
            <table>
                <tr><th>百分位</th><th>延迟</th></tr>
                <tr><td>P50</td><td>{result.p50_latency_ms:.2f}ms</td></tr>
                <tr><td>P95</td><td>{result.p95_latency_ms:.2f}ms</td></tr>
                <tr><td>P99</td><td>{result.p99_latency_ms:.2f}ms</td></tr>
            </table>
        </div>
    </div>
</div>"""

    def _generate_category_section(self, result: BenchmarkResult) -> str:
        """生成分类统计区域"""
        if not result.category_results:
            return ""

        rows = []
        for category, stats in result.category_results.items():
            rows.append(f"""<tr>
    <td>{category}</td>
    <td>{stats['count']}</td>
    <td>{stats['avg_recall']:.2%}</td>
    <td>{stats['avg_precision']:.2%}</td>
    <td>{stats['avg_f1']:.2%}</td>
    <td>{stats['avg_latency_ms']:.2f}ms</td>
</tr>""")

        return f"""<div class="section">
    <h2 class="section-title">📁 分类统计</h2>
    <table>
        <thead>
            <tr>
                <th>类别</th>
                <th>用例数</th>
                <th>平均召回率</th>
                <th>平均精确率</th>
                <th>平均 F1</th>
                <th>平均延迟</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows)}
        </tbody>
    </table>
</div>"""

    def _generate_details_section(self, result: BenchmarkResult) -> str:
        """生成详细结果区域"""
        if not result.case_results:
            return ""

        successful_cases = [r for r in result.case_results if not r.error]
        failed_cases = [r for r in result.case_results if r.error]

        sections = []

        if successful_cases:
            rows = []
            for case in successful_cases[:20]:
                rows.append(f"""<tr>
    <td>{case.test_case_id}</td>
    <td>{case.test_case_name}</td>
    <td><span class="badge badge-success">{case.category.value}</span></td>
    <td>{case.difficulty}</td>
    <td>{case.finding_recall:.2%}</td>
    <td>{case.finding_precision:.2%}</td>
    <td>{case.finding_f1:.2%}</td>
    <td>{case.latency_ms:.2f}ms</td>
    <td>{case.stability_score:.2%}</td>
</tr>""")

            note = f"\n<p><em>仅显示前 20 条，共 {len(successful_cases)} 条成功用例</em></p>" if len(successful_cases) > 20 else ""

            sections.append(f"""<div class="section">
    <h2 class="section-title">✅ 成功用例</h2>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>名称</th>
                <th>类别</th>
                <th>难度</th>
                <th>召回率</th>
                <th>精确率</th>
                <th>F1</th>
                <th>延迟</th>
                <th>稳定性</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows)}
        </tbody>
    </table>
    {note}
</div>""")

        if failed_cases:
            rows = []
            for case in failed_cases:
                error_msg = case.error[:50] + "..." if case.error and len(case.error) > 50 else case.error
                rows.append(f"""<tr>
    <td>{case.test_case_id}</td>
    <td>{case.test_case_name}</td>
    <td><span class="badge badge-danger">{case.category.value}</span></td>
    <td>{error_msg}</td>
</tr>""")

            sections.append(f"""<div class="section">
    <h2 class="section-title">❌ 失败用例</h2>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>名称</th>
                <th>类别</th>
                <th>错误信息</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows)}
        </tbody>
    </table>
</div>""")

        return "".join(sections)

    def _generate_footer_section(self) -> str:
        """生成尾部区域"""
        return f"""</div>
<div class="footer">
    <p>报告由智能体评测系统自动生成 · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</div>"""

    def _generate_html_footer(self) -> str:
        """生成 HTML 尾部"""
        return "</html>"

    def save(self, result: BenchmarkResult, file_path: str) -> None:
        """保存报告到文件

        Args:
            result: 评测结果
            file_path: 文件路径
        """
        content = self.generate(result)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)


def generate_html_report(
    result: BenchmarkResult,
    title: str = "智能体评测报告",
    output_path: Optional[str] = None,
) -> str:
    """生成 HTML 报告的便捷函数

    Args:
        result: 评测结果
        title: 报告标题
        output_path: 输出文件路径（可选）

    Returns:
        HTML 格式的报告字符串
    """
    reporter = HTMLReporter(title=title)
    report = reporter.generate(result)

    if output_path:
        reporter.save(result, output_path)

    return report
