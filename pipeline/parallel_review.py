"""
多评审者并行调度模块

协调多个 ReviewerAgent 实例并行执行代码审查，
收集和汇总各维度的评审发现。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from logger import logger
from tools.diff_parser import DiffChunk
from tools.pr_parser import PRContext
from agents.reviewer import Finding

_parallel_logger = logger.get_logger("pipeline.parallel_review")


@dataclass
class ParallelReviewResult:
    """并行评审结果的数据结构。

    包含汇总的发现列表和各评审者的独立结果。
    """

    findings: List[Finding] = field(default_factory=list)
    """合并后的全部发现列表。"""

    reviewer_results: Dict[str, List[Finding]] = field(default_factory=dict)
    """按评审者名称分组的发现。"""

    total_reviewers: int = 0
    """参与的评审者总数。"""

    successful_reviewers: int = 0
    """成功完成评审的评审者数。"""

    failed_reviewers: List[str] = field(default_factory=list)
    """执行失败的评审者名称列表。"""


class ParallelReviewManager:
    """多评审者并行调度管理器。

    协调多个 ReviewerAgent 实例并行执行代码审查，
    使用 asyncio.gather 并发调用各评审者的 review() 方法。

    参数:
        reviewers: ReviewerAgent 实例列表。
        timeout: 单个评审者的超时秒数（默认 300）。
    """

    def __init__(
        self,
        reviewers: List[Any],
        timeout: int = 300,
    ) -> None:
        if not reviewers:
            raise ValueError("reviewers 列表不能为空")

        self._reviewers = list(reviewers)
        self._timeout = timeout
        self._result: Optional[ParallelReviewResult] = None

        _parallel_logger.info(
            "初始化 ParallelReviewManager: reviewers=%d timeout=%d",
            len(self._reviewers), self._timeout,
        )

    @property
    def reviewers(self) -> List[Any]:
        """获取注册的评审者列表。"""
        return list(self._reviewers)

    @property
    def result(self) -> Optional[ParallelReviewResult]:
        """获取最近一次 run_all 的结果。"""
        return self._result

    async def run_all(
        self,
        diff_chunks: List[DiffChunk],
        pr_context: PRContext,
    ) -> ParallelReviewResult:
        """并行执行所有评审者的 review 方法。

        使用 asyncio.gather 并发调度，每个评审者独立运行。
        任一评审者失败不影响其他评审者的执行。

        Args:
            diff_chunks: Diff 块列表。
            pr_context: PR 上下文信息。

        Returns:
            ParallelReviewResult，包含汇总和分组的发现。
        """
        _parallel_logger.info(
            "并行评审开始: reviewers=%d chunks=%d",
            len(self._reviewers), len(diff_chunks),
        )

        if not diff_chunks:
            _parallel_logger.warning("diff_chunks 为空，跳过并行评审")
            empty = ParallelReviewResult(
                total_reviewers=len(self._reviewers),
            )
            self._result = empty
            return empty

        reviewer_results: Dict[str, List[Finding]] = {}
        failed_reviewers: List[str] = []

        async def _run_single(reviewer: Any) -> tuple[str, List[Finding], bool]:
            name = getattr(reviewer, "name", str(reviewer))
            try:
                findings = await asyncio.wait_for(
                    reviewer.review(diff_chunks, pr_context),
                    timeout=self._timeout,
                )
                _parallel_logger.info(
                    "评审者完成: name=%s findings=%d",
                    name, len(findings),
                )
                return name, findings, True
            except asyncio.TimeoutError:
                _parallel_logger.warning(
                    "评审者超时: name=%s timeout=%d",
                    name, self._timeout,
                )
                return name, [], False
            except Exception:
                _parallel_logger.warning(
                    "评审者失败: name=%s", name, exc_info=True,
                )
                return name, [], False

        tasks = [_run_single(r) for r in self._reviewers]
        results = await asyncio.gather(*tasks)

        all_findings: List[Finding] = []
        for name, findings, success in results:
            reviewer_results[name] = findings
            all_findings.extend(findings)
            if not success:
                failed_reviewers.append(name)

        successful = len(self._reviewers) - len(failed_reviewers)

        self._result = ParallelReviewResult(
            findings=all_findings,
            reviewer_results=reviewer_results,
            total_reviewers=len(self._reviewers),
            successful_reviewers=successful,
            failed_reviewers=failed_reviewers,
        )

        _parallel_logger.info(
            "并行评审完成: total=%d success=%d failed=%d findings=%d",
            self._result.total_reviewers,
            self._result.successful_reviewers,
            len(self._result.failed_reviewers),
            len(self._result.findings),
        )

        return self._result

    def get_findings_by_reviewer(self) -> Dict[str, List[Finding]]:
        """获取按评审者分组的发现。

        Returns:
            {评审者名称: [Finding, ...]}，未执行时返回空 dict。
        """
        if self._result is None:
            return {}
        return dict(self._result.reviewer_results)

    def get_findings_by_role(self) -> Dict[str, List[Finding]]:
        """获取按评审角色分组的发现。

        Returns:
            {角色: [Finding, ...]}，未执行时返回空 dict。
        """
        if self._result is None:
            return {}

        by_role: Dict[str, List[Finding]] = {}
        for finding in self._result.findings:
            role = finding.role
            if role not in by_role:
                by_role[role] = []
            by_role[role].append(finding)
        return by_role

    def get_findings_by_severity(self) -> Dict[str, List[Finding]]:
        """获取按严重级别分组的发现。

        Returns:
            {severity: [Finding, ...]}，未执行时返回空 dict。
        """
        if self._result is None:
            return {}

        by_severity: Dict[str, List[Finding]] = {}
        for finding in self._result.findings:
            sev = finding.severity
            if sev not in by_severity:
                by_severity[sev] = []
            by_severity[sev].append(finding)
        return by_severity

    def get_statistics(self) -> Dict[str, Any]:
        """获取评审统计信息。

        Returns:
            包含统计数据的字典。
        """
        if self._result is None:
            return {"status": "not_executed"}

        by_severity = self.get_findings_by_severity()
        return {
            "status": "completed",
            "total_reviewers": self._result.total_reviewers,
            "successful_reviewers": self._result.successful_reviewers,
            "failed_reviewers": list(self._result.failed_reviewers),
            "total_findings": len(self._result.findings),
            "by_severity": {
                sev: len(fs) for sev, fs in by_severity.items()
            },
            "by_role": {
                role: len(fs)
                for role, fs in self.get_findings_by_role().items()
            },
        }
