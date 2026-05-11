"""F-08: 质疑者 Agent 验证脚本"""

import asyncio
import sys
sys.path.insert(0, r"d:\project\code-review")

from typing import Any, List

from agents import Finding, ProsecutorAgent, Challenge
from agents.finding import _SEVERITY_VALUES

from agentscope.model import ChatModelBase, ChatResponse
from agentscope.message import TextBlock, ToolUseBlock
from agentscope.formatter import FormatterBase


passed = 0
failed = 0
errors: List[str] = []


class MockFormatter(FormatterBase):
    """模拟 formatter。"""

    async def format(self, *args: Any, **kwargs: Any) -> List[dict]:
        return []


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        msg = f"  [FAIL] {name}" + (f" - {detail}" if detail else "")
        print(msg)
        errors.append(msg)


class MockModel(ChatModelBase):
    """模拟 LLM 模型，返回 ToolUseBlock 触发 structured_model 流程。"""

    def __init__(self, responses: List[dict] | None = None) -> None:
        super().__init__(model_name="mock-prosecutor", stream=False)
        self.responses = responses or []
        self.call_count = 0

    async def __call__(self, *args: Any, **kwargs: Any) -> ChatResponse:
        self.call_count += 1
        if self.responses:
            raw = self.responses.pop(0)
        else:
            raw = {
                "is_valid": True,
                "reasons": ["证据充分", "逻辑合理"],
                "confidence": 0.85,
            }
        return ChatResponse(
            content=[
                TextBlock(type="text", text="质疑分析完成"),
                ToolUseBlock(
                    type="tool_use",
                    id="call_1",
                    name="generate_response",
                    input=raw,
                ),
            ],
        )

    def _parse_next_response(self, *args, **kwargs):
        pass


class ErrorModel(ChatModelBase):
    """模拟会抛出异常的模型。"""

    def __init__(self) -> None:
        super().__init__(model_name="error-model", stream=False)

    async def __call__(self, *args: Any, **kwargs: Any) -> ChatResponse:
        raise RuntimeError("模拟模型调用失败")

    def _parse_next_response(self, *args, **kwargs):
        pass


def _make_finding(
    severity: str = "minor",
    reviewer: str = "R1",
    role: str = "security",
    title: str = "测试发现",
    file_path: str = "src/test.py",
) -> Finding:
    return Finding(
        severity=severity,
        reviewer=reviewer,
        role=role,
        title=title,
        file_path=file_path,
        line_range=(10, 20),
        description="这是一个测试发现",
        suggestion="修复建议",
        confidence=0.9,
        evidence=["第 15 行: 可疑代码"],
    )


_formatter = MockFormatter()


def _make_prosecutor(
    name: str = "质疑者",
    model: ChatModelBase | None = None,
) -> ProsecutorAgent:
    return ProsecutorAgent(
        name=name,
        role="prosecutor",
        sys_prompt="你是一个质疑者",
        model=model or MockModel(),
        formatter=_formatter,
    )


def run_tests() -> None:
    print("=" * 60)
    print("F-08: 质疑者 Agent 验证")
    print("=" * 60)

    # ---------------------------------------------------------------
    print("\n--- 1. Challenge 数据类 ---")
    # ---------------------------------------------------------------

    # 1.1 默认创建
    c = Challenge()
    check("Challenge 默认创建", isinstance(c, Challenge))
    check("finding_id 默认为空", c.finding_id == "")
    check("is_valid 默认为 True", c.is_valid is True)
    check("reasons 默认为空列表", c.reasons == [])
    check("confidence 默认为 0.0", c.confidence == 0.0)

    # 1.2 带数据创建
    c2 = Challenge(
        finding_id="f123",
        is_valid=False,
        reasons=["误报"],
        confidence=0.95,
    )
    check("带数据创建", c2.finding_id == "f123")
    check("is_valid=False", c2.is_valid is False)
    check("reasons 含误报", "误报" in c2.reasons)
    check("confidence=0.95", c2.confidence == 0.95)

    # ---------------------------------------------------------------
    print("\n--- 2. ProsecutorAgent 初始化 ---")
    # ---------------------------------------------------------------

    # 2.1 正常创建
    model = MockModel()
    agent = _make_prosecutor(model=model)
    check("正常创建", isinstance(agent, ProsecutorAgent))
    check("name 属性", agent.name == "质疑者")

    check("role 属性", agent.role == "prosecutor")

    # ---------------------------------------------------------------
    print("\n--- 3. challenge 方法 - 正常流程 ---")
    # ---------------------------------------------------------------

    async def test_challenge_normal():
        model = MockModel()
        agent = _make_prosecutor(model=model)
        finding = _make_finding()
        result = await agent.challenge(finding)

        check("返回 Challenge", isinstance(result, Challenge))
        check("finding_id 匹配", result.finding_id == finding.id)
        check("is_valid=True", result.is_valid is True)
        check("有质疑理由", len(result.reasons) > 0)
        check("confidence=0.85", result.confidence == 0.85)
        check("模型被调用 1 次", model.call_count == 1)

    asyncio.run(test_challenge_normal())

    # ---------------------------------------------------------------
    print("\n--- 4. challenge 方法 - 质疑成立(is_valid=False) ---")
    # ---------------------------------------------------------------

    async def test_challenge_invalid():
        model = MockModel(responses=[
            {
                "is_valid": False,
                "reasons": ["此问题已在其他文件中修复", "不是本次变更引入"],
                "confidence": 0.92,
            },
        ])
        agent = _make_prosecutor(model=model)
        finding = _make_finding()
        result = await agent.challenge(finding)

        check("质疑成立 is_valid=False", result.is_valid is False)
        check("含 2 条理由", len(result.reasons) == 2)
        check("confidence>0.9", result.confidence > 0.9)

    asyncio.run(test_challenge_invalid())

    # ---------------------------------------------------------------
    print("\n--- 5. challenge 方法 - 模型异常回退 ---")
    # ---------------------------------------------------------------

    async def test_challenge_error():
        model = ErrorModel()
        agent = _make_prosecutor(model=model)
        finding = _make_finding()
        result = await agent.challenge(finding)

        check("异常回退返回 Challenge", isinstance(result, Challenge))
        check("回退 is_valid=True", result.is_valid is True)
        check("回退 confidence=0.5", result.confidence == 0.5)
        check("含回退理由", len(result.reasons) > 0)

    asyncio.run(test_challenge_error())

    # ---------------------------------------------------------------
    print("\n--- 6. _build_challenge_prompt ---")
    # ---------------------------------------------------------------

    agent = _make_prosecutor()
    finding = _make_finding(
        severity="critical",
        title="硬编码密钥",
        file_path="src/auth.py",
    )
    prompt = agent._build_challenge_prompt(finding)

    check("提示词含评审者", "R1" in prompt)
    check("提示词含维度", "security" in prompt)
    check("提示词含严重级别", "critical" in prompt)
    check("提示词含标题", "硬编码密钥" in prompt)
    check("提示词含文件路径", "src/auth.py" in prompt)
    check("提示词含分析角度", "误报" in prompt)
    check("提示词含角色设定", "质疑者" in prompt)

    # ---------------------------------------------------------------
    print("\n--- 7. 包导出 ---")
    # ---------------------------------------------------------------

    check("from agents import ProsecutorAgent", True)
    check("from agents import Challenge", True)

    print("\n" + "=" * 60)
    total = passed + failed
    print(f"  总计: {total}  |  通过: {passed}  |  失败: {failed}")
    print("=" * 60)

    if errors:
        print("\n失败详情:")
        for e in errors:
            print(e)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run_tests()
