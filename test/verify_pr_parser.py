"""F-04: PR 描述解析器验证脚本"""

import sys
sys.path.insert(0, r"d:\project\code-review")

import os

from tools.pr_parser import (
    PRContext,
    PRParseError,
    parse_pr_description,
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name: str) -> str:
    path = os.path.join(FIXTURES_DIR, name)
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_empty_pr():
    try:
        parse_pr_description("")
        assert False, "空文本应抛出 PRParseError"
    except PRParseError:
        print("  1.1 空文本异常 [PASS]")


def test_whitespace_pr():
    try:
        parse_pr_description("   \n\n  ")
        assert False, "空白文本应抛出 PRParseError"
    except PRParseError:
        print("  1.2 空白文本异常 [PASS]")


def test_full_sample():
    text = load_fixture("sample_pr.md")
    ctx = parse_pr_description(text)

    assert ctx.title == "用户认证模块重构：加盐哈希与数据模型分离", f"title={ctx.title}"
    print("  2.1 标题解析 [PASS]")

    assert ctx.author == "dev_user", f"author={ctx.author}"
    print("  2.2 作者解析 [PASS]")

    assert ctx.head_branch == "feature/auth-refactor", f"head={ctx.head_branch}"
    assert ctx.base_branch == "main", f"base={ctx.base_branch}"
    print("  2.3 分支解析 [PASS]")

    expected_labels = ["enhancement", "security", "breaking-change"]
    assert ctx.labels == expected_labels, f"labels={ctx.labels}"
    print("  2.4 标签解析 [PASS]")

    assert "加盐哈希" in ctx.description, "描述应包含加盐哈希"
    assert "src/models/user.py" in ctx.description, "描述应包含文件路径"
    print("  2.5 描述解析 [PASS]")

    assert "密码安全等级提升" in ctx.changed_files_summary, f"summary={ctx.changed_files_summary}"
    print("  2.6 变更概要解析 [PASS]")

    print(f"  2.7 完整解析 [PASS] (labels={ctx.labels}, desc_len={len(ctx.description)})")


def test_partial_pr():
    text = """**标题**: 简单修复

**作者**: dev
"""
    ctx = parse_pr_description(text)
    assert ctx.title == "简单修复"
    assert ctx.author == "dev"
    assert ctx.labels == []
    assert ctx.description == ""
    assert ctx.base_branch == ""
    assert ctx.head_branch == ""
    print("  3.1 部分字段 PR [PASS]")


def test_branch_variants():
    text = """**标题**: 分支测试
**描述**: 测试不同分支格式
**作者**: test
**分支**: develop -> main
"""
    ctx = parse_pr_description(text)
    assert ctx.head_branch == "develop"
    assert ctx.base_branch == "main"
    print("  4.1 分支格式 -> [PASS]")

    text2 = """**标题**: 箭头格式
**描述**: 测试箭头
**作者**: test
**分支**: feature/foo → release/v2
"""
    ctx2 = parse_pr_description(text2)
    assert ctx2.head_branch == "feature/foo"
    assert ctx2.base_branch == "release/v2"
    print("  4.2 分支格式 → [PASS]")


def test_labels_with_dash():
    text = """**标题**: 标签格式
**描述**: 测试标签中的横线前缀
**作者**: test
**标签**: - bug, - ui, - performance
"""
    ctx = parse_pr_description(text)
    assert "bug" in ctx.labels, f"labels={ctx.labels}"
    assert "ui" in ctx.labels
    assert "performance" in ctx.labels
    print("  5.1 标签横线前缀处理 [PASS]")


def test_missing_required_fields():
    text = """**标题**: 无作者"""
    ctx = parse_pr_description(text)
    assert ctx.title == "无作者"
    assert ctx.author == ""
    print("  6.1 缺失字段不抛异常 [PASS]")


def test_long_description():
    lines = ["**标题**: 长描述测试"]
    lines.append("**描述**: 起始行")
    for i in range(20):
        lines.append(f"这是第 {i+1} 行描述内容")
    lines.append("**作者**: dev")
    text = "\n".join(lines)

    ctx = parse_pr_description(text)
    assert len(ctx.description.splitlines()) == 21
    assert "起始行" in ctx.description
    print("  7.1 多行描述解析 [PASS]")


if __name__ == "__main__":
    test_empty_pr()
    test_whitespace_pr()
    test_full_sample()
    test_partial_pr()
    test_branch_variants()
    test_labels_with_dash()
    test_missing_required_fields()
    test_long_description()
    print("\n全部验证通过! [PASS]")
    sys.exit(0)
