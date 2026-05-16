"""
验证评测系统测试用例 Schema 定义

测试目标：
1. SyntheticTestCase 能正确解析有效数据
2. 必填字段缺失时抛出 ValidationError
3. 枚举值验证（category, severity）
4. 默认值处理
"""

import pytest
from pydantic import ValidationError


class TestSyntheticTestCase:
    """SyntheticTestCase 数据验证测试"""

    def test_create_valid_test_case(self):
        """测试：有效数据能正确创建 SyntheticTestCase"""
        from evaluation.datasets.schemas import (
            SyntheticTestCase,
            InjectedIssue,
            IssueCategory,
            DiffChunkSchema,
        )

        case = SyntheticTestCase(
            id="SEC-001",
            name="SQL 注入漏洞检测",
            category=IssueCategory.SECURITY,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/db/query.py",
                    language="python",
                    old_start=10,
                    old_count=5,
                    new_start=10,
                    new_count=8,
                    additions=["query = f\"SELECT * FROM users WHERE id = {user_id}\""],
                    deletions=[],
                    context="def get_user(user_id):",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="critical",
                    title="SQL 注入漏洞",
                    description="用户输入直接拼接到 SQL 语句",
                    file_path="src/db/query.py",
                    line_range=(11, 12),
                    detection_hints=["SQL injection", "f-string"],
                )
            ],
        )

        assert case.id == "SEC-001"
        assert case.category == IssueCategory.SECURITY
        assert len(case.injected_issues) == 1
        assert case.injected_issues[0].severity == "critical"

    def test_missing_required_field_raises_error(self):
        """测试：必填字段缺失时抛出 ValidationError"""
        from evaluation.datasets.schemas import SyntheticTestCase

        with pytest.raises(ValidationError) as exc_info:
            SyntheticTestCase(
                id="SEC-002",
                name="缺少必填字段",
            )

        errors = exc_info.value.errors()
        error_fields = {e["loc"][0] for e in errors}
        assert "category" in error_fields
        assert "difficulty" in error_fields
        assert "diff_chunks" in error_fields

    def test_invalid_category_raises_error(self):
        """测试：无效的 category 枚举值抛出 ValidationError"""
        from evaluation.datasets.schemas import SyntheticTestCase

        with pytest.raises(ValidationError) as exc_info:
            SyntheticTestCase(
                id="SEC-003",
                name="无效分类",
                category="invalid_category",
                difficulty="medium",
                diff_chunks=[],
            )

        errors = exc_info.value.errors()
        assert any("category" in str(e["loc"]) for e in errors)

    def test_invalid_severity_raises_error(self):
        """测试：无效的 severity 值抛出 ValidationError"""
        from evaluation.datasets.schemas import (
            SyntheticTestCase,
            InjectedIssue,
            IssueCategory,
        )

        with pytest.raises(ValidationError) as exc_info:
            SyntheticTestCase(
                id="SEC-004",
                name="无效严重级别",
                category=IssueCategory.SECURITY,
                difficulty="medium",
                diff_chunks=[],
                injected_issues=[
                    InjectedIssue(
                        category=IssueCategory.SECURITY,
                        severity="invalid_severity",
                        title="测试",
                        description="测试",
                        file_path="test.py",
                        line_range=(1, 2),
                        detection_hints=[],
                    )
                ],
            )

        errors = exc_info.value.errors()
        assert any("severity" in str(e["loc"]) for e in errors)

    def test_default_values(self):
        """测试：可选字段使用默认值"""
        from evaluation.datasets.schemas import (
            SyntheticTestCase,
            IssueCategory,
        )

        case = SyntheticTestCase(
            id="SEC-005",
            name="默认值测试",
            category=IssueCategory.SECURITY,
            difficulty="medium",
            diff_chunks=[],
        )

        assert case.pr_context is None
        assert case.injected_issues == []
        assert case.expected_tools == []
        assert case.expected_findings_count == 0

    def test_injected_issue_line_range_validation(self):
        """测试：line_range 必须是有效的行号范围"""
        from evaluation.datasets.schemas import (
            InjectedIssue,
            IssueCategory,
        )

        issue = InjectedIssue(
            category=IssueCategory.SECURITY,
            severity="high",
            title="测试",
            description="测试",
            file_path="test.py",
            line_range=(10, 20),
            detection_hints=["hint"],
        )

        assert issue.line_range == (10, 20)

    def test_diff_chunk_schema(self):
        """测试：DiffChunkSchema 正确解析 diff 块"""
        from evaluation.datasets.schemas import DiffChunkSchema

        chunk = DiffChunkSchema(
            file_path="src/main.py",
            language="python",
            old_start=1,
            old_count=5,
            new_start=1,
            new_count=8,
            additions=["new line 1", "new line 2"],
            deletions=["old line 1"],
            context="def main():",
        )

        assert chunk.file_path == "src/main.py"
        assert chunk.language == "python"
        assert len(chunk.additions) == 2
        assert len(chunk.deletions) == 1

    def test_all_categories_valid(self):
        """测试：所有 IssueCategory 枚举值都有效"""
        from evaluation.datasets.schemas import (
            SyntheticTestCase,
            IssueCategory,
        )

        for category in IssueCategory:
            case = SyntheticTestCase(
                id=f"TEST-{category.value}",
                name=f"测试 {category.value}",
                category=category,
                difficulty="medium",
                diff_chunks=[],
            )
            assert case.category == category

    def test_all_severities_valid(self):
        """测试：所有 severity 值都有效"""
        from evaluation.datasets.schemas import (
            SyntheticTestCase,
            InjectedIssue,
            IssueCategory,
        )

        valid_severities = ["critical", "high", "medium", "low"]

        for severity in valid_severities:
            case = SyntheticTestCase(
                id=f"TEST-{severity}",
                name=f"测试 {severity}",
                category=IssueCategory.SECURITY,
                difficulty="medium",
                diff_chunks=[],
                injected_issues=[
                    InjectedIssue(
                        category=IssueCategory.SECURITY,
                        severity=severity,
                        title="测试",
                        description="测试",
                        file_path="test.py",
                        line_range=(1, 2),
                        detection_hints=[],
                    )
                ],
            )
            assert case.injected_issues[0].severity == severity


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
