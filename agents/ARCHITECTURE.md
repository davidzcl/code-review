# agents/ 模块架构文档

## 模块职责与边界

`agents/` 负责 AgentScope 框架下的智能代理封装，提供：
- 统一的 agent 创建接口（基于模型注册机制）
- 评审者 agent 的标准化定义与配置
- 辩论循环中各角色 agent（质疑者、辩护者、裁决者）的实现
- 质量评估 agent（可选模块）

**边界**：agent 模块不处理 Git 数据解析、报告格式化或辩论循环控制流——这些分别属于 `tools/` 和 `pipeline/`。

---

## 对外接口定义

### 1. 模型注册与工厂（已完成）

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
    "model_type": "dashscope | openai_compatible | ollama | <custom>",
    "model_name": "qwen-max",
    "stream": true,
    "api_key": "sk-xxx"
}
```

### 2. 评审者 Agent（已完成）

```python
class ReviewerAgent(ReActAgent):
    """已实现。继承 ReActAgent，完整实现 review() 方法。"""

    async def review(
        self,
        diff_chunks: list[DiffChunk],
        pr_context: PRContext
    ) -> list[Finding]
```

**Finding 数据结构**（已完成）：
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

### 3. 辩论循环 Agent（已完成）

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


class JudgeAgent:
    """
    参数:
        name: str
        model: ChatModelBase
    """
    async def adjudicate(self, debate_record: DebateRecord) -> Verdict

@dataclass
class Verdict:
    findings: list[Finding]    # 最终确认的发现列表
    dismissed: list[str]       # 被驳回的 finding_id
    merged: list[MergeRecord]  # 合并记录
    summary: str               # 评审总结
```

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
├── judge.py              # 裁决者 agent（待实现）
└── evaluator.py          # 质量评估 agent（待实现）
```

### 核心算法

- **评审者**：提示词注入 + ReActAgent 工具调用 chain，分阶段执行「理解 diff → 识别模式 → 生成发现」
- **质疑者**：接收 Finding + 代码上下文 → 生成质疑 → 评分
- **辩护者**：接收 Finding + Challenge → 查证代码 → 输出 Defense
- **裁决者**：聚合多轮 Debate → 按置信度排序 → 低于阈值丢弃 → 相似度聚类合并 → 生成 Verdict

### 数据流程

```
config.py ──→ create_model(config) ──→ ChatModelBase ──→ ReviewerAgent(model)
                                                       ──→ ProsecutorAgent(model)
                                                       ──→ DefenderAgent(model)
                                                       ──→ JudgeAgent(model)
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

## 经验总结

### structured_model 替代手工 JSON 解析

ProsecutorAgent、DefenderAgent 初始实现通过 `_parse_challenge()` / `_extract_text()` 等手工方法从 LLM 文本响应中提取 JSON 并构造数据类。经重构后，利用 AgentScope ReActAgent 内置的 `structured_model` 参数消除所有解析代码。

#### 机制

`reply(msg, structured_model=Challenge)` 触发 ReActAgent 内部流程：
1. 根据 `Challenge.model_json_schema()` 注册 `generate_response` tool
2. 强制 LLM 以 function calling 方式调用该 tool（`tool_choice="required"`）
3. `generate_response(**kwargs)` 中执行 `Challenge.model_validate(kwargs).model_dump()`
4. 结构化数据存入 `response.metadata`

调用方直接 `Challenge(**response.metadata)` 构造结果，无需任何 JSON 解析或文本提取。

#### 变更对比

| 维度 | 旧方案 | 新方案 |
|------|--------|--------|
| 代码量 | `_parse_*` + `_extract_text` 共 ~100 行/agent | 0 行 |
| 输出约束 | Prompt 中写 JSON 格式描述，模型可能偏离 | LLM function calling + pydantic schema，强制匹配 |
| 错误处理 | 手工 `try/except JSONDecodeError` | `model_validate` 自动校验类型，异常回退写在调用方 |
| 测试 | 需测试 JSON 解析、非法输入、嵌套 JSON 等边缘情况 | 删除对应测试项（~25 项），MockModel 返回 `ToolUseBlock` 模拟真实 LLM 行为 |
| 维护成本 | 每个新数据类需配套解析方法 | 继承 `BaseModel` 即自动获得 schema，无额外代码 |

#### MockModel 测试模式

```python
MockModel.__call__ 返回 ChatResponse(content=[
    TextBlock(type="text", text="分析完成"),
    ToolUseBlock(type="tool_use", id="call_1",
                 name="generate_response", input={...}),
])
```

ReActAgent 的 `_acting()` 执行 `generate_response(**input)`，通过 pydantic 校验后产出 `response.metadata`。Mock 仅需保证 `input` 字段名与 pydantic 模型字段一致。

### Finding 使用 pydantic.BaseModel 而非 @dataclass

`Finding` 数据类从 `@dataclass` 重构为 `pydantic.BaseModel`，基于以下考虑：

| 考虑 | `@dataclass` | `pydantic.BaseModel` |
|------|-------------|---------------------|
| 类型校验 | 手动 `_validate_severity()` 函数 | `@field_validator` 声明式，构造时自动触发 |
| JSON schema | 无 | `model_json_schema()` 可直接注入 LLM function calling |
| 与 ReActAgent 集成 | 不支持 `structured_model` | 可直接传入 `reply(structured_model=Finding)` 约束 LLM 输出 |
| 序列化 | 需手动 `to_dict()` | 内置 `model_dump()` / `model_dump_json()` |
| 依赖 | 标准库 | 已在 `agentscope` 传递依赖中 |

#### 关键变更模式

```python
# 旧版 @dataclass
from dataclasses import dataclass, field

@dataclass
class Finding:
    id: str = ""
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
    evidence: list[str] = field(default_factory=list)

# 新版 pydantic
from pydantic import BaseModel, Field, field_validator

class Finding(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    evidence: list[str] = Field(default_factory=list)

    @field_validator("severity")
    @classmethod
    def _check_severity(cls, v: str) -> str:
        ...
```

#### 注意点

1. **缓存失效**：`__pycache__` 中旧 bytecode 可能残留旧 dataclass 结构，模块导入后 `_ReActAgentMeta` 的 `__new__` 仍引用旧布局。重构后必须清理 `agents/__pycache__/`。
2. **异常捕获链**：pydantic 校验失败抛出 `ValidationError`（非 `ValueError`），`_parse_findings` 中的 except 子句必须追加 `ValidationError`。
3. **`from __future__ import annotations` 行为差异**：pydantic v2 在 `from __future__ import annotations` 下使用 `__pydantic_fields__` 而非 `__annotations__` 解析字段。字段定义必须使用 pydantic 类型（如 `List[str]` 而非 `list[str]`）以确保正确校验。

