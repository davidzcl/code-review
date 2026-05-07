# PR 评审智能代理系统 (PR Review Agent System)

## 项目概览

### 项目目标

构建一个只读性质的 Pull Request 评审智能代理系统，通过多个评审者 agent 协同工作、结构化辩论循环（debate loop）机制，生成标准化的代码评审报告。

核心价值：
- 自动化发现 PR 中潜在的 bug、安全漏洞、性能问题和代码风格问题
- 通过辩论机制减少误报（false positive）、提升评审质量
- 生成标准化报告，降低人工 code review 的认知负荷

## 启动规则

1、读取 ‘PROGRESS.md’ 文件，获取当前任务进度。
2、查看子目录的文件 ‘*\ARCHITECTURE.md’，获取系统架构信息。
3、读取 ‘docs\features.md’ 文件，获取系统功能列表。

---

## 技术栈及版本信息

### 编程语言

| 语言 | 版本 | 选型理由 |
|------|------|----------|
| Python | 3.12.12 | AgentScope 要求 ≥3.10；3.12 为当前稳定 LTS 路径 |

### 核心框架

| 框架/库 | 版本 | 选型理由 |
|----------|------|----------|
| AgentScope | 1.0.18 | 需求指定；提供 ReActAgent、MsgHub、模型抽象等基础能力 |
| python-dotenv | ≥1.0.0 | 环境变量管理 |

### LLM 后端

| 后端 | 接入方式 | 说明 |
|------|----------|------|
| DashScope | DashScopeChatModel | 通义千问系列，通过 DASHSCOPE_API_KEY 认证 |
| OpenAI Compatible | OpenAIChatModel | 支持 DeepSeek、vLLM 等 OpenAI API 兼容后端 |
| Ollama | OllamaChatModel | 本地部署模型，需单独安装 ollama Python 包 |

### 开发工具

| 工具 | 用途 |
|------|------|
| Conda (agentscope env) | Python 虚拟环境管理 |
| Git | 版本控制与 diff 数据源 |

---

## 全局硬约束

### 性能指标

| 指标 | 阈值 | 说明 |
|------|------|------|
| 单次评审最大 diff 字符数 | 120,000 chars | 通过 MAX_DIFF_CHARS 环境变量配置 |
| 最大辩论轮次 | 3 轮 | 防止无限辩论循环 |
| 模型调用超时 | 120s | HTTP 请求级别超时 |
| 报告生成最大延迟 | 规则 + 模板填充，<5s | 不含 LLM 调用时间 |
| 工具输出截断 | 8,000 chars | SEARCH_MAX_RESULTS=200 行 |
| Git 命令超时 | 30s | 通过 GIT_TIMEOUT 环境变量配置 |

### 兼容性限制

| 约束 | 详情 |
|------|------|
| Git 格式 | 仅支持 unified diff 格式 |
| 代码库访问 | **只读**，严禁任何写操作 |
| 大文件过滤 | 超过 MAX_DIFF_CHARS 的 diff 将截断处理 |
| 模型响应格式 | 要求返回 ChatResponse 类型（AgentScope 标准） |

### 安全规范

| 规范 | 要求 |
|------|------|
| API Key 管理 | 仅在 .env 文件中存储，不提交到版本控制 |
| 审计日志 | 所有 agent 调用记录到日志 |
| 代码隔离 | 评审过程不执行任何用户代码；`run_tests` 内置 6 种高危模式拦截 |
| 输入消毒 | PR 描述中的 HTML/script 标签需转义后再嵌入报告 |
| 密钥脱敏 | `scan_secrets` 输出中密钥体替换为 `***`，仅保留前后 8 字符上下文 |

### 合规性

- 遵循 Apache 2.0 License（与 AgentScope 一致）
- 输出报告不含受版权保护的训练数据片段

### 测试

- 在目录 ‘test’ 创建测试文件
- 所有功能组件都有对应的测试用例
- 测试用例覆盖不同场景，包括边界条件、异常输入、正常操作



---

## 目录结构

```
code-review/
├── agents/           # AgentScope agent 封装模块
├── tools/            # 工具组件
├── skills/           # 技能模块（辩论循环、裁决逻辑）
├── test/             # 测试代码与 fixtures
├── docs/             # 项目文档
├── .env              # 环境变量（不提交）
├── config.py         # 配置中心
├── main.py           # 系统入口
├── requirements.txt  # 依赖声明
├── AGENTS.md         # 本文件
└── PROGRESS.md       # 进度跟踪
```

---

## agent 角色定义

| agent 名称 | 角色 | 职责 |
|------------|------|------|
| SecurityReviewer | 安全审计 | 注入攻击、认证绕过、敏感信息泄露、加密缺陷 |
| PerformanceReviewer | 性能优化 | N+1 查询、内存泄漏、阻塞 IO、锁竞争、算法退化 |
| LogicReviewer | 逻辑审查 | 边界条件、空值检查、异常处理、竞态条件、事务一致性 |
| StyleReviewer | 代码风格 | 命名规范、函数复杂度、重复代码、耦合度、测试覆盖 |
| Prosecutor | 质疑者 | 对候选问题进行合理性验证与质疑 |
| Defender | 辩护者 | 收集支持证据，反驳不合理的质疑 |
| Judge | 裁决者 | 合并重复发现，做出最终评审结论 |

---

## 数据流

```
[Git Diff] ──→ tools/tools.py        ──→ raw diff / 文件列表
[Git HEAD] ──→ tools/tools.py        ──→ workspace_status (JSON)
[PR 描述]  ──→ tools/pr_parser.py    ──→ 结构化 PR 元数据
                                                │
                                ┌───────────────┼───────────────┐
                                ▼               ▼               ▼
                     agents/reviewer × 4   tools/secret_scanner  tools/search_code
                     (并行)                tools/risk_scan       (可选搜索)
                                │               │               │
                                ▼               ▼               ▼
                         skills/debate_loop.py  ──→ 辩论循环
                         ├── 质疑 (prosecutor)
                         ├── 辩护 (defender)
                         ├── 反驳
                         ├── 合并 (issue_merger)
                         └── 裁决 (verdict)
                                                │
                                                ▼
                         tools/report_writer.py ──→ 评审报告 (MD/HTML)
                                                │
                                                ▼
                         agents/evaluator.py   ──→ 质量评估 (可选)
```
---

## 经验总结

1. **AgentScope 模块注意**：模块目录在 ‘D:\project\agentscope’
2. **PowerShell `&&` 不兼容**：Windows 下多命令串联需使用 `;` 或分次执行
3. **`git diff HEAD` 回退策略**：裸仓库无 HEAD commit 时自动降级为 `git diff`
4. **singleton 双重检查锁**：`__new__` + `__init__` 均加锁，防止竞态条件下重复初始化