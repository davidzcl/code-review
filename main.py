"""
PR 评审智能代理系统 — 系统入口

完整编排入口，串联：前置 Guardrail → 并行评审 → 辩论循环 → 合并 → 裁决 → 报告 → 评估
支持命令行参数指定 PR 信息。
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Any, Dict, List, Optional

from logger import logger
from config import (
    DEFAULT_REVIEWER_PROFILES,
    MAX_DEBATE_ROUNDS,
    MIN_CONFIDENCE_THRESHOLD,
    DEFAULT_REPORT_FORMAT,
    SUPPORTED_REPORT_FORMATS,
    LOG_LEVEL,
    OUTPUT_DIR,
)

from agents import (
    create_model,
    ReviewerAgent,
    ProsecutorAgent,
    DefenderAgent,
    EvaluatorAgent,
    AgentInitializationError,
)
from tools import (
    parse_diff,
    parse_pr_description,
    generate_report,
    write_report,
    build_guardrail_toolkit,
    build_guardrail_context,
)
from tools.tools import git_diff
from pipeline.parallel_review import ParallelReviewManager
from pipeline.debate_loop import run_debate_loop
from pipeline.issue_merger import merge_similar_findings
from pipeline.verdict import make_final_verdict

_main_logger = logger.get_logger("main")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PR 评审智能代理系统",
    )
    parser.add_argument(
        "--repo-dir", type=str, default=None,
        help="目标 Git 仓库目录（默认: 当前工作目录）",
    )
    
    parser.add_argument(
        "--base", type=str, default="",
        help="基准分支/commit",
    )
    parser.add_argument(
        "--target", type=str, default="",
        help="目标分支/commit",
    )
    parser.add_argument(
        "--pr-description", type=str, default="",
        help="PR 描述文本（Markdown 格式）",
    )
    parser.add_argument(
        "--pr-file", type=str, default="",
        help="PR 描述文件路径（替代 --pr-description）",
    )
    parser.add_argument(
        "--model-config", type=str, default="",
        help="模型配置 JSON 字符串",
    )
    parser.add_argument(
        "--output", type=str, default="",
        help="输出目录（默认: .review-agent/）",
    )
    parser.add_argument(
        "--format", type=str, default=DEFAULT_REPORT_FORMAT,
        choices=SUPPORTED_REPORT_FORMATS,
        help=f"报告输出格式（默认: {DEFAULT_REPORT_FORMAT}）",
    )
    parser.add_argument(
        "--skip-guardrail", action="store_true",
        help="跳过前置 Guardrail 扫描",
    )
    parser.add_argument(
        "--skip-evaluation", action="store_true",
        help="跳过 AI 质量评估",
    )
    parser.add_argument(
        "--max-rounds", type=int, default=MAX_DEBATE_ROUNDS,
        help=f"最大辩论轮次（默认: {MAX_DEBATE_ROUNDS}）",
    )
    parser.add_argument(
        "--confidence", type=float, default=MIN_CONFIDENCE_THRESHOLD,
        help=f"置信度阈值（默认: {MIN_CONFIDENCE_THRESHOLD}）",
    )
    return parser.parse_args()


def _load_pr_description(args: argparse.Namespace) -> str:
    if args.pr_file:
        path = os.path.abspath(args.pr_file)
        if not os.path.isfile(path):
            _main_logger.error("PR 文件不存在: %s", path)
            sys.exit(1)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return args.pr_description


def _load_model_config(args: argparse.Namespace) -> Dict[str, Any]:
    import json
    from config import (
        DEFAULT_DASHSCOPE_MODEL_CONFIG,
        DEFAULT_OPENAI_MODEL_CONFIG,
    )

    if args.model_config:
        try:
            return json.loads(args.model_config)
        except json.JSONDecodeError as e:
            _main_logger.error("模型配置 JSON 解析失败: %s", e)
            sys.exit(1)

    if os.getenv("DASHSCOPE_API_KEY"):
        return DEFAULT_DASHSCOPE_MODEL_CONFIG
    if os.getenv("OPENAI_API_KEY"):
        return DEFAULT_OPENAI_MODEL_CONFIG

    _main_logger.error(
        "未找到 API Key。请在 .env 文件中设置 DASHSCOPE_API_KEY 或 "
        "OPENAI_API_KEY，或通过 --model-config 参数指定。"
    )
    sys.exit(1)


async def run_pipeline(args: argparse.Namespace) -> None:
    _main_logger.info("PR 评审流水线启动")

    # Phase 0: 加载输入
    _main_logger.info("[Phase 0] 加载 PR 信息")
    pr_text = _load_pr_description(args)
    pr_context = parse_pr_description(pr_text) if pr_text else None
    diff_text = git_diff(args.base, args.target, cwd=args.repo_dir)
    diff_chunks = parse_diff(diff_text)

    _main_logger.info(
        "PR 信息: title=%s author=%s files=%d chunks=%d",
        pr_context.title if pr_context else "N/A",
        pr_context.author if pr_context else "N/A",
        len(diff_chunks),
    )

    if not diff_chunks:
        _main_logger.warning("diff 为空，无变更可评审")
        return

    # Phase 0.5: 前置 Guardrail
    guardrail_context = ""
    if not args.skip_guardrail:
        _main_logger.info("[Phase 0.5] 前置 Guardrail 扫描")
        guardrail_context = build_guardrail_context(diff_text, args.base, args.target, cwd=args.repo_dir)
        _main_logger.info("Guardrail 完成: %d 字符", len(guardrail_context))

    # Phase 1: 创建模型
    _main_logger.info("[Phase 1] 创建模型")
    model_config = _load_model_config(args)
    model = create_model(model_config)

    # Phase 2: 创建评审者
    _main_logger.info("[Phase 2] 创建评审者 (%d 个)", len(DEFAULT_REVIEWER_PROFILES))

    guardrail_toolkit = build_guardrail_toolkit()

    reviewers = []
    for profile in DEFAULT_REVIEWER_PROFILES:
        sys_prompt = profile.sys_prompt
        if guardrail_context:
            sys_prompt += guardrail_context

        agent = ReviewerAgent(
            name=profile.name,
            role=profile.role,
            sys_prompt=sys_prompt,
            model=model,
            toolkit=guardrail_toolkit,
        )
        reviewers.append(agent)

    # Phase 3: 并行评审
    _main_logger.info("[Phase 3] 并行评审")
    manager = ParallelReviewManager(reviewers=reviewers, timeout=300)
    parallel_result = await manager.run_all(diff_chunks, pr_context)

    findings = parallel_result.findings
    _main_logger.info(
        "评审完成: total=%d success=%d failed=%s findings=%d",
        parallel_result.total_reviewers,
        parallel_result.successful_reviewers,
        parallel_result.failed_reviewers,
        len(findings),
    )

    if not findings:
        _main_logger.warning("未发现任何问题")
        return

    # Phase 4: 辩论循环
    _main_logger.info("[Phase 4] 辩论循环 max_rounds=%d", args.max_rounds)

    prosecutor = ProsecutorAgent(
        name="ProsecutorAgent",
        role="prosecutor",
        sys_prompt="你是一位质疑者，对评审发现提出质疑。",
        model=model,
    )
    defender = DefenderAgent(
        name="DefenderAgent",
        role="defender",
        sys_prompt="你是一位辩护者，为评审发现辩护。",
        model=model,
    )

    debate_records = await run_debate_loop(
        findings=findings,
        prosecutor=prosecutor,
        defender=defender,
        diff_context=diff_text[:5000],
        max_rounds=args.max_rounds,
        confidence_threshold=args.confidence,
    )

    # Phase 5: 合并
    _main_logger.info("[Phase 5] 合并相似发现")
    merge_records = merge_similar_findings(debate_records)

    # Phase 6: 裁决
    _main_logger.info("[Phase 6] 最终裁决")
    verdict = make_final_verdict(debate_records, merge_records)

    # Phase 7: 报告生成
    _main_logger.info("[Phase 7] 生成报告 format=%s", args.format)
    diff_summary = f"变更 {len(diff_chunks)} 个文件"
    report = generate_report(
        verdict=verdict,
        pr_context=pr_context,
        diff_summary=diff_summary,
        output_format=args.format,
    )

    output_dir = os.path.abspath(args.output) if args.output else str(OUTPUT_DIR)
    ext = ".md" if args.format == "markdown" else f".{args.format}"
    output_path = os.path.join(output_dir, f"review_report{ext}")
    write_report(report, output_path)

    _main_logger.info("报告已输出: %s", output_path)

    # Phase 8: 质量评估
    if not args.skip_evaluation:
        _main_logger.info("[Phase 8] AI 质量评估")
        evaluator = EvaluatorAgent(
            name="EvaluatorAgent",
            model=model,
        )
        eval_result = await evaluator.evaluate(verdict, pr_context)
        _main_logger.info(
            "评估结果: score=%.2f coverage=%.2f clarity=%.2f actionability=%.2f",
            eval_result.score,
            eval_result.coverage_score,
            eval_result.clarity_score,
            eval_result.actionability_score,
        )

    _main_logger.info("PR 评审流水线完成")


def main() -> None:
    logger.setup_logger(level=LOG_LEVEL)

    args = parse_args()
    asyncio.run(run_pipeline(args))


if __name__ == "__main__":
    main()