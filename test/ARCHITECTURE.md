# test/ 模块架构文档

## 模块职责与边界

`test/` 负责系统所有测试代码和测试资源的组织管理：
- 各模块的单元测试和集成验证
- 测试 fixtures（样本 diff、mock 响应等）
- 端到端测试

**边界**：test/ 不包含任何生产代码。每个验证脚本对应 features.md 中的一条功能项。

---

## 目录结构

```
test/
├── __init__.py
├── fixtures/                      # 测试数据
│   ├── sample_simple.diff         # 简单 diff 样本（单文件）
│   ├── sample_multi_file.diff     # 多文件 diff 样本
│   ├── sample_pr.md               # 示例 PR 描述
│   └── mock_responses/            # Mock LLM 响应
│       └── reviewer_findings.json
├── verify_model_registry.py       # [PASS] F-01
├── verify_diff_parser.py          # [PENDING] F-03
├── verify_pr_parser.py            # [PENDING] F-04
├── verify_reviewer_agent.py       # [PENDING] F-05
├── verify_parallel_review.py      # [PENDING] F-06
├── verify_debate_loop.py          # [PENDING] F-07
├── verify_prosecutor.py           # [PENDING] F-08
├── verify_defender.py             # [PENDING] F-09
├── verify_issue_merger.py         # [PENDING] F-10
├── verify_verdict.py              # [PENDING] F-11
├── verify_report_md.py            # [PENDING] F-12
├── verify_report_html.py          # [PENDING] F-13
├── verify_evaluator.py            # [PENDING] F-14
└── verify_e2e.py                  # [PENDING] F-15
```

---

## 验证脚本规范

每个 `verify_*.py` 脚本必须：

1. 在 `if __name__ == "__main__"` 下执行
2. 使用 `assert` 语句验证功能正确性
3. 成功时 `exit(0)`，失败时 `exit(1)`
4. 输出格式：`[PASS] / [FAIL] <描述>`
5. 使用 mock 模型，不触发真实 API 调用

**模板**：
```python
"""F-XX: <功能名称> 验证脚本"""
import sys
sys.path.insert(0, "d:/project/code-review")

from agentscope.model import ChatModelBase, ChatResponse

# Mock 模型用于测试
class MockModel(ChatModelBase):
    def __init__(self):
        super().__init__(model_name="mock", stream=False)
    async def __call__(self, *args, **kwargs):
        return ChatResponse(content=[])

def test_something():
    # 测试逻辑
    assert True, "测试失败时输出此消息"
    print("[PASS] 测试项描述")

if __name__ == "__main__":
    test_something()
    print("\n全部验证通过!")
```

---

## Fixtures 设计要求

### sample_simple.diff
- 单文件单函数变更
- 包含：1 个 addition、1 个 deletion
- 用于 diff_parser 基础测试

### sample_multi_file.diff
- 3 个文件变更
- 包含：新增文件、修改文件、删除文件
- 用于 diff_parser 多文件边界条件测试

### sample_pr.md
- 标准 PR 模板（中文）
- 包含：标题、描述、标签、分支信息
- 用于 pr_parser 测试

---

## 依赖关系

| 依赖 | 类型 | 说明 |
|------|------|------|
| `agents` | 运行时依赖 | 被测模块 |
| `tools` | 运行时依赖 | 被测模块 |
| `skills` | 运行时依赖 | 被测模块 |
| `fixtures/` | 数据依赖 | 测试样本数据 |
