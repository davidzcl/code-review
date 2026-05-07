"""
风险分析工具

提供基于规则的风险扫描能力：
- hotspot_analysis: 零外部依赖，基于路径关键词匹配的风险评分
- static_analysis:  语言特定的静态分析（P3 阶段实现，当前为 stub）
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from logger import logger

_risk_logger = logger.get_logger("risk_scan")


@dataclass
class RiskScore:
    file_path: str
    risk_level: str
    reasons: List[str] = field(default_factory=list)


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
