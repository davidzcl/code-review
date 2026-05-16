# -*- coding: utf-8 -*-
"""
快速评测脚本 - 开发过程中使用

用法:
    python scripts/run_evaluation.py --agent reviewer --category security
    python scripts/run_evaluation.py --pipeline --case E2E-SEC-001
    python scripts/run_evaluation.py --list
"""

import argparse
import asyncio
import sys
import os

from agents.model_registry import create_model
from config import (
    DEFAULT_DASHSCOPE_MODEL_CONFIG,
    DEFAULT_OPENAI_MODEL_CONFIG,
    DASHSCOPE_API_KEY,
    OPENAI_API_KEY,
    get_model_config,
)
from tools.toolkit import Toolkit
from tools.tools import (
    git_diff,
    read_file,
    get_changed_files,
    get_workspace_status,
)
from tools.search import search_code
from tools.test_runner import run_tests
from tools.risk_scan import scan_risk_signals
from evaluation import ReviewerBenchmark, BenchmarkConfig
from evaluation.datasets import IssueCategory
from agents.reviewer import ReviewerAgent
from config import DEFAULT_REVIEWER_PROFILES
from evaluation.benchmark import PipelineBenchmark
from evaluation.datasets.e2e_cases import E2E_TEST_CASES
from agents.reviewer import ReviewerAgent
from agents.prosecutor import ProsecutorAgent
from agents.defender import DefenderAgent

# 设置项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_real_model(model_type: str = "dashscope", model_name: str = None):
    """创建真实模型实例
    
    Args:
        model_type: 模型类型 (dashscope / openai / ollama)
        model_name: 模型名称，None 则使用默认
    """
    
    config = get_model_config(model_type)
    if model_name:
        config["model_name"] = model_name
    config["temperature"] = 0.0  # 评测时使用确定性输出
    return create_model(config)


def create_toolkit():
    """创建工具集"""
    
    toolkit = Toolkit()
    toolkit.register(git_diff)
    toolkit.register(read_file)
    toolkit.register(get_changed_files)
    toolkit.register(get_workspace_status)
    toolkit.register(search_code)
    toolkit.register(run_tests)
    toolkit.register(scan_risk_signals)
    
    return toolkit


async def evaluate_agent(
    category: str,
    max_cases: int,
    model_type: str = "dashscope",
    model_name: str = None,
    use_mock: bool = False,
):
    """评测单个 Agent"""
    
    config = BenchmarkConfig(
        n_runs=1,
        categories=[IssueCategory(category)],
        max_cases_per_category=max_cases,
        temperature=0.0,
    )
    
    benchmark = ReviewerBenchmark(config=config)
    
    # 获取对应角色的配置
    profile = next(
        (p for p in DEFAULT_REVIEWER_PROFILES if p.role == category),
        DEFAULT_REVIEWER_PROFILES[0]
    )
    
    def create_agent():
        # 创建模型
        if use_mock:
            from unittest.mock import MagicMock
            from agentscope.model import ChatModelBase, ChatResponse
            
            model = MagicMock(spec=ChatModelBase)
            model.model_name = "mock-model"
            
            async def mock_call(*args, **kwargs):
                return ChatResponse(
                    text='{"findings": []}',
                    raw={},
                    usage={"prompt_tokens": 0, "completion_tokens": 0},
                )
            
            model.__call__ = mock_call
        else:
            model = create_real_model(model_type, model_name)
        
        # 创建工具集
        toolkit = Toolkit()
        
        return ReviewerAgent(
            name=f"{category.capitalize()}Reviewer",
            role=category,
            sys_prompt=profile.sys_prompt,
            model=model,
            toolkit=toolkit,
        )
    
    print(f"\n{'='*60}")
    print(f"评测 Agent: {category}")
    print(f"测试用例数: {max_cases}")
    print(f"模型: {model_type} ({model_name or 'default'})")
    print(f"{'='*60}\n")
    
    result = await benchmark.run_benchmark(
        agent_factory=create_agent,
        agent_name=f"{category.capitalize()}Reviewer",
        agent_role=category,
    )
    
    print("\n" + "="*60)
    print("评测结果")
    print("="*60)
    print(f"总用例数: {result.total_cases}")
    print(f"成功: {result.successful_cases}")
    print(f"失败: {result.failed_cases}")
    
    print(f"\n召回率: {result.avg_recall:.2%}")
    print(f"精确率: {result.avg_precision:.2%}")
    print(f"F1 分数: {result.avg_f1:.2%}")
    
    print(f"\n平均延迟: {result.avg_latency_ms:.0f}ms")
    print(f"P95 延迟: {result.p95_latency_ms:.0f}ms")
    print(f"稳定性: {result.avg_stability:.2%}")
    print(f"工具成功率: {result.avg_tool_success_rate:.2%}")
    
    if result.case_results:
        print("\n" + "="*60)
        print("详细结果")
        print("="*60)
        for case_result in result.case_results[:10]:
            status = "✓" if not case_result.error else "✗"
            print(f"{status} {case_result.test_case_id}: {case_result.test_case_name}")
            print(f"  召回: {case_result.finding_recall:.2%} | "
                  f"精确: {case_result.finding_precision:.2%} | "
                  f"F1: {case_result.finding_f1:.2%}")
            if case_result.error:
                print(f"  错误: {case_result.error}")


async def evaluate_pipeline(
    case_id: str,
    model_type: str = "dashscope",
    model_name: str = None,
    use_mock: bool = False,
):
    """评测完整流程"""
    
    case = next((c for c in E2E_TEST_CASES if c.test_id == case_id), None)
    if not case:
        print(f"未找到用例: {case_id}")
        print(f"可用用例: {[c.test_id for c in E2E_TEST_CASES]}")
        return
    
    print(f"\n{'='*60}")
    print(f"流程评测: {case_id}")
    print(f"用例名称: {case.name}")
    print(f"模型: {model_type} ({model_name or 'default'})")
    print(f"{'='*60}\n")
    
    benchmark = PipelineBenchmark()
    
    # 创建模型
    if use_mock:
        from unittest.mock import MagicMock
        from agentscope.model import ChatModelBase, ChatResponse
        
        model = MagicMock(spec=ChatModelBase)
        model.model_name = "mock-model"
        
        async def mock_call(*args, **kwargs):
            return ChatResponse(
                text='{"findings": []}',
                raw={},
                usage={"prompt_tokens": 0, "completion_tokens": 0},
            )
        
        model.__call__ = mock_call
    else:
        model = create_real_model(model_type, model_name)
    
    profile = DEFAULT_REVIEWER_PROFILES
    toolkit = Toolkit()
    
    result = await benchmark.run_pipeline(
        reviewers=[
            ReviewerAgent(
                name="SecurityReviewer",
                role="security",
                sys_prompt=profile[0].sys_prompt,
                model=model,
                toolkit=toolkit,
            ),
            ReviewerAgent(
                name="PerformanceReviewer",
                role="performance",
                sys_prompt=profile[1].sys_prompt,
                model=model,
                toolkit=toolkit,
            ),
            ReviewerAgent(
                name="LogicReviewer",
                role="logic",
                sys_prompt=profile[2].sys_prompt,
                model=model,
                toolkit=toolkit,
            ),
            ReviewerAgent(
                name="StyleReviewer",
                role="style",
                sys_prompt=profile[3].sys_prompt,
                model=model,
                toolkit=toolkit,
            ),
        ],
        prosecutor=ProsecutorAgent(
            name="Prosecutor",
            role="prosecutor",
            sys_prompt="你是一位质疑者，对评审发现提出质疑。",
            model=model,
        ),
        defender=DefenderAgent(
            name="Defender",
            role="defender",
            sys_prompt="你是一位辩护者，为评审发现辩护。",
            model=model,
        ),
        diff_chunks=case.diff_chunks,
        diff_context="",
    )
    
    print("\n" + "="*60)
    print("流程评测结果")
    print("="*60)
    if result.verdict:
        print(f"最终发现数: {len(result.verdict.findings)}")
        print(f"驳回发现数: {len(result.verdict.dismissed)}")
        print(f"合并发现数: {len(result.verdict.merged)}")
    else:
        print("未生成裁决结果")
    
    print(f"\n预期发现数: {case.expected_final_count}")
    
    if result.pipeline_result:
        pr = result.pipeline_result
        print(f"\n总耗时: {pr.total_duration_ms:.0f}ms")
        if pr.debate_metrics:
            print(f"辩论确认率: {pr.debate_metrics.confirmation_rate:.2%}")
        if pr.merge_metrics:
            print(f"合并率: {pr.merge_metrics.merge_rate:.2%}")


async def list_cases():
    """列出所有可用测试用例"""
    from evaluation.datasets import (
        get_security_test_cases,
        get_performance_test_cases,
        get_logic_test_cases,
        get_style_test_cases,
    )
    from evaluation.datasets.e2e_cases import E2E_TEST_CASES
    
    print("\n" + "="*60)
    print("安全类测试用例")
    print("="*60)
    for case in get_security_test_cases()[:10]:
        print(f"  {case.id}: {case.name} ({case.difficulty})")
    
    print("\n" + "="*60)
    print("性能类测试用例")
    print("="*60)
    for case in get_performance_test_cases()[:10]:
        print(f"  {case.id}: {case.name} ({case.difficulty})")
    
    print("\n" + "="*60)
    print("逻辑类测试用例")
    print("="*60)
    for case in get_logic_test_cases()[:10]:
        print(f"  {case.id}: {case.name} ({case.difficulty})")
    
    print("\n" + "="*60)
    print("风格类测试用例")
    print("="*60)
    for case in get_style_test_cases()[:10]:
        print(f"  {case.id}: {case.name} ({case.difficulty})")
    
    print("\n" + "="*60)
    print("端到端测试用例")
    print("="*60)
    for case in E2E_TEST_CASES:
        print(f"  {case.test_id}: {case.name} ({case.difficulty})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="开发过程评测工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出所有测试用例
  python scripts/run_evaluation.py --list
  
  # 评测 security 类 Agent (使用真实 API)
  python scripts/run_evaluation.py --agent reviewer --category security --max-cases 5
  
  # 使用 OpenAI 模型评测
  python scripts/run_evaluation.py --agent reviewer --category security --model-type openai --model-name gpt-4
  
  # 评测完整流程
  python scripts/run_evaluation.py --pipeline --case E2E-SEC-001
  
  # 使用 mock 模型（不调用真实 API）
  python scripts/run_evaluation.py --agent reviewer --category security --mock
        """
    )
    
    parser.add_argument("--agent", choices=["reviewer", "prosecutor", "defender"])
    parser.add_argument("--category", choices=["security", "performance", "logic", "style"])
    parser.add_argument("--max-cases", type=int, default=5, help="每类最大测试用例数")
    parser.add_argument("--pipeline", action="store_true", help="评测完整流程")
    parser.add_argument("--case", default="E2E-SEC-001", help="端到端用例 ID")
    parser.add_argument("--list", action="store_true", help="列出所有测试用例")
    
    # 模型配置
    parser.add_argument("--model-type", choices=["dashscope", "openai"], default="dashscope")
    parser.add_argument("--model-name", help="模型名称，如 qwen-max, gpt-4")
    parser.add_argument("--mock", action="store_true", help="使用 mock 模型（不调用真实 API）")
    
    args = parser.parse_args()
    
    if args.list:
        asyncio.run(list_cases())
    elif args.pipeline:
        asyncio.run(evaluate_pipeline(
            args.case,
            args.model_type,
            args.model_name,
            args.mock,
        ))
    elif args.agent and args.category:
        asyncio.run(evaluate_agent(
            args.category,
            args.max_cases,
            args.model_type,
            args.model_name,
            args.mock,
        ))
    else:
        parser.print_help()
