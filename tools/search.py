"""
代码搜索工具

基于 git grep 的只读代码搜索，支持按文件类型过滤、大小写控制。
搜索范围限已跟踪文件，不触及 untracked 文件。
"""

from __future__ import annotations

import os
import subprocess
from typing import List, Optional

from logger import logger

_search_logger = logger.get_logger("search")

SEARCH_TIMEOUT = int(os.getenv("SEARCH_TIMEOUT", "15"))
SEARCH_MAX_RESULTS = int(os.getenv("SEARCH_MAX_RESULTS", "200"))
SEARCH_DEFAULT_MAX_CHARS = int(os.getenv("SEARCH_DEFAULT_MAX_CHARS", "8000"))


def _git_grep(
    pattern: str,
    path: str = ".",
    file_types: Optional[str] = None,
    case_sensitive: bool = False,
    cwd: Optional[str] = None,
) -> str:
    args = ["grep", "--line-number", "--heading", "--break"]
    if not case_sensitive:
        args.append("--ignore-case")
    args.append(pattern)
    if file_types:
        args.extend(["--", file_types])
    else:
        args.append(".")

    cmd = ["git"] + args
    _search_logger.debug("搜索命令: %s", " ".join(cmd))

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=SEARCH_TIMEOUT,
        cwd=cwd or os.getcwd(),
        encoding="utf-8",
    )

    if result.returncode == 1:
        return ""
    if result.returncode != 0:
        _search_logger.warning("git grep 失败: %s", result.stderr.strip())
        raise RuntimeError(f"git grep 失败: {result.stderr.strip()}")

    return result.stdout


def _rg_search(
    pattern: str,
    path: str = ".",
    file_types: Optional[str] = None,
    case_sensitive: bool = False,
    cwd: Optional[str] = None,
) -> str:
    """ripgrep 回退方案（支持 untracked 文件）"""
    try:
        args = ["rg", "--line-number", "--heading", "--color", "never"]
        if not case_sensitive:
            args.append("--ignore-case")
        if file_types:
            args.extend(["--type", file_types])
        args.append(pattern)
        if path:
            args.append(path)

        _search_logger.debug("rg 回退命令: %s", " ".join(args))
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=SEARCH_TIMEOUT,
            cwd=cwd or os.getcwd(),
            encoding="utf-8",
        )

        if result.returncode == 1:
            return ""
        if result.returncode != 0:
            raise RuntimeError(f"rg 搜索失败: {result.stderr.strip()}")
        return result.stdout
    except FileNotFoundError:
        raise RuntimeError("ripgrep (rg) 未安装，无法搜索 untracked 文件")


def search_code(
    pattern: str,
    path: str = ".",
    file_types: Optional[str] = None,
    case_sensitive: bool = False,
    max_chars: int = SEARCH_DEFAULT_MAX_CHARS,
) -> str:
    """在代码库中搜索文本模式

    优先使用 git grep（仅搜索已跟踪文件），
    遇到新文件/untracked 文件时回退到 ripgrep。

    Args:
        pattern:       搜索模式（支持正则语法）
        path:          搜索路径，默认当前目录
        file_types:    文件类型过滤，如 "*.py" 或 glob 模式
        case_sensitive: 是否大小写敏感
        max_chars:      最大返回字符数

    Returns:
        匹配结果的文本表示（git grep 格式），超长自动截断

    Raises:
        RuntimeError: git/rg 命令失败
    """
    if not pattern.strip():
        raise ValueError("搜索模式不能为空")

    try:
        output = _git_grep(pattern, path, file_types, case_sensitive)
    except RuntimeError as e:
        _search_logger.warning("git grep 失败，尝试 ripgrep: %s", str(e))
        try:
            output = _rg_search(pattern, path, file_types, case_sensitive)
        except RuntimeError as rg_e:
            raise RuntimeError(
                f"git grep 和 ripgrep 均失败。git: {e} | rg: {rg_e}"
            )

    lines = output.splitlines()
    if len(lines) > SEARCH_MAX_RESULTS:
        output = "\n".join(lines[:SEARCH_MAX_RESULTS])
        output += f"\n... [截断，共 {len(lines)} 条匹配，仅显示前 {SEARCH_MAX_RESULTS} 条]"
        _search_logger.warning(
            "搜索结果截断: %d 条 -> %d 条", len(lines), SEARCH_MAX_RESULTS
        )

    if len(output) > max_chars:
        output = output[:max_chars]
        output += "\n... [截断]"

    return output
