"""F-14: AI 质量评估模块验证脚本"""

import sys
sys.path.insert(0, r"d:\project\code-review")

from typing import Any, List, Sequence

from agentscope.formatter import FormatterBase
from agentscope.message import Msg, TextBlock, ToolUseBlock
from agentscope.model import ChatModelBase, ChatResponse

from agents import (
    AgentInitializationError,
    EvaluatorAgent,
    EvaluationResult,
)
from agents.reviewer import Finding
from pipeline.verdict import Verdict
from pipeline.issue_merger import MergeRecord
from tools.pr_parser import PRContext

passed = 0
failed = 0
errors: List[str] = []


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


class MockFormatter(FormatterBase):
    async def format(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return [{"role": "user", "content": "mock"}]


class MockModel(ChatModelBase):
    def __init__(self, responses: Sequence[dict] | None = None, **kwargs: Any) -> None:
        super().__init__(model_name="mock-eval", stream=False)
        self._responses = list(responses) if responses else []
        self._call_count = 0

    async def __call__(self, *args: Any, **kwargs: Any) -> ChatResponse:
        self._call_count += 1
        if self._responses:
            resp = self._responses.pop(0)
            return ChatResponse(content=[
                TextBlock(type="text", text=resp.get("text", "")),
                ToolUseBlock(
                    type="tool_use",
                    id=f"call_{self._call_count}",
                    name="generate_response",
                    input=resp.get("input", {}),
                ),
            ])
        return ChatResponse(content=[
            TextBlock(type="text", text="评估完成"),
            ToolUseBlock(
                type="tool_use",
                id="call_default",
                name="generate_response",
                input={
                    "score": 0.85,
                    "coverage_score": 0.80,
                    "clarity_score": 0.90,
                    "actionability_score": 0.75,
                    "summary": "评审质量良好",
                    "improvement_suggestions": ["增加更多安全相关检查"],
                },
            ),
        ])


def _make_evaluator(model: ChatModelBase | None = None) -> EvaluatorAgent:
    return EvaluatorAgent(
        name="EvalAgent",
        model=model or MockModel(),
        formatter=MockFormatter(),
    )


def _finding(
    title: str = "test",
    file_path: str = "a.py",
    severity: str = "minor",
    role: str = "security",
    suggestion: str = "修复建议",
) -> Finding:
    return Finding(
        severity=severity,
        reviewer="R1",
        role=role,
        title=title,
        file_path=file_path,
        line_range=(10, 20),
        description=f"desc {title}",
        suggestion=suggestion,
        confidence=0.85,
        evidence=["line 15: code"],
    )


async def run_tests() -> None:
    print("=" * 60)
    print("F-14: AI 质量评估模块验证")
    print("=" * 60)

    # ---------------------------------------------------------------
    print("\n--- 1. EvaluationResult 数据类 ---")
    # ---------------------------------------------------------------

    r = EvaluationResult()
    check("默认创建", isinstance(r, EvaluationResult))
    check("score 默认 0.0", r.score == 0.0)
    check("improvement_suggestions 默认空", r.improvement_suggestions == [])
    check("summary 默认空", r.summary == "")

    r2 = EvaluationResult(
        score=0.85,
        coverage_score=0.80,
        clarity_score=0.90,
        actionability_score=0.75,
        summary="好",
        improvement_suggestions=["增加更多检查"],
    )
    check("带数据创建", r2.score == 0.85)
    check("coverage_score", r2.coverage_score == 0.80)

    # ---------------------------------------------------------------
    print("\n--- 2. EvaluatorAgent 初始化 ---")
    # ---------------------------------------------------------------

    agent = _make_evaluator()
    check("正常创建", isinstance(agent, EvaluatorAgent))
    check("role", agent.role == "evaluator")

    try:
        EvaluatorAgent(name="", model=agent.model, formatter=MockFormatter())
        check("空 name 应抛出异常", False, "未抛出 AgentInitializationError")
    except AgentInitializationError:
        check("空 name 抛出 AgentInitializationError", True)

    try:
        EvaluatorAgent(name="E", model="not_model", formatter=MockFormatter())
        check("非 ChatModelBase 应抛出异常", False, "未抛出")
    except AgentInitializationError:
        check("非 ChatModelBase 抛出异常", True)

    try:
        EvaluatorAgent(name="E", model=agent.model, formatter="not_formatter")
        check("非 FormatterBase 应抛出异常", False, "未抛出")
    except AgentInitializationError:
        check("非 FormatterBase 抛出异常", True)

    # ---------------------------------------------------------------
    print("\n--- 3. evaluate - 结构化模型返回 ---")
    # ---------------------------------------------------------------

    model = MockModel([
        {"input": {
            "score": 0.75,
            "coverage_score": 0.70,
            "clarity_score": 0.80,
            "actionability_score": 0.65,
            "summary": "中等质量",
            "improvement_suggestions": ["增加行号引用", "细化建议"],
        }},
    ])
    agent = _make_evaluator(model)
    v = Verdict(
        findings=[_finding("SQL注入", "db.py", "critical")],
        merged=[MergeRecord("p1", ["m1"], "相似")],
        summary="发现 1 个问题",
    )
    result = await agent.evaluate(v, PRContext(title="Test"))
    check("返回 EvaluationResult", isinstance(result, EvaluationResult))
    check("score", result.score == 0.75)
    check("coverage_score", result.coverage_score == 0.70)
    check("clarity_score", result.clarity_score == 0.80)
    check("actionability_score", result.actionability_score == 0.65)
    check("summary 非空", "中等质量" in result.summary)
    check("improvement_suggestions 非空", len(result.improvement_suggestions) > 0)

    # ---------------------------------------------------------------
    print("\n--- 4. _fallback_evaluation 直接验证 ---")
    # ---------------------------------------------------------------

    agent = _make_evaluator()

    # ---------------------------------------------------------------
    print("\n--- 6. _build_eval_prompt ---")
    # ---------------------------------------------------------------

    agent = _make_evaluator()
    v = Verdict(
        findings=[_finding("测试发现", "main.py", "important")],
        summary="评审总结",
    )
    prompt = agent._build_eval_prompt(v, PRContext(title="PR标题"))
    check("含 PR 信息标题", "PR标题" in prompt)
    check("含评审结果总结", "评审总结" in prompt)
    check("含发现列表", "测试发现" in prompt)
    check("含文件路径", "main.py" in prompt)
    check("含评估要求", "评估要求" in prompt)

    # ---------------------------------------------------------------
    print("\n--- 7. _fallback_evaluation ---")
    # ---------------------------------------------------------------

    agent = _make_evaluator()

    # 空
    result = agent._fallback_evaluation(Verdict())
    check("空 verdict 回退 score=0.5", result.score == 0.5)
    check("空 verdict  suggestions 非空", len(result.improvement_suggestions) > 0)

    # 全覆盖
    fs = [
        _finding("A", "a.py", "critical", "security", suggestion="s1"),
        _finding("B", "b.py", "important", "performance", suggestion="s2"),
        _finding("C", "c.py", "minor", "logic", suggestion="s3"),
        _finding("D", "d.py", "minor", "style", suggestion="s4"),
    ]
    result = agent._fallback_evaluation(Verdict(findings=fs))
    check("4 维度覆盖", result.score > 0)
    check("coverage_score = 1.0", result.coverage_score == 1.0)
    check("actionability_score = 1.0", result.actionability_score == 1.0)

    # 部分覆盖
    fs2 = [
        _finding("A", "a.py", "critical", "security"),
        _finding("B", "", "important", ""),
    ]
    result = agent._fallback_evaluation(Verdict(findings=fs2))
    check("部分覆盖 score < 1.0", result.score < 1.0)
    check("clarity_score < 1.0", result.clarity_score < 1.0)

    # ---------------------------------------------------------------
    print("\n--- 8. 包导出 ---")
    # ---------------------------------------------------------------

    from agents.evaluator import EvaluatorAgent as EA, EvaluationResult as ER
    check("from agents.evaluator import EvaluatorAgent", True)
    check("from agents.evaluator import EvaluationResult", True)

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
    import asyncio
    asyncio.run(run_tests())