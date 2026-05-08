"""F-07: 辩论循环引擎验证脚本"""

import asyncio
import sys
sys.path.insert(0, r"d:\project\code-review")

from typing import Any, Dict, List

from pipeline.debate_loop import DebateRecord, DebateRound, run_debate_loop
from agents.reviewer import Finding
from agents.prosecutor import ProsecutorAgent, Challenge
from agents.defender import DefenderAgent, Defense
from agents.base import AgentInitializationError

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


_formatter = MockFormatter()


class MockProsecutorModel(ChatModelBase):
    """模拟质疑者 LLM，返回结构化 Challenge 输出。"""

    def __init__(self, responses: List[Dict[str, Any]] | None = None) -> None:
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
                    id="call_pros",
                    name="generate_response",
                    input=raw,
                ),
            ],
        )


class MockDefenderModel(ChatModelBase):
    """模拟辩护者 LLM，返回结构化 Defense 输出。"""

    def __init__(self, responses: List[Dict[str, Any]] | None = None) -> None:
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
                    id="call_def",
                    name="generate_response",
                    input=raw,
                ),
            ],
        )


class ErrorModel(ChatModelBase):
    """模拟会抛出异常的模型。"""

    def __init__(self) -> None:
        super().__init__(model_name="error-model", stream=False)

    async def __call__(self, *args: Any, **kwargs: Any) -> ChatResponse:
        raise RuntimeError("模拟模型调用失败")


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


def _make_prosecutor(
    name: str = "质疑者",
    model: ChatModelBase | None = None,
) -> ProsecutorAgent:
    return ProsecutorAgent(
        name=name,
        role="prosecutor",
        sys_prompt="你是一个质疑者",
        model=model or MockProsecutorModel(),
        formatter=_formatter,
    )


def _make_defender(
    name: str = "辩护者",
    model: ChatModelBase | None = None,
) -> DefenderAgent:
    return DefenderAgent(
        name=name,
        role="defender",
        sys_prompt="你是一个辩护者",
        model=model or MockDefenderModel(),
        formatter=_formatter,
    )


def run_tests() -> None:
    print("=" * 60)
    print("F-07: 辩论循环引擎验证")
    print("=" * 60)

    # ---------------------------------------------------------------
    print("\n--- 1. DebateRound 数据类 ---")
    # ---------------------------------------------------------------

    r = DebateRound(round_number=1)
    check("默认创建", isinstance(r, DebateRound))
    check("round_number=1", r.round_number == 1)
    check("challenge 默认 None", r.challenge is None)
    check("defense 默认 None", r.defense is None)
    check("rebuttal 默认 None", r.rebuttal is None)

    c = Challenge(finding_id="f1", is_valid=False, reasons=["误报"], confidence=0.9)
    d = Defense(finding_id="f1", challenge_id="f1", finding_stands=True)
    r2 = DebateRound(round_number=2, challenge=c, defense=d, rebuttal="反驳")
    check("带数据创建", r2.round_number == 2)
    check("challenge 已设置", r2.challenge is not None)
    check("defense 已设置", r2.defense is not None)
    check("rebuttal 已设置", r2.rebuttal == "反驳")

    # ---------------------------------------------------------------
    print("\n--- 2. DebateRecord 数据类 ---")
    # ---------------------------------------------------------------

    f = _make_finding()
    rec = DebateRecord(finding_id=f.id, original_finding=f)
    check("默认创建", isinstance(rec, DebateRecord))
    check("finding_id 匹配", rec.finding_id == f.id)
    check("rounds 默认为空", rec.rounds == [])
    check("final_status 默认为 pending", rec.final_status == "pending")
    check("merged_into 默认 None", rec.merged_into is None)

    rec2 = DebateRecord(
        finding_id=f.id,
        original_finding=f,
        rounds=[r2],
        final_status="confirmed",
        merged_into=None,
    )
    check("带数据创建", rec2.final_status == "confirmed")
    check("rounds 含 1 轮", len(rec2.rounds) == 1)

    # ---------------------------------------------------------------
    print("\n--- 3. run_debate_loop - 空输入 ---")
    # ---------------------------------------------------------------

    async def test_empty():
        pros = _make_prosecutor()
        defd = _make_defender()
        records = await run_debate_loop(
            findings=[], prosecutor=pros, defender=defd,
            diff_context="", max_rounds=3,
        )
        check("空输入返回空列表", records == [])

    asyncio.run(test_empty())

    # ---------------------------------------------------------------
    print("\n--- 4. run_debate_loop - 单发现正常流程 ---")
    # ---------------------------------------------------------------

    async def test_single_confirmed():
        pros = _make_prosecutor()
        defd = _make_defender()
        finding = _make_finding()
        records = await run_debate_loop(
            findings=[finding], prosecutor=pros, defender=defd,
            diff_context="", max_rounds=3,
        )
        check("返回 1 条记录", len(records) == 1)
        rec = records[0]
        check("finding_id 匹配", rec.finding_id == finding.id)
        check("状态为 confirmed", rec.final_status == "confirmed")
        check("至少有 1 轮", len(rec.rounds) >= 1)
        check("第 1 轮有 challenge", rec.rounds[0].challenge is not None)
        check("第 1 轮有 defense", rec.rounds[0].defense is not None)
        check("defense.finding_stands=True", rec.rounds[0].defense.finding_stands is True)

    asyncio.run(test_single_confirmed())

    # ---------------------------------------------------------------
    print("\n--- 5. run_debate_loop - 发现被驳回 ---")
    # ---------------------------------------------------------------

    async def test_dismissed():
        pros_model = MockProsecutorModel(responses=[
            {"is_valid": False, "reasons": ["误报"], "confidence": 0.95},
        ])
        defd_model = MockDefenderModel(responses=[
            {"finding_stands": False, "counter_evidence": ["同意质疑，误报"],
             "revised_severity": None, "revised_confidence": 0.1},
        ])
        pros = _make_prosecutor(model=pros_model)
        defd = _make_defender(model=defd_model)
        finding = _make_finding()
        records = await run_debate_loop(
            findings=[finding], prosecutor=pros, defender=defd,
            diff_context="", max_rounds=1,
        )
        check("返回 1 条记录", len(records) == 1)
        check("状态为 dismissed", records[0].final_status == "dismissed")

    asyncio.run(test_dismissed())

    # ---------------------------------------------------------------
    print("\n--- 6. run_debate_loop - 多发现并行 ---")
    # ---------------------------------------------------------------

    async def test_multi_findings():
        pros = _make_prosecutor()
        defd = _make_defender()
        findings = [_make_finding(title="发现A", file_path="a.py"),
                    _make_finding(title="发现B", file_path="b.py")]
        records = await run_debate_loop(
            findings=findings, prosecutor=pros, defender=defd,
            diff_context="", max_rounds=2,
        )
        check("返回 2 条记录", len(records) == 2)
        check("各记录独立状态", all(r.final_status in ("confirmed", "dismissed") for r in records))

    asyncio.run(test_multi_findings())

    # ---------------------------------------------------------------
    print("\n--- 7. run_debate_loop - 低置信度触发多轮 ---")
    # ---------------------------------------------------------------

    async def test_low_confidence():
        pros_model = MockProsecutorModel(responses=[
            {"is_valid": True, "reasons": ["可能误报"], "confidence": 0.3},
            {"is_valid": True, "reasons": ["仍有疑问"], "confidence": 0.7},
        ])
        defd_model = MockDefenderModel(responses=[
            {"finding_stands": True, "counter_evidence": ["证据1"],
             "revised_severity": None, "revised_confidence": 0.3},
            {"finding_stands": True, "counter_evidence": ["证据2"],
             "revised_severity": None, "revised_confidence": 0.8},
        ])
        pros = _make_prosecutor(model=pros_model)
        defd = _make_defender(model=defd_model)
        finding = _make_finding()
        records = await run_debate_loop(
            findings=[finding], prosecutor=pros, defender=defd,
            diff_context="", max_rounds=3,
        )
        check("启动了 2 轮", len(records[0].rounds) == 2)
        check("最终状态 confirmed", records[0].final_status == "confirmed")

    asyncio.run(test_low_confidence())

    # ---------------------------------------------------------------
    print("\n--- 8. run_debate_loop - 质疑者异常回退 ---")
    # ---------------------------------------------------------------

    async def test_prosecutor_error():
        pros = _make_prosecutor(model=ErrorModel())
        defd = _make_defender()
        finding = _make_finding()
        records = await run_debate_loop(
            findings=[finding], prosecutor=pros, defender=defd,
            diff_context="", max_rounds=3,
        )
        check("返回 1 条记录", len(records) == 1)
        check("异常回退后 confirmed", records[0].final_status == "confirmed")
        check("至少有 1 轮", len(records[0].rounds) >= 1)
        if records[0].rounds:
            c = records[0].rounds[0].challenge
            check("质疑者默认认定有效", c is None or c.is_valid is True)

    asyncio.run(test_prosecutor_error())

    # ---------------------------------------------------------------
    print("\n--- 9. run_debate_loop - 辩护者异常回退 ---")
    # ---------------------------------------------------------------

    async def test_defender_error():
        pros = _make_prosecutor()
        defd = _make_defender(model=ErrorModel())
        finding = _make_finding()
        records = await run_debate_loop(
            findings=[finding], prosecutor=pros, defender=defd,
            diff_context="", max_rounds=3,
        )
        check("返回 1 条记录", len(records) == 1)
        check("异常回退后 confirmed", records[0].final_status == "confirmed")
        check("至少有 1 轮", len(records[0].rounds) >= 1)
        if records[0].rounds:
            d = records[0].rounds[0].defense
            check("辩护者默认认定有效", d is None or d.finding_stands is True)

    asyncio.run(test_defender_error())

    # ---------------------------------------------------------------
    print("\n--- 10. 包导出 ---")
    # ---------------------------------------------------------------

    from pipeline import DebateRecord as DR, DebateRound as DR2, run_debate_loop as RDL
    check("from pipeline import DebateRecord", True)
    check("from pipeline import DebateRound", True)
    check("from pipeline import run_debate_loop", True)

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
