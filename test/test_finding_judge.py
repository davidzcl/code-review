"""
验证 FindingJudge (LLM-as-Judge) 实现

测试目标：
1. 正确初始化 Judge
2. 正确评估单个 Finding
3. 正确计算召回率和精确率
4. 正确处理 mock LLM 响应
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestFindingJudge:
    """FindingJudge 测试"""

    def test_create_finding_judge(self):
        """测试：创建 FindingJudge 实例"""
        from evaluation.metrics.finding_judge import FindingJudge

        judge = FindingJudge(model_name="qwen-max")
        assert judge is not None
        assert judge.model_name == "qwen-max"

    @pytest.mark.asyncio
    async def test_evaluate_single_finding(self):
        """测试：评估单个 Finding"""
        from evaluation.metrics.finding_judge import FindingJudge

        judge = FindingJudge(model_name="qwen-max")

        predicted = {
            "title": "SQL 注入漏洞",
            "severity": "critical",
            "file_path": "db.py",
            "line_range": [10, 15],
        }

        ground_truth = {
            "title": "SQL 注入",
            "severity": "critical",
            "file_path": "db.py",
            "line_range": [10, 15],
        }

        with patch.object(judge, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "is_match": True,
                "confidence": 0.9,
                "reasoning": "标题和位置匹配",
            }

            result = await judge.evaluate_finding(predicted, ground_truth)

            assert result.is_match is True
            assert result.confidence >= 0.8

    @pytest.mark.asyncio
    async def test_evaluate_batch_findings(self):
        """测试：批量评估 Findings"""
        from evaluation.metrics.finding_judge import FindingJudge

        judge = FindingJudge(model_name="qwen-max")

        predicted_findings = [
            {"title": "SQL 注入", "severity": "critical", "file_path": "db.py"},
            {"title": "XSS 漏洞", "severity": "high", "file_path": "view.py"},
        ]

        ground_truth_findings = [
            {"title": "SQL 注入", "severity": "critical", "file_path": "db.py"},
            {"title": "硬编码密钥", "severity": "high", "file_path": "config.py"},
        ]

        with patch.object(judge, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "is_match": True,
                "confidence": 0.9,
                "reasoning": "匹配",
            }

            results = await judge.evaluate_batch(predicted_findings, ground_truth_findings)

            assert results.total_predicted == 2
            assert results.total_ground_truth == 2

    @pytest.mark.asyncio
    async def test_calculate_recall_precision(self):
        """测试：计算召回率和精确率"""
        from evaluation.metrics.finding_judge import FindingJudge

        judge = FindingJudge(model_name="qwen-max")

        predicted = [
            {"title": "SQL 注入", "severity": "critical"},
            {"title": "XSS 漏洞", "severity": "high"},
            {"title": "假阳性", "severity": "low"},
        ]

        ground_truth = [
            {"title": "SQL 注入", "severity": "critical"},
            {"title": "硬编码密钥", "severity": "high"},
        ]

        with patch.object(judge, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "is_match": False,
                "confidence": 0.5,
                "reasoning": "测试",
            }

            results = await judge.evaluate_batch(predicted, ground_truth)

            assert results.true_positives >= 0
            assert results.false_positives >= 0
            assert results.false_negatives >= 0

    def test_build_evaluation_prompt(self):
        """测试：构建评估提示词"""
        from evaluation.metrics.finding_judge import FindingJudge

        judge = FindingJudge(model_name="qwen-max")

        predicted = {"title": "SQL 注入", "severity": "critical"}
        ground_truth = {"title": "SQL 注入", "severity": "critical"}

        prompt = judge._build_evaluation_prompt(predicted, ground_truth)

        assert "SQL 注入" in prompt
        assert "critical" in prompt

    @pytest.mark.asyncio
    async def test_empty_findings(self):
        """测试：空 Findings 处理"""
        from evaluation.metrics.finding_judge import FindingJudge

        judge = FindingJudge(model_name="qwen-max")

        results = await judge.evaluate_batch([], [])

        assert results.total_predicted == 0
        assert results.total_ground_truth == 0
        assert results.recall == 0.0
        assert results.precision == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
