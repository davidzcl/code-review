"""
报告生成器

根据最终裁决结果和 PR 上下文生成格式化评审报告。
支持 Markdown / HTML / JSON 三种输出格式。
"""

from __future__ import annotations

import html as html_mod
import json
import os
from typing import Any, Dict, List, Optional

from agents.reviewer import Finding
from pipeline.verdict import Verdict
from pipeline.issue_merger import MergeRecord
from tools.pr_parser import PRContext
from logger import logger

_render_logger = logger.get_logger("report_writer")

_SEVERITY_ORDER = ["critical", "important", "minor"]
_SUPPORTED_FORMATS = {"markdown", "html", "json"}


def _escape_md(text: str) -> str:
    """转义 Markdown 特殊字符。"""
    chars = r"\`*_{}[]()#+-.!|"
    result = text
    for c in chars:
        result = result.replace(c, "\\" + c)
    return result


def _severity_label(severity: str) -> str:
    labels = {"critical": "🔴 Critical", "important": "🟡 Important", "minor": "🟢 Minor"}
    return labels.get(severity, severity)


def _build_overview(verdict: Verdict, pr_context: PRContext, diff_summary: str) -> str:
    """构建评审概览部分。"""
    lines: List[str] = []
    lines.append("## 评审概览")
    lines.append("")
    if pr_context.title:
        lines.append(f"- **PR 标题**: {_escape_md(pr_context.title)}")
    if pr_context.author:
        lines.append(f"- **作者**: {_escape_md(pr_context.author)}")
    if pr_context.head_branch or pr_context.base_branch:
        lines.append(f"- **分支**: {_escape_md(pr_context.head_branch or '')} → {_escape_md(pr_context.base_branch or '')}")
    total = len(verdict.findings)
    lines.append(f"- **发现数量**: {total} 个")
    severity_counts: Dict[str, int] = {}
    for f in verdict.findings:
        severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
    parts = []
    for s in _SEVERITY_ORDER:
        c = severity_counts.get(s, 0)
        if c:
            parts.append(f"{_severity_label(s)}: {c}")
    if parts:
        lines.append(f"- **严重级别分布**: {' | '.join(parts)}")
    if len(verdict.dismissed) > 0:
        lines.append(f"- **已驳回**: {len(verdict.dismissed)} 个")
    if len(verdict.merged) > 0:
        merged_count = sum(len(mr.merged_ids) for mr in verdict.merged)
        lines.append(f"- **已合并**: {merged_count} 个")
    if verdict.summary:
        lines.append(f"- **评审总结**: {verdict.summary}")
    return "\n".join(lines)


def _build_diff_summary(diff_summary: str) -> str:
    """构建变更摘要部分。"""
    lines: List[str] = []
    lines.append("## 变更摘要")
    lines.append("")
    lines.append(diff_summary or "（无变更摘要）")
    return "\n".join(lines)


def _build_findings(verdict: Verdict) -> str:
    """构建发现详情部分。"""
    lines: List[str] = []
    lines.append("## 发现详情")
    lines.append("")

    grouped: Dict[str, List[Finding]] = {}
    for f in verdict.findings:
        grouped.setdefault(f.severity, []).append(f)

    if not grouped:
        lines.append("未发现代码问题。")
        return "\n".join(lines)

    for severity in _SEVERITY_ORDER:
        findings = grouped.get(severity)
        if not findings:
            continue

        lines.append(f"### {_severity_label(severity)}")
        lines.append("")
        lines.append("| 文件 | 行 | 问题 | 建议 |")
        lines.append("|------|-----|------|------|")
        for f in findings:
            file_link = _escape_md(f.file_path) if f.file_path else "-"
            line_range = (
                f"{f.line_range[0]}-{f.line_range[1]}"
                if f.line_range and f.line_range != (0, 0)
                else "-"
            )
            title = _escape_md(f.title) if f.title else "-"
            suggestion = _escape_md(f.suggestion) if f.suggestion else "-"
            lines.append(f"| {file_link} | {line_range} | {title} | {suggestion} |")
        lines.append("")

    # Append dismissed
    if verdict.dismissed:
        lines.append("### 已驳回的问题")
        lines.append("")
        lines.append(f"以下 {len(verdict.dismissed)} 个发现在辩论中被驳回：")
        for did in verdict.dismissed:
            lines.append(f"- `{did}`")
        lines.append("")

    return "\n".join(lines)


def _generate_markdown(verdict: Verdict, pr_context: PRContext, diff_summary: str) -> str:
    """生成 Markdown 格式报告。"""
    parts: List[str] = []
    parts.append(f"# PR Review Report: {_escape_md(pr_context.title or '未命名')}")
    parts.append("")
    parts.append(_build_overview(verdict, pr_context, diff_summary))
    parts.append("")
    parts.append(_build_diff_summary(diff_summary))
    parts.append("")
    parts.append(_build_findings(verdict))
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("_由 PR Review Agent System 自动生成_")
    return "\n".join(parts)


def _generate_html(verdict: Verdict, pr_context: PRContext, diff_summary: str) -> str:
    """生成 HTML 格式报告。"""
    md = _generate_markdown(verdict, pr_context, diff_summary)
    html_lines: List[str] = []
    html_lines.append("<!DOCTYPE html>")
    html_lines.append('<html lang="zh-CN">')
    html_lines.append("<head>")
    html_lines.append('<meta charset="UTF-8">')
    html_lines.append("<title>PR Review Report</title>")
    html_lines.append("<style>")
    html_lines.append("body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:960px;margin:0 auto;padding:20px;line-height:1.6}")
    html_lines.append("h1{border-bottom:2px solid #eee;padding-bottom:10px}")
    html_lines.append("h2{margin-top:30px;border-bottom:1px solid #eee}")
    html_lines.append("table{border-collapse:collapse;width:100%;margin:10px 0}")
    html_lines.append("th,td{border:1px solid #ddd;padding:8px 12px;text-align:left}")
    html_lines.append("th{background:#f5f5f5;font-weight:600}")
    html_lines.append(".critical{color:#d32f2f}.important{color:#f57c00}.minor{color:#388e3c}")
    html_lines.append("</style>")
    html_lines.append("</head>")
    html_lines.append("<body>")
    html_lines.append(html_mod.escape(md))
    html_lines.append("</body>")
    html_lines.append("</html>")
    return "\n".join(html_lines)


def _generate_json(verdict: Verdict, pr_context: PRContext, diff_summary: str) -> str:
    """生成 JSON 格式报告。"""
    data: Dict[str, Any] = {
        "report": {
            "title": pr_context.title or "",
            "author": pr_context.author or "",
            "base_branch": pr_context.base_branch or "",
            "head_branch": pr_context.head_branch or "",
        },
        "verdict": {
            "summary": verdict.summary,
            "total_findings": len(verdict.findings),
            "dismissed": verdict.dismissed,
            "merged": [
                {
                    "primary_id": mr.primary_id,
                    "merged_ids": mr.merged_ids,
                    "reason": mr.merge_reason,
                }
                for mr in verdict.merged
            ],
            "findings": [
                {
                    "id": f.id,
                    "reviewer": f.reviewer,
                    "role": f.role,
                    "severity": f.severity,
                    "file_path": f.file_path,
                    "line_range": list(f.line_range) if f.line_range else None,
                    "title": f.title,
                    "description": f.description,
                    "suggestion": f.suggestion,
                    "confidence": f.confidence,
                    "evidence": f.evidence,
                }
                for f in verdict.findings
            ],
        },
        "diff_summary": diff_summary,
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def generate_report(
    verdict: Verdict,
    pr_context: PRContext,
    diff_summary: str = "",
    output_format: str = "markdown",
) -> str:
    """根据评审结果生成格式化报告。

    Args:
        verdict: 最终裁决结果。
        pr_context: PR 上下文信息。
        diff_summary: 代码变更摘要文本。
        output_format: 输出格式（"markdown" | "html" | "json"）。

    Returns:
        格式化后的报告字符串。

    Raises:
        ValueError: 不支持的输出格式。
    """
    fmt = output_format.lower().strip()
    if fmt not in _SUPPORTED_FORMATS:
        raise ValueError(
            f"不支持的输出格式: '{output_format}'，"
            f"有效值: {', '.join(_SUPPORTED_FORMATS)}"
        )

    _render_logger.info(
        "生成报告: format=%s findings=%d dismissed=%d",
        fmt, len(verdict.findings), len(verdict.dismissed),
    )

    if fmt == "markdown":
        return _generate_markdown(verdict, pr_context, diff_summary)
    elif fmt == "html":
        return _generate_html(verdict, pr_context, diff_summary)
    else:
        return _generate_json(verdict, pr_context, diff_summary)


def write_report(report_content: str, output_path: str) -> None:
    """将报告内容写入文件。

    自动创建不存在的父目录。

    Args:
        report_content: 报告内容字符串。
        output_path: 输出文件路径。
    """
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    _render_logger.info("报告已写入: %s (%d 字符)", output_path, len(report_content))