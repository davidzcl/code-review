# PR 评审智能代理系统 - README.md 大纲

## 1. 项目概述

### 1.1 项目简介
- 只读 Pull Request 评审智能代理系统
- 核心价值：4 个 reviewer agent 并行审查 + 结构化辩论循环 → 标准化评审报告
- 关键特性：自动发现 bug、安全漏洞、性能问题、代码风格问题；辩论机制减少误报；生成 MD/HTML 报告

### 1.2 核心架构
```
输入层 → 解析层 → 评审层 → 辩论层 → 裁决层 → 报告层 → 评估层
```

### 1.3 技术栈
| 组件 | 版本 / 说明 |
|------|------------|
| Python | 3.12.12 |
| 框架 | AgentScope 1.0.18（ReActAgent、MsgHub） |
| LLM 后端 | DashScope / OpenAI Compatible / Ollama |
| 环境管理 | Conda (agentscope env) |

### 1.4 目录结构
```
code-review/
├── agents/        # AgentScope agent 封装
├── tools/         # 工具组件
├── pipeline/      # 调度编排
├── test/          # 测试与 fixtures
├── docs/          # 项目文档
├── skills/        # 技能注册目录
├── config.py      # 配置中心
├── main.py        # 系统入口
└── AGENTS.md      # 架构说明
```

---

## 2. 快速开始

### 2.1 环境要求
- Python 3.12+
- Conda 环境管理
- LLM API Key（DashScope 或 OpenAI）

### 2.2 安装步骤
```bash
# 克隆仓库
git clone <repo-url>
cd code-review

# 创建 Conda 环境
conda create -n agentscope python=3.12.12
conda activate agentscope

# 安装依赖
pip install -r requirements.txt
```

### 2.3 配置环境变量
```bash
# 创建 .env 文件
cat > .env << EOF
# API 密钥（二选一）
DASHSCOPE_API_KEY=your-dashscope-api-key
# 或
OPENAI_API_KEY=your-openai-api-key
OPENAI_API_BASE_URL=https://api.openai.com/v1

# 评审参数
MAX_DEBATE_ROUNDS=3
MIN_CONFIDENCE_THRESHOLD=0.6

# 输出配置
OUTPUT_DIR_NAME=.review-agent
LOG_LEVEL=INFO
EOF
```

---

## 3. 使用指南

### 3.1 命令行接口

**基本用法：**
```bash
python main.py --repo-dir /path/to/repo --base main --target feature-branch
```

**完整参数说明：**
| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `--repo-dir` | str | 目标 Git 仓库目录 | 当前工作目录 |
| `--base` | str | 基准分支/commit | - |
| `--target` | str | 目标分支/commit | - |
| `--pr-description` | str | PR 描述文本 | - |
| `--pr-file` | str | PR 描述文件路径 | - |
| `--model-config` | str | 模型配置 JSON 字符串 | - |
| `--output` | str | 输出目录 | .review-agent/ |
| `--format` | str | 报告格式 (markdown/html/json) | markdown |
| `--skip-guardrail` | flag | 跳过前置 Guardrail 扫描 | False |
| `--skip-evaluation` | flag | 跳过 AI 质量评估 | False |
| `--max-rounds` | int | 最大辩论轮次 | 3 |
| `--confidence` | float | 置信度阈值 | 0.6 |

### 3.2 使用示例

**示例 1：评审本地分支**
```bash
python main.py \
  --repo-dir /workspace/my-project \
  --base main \
  --target feature/new-feature \
  --output ./reports
```

**示例 2：使用 PR 描述文件**
```bash
python main.py \
  --repo-dir /workspace/my-project \
  --base main \
  --target feature/new-feature \
  --pr-file ./pr_description.md \
  --format html
```

**示例 3：跳过某些阶段**
```bash
python main.py \
  --repo-dir /workspace/my-project \
  --base main \
  --target feature/new-feature \
  --skip-guardrail \
  --skip-evaluation
```

---

## 4. 执行流程

### 4.1 完整流程概览

```
[Phase 0] 加载 PR 信息
    ↓
[Phase 0.5] 前置 Guardrail 扫描（可选）
    ↓
[Phase 1] 创建 LLM 模型
    ↓
[Phase 2] 创建评审者 Agent（4个并行）
    ↓
[Phase 3] 并行评审
    ↓
[Phase 4] 辩论循环（Prosecutor vs Defender）
    ↓
[Phase 5] 合并相似发现
    ↓
[Phase 6] 最终裁决
    ↓
[Phase 7] 生成报告
    ↓
[Phase 8] AI 质量评估（可选）
```

### 4.2 各阶段详解

**Phase 0: 加载 PR 信息**
- 解析 PR 描述（Markdown 格式）
- 获取 Git Diff
- 提取变更文件和代码块

**Phase 0.5: 前置 Guardrail 扫描**
- 敏感信息扫描
- 风险检测
- 生成上下文信息

**Phase 1: 创建模型**
- 根据环境变量自动选择模型（DashScope 优先）
- 支持自定义模型配置

**Phase 2: 创建评审者**
- 安全评审者（SecurityReviewer）
- 性能评审者（PerformanceReviewer）
- 逻辑评审者（LogicReviewer）
- 风格评审者（StyleReviewer）

**Phase 3: 并行评审**
- 4 个评审者同时审查
- 每个评审者独立生成发现

**Phase 4: 辩论循环**
- Prosecutor 质疑发现的有效性
- Defender 为发现辩护
- 多轮辩论直到达成共识或达到最大轮次

**Phase 5: 合并相似发现**
- 识别重复或相似的评审发现
- 合并同类问题

**Phase 6: 最终裁决**
- 根据辩论结果和置信度阈值筛选发现
- 生成最终评审结论

**Phase 7: 生成报告**
- 支持 Markdown、HTML、JSON 格式
- 结构化的评审报告输出

**Phase 8: AI 质量评估**
- 评估评审报告质量
- 输出评分和改进建议

---

## 5. 配置参考

### 5.1 配置文件结构
所有配置通过 `.env` 文件管理：

```env
# ========== API 配置 ==========
DASHSCOPE_API_KEY=
OPENAI_API_KEY=
OPENAI_API_BASE_URL=https://api.openai.com/v1

# ========== 输出配置 ==========
OUTPUT_DIR_NAME=.review-agent
LOG_LEVEL=INFO
LOG_DIR=
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5

# ========== 评审参数 ==========
MAX_DEBATE_ROUNDS=3
MIN_CONFIDENCE_THRESHOLD=0.6

# ========== 限制参数 ==========
MAX_DIFF_CHARS=120000
MAX_CMD_OUTPUT=50000
MAX_SKILL_CHARS=12000
```

### 5.2 评审者配置
系统内置 4 个评审者角色：

| 评审者 | 角色 | 职责 |
|--------|------|------|
| SecurityReviewer | security | 检测安全漏洞（注入攻击、认证绕过、敏感信息泄露等） |
| PerformanceReviewer | performance | 检测性能问题（N+1 查询、内存泄漏、算法复杂度等） |
| LogicReviewer | logic | 检测逻辑错误（边界条件、空值检查、异常处理等） |
| StyleReviewer | style | 检测可维护性问题（命名规范、代码重复、复杂度等） |

### 5.3 模型配置

**DashScope 配置（默认）：**
```python
{
    "model_type": "dashscope",
    "model_name": "qwen3.6-flash",
    "stream": True,
    "api_key": "<your-api-key>",
    "multimodality": True
}
```

**OpenAI 兼容配置：**
```python
{
    "model_type": "openai",
    "model_name": "gpt-4o",
    "stream": True,
    "api_key": "<your-api-key>"
}
```

---

## 6. 核心组件

### 6.1 Agent 架构

**ReviewerAgent** (`agents/reviewer.py`)
- 执行代码审查
- 生成评审发现

**ProsecutorAgent** (`agents/prosecutor.py`)
- 对评审发现提出质疑
- 验证发现的有效性

**DefenderAgent** (`agents/defender.py`)
- 为评审发现辩护
- 反驳质疑

**EvaluatorAgent** (`agents/evaluator.py`)
- 评估评审报告质量
- 提供改进建议

### 6.2 Pipeline 组件

**ParallelReviewManager** (`pipeline/parallel_review.py`)
- 管理多个评审者并行执行

**DebateLoop** (`pipeline/debate_loop.py`)
- 协调质疑者和辩护者的辩论流程

**IssueMerger** (`pipeline/issue_merger.py`)
- 合并相似的评审发现

**Verdict** (`pipeline/verdict.py`)
- 生成最终评审裁决

### 6.3 Tools 组件

**DiffParser** (`tools/diff_parser.py`)
- 解析 Git Diff 输出

**PRParser** (`tools/pr_parser.py`)
- 解析 PR 描述文本

**ReportWriter** (`tools/report_writer.py`)
- 生成评审报告

**SecretScanner** (`tools/secret_scanner.py`)
- 扫描敏感信息泄露

**RiskScan** (`tools/risk_scan.py`)
- 执行风险检测

---

## 7. 输出格式

### 7.1 Markdown 报告
```markdown
# PR 评审报告

## 概览
- PR 标题: xxx
- 作者: xxx
- 变更文件: N 个
- 评审时间: xxx

## 发现问题

### 🔴 严重级别: HIGH
1. [安全] SQL 注入风险 - 文件: xxx.py:xxx
   - 描述: ...
   - 置信度: 0.95
   - 建议: ...

### 🟡 严重级别: MEDIUM
2. [性能] N+1 查询问题 - 文件: xxx.py:xxx
   - 描述: ...
   - 置信度: 0.85
   - 建议: ...

## 评审统计
- 总发现: N
- HIGH: N
- MEDIUM: N
- LOW: N
```

### 7.2 HTML 报告
- 交互式界面
- 可折叠的问题详情
- 代码高亮显示

### 7.3 JSON 报告
- 结构化数据
- 便于程序处理和集成

---

## 8. 测试

### 8.1 运行测试
```bash
# 运行所有测试
pytest test/ -v

# 运行特定测试
pytest test/verify_prosecutor.py -v

# 运行 e2e 测试
pytest test/verify_e2e.py -v
```

### 8.2 测试覆盖范围
| 测试文件 | 覆盖组件 |
|----------|----------|
| `verify_reviewer_agent.py` | ReviewerAgent |
| `verify_prosecutor.py` | ProsecutorAgent |
| `verify_defender.py` | DefenderAgent |
| `verify_evaluator.py` | EvaluatorAgent |
| `verify_parallel_review.py` | ParallelReviewManager |
| `verify_debate_loop.py` | 辩论循环 |
| `verify_verdict.py` | 裁决逻辑 |
| `verify_diff_parser.py` | Diff 解析器 |
| `verify_pr_parser.py` | PR 解析器 |
| `verify_report_md.py` | Markdown 报告 |
| `verify_report_html.py` | HTML 报告 |
| `verify_e2e.py` | 端到端测试 |

---

## 9. 故障排除

### 9.1 常见问题

**Q1: 缺少 API Key**
```
错误: 未找到 API Key。请在 .env 文件中设置 DASHSCOPE_API_KEY 或 OPENAI_API_KEY
```
**解决方案**: 在 `.env` 文件中配置 API Key

**Q2: Git 命令执行失败**
```
错误: git diff 命令执行失败
```
**解决方案**: 确保 `--repo-dir` 参数指向有效的 Git 仓库

**Q3: 报告生成失败**
```
错误: 输出目录创建失败
```
**解决方案**: 检查输出目录权限，确保有写入权限

### 9.2 日志排查
```bash
# 查看最近的日志
tail -f logs/info.log

# 查看错误日志
cat logs/error.log
```

### 9.3 调试模式
```bash
# 设置日志级别为 DEBUG
export LOG_LEVEL=DEBUG
python main.py --repo-dir ./ --base main --target feature
```

---

## 10. 许可证

MIT License

---

---

## 附录

### A. 环境变量完整列表

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `DASHSCOPE_API_KEY` | str | - | DashScope API 密钥 |
| `OPENAI_API_KEY` | str | - | OpenAI API 密钥 |
| `OPENAI_API_BASE_URL` | str | https://api.openai.com/v1 | OpenAI API 端点 |
| `OUTPUT_DIR_NAME` | str | .review-agent | 输出目录名 |
| `LOG_LEVEL` | str | INFO | 日志级别 |
| `MAX_DEBATE_ROUNDS` | int | 3 | 最大辩论轮次 |
| `MIN_CONFIDENCE_THRESHOLD` | float | 0.6 | 置信度阈值 |
| `MAX_DIFF_CHARS` | int | 120000 | Diff 最大字符数 |

### B. 报告格式对比

| 格式 | 优点 | 适用场景 |
|------|------|----------|
| Markdown | 简洁易读，便于版本控制 | Git PR、文档归档 |
| HTML | 美观交互，支持代码高亮 | 在线展示、分享 |
| JSON | 结构化数据，便于集成 | CI/CD 流水线、API 对接 |

---