"""模型注册机制验证脚本"""

import sys
sys.path.insert(0, r"d:\project\code-review")

from agents import (
    create_model,
    register_model,
    list_registered_models,
    is_model_registered,
    ModelRegistryError,
)

# 1. 内置模型类型
types = list_registered_models()
print(f"1. 已注册模型类型: {types}")
assert "dashscope" in types
assert "openai_compatible" in types
assert "ollama" in types
print("   [PASS]")

# 2. DashScope 模型创建
model = create_model({
    "model_type": "dashscope",
    "model_name": "qwen-max",
    "stream": False,
    "api_key": "test-key",
})
assert type(model).__name__ == "DashScopeChatModel"
print(f"2. DashScope 模型: {type(model).__name__} [PASS]")

# 3. OpenAI 兼容模型创建
model2 = create_model({
    "model_type": "openai_compatible",
    "model_name": "gpt-4o",
    "stream": True,
})
assert type(model2).__name__ == "OpenAIChatModel"
print(f"3. OpenAI 兼容模型: {type(model2).__name__} [PASS]")

# 4. 自定义模型注册与创建
from agentscope.model import ChatModelBase, ChatResponse


@register_model("verify_custom_model")
class VerifyCustomModel(ChatModelBase):
    async def __call__(self, *args, **kwargs):
        return ChatResponse(content=[])


assert is_model_registered("verify_custom_model")
cm = create_model({
    "model_type": "verify_custom_model",
    "model_name": "v",
    "stream": False,
})
assert type(cm).__name__ == "VerifyCustomModel"
print(f"4. 自定义模型装饰器: {type(cm).__name__} [PASS]")

# 5. 非法 model_type 异常
try:
    create_model({"model_type": "nonexistent"})
    assert False, "应该抛出异常"
except ModelRegistryError:
    print("5. 非法 model_type 异常 [PASS]")

# 6. 缺失 model_type 异常
try:
    create_model({"model_name": "test"})
    assert False, "应该抛出异常"
except ModelRegistryError:
    print("6. 缺失 model_type 异常 [PASS]")

# 7. config.py 导入
from config import (
    DASHSCOPE_API_KEY,
    DEFAULT_DASHSCOPE_MODEL_CONFIG,
    DEFAULT_REVIEWER_PROFILES,
    get_model_config,
    output_path,
)
assert DASHSCOPE_API_KEY
assert len(DEFAULT_REVIEWER_PROFILES) == 4
cfg = get_model_config("dashscope")
assert cfg["model_type"] == "dashscope"
print(f"7. config.py: {len(DEFAULT_REVIEWER_PROFILES)} 个评审者角色 [PASS]")

print("\n全部验证通过!")
