"""
PR 评审智能代理系统 - 工具组件模块

包含 Git 只读操作、diff 解析、PR 解析、报告生成、日志、密钥扫描、
风险扫描、代码搜索等工具实现。
"""

from tools.tools import (
    git_diff,
    WorkspaceChange,
)
from tools.diff_parser import (
    parse_diff,
    DiffChunk,
    AddedLine,
)
from tools.pr_parser import (
    parse_pr_description,
    PRContext,
    PRParseError,
)
from tools.report_writer import (
    generate_report,
    write_report,
)
from tools.risk_scan import (
    scan_risk_signals,
    hotspot_analysis,
    RiskFinding,
    RiskScore,
)
from tools.secret_scanner import (
    scan_secrets,
    SecretFinding,
)
from tools.toolkit import (
    build_guardrail_toolkit,
    build_guardrail_context,
)

__all__ = [
    "git_diff",
    "WorkspaceChange",
    "parse_diff",
    "DiffChunk",
    "AddedLine",
    "parse_pr_description",
    "PRContext",
    "PRParseError",
    "generate_report",
    "write_report",
    "scan_risk_signals",
    "hotspot_analysis",
    "RiskFinding",
    "RiskScore",
    "scan_secrets",
    "SecretFinding",
    "build_guardrail_toolkit",
    "build_guardrail_context",
]