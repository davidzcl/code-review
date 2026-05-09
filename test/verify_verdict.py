"""F-11: 最终裁决机制验证脚本"""

import sys
sys.path.insert(0, r"d:\project\code-review")

from typing import List

from pipeline.verdict import Verdict, make_final_verdict
from pipeline.debate_loop import DebateRecord, DebateRound
from pipeline.issue_merger import MergeRecord
from agents.reviewer import Finding

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


def _finding(
    title: str = "发现",
    file_path: str = "src/a.py",
    severity: str = "minor",
    role: str = "security",
) -> Finding:
    return Finding(
        severity=severity,
        reviewer="R1",
        role=role,
        title=title,
        file_path=file_path,
        line_range=(10, 20),
        description=f"desc {title}",
        suggestion="fix it",
        confidence=0.85,
        evidence=["line 15: code"],
    )


def _record(
    finding: Finding,
    status: str = "confirmed",
    round_count: int = 1,
) -> DebateRecord:
    rounds = [
        DebateRound(round_number=i + 1)
        for i in range(round_count)
    ]
    return DebateRecord(
        finding_id=finding.id,
        original_finding=finding,
        rounds=rounds,
        final_status=status,
    )


def run_tests() -> None:
    print("=" * 60)
    print("F-11: 最终裁决机制验证")
    print("=" * 60)

    # ---------------------------------------------------------------
    print("\n--- 1. Verdict 数据类 ---")
    # ---------------------------------------------------------------

    v = Verdict()
    check("默认创建", isinstance(v, Verdict))
    check("findings 默认空", v.findings == [])
    check("dismissed 默认空", v.dismissed == [])
    check("merged 默认空", v.merged == [])
    check("summary 默认空", v.summary == "")

    f = _finding()
    mr = MergeRecord(primary_id="p1", merged_ids=["m1"], merge_reason="相似")
    v2 = Verdict(
        findings=[f],
        dismissed=["d1"],
        merged=[mr],
        summary="test",
    )
    check("带数据创建", v2.findings == [f])
    check("dismissed 含 d1", v2.dismissed == ["d1"])
    check("merged 含 1 条", len(v2.merged) == 1)
    check("summary", v2.summary == "test")

    # ---------------------------------------------------------------
    print("\n--- 2. make_final_verdict - 空输入 ---")
    # ---------------------------------------------------------------

    v = make_final_verdict([], [])
    check("空输入 findings 为空", v.findings == [])
    check("空输入 dismissed 为空", v.dismissed == [])
    check("空输入 merged 为空", v.merged == [])
    check("空输入 summary 非空", v.summary != "")

    # ---------------------------------------------------------------
    print("\n--- 3. make_final_verdict - 全 confirmed ---")
    # ---------------------------------------------------------------

    f1 = _finding(title="A", file_path="a.py")
    f2 = _finding(title="B", file_path="b.py")
    records = [_record(f1), _record(f2)]
    v = make_final_verdict(records, [])
    check("2 个 confirmed", len(v.findings) == 2)
    check("无 dismissed", v.dismissed == [])
    check("summary 含 2", "2 个确认" in v.summary or "2 个" in v.summary)

    # ---------------------------------------------------------------
    print("\n--- 4. make_final_verdict - 混合 confirmed/dismissed ---")
    # ---------------------------------------------------------------

    f_c = _finding(title="C", file_path="c.py")
    f_d = _finding(title="D", file_path="d.py")
    records = [_record(f_c), _record(f_d, "dismissed")]
    v = make_final_verdict(records, [])
    check("1 个 confirmed", len(v.findings) == 1)
    check("dismissed 含 D", len(v.dismissed) == 1)
    check("summary 含 驳回", "驳回" in v.summary)

    # ---------------------------------------------------------------
    print("\n--- 5. make_final_verdict - 合并去重 ---")
    # ---------------------------------------------------------------

    f_x = _finding(title="注入", file_path="db.py", severity="critical")
    f_y = _finding(title="注入", file_path="db.py", severity="critical")
    records = [_record(f_x), _record(f_y)]
    merge_records = [
        MergeRecord(
            primary_id=f_x.id,
            merged_ids=[f_y.id],
            merge_reason="相似",
            merged_finding=f_x,
        ),
    ]
    v = make_final_verdict(records, merge_records)
    check("去重后 1 个 finding", len(v.findings) == 1)
    check("保留 primary", v.findings[0].id == f_x.id)
    check("merged 记录保留", len(v.merged) == 1)

    # ---------------------------------------------------------------
    print("\n--- 6. make_final_verdict - 多级严重程度统计 ---")
    # ---------------------------------------------------------------

    f_a = _finding(title="A", severity="critical")
    f_b = _finding(title="B", severity="important")
    f_c = _finding(title="C", severity="minor")
    records = [_record(f_a), _record(f_b), _record(f_c)]
    v = make_final_verdict(records, [])
    check("3 个 finding", len(v.findings) == 3)
    check("summary 含 critical", "critical" in v.summary)
    check("summary 含 important", "important" in v.summary)
    check("summary 含 minor", "minor" in v.summary)

    # ---------------------------------------------------------------
    print("\n--- 7. make_final_verdict - 全 dismissed ---")
    # ---------------------------------------------------------------

    f_z = _finding(title="Z")
    records = [_record(f_z, "dismissed")]
    v = make_final_verdict(records, [])
    check("findings 为空", v.findings == [])
    check("dismissed 含 Z", f_z.id in v.dismissed)

    # ---------------------------------------------------------------
    print("\n--- 8. 包导出 ---")
    # ---------------------------------------------------------------

    from pipeline.verdict import Verdict as V, make_final_verdict as MFV
    check("from pipeline.verdict import Verdict", True)
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
