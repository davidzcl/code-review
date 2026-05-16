"""
验证端到端测试用例数据集

测试目标：
1. 测试用例结构正确性
2. 测试用例加载
3. 分类筛选
"""

import pytest

from evaluation.datasets.e2e_cases import (
    E2ETestCase,
    E2ETestCategory,
    ExpectedFinding,
    E2E_TEST_CASES,
    get_e2e_cases_by_category,
    get_e2e_cases_by_difficulty,
    SQL_INJECTION_BASIC,
    XSS_REFLECTED,
    HARDCODED_SECRET,
    N_PLUS_ONE_QUERY,
    INEFFICIENT_ALGORITHM,
    NULL_POINTER_CHECK,
    OFF_BY_ONE,
    CODE_DUPLICATION,
    MIXED_ISSUES,
)


class TestExpectedFinding:
    """测试 ExpectedFinding"""

    def test_init(self):
        """测试：初始化"""
        finding = ExpectedFinding(
            title="Test Finding",
            category="security",
            severity="high",
        )

        assert finding.title == "Test Finding"
        assert finding.category == "security"
        assert finding.severity == "high"
        assert finding.should_be_confirmed is True
        assert finding.confidence_threshold == 0.6

    def test_custom_values(self):
        """测试：自定义值"""
        finding = ExpectedFinding(
            title="Custom Finding",
            category="performance",
            severity="medium",
            file_path="test.py",
            line_range=(10, 20),
            description="Test description",
            should_be_confirmed=False,
            confidence_threshold=0.8,
        )

        assert finding.file_path == "test.py"
        assert finding.line_range == (10, 20)
        assert finding.should_be_confirmed is False
        assert finding.confidence_threshold == 0.8


class TestE2ETestCase:
    """测试 E2ETestCase"""

    def test_init(self):
        """测试：初始化"""
        case = E2ETestCase(
            test_id="E2E-TEST-001",
            name="Test Case",
            category=E2ETestCategory.SECURITY,
            description="Test description",
            diff_chunks=[],
            expected_findings=[],
        )

        assert case.test_id == "E2E-TEST-001"
        assert case.name == "Test Case"
        assert case.category == E2ETestCategory.SECURITY
        assert case.difficulty == "medium"
        assert case.tags == []

    def test_expected_final_count_auto(self):
        """测试：自动计算预期最终数量"""
        findings = [
            ExpectedFinding(title="F1", category="security", severity="high", should_be_confirmed=True),
            ExpectedFinding(title="F2", category="security", severity="high", should_be_confirmed=True),
            ExpectedFinding(title="F3", category="security", severity="high", should_be_confirmed=False),
        ]

        case = E2ETestCase(
            test_id="E2E-TEST-002",
            name="Auto Count",
            category=E2ETestCategory.SECURITY,
            description="Test",
            diff_chunks=[],
            expected_findings=findings,
        )

        assert case.expected_final_count == 2

    def test_expected_final_count_explicit(self):
        """测试：显式指定预期最终数量"""
        case = E2ETestCase(
            test_id="E2E-TEST-003",
            name="Explicit Count",
            category=E2ETestCategory.SECURITY,
            description="Test",
            diff_chunks=[],
            expected_findings=[],
            expected_final_count=5,
        )

        assert case.expected_final_count == 5


class TestE2ETestCases:
    """测试预定义测试用例"""

    def test_sql_injection_basic(self):
        """测试：SQL注入基础用例"""
        assert SQL_INJECTION_BASIC.test_id == "E2E-SEC-001"
        assert SQL_INJECTION_BASIC.category == E2ETestCategory.SECURITY
        assert len(SQL_INJECTION_BASIC.diff_chunks) == 1
        assert len(SQL_INJECTION_BASIC.expected_findings) == 1
        assert SQL_INJECTION_BASIC.difficulty == "easy"

    def test_xss_reflected(self):
        """测试：XSS用例"""
        assert XSS_REFLECTED.test_id == "E2E-SEC-002"
        assert XSS_REFLECTED.category == E2ETestCategory.SECURITY
        assert len(XSS_REFLECTED.expected_findings) == 1

    def test_hardcoded_secret(self):
        """测试：硬编码密钥用例"""
        assert HARDCODED_SECRET.test_id == "E2E-SEC-003"
        assert HARDCODED_SECRET.category == E2ETestCategory.SECURITY

    def test_n_plus_one_query(self):
        """测试：N+1查询用例"""
        assert N_PLUS_ONE_QUERY.test_id == "E2E-PERF-001"
        assert N_PLUS_ONE_QUERY.category == E2ETestCategory.PERFORMANCE
        assert N_PLUS_ONE_QUERY.difficulty == "medium"

    def test_inefficient_algorithm(self):
        """测试：低效算法用例"""
        assert INEFFICIENT_ALGORITHM.test_id == "E2E-PERF-002"
        assert INEFFICIENT_ALGORITHM.category == E2ETestCategory.PERFORMANCE

    def test_null_pointer_check(self):
        """测试：空指针检查用例"""
        assert NULL_POINTER_CHECK.test_id == "E2E-LOGIC-001"
        assert NULL_POINTER_CHECK.category == E2ETestCategory.LOGIC
        assert NULL_POINTER_CHECK.difficulty == "easy"

    def test_off_by_one(self):
        """测试：边界条件用例"""
        assert OFF_BY_ONE.test_id == "E2E-LOGIC-002"
        assert OFF_BY_ONE.category == E2ETestCategory.LOGIC

    def test_code_duplication(self):
        """测试：代码重复用例"""
        assert CODE_DUPLICATION.test_id == "E2E-STYLE-001"
        assert CODE_DUPLICATION.category == E2ETestCategory.STYLE

    def test_mixed_issues(self):
        """测试：混合问题用例"""
        assert MIXED_ISSUES.test_id == "E2E-MIXED-001"
        assert MIXED_ISSUES.category == E2ETestCategory.MIXED
        assert len(MIXED_ISSUES.expected_findings) == 3
        assert MIXED_ISSUES.difficulty == "hard"


class TestE2ETestCaseFiltering:
    """测试用例筛选"""

    def test_total_cases(self):
        """测试：总用例数"""
        assert len(E2E_TEST_CASES) == 9

    def test_get_by_category_security(self):
        """测试：按安全类别筛选"""
        cases = get_e2e_cases_by_category(E2ETestCategory.SECURITY)

        assert len(cases) == 3
        assert all(c.category == E2ETestCategory.SECURITY for c in cases)

    def test_get_by_category_performance(self):
        """测试：按性能类别筛选"""
        cases = get_e2e_cases_by_category(E2ETestCategory.PERFORMANCE)

        assert len(cases) == 2
        assert all(c.category == E2ETestCategory.PERFORMANCE for c in cases)

    def test_get_by_category_logic(self):
        """测试：按逻辑类别筛选"""
        cases = get_e2e_cases_by_category(E2ETestCategory.LOGIC)

        assert len(cases) == 2
        assert all(c.category == E2ETestCategory.LOGIC for c in cases)

    def test_get_by_category_style(self):
        """测试：按风格类别筛选"""
        cases = get_e2e_cases_by_category(E2ETestCategory.STYLE)

        assert len(cases) == 1
        assert all(c.category == E2ETestCategory.STYLE for c in cases)

    def test_get_by_category_mixed(self):
        """测试：按混合类别筛选"""
        cases = get_e2e_cases_by_category(E2ETestCategory.MIXED)

        assert len(cases) == 1
        assert all(c.category == E2ETestCategory.MIXED for c in cases)

    def test_get_by_difficulty_easy(self):
        """测试：按简单难度筛选"""
        cases = get_e2e_cases_by_difficulty("easy")

        assert len(cases) == 4
        assert all(c.difficulty == "easy" for c in cases)

    def test_get_by_difficulty_medium(self):
        """测试：按中等难度筛选"""
        cases = get_e2e_cases_by_difficulty("medium")

        assert len(cases) == 4
        assert all(c.difficulty == "medium" for c in cases)

    def test_get_by_difficulty_hard(self):
        """测试：按困难难度筛选"""
        cases = get_e2e_cases_by_difficulty("hard")

        assert len(cases) == 1
        assert all(c.difficulty == "hard" for c in cases)


class TestDiffChunkContent:
    """测试 DiffChunk 内容"""

    def test_sql_injection_diff_content(self):
        """测试：SQL注入 diff 内容"""
        chunk = SQL_INJECTION_BASIC.diff_chunks[0]

        assert chunk.file_path == "db/query.py"
        assert chunk.language == "python"
        assert len(chunk.additions) == 3
        assert "SELECT" in chunk.additions[1]

    def test_n_plus_one_diff_content(self):
        """测试：N+1查询 diff 内容"""
        chunk = N_PLUS_ONE_QUERY.diff_chunks[0]

        assert chunk.file_path == "services/order.py"
        assert any("for oid in order_ids:" in line for line in chunk.additions)

    def test_mixed_issues_diff_content(self):
        """测试：混合问题 diff 内容"""
        chunk = MIXED_ISSUES.diff_chunks[0]

        assert chunk.file_path == "api/handler.py"
        assert len(chunk.additions) == 17


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
