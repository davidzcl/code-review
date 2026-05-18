import pytest
import asyncio
from unittest.mock import MagicMock
from agents.reviewer import ReviewerAgent
from evaluation.metrics.tool_usage import ToolCallMetric, ToolCallRecord


class TestToolCallInstrumentation:
    """测试工具调用轨迹采集"""

    def test_reviewer_agent_has_tool_call_history(self):
        """测试：ReviewerAgent 包含 tool_call_history 属性"""
        mock_model = MagicMock()
        agent = ReviewerAgent(
            name="Test",
            role="security",
            sys_prompt="test",
            model=mock_model,
        )
        assert hasattr(agent, "tool_call_history")
        assert len(agent.tool_call_history) == 0

    def test_clear_tool_call_history(self):
        """测试：清空工具调用历史"""
        mock_model = MagicMock()
        agent = ReviewerAgent(
            name="Test",
            role="security",
            sys_prompt="test",
            model=mock_model,
        )
        # 测试清空功能
        agent.clear_tool_call_history()
        assert len(agent.tool_call_history) == 0