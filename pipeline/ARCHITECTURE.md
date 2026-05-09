# pipeline/ 模块架构文档

## 模块职责与边界

`pipeline/` 负责系统的调度编排逻辑（workflow orchestration），包括：
- 多评审者并行调度与结果汇总
- 结构化辩论循环引擎（控制流）
- 发现合并规则引擎
- 最终裁决决策逻辑

**边界**：
- pipeline/ 不直接调用 LLM API — 由 `agents/` 负责
- pipeline/ 不处理 Git 数据解析 — 由 `tools/` 负责
- pipeline/ 是纯调度/规则层，编排 agent 交互序列，不定义 agent 技能

---

## 对外接口定义

### 0. 多评审者并行调度（已完成）

```python
@dataclass
class ParallelReviewResult:
    findings: list[Finding]
    reviewer_results: dict[str, list[Finding]]
    total_reviewers: int
    successful_reviewers: int
    failed_reviewers: list[str]

class ParallelReviewManager:
    def __init__(self, reviewers: list[ReviewerAgent], timeout: int = 300)
    async def run_all(diff_chunks, pr_context) -> ParallelReviewResult
    def get_findings_by_reviewer() -> dict[str, list[Finding]]
    def get_findings_by_role() -> dict[str, list[Finding]]
    def get_findings_by_severity() -> dict[str, list[Finding]]
    def get_statistics() -> dict
```

### 1. 辩论循环引擎（已完成）

```python
@dataclass
class DebateRecord:
    finding_id: str
    original_finding: Finding
    rounds: list[DebateRound]
    final_status: str               # confirmed | dismissed
    merged_into: str | None

@dataclass
class DebateRound:
    round_number: int
    challenge: Challenge | None
    defense: Defense | None
    rebuttal: str | None

async def run_debate_loop(
    findings: list[Finding],
    prosecutor: ProsecutorAgent,
    defender: DefenderAgent,
    diff_context: str,
    max_rounds: int = 3,
    confidence_threshold: float = 0.6,
) -> list[DebateRecord]
```

### 2. 发现合并规则（已完成）

```python
@dataclass
class MergeRecord:
    primary_id: str
    merged_ids: list[str]
    merge_reason: str
    merged_finding: Finding

def merge_similar_findings(
    debate_records: list[DebateRecord],
    similarity_threshold: float = 0.8,
) -> list[MergeRecord]

def compute_finding_similarity(f1: Finding, f2: Finding) -> float
```

#### 相似度算法

| 维度 | 权重 | 计算方法 |
|------|------|----------|
| 文件路径 | 0.40 | 完全相同得满分 |
| 行范围 | 0.30 | Jaccard 重叠度（仅在相同文件中计算） |
| 标题+描述 | 0.20 | 单词级 Jaccard 相似度 |
| 严重级别 | 0.05 | 完全相同得满分 |
| 评审维度 | 0.05 | 完全相同得满分 |

#### 合并策略

- 仅合并 `final_status == "confirmed"` 的发现
- 按严重级别降序排列，更严重的问题作为 primary
- 贪心聚类：从头遍历，以第一个发现为基准合并后续相似发现
- 已合并的发现跳过后续比较

### 3. 最终裁决逻辑（已完成）

```python
@dataclass
class Verdict:
    findings: list[Finding]    # 最终确认的发现列表（已去重合并）
    dismissed: list[str]       # 被驳回的 finding_id
    merged: list[MergeRecord]  # 合并记录
    summary: str               # 评审总结（含统计信息）

def make_final_verdict(
    debate_records: list[DebateRecord],
    merge_records: list[MergeRecord],
) -> Verdict
```

#### 处理流程

1. 从辩论记录提取 confirmed/dismissed 发现
2. 按合并记录移除被 merged 的 finding（保留 primary）
3. 生成总结文本，含数量统计和严重级别分布

### 4. 系统入口编排 — main.py（待实现，F-16）

`main.py` 暴露单一异步函数 `run_review_pipeline`，按固定顺序调用 pipeline 各组件。

```python
# 输入
class ReviewRequest:
    base: str | None            # Git base commit，默认取 GIT_BASE 环境变量
    target: str | None          # Git target commit
    staged_only: bool = False   # 仅 staged 变更
    file_filter: str | None     # 文件过滤 glob
    pr_text: str | None         # PR 描述文本（可选，无 PR 则传 None）
    max_debate_rounds: int = 3  # 覆盖 config 默认值
    confidence_threshold: float = 0.6

# 输出
class ReviewResponse:
    verdict: Verdict                       # 最终裁决
    debate_records: list[DebateRecord]     # 完整辩论记录
    review_result: ParallelReviewResult    # 并行评审原始结果
    report_markdown: str                   # MD 格式报告
    report_html: str                       # HTML 格式报告
    findings_json: str                     # findings.json 内容
    duration_seconds: float                # 总耗时

async def run_review_pipeline(request: ReviewRequest) -> ReviewResponse
```

**编排流程**：
1. `git_diff()` → raw diff
2. `parse_diff()` → `list[DiffChunk]`；`parse_pr_description()` → `PRContext`
3. 前置 guardrail：`scan_secrets()` + `scan_risk_signals()` → 结果注入 reviewer prompt
4. `ParallelReviewManager.run_all()` → `list[Finding]`
5. `run_debate_loop()` → `list[DebateRecord]`
6. `merge_similar_findings()` → `list[MergeRecord]`
7. `make_final_verdict()` → `Verdict`
8. `generate_report()` → 落盘到 `OUTPUT_DIR`

**错误处理矩阵**：

| 错误场景 | 处理策略 |
|----------|----------|
| 缺少 base/target 且无环境变量 | 抛出 `ValueError`，不启动流程 |
| `OUTPUT_DIR` 不存在 | 自动创建目录 |
| 单个 reviewer 超时/异常 | 不影响其他 reviewer（已实现） |
| prosecutor/defender 异常 | 回退默认值（已实现） |
| 空 diff | 跳过评审，返回空结果（已实现） |

---

## 内部实现架构

### 模块划分

```
pipeline/
├── __init__.py           # 包入口
├── parallel_review.py    # 多评审者并行调度（从 skills/ 迁移）
├── debate_loop.py        # 辩论循环引擎（已完成）
├── issue_merger.py       # 发现合并规则（已完成）
└── verdict.py            # 裁决逻辑（已完成）
```

---

## 依赖关系

### 外部依赖

| 依赖 | 类型 | 用途 |
|------|------|------|
| `asyncio` | 标准库 | 并行任务调度、超时控制 |
| `dataclasses` | 标准库 | 数据结构定义 |

### 内部依赖

| 依赖 | 类型 | 交互方式 | 数据格式 |
|------|------|----------|----------|
| `agents.reviewer` | 单向依赖 | 导入 Finding 类型、ReviewerAgent | Python class/dataclass |
| `agents.prosecutor` | 单向依赖 | 导入 ProsecutorAgent、Challenge | Python class/dataclass |
| `agents.defender` | 单向依赖 | 导入 DefenderAgent、Defense | Python class/dataclass |
| `tools.diff_parser` | 单向依赖 | 导入 DiffChunk 类型 | Python dataclass |
| `tools.pr_parser` | 单向依赖 | 导入 PRContext 类型 | Python dataclass |
| `logger` | 单向依赖 | 获取日志器 | Python module |

## 常见错误与解决方案

> 完整记录参见 `docs/errors-and-resolutions.md` §3。