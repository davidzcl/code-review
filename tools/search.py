"""
代码搜索工具

基于 git grep 的只读代码搜索，支持按文件类型过滤、大小写控制。
搜索范围限已跟踪文件，不触及 untracked 文件。
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Set

from logger import logger
from config import _env_int

_search_logger = logger.get_logger("search")

SEARCH_TIMEOUT = _env_int("SEARCH_TIMEOUT", 15)
SEARCH_MAX_RESULTS = _env_int("SEARCH_MAX_RESULTS", 200)

EXCLUDED_DIRS: Set[str] = {
    ".git", ".review-agent", ".tmp", ".pytest_cache",
    "__pycache__", "node_modules", ".venv",
}

EXCLUDED_EXTENSIONS: Set[str] = {
    ".md", ".txt", ".toml", ".yaml", ".yml", ".json",
}


@dataclass
class SearchResult:
    file_path: str
    line: int
    content: str


def _build_git_exclude_args() -> List[str]:
    args: List[str] = []
    for d in EXCLUDED_DIRS:
        args.append(f":(exclude){d}/")
        args.append(f":(exclude){d}/*")
    for ext in EXCLUDED_EXTENSIONS:
        args.append(f":(exclude)*{ext}")
    return args


def _build_rg_exclude_args() -> List[str]:
    args: List[str] = []
    for d in EXCLUDED_DIRS:
        args.extend(["--glob", f"!{d}/**"])
    for ext in EXCLUDED_EXTENSIONS:
        args.extend(["--glob", f"!*{ext}"])
    return args


def _parse_search_output(raw: str) -> List[SearchResult]:
    """将 git grep / rg 文本输出解析为 SearchResult 列表。"""
    results: List[SearchResult] = []
    current_file: Optional[str] = None

    for line in raw.splitlines():
        if not line.strip():
            continue
        if _is_file_heading(line, current_file):
            current_file = line.strip()
        else:
            parts = line.split(":", 1)
            if len(parts) == 2 and current_file:
                try:
                    line_no = int(parts[0])
                    results.append(
                        SearchResult(
                            file_path=current_file,
                            line=line_no,
                            content=parts[1],
                        )
                    )
                except ValueError:
                    pass
    return results


def _is_file_heading(line: str, current_file: Optional[str]) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if ":" not in stripped:
        return True
    first_colon = stripped.index(":")
    after_colon = stripped[first_colon + 1:]
    if after_colon and after_colon[0].isdigit():
        return False
    if current_file is None:
        return True
    return False


def _git_grep(
    pattern: str,
    path: str = ".",
    file_types: Optional[str] = None,
    case_sensitive: bool = False,
    cwd: Optional[str] = None,
) -> List[SearchResult]:
    args = ["grep", "--line-number", "--heading", "--break"]
    if not case_sensitive:
        args.append("--ignore-case")
    args.append(pattern)
    pathspecs: List[str] = []
    if file_types:
        pathspecs.append(file_types)
    else:
        pathspecs.append(".")
    pathspecs.extend(_build_git_exclude_args())
    args.extend(["--"] + pathspecs)

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
        return []
    if result.returncode != 0:
        _search_logger.warning("git grep 失败: %s", result.stderr.strip())
        raise RuntimeError(f"git grep 失败: {result.stderr.strip()}")

    return _parse_search_output(result.stdout)


def _rg_search(
    pattern: str,
    path: str = ".",
    file_types: Optional[str] = None,
    case_sensitive: bool = False,
    cwd: Optional[str] = None,
) -> List[SearchResult]:
    """ripgrep 回退方案（支持 untracked 文件）"""
    try:
        args = ["rg", "--line-number", "--heading", "--color", "never"]
        if not case_sensitive:
            args.append("--ignore-case")
        if file_types:
            args.extend(["--type", file_types])
        args.extend(_build_rg_exclude_args())
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
            return []
        if result.returncode != 0:
            raise RuntimeError(f"rg 搜索失败: {result.stderr.strip()}")
        return _parse_search_output(result.stdout)
    except FileNotFoundError:
        raise RuntimeError("ripgrep (rg) 未安装，无法搜索 untracked 文件")


def search_code(
    pattern: str,
    path: str = ".",
    file_types: Optional[str] = None,
    case_sensitive: bool = False,
) -> List[SearchResult]:
    """在代码库中搜索文本模式

    优先使用 git grep（仅搜索已跟踪文件），
    遇到新文件/untracked 文件时回退到 ripgrep。

    自动排除目录: .git, .review-agent, .tmp, .pytest_cache,
                  __pycache__, node_modules, .venv
    自动跳过文件扩展名: .md, .txt, .toml, .yaml, .yml, .json

    Args:
        pattern:       搜索模式（支持正则语法）
        path:          搜索路径，默认当前目录
        file_types:    文件类型过滤，如 "*.py" 或 glob 模式
        case_sensitive: 是否大小写敏感

    Returns:
        匹配结果列表，每条包含文件路径、行号和内容

    Raises:
        ValueError:  搜索模式为空
        RuntimeError: git/rg 命令失败
    """
    if not pattern.strip():
        raise ValueError("搜索模式不能为空")

    try:
        results = _git_grep(pattern, path, file_types, case_sensitive)
    except RuntimeError as e:
        _search_logger.warning("git grep 失败，尝试 ripgrep: %s", str(e))
        try:
            results = _rg_search(pattern, path, file_types, case_sensitive)
        except RuntimeError as rg_e:
            raise RuntimeError(
                f"git grep 和 ripgrep 均失败。git: {e} | rg: {rg_e}"
            )

    if len(results) > SEARCH_MAX_RESULTS:
        _search_logger.warning(
            "搜索结果截断: %d 条 -> %d 条", len(results), SEARCH_MAX_RESULTS
        )
        results = results[:SEARCH_MAX_RESULTS]

    return results
