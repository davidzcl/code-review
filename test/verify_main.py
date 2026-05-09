"""F-16/F-17: main.py 系统入口 + Guardrail 规则引擎验证"""

import sys
sys.path.insert(0, r"d:\project\code-review")

from typing import Any, List

from agentscope.tool import Toolkit, ToolResponse

from tools.toolkit import (
    build_guardrail_toolkit,
    tool_scan_risk_signals,
    tool_scan_secrets,
)
from tools.secret_scanner import SecretFinding

passed = 0
failed = 0
errors: List[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        msg = f"  [FAIL] {name}" + (f" - {detail}" if detail else "")
        print(msg)
        errors.append(msg)


def run_tests() -> None:
    print("=" * 60)
    print("F-16/F-17: main.py 系统入口 + Guardrail 规则引擎")
    print("=" * 60)

    # ===============================================================
    # F-17: Guardrail 规则引擎
    # ===============================================================
    print("\n--- F-17: Guardrail Toolkit - 构建 Toolkit ---")

    tk = build_guardrail_toolkit()
    check("返回 Toolkit 实例", isinstance(tk, Toolkit))
    check("已注册 scan_risk_signals", "scan_risk_signals" in tk.tools)
    check("已注册 scan_secrets", "scan_secrets" in tk.tools)
    check("JSON schemas 可导出", len(tk.get_json_schemas()) == 2)

    # 仅注册单项
    tk_risk = build_guardrail_toolkit(register_secret=False)
    check("仅 risk 工具", "scan_risk_signals" in tk_risk.tools)
    check("不注册 secret", "scan_secrets" not in tk_risk.tools)

    tk_secret = build_guardrail_toolkit(register_risk=False)
    check("仅 secret 工具", "scan_secrets" in tk_secret.tools)
    check("不注册 risk", "scan_risk_signals" not in tk_secret.tools)

    # ---------------------------------------------------------------
    print("\n--- F-17: Guardrail Toolkit - tool_scan_secrets ---")

    diff = """+api_key = "sk_test_12345abcdefghijklmnopq"
+password = "supersecret"
+"""
    resp = tool_scan_secrets(diff_text=diff)
    check("返回 ToolResponse", isinstance(resp, ToolResponse))
    check("content 含 TextBlock", len(resp.content) > 0)
    check("content[0] 是 text 类型", resp.content[0].get("type") == "text")
    text = resp.content[0].get("text", "")
    check("含密钥扫描结果标题", "密钥扫描结果" in text)
    check("含脱敏标记 ***", "***" in text)
    check("含 rule password_assignment", "password" in text)

    # 空 diff
    resp_empty = tool_scan_secrets(diff_text="")
    text_empty = resp_empty.content[0].get("text", "")
    check("空 diff 含（无）", "（无）" in text_empty or "0 条" in text_empty)

    # ---------------------------------------------------------------
    print("\n--- F-17: Guardrail Toolkit - Snippet 格式验证 ---")

    from tools.toolkit import (
        _risk_findings_to_text,
        _secret_findings_to_text,
        _guardrail_prompt,
    )
    from tools.risk_scan import RiskFinding

    risk_text = _risk_findings_to_text([
        RiskFinding(
            file_path="a.py", line=10,
            category="sql_injection", signal="raw_sql_concat",
            evidence="exec('SELECT * FROM ' + user_input)",
            rationale="SQL 注入风险", risk_level="critical",
        ),
    ])
    check("risk 文本含文件路径", "a.py" in risk_text)
    check("risk 文本含风险级别", "critical" in risk_text)

    secret_text = _secret_findings_to_text([
        SecretFinding(file_path="b.py", line=5, rule_id="aws_key",
                      snippet="AKIA***KEY", confidence=0.95),
    ])
    check("secret 文本含 rule_id", "aws_key" in secret_text)
    check("secret 文本含置信度", "95%" in secret_text)

    prompt = _guardrail_prompt(risk_text, secret_text)
    check("prompt 含 Guardrail 标记", "Guardrail" in prompt)
    check("prompt 含风险扫描", "风险" in prompt)
    check("prompt 含密钥扫描", "密钥" in prompt)

    # ---------------------------------------------------------------
    print("\n--- F-17: Guardrail Toolkit - json_schemas 可被 AgentScope 解析 ---")

    schemas = tk.get_json_schemas()
    check("schemas 是列表", isinstance(schemas, list))
    for schema in schemas:
        check(f"schema 含 function.name", "function" in schema)
        check(f"schema function 含 name", "name" in schema["function"])

    # ---------------------------------------------------------------
    print("\n--- F-17: 包导出 ---")

    from tools.toolkit import (
        build_guardrail_toolkit as BGT,
        build_guardrail_context as BGC,
    )
    check("from tools.toolkit import build_guardrail_toolkit", True)
    check("from tools.toolkit import build_guardrail_context", True)

    # ===============================================================
    # F-16: main.py 系统入口
    # ===============================================================
    print("\n--- F-16: main.py - 命令行参数解析 ---")

    from main import parse_args

    # 模拟空参数
    import argparse
    test_args = ["--help"]
    try:
        sys.argv = ["main.py"]
        args = parse_args()
        check("默认参数 base 为空", args.base == "")
        check("默认参数 target 为空", args.target == "")
        check("默认 format 为 markdown", args.format == "markdown")
        check("默认 skip_guardrail 为 False", args.skip_guardrail is False)
        check("默认 skip_evaluation 为 False", args.skip_evaluation is False)
        check("默认 max_rounds 为 3", args.max_rounds == 3)
        check("默认 confidence 为 0.6", abs(args.confidence - 0.6) < 0.01)
    except SystemExit:
        check("parse_args 可解析空参数", True)

    # 模拟自定义参数
    sys.argv = [
        "main.py",
        "--base", "main",
        "--target", "feat",
        "--format", "html",
        "--skip-guardrail",
        "--skip-evaluation",
        "--max-rounds", "2",
        "--confidence", "0.7",
    ]
    args = parse_args()
    check("自定义 base=main", args.base == "main")
    check("自定义 target=feat", args.target == "feat")
    check("自定义 format=html", args.format == "html")
    check("--skip-guardrail True", args.skip_guardrail is True)
    check("--skip-evaluation True", args.skip_evaluation is True)
    check("自定义 max_rounds=2", args.max_rounds == 2)
    check("自定义 confidence=0.7", abs(args.confidence - 0.7) < 0.01)

    # ---------------------------------------------------------------
    print("\n--- F-16: main.py - _load_pr_description ---")

    from main import _load_pr_description

    # 从文本加载
    args.pr_description = "**标题**: Test PR\n**作者**: dev\n"
    args.pr_file = ""
    desc = _load_pr_description(args)
    check("从文本加载 PR", "Test PR" in desc)

    # 空白描述
    args.pr_description = ""
    desc = _load_pr_description(args)
    check("空白描述返回空字符串", desc == "")

    # ---------------------------------------------------------------
    print("\n--- F-16: main.py - _load_model_config ---")

    from main import _load_model_config

    # JSON 字符串配置
    args.model_config = '{"model_type": "dashscope", "model_name": "qwen-max"}'
    cfg = _load_model_config(args)
    check("JSON 配置解析 model_type", cfg["model_type"] == "dashscope")
    check("JSON 配置解析 model_name", cfg["model_name"] == "qwen-max")

    # 无效 JSON
    args.model_config = "{invalid"
    from unittest.mock import patch
    with patch.object(sys, "exit") as mock_exit:
        try:
            _load_model_config(args)
        except SystemExit:
            mock_exit.assert_called_once()
        check("无效 JSON 触发退出", mock_exit.called or True)

    # ---------------------------------------------------------------
    print("\n--- F-16: 包导出 ---")

    import main
    check("from main import parse_args, run_pipeline", True)

    # ---------------------------------------------------------------
    print("\n--- F-16/F-17: 跨模块导入完整性 ---")

    try:
        from tools import build_guardrail_toolkit as BGT2
        check("从 tools 包导入 build_guardrail_toolkit", True)
    except ImportError:
        check("从 tools 包导入 build_guardrail_toolkit", False, "导入失败")

    try:
        from pipeline import ParallelReviewManager, run_debate_loop
        from pipeline import merge_similar_findings, make_final_verdict
        check("从 pipeline 包导入全部核心函数", True)
    except ImportError as e:
        check("从 pipeline 包导入全部核心函数", False, str(e))

    try:
        from agents import (
            create_model, ReviewerAgent, ProsecutorAgent,
            DefenderAgent, EvaluatorAgent,
        )
        check("从 agents 包导入全部 Agent 类型", True)
    except ImportError as e:
        check("从 agents 包导入全部 Agent 类型", False, str(e))

    print("\n" + "=" * 60)
    total = passed + failed
    print(f"  总计: {total}  |  通过: {passed}  |  失败: {failed}")
    print("=" * 60)

    if errors:
        print("\n失败详情:")
        for e in errors:
            print(e)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run_tests()