"""
AI 质量评估模块

对评审报告（Verdict）进行质量评估，输出评分和改进建议。
作为可选模块运行，不影响主评审流程。
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from agentscope.message import Msg
from agentscope.agent import ReActAgent
from agentscope.model import ChatModelBase
from agentscope.formatter import FormatterBase
from agentscope.tool import Toolkit
from agentscope.memory import InMemoryMemory

from agents.base import AgentInitializationError
from agents.formatter_registry import create_formatter, infer_formatter_type
from pipeline.verdict import Verdict
from tools.pr_parser import PRContext
from logger import logger

_evaluator_logger = logger.get_logger("agents.evaluator")


class EvaluationResult(BaseModel):
    """质量评估结果。

    从覆盖率、清晰度、可操作性三个维度评估评审质量。
    """

    score: float = Field(default=0.0, ge=0.0, le=1.0)
    coverage_score: float = Field(default=0.0, ge=0.0, le=1.0)
    clarity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    actionability_score: float = Field(default=0.0, ge=0.0, le=1.0)
    summary: str = ""
    improvement_suggestions: List[str] = Field(default_factory=list)


_EVALUATOR_SYS_PROMPT = """你是一位评审质量评估专家。对代码评审报告的质量进行评估。

请从以下三个维度打分（0.0 ~ 1.0）：
1. **覆盖率**（coverage_score）：评审是否覆盖了安全、性能、逻辑、风格等多个维度
2. **清晰度**（clarity_score）：问题描述是否具体、有明确的文件路径和行号引用
3. **可操作性**（actionability_score）：修复建议是否具体可行

同时给出总体评分 score 和改进建议 improvement_suggestions。

各维度权重：覆盖率 0.30、清晰度 0.40、可操作性 0.30。
总体评分 = 覆盖率 × 0.30 + 清晰度 × 0.40 + 可操作性 × 0.30。"""


class EvaluatorAgent(ReActAgent):
    """评审质量评估 Agent。

    对最终裁决结果进行质量评估，输出评分和改进建议。

    参数:
        name: Agent 名称。
        sys_prompt: 系统提示词（可选，有默认值）。
        model: 模型实例。
        formatter: 消息格式化器。
        toolkit: 工具集（可选）。
        memory: 记忆存储（可选）。
        max_iters: 最大迭代次数（默认 10）。
    """

    def __init__(
        self,
        name: str,
        model: ChatModelBase,
        formatter: Optional[FormatterBase] = None,
        sys_prompt: str = "",
        toolkit: Toolkit | None = None,
        memory: InMemoryMemory | None = None,
        max_iters: int = 10,
    ) -> None:
        if not name or not name.strip():
            raise AgentInitializationError("name 不能为空")
        if not isinstance(model, ChatModelBase):
            raise AgentInitializationError(
                f"model 必须是 ChatModelBase 实例，收到: {type(model)}"
            )

        final_sys_prompt = sys_prompt or _EVALUATOR_SYS_PROMPT

        super().__init__(
            name=name,
            sys_prompt=final_sys_prompt,
            model=model,
            formatter=formatter or create_formatter(infer_formatter_type(model)),
            toolkit=toolkit or Toolkit(),
            memory=memory or InMemoryMemory(),
            max_iters=max_iters,
        )

        self._role = "evaluator"
        _evaluator_logger.info(
            "初始化 EvaluatorAgent: name=%s", name,
        )

    @property
    def role(self) -> str:
        return self._role

    async def evaluate(
        self,
        verdict: Verdict,
        pr_context: PRContext,
    ) -> EvaluationResult:
        """对评审报告进行质量评估。

        Args:
            verdict: 最终裁决结果。
            pr_context: PR 上下文信息。

        Returns:
            质量评估结果。
        """
        _evaluator_logger.info(
            "开始评估: findings=%d dismissed=%d",
            len(verdict.findings), len(verdict.dismissed),
        )

        prompt = self._build_eval_prompt(verdict, pr_context)
        msg = Msg(self.name, prompt, "user")
        reply = await self.reply(msg, structured_model=EvaluationResult)

        result = self._parse_result(reply, verdict)

        _evaluator_logger.info(
            "评估完成: score=%.2f coverage=%.2f clarity=%.2f actionability=%.2f",
            result.score, result.coverage_score,
            result.clarity_score, result.actionability_score,
        )
        return result

    def _build_eval_prompt(
        self,
        verdict: Verdict,
        pr_context: PRContext,
    ) -> str:
        lines: List[str] = []
        lines.append("## PR 信息")
        lines.append(f"标题: {pr_context.title or '未命名'}")
        lines.append(f"作者: {pr_context.author or '未知'}")
        lines.append("")

        lines.append("## 评审结果")
        lines.append(f"总结: {verdict.summary}")
        lines.append(f"发现数量: {len(verdict.findings)}")
        lines.append(f"驳回数量: {len(verdict.dismissed)}")
        lines.append(f"合并数量: {len(verdict.merged)}")
        lines.append("")

        if verdict.findings:
            lines.append("## 发现的详细列表")
            for f in verdict.findings:
                lines.append(
                    f"- [{f.severity}] {f.file_path}:{f.line_range} "
                    f"{f.title} (reviewer={f.reviewer}, role={f.role})"
                )
            lines.append("")

        lines.append("## 评估要求")
        lines.append(
            "请从覆盖率、清晰度、可操作性三个维度打分（0.0~1.0），"
            "给出总体评分和改进建议。"
        )
        return "\n".join(lines)

    def _parse_result(
        self,
        reply: Msg,
        verdict: Verdict,
    ) -> EvaluationResult:
        metadata = reply.metadata or {}
        try:
            return EvaluationResult(
                **{k: v for k, v in metadata.items()
                   if k in EvaluationResult.model_fields},
            )
        except Exception:
            _evaluator_logger.warning(
                "structured_model 解析失败，使用回退评估",
            )
            return self._fallback_evaluation(verdict)

    def _fallback_evaluation(self, verdict: Verdict) -> EvaluationResult:
        total = len(verdict.findings)
        if total == 0:
            return EvaluationResult(
                score=0.5, coverage_score=0.0,
                clarity_score=0.0, actionability_score=0.0,
                summary="未发现任何问题",
                improvement_suggestions=["评审未覆盖任何代码问题"],
            )

        roles = set(f.role for f in verdict.findings if f.role)
        coverage = min(1.0, len(roles) / 4.0)

        files_with_lines = sum(
            1 for f in verdict.findings
            if f.file_path and f.line_range != (0, 0)
        )
        clarity = files_with_lines / total if total > 0 else 0.0

        actionability = 0.0
        if total > 0:
            actionability = sum(
                1 for f in verdict.findings if f.suggestion
            ) / total

        score = coverage * 0.30 + clarity * 0.40 + actionability * 0.30

        suggestions = []
        if coverage < 0.5:
            suggestions.append("评审维度覆盖不足")
        if clarity < 0.5:
            suggestions.append("部分问题缺少文件路径或行号引用")
        if actionability < 0.5:
            suggestions.append("部分建议不够具体")

        return EvaluationResult(
            score=round(score, 4),
            coverage_score=round(coverage, 4),
            clarity_score=round(clarity, 4),
            actionability_score=round(actionability, 4),
            summary=f"回退评估: {total} 个发现",
            improvement_suggestions=suggestions,
        )