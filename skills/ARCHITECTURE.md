# skills/ 模块架构文档

## 模块职责与边界

`skills/` 是 agent 技能注册目录。**唯一用途**：存放 markdown 格式的技能描述文件，供 agent 在运行时加载和引用。

**核心原则**：
- skills/ 不含可执行代码 — 无 `.py`、无 `.json`、无配置文件
- skills/ 不含调度逻辑 — 编排控制流归属 `pipeline/`
- skills/ 不含业务规则 — 规则引擎归属 `pipeline/`
- skills/ 不含工具函数 — 工具实现归属 `tools/`

---

## 文件规范

### 目录组织

```
skills/
├── ARCHITECTURE.md        # 本文件
├── <skill_name>/           # 每个技能一个独立子目录
│   └── skill.md            # 该技能的描述文件（唯一文件）
└── <another_skill>/
    └── skill.md
```

### 硬约束

| 规则 | 说明 |
|------|------|
| 仅 `.md` 文件 | 不允许任何其他文件类型 |
| 每个技能一个子目录 | 技能名即目录名，目录内仅一个 `skill.md` |
| 禁止代码实现 | 不放置 Python、shell 等任何可执行代码 |
| 禁止嵌套子目录 | `skill.md` 必须是目录中唯一的直接子项 |

### skill.md 格式模板

```markdown
# <技能名称>

## 描述
<一句话描述该技能的功能与目标>

## 触发条件
<什么情况下 agent 应调用此技能>

## 输入参数
- param1 (类型): 描述
- param2 (类型): 描述

## 输出格式
<期望输出的结构说明>

## 约束
<调用此技能时须遵守的限制>

## 示例
<一个完整的使用示例，展示输入和预期输出>
```

---

## 运行时加载机制

agent 在初始化时通过扫描 `skills/` 目录树，读取所有 `skill.md` 文件内容，构建技能描述索引。此加载逻辑由 `agents/` 或 `pipeline/` 层实现，不在 `skills/` 目录内。

```
skills/*/skill.md  ──→  skills_loader (agents/ 或 pipeline/)  ──→  agent.skills[]
```

---

## 依赖关系

`skills/` 不依赖任何项目内部模块。skill.md 文件中引用的类型名（如 DiffChunk、PRContext、Finding）是约定而非硬依赖，由加载方负责解析和映射。
