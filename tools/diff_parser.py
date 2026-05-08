"""
Diff 解析器

将 unified diff 原始文本解析为结构化 DiffChunk 列表。
解析流程：
  1. 按 diff --git 分割文件
  2. @@ 行解析新旧文件行号范围
  3. +/-/空格 前缀分类行为 additions/deletions/context
  4. 根据扩展名推断编程语言
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from logger import logger

_diff_logger = logger.get_logger("diff_parser")


@dataclass
class DiffChunk:
    file_path: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    context: str
    additions: List[str] = field(default_factory=list)
    deletions: List[str] = field(default_factory=list)
    language: str = ""
    is_new_file: bool = False
    is_deleted_file: bool = False


class DiffParseError(Exception):
    """Diff 解析异常。"""


_LANGUAGE_MAP: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescriptreact",
    ".jsx": "javascriptreact",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".sql": "sql",
    ".md": "markdown",
    ".dockerfile": "dockerfile",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "ini",
}


def _infer_language(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    base = os.path.basename(file_path).lower()
    if base == "dockerfile":
        return "dockerfile"
    if base in ("makefile", "gnumakefile"):
        return "makefile"
    return _LANGUAGE_MAP.get(ext, "")


def _parse_hunk_header(line: str) -> tuple:
    m = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
    if not m:
        raise DiffParseError(f"无效的 hunk header: {line}")
    return (
        int(m.group(1)),
        int(m.group(2) or 1),
        int(m.group(3)),
        int(m.group(4) or 1),
    )


_CONTEXT_LINES = 3


def _extract_context(
    additions: List[str],
    deletions: List[str],
    context_lines: List[str],
) -> str:
    context: List[str] = []
    if context_lines:
        start = max(0, len(context_lines) - _CONTEXT_LINES)
        context.extend(context_lines[start:])
    if additions or deletions:
        context.append("... 变更行 ...")
    return "\n".join(context[-_CONTEXT_LINES * 2:])


def parse_diff(diff_text: str) -> List[DiffChunk]:
    """解析 unified diff 文本为结构化数据。

    Args:
        diff_text: git diff 输出字符串

    Returns:
        DiffChunk 列表，按文件分组

    Raises:
        DiffParseError: 格式无效时抛出
    """
    if not diff_text.strip():
        return []

    chunks: List[DiffChunk] = []
    current_file: Optional[str] = None
    is_new = False
    is_deleted = False
    in_hunk = False

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            if current_file and in_hunk:
                chunks.append(DiffChunk(
                    file_path=current_file,
                    old_start=old_start,
                    old_count=old_count,
                    new_start=new_start,
                    new_count=new_count,
                    context=_extract_context(additions, deletions, context_lines),
                    additions=additions,
                    deletions=deletions,
                    language=_infer_language(current_file),
                    is_new_file=is_new,
                    is_deleted_file=is_deleted,
                ))

            parts = line.split()
            current_file = parts[3][2:] if len(parts) >= 4 else None
            is_new = False
            is_deleted = False
            in_hunk = False

        elif line.startswith("new file mode"):
            is_new = True
        elif line.startswith("deleted file mode"):
            is_deleted = True

        elif line.startswith("@@"):
            if current_file and in_hunk:
                chunks.append(DiffChunk(
                    file_path=current_file,
                    old_start=old_start,
                    old_count=old_count,
                    new_start=new_start,
                    new_count=new_count,
                    context=_extract_context(additions, deletions, context_lines),
                    additions=additions,
                    deletions=deletions,
                    language=_infer_language(current_file),
                    is_new_file=is_new,
                    is_deleted_file=is_deleted,
                ))

            old_start, old_count, new_start, new_count = _parse_hunk_header(line)
            additions = []
            deletions = []
            context_lines = []
            in_hunk = True

        elif in_hunk and current_file:
            if line.startswith("+") and not line.startswith("+++"):
                additions.append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                deletions.append(line[1:])
            elif line.startswith(" "):
                context_lines.append(line[1:])

    if current_file and in_hunk:
        chunks.append(DiffChunk(
            file_path=current_file,
            old_start=old_start,
            old_count=old_count,
            new_start=new_start,
            new_count=new_count,
            context=_extract_context(additions, deletions, context_lines),
            additions=additions,
            deletions=deletions,
            language=_infer_language(current_file),
            is_new_file=is_new,
            is_deleted_file=is_deleted,
        ))

    _diff_logger.info("解析完成: %d 个文件变更块", len(chunks))
    return chunks


def get_changed_files(diff_text: str) -> List[str]:
    """从 diff 文本中提取变更文件路径列表。"""
    files: List[str] = []
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                files.append(parts[3][2:])
    return files


@dataclass
class AddedLine:
    file_path: str
    line: int
    content: str


def get_added_lines(diff_text: str) -> List[AddedLine]:
    """从 unified diff 文本中提取所有新增代码行（含行号）。

    与 parse_diff 共享相同的状态机解析逻辑，
    但返回行级粒度的数据，供 risk_scan 等模块使用。

    Args:
        diff_text: git diff 输出字符串

    Returns:
        AddedLine 列表，每条包含 file_path/line/content
    """
    results: List[AddedLine] = []
    current_file: Optional[str] = None
    new_line: int = 0
    in_hunk: bool = False

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            current_file = parts[3][2:] if len(parts) >= 4 else None
            new_line = 0
            in_hunk = False
        elif line.startswith("@@ "):
            m = re.search(r'\+(\d+)(?:,\d+)? ', line)
            if m:
                new_line = int(m.group(1))
            in_hunk = True
        elif in_hunk and current_file:
            if line.startswith("+") and not line.startswith("+++"):
                results.append(AddedLine(
                    file_path=current_file,
                    line=new_line,
                    content=line[1:],
                ))
                new_line += 1
            elif line.startswith(" "):
                new_line += 1

    return results


def split_by_file(diff_text: str) -> Dict[str, str]:
    """按文件分割 diff 文本。

    Returns:
        {文件路径: 该文件的 diff 片段}
    """
    sections: Dict[str, str] = {}
    current_file: Optional[str] = None
    current_lines: List[str] = []

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            if current_file and current_lines:
                sections[current_file] = "\n".join(current_lines)
                current_lines = []
            parts = line.split()
            current_file = parts[3][2:] if len(parts) >= 4 else None
            if current_file:
                current_lines.append(line)
        elif current_file:
            current_lines.append(line)

    if current_file and current_lines:
        sections[current_file] = "\n".join(current_lines)

    return sections
