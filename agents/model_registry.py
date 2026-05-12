"""
自定义模型注册与工厂模块

基于 agentscope ChatModelBase 抽象基类，提供：
1. 模型类型注册机制（装饰器 + 显式注册）
2. 工厂函数 create_model() —— 从配置字典创建模型实例
3. 内置适配器：DashScope、OpenAI 兼容、本地 Ollama
4. 扩展接口：继承 ChatModelBase 并通过 register_model() 注册

用法示例:
    from agents.model_registry import create_model, register_model
    from agentscope.model import ChatModelBase, ChatResponse

    # 方式一：使用内置适配器
    model = create_model({
        "model_type": "dashscope",
        "model_name": "qwen-max",
        "stream": True,
    })

    # 方式二：注册自定义模型
    @register_model("my_custom_model")
    class MyModel(ChatModelBase):
        async def __call__(self, *args, **kwargs) -> ChatResponse:
            ...

    model = create_model({"model_type": "my_custom_model", ...})
"""

from __future__ import annotations

import os
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Type, TypeVar, AsyncGenerator

from agentscope.model import (
    ChatModelBase,
    ChatResponse,
    DashScopeChatModel,
    OpenAIChatModel,
    OllamaChatModel,
)

logger = logging.getLogger(__name__)

# 模型工厂函数类型别名
ModelFactory = Callable[..., ChatModelBase]
# 自定义模型类（必须是 ChatModelBase 的子类）
TModel = TypeVar("TModel", bound=ChatModelBase)


class ModelRegistryError(Exception):
    """模型注册或创建过程中的异常。"""

    pass


class _ModelRegistry:
    """内部模型注册表，存储 model_type -> 工厂函数的映射。

    单例模式，全局唯一实例。
    """

    _instance: Optional[_ModelRegistry] = None

    def __new__(cls) -> _ModelRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._factories: Dict[str, ModelFactory] = {} # type: ignore
            cls._instance._model_classes: Dict[str, Type[ChatModelBase]] = {} # type: ignore
        return cls._instance

    def register(
        self,
        model_type: str,
        factory: Optional[ModelFactory] = None,
        model_class: Optional[Type[ChatModelBase]] = None,
    ) -> None:
        """注册一个模型类型及其工厂函数。

        Args:
            model_type: 模型类型标识符，配置中 model_type 字段对应此值。
            factory: 工厂函数，签名为 (**kwargs) -> ChatModelBase。
            model_class: 模型类（可选），用于文档和自省。
        """
        if model_type in self._factories:
            logger.warning(f"覆盖已注册的模型类型: {model_type}")
        if factory is not None:
            self._factories[model_type] = factory
        if model_class is not None:
            self._model_classes[model_type] = model_class

    def get_factory(self, model_type: str) -> ModelFactory:
        """获取指定模型类型的工厂函数。

        Raises:
            ModelRegistryError: 模型类型未注册时抛出。
        """
        if model_type not in self._factories:
            raise ModelRegistryError(
                f"未注册的模型类型: '{model_type}'。"
                f"已注册类型: {list(self._factories.keys())}"
            )
        return self._factories[model_type]

    def list_types(self) -> list[str]:
        """列出所有已注册的模型类型。"""
        return list(self._factories.keys())

    def is_registered(self, model_type: str) -> bool:
        """检查模型类型是否已注册。"""
        return model_type in self._factories

    def clear(self) -> None:
        """清空所有注册（仅用于测试）。"""
        self._factories.clear()
        self._model_classes.clear()


# 全局注册表单例
_registry = _ModelRegistry()


def register_model(
    model_type: str,
    factory: Optional[ModelFactory] = None,
):
    """模型注册装饰器/函数。

    两种用法：
    1. 作为装饰器:
        @register_model("my_model")
        class MyModel(ChatModelBase):
            ...
    2. 作为显式注册函数:
        register_model("my_model", factory=my_factory_function)

    Args:
        model_type: 模型类型标识符。
        factory: 显式指定的工厂函数（方式2），为 None 时使用装饰器模式（方式1）。
    """

    def decorator(model_cls_or_obj: Any) -> Any:
        # 方式2：factory 函数已提供
        if factory is not None:
            _registry.register(model_type, factory=factory)
            return model_cls_or_obj

        # 方式1：装饰器作用于类
        if isinstance(model_cls_or_obj, type) and issubclass(
            model_cls_or_obj, ChatModelBase
        ):

            def default_factory(**kwargs: Any) -> ChatModelBase:
                # 过滤出模型类 __init__ 接受的参数
                valid_kwargs = {
                    k: v for k, v in kwargs.items() if k != "model_type"
                }
                return model_cls_or_obj(**valid_kwargs)

            _registry.register(model_type, factory=default_factory)
            _registry.register(model_type, model_class=model_cls_or_obj)
            logger.info(f"注册自定义模型: {model_type} -> {model_cls_or_obj.__name__}")
            return model_cls_or_obj

        raise ModelRegistryError(
            f"@register_model 装饰器只能用于 ChatModelBase 子类，"
            f"收到类型: {type(model_cls_or_obj)}"
        )

    # 判断调用方式
    if factory is not None:
        # 方式2：显式注册，decorator 接收任意对象并直接注册
        # 这种情况下 factory 和 model_cls_or_obj 其实不需要 decorator
        # 简化为直接注册
        _registry.register(model_type, factory=factory)
        return factory
    return decorator


# ============================================================
# 内置适配器工厂函数
# ============================================================


def _dashscope_factory(**kwargs: Any) -> DashScopeChatModel:
    """DashScope 模型工厂。

    从配置和环境变量中提取 api_key 和必要参数。
    优先级: 配置字典 > 环境变量 DASHSCOPE_API_KEY
    """
    api_key = kwargs.pop("api_key", None) or os.getenv("DASHSCOPE_API_KEY", "")
    model_name = kwargs.pop("model_name", "qwen-max")
    stream = kwargs.pop("stream", True)

    # 部分模型需要多模态 API，但 AgentScope 的自动检测
    # （仅检查 -vl 后缀和 qvq 前缀）无法识别。
    multimodality = kwargs.pop("multimodality", False)

    # 传递剩余参数给模型构造函数
    return DashScopeChatModel(
        model_name=model_name,
        api_key=api_key,
        stream=stream,
        multimodality=multimodality,
    )


def _openai_compatible_factory(**kwargs: Any) -> OpenAIChatModel:
    """OpenAI 兼容模型工厂。

    支持: OpenAI 官方 API、DeepSeek、vLLM、LM Studio 等。
    通过 client_kwargs.base_url 指定自定义端点。
    """
    model_name = kwargs.pop("model_name", "gpt-4o")
    api_key = kwargs.pop("api_key", None) or os.getenv("OPENAI_API_KEY", "")
    stream = kwargs.pop("stream", True)

    # client_kwargs 用于初始化 OpenAI 客户端参数（base_url 等）
    client_kwargs: Dict[str, Any] = kwargs.pop("client_kwargs", kwargs.pop("client_args", {}) or {})
    # generate_kwargs 用于生成时参数（temperature, top_p 等）
    generate_kwargs: Dict[str, Any] = kwargs.pop("generate_kwargs", kwargs.pop("generate_args", {}) or {})

    return OpenAIChatModel(
        model_name=model_name,
        api_key=api_key,
        stream=stream,
        client_kwargs=client_kwargs if client_kwargs else None,
        generate_kwargs=generate_kwargs if generate_kwargs else None,
    )


def _ollama_factory(**kwargs: Any) -> OllamaChatModel:
    """Ollama 本地模型工厂。

    需要安装 ollama Python 包: pip install ollama>=0.1.7
    """
    model_name = kwargs.pop("model_name", "llama3")
    stream = kwargs.pop("stream", True)
    options = kwargs.pop("options", {})

    try:
        return OllamaChatModel(
            model_name=model_name,
            stream=stream,
            options=options,
        )
    except ImportError as e:
        raise ModelRegistryError(
            f"Ollama 模型需要安装 ollama Python 包: pip install ollama>=0.1.7\n"
            f"原始错误: {e}"
        ) from e


# ============================================================
# 预注册内置模型类型
# ============================================================

_registry.register("dashscope", factory=_dashscope_factory)
_registry.register("openai_compatible", factory=_openai_compatible_factory)
_registry.register("ollama", factory=_ollama_factory)


def create_model(config: Dict[str, Any]) -> ChatModelBase:
    """从配置字典创建模型实例。

    配置字典必须包含 model_type 字段，其余字段传递给对应工厂函数。

    Args:
        config: 模型配置字典，格式:
            {
                "model_type": "dashscope",       # 必填：模型类型
                "model_name": "qwen-max",       # 必填：模型名称
                "stream": True,                 # 可选：流式输出
                "api_key": "sk-xxx",            # 可选：API 密钥
                # 其余参数传递给模型构造函数
            }

    Returns:
        ChatModelBase 子类实例

    Raises:
        ModelRegistryError: model_type 未找到或缺失 model_type 字段时抛出

    Examples:
        >>> # DashScope 模型
        >>> model = create_model({
        ...     "model_type": "dashscope",
        ...     "model_name": "qwen-max",
        ...     "stream": False,
        ... })

        >>> # OpenAI 兼容模型（DeepSeek）
        >>> model = create_model({
        ...     "model_type": "openai_compatible",
        ...     "model_name": "deepseek-chat",
        ...     "stream": True,
        ...     "client_kwargs": {"base_url": "https://api.deepseek.com/v1"},
        ... })

        >>> # Ollama 本地模型（需安装 ollama 包）
        >>> model = create_model({
        ...     "model_type": "ollama",
        ...     "model_name": "qwen2.5:7b",
        ...     "stream": True,
        ... })
    """
    if not isinstance(config, dict):
        raise ModelRegistryError(f"config 必须是 dict，收到: {type(config)}")

    model_type = config.get("model_type")
    if not model_type:
        raise ModelRegistryError(
            f"配置缺少必填字段 'model_type'。当前 keys: {list(config.keys())}"
        )

    factory = _registry.get_factory(model_type)
    # 使用 config 的浅拷贝，避免修改原始配置
    config_copy = config.copy()
    return factory(**config_copy)


def list_registered_models() -> list[str]:
    """列出所有已注册的模型类型。"""
    return _registry.list_types()


def is_model_registered(model_type: str) -> bool:
    """检查模型类型是否已注册。"""
    return _registry.is_registered(model_type)
