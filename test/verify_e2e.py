"""F-15: 端到端集成测试

模拟完整评审流程，串联全部 6 个阶段：
评审 → 辩论 → 合并 → 裁决 → 报告 → 评估
所有 Agent 使用 MockModel 注入预定响应。
"""

import sys
import json
sys.path.insert(0, r"d:\project\code-review")

from typing import Any, List, Sequence

from agentscope.formatter import FormatterBase
from agentscope.message import Msg, TextBlock, ToolUseBlock
from agentscope.model import ChatModelBase, ChatResponse

from agents.reviewer import ReviewerAgent, Finding
from agents.prosecutor import ProsecutorAgent, Challenge
from agents.defender import DefenderAgent, Defense
from agents.evaluator import EvaluatorAgent, EvaluationResult

from tools.pr_parser import PRContext
from tools.diff_parser import DiffChunk
from tools.report_writer import generate_report

from pipeline.parallel_review import ParallelReviewManager
from pipeline.debate_loop import run_debate_loop
from pipeline.issue_merger import merge_similar_findings
from pipeline.verdict import make_final_verdict

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
    """支持顺序响应的 MockModel。

    responses 中的每个条目可以是：
      - dict with "text" key: 纯文本响应（用于 ReviewerAgent）
      - dict with "input" key: 结构化模型响应（用于 Prosecutor/Defender/Evaluator）
    """

    def __init__(self, responses: Sequence[dict] | None = None, **kwargs: Any) -> None:
        super().__init__(model_name="mock-e2e", stream=False)
        self._responses = list(responses) if responses else []
        self._call_count = 0
        self.total_calls = 0

    async def __call__(self, *args: Any, **kwargs: Any) -> ChatResponse:
        self._call_count += 1
        self.total_calls += 1
        resp = self._responses.pop(0) if self._responses else {}
        blocks: list = []

        if "text" in resp:
            blocks.append(TextBlock(type="text", text=resp["text"]))

        if "input" in resp:
            blocks.append(ToolUseBlock(
                type="tool_use",
                id=f"call_{self._call_count}",
                name="generate_response",
                input=resp["input"],
            ))

        if not blocks:
            blocks.append(TextBlock(type="text", text=""))

        return ChatResponse(content=blocks)


def _make_reviewer(
    name: str,
    role: str,
    sys_prompt: str,
    model: MockModel,
) -> ReviewerAgent:
    return ReviewerAgent(
        name=name,
        role=role,
        sys_prompt=sys_prompt,
        model=model,
        formatter=MockFormatter(),
    )


def _make_diff_chunks() -> List[DiffChunk]:
    return [
        DiffChunk(
            file_path="src/auth.py",
            old_start=10,
            old_count=5,
            new_start=10,
            new_count=8,
            context="def login():",
            additions=["    token = jwt.encode(payload, secret)"],
            deletions=["    token = generate_token()"],
            language="python",
        ),
        DiffChunk(
            file_path="src/db.py",
            old_start=50,
            old_count=3,
            new_start=50,
            new_count=7,
            context="def query_users():",
            additions=["    users = User.objects.filter(active=True)",
                       "    for u in users:"],
            deletions=["    users = User.objects.all()"],
            language="python",
        ),
    ]


def _make_pr_context() -> PRContext:
    return PRContext(
        title="安全修复与性能优化",
        description="修复 JWT 注入漏洞并优化数据库查询",
        author="dev_user",
        labels=["security", "performance"],
        base_branch="main",
        head_branch="fix-security",
    )


def run_tests() -> None:
    print("=" * 60)
    print("F-15: 端到端集成测试")
    print("=" * 60)

    # ===============================================================
    # Phase 1: 平行评审
    # ===============================================================
    print("\n--- Phase 1: 多评审者平行评审 ---")

    sec_responses = [
        {"text": json.dumps([
            {"severity": "critical", "file_path": "src/auth.py",
             "line_start": 12, "line_end": 15,
             "title": "JWT 签名未验证",
             "description": "JWT token 缺少签名验证",
             "suggestion": "添加签名验证逻辑", "confidence": 0.90},
        ])},
    ]
    perf_responses = [
        {"text": json.dumps([
            {"severity": "important", "file_path": "src/db.py",
             "line_start": 52, "line_end": 56,
             "title": "N+1 查询",
             "description": "循环中逐条查询",
             "suggestion": "使用 select_related 预加载", "confidence": 0.85},
        ])},
    ]

    sec_reviewer = _make_reviewer(
        "SecurityReviewer", "security",
        "你是一位安全审计专家。",
        MockModel(sec_responses),
    )
    perf_reviewer = _make_reviewer(
        "PerformanceReviewer", "performance",
        "你是一位性能优化专家。",
        MockModel(perf_responses),
    )

    diff_chunks = _make_diff_chunks()
    pr_context = _make_pr_context()

    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    manager = ParallelReviewManager(
        reviewers=[sec_reviewer, perf_reviewer],
        timeout=30,
    )
    parallel_result = loop.run_until_complete(
        manager.run_all(diff_chunks, pr_context),
    )

    all_findings = parallel_result.findings
    check("评审产生发现 > 0", len(all_findings) > 0)
    check("至少含一个 critical", any(f.severity == "critical" for f in all_findings))
    check("至少含一个 important", any(f.severity == "important" for f in all_findings))
    check("含 security 角色", any(f.role == "security" for f in all_findings))
    check("含 performance 角色", any(f.role == "performance" for f in all_findings))
    check("所有评审者成功", len(parallel_result.failed_reviewers) == 0)
    print(f"  发现数: {len(all_findings)}")

    # ===============================================================
    # Phase 2: 辩论循环
    # ===============================================================
    print("\n--- Phase 2: 辩论循环 ---")

    prosecutor_responses = [
        {"input": {"is_valid": True, "reasons": ["确认存在安全隐患"],
                   "confidence": 0.80}},
        {"input": {"is_valid": True, "reasons": ["确认存在性能问题"],
                   "confidence": 0.75}},
    ]
    defender_responses = [
        {"input": {"finding_stands": True, "counter_evidence": ["代码未验证签名"],
                   "revised_severity": None, "revised_confidence": 0.90}},
        {"input": {"finding_stands": True, "counter_evidence": ["循环查询无缓存"],
                   "revised_severity": "important", "revised_confidence": 0.85}},
    ]

    prosecutor = ProsecutorAgent(
        name="ProsecutorAgent",
        role="prosecutor",
        sys_prompt="你是一位质疑者。",
        model=MockModel(prosecutor_responses),
        formatter=MockFormatter(),
    )
    defender = DefenderAgent(
        name="DefenderAgent",
        role="defender",
        sys_prompt="你是一位辩护者。",
        model=MockModel(defender_responses),
        formatter=MockFormatter(),
    )

    diff_context = "src/auth.py: JWT 编码; src/db.py: ORM 查询"
    debate_records = loop.run_until_complete(run_debate_loop(
        findings=all_findings,
        prosecutor=prosecutor,
        defender=defender,
        diff_context=diff_context,
        max_rounds=1,
        confidence_threshold=0.6,
    ))

    check("辩论记录数与发现数一致", len(debate_records) == len(all_findings))
    for dr in debate_records:
        has_challenge = any(r.challenge is not None for r in dr.rounds)
        has_defense = any(r.defense is not None for r in dr.rounds)
        check(f"finding {dr.finding_id[:8]} 有质疑", has_challenge)
        check(f"finding {dr.finding_id[:8]} 有辩护", has_defense)
        check(f"finding {dr.finding_id[:8]} 状态为 confirmed",
              dr.final_status == "confirmed")

    # ===============================================================
    # Phase 3: 发现合并
    # ===============================================================
    print("\n--- Phase 3: 发现合并 ---")

    merge_records = merge_similar_findings(debate_records, similarity_threshold=0.9)
    check("合并记录类型正确", isinstance(merge_records, list))
    print(f"  合并记录数: {len(merge_records)}")

    # ===============================================================
    # Phase 4: 最终裁决
    # ===============================================================
    print("\n--- Phase 4: 最终裁决 ---")

    verdict = make_final_verdict(debate_records, merge_records)
    check("Verdict 含 findings", len(verdict.findings) > 0)
    check("Verdict summary 非空", len(verdict.summary) > 0)
    check("Verdict dismissed 存在", isinstance(verdict.dismissed, list))
    print(f"  最终发现: {len(verdict.findings)}, 驳回: {len(verdict.dismissed)}")

    # ===============================================================
    # Phase 5: 报告生成
    # ===============================================================
    print("\n--- Phase 5: 报告生成 ---")

    md_report = generate_report(verdict, pr_context, "变更 2 个文件", "markdown")
    check("Markdown 报告非空", len(md_report) > 0)
    check("含报告标题", "PR Review Report" in md_report)
    check("含 PR 标题", "安全修复与性能优化" in md_report)
    check("含评审概览", "评审概览" in md_report)
    check("含发现详情", "发现详情" in md_report)
    check("含变更摘要", "变更 2 个文件" in md_report)
    check("含自动生成标记", "自动生成" in md_report)

    html_report = generate_report(verdict, pr_context, "变更 2 个文件", "html")
    check("HTML 报告非空", len(html_report) > 0)
    check("HTML 含 DOCTYPE", "<!DOCTYPE html>" in html_report)

    json_report = generate_report(verdict, pr_context, "变更 2 个文件", "json")
    parsed = json.loads(json_report)
    check("JSON 可解析", isinstance(parsed, dict))
    check("JSON 含 findings", len(parsed["verdict"]["findings"]) > 0)

    # ===============================================================
    # Phase 6: 质量评估
    # ===============================================================
    print("\n--- Phase 6: AI 质量评估 ---")

    evaluator_model = MockModel([
        {"input": {
            "score": 0.82,
            "coverage_score": 0.75,
            "clarity_score": 0.85,
            "actionability_score": 0.80,
            "summary": "评审质量良好",
            "improvement_suggestions": ["增加更多安全相关检查"],
        }},
    ])
    evaluator = EvaluatorAgent(
        name="EvaluatorAgent",
        model=evaluator_model,
        formatter=MockFormatter(),
    )
    eval_result = loop.run_until_complete(
        evaluator.evaluate(verdict, pr_context),
    )
    check("评估返回 EvaluationResult", isinstance(eval_result, EvaluationResult))
    check("评估 score > 0", eval_result.score > 0)
    check("评估 summary 非空", len(eval_result.summary) > 0)
    check("评估 suggestions 存在",
          len(eval_result.improvement_suggestions) > 0)

    loop.close()

    # ===============================================================
    print("\n--- 7. 包导出 ---")
    # ===============================================================

    from tools.report_writer import generate_report as GR
    from pipeline.verdict import make_final_verdict as MFV
    from pipeline.issue_merger import merge_similar_findings as MSF
    from pipeline.debate_loop import run_debate_loop as RDL
    from pipeline.parallel_review import ParallelReviewManager as PRM
    check("from pipeline.parallel_review import ParallelReviewManager", True)
    check("from pipeline.debate_loop import run_debate_loop", True)
    check("from pipeline.issue_merger import merge_similar_findings", True)
    check("from pipeline.verdict import make_final_verdict", True)

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