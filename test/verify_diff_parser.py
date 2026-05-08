"""F-03: Git Diff 解析器验证脚本"""

import sys
sys.path.insert(0, r"d:\project\code-review")

import os

from tools.diff_parser import (
    AddedLine,
    DiffChunk,
    DiffParseError,
    parse_diff,
    get_changed_files,
    get_added_lines,
    split_by_file,
    _infer_language,
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name: str) -> str:
    path = os.path.join(FIXTURES_DIR, name)
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_empty_diff():
    result = parse_diff("")
    assert result == [], "空 diff 应返回空列表"
    print("  1.1 空 diff 处理 [PASS]")


def test_whitespace_diff():
    result = parse_diff("   \n\n  ")
    assert result == [], "空白 diff 应返回空列表"
    print("  1.2 空白 diff 处理 [PASS]")


def test_simple_diff():
    text = load_fixture("sample_simple.diff")
    chunks = parse_diff(text)

    assert len(chunks) == 2, f"期望 2 个 chunks（2 个 hunks），实际 {len(chunks)}"

    c0 = chunks[0]
    assert c0.file_path == "src/utils/calculator.py"
    assert c0.old_start == 10
    assert c0.old_count == 7
    assert c0.new_start == 10
    assert c0.new_count == 7
    assert c0.language == "python"
    assert not c0.is_new_file
    assert not c0.is_deleted_file
    assert len(c0.deletions) == 1, f"chunk[0] deletions: {c0.deletions}"
    assert "a: 被除数" in c0.deletions[0]
    assert len(c0.additions) == 1, f"chunk[0] additions: {c0.additions}"
    assert "a: 被除数（支持负数）" in c0.additions[0]

    c1 = chunks[1]
    assert c1.file_path == "src/utils/calculator.py"
    assert c1.old_start == 18
    assert c1.old_count == 6
    assert c1.new_start == 18
    assert c1.new_count == 7
    assert len(c1.additions) == 3, f"chunk[1] additions({len(c1.additions)}): {c1.additions}"
    assert "TypeError: 参数非整数" in c1.additions[0]
    assert "isinstance" in c1.additions[1]
    assert "raise TypeError" in c1.additions[2]

    print(f"  2.1 单文件 2-hunk diff 解析 [PASS] (file={c0.file_path}, lang={c0.language})")


def test_multi_file_diff():
    text = load_fixture("sample_multi_file.diff")
    chunks = parse_diff(text)

    assert len(chunks) == 3, f"期望 3 个 chunks，实际 {len(chunks)}"

    file_paths = [c.file_path for c in chunks]
    expected = [
        "src/models/user.py",
        "src/services/auth.py",
        "src/legacy/deprecated.py",
    ]
    assert file_paths == expected, f"文件路径不匹配: {file_paths}"

    assert chunks[0].is_new_file, "user.py 应标记为新文件"
    assert chunks[0].additions, "新文件应有新增行"
    assert not chunks[0].deletions

    assert not chunks[1].is_new_file, "auth.py 不应标记为新文件"
    assert not chunks[1].is_deleted_file
    assert len(chunks[1].additions) > 0, "auth.py 应有新增行"
    assert len(chunks[1].deletions) > 0, "auth.py 应有删除行"

    assert chunks[2].is_deleted_file, "deprecated.py 应标记为删除"
    assert not chunks[2].additions
    assert chunks[2].deletions, "删除文件应有删除行"

    print(f"  3.1 多文件 diff 解析 [PASS] ({len(chunks)} 文件)")


def test_get_changed_files():
    text = load_fixture("sample_multi_file.diff")
    files = get_changed_files(text)
    expected = [
        "src/models/user.py",
        "src/services/auth.py",
        "src/legacy/deprecated.py",
    ]
    assert files == expected, f"变更文件列表不匹配: {files}"
    print("  4.1 get_changed_files [PASS]")


def test_split_by_file():
    text = load_fixture("sample_multi_file.diff")
    sections = split_by_file(text)
    assert len(sections) == 3, f"期望 3 个 sections，实际 {len(sections)}"
    for path in [
        "src/models/user.py",
        "src/services/auth.py",
        "src/legacy/deprecated.py",
    ]:
        assert path in sections, f"缺少 {path}"
        assert sections[path].startswith("diff --git"), f"{path} 片段格式异常"
    print("  5.1 split_by_file [PASS]")


def test_infer_language():
    cases = [
        ("src/main.py", "python"),
        ("app.js", "javascript"),
        ("app.tsx", "typescriptreact"),
        ("Dockerfile", "dockerfile"),
        ("Makefile", "makefile"),
        ("unknown.xyz", ""),
    ]
    for path, expected in cases:
        result = _infer_language(path)
        assert result == expected, f"{path}: 期望 {expected}，实际 {result}"
    print("  6.1 语言推断 [PASS]")


def test_context_extraction():
    text = load_fixture("sample_simple.diff")
    chunks = parse_diff(text)
    assert chunks[0].context, "chunk[0] 应有上下文内容"
    assert chunks[1].context, "chunk[1] 应有上下文内容"
    print("  7.1 上下文提取 [PASS]")


def test_get_added_lines():
    text = load_fixture("sample_simple.diff")
    lines = get_added_lines(text)
    assert len(lines) == 4, f"期望 4 条新增行（hunk1:1 + hunk2:3），实际 {len(lines)}"
    assert lines[0].file_path == "src/utils/calculator.py"
    assert lines[0].line == 13
    assert "a: 被除数（支持负数）" in lines[0].content
    assert lines[1].line == 21
    assert "TypeError" in lines[1].content
    assert lines[2].line == 25
    assert "isinstance" in lines[2].content
    assert lines[3].line == 26
    assert "raise TypeError" in lines[3].content
    for al in lines:
        assert isinstance(al, AddedLine)
    print("  8.1 get_added_lines 单文件 [PASS]")

    text_multi = load_fixture("sample_multi_file.diff")
    lines_multi = get_added_lines(text_multi)
    assert len(lines_multi) == 22, f"期望 22 条新增行（user.py 15 + auth.py 7），实际 {len(lines_multi)}"
    file_set = {al.file_path for al in lines_multi}
    assert "src/models/user.py" in file_set
    assert "src/services/auth.py" in file_set
    assert "src/legacy/deprecated.py" not in file_set
    print("  8.2 get_added_lines 多文件 [PASS]")


if __name__ == "__main__":
    test_empty_diff()
    test_whitespace_diff()
    test_simple_diff()
    test_multi_file_diff()
    test_get_changed_files()
    test_split_by_file()
    test_infer_language()
    test_context_extraction()
    test_get_added_lines()
    print("\n全部验证通过! [PASS]")
    sys.exit(0)
