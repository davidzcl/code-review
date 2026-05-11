"""
Git 只读操作封装

提供 git diff、git show、git diff HEAD 等只读 Git 命令的 Python 封装。
所有操作均为只读，不修改仓库状态。
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from logger import logger

_tools_logger = logger.get_logger("tools")

GIT_TIMEOUT = int(os.getenv("GIT_TIMEOUT", "30"))
MAX_DIFF_CHARS = int(os.getenv("MAX_DIFF_CHARS", "120000"))
MAX_CMD_OUTPUT = int(os.getenv("MAX_CMD_OUTPUT", "50000"))


def _run_git(args: List[str], cwd: Optional[str] = None) -> str:
    """只读 git 命令包装器

    Args:
        args: git 子命令参数列表
        cwd:  执行目录

    Returns:
        命令标准输出

    Raises:
        RuntimeError: git 命令失败时抛出
    """
    cmd = ["git"] + args
    _tools_logger.debug("执行 git 命令: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
            cwd=cwd or os.getcwd(),
            encoding="utf-8",
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"git 命令超时 ({GIT_TIMEOUT}s): {' '.join(cmd)}")
    except FileNotFoundError:
        raise RuntimeError("git 未安装或不在 PATH 中")

    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} 失败 (code={result.returncode}): "
            f"{result.stderr.strip()}"
        )

    return result.stdout


# ============================================================
# Git Diff
# ============================================================


def git_diff(
    base: Optional[str] = None,
    target: Optional[str] = None,
    staged_only: bool = False,
    file_filter: Optional[str] = None,
    cwd: Optional[str] = None,
) -> str:
    """获取 Git 仓库差异内容

    Args:
        base:        基准 commit/tag，默认从 GIT_BASE 环境变量读取
        target:      目标 commit/tag，默认从 GIT_TARGET 环境变量读取
        staged_only: 是否仅显示已暂存（staged）的变更
        file_filter: 文件路径过滤
        cwd:         执行目录，默认当前工作区

    Returns:
        unified diff 原始字符串

    Raises:
        ValueError: 未指定 base/target 且环境变量缺失
    """
    base = base or os.getenv("GIT_BASE")
    target = target or os.getenv("GIT_TARGET")

    if not base and not target:
        raise ValueError(
            "未指定 base 或 target，请传参或设置环境变量 GIT_BASE/GIT_TARGET"
        )

    args = ["diff", "--unified=3"]
    if staged_only:
        args.append("--staged")
    if file_filter:
        args.extend(["--", file_filter])
    if base:
        args.append(base)
    if target:
        args.append(target)

    result = _run_git(args, cwd)
    if len(result) > MAX_DIFF_CHARS:
        result = result[:MAX_DIFF_CHARS] + f"\n... [截断于 {MAX_DIFF_CHARS:,} chars]"
        _tools_logger.warning("diff 输出已截断 (%d chars)", MAX_DIFF_CHARS)

    return result


# ============================================================
# Changed Files
# ============================================================


def get_changed_files(
    base: Optional[str] = None,
    target: Optional[str] = None,
    by_type: bool = False,
) -> List[str] | Dict[str, List[str]]:
    """提取变更文件列表，可选按扩展名分组

    Args:
        base:    基准 commit
        target:  目标 commit
        by_type: 是否按文件扩展名分组返回

    Returns:
        by_type=False: 文件路径列表
        by_type=True:  {扩展名: [文件路径列表]}
    """
    base = base or os.getenv("GIT_BASE")
    target = target or os.getenv("GIT_TARGET")

    args = ["diff", "--name-only"]
    if base:
        args.append(base)
    if target:
        args.append(target)

    files = [f.strip() for f in _run_git(args).splitlines() if f.strip()]

    if not by_type:
        return files

    grouped: Dict[str, List[str]] = {}
    for f in files:
        ext = Path(f).suffix or "no-ext"
        grouped.setdefault(ext, []).append(f)
    return grouped


# ============================================================
# Read File
# ============================================================


def read_file(
    file_path: str,
    commit: Optional[str] = None,
    start_line: int = 1,
    end_line: Optional[int] = None,
    max_chars: int = 8000,
) -> str:
    """只读读取指定版本文件内容

    Args:
        file_path:  文件路径（相对于仓库根目录）
        commit:     commit hash / 分支名，None 表示当前工作区
        start_line: 起始行号（从 1 开始）
        end_line:   结束行号（含），None 表示文件末尾
        max_chars:  最大返回字符数

    Returns:
        文件内容字符串
    """
    if commit:
        spec = f"{commit}:{file_path}"
        content = _run_git(["show", spec])
    else:
        content = _run_git(["show", f"HEAD:{file_path}"])

    lines = content.splitlines(keepends=True)
    if end_line is not None:
        lines = lines[start_line - 1 : end_line]
    elif start_line > 1:
        lines = lines[start_line - 1 :]

    result = "".join(lines)
    if len(result) > max_chars:
        result = result[:max_chars] + "\n... [截断]"

    return result


# ============================================================
# Git 工作区状态检测（git diff HEAD）
# ============================================================


@dataclass
class WorkspaceChange:
    """工作区中单个文件的变更描述"""

    file_path: str
    old_start: int = 0
    old_count: int = 0
    new_start: int = 0
    new_count: int = 0
    additions: List[str] = field(default_factory=list)
    deletions: List[str] = field(default_factory=list)
    context_lines: List[str] = field(default_factory=list)
    is_new_file: bool = False
    is_deleted_file: bool = False


@dataclass
class WorkspaceStatus:
    """工作区状态快照"""

    changes: List[WorkspaceChange]
    total_additions: int = 0
    total_deletions: int = 0
    changed_files_count: int = 0
    raw_diff: str = ""


def _parse_diff_chunk(lines: List[str], chunk_start: int) -> Optional[WorkspaceChange]:
    """解析单个 diff chunk（@@ 区域）

    Args:
        lines:       整个 diff 输出的行数组
        chunk_start: @@ 行的索引

    Returns:
        解析后的 WorkspaceChange，或 None 解析失败
    """
    if chunk_start >= len(lines):
        return None

    header = lines[chunk_start]
    if not header.startswith("@@"):
        return None

    parts = header.split(" ")
    if len(parts) < 3:
        return None

    try:
        old_info = parts[1].lstrip("-")
        new_info = parts[2].lstrip("+")
        old_start, old_count = (int(x) for x in old_info.split(",")) if "," in old_info else (int(old_info), 1)
        new_start, new_count = (int(x) for x in new_info.split(",")) if "," in new_info else (int(new_info), 1)
    except (ValueError, IndexError):
        return None

    change = WorkspaceChange(
        file_path="",
        old_start=old_start,
        old_count=old_count,
        new_start=new_start,
        new_count=new_count,
    )

    additions = []
    deletions = []
    context_lines = []

    i = chunk_start + 1
    while i < len(lines):
        line = lines[i]
        if line.startswith("@@"):
            break
        if line.startswith("+"):
            additions.append(line[1:])
        elif line.startswith("-"):
            deletions.append(line[1:])
        elif line.startswith(" "):
            context_lines.append(line[1:])
        i += 1

    change.additions = additions
    change.deletions = deletions
    change.context_lines = context_lines

    return change


def get_workspace_status(cwd: Optional[str] = None) -> WorkspaceStatus:
    """检测 Git 工作区状态

    执行 git diff HEAD 获取已修改但未提交的变更，
    解析为结构化数据并以 JSON 兼容格式输出。

    Args:
        cwd: 仓库目录，默认当前工作目录

    Returns:
        WorkspaceStatus 包含解析后的变更列表和统计信息
    """
    try:
        raw_diff = _run_git(["diff", "HEAD", "--unified=3"], cwd=cwd)
    except RuntimeError:
        _tools_logger.warning("git diff HEAD 失败，回退到 git diff")
        raw_diff = _run_git(["diff", "--unified=3"], cwd=cwd)

    if not raw_diff.strip():
        _tools_logger.info("工作区干净，无未提交变更")
        return WorkspaceStatus(changes=[], raw_diff="")

    changes: List[WorkspaceChange] = []
    raw_lines = raw_diff.splitlines()
    i = 0

    while i < len(raw_lines):
        line = raw_lines[i]

        if line.startswith("diff --git"):
            parts = line.split(" ")
            file_a = parts[2][2:] if len(parts) > 2 else ""
            file_b = parts[3][2:] if len(parts) > 3 else ""
            file_path = file_b if file_b else file_a

            i += 1
            is_new = False
            is_deleted = False

            while i < len(raw_lines) and not raw_lines[i].startswith("@@"):
                if raw_lines[i].startswith("new file"):
                    is_new = True
                if raw_lines[i].startswith("deleted file"):
                    is_deleted = True
                i += 1

            while i < len(raw_lines):
                if raw_lines[i].startswith("@@"):
                    change = _parse_diff_chunk(raw_lines, i)
                    if change is not None:
                        change.file_path = file_path
                        change.is_new_file = is_new
                        change.is_deleted_file = is_deleted
                        changes.append(change)
                    while i < len(raw_lines) and not raw_lines[i].startswith("diff --git"):
                        i += 1
                else:
                    i += 1
        else:
            i += 1

    total_additions = sum(len(c.additions) for c in changes)
    total_deletions = sum(len(c.deletions) for c in changes)
    changed_files = len({c.file_path for c in changes})

    return WorkspaceStatus(
        changes=changes,
        total_additions=total_additions,
        total_deletions=total_deletions,
        changed_files_count=changed_files,
        raw_diff=raw_diff,
    )


def workspace_status_to_dict(status: WorkspaceStatus) -> Dict[str, Any]:
    """将 WorkspaceStatus 转换为序列化字典（JSON 兼容）

    Args:
        status: 工作区状态对象

    Returns:
        可序列化为 JSON 的字典
    """
    return {
        "summary": {
            "changed_files_count": status.changed_files_count,
            "total_additions": status.total_additions,
            "total_deletions": status.total_deletions,
        },
        "changes": [
            {
                "file_path": c.file_path,
                "location": {
                    "old_start": c.old_start,
                    "old_count": c.old_count,
                    "new_start": c.new_start,
                    "new_count": c.new_count,
                },
                "additions": c.additions,
                "deletions": c.deletions,
                "context_lines": c.context_lines,
                "is_new_file": c.is_new_file,
                "is_deleted_file": c.is_deleted_file,
            }
            for c in status.changes
        ],
    }


def get_workspace_status_json(cwd: Optional[str] = None) -> str:
    """获取工作区状态并返回 JSON 字符串

    Args:
        cwd: 仓库目录

    Returns:
        格式化 JSON 字符串
    """
    status = get_workspace_status(cwd=cwd)
    return json.dumps(workspace_status_to_dict(status), ensure_ascii=False, indent=2)
