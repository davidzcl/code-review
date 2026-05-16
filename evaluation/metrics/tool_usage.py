"""
工具调用评测指标

分析智能体的工具调用轨迹，计算工具选择和参数传递的准确性。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolCallRecord:
    """工具调用记录"""

    tool_name: str
    parameters: Dict[str, Any]
    success: bool
    error: Optional[str] = None
    timestamp: Optional[float] = None


@dataclass
class ToolCallAnalysisResult:
    """工具调用分析结果"""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    unique_tools: List[str] = field(default_factory=list)
    call_details: List[ToolCallRecord] = field(default_factory=list)


class ToolCallMetric:
    """工具调用评测指标

    分析工具调用轨迹，计算：
    - 工具选择准确率
    - 参数传递准确率
    - 调用成功率
    """

    def analyze(self, trajectory: List[ToolCallRecord]) -> ToolCallAnalysisResult:
        """分析工具调用轨迹

        Args:
            trajectory: 工具调用记录列表

        Returns:
            分析结果
        """
        if not trajectory:
            return ToolCallAnalysisResult()

        successful = sum(1 for r in trajectory if r.success)
        failed = len(trajectory) - successful
        unique_tools = list(set(r.tool_name for r in trajectory))

        return ToolCallAnalysisResult(
            total_calls=len(trajectory),
            successful_calls=successful,
            failed_calls=failed,
            unique_tools=unique_tools,
            call_details=trajectory,
        )

    def calculate_selection_accuracy(
        self,
        trajectory: List[ToolCallRecord],
        expected_tools: List[str],
    ) -> float:
        """计算工具选择准确率

        Args:
            trajectory: 工具调用记录列表
            expected_tools: 期望调用的工具列表

        Returns:
            选择准确率 (0.0-1.0)
        """
        if not expected_tools:
            return 1.0

        if not trajectory:
            return 0.0

        called_tools = [r.tool_name for r in trajectory]
        correct_selections = sum(1 for t in called_tools if t in expected_tools)

        return correct_selections / len(expected_tools)

    def calculate_parameter_accuracy(
        self,
        trajectory: List[ToolCallRecord],
        expected_params: Dict[str, Any],
    ) -> float:
        """计算参数传递准确率

        Args:
            trajectory: 工具调用记录列表
            expected_params: 期望的参数

        Returns:
            参数准确率 (0.0-1.0)
        """
        if not expected_params:
            return 1.0

        if not trajectory:
            return 0.0

        total_params = len(expected_params)
        correct_params = 0

        for record in trajectory:
            for key, expected_value in expected_params.items():
                if key in record.parameters:
                    actual_value = record.parameters[key]
                    if actual_value == expected_value:
                        correct_params += 1

        return correct_params / total_params if total_params > 0 else 1.0

    def calculate_success_rate(self, trajectory: List[ToolCallRecord]) -> float:
        """计算调用成功率

        Args:
            trajectory: 工具调用记录列表

        Returns:
            成功率 (0.0-1.0)
        """
        if not trajectory:
            return 0.0

        successful = sum(1 for r in trajectory if r.success)
        return successful / len(trajectory)

    def get_statistics(
        self,
        trajectory: List[ToolCallRecord],
        expected_tools: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """获取完整统计信息

        Args:
            trajectory: 工具调用记录列表
            expected_tools: 期望调用的工具列表

        Returns:
            统计信息字典
        """
        analysis = self.analyze(trajectory)

        stats = {
            "total_calls": analysis.total_calls,
            "successful_calls": analysis.successful_calls,
            "failed_calls": analysis.failed_calls,
            "success_rate": self.calculate_success_rate(trajectory),
            "unique_tools": analysis.unique_tools,
        }

        if expected_tools:
            stats["selection_accuracy"] = self.calculate_selection_accuracy(
                trajectory, expected_tools
            )

        return stats
