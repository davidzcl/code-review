# evaluation/ 模块架构文档

## 模块职责与边界

`evaluation/` 负责智能体评测系统的完整实现，包括：

- 多维度评测指标设计与计算
- 单智能体评测基准（ReviewerBenchmark）
- 流程评测基准（PipelineBenchmark）
- 合成测试用例数据集构建
- 评测报告生成（MD/HTML）
- CI/CD 集成配置

**边界**：

- evaluation/ 不直接调用 LLM API — 测试中必须 mock
- evaluation/ 不修改代码库 — 只读访问
- evaluation/ 是独立评测层，不参与生产评审流程

***

## 对外接口定义

### 1. 评测指标模块（metrics/）

#### 1.1 稳定性指标

```python
@dataclass
class StabilityResult:
    findings: List[Finding]
    timestamp: datetime

class StabilityMetric:
    """输出稳定性评测
    
    计算维度：
    - 结构一致性：相同字段出现频率
    - KL散度：严重级别分布一致性
    """
    
    def __init__(self, n_runs: int = 3)
    
    def calculate_structural_consistency(
        self, 
        results: List[StabilityResult]
    ) -> float
        """计算结构一致性，返回 0.0-1.0"""
    
    def calculate_kl_divergence(
        self,
        results: List[StabilityResult]
    ) -> float
        """计算 KL 散度，值越小越稳定"""
```

#### 1.2 延迟指标

```python
@dataclass
class LatencyResult:
    start_time: float
    end_time: float
    total_latency_ms: float

class LatencyMetric:
    """响应延迟评测
    
    计算维度：
    - P50/P95/P99 百分位数
    - 平均/最小/最大延迟
    """
    
    def record(self, result: LatencyResult) -> None
        """记录单次延迟"""
    
    def calculate_percentiles(self) -> Dict[str, float]
        """返回 {p50, p95, p99, avg, min, max}"""
```

#### 1.3 工具调用指标

```python
@dataclass
class ToolCallRecord:
    tool_name: str
    parameters: Dict[str, Any]
    success: bool
    error: Optional[str] = None

@dataclass
class ToolCallAnalysisResult:
    total_calls: int
    successful_calls: int
    failed_calls: int
    tool_distribution: Dict[str, int]
    success_rate: float

class ToolCallMetric:
    """工具调用准确率评测
    
    计算维度：
    - 工具选择准确率
    - 参数准确率
    - 调用成功率
    """
    
    def analyze(self, trajectory: List[ToolCallRecord]) -> ToolCallAnalysisResult
```

#### 1.4 Finding 评判指标

```python
@dataclass
class FindingMatchResult:
    finding_id: str
    matched_ground_truth: Optional[str]
    similarity_score: float
    is_true_positive: bool

@dataclass
class BatchEvaluationResult:
    total_findings: int
    true_positives: int
    false_positives: int
    false_negatives: int
    recall: float
    precision: float
    f1_score: float

class FindingJudge:
    """LLM-as-Judge 评估
    
    使用强模型（qwen-max）作为裁判评估 Finding 质量
    """
    
    def __init__(self, model_name: str = "qwen-max", temperature: float = 0.0)
    
    async def evaluate(
        self,
        finding: Finding,
        ground_truth: InjectedIssue
    ) -> FindingMatchResult
    
    async def evaluate_batch(
        self,
        findings: List[Finding],
        ground_truths: List[InjectedIssue]
    ) -> BatchEvaluationResult
```

#### 1.5 流程评测指标

```python
@dataclass
class StageMetrics:
    stage_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    success: bool
    error: Optional[str]

@dataclass
class DebateMetrics:
    total_findings: int
    confirmed_count: int
    dismissed_count: int
    confirmation_rate: float
    avg_rounds_per_finding: float

@dataclass
class MergeMetrics:
    total_findings: int
    merged_groups: int
    merge_rate: float
    avg_similarity: float

@dataclass
class ResourceMetrics:
    total_llm_calls: int
    total_tokens: int
    avg_tokens_per_call: float

@dataclass
class PipelineResult:
    pipeline_id: str
    start_time: datetime
    end_time: datetime
    total_duration_ms: float
    stage_metrics: List[StageMetrics]
    debate_metrics: Optional[DebateMetrics]
    merge_metrics: Optional[MergeMetrics]
    resource_metrics: Optional[ResourceMetrics]

class PipelineMetrics:
    """流程评测指标计算器"""
    
    def record(self, result: PipelineResult) -> None
    def calculate_stage_statistics(self) -> Dict[str, Dict[str, float]]
    def calculate_debate_statistics(self) -> Dict[str, float]
    def get_summary(self) -> Dict[str, Any]
```

### 2. 评测基准模块（benchmark/）

#### 2.1 单智能体评测

```python
@dataclass
class BenchmarkConfig:
    n_runs: int = 3
    temperature: float = 0.0
    categories: Optional[List[IssueCategory]] = None
    max_cases_per_category: Optional[int] = None
    judge_model: str = "qwen-max"

@dataclass
class TestCaseResult:
    test_case_id: str
    test_case_name: str
    category: IssueCategory
    difficulty: str
    finding_recall: float
    finding_precision: float
    finding_f1: float
    latency_ms: float
    stability_score: float
    error: Optional[str] = None

@dataclass
class BenchmarkResult:
    agent_name: str
    agent_role: str
    config: BenchmarkConfig
    start_time: datetime
    end_time: Optional[datetime]
    total_cases: int
    successful_cases: int
    failed_cases: int
    avg_recall: float
    avg_precision: float
    avg_f1: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    avg_stability: float
    avg_tool_success_rate: float
    case_results: List[TestCaseResult]
    category_results: Dict[str, Dict[str, float]]

class ReviewerBenchmark:
    """ReviewerAgent 评测基准
    
    评测维度：
    - Finding 检出准确率（召回率/精确率/F1）
    - 响应延迟（P50/P95/P99）
    - 输出稳定性
    - 工具调用成功率
    """
    
    def __init__(self, config: Optional[BenchmarkConfig] = None)
    
    def load_test_cases(
        self,
        categories: Optional[List[IssueCategory]] = None,
        max_per_category: Optional[int] = None
    ) -> None
    
    async def run_benchmark(
        self,
        agent_factory: Callable[[], Any],
        agent_name: str = "ReviewerAgent",
        agent_role: str = "reviewer"
    ) -> BenchmarkResult
    
    def run_benchmark_sync(self, ...) -> BenchmarkResult
```

#### 2.2 流程评测

```python
@dataclass
class PipelineBenchmarkConfig:
    max_debate_rounds: int = 3
    confidence_threshold: float = 0.6
    merge_similarity_threshold: float = 0.8
    parallel_timeout: int = 300
    track_resources: bool = True

@dataclass
class PipelineBenchmarkResult:
    pipeline_id: str
    config: PipelineBenchmarkConfig
    start_time: datetime
    end_time: Optional[datetime]
    parallel_review_result: Optional[ParallelReviewResult]
    debate_records: List[DebateRecord]
    merge_records: List[MergeRecord]
    verdict: Optional[Verdict]
    pipeline_result: Optional[PipelineResult]

class PipelineBenchmark:
    """流程评测基准
    
    评测完整评审流程：
    - 并行评审阶段
    - 辩论循环阶段
    - 合并阶段
    - 裁决阶段
    """
    
    def __init__(self, config: Optional[PipelineBenchmarkConfig] = None)
    
    async def run_pipeline(
        self,
        reviewers: List[Any],
        prosecutor: Any,
        defender: Any,
        diff_chunks: List[DiffChunk],
        pr_context: Optional[PRContext] = None,
        diff_context: str = ""
    ) -> PipelineBenchmarkResult
    
    def get_summary(self) -> Dict[str, Any]

def run_pipeline_benchmark(...) -> PipelineBenchmarkResult
    """同步运行流程评测"""
```

### 3. 测试用例数据集（datasets/）

#### 3.1 数据结构定义

```python
class IssueCategory(str, Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    LOGIC = "logic"
    STYLE = "style"

@dataclass
class InjectedIssue:
    category: IssueCategory
    severity: str              # critical | high | medium | low
    title: str
    description: str
    file_path: str
    line_range: Tuple[int, int]
    detection_hints: List[str]

@dataclass
class SyntheticTestCase:
    id: str
    name: str
    category: IssueCategory
    difficulty: str            # easy | medium | hard
    diff_chunks: List[DiffChunkSchema]
    pr_context: Optional[PRContextSchema]
    injected_issues: List[InjectedIssue]
```

#### 3.2 预定义测试用例

| 数据集 | 文件                    | 用例数 | 覆盖问题类型               |
| --- | --------------------- | --- | -------------------- |
| 安全类 | security\_cases.py    | 30  | SQL注入、XSS、硬编码密钥、命令注入 |
| 性能类 | performance\_cases.py | 25  | N+1查询、O(n²)复杂度、内存泄漏  |
| 逻辑类 | logic\_cases.py       | 25  | 空指针检查、边界条件、类型错误      |
| 风格类 | style\_cases.py       | 20  | 命名规范、代码重复、复杂度        |
| 端到端 | e2e\_cases.py         | 9   | 多类型混合、完整流程           |

### 4. 报告生成模块（reporter/）

#### 4.1 Markdown 报告

```python
class MDReporter:
    """Markdown 格式报告生成器"""
    
    def generate(self, result: BenchmarkResult) -> str
        """生成完整 Markdown 报告"""
    
    def save(self, result: BenchmarkResult, file_path: str) -> None
        """保存报告到文件"""
    
    def _generate_header(self, result: BenchmarkResult) -> str
    def _generate_summary(self, result: BenchmarkResult) -> str
    def _generate_category_results(self, result: BenchmarkResult) -> str
    def _generate_detailed_results(self, result: BenchmarkResult) -> str
```

#### 4.2 HTML 报告

```python
class HTMLReporter:
    """HTML 格式报告生成器
    
    特性：
    - 响应式布局
    - CSS 样式美化
    - 进度条可视化
    """
    
    def generate(self, result: BenchmarkResult) -> str
    def save(self, result: BenchmarkResult, file_path: str) -> None

def generate_html_report(
    result: BenchmarkResult,
    title: str = "智能体评测报告",
    output_path: Optional[str] = None
) -> str
```

***

## 内部实现架构

### 模块划分

```
evaluation/
├── __init__.py              # 包入口
├── metrics/                 # 评测指标
│   ├── __init__.py
│   ├── stability.py         # 稳定性指标
│   ├── latency.py           # 延迟指标
│   ├── tool_usage.py        # 工具调用指标
│   ├── finding_judge.py     # LLM-as-Judge
│   └── pipeline_metrics.py  # 流程评测指标
├── benchmark/               # 评测基准
│   ├── __init__.py
│   ├── reviewer_benchmark.py  # 单智能体评测
│   └── pipeline_benchmark.py  # 流程评测
├── datasets/                # 测试用例数据集
│   ├── __init__.py
│   ├── schemas.py           # 数据结构定义
│   ├── security_cases.py    # 安全类用例 (30条)
│   ├── performance_cases.py # 性能类用例 (25条)
│   ├── logic_cases.py       # 逻辑类用例 (25条)
│   ├── style_cases.py       # 风格类用例 (20条)
│   └── e2e_cases.py         # 端到端用例 (9条)
└── reporter/                # 报告生成
    ├── __init__.py
    ├── md_reporter.py       # Markdown 报告
    └── html_reporter.py     # HTML 报告
```

### 核心算法

#### 稳定性计算

```
结构一致性 = Σ(字段出现次数 / 总运行次数) / 字段总数

KL散度 = Σ P(x) * log(P(x) / Q(x))
- P(x): 实际严重级别分布
- Q(x): 参考分布（均匀分布）
- 使用平滑因子 ε=1e-10 避免 log(0)
```

#### 延迟百分位数

```
使用 numpy.percentile 计算：
- P50: 第 50 百分位数
- P95: 第 95 百分位数
- P99: 第 99 百分位数
```

#### Finding 匹配

```
1. 关键词匹配：detection_hints 与 finding.title/description
2. LLM-as-Judge：使用 qwen-max 评估语义相似度
3. 综合评分：关键词匹配权重 0.3 + LLM 评分权重 0.7
```

#### 相似度计算（合并）

```
相似度 = 0.40 * 文件路径匹配
       + 0.30 * 行范围 Jaccard 重叠度
       + 0.20 * 标题描述词频相似度
       + 0.05 * 严重级别匹配
       + 0.05 * 评审维度匹配
```

***

## 依赖关系

### 外部依赖

| 依赖             | 版本    | 用途          |
| -------------- | ----- | ----------- |
| numpy          | ≥1.24 | 百分位数计算、统计函数 |
| pydantic       | ≥2.0  | 数据验证与序列化    |
| pytest         | ≥9.0  | 测试框架        |
| pytest-asyncio | ≥0.23 | 异步测试支持      |
| pytest-mock    | ≥3.14 | Mock 工具     |

### 内部依赖

| 依赖                         | 类型   | 交互方式                    | 数据格式             |
| -------------------------- | ---- | ----------------------- | ---------------- |
| `agents.reviewer`          | 单向依赖 | 导入 Finding 类型           | Python dataclass |
| `pipeline.parallel_review` | 单向依赖 | 导入 ParallelReviewResult | Python dataclass |
| `pipeline.debate_loop`     | 单向依赖 | 导入 DebateRecord         | Python dataclass |
| `pipeline.issue_merger`    | 单向依赖 | 导入 MergeRecord          | Python dataclass |
| `pipeline.verdict`         | 单向依赖 | 导入 Verdict              | Python dataclass |
| `tools.diff_parser`        | 单向依赖 | 导入 DiffChunk            | Python dataclass |
| `logger`                   | 单向依赖 | 获取日志器                   | Python module    |

***

## 评测流程

### 单智能体评测流程

```
1. 加载测试用例
   ↓
2. 创建 Agent 实例（通过 factory）
   ↓
3. 执行评测（每个用例运行 n_runs 次）
   ├── 调用 agent.review()
   ├── 记录延迟
   ├── 计算 Finding 匹配
   └── 收集工具调用轨迹
   ↓
4. 计算汇总指标
   ├── 召回率/精确率/F1
   ├── 延迟百分位数
   ├── 稳定性分数
   └── 工具成功率
   ↓
5. 生成评测报告
```

### 流程评测流程

```
1. 初始化 PipelineBenchmark
   ↓
2. 执行并行评审
   ├── 记录阶段耗时
   └── 收集 Finding 列表
   ↓
3. 执行辩论循环
   ├── 记录辩论轮次
   └── 统计确认/驳回率
   ↓
4. 执行合并
   ├── 计算相似度
   └── 记录合并率
   ↓
5. 生成裁决
   └── 统计最终发现
   ↓
6. 汇总流程指标
```

***

## CI/CD 集成

### GitHub Actions 工作流

```yaml
触发条件:
  - push: main/develop 分支
  - pull_request: main 分支
  - workflow_dispatch: 手动触发

任务:
  test:
    - 运行指标测试
    - 运行基准测试
    - 运行用例测试
    - 运行报告测试
    - 运行集成测试
  
  lint:
    - Ruff 代码风格检查
    - MyPy 类型检查
```

***

## 常见错误与解决方案

| 错误                                                | 原因           | 解决方案                                                  |
| ------------------------------------------------- | ------------ | ----------------------------------------------------- |
| `ModuleNotFoundError: evaluation.metrics.latency` | 模块未创建        | 创建对应 `.py` 文件并在 `__init__.py` 导入                      |
| `KL散度计算错误 (log(0))`                               | 分布中存在 0 值    | 添加平滑因子 `SMOOTH_EPSILON=1e-10`                         |
| `百分位数断言失败`                                        | numpy 计算精度   | 使用范围判断而非精确匹配                                          |
| `DiffChunk 参数错误`                                  | 字段名不匹配       | 使用 `old_start/new_start` 而非 `old_content/new_content` |
| `MagicMock 比较错误`                                  | 未设置 mock 返回值 | 设置 `mock.confidence = 0.8` 等属性                        |

