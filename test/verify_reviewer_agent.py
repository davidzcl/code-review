"""F-05: 评审者 Agent 基类验证脚本"""

import sys
sys.path.insert(0, r"d:\project\code-review")

from typing import Any, List, Optional, Sequence

from agentscope.formatter import FormatterBase
from agentscope.message import Msg, TextBlock
from agentscope.model import ChatModelBase, ChatResponse

from agents import (
    AgentInitializationError,
    Finding,
    ReviewerAgent,
    create_model,
    is_model_registered,
    list_registered_models,
)
from tools.diff_parser import DiffChunk
from tools.pr_parser import PRContext


class MockFormatter(FormatterBase):
    async def format(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return [{"role": "user", "content": "mock"}]


class MockModel(ChatModelBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(model_name="mock-model", stream=False)

    async def __call__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> ChatResponse:
        return ChatResponse(content=[
            TextBlock(type="text", text='[{"severity": "important", "file_path": "src/main.py", "line_start": 10, "line_end": 20, "title": "测试发现", "description": "这是一个测试", "suggestion": "修复建议", "confidence": 0.85}]'),
        ])


def test_finding_dataclass():
    f = Finding(
        reviewer="TestReviewer",
        role="security",
        severity="critical",
        file_path="src/main.py",
        line_range=(1, 10),
        title="SQL 注入风险",
        description="用户输入未转义",
        suggestion="使用参数化查询",
        confidence=0.95,
        evidence=["第 5 行: query(f'SELECT * FROM users WHERE id = {user_id}')"],
    )
    assert f.id, "Finding id 不应为空"
    assert f.reviewer == "TestReviewer"
    assert f.role == "security"
    assert f.severity == "critical"
    assert f.file_path == "src/main.py"
    assert f.line_range == (1, 10)
    assert f.title == "SQL 注入风险"
    assert f.confidence == 0.95
    assert len(f.evidence) == 1
    print("  1.1 Finding 数据类创建 [PASS]")


def test_finding_default_id():
    f1 = Finding(reviewer="R1", role="style", title="T1")
    f2 = Finding(reviewer="R2", role="style", title="T2")
    assert f1.id != f2.id, "自动生成的 id 应唯一"
    print("  1.2 Finding 自动生成唯一 id [PASS]")


def test_finding_default_values():
    f = Finding(reviewer="R", role="logic", title="T")
    assert f.severity == "minor"
    assert f.line_range == (0, 0)
    assert f.confidence == 0.0
    assert f.evidence == []
    assert f.suggestion == ""
    print("  1.3 Finding 默认值 [PASS]")


def test_agent_initialization_error():
    e = AgentInitializationError("测试错误")
    assert str(e) == "测试错误"
    print("  2.1 AgentInitializationError [PASS]")


def test_reviewer_agent_creation():
    model = MockModel()
    formatter = MockFormatter()
    agent = ReviewerAgent(
        name="SecurityReviewer",
        role="security",
        sys_prompt="你是一位安全审计专家。",
        model=model,
        formatter=formatter,
    )
    assert agent.name == "SecurityReviewer"
    assert agent.role == "security"
    assert agent.sys_prompt == "你是一位安全审计专家。"
    assert agent.model is model
    assert agent.formatter is formatter
    print("  3.1 ReviewerAgent 正常创建 [PASS]")


def test_reviewer_agent_empty_name():
    try:
        MockModel()
        ReviewerAgent(
            name="",
            role="security",
            sys_prompt="test",
            model=MockModel(),
            formatter=MockFormatter(),
        )
        assert False, "空 name 应抛出异常"
    except AgentInitializationError:
        print("  3.2 空 name 抛出 AgentInitializationError [PASS]")


def test_reviewer_agent_empty_sys_prompt():
    try:
        ReviewerAgent(
            name="Test",
            role="security",
            sys_prompt="",
            model=MockModel(),
            formatter=MockFormatter(),
        )
        assert False, "空 sys_prompt 应抛出异常"
    except AgentInitializationError:
        print("  3.3 空 sys_prompt 抛出 AgentInitializationError [PASS]")


def test_reviewer_agent_invalid_model():
    try:
        ReviewerAgent(
            name="Test",
            role="security",
            sys_prompt="test",
            model="not_a_model",
            formatter=MockFormatter(),
        )
        assert False, "非 ChatModelBase 应抛出异常"
    except AgentInitializationError:
        print("  3.4 无效 model 类型抛出 AgentInitializationError [PASS]")


def test_reviewer_agent_invalid_formatter():
    try:
        ReviewerAgent(
            name="Test",
            role="security",
            sys_prompt="test",
            model=MockModel(),
            formatter="not_a_formatter",
        )
        assert False, "非 FormatterBase 应抛出异常"
    except AgentInitializationError:
        print("  3.5 无效 formatter 类型抛出 AgentInitializationError [PASS]")


def test_build_review_prompt():
    model = MockModel()
    formatter = MockFormatter()
    agent = ReviewerAgent(
        name="TestReviewer",
        role="security",
        sys_prompt="你是一位安全审计专家。",
        model=model,
        formatter=formatter,
    )

    chunks = [
        DiffChunk(
            file_path="src/main.py",
            old_start=1,
            old_count=5,
            new_start=1,
            new_count=6,
            context="def foo():",
            additions=["    print('hello')"],
            deletions=["    print('hi')"],
            language="python",
        ),
    ]
    pr_ctx = PRContext(
        title="测试 PR",
        description="修复安全问题",
        author="test_user",
        labels=["bug"],
        base_branch="main",
        head_branch="fix-security",
    )

    prompt = agent._build_review_prompt(chunks, pr_ctx)
    assert "## PR 信息" in prompt
    assert "测试 PR" in prompt
    assert "修复安全问题" in prompt
    assert "test_user" in prompt
    assert "bug" in prompt
    assert "main" in prompt
    assert "fix-security" in prompt
    assert "## 代码变更" in prompt
    assert "src/main.py" in prompt
    assert "python" in prompt
    assert "print('hello')" in prompt
    assert "print('hi')" in prompt
    assert "severity" in prompt
    assert "confidence" in prompt
    print("  4.1 _build_review_prompt 生成完整提示词 [PASS]")


def test_build_review_prompt_empty_chunks():
    model = MockModel()
    formatter = MockFormatter()
    agent = ReviewerAgent(
        name="TestReviewer",
        role="security",
        sys_prompt="test",
        model=model,
        formatter=formatter,
    )
    pr_ctx = PRContext(title="Empty PR")
    prompt = agent._build_review_prompt([], pr_ctx)
    assert "0 个变更块" in prompt or "0" in prompt
    print("  4.2 _build_review_prompt 空 diff 块 [PASS]")


def test_parse_findings_from_msg():
    model = MockModel()
    formatter = MockFormatter()
    agent = ReviewerAgent(
        name="TestReviewer",
        role="security",
        sys_prompt="test",
        model=model,
        formatter=formatter,
    )

    msg = Msg(
        name="assistant",
        content="""```json
[
    {
        "severity": "critical",
        "file_path": "src/auth.py",
        "line_start": 15,
        "line_end": 25,
        "title": "硬编码密钥",
        "description": "API 密钥直接写在代码中",
        "suggestion": "使用环境变量",
        "confidence": 0.98,
        "evidence": ["第 15 行: API_KEY = 'sk-123456'"]
    }
]
```""",
        role="assistant",
    )

    findings = agent._parse_findings(msg)
    assert len(findings) == 1
    f = findings[0]
    assert f.reviewer == "TestReviewer"
    assert f.role == "security"
    assert f.severity == "critical"
    assert f.file_path == "src/auth.py"
    assert f.line_range == (15, 25)
    assert f.title == "硬编码密钥"
    assert f.suggestion == "使用环境变量"
    assert f.confidence == 0.98
    assert len(f.evidence) == 1
    print("  5.1 解析 Msg 中的 findings（JSON 代码块）[PASS]")


def test_parse_findings_from_chat_response():
    model = MockModel()
    formatter = MockFormatter()
    agent = ReviewerAgent(
        name="TestReviewer",
        role="security",
        sys_prompt="test",
        model=model,
        formatter=formatter,
    )

    response = ChatResponse(content=[
        TextBlock(type="text", text='[{"severity": "important", "file_path": "src/db.py", "title": "N+1 查询", "description": "循环中查询数据库", "suggestion": "使用 JOIN", "confidence": 0.75}]'),
    ])

    findings = agent._parse_findings(response)
    assert len(findings) == 1
    f = findings[0]
    assert f.reviewer == "TestReviewer"
    assert f.role == "security"
    assert f.severity == "important"
    assert f.file_path == "src/db.py"
    assert f.title == "N+1 查询"
    assert f.confidence == 0.75
    print("  5.2 解析 ChatResponse 中的 findings [PASS]")


def test_parse_findings_none():
    from agentscope.model import DashScopeChatModel
    from config import DASHSCOPE_API_KEY
    model = DashScopeChatModel(model_name="qwen-max", api_key=DASHSCOPE_API_KEY, stream=False)
    formatter = MockFormatter()
    agent = ReviewerAgent(
        name="TestReviewer",
        role="security",
        sys_prompt="test",
        model=model,
        formatter=formatter,
    )

    findings = agent._parse_findings(None)
    assert findings == []
    print("  5.3 解析 None 响应返回空列表 [PASS]")


def test_parse_findings_empty_text():
    model = MockModel()
    formatter = MockFormatter()
    agent = ReviewerAgent(
        name="TestReviewer",
        role="security",
        sys_prompt="test",
        model=model,
        formatter=formatter,
    )

    msg = Msg(name="assistant", content="没有发现问题", role="assistant")
    findings = agent._parse_findings(msg)
    assert findings == []
    print("  5.4 解析无 JSON 文本返回空列表 [PASS]")


def test_parse_findings_invalid_entry():
    model = MockModel()
    formatter = MockFormatter()
    agent = ReviewerAgent(
        name="TestReviewer",
        role="security",
        sys_prompt="test",
        model=model,
        formatter=formatter,
    )

    msg = Msg(
        name="assistant",
        content="""```json
[
    {"severity": "invalid_severity", "file_path": "x.py", "title": "T", "description": "D", "suggestion": "S", "confidence": 0.5},
    {"severity": "important", "file_path": "y.py", "title": "T2", "description": "D2", "suggestion": "S2", "confidence": 0.8}
]
```""",
        role="assistant",
    )

    findings = agent._parse_findings(msg)
    assert len(findings) == 1, f"期望 1 个有效 finding（无效 severity 应被跳过），实际 {len(findings)}"
    assert findings[0].file_path == "y.py"
    print("  5.5 无效 severity 条目被跳过 [PASS]")


def test_review_empty_diff():
    model = MockModel()
    formatter = MockFormatter()
    agent = ReviewerAgent(
        name="EmptyReviewer",
        role="style",
        sys_prompt="test",
        model=model,
        formatter=formatter,
    )

    import asyncio
    findings = asyncio.run(agent.review([], PRContext(title="Empty")))
    assert findings == [], "空 diff 应返回空列表"
    print("  6.1 review 空 diff 返回空列表 [PASS]")


def test_extract_text():
    model = MockModel()
    formatter = MockFormatter()
    agent = ReviewerAgent(
        name="Test",
        role="style",
        sys_prompt="test",
        model=model,
        formatter=formatter,
    )

    assert agent._extract_text(None) is None
    assert agent._extract_text("hello") == "hello"

    msg = Msg(name="user", content="hello world", role="user")
    assert agent._extract_text(msg) == "hello world"

    response = ChatResponse(content=[TextBlock(type="text", text="chat response")])
    assert agent._extract_text(response) == "chat response"

    print("  7.1 _extract_text 多种输入类型 [PASS]")


def test_try_parse_json():
    assert ReviewerAgent._try_parse_json('{"a": 1}') == {"a": 1}
    assert ReviewerAgent._try_parse_json('[1, 2, 3]') == [1, 2, 3]
    assert ReviewerAgent._try_parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert ReviewerAgent._try_parse_json('plain text') is None
    assert ReviewerAgent._try_parse_json('') is None
    print("  8.1 _try_parse_json 多种格式 [PASS]")


def test_agents_package_exports():
    from agents import (
        AgentInitializationError,
        Finding,
        ReviewerAgent,
        create_model,
        is_model_registered,
        list_registered_models,
        register_model,
        ModelRegistryError,
    )
    assert AgentInitializationError is not None
    assert Finding is not None
    assert ReviewerAgent is not None
    assert is_model_registered("dashscope")
    types = list_registered_models()
    assert "dashscope" in types
    print("  9.1 agents 包导出完整性 [PASS]")


if __name__ == "__main__":
    test_finding_dataclass()
    test_finding_default_id()
    test_finding_default_values()
    test_agent_initialization_error()
    test_reviewer_agent_creation()
    test_reviewer_agent_empty_name()
    test_reviewer_agent_empty_sys_prompt()
    test_reviewer_agent_invalid_model()
    test_reviewer_agent_invalid_formatter()
    test_build_review_prompt()
    test_build_review_prompt_empty_chunks()
    test_parse_findings_from_msg()
    test_parse_findings_from_chat_response()
    test_parse_findings_none()
    test_parse_findings_empty_text()
    test_parse_findings_invalid_entry()
    test_review_empty_diff()
    test_extract_text()
    test_try_parse_json()
    test_agents_package_exports()

    print("\n全部验证通过! [PASS]")
    sys.exit(0)
