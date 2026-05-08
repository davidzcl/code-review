"""
PR 描述解析器

将 Markdown 格式的 PR 描述文本解析为结构化 PRContext。
支持标准格式：
  **标题**: ...
  **描述**: ...
  **标签**: ...
  **分支**: source → target
  **作者**: ...
  **评审者**: ...
  **关联 Issue**: ...
  **变更概要**: ...
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from logger import logger

_pr_logger = logger.get_logger("pr_parser")


@dataclass
class PRContext:
    title: str = ""
    description: str = ""
    labels: List[str] = field(default_factory=list)
    base_branch: str = ""
    head_branch: str = ""
    author: str = ""
    changed_files_summary: str = ""


class PRParseError(Exception):
    """PR 解析异常。"""


_FIELD_PATTERN = re.compile(r"^\*\*(.+?)\*\*:\s*(.*)")


def _parse_branch(value: str) -> tuple:
    parts = re.split(r"\s*[→➡]\s*", value, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    parts = re.split(r"\s*->\s*", value, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    if "/" in value:
        return value.strip(), ""
    return "", value.strip()


def parse_pr_description(pr_text: str) -> PRContext:
    """解析 PR 描述文本为结构化数据。

    Args:
        pr_text: PR 描述原始文本（Markdown 格式）

    Returns:
        PRContext 对象

    Raises:
        PRParseError: 必填字段缺失时抛出
    """
    if not pr_text or not pr_text.strip():
        raise PRParseError("PR 描述文本为空")

    ctx = PRContext()
    description_lines: List[str] = []
    in_description = False

    for line in pr_text.splitlines():
        stripped = line.strip()
        m = _FIELD_PATTERN.match(stripped)
        if m:
            field_name = m.group(1).strip()
            field_value = m.group(2).strip()

            if field_name == "标题":
                ctx.title = field_value
                in_description = False
            elif field_name == "描述":
                if field_value:
                    description_lines.append(field_value)
                in_description = True
            elif field_name == "标签":
                ctx.labels = [
                    tag.strip().lstrip("- ").strip()
                    for tag in field_value.split(",")
                    if tag.strip()
                ]
                in_description = False
            elif field_name == "分支":
                ctx.head_branch, ctx.base_branch = _parse_branch(field_value)
                in_description = False
            elif field_name == "作者":
                ctx.author = field_value
                in_description = False
            elif field_name in ("变更概要", "变更摘要"):
                ctx.changed_files_summary = field_value
                in_description = False
            else:
                in_description = False
        elif in_description and stripped:
            description_lines.append(stripped)
        elif stripped:
            in_description = False

    ctx.description = "\n".join(description_lines)

    if not ctx.title:
        _pr_logger.warning("PR 缺少标题字段")
    if not ctx.author:
        _pr_logger.warning("PR 缺少作者字段")

    _pr_logger.info(
        "PR 解析完成: title=%s labels=%s base=%s head=%s",
        ctx.title, ctx.labels, ctx.base_branch, ctx.head_branch,
    )
    return ctx
