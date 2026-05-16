"""
验证 StabilityMetric 实现

测试目标：
1. 正确计算结构一致性（字段出现频率）
2. 正确计算严重级别分布 KL 散度
3. 正确处理空结果
4. 正确处理单次运行结果
"""

import pytest
from typing import List, Any


class TestStabilityMetric:
    """StabilityMetric 测试"""

    def test_create_stability_metric(self):
        """测试：创建 StabilityMetric 实例"""
        from evaluation.metrics.stability import StabilityMetric

        metric = StabilityMetric(n_runs=3)
        assert metric.n_runs == 3

    def test_structural_consistency_identical_results(self):
        """测试：完全相同的结果，结构一致性为 1.0"""
        from evaluation.metrics.stability import StabilityMetric
        from evaluation.metrics.stability import StabilityResult

        metric = StabilityMetric(n_runs=3)

        results = [
            StabilityResult(
                findings=[
                    {"title": "SQL 注入", "severity": "critical", "file_path": "db.py"}
                ]
            ),
            StabilityResult(
                findings=[
                    {"title": "SQL 注入", "severity": "critical", "file_path": "db.py"}
                ]
            ),
            StabilityResult(
                findings=[
                    {"title": "SQL 注入", "severity": "critical", "file_path": "db.py"}
                ]
            ),
        ]

        score = metric.calculate_structural_consistency(results)
        assert score == 1.0

    def test_structural_consistency_different_results(self):
        """测试：完全不同的结果，结构一致性为 0.0"""
        from evaluation.metrics.stability import StabilityMetric, StabilityResult

        metric = StabilityMetric(n_runs=3)

        results = [
            StabilityResult(
                findings=[{"title": "问题 A", "severity": "critical", "file_path": "a.py"}]
            ),
            StabilityResult(
                findings=[{"title": "问题 B", "severity": "high", "file_path": "b.py"}]
            ),
            StabilityResult(
                findings=[{"title": "问题 C", "severity": "medium", "file_path": "c.py"}]
            ),
        ]

        score = metric.calculate_structural_consistency(results)
        assert score < 0.5

    def test_severity_distribution_kl_divergence(self):
        """测试：严重级别分布 KL 散度计算"""
        from evaluation.metrics.stability import StabilityMetric, StabilityResult

        metric = StabilityMetric(n_runs=3)

        results = [
            StabilityResult(
                findings=[
                    {"severity": "critical"},
                    {"severity": "high"},
                    {"severity": "medium"},
                ]
            ),
            StabilityResult(
                findings=[
                    {"severity": "critical"},
                    {"severity": "high"},
                    {"severity": "medium"},
                ]
            ),
            StabilityResult(
                findings=[
                    {"severity": "critical"},
                    {"severity": "high"},
                    {"severity": "medium"},
                ]
            ),
        ]

        kl_div = metric.calculate_severity_kl_divergence(results)
        assert kl_div == 0.0

    def test_severity_distribution_different(self):
        """测试：不同的严重级别分布，KL 散度 > 0"""
        from evaluation.metrics.stability import StabilityMetric, StabilityResult

        metric = StabilityMetric(n_runs=3)

        results = [
            StabilityResult(
                findings=[{"severity": "critical"}, {"severity": "critical"}]
            ),
            StabilityResult(
                findings=[{"severity": "low"}, {"severity": "low"}]
            ),
            StabilityResult(
                findings=[{"severity": "medium"}, {"severity": "medium"}]
            ),
        ]

        kl_div = metric.calculate_severity_kl_divergence(results)
        assert kl_div > 0.5

    def test_empty_results_returns_zero(self):
        """测试：空结果返回 0.0"""
        from evaluation.metrics.stability import StabilityMetric

        metric = StabilityMetric(n_runs=3)

        score = metric.calculate_structural_consistency([])
        assert score == 0.0

    def test_single_result_returns_one(self):
        """测试：单次运行结果返回 1.0"""
        from evaluation.metrics.stability import StabilityMetric, StabilityResult

        metric = StabilityMetric(n_runs=1)

        results = [
            StabilityResult(
                findings=[{"title": "问题", "severity": "high", "file_path": "test.py"}]
            )
        ]

        score = metric.calculate_structural_consistency(results)
        assert score == 1.0

    def test_overall_stability_score(self):
        """测试：综合稳定性评分"""
        from evaluation.metrics.stability import StabilityMetric, StabilityResult

        metric = StabilityMetric(n_runs=3)

        results = [
            StabilityResult(
                findings=[
                    {"title": "SQL 注入", "severity": "critical", "file_path": "db.py"}
                ]
            ),
            StabilityResult(
                findings=[
                    {"title": "SQL 注入", "severity": "critical", "file_path": "db.py"}
                ]
            ),
            StabilityResult(
                findings=[
                    {"title": "SQL 注入", "severity": "high", "file_path": "db.py"}
                ]
            ),
        ]

        score = metric.calculate_overall_stability(results)
        assert 0.5 <= score <= 1.0

    def test_stability_result_dataclass(self):
        """测试：StabilityResult 数据类"""
        from evaluation.metrics.stability import StabilityResult

        result = StabilityResult(
            findings=[{"title": "测试", "severity": "high"}],
            metadata={"run_id": 1},
        )

        assert len(result.findings) == 1
        assert result.metadata["run_id"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
