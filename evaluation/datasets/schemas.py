"""
评测系统测试用例 Schema 定义

定义合成测试用例的数据结构，用于注入已知问题并验证智能体检测能力。
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator


class IssueCategory(str, Enum):
    """问题分类枚举"""

    SECURITY = "security"
    PERFORMANCE = "performance"
    LOGIC = "logic"
    STYLE = "style"


class DiffChunkSchema(BaseModel):
    """Diff 块数据结构"""

    file_path: str = Field(description="文件路径")
    language: Optional[str] = Field(default=None, description="编程语言")
    old_start: int = Field(description="旧文件起始行号")
    old_count: int = Field(description="旧文件行数")
    new_start: int = Field(description="新文件起始行号")
    new_count: int = Field(description="新文件行数")
    additions: List[str] = Field(default_factory=list, description="新增行")
    deletions: List[str] = Field(default_factory=list, description="删除行")
    context: Optional[str] = Field(default=None, description="上下文")


class PRContextSchema(BaseModel):
    """PR 上下文数据结构"""

    title: str = Field(description="PR 标题")
    description: Optional[str] = Field(default=None, description="PR 描述")
    author: Optional[str] = Field(default=None, description="作者")
    labels: List[str] = Field(default_factory=list, description="标签")
    base_branch: Optional[str] = Field(default=None, description="目标分支")
    head_branch: Optional[str] = Field(default=None, description="源分支")


class InjectedIssue(BaseModel):
    """注入的已知问题"""

    category: IssueCategory = Field(description="问题分类")
    severity: str = Field(description="严重级别")
    title: str = Field(description="问题标题")
    description: str = Field(description="问题描述")
    file_path: str = Field(description="文件路径")
    line_range: Tuple[int, int] = Field(description="行号范围 (start, end)")
    detection_hints: List[str] = Field(default_factory=list, description="检测提示关键词")

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """验证 severity 必须是有效值"""
        valid_severities = {"critical", "high", "medium", "low"}
        if v not in valid_severities:
            raise ValueError(f"severity 必须是 {valid_severities} 之一，收到: {v}")
        return v


class SyntheticTestCase(BaseModel):
    """合成测试用例"""

    id: str = Field(description="测试用例 ID")
    name: str = Field(description="测试用例名称")
    category: IssueCategory = Field(description="问题分类")
    difficulty: str = Field(description="难度级别")
    diff_chunks: List[DiffChunkSchema] = Field(description="Diff 块列表")
    pr_context: Optional[PRContextSchema] = Field(default=None, description="PR 上下文")
    injected_issues: List[InjectedIssue] = Field(
        default_factory=list, description="注入的问题列表"
    )
    expected_tools: List[str] = Field(default_factory=list, description="期望调用的工具")
    expected_findings_count: int = Field(default=0, description="期望的发现数量")
