"""
风险分析工具

检测 PR 中新增代码行的潜在风险信号：
- hotspot_analysis: 基于路径关键词的风险评分
- static_analysis:  语言特定的静态分析
- scan_risk_signals: 基于 diff 新增行的风险信号检测（SQL 注入/命令注入/敏感信息泄露/
                     签名验证问题/正确性问题）+ 测试覆盖检查

scan_risk_signals 流程：
  git_diff → 解析新增行 → 逐行匹配风险规则 → 测试覆盖检查 → 返回风险列表
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Pattern, Tuple

from logger import logger
from tools.tools import git_diff
from tools.diff_parser import get_added_lines, get_changed_files as get_changed_files_from_diff, AddedLine

_risk_logger = logger.get_logger("risk_scan")


# ════════════════════════════════════════════════════════════════
# 数据模型
# ════════════════════════════════════════════════════════════════


@dataclass
class RiskScore:
    file_path: str
    risk_level: str
    reasons: List[str] = field(default_factory=list)


@dataclass
class RiskFinding:
    file_path: str
    line: int
    category: str
    signal: str
    evidence: str
    rationale: str
    risk_level: str


# ════════════════════════════════════════════════════════════════
# 风险规则定义
# ════════════════════════════════════════════════════════════════

RiskRule = Tuple[str, str, Pattern, str, str]

RISK_RULES: List[RiskRule] = [
    # ── SQL Injection ──
    ("sql_injection", "raw_sql_concat",
     re.compile(r'(?:execute|executemany|exec)\s*\([^)]*\+'),
     "SQL 语句使用字符串拼接参数，可能导致 SQL 注入漏洞", "critical"),

    ("sql_injection", "fstring_in_sql",
     re.compile(r'(?:execute|executemany|exec)\s*\(\s*f["\']'),
     "SQL 语句使用 f-string 嵌入变量，可能导致 SQL 注入漏洞", "critical"),

    # ── Command Injection ──
    ("command_injection", "shell_true",
     re.compile(r'(?:subprocess\.\w+|os\.system|os\.popen)\s*\([^)]*shell\s*=\s*(?:True|1)\b', re.IGNORECASE),
     "shell=True 开启 shell 注入攻击面，建议传参数列表而非字符串", "critical"),

    ("command_injection", "eval_exec_usage",
     re.compile(r'\b(?:eval|exec)\s*\('),
     "eval/exec 可执行任意代码，存在严重安全风险，应严格避免或消毒输入", "critical"),

    # ── Sensitive Information Leakage ──
    ("sensitive_info", "leak_to_log",
     re.compile(r'(?:print|log(?:ger)?\.(?:info|debug|warning|error))\s*\([^)]*(?:password|secret|token|api_?key|credential)', re.IGNORECASE),
     "敏感信息（password/secret/token）可能被输出到日志或控制台", "important"),

    # ── Signature Verification ──
    ("signature_verify", "disabled_verify",
     re.compile(r'verify\s*=\s*(?:False|0)\b'),
     "证书验证被禁用，通信可能被中间人攻击", "critical"),

    ("signature_verify", "disabled_hostname_check",
     re.compile(r'check_hostname\s*=\s*(?:False|0)\b'),
     "主机名验证被禁用，通信可能被中间人攻击", "critical"),

    # ── Correctness ──
    ("correctness", "mutable_default_arg",
     re.compile(r'def \w+\([^)]*=\s*(?:\[\]|\{\}|set\(\))'),
     "可变默认参数（list/dict/set）在多次调用间共享同一对象，可能导致状态泄漏", "important"),

    ("correctness", "negative_amount",
     re.compile(r'(?:amount|price|total|balance|value)\s*=\s*-\d+', re.IGNORECASE),
     "硬编码负值金额/余额字段，请确认是否为逻辑错误", "important"),

    ("correctness", "bypass_approval",
     re.compile(r'(?:auto_approve|auto_merge|skip_review|bypass_check)\s*=\s*(?:True|1)\b', re.IGNORECASE),
     "绕过了审批/审查流程，需要人工确认是否合规", "important"),
]


# ════════════════════════════════════════════════════════════════
# 高风险文件路径模式（用于 hotspot_analysis）
# ════════════════════════════════════════════════════════════════

HIGH_RISK_PATTERNS: Dict[str, List[str]] = {
    "authentication":      ["auth", "login", "session", "token", "jwt", "oauth"],
    "authorization":       ["permission", "rbac", "acl", "access_control", "middleware"],
    "data_persistence":    ["database", "migration", "schema", "model", "repository", "orm", "sql"],
    "payment":             ["payment", "billing", "invoice", "checkout", "stripe", "paypal"],
    "crypto":              ["crypto", "encrypt", "decrypt", "hash", "cipher", "ssl", "tls", "certificate"],
    "config_and_secret":   ["config", "settings", "secret", "credential", ".env", "environment"],
    "ci_cd":               [".github/workflows", "Jenkinsfile", ".gitlab-ci", "Dockerfile", "docker-compose"],
    "networking":          ["socket", "network", "proxy", "firewall", "port", "http", "api", "endpoint"],
}


# ════════════════════════════════════════════════════════════════
# 测试文件识别模式
# ════════════════════════════════════════════════════════════════

_TEST_FILE_PATTERNS: List[Pattern] = [
    re.compile(r'test_'),
    re.compile(r'_test\.'),
    re.compile(r'/tests?/'),
]


# ════════════════════════════════════════════════════════════════
# 内部实现
# ════════════════════════════════════════════════════════════════


def _parse_diff_added_lines(diff_text: str) -> List[RiskFinding]:
    """从 unified diff 中提取新增代码行（委托 diff_parser.get_added_lines）。"""
    findings: List[RiskFinding] = []
    for al in get_added_lines(diff_text):
        findings.append(RiskFinding(
            file_path=al.file_path,
            line=al.line,
            category="",
            signal="",
            evidence=al.content,
            rationale="",
            risk_level="",
        ))
    return findings


def _match_rules(added_lines: List[RiskFinding]) -> List[RiskFinding]:
    """将新增行与风险规则匹配，产生风险信号。"""
    results: List[RiskFinding] = []

    for entry in added_lines:
        for category, signal, pattern, rationale, risk_level in RISK_RULES:
            if pattern.search(entry.evidence):
                _risk_logger.info(
                    "风险信号 | %s:%d | %s/%s | %s",
                    entry.file_path, entry.line, category, signal,
                    entry.evidence.strip()[:80],
                )
                results.append(RiskFinding(
                    file_path=entry.file_path,
                    line=entry.line,
                    category=category,
                    signal=signal,
                    evidence=entry.evidence,
                    rationale=rationale,
                    risk_level=risk_level,
                ))
                break

    return results


def _scan_empty_except(added_lines: List[RiskFinding]) -> List[RiskFinding]:
    """跨行检测空的异常处理块（except ...: 后紧跟 pass）。"""
    results: List[RiskFinding] = []
    single_except = re.compile(r'except\s+\w+\s*:\s*$|except\s*:\s*$')

    for i, entry in enumerate(added_lines):
        if not single_except.search(entry.evidence):
            continue
        for j in range(i + 1, min(i + 5, len(added_lines))):
            next_content = added_lines[j].evidence.strip()
            if next_content == "pass":
                _risk_logger.info(
                    "风险信号 | %s:%d | correctness/empty_except | %s",
                    entry.file_path, entry.line, entry.evidence.strip(),
                )
                results.append(RiskFinding(
                    file_path=entry.file_path,
                    line=entry.line,
                    category="correctness",
                    signal="empty_except",
                    evidence=entry.evidence + "\n" + added_lines[j].evidence,
                    rationale="空的异常处理块会静默吞掉所有错误，应至少记录日志",
                    risk_level="important",
                ))
                break
            elif next_content and not next_content.startswith("#"):
                break

    return results


def _is_test_file(file_path: str) -> bool:
    path = file_path.lower().replace("\\", "/")
    return any(p.search(path) for p in _TEST_FILE_PATTERNS)


def _find_matching_test(source_file: str, changed_files: List[str]) -> Optional[str]:
    """查找 source_file 对应的测试文件。"""
    base = os.path.splitext(source_file)[0]
    stem = os.path.basename(base)
    dir_part = os.path.dirname(base).replace("\\", "/")

    candidates = [
        f"{dir_part}/test_{stem}.py",
        f"{dir_part}/{stem}_test.py",
        f"tests/test_{stem}.py",
        f"tests/{stem}_test.py",
    ]

    for cf in changed_files:
        cf_norm = cf.replace("\\", "/").lower()
        for candidate in candidates:
            if cf_norm == candidate.lower():
                return cf
    return None


def _check_test_coverage(
    changed_files: List[str],
    risk_signals: Optional[List[RiskFinding]] = None,
) -> List[RiskFinding]:
    """检查高风险源文件是否有对应测试变更。"""
    source_files_with_risk: set = set()

    if risk_signals:
        for r in risk_signals:
            if r.risk_level in ("critical", "important"):
                source_files_with_risk.add(r.file_path.replace("\\", "/").lower())

    test_gaps: List[RiskFinding] = []
    tracked: set = set()

    for src_file in changed_files:
        src_norm = src_file.replace("\\", "/").lower()
        if src_norm in tracked:
            continue
        if _is_test_file(src_norm):
            continue
        if source_files_with_risk and src_norm not in source_files_with_risk:
            continue

        match = _find_matching_test(src_file, changed_files)
        if match is None:
            test_gaps.append(RiskFinding(
                file_path=src_file,
                line=0,
                category="test_coverage",
                signal="missing_test",
                evidence="",
                rationale=f"文件 {src_file} 发生变更但未发现对应的测试文件变更，建议补充测试",
                risk_level="minor",
            ))
            _risk_logger.info("测试缺失 | %s | 无对应测试文件", src_file)

        tracked.add(src_norm)

    return test_gaps


# ════════════════════════════════════════════════════════════════
# 公共 API
# ════════════════════════════════════════════════════════════════


def hotspot_analysis(changed_files: List[str]) -> List[RiskScore]:
    """分析变更文件的风险等级

    基于预定义的高风险路径关键词规则匹配，
    命中 1 个类别标记为 medium，命中 ≥2 个类别标记为 high。

    Args:
        changed_files: 变更文件路径列表

    Returns:
        每个文件对应的 RiskScore 列表
    """
    results: List[RiskScore] = []

    for file_path in changed_files:
        path_lower = file_path.lower().replace("\\", "/")
        matched_categories: List[str] = []

        for category, keywords in HIGH_RISK_PATTERNS.items():
            for kw in keywords:
                if kw in path_lower:
                    matched_categories.append(category)
                    break

        if matched_categories:
            severity = "high" if len(matched_categories) >= 2 else "medium"
            reasons = [
                f"命中高风险类别: {cat}" for cat in sorted(matched_categories)
            ]
        else:
            severity = "low"
            reasons = []

        results.append(RiskScore(
            file_path=file_path,
            risk_level=severity,
            reasons=reasons,
        ))

        _risk_logger.debug(
            "风险扫描 | %s | level=%s | categories=%s",
            file_path,
            severity,
            ",".join(matched_categories) if matched_categories else "none",
        )

    return results


_LINTER_COMMANDS: Dict[str, str] = {
    ".py": "ruff check --format=concise {file}",
    ".js": "eslint --format=compact {file}",
    ".ts": "eslint --format=compact {file}",
    ".tsx": "eslint --format=compact {file}",
    ".jsx": "eslint --format=compact {file}",
}


def static_analysis(
    file_path: str,
    language: Optional[str] = None,
    cwd: Optional[str] = None,
) -> List[dict]:
    """语言特定的静态分析

    根据文件扩展名自动选择 linter 并执行。
    当前支持: .py → ruff, .js/.ts/.tsx/.jsx → eslint

    Args:
        file_path:  待分析文件路径
        language:   语言标识（预留扩展），None 时根据扩展名推断
        cwd:        工作目录

    Returns:
        分析结果列表，每条含 file / line / message / severity

    Raises:
        NotImplementedError: 不支持的扩展名
        RuntimeError: linter 命令执行失败
    """
    ext = os.path.splitext(file_path)[1].lower()
    command_template = _LINTER_COMMANDS.get(ext)

    if not command_template:
        _risk_logger.warning("不支持的静态分析类型: %s", ext)
        raise NotImplementedError(f"不支持的静态分析类型: {ext}")

    command = command_template.format(file=file_path)
    _risk_logger.info("执行静态分析: %s", command)

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=cwd or os.getcwd(),
            encoding="utf-8",
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"静态分析超时: {command}")
    except Exception as e:
        raise RuntimeError(f"静态分析执行失败: {e}")

    issues: List[dict] = []
    for output_line in result.stdout.splitlines():
        output_line = output_line.strip()
        if not output_line:
            continue
        issues.append({
            "file": file_path,
            "raw": output_line,
        })

    if result.stderr.strip():
        _risk_logger.warning(
            "静态分析 stderr: %s", result.stderr.strip()[:500]
        )

    return issues


def scan_risk_signals(
    base: Optional[str] = None,
    target: Optional[str] = None,
    cwd: Optional[str] = None,
) -> Dict[str, List[RiskFinding]]:
    """扫描 diff 中的风险信号和测试覆盖缺口。

    流程：
      1. git_diff 获取 PR diff
      2. 解析新增代码行（含行号）
      3. 逐行匹配风险规则（SQL 注入/命令注入/敏感信息泄露等）
      4. 跨行扫描空的异常处理块
      5. 检查高风险文件的测试覆盖

    Args:
        base:  基准分支/commit
        target: 目标分支/commit
        cwd: 执行目录（可选）。

    Returns:
        {
            "risk_signals": [...],   # 匹配到风险规则的新增行
            "test_gaps": [...],      # 高风险文件缺少对应测试
        }
    """
    _risk_logger.info("开始风险扫描 base=%s target=%s", base, target)

    diff_text = git_diff(base, target, cwd=cwd)
    added_lines = _parse_diff_added_lines(diff_text)
    _risk_logger.info("解析新增行: %d 行", len(added_lines))

    risk_signals = _match_rules(added_lines)
    risk_signals.extend(_scan_empty_except(added_lines))

    changed_file_list = get_changed_files_from_diff(diff_text)
    test_gaps = _check_test_coverage(changed_file_list, risk_signals)

    _risk_logger.info(
        "风险扫描完成: %d 个风险信号, %d 个测试缺口",
        len(risk_signals), len(test_gaps),
    )

    return {
        "risk_signals": risk_signals,
        "test_gaps": test_gaps,
    }
