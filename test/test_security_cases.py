"""
验证安全类测试用例数据集

测试目标：
1. 正确加载测试用例
2. 测试用例数量正确
3. 测试用例结构有效
"""

import pytest


class TestSecurityCases:
    """安全类测试用例验证"""

    def test_load_security_cases(self):
        """测试：加载安全类测试用例"""
        from evaluation.datasets.security_cases import get_security_test_cases

        cases = get_security_test_cases()

        assert cases is not None
        assert len(cases) == 30

    def test_case_structure(self):
        """测试：测试用例结构有效"""
        from evaluation.datasets.security_cases import get_security_test_cases

        cases = get_security_test_cases()

        for case in cases:
            assert case.id is not None
            assert case.name is not None
            assert case.category.value == "security"
            assert len(case.diff_chunks) > 0
            assert len(case.injected_issues) > 0

    def test_sql_injection_cases(self):
        """测试：SQL 注入测试用例数量"""
        from evaluation.datasets.security_cases import get_security_test_cases

        cases = get_security_test_cases()
        sql_cases = [c for c in cases if c.id.startswith("SEC-SQL")]

        assert len(sql_cases) == 5

    def test_xss_cases(self):
        """测试：XSS 测试用例数量"""
        from evaluation.datasets.security_cases import get_security_test_cases

        cases = get_security_test_cases()
        xss_cases = [c for c in cases if c.id.startswith("SEC-XSS")]

        assert len(xss_cases) == 5

    def test_hardcoded_secret_cases(self):
        """测试：硬编码密钥测试用例数量"""
        from evaluation.datasets.security_cases import get_security_test_cases

        cases = get_security_test_cases()
        key_cases = [c for c in cases if c.id.startswith("SEC-KEY")]

        assert len(key_cases) == 5

    def test_command_injection_cases(self):
        """测试：命令注入测试用例数量"""
        from evaluation.datasets.security_cases import get_security_test_cases

        cases = get_security_test_cases()
        cmd_cases = [c for c in cases if c.id.startswith("SEC-CMD")]

        assert len(cmd_cases) == 4

    def test_path_traversal_cases(self):
        """测试：路径遍历测试用例数量"""
        from evaluation.datasets.security_cases import get_security_test_cases

        cases = get_security_test_cases()
        path_cases = [c for c in cases if c.id.startswith("SEC-PATH")]

        assert len(path_cases) == 3

    def test_deserialization_cases(self):
        """测试：反序列化测试用例数量"""
        from evaluation.datasets.security_cases import get_security_test_cases

        cases = get_security_test_cases()
        deser_cases = [c for c in cases if c.id.startswith("SEC-DESER")]

        assert len(deser_cases) == 3

    def test_information_disclosure_cases(self):
        """测试：信息泄露测试用例数量"""
        from evaluation.datasets.security_cases import get_security_test_cases

        cases = get_security_test_cases()
        leak_cases = [c for c in cases if c.id.startswith("SEC-LEAK")]

        assert len(leak_cases) == 3

    def test_ssrf_cases(self):
        """测试：SSRF 测试用例数量"""
        from evaluation.datasets.security_cases import get_security_test_cases

        cases = get_security_test_cases()
        ssrf_cases = [c for c in cases if c.id.startswith("SEC-SSRF")]

        assert len(ssrf_cases) == 2

    def test_severity_distribution(self):
        """测试：严重级别分布"""
        from evaluation.datasets.security_cases import get_security_test_cases

        cases = get_security_test_cases()

        severities = {}
        for case in cases:
            for issue in case.injected_issues:
                sev = issue.severity
                severities[sev] = severities.get(sev, 0) + 1

        assert "critical" in severities
        assert "high" in severities

    def test_detection_hints(self):
        """测试：检测提示关键词"""
        from evaluation.datasets.security_cases import get_security_test_cases

        cases = get_security_test_cases()

        for case in cases:
            for issue in case.injected_issues:
                assert len(issue.detection_hints) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
