"""
验证 ToolCallMetric 实现

测试目标：
1. 正确分析工具调用轨迹
2. 正确计算工具选择准确率
3. 正确计算参数传递准确率
4. 正确计算调用成功率
"""

import pytest


class TestToolCallMetric:
    """ToolCallMetric 测试"""

    def test_create_tool_call_metric(self):
        """测试：创建 ToolCallMetric 实例"""
        from evaluation.metrics.tool_usage import ToolCallMetric

        metric = ToolCallMetric()
        assert metric is not None

    def test_analyze_tool_calls(self):
        """测试：分析工具调用轨迹"""
        from evaluation.metrics.tool_usage import ToolCallMetric, ToolCallRecord

        metric = ToolCallMetric()

        trajectory = [
            ToolCallRecord(
                tool_name="scan_risk_signals",
                parameters={"base": "main", "target": "feature"},
                success=True,
                error=None,
            ),
            ToolCallRecord(
                tool_name="scan_secrets",
                parameters={"diff_text": "sample diff"},
                success=True,
                error=None,
            ),
        ]

        result = metric.analyze(trajectory)

        assert result.total_calls == 2
        assert result.successful_calls == 2

    def test_tool_selection_accuracy(self):
        """测试：工具选择准确率"""
        from evaluation.metrics.tool_usage import ToolCallMetric, ToolCallRecord

        metric = ToolCallMetric()

        trajectory = [
            ToolCallRecord(tool_name="scan_risk_signals", parameters={}, success=True),
            ToolCallRecord(tool_name="scan_secrets", parameters={}, success=True),
        ]

        expected_tools = ["scan_risk_signals", "scan_secrets"]
        accuracy = metric.calculate_selection_accuracy(trajectory, expected_tools)

        assert accuracy == 1.0

    def test_tool_selection_accuracy_partial(self):
        """测试：部分正确的工具选择"""
        from evaluation.metrics.tool_usage import ToolCallMetric, ToolCallRecord

        metric = ToolCallMetric()

        trajectory = [
            ToolCallRecord(tool_name="scan_risk_signals", parameters={}, success=True),
            ToolCallRecord(tool_name="wrong_tool", parameters={}, success=True),
        ]

        expected_tools = ["scan_risk_signals", "scan_secrets"]
        accuracy = metric.calculate_selection_accuracy(trajectory, expected_tools)

        assert accuracy == 0.5

    def test_parameter_accuracy(self):
        """测试：参数传递准确率"""
        from evaluation.metrics.tool_usage import ToolCallMetric, ToolCallRecord

        metric = ToolCallMetric()

        trajectory = [
            ToolCallRecord(
                tool_name="scan_risk_signals",
                parameters={"base": "main", "target": "feature"},
                success=True,
            ),
        ]

        expected_params = {"base": "main", "target": "feature"}
        accuracy = metric.calculate_parameter_accuracy(trajectory, expected_params)

        assert accuracy == 1.0

    def test_call_success_rate(self):
        """测试：调用成功率"""
        from evaluation.metrics.tool_usage import ToolCallMetric, ToolCallRecord

        metric = ToolCallMetric()

        trajectory = [
            ToolCallRecord(tool_name="tool1", parameters={}, success=True),
            ToolCallRecord(tool_name="tool2", parameters={}, success=False, error="timeout"),
            ToolCallRecord(tool_name="tool3", parameters={}, success=True),
        ]

        rate = metric.calculate_success_rate(trajectory)

        assert rate == 2 / 3

    def test_empty_trajectory(self):
        """测试：空轨迹"""
        from evaluation.metrics.tool_usage import ToolCallMetric

        metric = ToolCallMetric()

        result = metric.analyze([])

        assert result.total_calls == 0
        assert result.successful_calls == 0

    def test_tool_call_record_dataclass(self):
        """测试：ToolCallRecord 数据类"""
        from evaluation.metrics.tool_usage import ToolCallRecord

        record = ToolCallRecord(
            tool_name="scan_risk_signals",
            parameters={"base": "main"},
            success=True,
            error=None,
        )

        assert record.tool_name == "scan_risk_signals"
        assert record.parameters == {"base": "main"}
        assert record.success is True
        assert record.error is None

    def test_get_statistics(self):
        """测试：获取完整统计信息"""
        from evaluation.metrics.tool_usage import ToolCallMetric, ToolCallRecord

        metric = ToolCallMetric()

        trajectory = [
            ToolCallRecord(tool_name="scan_risk_signals", parameters={"base": "main"}, success=True),
            ToolCallRecord(tool_name="scan_secrets", parameters={"diff_text": "test"}, success=True),
            ToolCallRecord(tool_name="search_code", parameters={"pattern": "TODO"}, success=False, error="not found"),
        ]

        expected_tools = ["scan_risk_signals", "scan_secrets"]
        stats = metric.get_statistics(trajectory, expected_tools)

        assert stats["total_calls"] == 3
        assert stats["successful_calls"] == 2
        assert stats["success_rate"] == 2 / 3
        assert "selection_accuracy" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
