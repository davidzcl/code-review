# skills/ 模块架构文档

## 模块职责与边界

`skills/` 负责实现系统的核心业务逻辑（非 AI agent 部分），包括：
- 结构化辩论循环引擎（控制流）
- 发现合并规则引擎
- 证据收集与关联逻辑
- 最终裁决决策逻辑

**边界**：skills/ 不直接调用 LLM API、不处理 Git 数据——LLM 调用由 `agents/` 负责，数据由 `tools/` 负责。skills/ 是纯业务规则层。

---

## 对外接口定义

### 1. 辩论循环引擎（待实现）

```python
@dataclass
class DebateRecord:
    finding_id: str
    original_finding: Finding
    rounds: list[DebateRound]
    final_status: str               # confirmed | dismissed | merged
    merged_into: str | None         # 如被合并，指向主 finding_id

@dataclass
class DebateRound:
    round_number: int
    challenge: Challenge | None
    defense: Defense | None
    rebuttal: str | None            # 反驳内容

async def run_debate_loop(
    findings: list[Finding],
    prosecutor: ProsecutorAgent,
    defender: DefenderAgent,
    diff_context: str,
    max_rounds: int = 3,
    confidence_threshold: float = 0.6,
) -> list[DebateRecord]
    """
    对所有候选问题执行辩论循环。

    参数:
        findings:             评审者生成的候选问题列表
        prosecutor:           质疑者 agent 实例
        defender:             辩护者 agent 实例
        diff_context:         原始 diff 上下文（供辩护者查证）
        max_rounds:           最大辩论轮次
        confidence_threshold: 置信度阈值，低于此值的问题被驳回

    返回:
        DebateRecord 列表，每条记录包含完整辩论过程

    流程:
        1. 对每个 finding 执行辩论:
           a. 质疑者生成 Challenge
           b. 若质疑不成立(is_valid=False)，finding 直接确认
           c. 若质疑成立，辩护者生成 Defense
           d. 若辩护失败(finding_stands=False)，finding 被驳回
           e. 若辩护成功且未达 max_rounds，进入反驳轮次
           f. 达到 max_rounds 或共识后终止
        2. 置信度过滤
        3. 返回所有 DebateRecord
    """
```

### 2. 发现合并规则引擎（待实现）

```python
@dataclass
class MergeRecord:
    primary_id: str                  # 主 finding_id
    merged_ids: list[str]            # 被合并的 finding_id 列表
    merge_reason: str                # 合并原因
    merged_finding: Finding          # 合并后的 finding

def merge_similar_findings(
    debate_records: list[DebateRecord],
    similarity_threshold: float = 0.8,
) -> list[MergeRecord]
    """
    合并语义相似的发现。

    参数:
        debate_records:        辩论完成的记录列表
        similarity_threshold:  相似度阈值

    返回:
        合并记录列表

    合并规则:
        1. 同一文件 + 行范围重叠 → 自动合并
        2. 不同文件但相同错误模式 → 合并到首次出现的文件
        3. 标题文本相似度 > threshold → 候选合并
        4. 不同评审维度但指向同一代码段 → 保留 severity 最高的
    """

def compute_finding_similarity(f1: Finding, f2: Finding) -> float:
    """
    计算两个发现的语义相似度 (0.0-1.0)。

    基于:
        - 文件路径重叠度 (30%)
        - 行范围重叠度 (20%)
        - 标题文本 Jaccard 相似度 (30%)
        - 严重级别一致性 (20%)
    """
```

### 3. 最终裁决逻辑（待实现）

```python
def make_final_verdict(
    debate_records: list[DebateRecord],
    merge_records: list[MergeRecord],
) -> Verdict
    """
    基于辩论记录和合并记录生成最终裁决。

    参数:
        debate_records: 辩论记录
        merge_records:  合并记录

    返回:
        Verdict 对象

    裁决规则:
        1. confirmed 且 confidence ≥ threshold → 纳入报告
        2. 合并后的 finding 取最高 severity
        3. 按 severity 降序排列
        4. 生成评审摘要文本
    """
```

---

## 内部实现架构

### 模块划分

```
skills/
├── __init__.py           # 包入口
├── debate_loop.py        # 辩论循环引擎（待实现）
│   ├── run_debate_loop()
│   └── _single_debate()  # 单个 finding 的辩论
├── issue_merger.py       # 发现合并规则（待实现）
│   ├── merge_similar_findings()
│   └── compute_finding_similarity()
└── verdict.py            # 裁决逻辑（待实现）
    └── make_final_verdict()
```

### 核心算法

**辩论循环算法（伪代码）**：
```
for each finding in findings:
    round = 0
    while round < max_rounds:
        challenge = await prosecutor.challenge(finding)
        if not challenge.is_valid:
            finding.confirmed = True; break

        defense = await defender.defend(finding, challenge, diff_context)
        if not defense.finding_stands:
            finding.confirmed = False; break

        # 更新 finding 信息
        finding.confidence = defense.revised_confidence or finding.confidence
        finding.severity = defense.revised_severity or finding.severity

        round += 1

    # 最终检查
    finding.confirmed = finding.confidence >= confidence_threshold
```

**合并算法（伪代码）**：
```
1. 按文件路径分组
2. 组内按起始行排序
3. 相邻 finding 检查行范围重叠 → 合并
4. 跨组检查标题相似度 > threshold → 候选
5. 对候选对：LLM 辅助判断是否为同一问题 → 合并/保留
```

### 数据流程

```
[agents/reviewer.py × 4] ──→ findings: list[Finding]
                                    │
                                    ▼
[skills/debate_loop.py]            ← [agents/prosecutor.py]
  run_debate_loop()                ← [agents/defender.py]
  ──→ debate_records: list[DebateRecord]
                                    │
                                    ▼
[skills/issue_merger.py]           ← [tools/diff_parser.py]
  merge_similar_findings()
  ──→ merge_records: list[MergeRecord]
                                    │
                                    ▼
[skills/verdict.py]
  make_final_verdict()
  ──→ Verdict
```

---

## 依赖关系

| 依赖 | 类型 | 交互方式 | 数据格式 |
|------|------|----------|----------|
| `agents.prosecutor` | 接口依赖 | 传入实例，调用 async challenge() | Finding → Challenge |
| `agents.defender` | 接口依赖 | 传入实例，调用 async defend() | (Finding, Challenge, str) → Defense |
| `agents.reviewer` | 类型依赖 | 导入 Finding 数据类 | Python dataclass |
| `agents.judge` | 类型依赖 | 导入 Verdict 数据类 | Python dataclass |
| `config.py` | 配置依赖 | 导入阈值和限制常量 | Python 模块属性 |
