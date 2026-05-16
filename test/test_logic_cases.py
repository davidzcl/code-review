"""
验证逻辑类测试用例数据集

测试目标：
1. 正确加载测试用例
2. 测试用例数量正确
3. 测试用例结构有效
"""

import pytest


class TestLogicCases:
    """逻辑类测试用例验证"""

    def test_load_logic_cases(self):
        """测试：加载逻辑类测试用例"""
        from evaluation.datasets.logic_cases import get_logic_test_cases

        cases = get_logic_test_cases()

        assert cases is not None
        assert len(cases) == 25

    def test_case_structure(self):
        """测试：测试用例结构有效"""
        from evaluation.datasets.logic_cases import get_logic_test_cases

        cases = get_logic_test_cases()

        for case in cases:
            assert case.id is not None
            assert case.name is not None
            assert case.category.value == "logic"
            assert len(case.diff_chunks) > 0
            assert len(case.injected_issues) > 0

    def test_null_check_cases(self):
        """测试：空指针检查测试用例数量"""
        from evaluation.datasets.logic_cases import get_logic_test_cases

        cases = get_logic_test_cases()
        null_cases = [c for c in cases if c.id.startswith("LOGIC-NULL")]

        assert len(null_cases) == 5

    def test_boundary_cases(self):
        """测试：边界条件测试用例数量"""
        from evaluation.datasets.logic_cases import get_logic_test_cases

        cases = get_logic_test_cases()
        bound_cases = [c for c in cases if c.id.startswith("LOGIC-BOUND")]

        assert len(bound_cases) == 5

    def test_type_cases(self):
        """测试：类型错误测试用例数量"""
        from evaluation.datasets.logic_cases import get_logic_test_cases

        cases = get_logic_test_cases()
        type_cases = [c for c in cases if c.id.startswith("LOGIC-TYPE")]

        assert len(type_cases) == 4

    def test_condition_cases(self):
        """测试：条件判断测试用例数量"""
        from evaluation.datasets.logic_cases import get_logic_test_cases

        cases = get_logic_test_cases()
        cond_cases = [c for c in cases if c.id.startswith("LOGIC-COND")]

        assert len(cond_cases) == 4

    def test_exception_cases(self):
        """测试：异常处理测试用例数量"""
        from evaluation.datasets.logic_cases import get_logic_test_cases

        cases = get_logic_test_cases()
        except_cases = [c for c in cases if c.id.startswith("LOGIC-EXCEPT")]

        assert len(except_cases) == 3

    def test_concurrency_cases(self):
        """测试：并发问题测试用例数量"""
        from evaluation.datasets.logic_cases import get_logic_test_cases

        cases = get_logic_test_cases()
        conc_cases = [c for c in cases if c.id.startswith("LOGIC-CONC")]

        assert len(conc_cases) == 2

    def test_resource_cases(self):
        """测试：资源泄漏测试用例数量"""
        from evaluation.datasets.logic_cases import get_logic_test_cases

        cases = get_logic_test_cases()
        resource_cases = [c for c in cases if c.id.startswith("LOGIC-RESOURCE")]

        assert len(resource_cases) == 2

    def test_severity_distribution(self):
        """测试：严重级别分布"""
        from evaluation.datasets.logic_cases import get_logic_test_cases

        cases = get_logic_test_cases()

        severities = {}
        for case in cases:
            for issue in case.injected_issues:
                sev = issue.severity
                severities[sev] = severities.get(sev, 0) + 1

        assert "high" in severities or "medium" in severities

    def test_detection_hints(self):
        """测试：检测提示关键词"""
        from evaluation.datasets.logic_cases import get_logic_test_cases

        cases = get_logic_test_cases()

        for case in cases:
            for issue in case.injected_issues:
                assert len(issue.detection_hints) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
