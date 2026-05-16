"""
验证流程评测指标

测试目标：
1. StageMetrics 计算正确性
2. DebateMetrics 计算正确性
3. MergeMetrics 计算正确性
4. VerdictMetrics 计算正确性
5. ResourceMetrics 计算正确性
6. PipelineResult 序列化
7. PipelineMetrics 汇总统计
"""

import pytest
from datetime import datetime, timedelta
import numpy as np

from evaluation.metrics.pipeline_metrics import (
    StageMetrics,
    DebateMetrics,
    MergeMetrics,
    VerdictMetrics,
    ResourceMetrics,
    PipelineResult,
    PipelineMetrics,
)


class TestStageMetrics:
    """测试 StageMetrics"""

    def test_duration_calculation(self):
        """测试：自动计算耗时"""
        start = datetime(2026, 5, 16, 10, 0, 0)
        end = datetime(2026, 5, 16, 10, 0, 5)
        stage = StageMetrics(
            stage_name="parallel_review",
            start_time=start,
            end_time=end,
        )

        assert stage.duration_ms == 5000.0

    def test_explicit_duration(self):
        """测试：显式指定耗时"""
        start = datetime(2026, 5, 16, 10, 0, 0)
        end = datetime(2026, 5, 16, 10, 0, 5)
        stage = StageMetrics(
            stage_name="debate",
            start_time=start,
            end_time=end,
            duration_ms=3000.0,
        )

        assert stage.duration_ms == 3000.0

    def test_error_stage(self):
        """测试：错误阶段"""
        start = datetime(2026, 5, 16, 10, 0, 0)
        end = datetime(2026, 5, 16, 10, 0, 1)
        stage = StageMetrics(
            stage_name="merge",
            start_time=start,
            end_time=end,
            success=False,
            error="Merge conflict",
        )

        assert stage.success is False
        assert stage.error == "Merge conflict"


class TestDebateMetrics:
    """测试 DebateMetrics"""

    def test_calculate_rates(self):
        """测试：计算确认率和驳回率"""
        metrics = DebateMetrics(
            total_findings=10,
            total_rounds=25,
            confirmed_count=7,
            dismissed_count=3,
        )
        metrics.calculate_rates()

        assert metrics.confirmation_rate == 0.7
        assert metrics.dismissal_rate == 0.3
        assert metrics.avg_rounds_per_finding == 2.5

    def test_zero_findings(self):
        """测试：零发现"""
        metrics = DebateMetrics()
        metrics.calculate_rates()

        assert metrics.confirmation_rate == 0.0
        assert metrics.dismissal_rate == 0.0


class TestMergeMetrics:
    """测试 MergeMetrics"""

    def test_calculate_rates(self):
        """测试：计算合并率"""
        metrics = MergeMetrics(
            total_findings=20,
            merged_groups=3,
            total_merged=8,
            similarity_scores=[0.85, 0.90, 0.88],
        )
        metrics.calculate_rates()

        assert metrics.merge_rate == 0.4
        assert metrics.avg_group_size == pytest.approx(8 / 3, rel=0.01)
        assert metrics.avg_similarity == pytest.approx(0.8767, rel=0.01)

    def test_empty_similarity(self):
        """测试：空相似度列表"""
        metrics = MergeMetrics(total_findings=10)
        metrics.calculate_rates()

        assert metrics.avg_similarity == 0.0


class TestResourceMetrics:
    """测试 ResourceMetrics"""

    def test_calculate_averages(self):
        """测试：计算平均值"""
        metrics = ResourceMetrics(
            total_llm_calls=10,
            total_tokens=5000,
            prompt_tokens=3000,
            completion_tokens=2000,
        )
        metrics.calculate_averages()

        assert metrics.avg_tokens_per_call == 500.0

    def test_zero_calls(self):
        """测试：零调用"""
        metrics = ResourceMetrics()
        metrics.calculate_averages()

        assert metrics.avg_tokens_per_call == 0.0


class TestPipelineResult:
    """测试 PipelineResult"""

    def test_duration_calculation(self):
        """测试：自动计算总耗时"""
        start = datetime(2026, 5, 16, 10, 0, 0)
        end = datetime(2026, 5, 16, 10, 5, 0)
        result = PipelineResult(
            pipeline_id="test-001",
            start_time=start,
            end_time=end,
        )

        assert result.total_duration_ms == 300000.0

    def test_get_stage_duration(self):
        """测试：获取阶段耗时"""
        start = datetime(2026, 5, 16, 10, 0, 0)
        end = datetime(2026, 5, 16, 10, 5, 0)

        stage1 = StageMetrics(
            stage_name="parallel_review",
            start_time=start,
            end_time=start + timedelta(seconds=60),
        )
        stage2 = StageMetrics(
            stage_name="debate",
            start_time=start + timedelta(seconds=60),
            end_time=start + timedelta(seconds=180),
        )

        result = PipelineResult(
            pipeline_id="test-002",
            start_time=start,
            end_time=end,
            stage_metrics=[stage1, stage2],
        )

        assert result.get_stage_duration("parallel_review") == 60000.0
        assert result.get_stage_duration("debate") == 120000.0
        assert result.get_stage_duration("nonexistent") is None

    def test_get_stage_breakdown(self):
        """测试：获取阶段耗时占比"""
        start = datetime(2026, 5, 16, 10, 0, 0)
        end = datetime(2026, 5, 16, 10, 10, 0)

        stage1 = StageMetrics(
            stage_name="parallel_review",
            start_time=start,
            end_time=start + timedelta(seconds=120),
        )
        stage2 = StageMetrics(
            stage_name="debate",
            start_time=start + timedelta(seconds=120),
            end_time=start + timedelta(seconds=360),
        )
        stage3 = StageMetrics(
            stage_name="merge",
            start_time=start + timedelta(seconds=360),
            end_time=start + timedelta(seconds=420),
        )

        result = PipelineResult(
            pipeline_id="test-003",
            start_time=start,
            end_time=end,
            stage_metrics=[stage1, stage2, stage3],
        )

        breakdown = result.get_stage_breakdown()

        assert breakdown["parallel_review"] == pytest.approx(20.0, rel=0.01)
        assert breakdown["debate"] == pytest.approx(40.0, rel=0.01)
        assert breakdown["merge"] == pytest.approx(10.0, rel=0.01)

    def test_to_dict(self):
        """测试：序列化为字典"""
        start = datetime(2026, 5, 16, 10, 0, 0)
        end = datetime(2026, 5, 16, 10, 5, 0)

        result = PipelineResult(
            pipeline_id="test-004",
            start_time=start,
            end_time=end,
            finding_recall=0.85,
            finding_precision=0.90,
            finding_f1=0.87,
        )

        data = result.to_dict()

        assert data["pipeline_id"] == "test-004"
        assert data["success"] is True
        assert data["quality"]["finding_recall"] == 0.85
        assert data["quality"]["finding_precision"] == 0.90


class TestPipelineMetrics:
    """测试 PipelineMetrics"""

    def test_record_result(self):
        """测试：记录结果"""
        metrics = PipelineMetrics()

        start = datetime(2026, 5, 16, 10, 0, 0)
        end = datetime(2026, 5, 16, 10, 5, 0)

        result = PipelineResult(
            pipeline_id="test-001",
            start_time=start,
            end_time=end,
        )

        metrics.record(result)

        assert len(metrics.results) == 1

    def test_calculate_stage_statistics(self):
        """测试：计算阶段统计"""
        metrics = PipelineMetrics()

        for i in range(3):
            start = datetime(2026, 5, 16, 10, i, 0)
            end = start + timedelta(minutes=5)

            stage = StageMetrics(
                stage_name="parallel_review",
                start_time=start,
                end_time=end,
            )

            result = PipelineResult(
                pipeline_id=f"test-{i:03d}",
                start_time=start,
                end_time=end,
                stage_metrics=[stage],
            )

            metrics.record(result)

        stats = metrics.calculate_stage_statistics()

        assert "parallel_review" in stats
        assert stats["parallel_review"]["count"] == 3
        assert stats["parallel_review"]["avg_ms"] == 300000.0

    def test_calculate_debate_statistics(self):
        """测试：计算辩论统计"""
        metrics = PipelineMetrics()

        for i in range(3):
            start = datetime(2026, 5, 16, 10, i, 0)
            end = start + timedelta(minutes=5)

            debate = DebateMetrics(
                total_findings=10 + i,
                total_rounds=20 + i * 5,
                confirmed_count=7 + i,
                dismissed_count=3 - i if i < 3 else 0,
            )
            debate.calculate_rates()

            result = PipelineResult(
                pipeline_id=f"test-{i:03d}",
                start_time=start,
                end_time=end,
                debate_metrics=debate,
            )

            metrics.record(result)

        stats = metrics.calculate_debate_statistics()

        assert stats["total_findings"] == 33
        assert "avg_rounds" in stats
        assert "avg_confirmation_rate" in stats

    def test_calculate_resource_statistics(self):
        """测试：计算资源统计"""
        metrics = PipelineMetrics()

        for i in range(3):
            start = datetime(2026, 5, 16, 10, i, 0)
            end = start + timedelta(minutes=5)

            resource = ResourceMetrics(
                total_llm_calls=10 + i * 2,
                total_tokens=1000 + i * 500,
            )
            resource.calculate_averages()

            result = PipelineResult(
                pipeline_id=f"test-{i:03d}",
                start_time=start,
                end_time=end,
                resource_metrics=resource,
            )

            metrics.record(result)

        stats = metrics.calculate_resource_statistics()

        assert stats["total_llm_calls"] == 36
        assert stats["total_tokens"] == 4500

    def test_calculate_quality_statistics(self):
        """测试：计算质量统计"""
        metrics = PipelineMetrics()

        for i in range(3):
            start = datetime(2026, 5, 16, 10, i, 0)
            end = start + timedelta(minutes=5)

            result = PipelineResult(
                pipeline_id=f"test-{i:03d}",
                start_time=start,
                end_time=end,
                finding_recall=0.80 + i * 0.05,
                finding_precision=0.85 + i * 0.03,
                finding_f1=0.82 + i * 0.04,
            )

            metrics.record(result)

        stats = metrics.calculate_quality_statistics()

        assert stats["avg_recall"] == pytest.approx(0.85, rel=0.01)
        assert stats["avg_precision"] == pytest.approx(0.88, rel=0.01)
        assert stats["success_rate"] == 1.0

    def test_calculate_latency_percentiles(self):
        """测试：计算延迟百分位数"""
        metrics = PipelineMetrics()

        durations = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

        for i, duration in enumerate(durations):
            start = datetime(2026, 5, 16, 10, i, 0)
            end = start + timedelta(milliseconds=duration)

            result = PipelineResult(
                pipeline_id=f"test-{i:03d}",
                start_time=start,
                end_time=end,
            )

            metrics.record(result)

        percentiles = metrics.calculate_latency_percentiles()

        assert percentiles["avg_ms"] == 550.0
        assert percentiles["min_ms"] == 100.0
        assert percentiles["max_ms"] == 1000.0
        assert "p50_ms" in percentiles
        assert "p95_ms" in percentiles
        assert "p99_ms" in percentiles

    def test_get_summary(self):
        """测试：获取汇总报告"""
        metrics = PipelineMetrics()

        for i in range(5):
            start = datetime(2026, 5, 16, 10, i, 0)
            end = start + timedelta(minutes=5)

            stage = StageMetrics(
                stage_name="parallel_review",
                start_time=start,
                end_time=end,
            )

            debate = DebateMetrics(
                total_findings=10,
                confirmed_count=7,
                dismissed_count=3,
            )
            debate.calculate_rates()

            resource = ResourceMetrics(
                total_llm_calls=10,
                total_tokens=1000,
            )

            result = PipelineResult(
                pipeline_id=f"test-{i:03d}",
                start_time=start,
                end_time=end,
                stage_metrics=[stage],
                debate_metrics=debate,
                resource_metrics=resource,
                finding_recall=0.85,
                finding_precision=0.90,
                finding_f1=0.87,
            )

            metrics.record(result)

        summary = metrics.get_summary()

        assert summary["total_runs"] == 5
        assert summary["successful_runs"] == 5
        assert summary["failed_runs"] == 0
        assert "latency" in summary
        assert "stages" in summary
        assert "debate" in summary
        assert "resources" in summary
        assert "quality" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
