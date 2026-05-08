"""F-06: 多评审者并行调度验证脚本"""

import asyncio
import sys
sys.path.insert(0, r"d:\project\code-review")

from typing import Any, List

from agents.reviewer import Finding
from pipeline import ParallelReviewManager, ParallelReviewResult
from tools.diff_parser import DiffChunk
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


class MockReviewer:
    """模拟评审者，用于并行调度测试。"""

    def __init__(self, name: str, findings: List[Finding], fail: bool = False):
        self.name = name
        self._findings = findings
        self._fail = fail
        self.call_count = 0

    async def review(
        self,
        diff_chunks: List[DiffChunk],
        pr_context: PRContext,
    ) -> List[Finding]:
        self.call_count += 1
        if self._fail:
            raise RuntimeError(f"{self.name} 模拟失败")
        return list(self._findings)


class SlowReviewer:
    """慢速评审者，用于超时测试。"""

    def __init__(self, name: str, delay: float):
        self.name = name
        self._delay = delay

    async def review(
        self,
        diff_chunks: List[DiffChunk],
        pr_context: PRContext,
    ) -> List[Finding]:
        await asyncio.sleep(self._delay)
        return [Finding(severity="minor", title="慢速发现")]


def _make_finding(
    severity: str = "minor",
    reviewer: str = "",
    role: str = "",
    title: str = "",
) -> Finding:
    return Finding(
        severity=severity,
        reviewer=reviewer,
        role=role,
        title=title,
    )


def run_tests() -> None:
    print("=" * 60)
    print("F-06: 多评审者并行调度验证")
    print("=" * 60)

    # ---------------------------------------------------------------
    print("\n--- 1. ParallelReviewResult ---")
    # ---------------------------------------------------------------

    # 1.1 默认创建
    result = ParallelReviewResult()
    check("创建 ParallelReviewResult 实例", isinstance(result, ParallelReviewResult))
    check("findings 默认为空列表", result.findings == [])
    check("reviewer_results 默认为空 dict", result.reviewer_results == {})
    check("total_reviewers 默认为 0", result.total_reviewers == 0)
    check("successful_reviewers 默认为 0", result.successful_reviewers == 0)
    check("failed_reviewers 默认为空列表", result.failed_reviewers == [])

    # 1.2 带数据创建
    findings = [_make_finding(severity="critical", title="问题1")]
    data_result = ParallelReviewResult(
        findings=findings,
        reviewer_results={"R1": findings},
        total_reviewers=2,
        successful_reviewers=2,
        failed_reviewers=[],
    )
    check("带数据创建结果正确", data_result.total_reviewers == 2)
    check("findings 数据正确", len(data_result.findings) == 1)
    check("reviewer_results 数据正确", "R1" in data_result.reviewer_results)

    # ---------------------------------------------------------------
    print("\n--- 2. ParallelReviewManager 初始化 ---")
    # ---------------------------------------------------------------

    # 2.1 正常创建
    reviewers = [
        MockReviewer("R1", [_make_finding(title="A")]),
        MockReviewer("R2", [_make_finding(title="B")]),
    ]
    mgr = ParallelReviewManager(reviewers)
    check("并行管理器正常创建", isinstance(mgr, ParallelReviewManager))
    check("reviewers 属性返回副本", len(mgr.reviewers) == 2)
    check("result 初始为 None", mgr.result is None)

    # 2.2 空列表创建
    try:
        ParallelReviewManager([])
        check("空 reviewers 抛出 ValueError", False)
    except ValueError:
        check("空 reviewers 抛出 ValueError", True)

    # ---------------------------------------------------------------
    print("\n--- 3. run_all 基本并行 ---")
    # ---------------------------------------------------------------

    async def test_basic_parallel():
        r1 = MockReviewer("R1", [
            _make_finding(severity="critical", reviewer="R1", role="security", title="安全问题"),
        ])
        r2 = MockReviewer("R2", [
            _make_finding(severity="important", reviewer="R2", role="performance", title="性能问题"),
            _make_finding(severity="minor", reviewer="R2", role="performance", title="风格问题"),
        ])
        mgr = ParallelReviewManager([r1, r2])
        chunk = DiffChunk(
            file_path="test.py",
            old_start=1, old_count=5,
            new_start=1, new_count=7,
            additions=["+new code"],
            deletions=["-old code"],
            context="",
        )
        ctx = PRContext(title="Test PR")
        result = await mgr.run_all([chunk], ctx)

        check("返回 ParallelReviewResult", isinstance(result, ParallelReviewResult))
        check("总发现数 3", len(result.findings) == 3)
        check("total_reviewers 为 2", result.total_reviewers == 2)
        check("全部成功", result.successful_reviewers == 2)
        check("无失败", result.failed_reviewers == [])
        check("每个 reviewer 被调用 1 次", r1.call_count == 1 and r2.call_count == 1)

        # 验证分组
        by_reviewer = mgr.get_findings_by_reviewer()
        check("get_findings_by_reviewer 有 2 个 key", len(by_reviewer) == 2)
        check("R1 发现 1 条", len(by_reviewer.get("R1", [])) == 1)
        check("R2 发现 2 条", len(by_reviewer.get("R2", [])) == 2)

        by_role = mgr.get_findings_by_role()
        check("get_findings_by_role 含 security", "security" in by_role)
        check("get_findings_by_role 含 performance", "performance" in by_role)

        by_sev = mgr.get_findings_by_severity()
        check("get_findings_by_severity 含 critical", "critical" in by_sev)
        check("get_findings_by_severity 含 important", "important" in by_sev)
        check("get_findings_by_severity 含 minor", "minor" in by_sev)

        stats = mgr.get_statistics()
        check("get_statistics status completed", stats["status"] == "completed")
        check("get_statistics total_findings 3", stats["total_findings"] == 3)
        check("by_severity critical=1", stats["by_severity"].get("critical") == 1)
        check("by_severity important=1", stats["by_severity"].get("important") == 1)
        check("by_role security=1", stats["by_role"].get("security") == 1)

        # result 属性可访问
        check("result 属性绑定额外的结果", mgr.result is result)

    asyncio.run(test_basic_parallel())

    # ---------------------------------------------------------------
    print("\n--- 4. run_all 空 diff ---")
    # ---------------------------------------------------------------

    async def test_empty_diff():
        r1 = MockReviewer("R1", [_make_finding(title="A")])
        mgr = ParallelReviewManager([r1])
        ctx = PRContext(title="Test")
        result = await mgr.run_all([], ctx)

        check("空 diff 返回 ParallelReviewResult", isinstance(result, ParallelReviewResult))
        check("空 diff 发现数为 0", len(result.findings) == 0)
        check("空 diff r1 未被调用", r1.call_count == 0)

    asyncio.run(test_empty_diff())

    # ---------------------------------------------------------------
    print("\n--- 5. run_all 部分失败 ---")
    # ---------------------------------------------------------------

    async def test_partial_failure():
        r1 = MockReviewer("R1", [
            _make_finding(severity="critical", reviewer="R1", title="安全发现"),
        ])
        r2 = MockReviewer("R2", [], fail=True)
        r3 = MockReviewer("R3", [
            _make_finding(severity="minor", reviewer="R3", title="风格发现"),
        ])

        mgr = ParallelReviewManager([r1, r2, r3])
        chunk = DiffChunk(
            file_path="app.py",
            old_start=1, old_count=1,
            new_start=1, new_count=2,
            additions=["+new"],
            deletions=["-old"],
            context="",
        )
        ctx = PRContext(title="Test")
        result = await mgr.run_all([chunk], ctx)

        check("部分失败返回 ParallelReviewResult", isinstance(result, ParallelReviewResult))
        check("总发现数 2（R2 失败）", len(result.findings) == 2)
        check("successful_reviewers 为 2", result.successful_reviewers == 2)
        check("failed_reviewers 含 R2", "R2" in result.failed_reviewers)
        check("R1 被调用", r1.call_count == 1)
        check("R3 被调用", r3.call_count == 1)

        stats = mgr.get_statistics()
        check("stats total_reviewers 3", stats["total_reviewers"] == 3)
        check("stats failed_reviewers 含 R2", "R2" in stats["failed_reviewers"])

    asyncio.run(test_partial_failure())

    # ---------------------------------------------------------------
    print("\n--- 6. run_all 超时 ---")
    # ---------------------------------------------------------------

    async def test_timeout():
        r1 = MockReviewer("R1", [_make_finding(title="快速发现")])
        r2 = SlowReviewer("R2", delay=0.3)
        mgr = ParallelReviewManager([r1, r2], timeout=0.1)
        chunk = DiffChunk(
            file_path="x.py",
            old_start=1, old_count=1,
            new_start=1, new_count=1,
            additions=["+x"],
            deletions=["-y"],
            context="",
        )
        ctx = PRContext(title="Test")
        result = await mgr.run_all([chunk], ctx)

        check("超时返回 ParallelReviewResult", isinstance(result, ParallelReviewResult))
        check("R1 发现 1 条", len(result.reviewer_results.get("R1", [])) == 1)
        check("R2 超时发现 0 条", len(result.reviewer_results.get("R2", [])) == 0)

    asyncio.run(test_timeout())

    # ---------------------------------------------------------------
    print("\n--- 7. 分组方法 - 未执行状态 ---")
    # ---------------------------------------------------------------

    mgr_idle = ParallelReviewManager([MockReviewer("RX", [])])
    check("未执行 get_findings_by_reviewer 返回空", mgr_idle.get_findings_by_reviewer() == {})
    check("未执行 get_findings_by_role 返回空", mgr_idle.get_findings_by_role() == {})
    check("未执行 get_findings_by_severity 返回空", mgr_idle.get_findings_by_severity() == {})
    stats_idle = mgr_idle.get_statistics()
    check("未执行 get_statistics status=not_executed", stats_idle["status"] == "not_executed")

    # ---------------------------------------------------------------
    print("\n--- 8. pipeline 包导出 ---")
    # ---------------------------------------------------------------

    check("from pipeline import ParallelReviewManager", True)
    check("from pipeline import ParallelReviewResult", True)

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
