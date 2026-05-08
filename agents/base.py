"""
AgentScope 基础 agent 封装模块

提供统一的 agent 基类封装和自定义异常。
"""

from __future__ import annotations


class AgentInitializationError(Exception):
    """Agent 初始化失败异常。

    在 agent 初始化过程中缺少必要参数或参数无效时抛出。
    """

    pass
