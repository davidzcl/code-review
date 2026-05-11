"""
前置 Guardrail 规则引擎

将 risk_scan 和 secret_scanner 封装为 AgentScope Toolkit 可注册的工具函数，
供 ReviewerAgent 在评审前调用，结果注入 sys_prompt。
"""

from typing import Any, Dict, List, Optional

from agentscope.message import TextBlock
from agentscope.tool import Toolkit, ToolResponse

from logger import logger
from tools.risk_scan import (
    RiskFinding,
    RiskScore,
    hotspot_analysis,
    scan_risk_signals,
)
from tools.secret_scanner import SecretFinding, scan_secrets
from tools.diff_parser import parse_diff

_toolkit_logger = logger.get_logger("tools.toolkit")


def _risk_findings_to_text(findings: List[RiskFinding], max_items: int = 20) -> str:
    """将 RiskFinding 列表格式化为文本。"""
    if not findings:
        return "（无）"
    lines = [f"  共 {len(findings)} 条风险信号（仅显示前 {max_items} 条）:"]
    for r in findings[:max_items]:
        lines.append(
            f"    [{r.risk_level}] {r.file_path}:{r.line} "
            f"[{r.category}/{r.signal}] {r.rationale}"
        )
    return "\n".join(lines)


def _secret_findings_to_text(findings: List[SecretFinding], max_items: int = 20) -> str:
    """将 SecretFinding 列表格式化为文本。"""
    if not findings:
        return "（无）"
    lines = [f"  共 {len(findings)} 条密钥扫描结果（仅显示前 {max_items} 条）:"]
    for s in findings[:max_items]:
        lines.append(
            f"    [{s.confidence:.0%}] {s.file_path}:{s.line} "
            f"[{s.rule_id}] {s.snippet}"
        )
    return "\n".join(lines)


def tool_scan_risk_signals(
    base: str = "",
    target: str = "",
    diff_text: str = "",
    cwd: Optional[str] = None,
) -> ToolResponse:
    """扫描代码变更中的风险信号。

    基于预定义规则（SQL 注入、命令注入、敏感信息泄露等）
    匹配 diff 中的新增代码行。

    Args:
        cwd: 执行目录（可选）。
        base: 基准分支/commit。
        target: 目标分支/commit。
        diff_text: 原始 diff 文本（提供此项则跳过 git 调用）。

    Returns:
        包含风险信号和测试缺口描述的工具响应。
    """
    _toolkit_logger.info("guardrail: scan_risk_signals base=%s target=%s", base, target)

    if not diff_text:
        from tools.tools import git_diff
        diff_text = git_diff(base, target, cwd=cwd)

    result = scan_risk_signals(base, target, cwd=cwd)

    signals = result.get("risk_signals", [])
    gaps = result.get("test_gaps", [])

    lines = [
        "## 前置 Guardrail 扫描结果",
        "",
        "### 风险信号",
        _risk_findings_to_text(signals),
        "",
        "### 测试覆盖缺口",
        _risk_findings_to_text(gaps),
    ]

    return ToolResponse(content=[TextBlock(type="text", text="\n".join(lines))])


def tool_scan_secrets(
    diff_text: str = "",
    file_path: str = "",
) -> ToolResponse:
    """扫描代码变更中的密钥泄露。

    基于正则规则匹配高置信度密钥模式（API Key、Token、Private Key 等），
    结果自动脱敏。

    Args:
        diff_text: 待扫描的 diff 文本。
        file_path: 文件路径（用于结果标记）。

    Returns:
        包含密钥扫描结果的工具响应。
    """
    _toolkit_logger.info("guardrail: scan_secrets")

    findings = scan_secrets(diff_text, file_path)

    lines = [
        "## 密钥扫描结果",
        "",
        _secret_findings_to_text(findings),
    ]

    return ToolResponse(content=[TextBlock(type="text", text="\n".join(lines))])


def _guardrail_prompt(
    risk_text: str,
    secret_text: str,
) -> str:
    """构建前置 Guardrail 提示词，注入 reviewer sys_prompt。"""
    return (
        "\n\n=== 前置 Guardrail 分析结果 ===\n"
        f"风险扫描:\n{risk_text}\n"
        f"密钥扫描:\n{secret_text}\n"
        "=============================="
    )


def build_guardrail_toolkit(
    register_risk: bool = True,
    register_secret: bool = True,
) -> Toolkit:
    """创建并返回预注册了 Guardrail 工具的 Toolkit 实例。

    Args:
        register_risk: 是否注册风险扫描工具。
        register_secret: 是否注册密钥扫描工具。

    Returns:
        包含 Guardrail 工具的 Toolkit 实例。
    """
    tk = Toolkit()

    if register_risk:
        tk.register_tool_function(
            tool_func=tool_scan_risk_signals,
            func_name="scan_risk_signals",
            func_description="扫描代码变更中的安全风险信号和测试覆盖缺口",
        )
        _toolkit_logger.info("已注册工具: scan_risk_signals")

    if register_secret:
        tk.register_tool_function(
            tool_func=tool_scan_secrets,
            func_name="scan_secrets",
            func_description="扫描代码变更中的密钥泄露",
        )
        _toolkit_logger.info("已注册工具: scan_secrets")
        
    tk.register_agent_skill(r"D:\project\code-review\skills\code-review")
    _toolkit_logger.info("已注册技能: code-review skill")

    return tk


def build_guardrail_context(
    diff_text: str,
    base: str = "",
    target: str = "",
    cwd: Optional[str] = None,
) -> str:
    """运行前置 Guardrail 分析并返回上下文文本。

    供外部直接调用，结果可注入 reviewer sys_prompt 或写入日志。

    Args:
        diff_text: 原始 diff 文本。
        cwd: 执行目录（可选）。
        base: 基准分支/commit。
        target: 目标分支/commit。

    Returns:
        格式化的 Guardrail 上下文文本。
    """
    risk_result = scan_risk_signals(base, target, cwd=cwd)
    secret_findings = scan_secrets(diff_text)

    risk_text = _risk_findings_to_text(risk_result.get("risk_signals", []))
    secret_text = _secret_findings_to_text(secret_findings)

    return _guardrail_prompt(risk_text, secret_text)