"""
响应时间评测指标

记录并计算智能体响应时间的统计信息。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class LatencyResult:
    """单次延迟记录"""

    start_time: float
    end_time: float
    total_latency_ms: float
    tool_call_overhead_ms: float = 0.0
    first_token_latency_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LatencyMetric:
    """延迟评测指标

    记录并计算响应时间的统计信息，包括：
    - 延迟百分位数（P50/P95/P99）
    - 平均延迟
    - 最小/最大延迟
    - 工具调用开销
    """

    def __init__(self):
        self.records: List[LatencyResult] = []

    def record(self, result: LatencyResult) -> None:
        """记录延迟数据

        Args:
            result: 延迟结果
        """
        self.records.append(result)

    def calculate_percentiles(self) -> Dict[str, float]:
        """计算延迟百分位数

        Returns:
            包含 P50/P95/P99 的字典
        """
        if not self.records:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0}

        latencies = [r.total_latency_ms for r in self.records]

        return {
            "p50": float(np.percentile(latencies, 50)),
            "p95": float(np.percentile(latencies, 95)),
            "p99": float(np.percentile(latencies, 99)),
        }

    def calculate_average_latency(self) -> float:
        """计算平均延迟

        Returns:
            平均延迟（毫秒）
        """
        if not self.records:
            return 0.0

        latencies = [r.total_latency_ms for r in self.records]
        return sum(latencies) / len(latencies)

    def get_statistics(self) -> Dict[str, Any]:
        """获取完整统计信息

        Returns:
            包含 count/min/max/avg/percentiles 的字典
        """
        if not self.records:
            return {
                "count": 0,
                "min_ms": 0.0,
                "max_ms": 0.0,
                "avg_ms": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
            }

        latencies = [r.total_latency_ms for r in self.records]
        percentiles = self.calculate_percentiles()

        return {
            "count": len(self.records),
            "min_ms": min(latencies),
            "max_ms": max(latencies),
            "avg_ms": self.calculate_average_latency(),
            **percentiles,
        }

    def reset(self) -> None:
        """重置记录"""
        self.records = []
