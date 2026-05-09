"""F-13: HTML 报告生成验证脚本"""

import sys
sys.path.insert(0, r"d:\project\code-review")

from typing import List

from tools.report_writer import generate_report
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
    title: str = "测试",
    file_path: str = "src/a.py",
    severity: str = "minor",
) -> Finding:
    return Finding(
        severity=severity,
        reviewer="R1",
        role="security",
        title=title,
        file_path=file_path,
        line_range=(10, 20),
        description=f"desc {title}",
        suggestion="修复建议",
        confidence=0.85,
        evidence=["line 15: code"],
    )


def _generate(verdict=None, ctx=None, diff="", fmt="html") -> str:
    return generate_report(
        verdict or Verdict(),
        ctx or PRContext(title="HTML Test"),
        diff,
        fmt,
    )


def run_tests() -> None:
    print("=" * 60)
    print("F-13: HTML 报告生成验证")
    print("=" * 60)

    # ---------------------------------------------------------------
    print("\n--- 1. HTML 文档结构 ---")
    # ---------------------------------------------------------------

    html = _generate()
    check("<!DOCTYPE html>", "<!DOCTYPE html>" in html)
    check("<html>", "<html" in html)
    check("</html>", "</html>" in html)
    check("<head>", "<head>" in html)
    check("<body>", "<body>" in html)
    check("</body>", "</body>" in html)
    check("charset UTF-8", "charset" in html and "UTF-8" in html)

    # ---------------------------------------------------------------
    print("\n--- 2. CSS 样式 ---")
    # ---------------------------------------------------------------

    html = _generate()
    check("style 标签", "<style>" in html)
    check("font-family", "font-family" in html)
    check("border-collapse", "border-collapse" in html)
    check("critical 颜色类", ".critical{color:" in html.replace(" ", ""))
    check("important 颜色类", ".important{color:" in html.replace(" ", ""))

    # ---------------------------------------------------------------
    print("\n--- 3. 内容完整性 ---")
    # ---------------------------------------------------------------

    ctx = PRContext(title="安全修复", author="alice", base_branch="main", head_branch="feat")
    v = Verdict(
        findings=[_finding("SQL注入", "db.py", "critical")],
        dismissed=["f_d1"],
        merged=[MergeRecord("f_p1", ["f_m1"], "相似")],
        summary="评审完成",
    )
    html = generate_report(v, ctx, "变更 3 个文件", "html")
    check("含标题", "安全修复" in html)
    check("含作者", "alice" in html)
    check("含文件路径", "db" in html and "py" in html)
    check("含 dismissed", "f_d1" in html)
    check("含变更摘要", "变更 3 个文件" in html)
    check("含 summary", "评审完成" in html)

    # ---------------------------------------------------------------
    print("\n--- 4. 跨 severity 渲染 ---")
    # ---------------------------------------------------------------

    v = Verdict(findings=[
        _finding("A", "a.py", "critical"),
        _finding("B", "b.py", "important"),
        _finding("C", "c.py", "minor"),
    ])
    html = _generate(v)
    check("3 个 severity 都渲染", html.count("Critical") + html.count("Important") + html.count("Minor") >= 3)

    # ---------------------------------------------------------------
    print("\n--- 5. 空数据无害渲染 ---")
    # ---------------------------------------------------------------

    html = _generate()
    check("空数据不抛异常", True)
    check("含报告标题", "PR Review Report" in html)

    # ---------------------------------------------------------------
    print("\n--- 6. HTML 文本转义 ---")
    # ---------------------------------------------------------------

    f = _finding(title="<script>alert('xss')</script>")
    v = Verdict(findings=[f])
    html = _generate(v)
    check("script 标签被转义", "&lt;script&gt;" in html)
    check("单引号被转义", "&#x27;" in html or "&apos;" in html or "alert" not in html)

    # ---------------------------------------------------------------
    print("\n--- 7. 包导出 ---")
    # ---------------------------------------------------------------

    from tools.report_writer import generate_report as GR
    check("from tools.report_writer import generate_report", True)

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