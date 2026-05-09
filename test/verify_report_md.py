"""F-12: Markdown 报告生成验证脚本"""

import os
import sys
import tempfile
sys.path.insert(0, r"d:\project\code-review")

from typing import List

from tools.report_writer import (
    generate_report,
    write_report,
    _escape_md,
    _severity_label,
)
from pipeline.verdict import Verdict
from pipeline.issue_merger import MergeRecord
from agents.reviewer import Finding
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


def _finding(
    title: str = "测试问题",
    file_path: str = "src/a.py",
    line_start: int = 10,
    line_end: int = 20,
    severity: str = "minor",
    role: str = "security",
    suggestion: str = "修复建议",
) -> Finding:
    return Finding(
        id=f"f_{title}_{severity}",
        severity=severity,
        reviewer="R1",
        role=role,
        title=title,
        file_path=file_path,
        line_range=(line_start, line_end),
        description=f"desc {title}",
        suggestion=suggestion,
        confidence=0.85,
        evidence=["line 15: code"],
    )


def run_tests() -> None:
    print("=" * 60)
    print("F-12: Markdown 报告生成验证")
    print("=" * 60)

    # ---------------------------------------------------------------
    print("\n--- 1. 辅助函数 ---")
    # ---------------------------------------------------------------

    check("_escape_md 转义 *", _escape_md("a*b") == r"a\*b")
    check("_escape_md 转义 [", _escape_md("[link]") == r"\[link\]")
    check("_escape_md 普通文本不变", _escape_md("hello") == "hello")
    check("_severity_label critical", "Critical" in _severity_label("critical"))
    check("_severity_label unknown", _severity_label("unknown") == "unknown")

    # ---------------------------------------------------------------
    print("\n--- 2. generate_report - 空数据 ---")
    # ---------------------------------------------------------------

    verdict = Verdict()
    ctx = PRContext(title="Test PR")
    md = generate_report(verdict, ctx, "")
    check("空数据返回字符串", isinstance(md, str))
    check("含标题", "Test PR" in md)
    check("含概览标题", "评审概览" in md)
    check("含变更摘要标题", "变更摘要" in md)
    check("含发现详情标题", "发现详情" in md)
    check("未发现代码问题", "未发现代码问题" in md)
    check("含页脚", "自动生成" in md)

    # ---------------------------------------------------------------
    print("\n--- 3. generate_report - 基本 Markdown 报告 ---")
    # ---------------------------------------------------------------

    findings = [
        _finding(title="SQL注入", severity="critical", file_path="src/db.py", line_start=15, line_end=25),
        _finding(title="N+1查询", severity="important", file_path="src/orm.py", line_start=30, line_end=35),
        _finding(title="命名不规范", severity="minor", file_path="src/utils.py", line_start=1, line_end=5),
    ]
    verdict = Verdict(findings=findings)
    ctx = PRContext(title="Security Fix", author="alice", base_branch="main", head_branch="feat")
    md = generate_report(verdict, ctx, "变更了 3 个文件")
    check("含 PR 标题", "Security Fix" in md)
    check("含作者", "alice" in md)
    check("含分支", "feat" in md)
    check("含变更摘要内容", "变更了 3 个文件" in md)
    check("含 Critical 表格", "🔴 Critical" in md)
    check("含 Important 表格", "🟡 Important" in md)
    check("含 Minor 表格", "🟢 Minor" in md)
    check("含发现数量", "3" in md)
    check("含文件路径", "db" in md and "src" in md)
    check("含行范围", "15-25" in md)
    check("含建议", "修复建议" in md)

    # ---------------------------------------------------------------
    print("\n--- 4. generate_report - 含 dismissed/merged ---")
    # ---------------------------------------------------------------

    verdict = Verdict(
        findings=[_finding(title="有效问题", severity="critical")],
        dismissed=["f_d1", "f_d2"],
        merged=[MergeRecord(primary_id="f_p1", merged_ids=["f_m1"], merge_reason="相似")],
        summary="评审完成",
    )
    ctx = PRContext(title="Dismiss Test")
    md = generate_report(verdict, ctx, "")
    check("含已驳回标题", "已驳回" in md)
    check("含 dismissed ID", "f_d1" in md)
    check("含合并数", "1" in md)
    check("含总结", "评审完成" in md)

    # ---------------------------------------------------------------
    print("\n--- 5. generate_report - HTML 格式 ---")
    # ---------------------------------------------------------------

    verdict = Verdict(findings=[_finding(title="XSS")])
    html = generate_report(verdict, PRContext(title="HTML Test"), "", "html")
    check("HTML 格式返回字符串", isinstance(html, str))
    check("含 DOCTYPE", "<!DOCTYPE html>" in html)
    check("含 html 标签", "<html" in html)
    check("含 style 标签", "<style>" in html)
    check("含 body", "<body>" in html)
    check("含 XSS 内容", "XSS" in html)

    # ---------------------------------------------------------------
    print("\n--- 6. generate_report - JSON 格式 ---")
    # ---------------------------------------------------------------

    import json
    verdict = Verdict(
        findings=[_finding(title="JSON测试", severity="critical")],
        summary="json summary",
    )
    js = generate_report(verdict, PRContext(title="JSON Test"), "", "json")
    check("JSON 格式返回字符串", isinstance(js, str))
    parsed = json.loads(js)
    check("JSON 可解析", isinstance(parsed, dict))
    check("含 report 字段", "report" in parsed)
    check("含 verdict 字段", "verdict" in parsed)
    check("含 findings", len(parsed["verdict"]["findings"]) == 1)

    # ---------------------------------------------------------------
    print("\n--- 7. generate_report - 无效格式 ---")
    # ---------------------------------------------------------------

    try:
        generate_report(Verdict(), PRContext(), "", "pdf")
        check("无效格式应抛出异常", False, "未抛出 ValueError")
    except ValueError:
        check("无效格式抛出 ValueError", True)

    # ---------------------------------------------------------------
    print("\n--- 8. write_report - 文件写入 ---")
    # ---------------------------------------------------------------

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as tmp:
        tmp_path = tmp.name

    try:
        write_report("# Test Report", tmp_path)
        check("write_report 不抛出异常", True)
        with open(tmp_path, "r", encoding="utf-8") as f:
            content = f.read()
        check("写入内容正确", content == "# Test Report")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # ---------------------------------------------------------------
    print("\n--- 9. 包导出 ---")
    # ---------------------------------------------------------------

    from tools.report_writer import (
        generate_report as GR,
        write_report as WR,
    )
    check("from tools.report_writer import generate_report", True)
    check("from tools.report_writer import write_report", True)

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