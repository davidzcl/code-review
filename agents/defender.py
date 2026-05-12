"""
辩护者 Agent 模块

针对质疑为评审发现进行辩护，提供反证。
"""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field

from agentscope.message import Msg
from agentscope.agent import ReActAgent
from agentscope.model import ChatModelBase
from agentscope.formatter import FormatterBase
from agentscope.tool import Toolkit
from agentscope.memory import MemoryBase, InMemoryMemory

from agents.base import AgentInitializationError
from agents.prosecutor import Challenge
from agents.reviewer import Finding
from agents.formatter_registry import create_formatter, infer_formatter_type
from logger import logger

_defender_logger = logger.get_logger("agents.defender")

class DefenseReply(BaseModel):
    """辩护回复的数据结构。"""
    finding_stands: bool = Field(default=True, description="是否支持该发现")
    counter_evidence: List[str] = Field(default_factory=list, description="反证证据")
    revised_severity: Optional[str] = Field(default=None, description="修订后的严重程度")
    revised_confidence: Optional[float] = Field(default=None, description="修订置信度")

class Defense(BaseModel):
    """辩护结果的数据结构。"""

    finding_id: str = ""
    challenge_id: str = ""
    reply: DefenseReply = Field(default_factory=DefenseReply)


class DefenderAgent(ReActAgent):
    """辩护者 Agent。

    针对质疑为评审发现进行辩护，提供反证。

    参数:
        name: Agent 名称。
        role: 评审角色。
        sys_prompt: 系统提示词。
        model: 模型实例。
        formatter: 消息格式化器。
        toolkit: 工具集（可选）。
        memory: 记忆存储（可选）。
        max_iters: 最大推理-行动迭代次数（默认 10）。
    """

    def __init__(
        self,
        name: str,
        role: str,
        sys_prompt: str,
        model: ChatModelBase,
        formatter: Optional[FormatterBase] = None,
        toolkit: Optional[Toolkit] = None,
        memory: Optional[MemoryBase] = None,
        max_iters: int = 10,
    ) -> None:
        if not name or not name.strip():
            raise AgentInitializationError("name 不能为空")
        if not sys_prompt or not sys_prompt.strip():
            raise AgentInitializationError("sys_prompt 不能为空")
        if not isinstance(model, ChatModelBase):
            raise AgentInitializationError(
                f"model 必须是 ChatModelBase 实例，收到: {type(model)}"
            )

        super().__init__(
            name=name,
            sys_prompt=sys_prompt,
            model=model,
            formatter=formatter or create_formatter(infer_formatter_type(model)),
            toolkit=toolkit or Toolkit(),
            memory=memory or InMemoryMemory(),
            max_iters=max_iters,
        )

        self._role = role
        _defender_logger.info(
            "初始化辩护者 Agent: name=%s role=%s model=%s",
            name, role, type(model).__name__,
        )

    @property
    def role(self) -> str:
        """获取评审角色。"""
        return self._role

    async def reply(self, msg: Any = None, **kwargs: Any) -> Any:
        """带日志记录的回复方法。

        包装 AgentScope ReActAgent.reply，增加调用日志。

        Args:
            msg: 输入消息。
            **kwargs: 其他参数。

        Returns:
            模型回复。
        """
        _defender_logger.debug(
            "调用 reply: agent=%s", self.name,
        )
        return await super().reply(msg, **kwargs)

    async def defend(
        self,
        finding: Finding,
        challenge: Challenge,
        diff_context: str,
    ) -> Defense:
        """针对质疑进行辩护。

        接收评审发现和质疑内容，结合代码上下文进行辩护。

        Args:
            finding: 原始评审发现。
            challenge: 质疑结果。
            diff_context: 相关代码变更上下文。

        Returns:
            Defense 对象，包含辩护结果。
        """
        _defender_logger.info(
            "辩护开始: finding_id=%s challenge_id=%s",
            finding.id, challenge.finding_id,
        )

        prompt = self._build_defense_prompt(finding, challenge, diff_context)
        msg = Msg(self.name, prompt, "user")

        try:
            response = await self.reply(msg, structured_model=DefenseReply)
            metadata = response.metadata or {}
            defense = Defense(
                finding_id=finding.id,
                challenge_id=challenge.finding_id,
                reply=DefenseReply(
                    **{k: v for k, v in metadata.items()
                       if k in ("finding_stands", "counter_evidence",
                            "revised_severity", "revised_confidence")}
                ),
            )

            _defender_logger.info(
                "辩护完成: finding_id=%s stands=%s",
                finding.id, defense.reply.finding_stands,
            )
            return defense
        except Exception:
            _defender_logger.warning(
                "辩护失败，默认认定发现成立: finding_id=%s",
                finding.id, exc_info=True,
            )
            return Defense(
                finding_id=finding.id,
                challenge_id=challenge.finding_id,
                reply=DefenseReply(
                    finding_stands=True,
                    counter_evidence=["辩护者处理异常，默认认定发现成立"],
                ),
            )

    def _build_defense_prompt(
        self,
        finding: Finding,
        challenge: Challenge,
        diff_context: str,
    ) -> str:
        """构建辩护提示词。"""
        lines: List[str] = []
        lines.append("你是一位代码审查辩护者。")
        lines.append("你的任务是为评审发现进行辩护，反驳不合理的质疑。")
        lines.append("")
        lines.append("## 原始评审发现")
        lines.append(f"- 评审者: {finding.reviewer}")
        lines.append(f"- 维度: {finding.role}")
        lines.append(f"- 严重级别: {finding.severity}")
        if finding.file_path:
            lines.append(f"- 文件: {finding.file_path}")
            lines.append(
                f"- 行范围: {finding.line_range[0]}-{finding.line_range[1]}"
            )
        lines.append(f"- 标题: {finding.title}")
        if finding.description:
            lines.append(f"- 描述: {finding.description}")
        if finding.suggestion:
            lines.append(f"- 建议: {finding.suggestion}")
        if finding.evidence:
            lines.append(f"- 证据:")
            for e in finding.evidence:
                lines.append(f"  - {e}")
        lines.append("")
        lines.append("## 质疑内容")
        lines.append(f"- 质疑成立: {challenge.is_valid}")
        if challenge.reasons:
            lines.append(f"- 质疑理由:")
            for r in challenge.reasons:
                lines.append(f"  - {r}")
        lines.append(f"- 质疑置信度: {challenge.confidence}")
        lines.append("")
        lines.append("## 代码变更上下文")
        lines.append(diff_context or "（无上下文）")
        lines.append("")
        lines.append(
            "请结合代码上下文判断发现是否成立，给出辩护理由。"
        )
        return "\n".join(lines)


