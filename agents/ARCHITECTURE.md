# agents/ 模块架构文档

## 模块职责与边界

`agents/` 负责 AgentScope 框架下的智能代理封装，提供：
- 统一的 agent 创建接口（基于模型注册机制）
- 评审者 agent 的标准化定义与配置
- 辩论循环中各角色 agent（质疑者、辩护者）的实现
- 质量评估 agent（可选模块）

**边界**：agent 模块不处理 Git 数据解析、报告格式化或辩论循环控制流——这些分别属于 `tools/` 和 `pipeline/`。

---

## 对外接口定义

### 1. 模型注册与工厂

```python
# 工厂函数
def create_model(config: dict) -> ChatModelBase

# 装饰器注册
@register_model("model_type_str")
class MyModel(ChatModelBase): ...

# 查询
def list_registered_models() -> list[str]
def is_model_registered(model_type: str) -> bool

# 异常
class ModelRegistryError(Exception)
```

**配置字典格式**：
```json
{
    "model_type": "dashscope | openai | deepseek | ollama | <custom>",
    "model_name": "qwen-max",
    "stream": true,
    "api_key": "sk-xxx",
    "multimodality": False,
}
```

### 1.5. Formatter 注册与工厂

不同 `model_type` 对应不同的消息格式要求，`formatter_registry.py` 提供基于 `model_type` 的 formatter 自动创建。

```python
# 工厂函数
def create_formatter(model_type: str, **kwargs) -> FormatterBase

# 装饰器注册
@register_formatter("model_type_str")
class MyFormatter(FormatterBase): ...

# 查询
def list_registered_formatters() -> list[str]
def is_formatter_registered(model_type: str) -> bool

# 自推断（无显式 formatter 时根据 model 实例判断）
# DeepSeek 通过 model_name 中是否包含 "deepseek" 判定
def infer_formatter_type(model: ChatModelBase) -> str

# 异常
class FormatterRegistryError(Exception)
```

**预注册映射**：

| model_type | Model 类 | Formatter 类 |
|------------|----------|-------------|
| `dashscope` | `DashScopeChatModel` | `DashScopeChatFormatter` |
| `openai` | `OpenAIChatModel` | `OpenAIChatFormatter` |
| `deepseek` | `OpenAIChatModel` | `DeepSeekChatFormatter` |
| `ollama` | `OllamaChatModel` | `OllamaChatFormatter` |

### 2. 评审者 Agent

```python
class ReviewerAgent(ReActAgent):
    """已实现。继承 ReActAgent，完整实现 review() 方法。"""

    async def review(
        self,
        diff_chunks: list[DiffChunk],
        pr_context: PRContext
    ) -> list[Finding]
```

**Finding 数据结构**：
```python
class Finding(BaseModel):
    id: str                    # 唯一标识，自动生成 uuid4
    reviewer: str              # 评审者名称
    role: str                  # 评审维度
    severity: str              # critical|important|minor
    file_path: str             # 涉及文件
    line_range: tuple[int,int] # 行范围
    title: str                 # 问题标题
    description: str           # 详细描述
    suggestion: str            # 修复建议
    confidence: float          # 置信度 0.0-1.0
    evidence: list[str]        # 支持证据

class AgentInitializationError(Exception):
    """已实现。Agent 初始化失败的异常。"""
```

### 3. 辩论循环 Agent

```python
class Challenge(BaseModel):
    finding_id: str
    is_valid: bool             # 质疑是否成立
    reasons: list[str]         # 质疑理由
    confidence: float


class Defense(BaseModel):
    finding_id: str
    challenge_id: str
    finding_stands: bool       # 原始发现是否成立
    counter_evidence: list[str]
    revised_severity: str | None
    revised_confidence: float | None


class ProsecutorAgent:
    """已实现。"""
    def __init__(self, name: str, model: ChatModelBase)
    async def challenge(self, finding: Finding) -> Challenge


class DefenderAgent:
    """已实现。"""
    def __init__(self, name: str, model: ChatModelBase)
    async def defend(
        self,
        finding: Finding,
        challenge: Challenge,
        diff_context: str       # 相关代码上下文
    ) -> Defense
```

### 4. 质量评估 Agent

```python
class EvaluationResult(BaseModel):
    score: float               # 总体评分 0.0~1.0
    coverage_score: float      # 覆盖率评分
    clarity_score: float       # 清晰度评分
    actionability_score: float # 可操作性评分
    summary: str               # 评估总结
    improvement_suggestions: list[str]  # 改进建议


class EvaluatorAgent(ReActAgent):
    """继承 ReActAgent，对报告进行质量评估。"""

    async def evaluate(
        self,
        verdict: Verdict,
        pr_context: PRContext,
    ) -> EvaluationResult
```

**评分规则**：
- 覆盖率 = reviewer role 种类数 / 4（security, performance, logic, style）
- 清晰度 = 有 file_path + line_range 的发现比例
- 可操作性 = 有 suggestion 的发现比例
- 总体评分 = coverage×0.30 + clarity×0.40 + actionability×0.30

**错误处理**：
- `ModelRegistryError`：模型类型未注册
- `AgentInitializationError`：agent 初始化失败（缺少必要参数）
- 所有 `async __call__` 通过 AgentScope 内置 tracing 记录异常

---

## 内部实现架构

### 模块划分

```
agents/
├── __init__.py           # 包入口
├── model_registry.py     # 模型注册（已完成）
│   ├── _ModelRegistry    # 单例注册表
│   ├── register_model()  # 装饰器/显式注册
│   ├── create_model()    # 工厂函数
│   └── 内置工厂函数
├── formatter_registry.py # Formatter 注册（已完成）
│   ├── _FormatterRegistry # 单例注册表
│   ├── register_formatter()  # 装饰器/显式注册
│   ├── create_formatter()    # 工厂函数
│   └── infer_formatter_type() # model 实例 → model_type 推断
├── base.py               # 基础异常定义（已完成）
├── reviewer.py           # 评审者 agent（已完成）
│   ├── Finding           # 评审发现数据类
│   ├── ReviewerAgent     # 评审者 Agent 基类（继承 ReActAgent）
│   └── review()          # 标准评审入口
├── prosecutor.py         # 质疑者 agent（已完成）
│   ├── Challenge          # 质疑数据类（pydantic BaseModel）
│   └── ProsecutorAgent    # 质疑者 Agent（async challenge）
├── defender.py           # 辩护者 agent（已完成）
│   ├── Defense            # 辩护数据类（pydantic BaseModel）
│   └── DefenderAgent      # 辩护者 Agent（async defend）
└── evaluator.py          # 质量评估模块（已完成）
```

### 核心算法

- **评审者**：提示词注入 + ReActAgent 工具调用 chain，分阶段执行「理解 diff → 识别模式 → 生成发现」
- **质疑者**：接收 Finding + 代码上下文 → 生成质疑 → 评分
- **辩护者**：接收 Finding + Challenge → 查证代码 → 输出 Defense
- **裁决**：辩论记录 + 合并记录 → `pipeline/verdict.py` 纯规则引擎聚合（confirmed/dismissed 提取 + 去重 + 统计），无 LLM 调用

### 数据流程

```
config.py ──→ create_model(config) ──→ ChatModelBase ──→ ReviewerAgent(model)
           ──→ create_formatter(model_type) ──→ FormatterBase ──→ ReviewerAgent(formatter)
                                                       ──→ ProsecutorAgent(model, formatter)
                                                       ──→ DefenderAgent(model, formatter)
                                                       ──→ EvaluatorAgent(model, formatter)
```

---

## 依赖关系

### 外部依赖

| 依赖 | 类型 | 交互方式 | 数据格式 |
|------|------|----------|----------|
| `agentscope.model` | 框架依赖 | 继承 ChatModelBase | Python 类/对象 |
| `agentscope.agent` | 框架依赖 | ReActAgent, UserAgent | Python 类/对象 |
| `agentscope.formatter` | 框架依赖 | 合成 formatter 实例 | Python 类/对象 |
| `agentscope.memory` | 框架依赖 | InMemoryMemory | Python 类/对象 |
| `agentscope.tool` | 框架依赖 | Toolkit 注册工具函数 | Python 函数引用 |

### 内部依赖

| 依赖 | 类型 | 交互方式 | 数据格式 |
|------|------|----------|----------|
| `config.py` | 单向依赖 | 导入配置常量 | Python 模块属性 |
| `tools.diff_parser` | 单向依赖 | 导入 DiffChunk 类型 | Python dataclass |
| `tools.pr_parser` | 单向依赖 | 导入 PRContext 类型 | Python dataclass |
| `pipeline.debate_loop` | 被调用方 | 被 debate_loop 作为参数传入 | Python 类实例 |

---

## 常见错误与解决方案

> 完整记录参见 `docs/errors-and-resolutions.md` §2 + §4。

---

## 经验总结

### structured_model 机制

ProsecutorAgent、DefenderAgent 利用 AgentScope ReActAgent 内置的 `structured_model` 参数消除手工 JSON 解析。
`structured_model` 使用 `pydantic.BaseModel` 定义数据类，`@field_validator` 声明式校验，构造时自动触发。
`reply(msg, structured_model=xxx)` 触发 function calling，通过 pydantic schema 强制约束 LLM 输出，
结构化数据存入 `response.metadata`。

**MockModel 模式**：返回 `ChatResponse` 含 `ToolUseBlock`，`input` 字段名须与 pydantic 模型字段一致。

**注意**：
1. 模块重构后必须清理 `__pycache__`，避免旧 bytecode 残留
2. pydantic 校验失败抛出 `ValidationError`，非 `ValueError`
3. `from __future__ import annotations` 下须使用 pydantic 类型确保正确校验

