"""
验证流程评测基准

测试目标：
1. PipelineBenchmark 初始化
2. 并行评审阶段评测
3. 辩论循环阶段评测
4. 合并阶段评测
5. 裁决阶段评测
6. 完整流程评测
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from evaluation.benchmark.pipeline_benchmark import (
    PipelineBenchmark,
    PipelineBenchmarkConfig,
    PipelineBenchmarkResult,
    run_pipeline_benchmark,
)
from tools.diff_parser import DiffChunk
from tools.pr_parser import PRContext
from agents.reviewer import Finding


class TestPipelineBenchmarkConfig:
    """测试 PipelineBenchmarkConfig"""

    def test_default_config(self):
        """测试：默认配置"""
        config = PipelineBenchmarkConfig()

        assert config.max_debate_rounds == 3
        assert config.confidence_threshold == 0.6
        assert config.merge_similarity_threshold == 0.8
        assert config.parallel_timeout == 300
        assert config.track_resources is True

    def test_custom_config(self):
        """测试：自定义配置"""
        config = PipelineBenchmarkConfig(
            max_debate_rounds=5,
            confidence_threshold=0.7,
            merge_similarity_threshold=0.9,
            parallel_timeout=600,
            track_resources=False,
        )

        assert config.max_debate_rounds == 5
        assert config.confidence_threshold == 0.7
        assert config.merge_similarity_threshold == 0.9
        assert config.parallel_timeout == 600
        assert config.track_resources is False


class TestPipelineBenchmarkResult:
    """测试 PipelineBenchmarkResult"""

    def test_init(self):
        """测试：初始化"""
        config = PipelineBenchmarkConfig()
        start = datetime.now()

        result = PipelineBenchmarkResult(
            pipeline_id="test-001",
            config=config,
            start_time=start,
        )

        assert result.pipeline_id == "test-001"
        assert result.config == config
        assert result.start_time == start
        assert result.end_time is None
        assert result.debate_records == []
        assert result.merge_records == []

    def test_to_dict(self):
        """测试：序列化"""
        config = PipelineBenchmarkConfig()
        start = datetime(2026, 5, 16, 10, 0, 0)
        end = datetime(2026, 5, 16, 10, 5, 0)

        result = PipelineBenchmarkResult(
            pipeline_id="test-002",
            config=config,
            start_time=start,
            end_time=end,
        )

        data = result.to_dict()

        assert data["pipeline_id"] == "test-002"
        assert "config" in data
        assert "timing" in data
        assert "summary" in data


class TestPipelineBenchmark:
    """测试 PipelineBenchmark"""

    @pytest.mark.asyncio
    async def test_init(self):
        """测试：初始化"""
        benchmark = PipelineBenchmark()

        assert benchmark.config is not None
        assert benchmark.metrics is not None
        assert benchmark.results == []

    @pytest.mark.asyncio
    async def test_init_with_config(self):
        """测试：带配置初始化"""
        config = PipelineBenchmarkConfig(max_debate_rounds=5)
        benchmark = PipelineBenchmark(config=config)

        assert benchmark.config.max_debate_rounds == 5

    @pytest.mark.asyncio
    async def test_run_pipeline_empty_diff(self):
        """测试：空 Diff 运行"""
        benchmark = PipelineBenchmark()

        mock_reviewer = MagicMock()
        mock_reviewer.name = "TestReviewer"
        mock_reviewer.review = AsyncMock(return_value=[])

        mock_prosecutor = MagicMock()
        mock_prosecutor.challenge = AsyncMock(return_value=MagicMock())

        mock_defender = MagicMock()
        mock_defender.defend = AsyncMock(return_value=MagicMock(stands=True))

        result = await benchmark.run_pipeline(
            reviewers=[mock_reviewer],
            prosecutor=mock_prosecutor,
            defender=mock_defender,
            diff_chunks=[],
            pr_context=PRContext(title="", description=""),
            diff_context="",
        )

        assert result is not None
        assert result.pipeline_id is not None
        assert result.parallel_review_result is not None
        assert len(result.parallel_review_result.findings) == 0

    @pytest.mark.asyncio
    async def test_run_pipeline_with_findings(self):
        """测试：带发现的运行"""
        benchmark = PipelineBenchmark()

        mock_finding = MagicMock(spec=Finding)
        mock_finding.id = "FIND-001"
        mock_finding.title = "Test Finding"
        mock_finding.severity = "high"
        mock_finding.category = "security"

        mock_reviewer = MagicMock()
        mock_reviewer.name = "TestReviewer"
        mock_reviewer.review = AsyncMock(return_value=[mock_finding])

        mock_challenge = MagicMock()
        mock_challenge.reasoning = "Test challenge"
        mock_challenge.confidence = 0.8

        mock_prosecutor = MagicMock()
        mock_prosecutor.challenge = AsyncMock(return_value=mock_challenge)

        mock_defense = MagicMock()
        mock_defense.stands = True
        mock_defense.reasoning = "Test defense"
        mock_defense.finding_stands = True
        mock_defense.revised_confidence = 0.9

        mock_defender = MagicMock()
        mock_defender.defend = AsyncMock(return_value=mock_defense)

        diff_chunk = DiffChunk(
            file_path="test.py",
            old_start=1,
            old_count=0,
            new_start=1,
            new_count=1,
            context="",
            additions=["print('hello')"],
            deletions=[],
        )

        result = await benchmark.run_pipeline(
            reviewers=[mock_reviewer],
            prosecutor=mock_prosecutor,
            defender=mock_defender,
            diff_chunks=[diff_chunk],
            pr_context=PRContext(title="Test PR", description="Test"),
            diff_context="test context",
        )

        assert result is not None
        assert result.parallel_review_result is not None
        assert len(result.parallel_review_result.findings) == 1
        assert len(result.debate_records) == 1
        assert result.verdict is not None

    @pytest.mark.asyncio
    async def test_run_pipeline_multiple_reviewers(self):
        """测试：多评审者运行"""
        benchmark = PipelineBenchmark()

        mock_finding1 = MagicMock(spec=Finding)
        mock_finding1.id = "FIND-001"
        mock_finding1.title = "Finding 1"
        mock_finding1.severity = "high"
        mock_finding1.category = "security"

        mock_finding2 = MagicMock(spec=Finding)
        mock_finding2.id = "FIND-002"
        mock_finding2.title = "Finding 2"
        mock_finding2.severity = "medium"
        mock_finding2.category = "performance"

        mock_reviewer1 = MagicMock()
        mock_reviewer1.name = "Reviewer1"
        mock_reviewer1.review = AsyncMock(return_value=[mock_finding1])

        mock_reviewer2 = MagicMock()
        mock_reviewer2.name = "Reviewer2"
        mock_reviewer2.review = AsyncMock(return_value=[mock_finding2])

        mock_prosecutor = MagicMock()
        mock_prosecutor.challenge = AsyncMock(return_value=MagicMock())

        mock_defender = MagicMock()
        mock_defender.defend = AsyncMock(return_value=MagicMock(stands=True))

        diff_chunk = DiffChunk(
            file_path="test.py",
            old_start=1,
            old_count=0,
            new_start=1,
            new_count=1,
            context="",
            additions=["print('hello')"],
            deletions=[],
        )

        result = await benchmark.run_pipeline(
            reviewers=[mock_reviewer1, mock_reviewer2],
            prosecutor=mock_prosecutor,
            defender=mock_defender,
            diff_chunks=[diff_chunk],
            pr_context=PRContext(title="", description=""),
            diff_context="",
        )

        assert result is not None
        assert result.parallel_review_result.total_reviewers == 2
        assert result.parallel_review_result.successful_reviewers == 2

    @pytest.mark.asyncio
    async def test_get_summary(self):
        """测试：获取汇总"""
        benchmark = PipelineBenchmark()

        mock_reviewer = MagicMock()
        mock_reviewer.name = "TestReviewer"
        mock_reviewer.review = AsyncMock(return_value=[])

        mock_prosecutor = MagicMock()
        mock_prosecutor.challenge = AsyncMock(return_value=MagicMock())

        mock_defender = MagicMock()
        mock_defender.defend = AsyncMock(return_value=MagicMock(stands=True))

        await benchmark.run_pipeline(
            reviewers=[mock_reviewer],
            prosecutor=mock_prosecutor,
            defender=mock_defender,
            diff_chunks=[],
            pr_context=PRContext(title="", description=""),
            diff_context="",
        )

        summary = benchmark.get_summary()

        assert summary is not None
        assert "total_runs" in summary
        assert summary["total_runs"] == 1

    @pytest.mark.asyncio
    async def test_extract_debate_metrics(self):
        """测试：提取辩论指标"""
        benchmark = PipelineBenchmark()

        from pipeline.debate_loop import DebateRecord, DebateRound

        records = [
            DebateRecord(
                finding_id="FIND-001",
                original_finding=MagicMock(),
                rounds=[DebateRound(round_number=1)],
                final_status="confirmed",
            ),
            DebateRecord(
                finding_id="FIND-002",
                original_finding=MagicMock(),
                rounds=[DebateRound(round_number=1), DebateRound(round_number=2)],
                final_status="dismissed",
            ),
        ]

        metrics = benchmark._extract_debate_metrics(records)

        assert metrics.total_findings == 2
        assert metrics.total_rounds == 3
        assert metrics.confirmed_count == 1
        assert metrics.dismissed_count == 1
        assert metrics.confirmation_rate == 0.5

    @pytest.mark.asyncio
    async def test_extract_merge_metrics(self):
        """测试：提取合并指标"""
        benchmark = PipelineBenchmark()

        from pipeline.issue_merger import MergeRecord
        from pipeline.debate_loop import DebateRecord

        merge_records = [
            MergeRecord(
                primary_id="FIND-001",
                merged_ids=["FIND-002", "FIND-003"],
                merge_reason="Similar findings",
                merged_finding=MagicMock(),
            ),
        ]

        debate_records = [
            DebateRecord(
                finding_id="FIND-001",
                original_finding=MagicMock(),
                final_status="confirmed",
            ),
            DebateRecord(
                finding_id="FIND-002",
                original_finding=MagicMock(),
                final_status="confirmed",
            ),
            DebateRecord(
                finding_id="FIND-003",
                original_finding=MagicMock(),
                final_status="confirmed",
            ),
        ]

        metrics = benchmark._extract_merge_metrics(merge_records, debate_records)

        assert metrics.total_findings == 3
        assert metrics.merged_groups == 1
        assert metrics.total_merged == 2


class TestRunPipelineBenchmark:
    """测试同步运行函数"""

    def test_run_pipeline_benchmark_sync(self):
        """测试：同步运行"""
        mock_reviewer = MagicMock()
        mock_reviewer.name = "TestReviewer"
        mock_reviewer.review = AsyncMock(return_value=[])

        mock_prosecutor = MagicMock()
        mock_prosecutor.challenge = AsyncMock(return_value=MagicMock())

        mock_defender = MagicMock()
        mock_defender.defend = AsyncMock(return_value=MagicMock(stands=True))

        result = run_pipeline_benchmark(
            reviewers=[mock_reviewer],
            prosecutor=mock_prosecutor,
            defender=mock_defender,
            diff_chunks=[],
            pr_context=PRContext(title="", description=""),
            diff_context="",
        )

        assert result is not None
        assert result.pipeline_id is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
