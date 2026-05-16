"""
质疑者 Agent 模块

对评审发现提出质疑，验证其有效性。
"""

from __future__ import annotations

from typing import Any, List, Optional
import uuid

from pydantic import BaseModel, Field

from agentscope.message import Msg
from agentscope.agent import ReActAgent
from agentscope.model import ChatModelBase
from agentscope.formatter import FormatterBase
from agentscope.tool import Toolkit
from agentscope.memory import MemoryBase, InMemoryMemory

from agents.base import AgentInitializationError

from agents.formatter_registry import create_formatter, infer_formatter_type
from agents.reviewer import Finding
from logger import logger

_prosecutor_logger = logger.get_logger("agents.prosecutor")

class ChallengeReply(BaseModel):
    """质疑回复的数据结构。"""
    is_valid: bool = Field(default=True, description="是否有效")
    reasons: List[str] = Field(default_factory=list, description="质疑理由")
    confidence: float = Field(default=0.0, description="置信度")

class Challenge(BaseModel):
    """质疑结果的数据结构。"""

    finding_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reply: ChallengeReply = Field(default_factory=ChallengeReply)


class ProsecutorAgent(ReActAgent):
    """质疑者 Agent。

    对评审发现提出质疑，验证其有效性。

    参数:
        name: Agent 名称。
        model: 模型实例。
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

        _prosecutor_logger.info(
            "初始化质疑者 Agent: name=%s role=%s model=%s",
            name, role, type(model).__name__,
        )

    @property
    def role(self) -> str:
        """获取评审角色。"""
        return self._role

    async def challenge(self, finding: Finding) -> Challenge:
        """对指定的评审发现提出质疑。

        基于 LLM 判断发现的真实性、准确性，生成质疑理由和置信度。

        Args:
            finding: 待质疑的评审发现。

        Returns:
            Challenge 对象，包含质疑结果。
        """
        _prosecutor_logger.info(
            "质疑开始: finding_id=%s title=%s",
            finding.id, finding.title,
        )

        prompt = self._build_challenge_prompt(finding)
        msg = Msg(self.name, prompt, "user")

        try:
            response = await self.reply(msg, structured_model=ChallengeReply)
            
            _prosecutor_logger.info(
                "Prosecutor 输出: %s",
                response,
                )
            
            metadata = response.metadata or {}
            challenge = Challenge(
                finding_id=finding.id,
                reply=ChallengeReply(
                    **{k: v for k, v in metadata.items() if k in ("is_valid", "reasons", "confidence")}
                ),
            )

            _prosecutor_logger.info(
                "质疑完成: finding_id=%s is_valid=%s confidence=%.2f",
                finding.id, challenge.reply.is_valid, challenge.reply.confidence,
            )
            return challenge
        except Exception:
            _prosecutor_logger.warning(
                "质疑失败，返回默认质疑: finding_id=%s",
                finding.id, exc_info=True,
            )
            return Challenge(
                finding_id=finding.id,
                is_valid=True,
                reasons=["质疑者处理异常，默认认定发现有效"],
                confidence=0.5,
            )

    def _build_challenge_prompt(self, finding: Finding) -> str:
        """构建质疑提示词。"""
        lines: List[str] = []
        lines.append("你是一位严谨的代码审查质疑者。")
        lines.append("你的任务是对以下评审发现提出质疑，验证其是否真实有效。")
        lines.append("")
        lines.append("## 待质疑的评审发现")
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
        lines.append(
            "请从以下角度分析发现的合理性："
            "1) 是否存在误报（false positive）？"
            "2) 证据链是否完整？"
            "3) 严重级别是否合理？"
        )
        return "\n".join(lines)
