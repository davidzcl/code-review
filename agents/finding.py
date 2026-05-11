"""
Finding 数据模型

独立模块，无项目内部依赖，避免循环导入。
"""

from __future__ import annotations

import uuid
from typing import List, Tuple

from pydantic import BaseModel, Field, field_validator

_SEVERITY_VALUES = {"critical", "important", "minor"}


class Finding(BaseModel):
    """评审发现的数据结构。

    表示评审者在代码审查过程中发现的一个具体问题。

    继承 pydantic.BaseModel，内建类型校验和 JSON schema 生成
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reviewer: str = ""
    role: str = ""
    severity: str = "minor"
    file_path: str = ""
    line_range: Tuple[int, int] = (0, 0)
    title: str = ""
    description: str = ""
    suggestion: str = ""
    confidence: float = 0.0
    evidence: List[str] = Field(default_factory=list)

    @field_validator("severity")
    @classmethod
    def _check_severity(cls, v: str) -> str:
        if v not in _SEVERITY_VALUES:
            raise ValueError(
                f"无效的严重级别: '{v}'，有效值: {_SEVERITY_VALUES}"
            )
        return v