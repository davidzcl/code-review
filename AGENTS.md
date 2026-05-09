# PR 评审智能代理系统

## 这是什么项目

只读 Pull Request 评审智能代理：4 个 reviewer agent 并行审查 + 结构化辩论循环（debate loop）→ 标准化评审报告。

- 自动发现 bug、安全漏洞、性能问题、代码风格问题
- 辩论机制减少误报（false positive）
- 生成 MD/HTML 报告，降低人工 review 认知负荷

## 启动规则

1. 读取 `PROGRESS.md`，获取当前任务进度
2. 查看各子目录 `*\\ARCHITECTURE.md`，获取模块架构信息
3. 读取 `docs\\features.md`，获取功能清单

## 技术栈

| 组件 | 版本 / 说明 |
|------|------------|
| Python | 3.12.12 |
| 框架 | AgentScope 1.0.18（ReActAgent、MsgHub） |
| LLM 后端 | DashScope / OpenAI Compatible / Ollama |
| 环境管理 | Conda (agentscope env) |

## 硬约束

| 约束 | 值 |
|------|-----|
| 代码库访问 | **只读**，严禁写操作 |
| 测试框架 | 新建测试必须用 pytest + pytest-asyncio，严禁创建新 verify_*.py |
| LLM 调用 | 测试中必须 mock，不触发真实 API |

## 目录结构

```
code-review/
├── agents/        # AgentScope agent 封装（reviewer/prosecutor/defender/evaluator）
├── tools/         # 工具组件（Git、解析器、扫描器、报告生成）
├── pipeline/      # 调度编排（并行评审、辩论循环、合并、裁决）
├── test/          # 测试与 fixtures
├── docs/          # 项目文档
├── skills/        # 技能注册目录（skill.md）
├── config.py      # 配置中心（环境变量 + ReviewerProfile）
├── main.py        # 系统入口
├── PROGRESS.md    # 进度跟踪
└── AGENTS.md      # 本文件
```

## 怎么验证

- 读取文件 `docs\\features.md`，获取验证功能清单

## 任务结束操作

1. 更新 `PROGRESS.md`
2. 更新子目录 `*\\ARCHITECTURE.md`
3. 更新 `docs\\features.md`
4. `git commit -m "任务完成：..."`

## 经验总结

1. AgentScope 模块目录：`D:\\project\\agentscope`
2. PowerShell 不支持 `&&`，多命令用 `;` 串联
3. `git diff HEAD` 在裸仓库自动降级为 `git diff`
4. singleton 双重检查锁：`__new__` + `__init__` 均加锁
5. 沙箱 Python：`D:\\software\\Anaconda3\\envs\\agentscope\\python.exe`
6. 错误诊断参考：`docs\\errors-and-resolutions.md`（ChatResponse 构造、DictMixin hasattr、TypedDict 访问等高频陷阱）
