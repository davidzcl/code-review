"""
评审者 Agent 模块

提供 Finding 数据结构和 ReviewerAgent 基类，用于代码审查。
ReviewerAgent 继承自 AgentScope 的 ReActAgent，封装了代码审查的标准化流程。
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator, ValidationError

from agentscope.agent import ReActAgent
from agentscope.formatter import FormatterBase
from agentscope.memory import InMemoryMemory
from agentscope.model import ChatModelBase
from agentscope.tool import Toolkit

from agents.base import AgentInitializationError
from agents.formatter_registry import create_formatter, infer_formatter_type
from agents.finding import Finding
from logger import logger
from tools.diff_parser import DiffChunk
from tools.pr_parser import PRContext

_reviewer_logger = logger.get_logger("agents.reviewer")

class ReviewReply(BaseModel):
    findings: List[Finding] = Field(description="评审发现列表")
    chunk_index: int = Field(description="当前处理的代码块索引", default=None)

class ReviewerAgent(ReActAgent):
    """代码评审者 Agent 基类。

    继承 AgentScope 的 ReActAgent，封装代码评审的标准化流程。
    每个评审者实例专注于一个评审维度（security、performance、logic、style）。

    参数:
        name: Agent 名称。
        role: 评审角色，如 security、performance、logic、style。
        sys_prompt: 系统提示词。
        model: 模型实例（来自 create_model）。
        formatter: 消息格式化器。
        toolkit: 工具集（可选）。
        memory: 记忆存储（可选，默认使用 InMemoryMemory）。
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
        memory: Optional[InMemoryMemory] = None,
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
        _reviewer_logger.info(
            "初始化评审者 Agent: name=%s role=%s model=%s",
            name, role, type(model).__name__,
        )

    @property
    def role(self) -> str:
        """获取评审角色。"""
        return self._role

    def _build_review_prompt(
        self,
        diff_chunks: List[DiffChunk],
        pr_context: PRContext,
    ) -> str:
        """构建评审提示词。

        将 diff 块和 PR 上下文组合成结构化的评审输入。

        Args:
            diff_chunks: Diff 块列表。
            pr_context: PR 上下文信息。

        Returns:
            格式化的评审提示词字符串。
        """
        lines: List[str] = []
        lines.append(f"## PR 信息")
        if pr_context:
            lines.append(f"- 标题: {pr_context.title}")
            lines.append(f"- 描述: {pr_context.description}")
            lines.append(f"- 作者: {pr_context.author}")
            lines.append(f"- 标签: {', '.join(pr_context.labels)}")
            lines.append(f"- 目标分支: {pr_context.base_branch}")
            lines.append(f"- 源分支: {pr_context.head_branch}")
            lines.append(f"- 变更概要: {pr_context.changed_files_summary}")
        else:
            lines.append(f"- 无 PR 信息")

        lines.append("")
        lines.append(f"## 代码变更 (共 {len(diff_chunks)} 个变更块)")
        lines.append("")

        for i, chunk in enumerate(diff_chunks):
            lines.append(f"### 变更块 {i + 1}: {chunk.file_path}")
            lines.append(f"- 语言: {chunk.language or '未知'}")
            if chunk.is_new_file:
                lines.append("- 状态: 新增文件")
            elif chunk.is_deleted_file:
                lines.append("- 状态: 删除文件")
            lines.append(
                f"- 行范围: {chunk.old_start}-{chunk.old_start + chunk.old_count}"
                f" → {chunk.new_start}-{chunk.new_start + chunk.new_count}"
            )
            lines.append(f"- 新增行: {len(chunk.additions)}")
            lines.append(f"- 删除行: {len(chunk.deletions)}")
            if chunk.additions:
                lines.append(f"  - 新增内容:")
                for line in chunk.additions:
                    lines.append(f"    + {line}")
            if chunk.deletions:
                lines.append(f"  - 删除内容:")
                for line in chunk.deletions:
                    lines.append(f"    - {line}")
            if chunk.context:
                lines.append(f"  - 上下文:")
                for ctx_line in chunk.context.split("\n"):
                    lines.append(f"    {ctx_line}")
            lines.append("")

        lines.append(
            "请从你的专业角度审查以上代码变更，"
            "识别潜在问题并以 JSON 格式输出评审发现列表。"
        )
        lines.append(
            "每个发现必须包含: "
            "severity(critical|important|minor), file_path, "
            "title, description, suggestion, confidence(0.0-1.0), "
            "evidence(string[], 引用变更中具体的代码行内容), "
            "chunk_index(integer, 可选, 对应上方「变更块 N」的序号)"
        )

        return "\n".join(lines)

    async def review(
        self,
        diff_chunks: List[DiffChunk],
        pr_context: PRContext,
    ) -> List[Finding]:
        """执行代码审查。

        Args:
            diff_chunks: Diff 块列表。
            pr_context: PR 上下文信息。

        Returns:
            Finding 列表，每个 finding 表示一个评审发现。
        """
        _reviewer_logger.info(
            "开始评审: reviewer=%s role=%s chunks=%d",
            self.name, self._role, len(diff_chunks),
        )

        if not diff_chunks:
            _reviewer_logger.warning("diff_chunks 为空，跳过评审")
            return []

        prompt = self._build_review_prompt(diff_chunks, pr_context)

        from agentscope.message import Msg

        msg = Msg(self.name, prompt, "user")
        reply = await self.reply(msg, structured_model=ReviewReply)

        findings = self._parse_findings(reply, diff_chunks)

        _reviewer_logger.info(
            "评审完成: reviewer=%s findings=%d",
            self.name, len(findings),
        )
        return findings
    
    def _resolve_line_range(
        self,
        file_path: str,
        chunk_index: Optional[int],
        diff_chunks: List[DiffChunk],
    ) -> Tuple[int, int]:
        """从 diff_chunks 中解析行号范围。

        策略:
            1. chunk_index 有效 → 直接取对应 chunk 范围
            2. chunk_index 缺失/无效 → 同 file_path 多 chunk 合并范围
            3. 无匹配 chunk → 返回 (0, 0)

        Args:
            file_path: LLM 输出的文件路径。
            chunk_index: LLM 输出的变更块序号（1-based, 可选）。
            diff_chunks: 完整 DiffChunk 列表。

        Returns:
            (line_start, line_end)，1-based 闭区间。
        """
        if not file_path or not diff_chunks:
            return (0, 0)

        # 1. chunk_index 优先（LLM 输出的序号为 1-based）
        if chunk_index is not None:
            try:
                idx = int(chunk_index) - 1
                if 0 <= idx < len(diff_chunks):
                    c = diff_chunks[idx]
                    if c.file_path == file_path:
                        return (c.new_start, c.new_start + c.new_count - 1)
            except (ValueError, TypeError):
                pass

        # 2. 退化: 同 file_path 多 chunk 合并
        matching = [c for c in diff_chunks if c.file_path == file_path]
        if not matching:
            return (0, 0)

        if len(matching) == 1:
            c = matching[0]
            return (c.new_start, c.new_start + c.new_count - 1)

        min_start = min(c.new_start for c in matching)
        max_end = max(c.new_start + c.new_count - 1 for c in matching)
        return (min_start, max_end)

    def _parse_findings(self, response: Any, diff_chunks: List[DiffChunk]) -> List[Finding]:
        """解析模型响应中的评审发现。

        从 Msg 对象中提取 Finding 列表。
        当模型输出 JSON 格式数据时进行解析。

        Args:
            response: 模型响应。

        Returns:
            解析后的 Finding 列表。
        """
        findings: List[Finding] = []
        
        if isinstance(response, ReviewReply):
            findings = list(response.findings)
            for f in findings:
                f.reviewer = self.name
                f.role = self._role
                resolved = self._resolve_line_range(f.file_path, f.chunk_index, diff_chunks)
                if resolved != (0, 0):
                    f.line_range = resolved
            return findings

        try:
            text = self._extract_text(response)
            if not text:
                return findings

            parsed = self._try_parse_json(text)
            if parsed is None:
                return findings

            if isinstance(parsed, dict):
                parsed = [parsed]

            for item in parsed:
                if not isinstance(item, dict):
                    continue
                try:
                    finding = Finding(
                        reviewer=self.name,
                        role=self._role,
                        severity=item.get("severity", "minor"),
                        file_path=item.get("file_path", ""),
                        line_range=(0, 0),
                        title=item.get("title", ""),
                        description=item.get("description", ""),
                        suggestion=item.get("suggestion", ""),
                        confidence=float(
                            item.get("confidence", 0.0)
                        ),
                        evidence=item.get("evidence", []),
                    )
                    
                    resolved_range = self._resolve_line_range(
                        file_path=finding.file_path,
                        chunk_index=item.get("chunk_index"),
                        diff_chunks=diff_chunks,
                    )
                    if resolved_range != (0, 0):
                        finding.line_range = resolved_range
                    
                    findings.append(finding)
                except (ValueError, TypeError, KeyError, ValidationError):
                    _reviewer_logger.warning(
                        "跳过无效的 finding 条目: %s", item,
                    )
                    continue
        except Exception:
            _reviewer_logger.warning(
                "解析 findings 失败", exc_info=True
            )

        return findings

    @staticmethod
    def _extract_text(response: Any) -> Optional[str]:
        """从模型响应中提取文本内容。

        Args:
            response: 模型响应对象。

        Returns:
            提取的文本字符串，失败时返回 None。
        """
        if response is None:
            return None

        if isinstance(response, str):
            return response

        if isinstance(response, dict):
            content = response.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                texts = [
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                if texts:
                    return "\n".join(texts)
            return None

        try:
            if hasattr(response, "get_text_content"):
                return response.get_text_content()
        except (AttributeError, KeyError, TypeError):
            pass

        try:
            if hasattr(response, "text"):
                return response.text
        except (AttributeError, KeyError, TypeError):
            pass

        return None

    @staticmethod
    def _try_parse_json(text: str) -> Optional[Any]:
        """尝试从文本中提取并解析 JSON。

        支持纯 JSON 字符串和代码块包裹的 JSON。

        Args:
            text: 可能包含 JSON 的文本。

        Returns:
            解析后的 Python 对象，失败时返回 None。
        """
        import json
        import re

        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        json_match = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?```",
            text,
            re.DOTALL,
        )
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        array_match = re.search(r"\[.*\]", text, re.DOTALL)
        if array_match:
            try:
                return json.loads(array_match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    async def reply(self, msg: Any = None, **kwargs: Any) -> Any:
        """带日志记录的回复方法。

        包装 AgentScope ReActAgent.reply，增加调用日志。

        Args:
            msg: 输入消息。
            **kwargs: 其他参数。

        Returns:
            模型回复。
        """
        _reviewer_logger.debug(
            "调用 reply: agent=%s", self.name,
        )
        return await super().reply(msg, **kwargs)
