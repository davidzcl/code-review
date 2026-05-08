# tools/ 模块架构文档

## 模块职责与边界

`tools/` 负责系统所需的各类工具组件实现，包括：
- Git 操作的只读封装
- Git diff 的结构化解析
- PR 描述的提取与结构化
- 评审报告的生成与格式化
- 全局日志系统
- 安全测试执行（含危险操作检测）
- 密钥扫描（正则 + detect-secrets 可选）
- 代码搜索（git grep）
- 风险分析（hotspot 规则）

**边界**：tools/ 不包含任何 AI agent 逻辑、辩论控制流——这些属于 `agents/` 和 `skills/`。

---

## 对外接口定义

### 1. Git 只读操作（已实现，tools/tools.py）

```python
def git_diff(
    base: str | None = None,
    target: str | None = None,
    staged_only: bool = False,
    file_filter: str | None = None,
) -> str
    """获取 Git 仓库差异内容。
    参数:
        base:        基准 commit/tag，默认从 GIT_BASE 环境变量读取
        target:      目标 commit/tag，默认从 GIT_TARGET 环境变量读取
        staged_only: 仅显示已暂存（staged）的变更
        file_filter: 文件路径过滤
    返回:
        unified diff 原始字符串，超过 MAX_DIFF_CHARS 自动截断
    错误:
        环境变量缺失且未传参时抛出 ValueError
    """

def get_changed_files(
    base: str | None = None,
    target: str | None = None,
    by_type: bool = False,
) -> list[str] | dict[str, list[str]]
    """提取变更文件列表。
    参数:
        by_type: True 时按扩展名分组返回 {".py": [...], ".js": [...]}
    返回:
        by_type=False: 文件路径列表
        by_type=True:  {扩展名: [文件路径列表]}
    """

def read_file(
    file_path: str,
    commit: str | None = None,
    start_line: int = 1,
    end_line: int | None = None,
    max_chars: int = 8000,
) -> str
    """只读读取指定版本文件内容。
    参数:
        commit:    commit hash / 分支名，None 表示 HEAD
        start_line:起始行号（从 1 开始）
        end_line:  结束行号（含），None 表示文件末尾
        max_chars: 最大返回字符数
    返回:
        文件内容字符串，超长自动截断
    """

def get_workspace_status(cwd: str | None = None) -> WorkspaceStatus
    """检测 Git 工作区状态（git diff HEAD）。
    返回:
        WorkspaceStatus 包含解析后的变更列表和统计信息
    """

def get_workspace_status_json(cwd: str | None = None) -> str
    """工作区状态的 JSON 字符串表示。"""

def workspace_status_to_dict(status: WorkspaceStatus) -> dict
    """WorkspaceStatus → dict（JSON 兼容序列化）。"""
```

**数据结构**：
```python
@dataclass
class WorkspaceChange:
    file_path: str
    old_start: int; old_count: int
    new_start: int; new_count: int
    additions: list[str]
    deletions: list[str]
    context_lines: list[str]
    is_new_file: bool
    is_deleted_file: bool

@dataclass
class WorkspaceStatus:
    changes: list[WorkspaceChange]
    total_additions: int
    total_deletions: int
    changed_files_count: int
    raw_diff: str
```

### 2. Diff 解析器（已实现）

```python
@dataclass
class DiffChunk:
    file_path: str                   # 文件路径
    old_start: int                   # 旧文件起始行
    old_count: int                   # 旧文件行数
    new_start: int                   # 新文件起始行
    new_count: int                   # 新文件行数
    context: str                     # 变更上下文（前后各 3 行）
    additions: list[str]             # 新增行
    deletions: list[str]             # 删除行
    language: str                    # 编程语言（根据扩展名推断）
    is_new_file: bool                # 是否为新文件
    is_deleted_file: bool            # 是否为删除文件

def parse_diff(diff_text: str) -> list[DiffChunk]
    """解析 unified diff 文本为结构化数据。
    参数:
        diff_text: git diff 输出字符串
    返回:
        DiffChunk 列表，按文件分组
    错误:
        格式无效时抛出 DiffParseError
    """

def get_changed_files(diff_text: str) -> list[str]
    """提取变更文件列表。"""

def split_by_file(diff_text: str) -> dict[str, str]
    """按文件分割 diff 文本。
    返回:
        {文件路径: 该文件的 diff 片段}
    """

class DiffParseError(Exception):
    """Diff 解析异常。"""
```

### 3. PR 解析器（已实现）

```python
@dataclass
class PRContext:
    title: str                       # PR 标题
    description: str                 # PR 描述正文
    labels: list[str]                # 标签列表
    base_branch: str                 # 目标分支
    head_branch: str                 # 源分支
    author: str                      # 作者
    changed_files_summary: str       # 文件变更摘要

def parse_pr_description(pr_text: str) -> PRContext
    """解析 PR 描述文本为结构化数据。
    参数:
        pr_text: PR 描述原始文本（Markdown 格式）
    返回:
        PRContext 对象
    错误:
        必填字段缺失时抛出 PRParseError
    """

class PRParseError(Exception):
    """PR 解析异常。"""
```

### 4. 报告生成器（待实现）

```python
def generate_report(
    verdict: Verdict,
    pr_context: PRContext,
    diff_summary: str,
    format: str = "markdown"
) -> str
    """根据评审结果生成格式化报告。
    参数:
        verdict:      裁决者输出的最终 Verdict
        pr_context:   PR 元信息
        diff_summary: diff 变更摘要
        format:       "markdown" | "html" | "json"
    返回:
        格式化的报告字符串
    错误:
        不支持的格式抛出 ValueError
    """

def write_report(report_content: str, output_path: str) -> None
    """将报告写入文件。"""
```

**Markdown 报告模板结构**：
```markdown
# PR Review Report: {title}

## 评审概览
- PR: {pr_link}
- 作者: {author}
- 变更文件: {count} 个
- 发现问题: {total} 个 (Critical: {n}, Important: {m}, Minor: {k})

## 变更摘要
{diff_summary}

## 发现详情

### Critical
| 文件 | 行 | 问题 | 建议 |
|------|-----|------|------|

### Important
...

### Minor
...

## 评审元信息
- 辩论轮次: {rounds}
- 驳回发现: {dismissed_count}
- 合并发现: {merged_count}
```

### 5. 全局日志系统（已实现，tools/logger.py）

```python
class ReviewLogger:
    """全局日志管理器（单例）。

    功能：
    - RotatingFileHandler 日志轮转（10MB × 5 备份）
    - StreamHandler 控制台输出
    - threading.Lock 线程安全
    - 子 logger 按组件名称获取（get_logger）
    - 运行时动态调整日志级别（set_level）
    """

    def get_logger(self, name: str) -> logging.Logger
        """获取组件级别子 logger，如 'tools.diff_parser'、'agents.security'"""

    def debug(self, message: str, ...)
    def info(self, message: str, ...)
    def warning(self, message: str, ...)
    def error(self, message: str, ...)
    def critical(self, message: str, ...)

    def set_level(self, level_name: str) -> None
        """运行时动态调整日志级别: DEBUG / INFO / WARNING / ERROR / CRITICAL"""

logger = ReviewLogger()   # 模块级单例实例
```

**环境变量配置**：
| 变量 | 默认值 | 说明 |
|------|--------|------|
| LOG_LEVEL | INFO | 日志级别 |
| LOG_DIR | ./logs | 日志目录 |
| LOG_MAX_BYTES | 10485760 | 单个日志文件上限 |
| LOG_BACKUP_COUNT | 5 | 轮转保留文件数 |
| LOG_FORMAT | "%(asctime)s \| %(levelname)-8s \| %(name)s \| %(message)s" | 日志格式 |

### 6. 安全测试执行器（已实现，tools/test_runner.py）

```python
@dataclass
class RunTestResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int
    blocked: bool            # 是否因危险命令被阻止
    block_reason: str        # 阻止原因

def run_tests(
    command: str,
    cwd: str | None = None,
    timeout: int = 300,
    env_vars: dict | None = None,
) -> RunTestResult
    """安全执行测试命令。

    内置检测的高危模式：
    - rm -rf
    - git reset
    - git checkout
    - shutdown
    - reboot
    - sudo

    检测到高危命令时返回 blocked=True，并记录 WARNING 日志
    （含时间戳、执行用户、命令原文）。
    """

def _detect_danger(command: str) -> str | None
    """检测命令中是否包含危险操作。"""

def _record_danger_log(entry: DangerLogEntry) -> None
    """记录危险操作尝试到日志。"""
```

### 7. 密钥扫描器（待实现，tools/secret_scanner.py）

```python
@dataclass
class SecretFinding:
    file_path: str
    line: int
    rule_id: str
    snippet: str        # 已脱敏，密钥体替换为 ***
    confidence: float   # 0.0-1.0

def scan_secrets(diff_text: str, file_path: str = "") -> list[SecretFinding]
    """正则扫描 diff 中的疑似密钥。

    规则覆盖：AWS AKIA、GitHub Token、GitLab Token、SSH Private Key、
    Slack Token、JWT、Google API Key、Stripe Key、密码赋值等。
    """

def scan_secrets_detect_secrets(file_path: str) -> list[SecretFinding]
    """通过 detect-secrets 库扫描文件（可选依赖）。"""
```

### 8. 代码搜索（tools/search.py）

```python
@dataclass
class SearchResult:
    file_path: str
    line: int
    content: str

def search_code(
    pattern: str,
    path: str = ".",
    file_types: str | None = None,
    case_sensitive: bool = False,
) -> list[SearchResult]
    """在代码库中搜索文本模式。

    优先使用 git grep（仅搜索已跟踪文件），
    遇到新文件/untracked 文件时回退到 ripgrep。

    自动排除目录: .git, .review-agent, .tmp, .pytest_cache,
                  __pycache__, node_modules, .venv
    自动跳过文件扩展名: .md, .txt, .toml, .yaml, .yml, .json
    """
```

### 9. 风险分析（tools/risk_scan.py）

```python
@dataclass
class RiskScore:
    file_path: str
    risk_level: str       # "high" | "medium" | "low"
    reasons: list[str]

@dataclass
class RiskFinding:
    file_path: str
    line: int
    category: str
    signal: str
    evidence: str
    rationale: str
    risk_level: str

def hotspot_analysis(changed_files: list[str]) -> list[RiskScore]
    """分析变更文件的风险等级。

    高风险类别：authentication / authorization / data_persistence /
    payment / crypto / config / ci_cd / networking。
    """

def static_analysis(file_path: str, language: str) -> list[dict]
    """语言特定的静态分析（Python → ruff, JS/TS → eslint）。"""

def scan_risk_signals(
    base: str | None = None,
    target: str | None = None,
) -> dict[str, list[RiskFinding]]
    """扫描 diff 新增行中的风险信号 + 测试覆盖检测。

    流程:
      diff → 解析新增行 → 行级正则匹配 → 跨行空 except 检测
      → 测试覆盖检查（critical/important 级别文件的缺失测试）

    行级规则覆盖:
      - sql_injection: raw_sql_concat, fstring_in_sql
      - command_injection: shell_true, eval_exec_usage
      - sensitive_info: leak_to_log
      - signature_verify: disabled_verify, disabled_hostname_check
      - correctness: mutable_default_arg, negative_amount,
                     bypass_approval, empty_except

    返回:
        {"risk_signals": [...], "test_gaps": [...]}
    """
```

---

## 内部实现架构

### 模块划分

```
tools/
├── __init__.py           # 包入口（待创建）
├── logger.py             # 全局日志系统（已实现）
├── test_runner.py        # 安全测试执行（已实现）
├── tools.py              # Git 只读操作封装（已实现）
├── toolkit.py            # Toolkit 注册与调用调度（待实现）
├── diff_parser.py        # diff 解析（已实现）
├── pr_parser.py          # PR 描述解析（已实现）
├── report_writer.py      # 报告生成（待实现）
├── secret_scanner.py     # 密钥扫描（待实现）
├── search.py             # 代码搜索（已实现）
├── risk_scan.py          # 风险分析（已实现）
```

### 核心算法

- **diff_parser**: 基于正则的状态机解析器：
  1. 按 `^diff --git` 分割文件
  2. 解析 `@@ -old,count +new,count @@` 行号定位
  3. 前缀 `+`/`-`/` ` 分类行类型
  4. 根据扩展名推断 language
  5. 提取上下文行（前 3 行后 3 行）

- **pr_parser**: Markdown 头部解析器：
  1. 以 `##` 分隔章节
  2. 正则匹配 `**标签**:` / `**分支**:` 等字段
  3. 列表项解析为 labels 数组

- **report_writer**: Jinja2 模板引擎填充：
  1. 加载模板
  2. 注入 Verdict + PRContext
  3. 按 severity 分组渲染表格
  4. 可选 HTML 转换（markdown → html）

- **workspace_status_parser**: 行级状态机解析器：
  1. `diff --git` 分割文件
  2. `---`/`+++` 确认文件路径
  3. `@@` 行解析起始行号和改动计数
  4. `+`/`-`/` ` 前缀按行分类

- **risk_scan**: 基于正则的风险信号引擎：
  1. `git_diff` 获取 unified diff
  2. 状态机解析新增行（`+` 前缀）及其文件路径、行号
  3. 逐行匹配预编译危险模式集（SQL 注入/命令注入/敏感信息泄露/签名绕过/正确性陷阱）
  4. 跨行检测（`except: ... pass` 空异常块）
  5. 检测 `critical`/`important` 级别风险文件的测试覆盖缺口

- **secret_scanner**: 多规则正则匹配引擎：
  1. 逐行扫描
  2. 每行匹配所有规则（编译后 regex）
  3. 匹配结果自动脱敏（上下文 8 字符 + `***`）
  4. 低置信度规则（<0.6）可在 debate loop 中被质疑者过滤

- **test_runner**: 前置过滤 + subprocess：
  1. 命令字符串小写化
  2. 6 种高危模式 substring 匹配
  3. 命中则返回 blocked + WARNING 日志
  4. 未命中则 subprocess.run(timeout)

---

## 依赖关系

### 外部依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python subprocess | 标准库 | 执行 git 命令 |
| re (正则) | 标准库 | diff 文本解析 / 密钥扫描 |
| logging + RotatingFileHandler | 标准库 | 日志系统 |
| threading.Lock | 标准库 | 日志单例线程安全 |
| Jinja2 | ≥3.0 (待安装) | 报告模板渲染 |
| detect-secrets | 可选 (待安装) | 增强密钥扫描 |

### 内部依赖

| 依赖 | 类型 | 交互方式 | 数据格式 |
|------|------|----------|----------|
| `config.py` | 单向依赖 | 导入路径、限制常量 | Python 模块属性 |
| `tools.logger` | 工具依赖 | 各模块通过 logger.get_logger() 获取子 logger | logging.Logger |
| `tools.tools` | 功能依赖 | diff_parser/report_writer 导入 dataclass | Python dataclass |
| `skills.debate_loop` | 被调用方 | 接收 DebateRecord | Python dataclass → 模板变量 |
| `agents.judge` | 被调用方 | 接收 Verdict | Python dataclass → 模板变量 |
