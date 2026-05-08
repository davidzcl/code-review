"""调度编排层 — 工作流控制、并发管理、结果聚合"""

from pipeline.parallel_review import (
    ParallelReviewManager,
    ParallelReviewResult,
)
from pipeline.debate_loop import (
    DebateRecord,
    DebateRound,
    run_debate_loop,
)
from pipeline.issue_merger import (
    MergeRecord,
    compute_finding_similarity,
    merge_similar_findings,
)
from pipeline.verdict import (
    Verdict,
    make_final_verdict,
)

__all__ = [
    "ParallelReviewManager",
    "ParallelReviewResult",
    "DebateRecord",
    "DebateRound",
    "run_debate_loop",
    "MergeRecord",
    "compute_finding_similarity",
    "merge_similar_findings",
    "Verdict",
    "make_final_verdict",
]
