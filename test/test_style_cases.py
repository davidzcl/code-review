"""
验证风格类测试用例数据集

测试目标：
1. 正确加载测试用例
2. 测试用例数量正确
3. 测试用例结构有效
"""

import pytest


class TestStyleCases:
    """风格类测试用例验证"""

    def test_load_style_cases(self):
        """测试：加载风格类测试用例"""
        from evaluation.datasets.style_cases import get_style_test_cases

        cases = get_style_test_cases()

        assert cases is not None
        assert len(cases) == 20

    def test_case_structure(self):
        """测试：测试用例结构有效"""
        from evaluation.datasets.style_cases import get_style_test_cases

        cases = get_style_test_cases()

        for case in cases:
            assert case.id is not None
            assert case.name is not None
            assert case.category.value == "style"
            assert len(case.diff_chunks) > 0
            assert len(case.injected_issues) > 0

    def test_naming_cases(self):
        """测试：命名规范测试用例数量"""
        from evaluation.datasets.style_cases import get_style_test_cases

        cases = get_style_test_cases()
        name_cases = [c for c in cases if c.id.startswith("STYLE-NAME")]

        assert len(name_cases) == 4

    def test_duplication_cases(self):
        """测试：代码重复测试用例数量"""
        from evaluation.datasets.style_cases import get_style_test_cases

        cases = get_style_test_cases()
        dup_cases = [c for c in cases if c.id.startswith("STYLE-DUP")]

        assert len(dup_cases) == 3

    def test_long_function_cases(self):
        """测试：过长函数测试用例数量"""
        from evaluation.datasets.style_cases import get_style_test_cases

        cases = get_style_test_cases()
        long_cases = [c for c in cases if c.id.startswith("STYLE-LONG")]

        assert len(long_cases) == 3

    def test_documentation_cases(self):
        """测试：缺少文档测试用例数量"""
        from evaluation.datasets.style_cases import get_style_test_cases

        cases = get_style_test_cases()
        doc_cases = [c for c in cases if c.id.startswith("STYLE-DOC")]

        assert len(doc_cases) == 3

    def test_unused_cases(self):
        """测试：未使用代码测试用例数量"""
        from evaluation.datasets.style_cases import get_style_test_cases

        cases = get_style_test_cases()
        unused_cases = [c for c in cases if c.id.startswith("STYLE-UNUSED")]

        assert len(unused_cases) == 3

    def test_magic_cases(self):
        """测试：魔法数字测试用例数量"""
        from evaluation.datasets.style_cases import get_style_test_cases

        cases = get_style_test_cases()
        magic_cases = [c for c in cases if c.id.startswith("STYLE-MAGIC")]

        assert len(magic_cases) == 2

    def test_nesting_cases(self):
        """测试：嵌套过深测试用例数量"""
        from evaluation.datasets.style_cases import get_style_test_cases

        cases = get_style_test_cases()
        nest_cases = [c for c in cases if c.id.startswith("STYLE-NEST")]

        assert len(nest_cases) == 2

    def test_severity_distribution(self):
        """测试：严重级别分布"""
        from evaluation.datasets.style_cases import get_style_test_cases

        cases = get_style_test_cases()

        severities = {}
        for case in cases:
            for issue in case.injected_issues:
                sev = issue.severity
                severities[sev] = severities.get(sev, 0) + 1

        assert "low" in severities or "medium" in severities

    def test_detection_hints(self):
        """测试：检测提示关键词"""
        from evaluation.datasets.style_cases import get_style_test_cases

        cases = get_style_test_cases()

        for case in cases:
            for issue in case.injected_issues:
                assert len(issue.detection_hints) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
