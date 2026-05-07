# agents/ 模块架构文档

## 模块职责与边界

`agents/` 负责 AgentScope 框架下的智能代理封装，提供：
- 统一的 agent 创建接口（基于模型注册机制）
- 评审者 agent 的标准化定义与配置
- 辩论循环中各角色 agent（质疑者、辩护者、裁决者）的实现
- 质量评估 agent（可选模块）

**边界**：agent 模块不处理 Git 数据解析、报告格式化或辩论循环控制流——这些分别属于 `tools/` 和 `skills/`。

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

### 2. 评审者 Agent（待实现）

```python
class ReviewerAgent(ReActAgent):
    """
    参数:
        name: str                   - agent 名称
        role: str                   - security|performance|logic|style
        sys_prompt: str             - 系统提示词
        model: ChatModelBase        - 模型实例（来自 create_model）
        formatter: FormatterBase    - 消息格式化器
    """
    async def review(
        self,
        diff_chunks: list[DiffChunk],
        pr_context: PRContext
    ) -> list[Finding]
```

**Finding 数据结构**：
```python
@dataclass
class Finding:
    id: str                    # 唯一标识
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
```

### 3. 辩论循环 Agent（待实现）

```python
class ProsecutorAgent:
    """
    参数:
        name: str
        model: ChatModelBase
    """
    async def challenge(self, finding: Finding) -> Challenge

@dataclass
class Challenge:
    finding_id: str
    is_valid: bool             # 质疑是否成立
    reasons: list[str]         # 质疑理由
    confidence: float


class DefenderAgent:
    """
    参数:
        name: str
        model: ChatModelBase
    """
    async def defend(
        self,
        finding: Finding,
        challenge: Challenge,
        diff_context: str       # 相关代码上下文
    ) -> Defense

@dataclass
class Defense:
    finding_id: str
    challenge_id: str
    finding_stands: bool       # 原始发现是否成立
    counter_evidence: list[str]
    revised_severity: str | None
    revised_confidence: float | None


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
├── base.py               # AgentScope 基础 agent 封装（待实现）
├── reviewer.py           # 评审者 agent（待实现）
├── prosecutor.py         # 质疑者 agent（待实现）
├── defender.py           # 辩护者 agent（待实现）
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
| `skills.debate_loop` | 被调用方 | 被 debate_loop 作为参数传入 | Python 类实例 |
