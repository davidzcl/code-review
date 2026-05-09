# test/ 模块架构文档

## 模块职责与边界

`test/` 负责系统所有测试代码和测试资源的组织管理：
- 各模块的单元测试和集成验证
- 测试 fixtures（样本 diff、mock 响应等）
- 端到端测试

**边界**：test/ 不包含任何生产代码。

---

## 强制规范（LLM 生成测试时必须遵守）

1. **新建测试必须使用 pytest + pytest-asyncio**，严禁创建新的 `verify_*.py` 脚本
2. **所有 LLM 调用必须 mock**，不触发真实 API 调用
3. **异步函数必须加 `@pytest.mark.asyncio`** 标记
4. **测试文件命名**：`test_<模块名>.py`，如 `test_reviewer_agent.py`
5. **fixture 定义在 conftest.py**，测试文件中不定义可复用 mock
6. **现有 `verify_*.py` 脚本保持不变**，不迁移、不修改

---

## 目录结构

```
test/
├── __init__.py
├── conftest.py                  # pytest fixture 中心（待创建）
├── fixtures/                    # 测试数据
│   ├── sample_simple.diff
│   ├── sample_multi_file.diff
│   └── sample_pr.md
├── verify_*.py                  # 现有验证脚本（保持不变）
└── test_*.py                    # 新增 pytest 测试（待创建）
```

---

## 双框架并存策略

| 维度 | verify_*.py（旧） | test_*.py（新） |
|------|-------------------|----------------|
| 用途 | 快速功能验证、CI 门禁 | 完整单元测试、回归测试 |
| 运行命令 | `python test/verify_xxx.py` | `python -m pytest test/test_*.py -v` |
| 异步支持 | 手动 `asyncio.run()` | `@pytest.mark.asyncio` |
| Mock 策略 | 内联定义 | conftest.py fixture 注入 |
| 状态 | 冻结，不再新增 | 新增测试的唯一入口 |

---

## 依赖版本

| 包 | 版本 | 用途 |
|------|------|------|
| `pytest` | 9.0.2 | 测试框架核心 |
| `pytest-asyncio` | 配套 | 异步测试标记与事件循环管理 |
| `pytest-mock` | 配套 | `mocker` fixture，简化 mock 创建 |

---

## pytest 配置

项目根目录需包含 `pytest.ini` 或 `pyproject.toml` 配置：

```ini
# pytest.ini
[pytest]
testpaths = test
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
```

`asyncio_mode = auto` 是关键配置，使 `async def` 测试函数自动识别为异步测试。

---

## conftest.py Fixture 规范

`test/conftest.py` 定义全局 fixture，作用域覆盖整个 `test/` 目录。

**核心 fixture 清单**：

| Fixture | 返回值 | 用途 |
|---------|--------|------|
| `mock_model` | ChatModelBase 实例 | 模拟 LLM 响应 |
| `mock_formatter` | FormatterBase 实例 | 模拟消息格式化 |
| `sample_diff` | str | 加载 sample_simple.diff |
| `sample_diff_multi` | str | 加载 sample_multi_file.diff |
| `pr_context` | PRContext 实例 | 构造 PR 上下文对象 |
| `diff_chunks` | List[DiffChunk] | 解析后的 diff 块列表 |

**MockModel 响应模板**：
- 正常：返回结构化 Finding JSON 列表
- 空：`[]`
- 异常：非 JSON 字符串（测试解析错误处理）

---

## 测试用例编写模板

```python
import pytest
from agentscope.model import ChatModelBase, ChatResponse
from agentscope.message import TextBlock

@pytest.mark.asyncio
async def test_<功能描述>(mock_model, mock_formatter):
    """测试 docstring：一句话描述测试目标。"""
    # 1. 构造输入
    # 2. 调用被测函数
    # 3. 断言输出
```

**组织原则**：
1. 相关测试方法归入 `Test<类名>` 类
2. 多输入场景使用 `@pytest.mark.parametrize`
3. 一个测试只验证一个行为

---

## 运行命令

```bash
# 全部 pytest 测试
python -m pytest test/test_*.py -v

# 单个文件
python -m pytest test/test_reviewer_agent.py -v

# 快速失败
python -m pytest test/test_*.py -x

# 覆盖率报告
python -m pytest --cov=agents --cov=pipeline --cov=tools --cov-report=html:test/htmlcov test/test_*.py
```

---

## Fixtures 数据设计要求

| 文件 | 要求 |
|------|------|
| `sample_simple.diff` | 单文件单函数变更，1 addition + 1 deletion |
| `sample_multi_file.diff` | 3 文件变更：新增 + 修改 + 删除 |
| `sample_pr.md` | 标准 PR 模板（中文），含标题、描述、标签 |

---

## 依赖关系

| 依赖 | 类型 | 说明 |
|------|------|------|
| `agents` | 被测模块 | — |
| `tools` | 被测模块 | — |
| `pipeline` | 被测模块 | — |
| `fixtures/` | 数据依赖 | 测试样本 |
| `pytest` | 测试框架 | 9.0.2 |
| `pytest-asyncio` | 测试插件 | 异步测试支持 |

---

## 常见错误与解决方案

> 参见 `docs/errors-and-resolutions.md` §测试部分。
