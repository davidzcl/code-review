"""
系统配置中心

从 .env 文件和环境变量中加载配置，提供统一的配置访问接口。
支持模型配置、输出路径、评审流程参数等。
"""

from __future__ import annotations

import os
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import dotenv

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent

# 加载 .env
dotenv.load_dotenv(PROJECT_ROOT / ".env")


def _env(key: str, default: str = "") -> str:
    """读取环境变量，去除首尾空白。"""
    return os.getenv(key, default).strip()


def _env_int(key: str, default: int = 0) -> int:
    """读取整数环境变量。"""
    try:
        return int(_env(key, str(default)))
    except ValueError:
        return default


def _env_json(key: str, default: Any = None) -> Any:
    """读取 JSON 格式环境变量。"""
    val = _env(key)
    if not val:
        return default
    try:
        return json.loads(val)
    except json.JSONDecodeError:
        return default


# ============================================================
# 输出目录和文件配置
# ============================================================

OUTPUT_DIR = PROJECT_ROOT / _env("OUTPUT_DIR_NAME", ".review-agent")
TRANSCRIPT_FILE = _env("TRANSCRIPT_NAME", "transcript.jsonl")
REPORT_FILE = _env("REPORT_NAME", "report.md")
FINDINGS_FILE = _env("FINDINGS_NAME", "findings.json")
JUDGE_INPUT_FILE = _env("JUDGE_INPUT_NAME", "judge_input.json")
JUDGE_FILE = _env("JUDGE_NAME", "judge.json")
JUDGE_REPORT_FILE = _env("JUDGE_REPORT_NAME", "judge.md")
JUDGE_TRANSCRIPT_FILE = _env("JUDGE_TRANSCRIPT_NAME", "judge-transcript.jsonl")


# ============================================================
# 限制参数
# ============================================================

MAX_DIFF_CHARS = _env_int("MAX_DIFF_CHARS", 120000)
MAX_CMD_OUTPUT = _env_int("MAX_CMD_OUTPUT", 50000)
MAX_SKILL_CHARS = _env_int("MAX_SKILL_CHARS", 12000)


# ============================================================
# API 密钥和端点配置
# ============================================================

DASHSCOPE_API_KEY = _env("DASHSCOPE_API_KEY")
OPENAI_API_KEY = _env("OPENAI_API_KEY")
OPENAI_API_BASE_URL = _env("OPENAI_API_BASE_URL", "https://api.openai.com/v1")


# ============================================================
# 默认模型配置
# ============================================================

DEFAULT_DASHSCOPE_MODEL_CONFIG: Dict[str, Any] = {
    "model_type": "dashscope",
    "model_name": "qwen3.6-flash",
    "stream": True,
    "api_key": DASHSCOPE_API_KEY,
    "multimodality": True,
    "temperature": 0.5,
}

DEFAULT_OPENAI_MODEL_CONFIG: Dict[str, Any] = {
    "model_type": "openai",
    "model_name": "gpt-4o",
    "stream": True,
    "api_key": OPENAI_API_KEY,
}


# ============================================================
# 评审者配置（可扩展的多评审者角色）
# ============================================================

@dataclass
class ReviewerProfile:
    """评审者角色配置。"""

    name: str
    """评审者名称。"""
    role: str
    """评审角色，如 security、performance、logic、style。"""
    sys_prompt: str
    """系统提示词。"""
    model_config: Optional[Dict[str, Any]] = None
    """该评审者专用的模型配置，None 则使用默认配置。"""


# 默认评审者配置列表
DEFAULT_REVIEWER_PROFILES: List[ReviewerProfile] = [
    ReviewerProfile(
        name="SecurityReviewer",
        role="security",
        sys_prompt=(
            "你是一位资深安全审计专家。审查代码变更中的安全漏洞，"
            "包括但不限于：注入攻击、认证绕过、敏感信息泄露、权限提升、"
            "不安全的反序列化、加密实现缺陷。"
        ),
    ),
    ReviewerProfile(
        name="PerformanceReviewer",
        role="performance",
        sys_prompt=(
            "你是一位性能优化专家。审查代码变更中的性能问题，"
            "包括但不限于：N+1 查询、内存泄漏、不必要的对象创建、"
            "阻塞 IO、锁竞争、算法复杂度退化。"
        ),
    ),
    ReviewerProfile(
        name="LogicReviewer",
        role="logic",
        sys_prompt=(
            "你是一位逻辑审查专家。审查代码变更中的逻辑错误，"
            "包括但不限于：边界条件处理、空值检查、异常处理、"
            "竞态条件、死锁风险、事务一致性。"
        ),
    ),
    ReviewerProfile(
        name="StyleReviewer",
        role="style",
        sys_prompt=(
            "你是一位代码风格审查专家。审查代码变更中的可维护性问题，"
            "包括但不限于：命名规范、函数复杂度、重复代码、"
            "模块耦合度、测试覆盖率。"
        ),
    ),
]


# ============================================================
# 辩论循环参数
# ============================================================

MAX_DEBATE_ROUNDS = _env_int("MAX_DEBATE_ROUNDS", 3)
"""最大辩论轮次。"""

MIN_CONFIDENCE_THRESHOLD = float(_env("MIN_CONFIDENCE_THRESHOLD", "0.6"))
"""问题纳入报告的最低置信度阈值。"""


# ============================================================
# 报告输出格式
# ============================================================

SUPPORTED_REPORT_FORMATS = ["markdown", "html", "json"]
"""支持的输出格式。"""

DEFAULT_REPORT_FORMAT = "markdown"
"""默认输出格式。"""


# ============================================================
# 日志配置
# ============================================================

LOG_LEVEL = _env("LOG_LEVEL", "INFO")
"""日志级别： DEBUG / INFO / WARNING / ERROR / CRITICAL。"""
LOG_DIR = _env("LOG_DIR", "")
"""日志输出目录，为空则使用默认路径 {cwd}/logs。"""
LOG_MAX_BYTES = _env_int("LOG_MAX_BYTES", 10 * 1024 * 1024)
"""单个日志文件最大字节数（默认 10MB）。"""
LOG_BACKUP_COUNT = _env_int("LOG_BACKUP_COUNT", 5)
"""日志轮转保留的备份文件数。"""
LOG_FORMAT = _env(
    "LOG_FORMAT",
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
"""日志记录格式。"""
LOG_DATE_FORMAT = _env("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S")
"""日志时间戳格式。"""
LOG_RETENTION_DAYS = _env_int("LOG_RETENTION_DAYS", 30)
"""每日日志文件的保留天数（默认 30 天），超过此期限的日志文件自动清理。"""


def get_model_config(model_type: str = "dashscope") -> Dict[str, Any]:
    """获取指定类型的默认模型配置。

    Args:
        model_type: 模型类型标识符。

    Returns:
        模型配置字典。
    """
    if model_type == "dashscope":
        return DEFAULT_DASHSCOPE_MODEL_CONFIG.copy()
    if model_type == "openai_compatible":
        return DEFAULT_OPENAI_MODEL_CONFIG.copy()
    raise ValueError(f"不支持的默认模型类型: {model_type}")


def ensure_output_dir() -> Path:
    """确保输出目录存在，返回 Path 对象。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def output_path(filename: str) -> Path:
    """获取输出目录中的文件完整路径。"""
    return ensure_output_dir() / filename
