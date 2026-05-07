"""
安全测试执行工具

提供 run_tests 功能，内置危险操作检测机制。
检测到危险命令时立即阻止执行并记录安全日志。
"""

from __future__ import annotations

import getpass
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from logger import logger

_DANGER_PATTERNS: List[str] = [
    "rm -rf",
    "git reset",
    "git checkout",
    "shutdown",
    "reboot",
    "sudo ",
]

_test_logger = logger.get_logger("test_runner")


@dataclass
class RunTestResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int
    blocked: bool = False
    block_reason: str = ""


@dataclass
class DangerLogEntry:
    timestamp: str
    command: str
    user: str
    blocked: bool
    reason: str


def _detect_danger(command: str) -> Optional[str]:
    """检测命令中是否包含危险操作

    Args:
        command: 待执行的命令字符串

    Returns:
        命中危险模式的描述，无危险则返回 None
    """
    command_lower = command.lower()
    for pattern in _DANGER_PATTERNS:
        if pattern in command_lower:
            return f"检测到危险命令模式: '{pattern}'"
    return None


def _record_danger_log(entry: DangerLogEntry) -> None:
    """记录危险操作尝试到日志"""
    _test_logger.warning(
        "危险操作尝试 | 时间: %s | 用户: %s | 命令: %s | 已阻止: %s | 原因: %s",
        entry.timestamp,
        entry.user,
        entry.command,
        str(entry.blocked),
        entry.reason,
    )


def run_tests(
    command: str,
    cwd: Optional[str] = None,
    timeout: int = 300,
    env_vars: Optional[dict] = None,
) -> RunTestResult:
    """安全执行测试命令

    内置危险命令检测，阻止 rm -rf / git reset / git checkout / shutdown / reboot / sudo 等操作。

    Args:
        command:  测试命令字符串
        cwd:      执行目录，默认当前工作目录
        timeout:  超时秒数，默认 300s
        env_vars: 附加环境变量

    Returns:
        RunTestResult 包含执行结果和阻止信息
    """
    danger_reason = _detect_danger(command)
    if danger_reason is not None:
        entry = DangerLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            command=command,
            user=getpass.getuser(),
            blocked=True,
            reason=danger_reason,
        )
        _record_danger_log(entry)
        return RunTestResult(
            success=False,
            stdout="",
            stderr="",
            return_code=-1,
            blocked=True,
            block_reason=danger_reason,
        )

    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or os.getcwd(),
            env=env,
            encoding="utf-8",
        )
    except subprocess.TimeoutExpired:
        _test_logger.error("测试执行超时 | 命令: %s | 超时: %ds", command, timeout)
        return RunTestResult(
            success=False,
            stdout="",
            stderr=f"命令执行超时 ({timeout}s)",
            return_code=-1,
        )
    except Exception as e:
        _test_logger.error("测试执行异常 | 命令: %s | 错误: %s", command, str(e))
        return RunTestResult(
            success=False,
            stdout="",
            stderr=str(e),
            return_code=-1,
        )

    _test_logger.info(
        "测试执行完成 | 命令: %s | 返回码: %d",
        command,
        result.returncode,
    )
    return RunTestResult(
        success=result.returncode == 0,
        stdout=result.stdout,
        stderr=result.stderr,
        return_code=result.returncode,
    )
