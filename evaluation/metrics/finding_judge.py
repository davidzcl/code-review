"""
FindingJudge (LLM-as-Judge) 评测指标

使用 LLM 作为裁判，评估智能体输出的 Finding 质量。
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from agents.model_registry import create_model

class FindingJudgeReply(BaseModel):
    """Finding 评测裁判回复"""

    is_match: bool = Field(default=False, description="是否匹配")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="匹配置信度")
    reasoning: str = Field(default="", description="匹配理由")


@dataclass
class FindingMatchResult:
    """Finding 匹配结果"""

    is_match: bool
    confidence: float
    reasoning: str
    predicted_finding: Dict[str, Any] = field(default_factory=dict)
    ground_truth_finding: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchEvaluationResult:
    """批量评估结果"""

    total_predicted: int = 0
    total_ground_truth: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    recall: float = 0.0
    precision: float = 0.0
    f1_score: float = 0.0
    match_details: List[FindingMatchResult] = field(default_factory=list)


class FindingJudge:
    """Finding 评测裁判

    使用 LLM 评估智能体输出的 Finding 与 Ground Truth 的匹配程度。
    """

    def __init__(self, model_name: str = "qwen3.6-flash"):
        self.model_name = model_name
        self._llm_client = create_model({"model_name": model_name, "model_type": "dashscope", "temperature": 0.7})

    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """调用 LLM 进行评估

        Args:
            prompt: 评估提示词

        Returns:
            LLM 返回的评估结果
        """
        if self._llm_client is None:
            return {
                "is_match": False,
                "confidence": 0.0,
                "reasoning": "LLM client not initialized",
            }

        response = await self._llm_client.chat(prompt)
        return self._parse_llm_response(response)

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 响应

        Args:
            response: LLM 原始响应

        Returns:
            解析后的字典
        """
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "is_match": False,
                "confidence": 0.0,
                "reasoning": "Failed to parse LLM response",
            }

    def _build_evaluation_prompt(
        self,
        predicted: Dict[str, Any],
        ground_truth: Dict[str, Any],
    ) -> str:
        """构建评估提示词

        Args:
            predicted: 预测的 Finding
            ground_truth: Ground Truth Finding

        Returns:
            评估提示词
        """
        prompt = f"""你是一个代码审查专家，请评估以下两个 Finding 是否匹配。

预测的 Finding:
- 标题: {predicted.get('title', 'N/A')}
- 严重级别: {predicted.get('severity', 'N/A')}
- 文件路径: {predicted.get('file_path', 'N/A')}
- 行号范围: {predicted.get('line_range', 'N/A')}

Ground Truth Finding:
- 标题: {ground_truth.get('title', 'N/A')}
- 严重级别: {ground_truth.get('severity', 'N/A')}
- 文件路径: {ground_truth.get('file_path', 'N/A')}
- 行号范围: {ground_truth.get('line_range', 'N/A')}

请判断这两个 Finding 是否描述的是同一个问题。考虑以下因素：
1. 标题是否描述相同的问题类型
2. 严重级别是否一致
3. 文件路径是否匹配
4. 行号范围是否有重叠

请以 JSON 格式返回结果：
{{
    "is_match": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "判断理由"
}}
"""
        return prompt

    async def evaluate_finding(
        self,
        predicted: Dict[str, Any],
        ground_truth: Dict[str, Any],
    ) -> FindingMatchResult:
        """评估单个 Finding

        Args:
            predicted: 预测的 Finding
            ground_truth: Ground Truth Finding

        Returns:
            匹配结果
        """
        prompt = self._build_evaluation_prompt(predicted, ground_truth)
        llm_result = await self._call_llm(prompt)

        return FindingMatchResult(
            is_match=llm_result.get("is_match", False),
            confidence=llm_result.get("confidence", 0.0),
            reasoning=llm_result.get("reasoning", ""),
            predicted_finding=predicted,
            ground_truth_finding=ground_truth,
        )

    async def evaluate_batch(
        self,
        predicted_findings: List[Dict[str, Any]],
        ground_truth_findings: List[Dict[str, Any]],
    ) -> BatchEvaluationResult:
        """批量评估 Findings

        Args:
            predicted_findings: 预测的 Finding 列表
            ground_truth_findings: Ground Truth Finding 列表

        Returns:
            批量评估结果
        """
        if not predicted_findings and not ground_truth_findings:
            return BatchEvaluationResult()

        match_results: List[FindingMatchResult] = []
        matched_ground_truth: set = set()

        for pred in predicted_findings:
            best_match: Optional[FindingMatchResult] = None
            best_idx = -1

            for idx, gt in enumerate(ground_truth_findings):
                if idx in matched_ground_truth:
                    continue

                result = await self.evaluate_finding(pred, gt)
                if result.is_match:
                    if best_match is None or result.confidence > best_match.confidence:
                        best_match = result
                        best_idx = idx

            if best_match:
                match_results.append(best_match)
                matched_ground_truth.add(best_idx)
            else:
                match_results.append(
                    FindingMatchResult(
                        is_match=False,
                        confidence=0.0,
                        reasoning="No matching ground truth found",
                        predicted_finding=pred,
                    )
                )

        true_positives = sum(1 for r in match_results if r.is_match)
        false_positives = len(predicted_findings) - true_positives
        false_negatives = len(ground_truth_findings) - true_positives

        recall = true_positives / len(ground_truth_findings) if ground_truth_findings else 0.0
        precision = true_positives / len(predicted_findings) if predicted_findings else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return BatchEvaluationResult(
            total_predicted=len(predicted_findings),
            total_ground_truth=len(ground_truth_findings),
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            recall=recall,
            precision=precision,
            f1_score=f1,
            match_details=match_results,
        )
