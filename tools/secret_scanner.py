"""
密钥扫描工具

主通道：正则匹配高置信度密钥模式（零外部依赖）
可选通道：detect-secrets 库（需 pip install detect-secrets）

所有密钥输出自动脱敏，密钥体替换为 ***。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple

from logger import logger

_scanner_logger = logger.get_logger("secret_scanner")


@dataclass
class SecretFinding:
    file_path: str
    line: int
    rule_id: str
    snippet: str
    confidence: float


PATTERNS: List[Tuple[str, str, float]] = [
    ("aws_access_key",       r'(?<![A-Z0-9])AKIA[0-9A-Z]{16}(?![A-Z0-9])',              0.95),
    ("aws_secret_key",       r'(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])',  0.60),
    ("github_token",         r'(?<![A-Za-z0-9])ghp_[A-Za-z0-9]{36}(?![A-Za-z0-9])',       0.95),
    ("github_pat_v2",        r'(?<![A-Za-z0-9])github_pat_[A-Za-z0-9_]{40,}(?![A-Za-z0-9])', 0.95),
    ("gitlab_token",         r'(?<![A-Za-z0-9])glpat-[A-Za-z0-9\-_]{20,}(?![A-Za-z0-9])', 0.95),
    ("ssh_private_key",      r'-----BEGIN (?:RSA|DSA|EC|OPENSSH) PRIVATE KEY-----',       0.98),
    ("slack_token",          r'(?<![A-Za-z0-9])xox[baprs]-[A-Za-z0-9\-]{10,}(?![A-Za-z0-9])', 0.90),
    ("jwt_token",            r'eyJ[A-Za-z0-9\-_]{20,}\.[A-Za-z0-9\-_]{20,}\.[A-Za-z0-9\-_]{10,}', 0.70),
    ("google_api_key",       r'(?<![A-Za-z0-9])AIza[0-9A-Za-z\-_]{35}(?![A-Za-z0-9])',   0.90),
    ("stripe_key",           r'(?<![A-Za-z0-9])(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{24,}(?![A-Za-z0-9])', 0.95),
    ("basic_auth_header",    r'Basic\s+[A-Za-z0-9+/=]{20,}',                              0.85),
    ("password_assignment",  r'(?i)(?:password|passwd|pwd|secret)\s*[:=]\s*[\'"][^\s]{8,}[\'"]', 0.50),
]


_COMPILED: List[Tuple[str, re.Pattern, float]] = [
    (rule_id, re.compile(pattern), conf) for rule_id, pattern, conf in PATTERNS
]


def _sanitize(text: str, match: re.Match) -> str:
    start, end = match.span()
    ctx_start = max(0, start - 8)
    ctx_end = min(len(text), end + 8)
    before = text[ctx_start:start]
    after = text[end:ctx_end]
    return f"{before}***{after}"


def scan_secrets(diff_text: str, file_path: str = "") -> List[SecretFinding]:
    """正则扫描文本中的疑似密钥

    Args:
        diff_text:  待扫描的文本内容（diff 输出或文件内容）
        file_path:  来源文件路径（用于结果标记）

    Returns:
        SecretFinding 列表，按行号升序排列
    """
    findings: List[SecretFinding] = []
    lines = diff_text.splitlines()

    for line_no, line in enumerate(lines, start=1):
        for rule_id, pattern, confidence in _COMPILED:
            for match in pattern.finditer(line):
                finding = SecretFinding(
                    file_path=file_path,
                    line=line_no,
                    rule_id=rule_id,
                    snippet=_sanitize(line, match),
                    confidence=confidence,
                )
                findings.append(finding)

                _scanner_logger.info(
                    "密钥扫描命中 | %s:%d | rule=%s | confidence=%.2f",
                    file_path or "<inline>",
                    line_no,
                    rule_id,
                    confidence,
                )

    return findings


def scan_secrets_detect_secrets(file_path: str) -> List[SecretFinding]:
    """通过 detect-secrets 库扫描文件

    Args:
        file_path: 文件路径

    Returns:
        SecretFinding 列表

    Raises:
        RuntimeError: detect-secrets 未安装时抛出
    """
    try:
        from detect_secrets import SecretsCollection  # type: ignore
        from detect_secrets.settings import default_settings
    except ImportError:
        raise RuntimeError(
            "detect-secrets 未安装，请执行: pip install detect-secrets"
        )

    secrets = SecretsCollection()
    with default_settings():
        secrets.scan_file(file_path)

    findings: List[SecretFinding] = []
    for secret in secrets:
        findings.append(SecretFinding(
            file_path=secret.filename,
            line=secret.line_number,
            rule_id=secret.type,
            snippet=f"***{secret.secret_hash[:8]}",
            confidence=1.0 if secret.is_verified else 0.8,
        ))

        _scanner_logger.info(
            "detect-secrets 命中 | %s:%d | type=%s | verified=%s",
            secret.filename,
            secret.line_number,
            secret.type,
            secret.is_verified,
        )

    return findings
