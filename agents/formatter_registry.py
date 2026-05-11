"""
Formatter 注册与工厂模块

类似 model_registry.py，基于 model_type 提供对应的 Formatter 实例。
每个 LLM 后端有不同的消息格式要求，formatter 负责将 agent 内部消息
转换为模型可接受的 API 请求格式。

内置映射：
    dashscope  → DashScopeChatFormatter
    openai     → OpenAIChatFormatter
    deepseek   → DeepSeekChatFormatter（支持 reasoning_content）
    ollama     → OllamaChatFormatter

用法示例:
    from agents.formatter_registry import create_formatter

    formatter = create_formatter("dashscope")
    formatter = create_formatter("openai")
    formatter = create_formatter("deepseek")
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Type

from agentscope.formatter import (
    FormatterBase,
    DashScopeChatFormatter,
    OpenAIChatFormatter,
    OllamaChatFormatter,
    DeepSeekChatFormatter,
)
from agentscope.model import (
    ChatModelBase,
    DashScopeChatModel,
    OpenAIChatModel,
    OllamaChatModel,
)

FormatterFactory = Callable[..., FormatterBase]


class FormatterRegistryError(Exception):
    """Formatter 注册或创建过程中的异常。"""


class _FormatterRegistry:
    """内部 Formatter 注册表，存储 model_type → 工厂函数的映射。

    单例模式。
    """

    _instance: Optional[_FormatterRegistry] = None

    def __new__(cls) -> _FormatterRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._factories: Dict[str, FormatterFactory] = {}
        return cls._instance

    def register(self, model_type: str, factory: FormatterFactory) -> None:
        """注册一个 model_type 及其 formatter 工厂函数。"""
        self._factories[model_type] = factory

    def get_factory(self, model_type: str) -> FormatterFactory:
        """获取指定 model_type 的 formatter 工厂函数。

        Raises:
            FormatterRegistryError: model_type 未注册时。
        """
        if model_type not in self._factories:
            raise FormatterRegistryError(
                f"未注册的 formatter 类型: '{model_type}'。"
                f"已注册类型: {list(self._factories.keys())}"
            )
        return self._factories[model_type]

    def list_types(self) -> list[str]:
        """列出所有已注册的 model_type。"""
        return list(self._factories.keys())

    def is_registered(self, model_type: str) -> bool:
        """检查 model_type 是否已注册。"""
        return model_type in self._factories

    def clear(self) -> None:
        """清空所有注册（仅用于测试）。"""
        self._factories.clear()


_registry = _FormatterRegistry()


def register_formatter(model_type: str, factory: Optional[FormatterFactory] = None):
    """Formatter 注册装饰器/函数。

    两种用法：
    1. 作为装饰器:
        @register_formatter("my_model_type")
        class MyFormatter(FormatterBase):
            ...
    2. 作为显式注册:
        register_formatter("my_model_type", factory=my_factory_function)
    """

    def decorator(formatter_cls: Any) -> Any:
        if factory is not None:
            _registry.register(model_type, factory=factory)
            return formatter_cls

        if isinstance(formatter_cls, type) and issubclass(formatter_cls, FormatterBase):

            def default_factory(**kwargs: Any) -> FormatterBase:
                return formatter_cls(**kwargs)

            _registry.register(model_type, factory=default_factory)
            return formatter_cls

        raise FormatterRegistryError(
            f"@register_formatter 装饰器只能用于 FormatterBase 子类，"
            f"收到类型: {type(formatter_cls)}"
        )

    if factory is not None:
        _registry.register(model_type, factory=factory)
        return factory
    return decorator


# ============================================================
# 内置 adapter 工厂函数
# ============================================================


def _dashscope_formatter_factory(**kwargs: Any) -> DashScopeChatFormatter:
    return DashScopeChatFormatter(**kwargs)


def _openai_formatter_factory(**kwargs: Any) -> OpenAIChatFormatter:
    return OpenAIChatFormatter(**kwargs)


def _ollama_formatter_factory(**kwargs: Any) -> OllamaChatFormatter:
    return OllamaChatFormatter(**kwargs)


def _deepseek_formatter_factory(**kwargs: Any) -> DeepSeekChatFormatter:
    return DeepSeekChatFormatter(**kwargs)


# ============================================================
# 预注册内置 formatter
# ============================================================

_registry.register("dashscope", factory=_dashscope_formatter_factory)
_registry.register("openai", factory=_openai_formatter_factory)
_registry.register("deepseek", factory=_deepseek_formatter_factory)
_registry.register("ollama", factory=_ollama_formatter_factory)


# ============================================================
# 公开 API
# ============================================================


def create_formatter(model_type: str, **kwargs: Any) -> FormatterBase:
    """从 model_type 创建对应的 Formatter 实例。

    Args:
        model_type: 模型类型标识符（与 model_registry 共用同一套命名）。
        **kwargs: 传递给 formatter 构造函数的额外参数。

    Returns:
        FormatterBase 子类实例。

    Raises:
        FormatterRegistryError: model_type 未注册时。
    """
    factory = _registry.get_factory(model_type)
    return factory(**kwargs)


def list_registered_formatters() -> list[str]:
    """列出所有已注册的 formatter 类型。"""
    return _registry.list_types()


def is_formatter_registered(model_type: str) -> bool:
    """检查指定 model_type 是否已注册 formatter。"""
    return _registry.is_registered(model_type)


def infer_formatter_type(model: ChatModelBase) -> str:
    """从 model 实例推断对应的 model_type（用于 formatter 回退）。

    当调用方未显式传入 formatter 时，通过 isinstance 检查
    model 的具体子类来推断应使用的 formatter 类型。
    DeepSeek 使用 OpenAIChatModel，额外通过 model_name 中
    是否包含 "deepseek" 判定。

    Args:
        model: 已创建的 ChatModelBase 子类实例。

    Returns:
        对应的 model_type 字符串。无法识别时返回 "dashscope"。
    """
    if isinstance(model, DashScopeChatModel):
        return "dashscope"
    if isinstance(model, OpenAIChatModel):
        model_name = getattr(model, "model_name", "") or ""
        if "deepseek" in model_name.lower():
            return "deepseek"
        return "openai"
    if isinstance(model, OllamaChatModel):
        return "ollama"
    return "dashscope"