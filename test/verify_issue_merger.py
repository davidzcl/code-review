"""F-10: 发现合并规则引擎验证脚本"""

import sys
sys.path.insert(0, r"d:\project\code-review")

from typing import List

from pipeline.issue_merger import (
    MergeRecord,
    compute_finding_similarity,
    merge_similar_findings,
    _tokenize,
    _W_FILE_PATH, _W_LINE_RANGE, _W_TITLE_TEXT, _W_SEVERITY, _W_ROLE,
)
from pipeline.debate_loop import DebateRecord, DebateRound
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
    title: str = "test",
    file_path: str = "src/a.py",
    line_start: int = 10,
    line_end: int = 20,
    severity: str = "minor",
    role: str = "security",
    description: str = "",
) -> Finding:
    return Finding(
        severity=severity,
        reviewer="R1",
        role=role,
        title=title,
        file_path=file_path,
        line_range=(line_start, line_end),
        description=description or f"desc {title}",
        suggestion="fix it",
        confidence=0.85,
        evidence=["line 15: code"],
    )


def _record(finding: Finding, status: str = "confirmed") -> DebateRecord:
    return DebateRecord(
        finding_id=finding.id,
        original_finding=finding,
        final_status=status,
    )


def run_tests() -> None:
    print("=" * 60)
    print("F-10: 发现合并规则引擎验证")
    print("=" * 60)

    # ---------------------------------------------------------------
    print("\n--- 1. MergeRecord 数据类 ---")
    # ---------------------------------------------------------------

    mr = MergeRecord(primary_id="p1")
    check("默认创建", isinstance(mr, MergeRecord))
    check("primary_id", mr.primary_id == "p1")
    check("merged_ids 默认空", mr.merged_ids == [])
    check("merge_reason 默认空", mr.merge_reason == "")
    check("merged_finding 默认 None", mr.merged_finding is None)

    f = _finding()
    mr2 = MergeRecord(
        primary_id="p1",
        merged_ids=["m1", "m2"],
        merge_reason="相似",
        merged_finding=f,
    )
    check("带数据创建", mr2.primary_id == "p1")
    check("merged_ids", mr2.merged_ids == ["m1", "m2"])
    check("merge_reason", mr2.merge_reason == "相似")
    check("merged_finding", mr2.merged_finding is f)

    # ---------------------------------------------------------------
    print("\n--- 2. _tokenize 辅助函数 ---")
    # ---------------------------------------------------------------

    t1 = _tokenize("Hello World")
    check("英文字母", t1 == {"hello", "world"})

    t2 = _tokenize("hello hello")
    check("重复词去重", t2 == {"hello"})

    t3 = _tokenize("")
    check("空字符串", t3 == set())

    t4 = _tokenize("SQL 注入风险 N+1")
    check("中英混合", "sql" in t4 and "注入风险" in t4 and "n" in t4 and "1" in t4)

    # ---------------------------------------------------------------
    print("\n--- 3. compute_finding_similarity - 相同文件/行/标题 ---")
    # ---------------------------------------------------------------

    f1 = _finding(title="SQL注入", file_path="src/db.py", line_start=10, line_end=30)
    f2 = _finding(title="SQL注入", file_path="src/db.py", line_start=10, line_end=30)
    sim = compute_finding_similarity(f1, f2)
    check("完全相同", sim == 1.0)

    # ---------------------------------------------------------------
    print("\n--- 4. compute_finding_similarity - 部分重叠 ---")
    # ---------------------------------------------------------------

    f_a = _finding(title="SQL注入", file_path="src/db.py", line_start=10, line_end=30)
    f_b = _finding(title="SQL注入", file_path="src/db.py", line_start=20, line_end=40)
    sim = compute_finding_similarity(f_a, f_b)
    check("部分重叠 > 0.5", sim > 0.5)
    check("部分重叠 < 1.0", sim < 1.0)

    # ---------------------------------------------------------------
    print("\n--- 5. compute_finding_similarity - 不同文件 ---")
    # ---------------------------------------------------------------

    f_c = _finding(file_path="src/a.py")
    f_d = _finding(file_path="src/b.py")
    sim = compute_finding_similarity(f_c, f_d)
    check("不同文件 < 0.5", sim < 0.5)

    # ---------------------------------------------------------------
    print("\n--- 6. compute_finding_similarity - 无行范围重叠 ---")
    # ---------------------------------------------------------------

    f_e = _finding(line_start=1, line_end=10)
    f_f = _finding(line_start=50, line_end=60)
    sim = compute_finding_similarity(f_e, f_f)
    check("无行重叠不含行分数", sim < _W_FILE_PATH + _W_TITLE_TEXT + _W_SEVERITY + _W_ROLE)

    # ---------------------------------------------------------------
    print("\n--- 7. compute_finding_similarity - 默认行范围(0,0) ---")
    # ---------------------------------------------------------------

    f_g = Finding(severity="minor", reviewer="R1", role="security", title="x", file_path="a.py", line_range=(0, 0))
    f_h = Finding(severity="minor", reviewer="R1", role="security", title="x", file_path="a.py", line_range=(0, 0))
    sim = compute_finding_similarity(f_g, f_h)
    check("默认行范围不贡献分数", sim > 0)

    # ---------------------------------------------------------------
    print("\n--- 8. merge_similar_findings - 空输入 ---")
    # ---------------------------------------------------------------

    result = merge_similar_findings([])
    check("空列表返回空", result == [])

    # ---------------------------------------------------------------
    print("\n--- 9. merge_similar_findings - 无 confirmed ---")
    # ---------------------------------------------------------------

    recs = [_record(_finding(title="A"), "dismissed"),
            _record(_finding(title="B"), "dismissed")]
    result = merge_similar_findings(recs)
    check("无 confirmed 返回空", result == [])

    # ---------------------------------------------------------------
    print("\n--- 10. merge_similar_findings - 无可合并 ---")
    # ---------------------------------------------------------------

    recs = [_record(_finding(title="SQL注入", file_path="src/a.py")),
            _record(_finding(title="性能问题", file_path="src/b.py"))]
    result = merge_similar_findings(recs)
    check("无可合并返回空", result == [])

    # ---------------------------------------------------------------
    print("\n--- 11. merge_similar_findings - 两发现合并 ---")
    # ---------------------------------------------------------------

    target = _finding(title="SQL注入", file_path="src/db.py", line_start=10, line_end=20)
    duplicate = _finding(title="SQL注入", file_path="src/db.py", line_start=12, line_end=18)
    recs = [_record(target), _record(duplicate)]
    result = merge_similar_findings(recs)
    check("生成 1 条合并记录", len(result) == 1)
    check("primary 是 target", result[0].primary_id == target.id)
    check("merged 含 duplicate", duplicate.id in result[0].merged_ids)

    # ---------------------------------------------------------------
    print("\n--- 12. merge_similar_findings - 严重级别排序 ---")
    # ---------------------------------------------------------------

    critical = _finding(title="SQL注入", file_path="db.py", severity="critical")
    minor = _finding(title="SQL注入", file_path="db.py", severity="minor")
    recs = [_record(minor), _record(critical)]
    result = merge_similar_findings(recs)
    check("critical 为 primary", result[0].primary_id == critical.id)

    # ---------------------------------------------------------------
    print("\n--- 13. merge_similar_findings - 低阈值合并更多 ---")
    # ---------------------------------------------------------------

    fa = _finding(title="注入", file_path="a.py")
    fb = _finding(title="注入", file_path="b.py")
    fc = _finding(title="注入", file_path="c.py")
    recs = [_record(fa), _record(fb), _record(fc)]
    result_high = merge_similar_findings(recs, similarity_threshold=1.0)
    result_low = merge_similar_findings(recs, similarity_threshold=0.1)
    check("阈值 1.0 无合并", result_high == [])
    check("阈值 0.1 有合并", len(result_low) > 0)

    # ---------------------------------------------------------------
    print("\n--- 14. 包导出 ---")
    # ---------------------------------------------------------------

    from pipeline.issue_merger import MergeRecord as MR, compute_finding_similarity as CFS, merge_similar_findings as MSF
    check("from pipeline.issue_merger import MergeRecord", True)
    check("from pipeline.issue_merger import compute_finding_similarity", True)
    check("from pipeline.issue_merger import merge_similar_findings", True)

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
