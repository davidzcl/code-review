"""
Finding 数据模型

独立模块，无项目内部依赖，避免循环导入。
"""

from __future__ import annotations

import uuid
from typing import List, Literal, Tuple

from pydantic import BaseModel, Field


class Finding(BaseModel):
    """评审发现的数据结构。

    表示评审者在代码审查过程中发现的一个具体问题。

    继承 pydantic.BaseModel，内建类型校验和 JSON schema 生成
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reviewer: str = Field(description="评审者名称", ignore=True)
    role: str = Field(description="评审角色", ignore=True)
    severity: Literal["high", "medium", "low", "critical"] = Field(default="low", description="严重级别")
    file_path: str = Field(description="文件路径")
    line_range: Tuple[int, int] = Field(description="代码行范围", ignore=True)
    title: str = Field(description="问题标题")
    description: str = Field(description="问题描述")
    suggestion: str = Field(description="建议修复")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="匹配置信度")
    evidence: List[str] = Field(default_factory=list, description="支持证据")