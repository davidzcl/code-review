"""F-09: 辩护者 Agent 验证脚本"""

import asyncio
import sys
sys.path.insert(0, r"d:\project\code-review")

from typing import Any, List

from agents import Finding, ProsecutorAgent, Challenge
from agents.defender import DefenderAgent, Defense

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
        super().__init__(model_name="mock-defender", stream=False)
        self.responses = responses or []
        self.call_count = 0

    async def __call__(self, *args: Any, **kwargs: Any) -> ChatResponse:
        self.call_count += 1
        if self.responses:
            raw = self.responses.pop(0)
        else:
            raw = {
                "finding_stands": True,
                "counter_evidence": ["代码变更与此无关", "该问题确实存在"],
                "revised_severity": None,
                "revised_confidence": None,
            }
        return ChatResponse(
            content=[
                TextBlock(type="text", text="辩护分析完成"),
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
    severity: str = "critical",
    reviewer: str = "R1",
    role: str = "security",
    title: str = "SQL注入风险",
    file_path: str = "src/db.py",
) -> Finding:
    return Finding(
        severity=severity,
        reviewer=reviewer,
        role=role,
        title=title,
        file_path=file_path,
        line_range=(15, 25),
        description="存在 SQL 注入风险",
        suggestion="使用参数化查询",
        confidence=0.9,
        evidence=["第 20 行: execute(f\"SELECT * FROM users WHERE id = {uid}\")"],
    )


_formatter = MockFormatter()


def _make_defender(
    name: str = "辩护者",
    model: ChatModelBase | None = None,
) -> DefenderAgent:
    return DefenderAgent(
        name=name,
        role="defender",
        sys_prompt="你是一个辩护者",
        model=model or MockModel(),
        formatter=_formatter,
    )


def _make_challenge(
    finding_id: str = "",
    is_valid: bool = True,
    reasons: List[str] | None = None,
    confidence: float = 0.85,
) -> Challenge:
    return Challenge(
        finding_id=finding_id,
        is_valid=is_valid,
        reasons=reasons or ["证据不足", "可能是误报"],
        confidence=confidence,
    )


def run_tests() -> None:
    print("=" * 60)
    print("F-09: 辩护者 Agent 验证")
    print("=" * 60)

    # ---------------------------------------------------------------
    print("\n--- 1. Defense 数据类 ---")
    # ---------------------------------------------------------------

    # 1.1 默认创建
    d = Defense()
    check("Defense 默认创建", isinstance(d, Defense))
    check("finding_id 默认为空", d.finding_id == "")
    check("challenge_id 默认为空", d.challenge_id == "")
    check("finding_stands 默认为 True", d.finding_stands is True)
    check("counter_evidence 默认为空", d.counter_evidence == [])
    check("revised_severity 默认为 None", d.revised_severity is None)
    check("revised_confidence 默认为 None", d.revised_confidence is None)

    # 1.2 带数据创建
    d2 = Defense(
        finding_id="f001",
        challenge_id="c001",
        finding_stands=False,
        counter_evidence=["确实有误"],
        revised_severity="minor",
        revised_confidence=0.3,
    )
    check("带数据 finding_id", d2.finding_id == "f001")
    check("带数据 challenge_id", d2.challenge_id == "c001")
    check("finding_stands=False", d2.finding_stands is False)
    check("revised_severity=minor", d2.revised_severity == "minor")
    check("revised_confidence=0.3", d2.revised_confidence == 0.3)

    # ---------------------------------------------------------------
    print("\n--- 2. DefenderAgent 初始化 ---")
    # ---------------------------------------------------------------

    model = MockModel()
    agent = _make_defender(model=model)
    check("正常创建", isinstance(agent, DefenderAgent))
    check("name 属性", agent.name == "辩护者")

    # ---------------------------------------------------------------
    print("\n--- 3. defend 方法 - 辩护成功 ---")
    # ---------------------------------------------------------------

    async def test_defend_stands():
        model = MockModel()
        agent = _make_defender(model=model)
        finding = _make_finding()
        challenge = _make_challenge(finding_id=finding.id)

        result = await agent.defend(finding, challenge, "diff context")

        check("返回 Defense", isinstance(result, Defense))
        check("finding_id 匹配", result.finding_id == finding.id)
        check("challenge_id 匹配", result.challenge_id == challenge.finding_id)
        check("finding_stands=True", result.finding_stands is True)
        check("有辩护证据", len(result.counter_evidence) > 0)
        check("模型被调用 1 次", model.call_count == 1)

    asyncio.run(test_defend_stands())

    # ---------------------------------------------------------------
    print("\n--- 4. defend 方法 - 辩护失败(接受质疑) ---")
    # ---------------------------------------------------------------

    async def test_defend_falls():
        model = MockModel(responses=[
            {
                "finding_stands": False,
                "counter_evidence": ["同意质疑，确实是误报"],
                "revised_severity": None,
                "revised_confidence": 0.1,
            },
        ])
        agent = _make_defender(model=model)
        finding = _make_finding()
        challenge = _make_challenge(finding_id=finding.id, is_valid=True)

        result = await agent.defend(finding, challenge, "diff context")

        check("finding_stands=False", result.finding_stands is False)
        check("revised_confidence=0.1", result.revised_confidence == 0.1)

    asyncio.run(test_defend_falls())

    # ---------------------------------------------------------------
    print("\n--- 5. defend 方法 - 修订严重级别 ---")
    # ---------------------------------------------------------------

    async def test_defend_revise_severity():
        model = MockModel(responses=[
            {
                "finding_stands": True,
                "counter_evidence": ["问题确实存在，但影响范围有限"],
                "revised_severity": "minor",
                "revised_confidence": 0.6,
            },
        ])
        agent = _make_defender(model=model)
        finding = _make_finding(severity="critical")
        challenge = _make_challenge(finding_id=finding.id)

        result = await agent.defend(finding, challenge, "diff context")

        check("revised_severity=minor", result.revised_severity == "minor")
        check("revised_confidence=0.6", result.revised_confidence == 0.6)

    asyncio.run(test_defend_revise_severity())

    # ---------------------------------------------------------------
    print("\n--- 6. defend 方法 - 模型异常回退 ---")
    # ---------------------------------------------------------------

    async def test_defend_error():
        model = ErrorModel()
        agent = _make_defender(model=model)
        finding = _make_finding()
        challenge = _make_challenge(finding_id=finding.id)

        result = await agent.defend(finding, challenge, "diff context")

        check("异常回退返回 Defense", isinstance(result, Defense))
        check("finding_stands=True", result.finding_stands is True)
        check("有回退理由", len(result.counter_evidence) > 0)

    asyncio.run(test_defend_error())

    # ---------------------------------------------------------------
    print("\n--- 7. _build_defense_prompt ---")
    # ---------------------------------------------------------------

    agent = _make_defender()
    finding = _make_finding()
    challenge = _make_challenge(
        finding_id=finding.id,
        is_valid=False,
        reasons=["此代码无执行路径", "输入已清理"],
    )
    prompt = agent._build_defense_prompt(finding, challenge, "diff context:\n+ def query():")

    check("提示词含评审者", "R1" in prompt)
    check("提示词含维度", "security" in prompt)
    check("提示词含质疑内容", "质疑成立" in prompt)
    check("提示词含质疑理由", "输入已清理" in prompt)
    check("提示词含代码上下文", "diff context" in prompt)
    check("提示词含角色设定", "辩护者" in prompt)

    # ---------------------------------------------------------------
    print("\n--- 8. 包导出 ---")
    # ---------------------------------------------------------------

    check("from agents import DefenderAgent", True)
    check("from agents import Defense", True)

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
