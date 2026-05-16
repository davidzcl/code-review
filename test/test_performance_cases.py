"""
验证性能类测试用例数据集

测试目标：
1. 正确加载测试用例
2. 测试用例数量正确
3. 测试用例结构有效
"""

import pytest


class TestPerformanceCases:
    """性能类测试用例验证"""

    def test_load_performance_cases(self):
        """测试：加载性能类测试用例"""
        from evaluation.datasets.performance_cases import get_performance_test_cases

        cases = get_performance_test_cases()

        assert cases is not None
        assert len(cases) == 25

    def test_case_structure(self):
        """测试：测试用例结构有效"""
        from evaluation.datasets.performance_cases import get_performance_test_cases

        cases = get_performance_test_cases()

        for case in cases:
            assert case.id is not None
            assert case.name is not None
            assert case.category.value == "performance"
            assert len(case.diff_chunks) > 0
            assert len(case.injected_issues) > 0

    def test_complexity_cases(self):
        """测试：复杂度问题测试用例数量"""
        from evaluation.datasets.performance_cases import get_performance_test_cases

        cases = get_performance_test_cases()
        complex_cases = [c for c in cases if c.id.startswith("PERF-COMPLEX")]

        assert len(complex_cases) == 5

    def test_n1_cases(self):
        """测试：N+1 查询测试用例数量"""
        from evaluation.datasets.performance_cases import get_performance_test_cases

        cases = get_performance_test_cases()
        n1_cases = [c for c in cases if c.id.startswith("PERF-N1")]

        assert len(n1_cases) == 5

    def test_memory_cases(self):
        """测试：内存问题测试用例数量"""
        from evaluation.datasets.performance_cases import get_performance_test_cases

        cases = get_performance_test_cases()
        mem_cases = [c for c in cases if c.id.startswith("PERF-MEM")]

        assert len(mem_cases) == 4

    def test_redundant_cases(self):
        """测试：重复计算测试用例数量"""
        from evaluation.datasets.performance_cases import get_performance_test_cases

        cases = get_performance_test_cases()
        redundant_cases = [c for c in cases if c.id.startswith("PERF-REDUNDANT")]

        assert len(redundant_cases) == 4

    def test_string_cases(self):
        """测试：字符串操作测试用例数量"""
        from evaluation.datasets.performance_cases import get_performance_test_cases

        cases = get_performance_test_cases()
        str_cases = [c for c in cases if c.id.startswith("PERF-STR")]

        assert len(str_cases) == 3

    def test_cache_cases(self):
        """测试：缓存问题测试用例数量"""
        from evaluation.datasets.performance_cases import get_performance_test_cases

        cases = get_performance_test_cases()
        cache_cases = [c for c in cases if c.id.startswith("PERF-CACHE")]

        assert len(cache_cases) == 2

    def test_blocking_cases(self):
        """测试：阻塞操作测试用例数量"""
        from evaluation.datasets.performance_cases import get_performance_test_cases

        cases = get_performance_test_cases()
        block_cases = [c for c in cases if c.id.startswith("PERF-BLOCK")]

        assert len(block_cases) == 2

    def test_severity_distribution(self):
        """测试：严重级别分布"""
        from evaluation.datasets.performance_cases import get_performance_test_cases

        cases = get_performance_test_cases()

        severities = {}
        for case in cases:
            for issue in case.injected_issues:
                sev = issue.severity
                severities[sev] = severities.get(sev, 0) + 1

        assert "high" in severities or "medium" in severities

    def test_detection_hints(self):
        """测试：检测提示关键词"""
        from evaluation.datasets.performance_cases import get_performance_test_cases

        cases = get_performance_test_cases()

        for case in cases:
            for issue in case.injected_issues:
                assert len(issue.detection_hints) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
