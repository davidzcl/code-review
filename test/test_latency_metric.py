"""
验证 LatencyMetric 实现

测试目标：
1. 正确记录响应时间
2. 正确计算延迟百分位数（P50/P95/P99）
3. 正确处理空结果
"""

import pytest
import time


class TestLatencyMetric:
    """LatencyMetric 测试"""

    def test_create_latency_metric(self):
        """测试：创建 LatencyMetric 实例"""
        from evaluation.metrics.latency import LatencyMetric

        metric = LatencyMetric()
        assert metric is not None

    def test_record_latency(self):
        """测试：记录延迟数据"""
        from evaluation.metrics.latency import LatencyMetric, LatencyResult

        metric = LatencyMetric()
        result = LatencyResult(
            start_time=time.time(),
            end_time=time.time() + 1.0,
            total_latency_ms=1000.0,
        )

        metric.record(result)
        assert len(metric.records) == 1

    def test_calculate_percentiles(self):
        """测试：计算延迟百分位数"""
        from evaluation.metrics.latency import LatencyMetric, LatencyResult

        metric = LatencyMetric()

        for i in range(10):
            result = LatencyResult(
                start_time=time.time(),
                end_time=time.time() + (i + 1) * 0.1,
                total_latency_ms=(i + 1) * 100.0,
            )
            metric.record(result)

        percentiles = metric.calculate_percentiles()

        assert "p50" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles
        assert percentiles["p50"] == 550.0
        assert 950.0 <= percentiles["p95"] <= 960.0
        assert 990.0 <= percentiles["p99"] <= 1000.0

    def test_empty_records_returns_zero(self):
        """测试：空记录返回 0"""
        from evaluation.metrics.latency import LatencyMetric

        metric = LatencyMetric()
        percentiles = metric.calculate_percentiles()

        assert percentiles["p50"] == 0.0
        assert percentiles["p95"] == 0.0
        assert percentiles["p99"] == 0.0

    def test_single_record(self):
        """测试：单条记录"""
        from evaluation.metrics.latency import LatencyMetric, LatencyResult

        metric = LatencyMetric()
        result = LatencyResult(
            start_time=time.time(),
            end_time=time.time() + 0.5,
            total_latency_ms=500.0,
        )
        metric.record(result)

        percentiles = metric.calculate_percentiles()

        assert percentiles["p50"] == 500.0
        assert percentiles["p95"] == 500.0
        assert percentiles["p99"] == 500.0

    def test_average_latency(self):
        """测试：计算平均延迟"""
        from evaluation.metrics.latency import LatencyMetric, LatencyResult

        metric = LatencyMetric()

        latencies = [100.0, 200.0, 300.0, 400.0, 500.0]
        for lat in latencies:
            result = LatencyResult(
                start_time=time.time(),
                end_time=time.time() + lat / 1000.0,
                total_latency_ms=lat,
            )
            metric.record(result)

        avg = metric.calculate_average_latency()
        assert avg == 300.0

    def test_latency_result_dataclass(self):
        """测试：LatencyResult 数据类"""
        from evaluation.metrics.latency import LatencyResult

        start = time.time()
        end = start + 1.0

        result = LatencyResult(
            start_time=start,
            end_time=end,
            total_latency_ms=1000.0,
            tool_call_overhead_ms=200.0,
        )

        assert result.start_time == start
        assert result.end_time == end
        assert result.total_latency_ms == 1000.0
        assert result.tool_call_overhead_ms == 200.0

    def test_get_statistics(self):
        """测试：获取完整统计信息"""
        from evaluation.metrics.latency import LatencyMetric, LatencyResult

        metric = LatencyMetric()

        for i in range(5):
            result = LatencyResult(
                start_time=time.time(),
                end_time=time.time() + (i + 1) * 0.1,
                total_latency_ms=(i + 1) * 100.0,
            )
            metric.record(result)

        stats = metric.get_statistics()

        assert stats["count"] == 5
        assert stats["min_ms"] == 100.0
        assert stats["max_ms"] == 500.0
        assert stats["avg_ms"] == 300.0
        assert "p50" in stats
        assert "p95" in stats
        assert "p99" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
