"""
端到端测试用例数据集

定义完整的评审流程测试用例，包括：
- 真实的 diff 输入
- 预期的发现列表
- 预期的辩论结果
- 预期的最终裁决
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from tools.diff_parser import DiffChunk


class E2ETestCategory(str, Enum):
    """端到端测试类别"""

    SECURITY = "security"
    PERFORMANCE = "performance"
    LOGIC = "logic"
    STYLE = "style"
    MIXED = "mixed"


@dataclass
class ExpectedFinding:
    """预期发现"""

    title: str
    category: str
    severity: str
    file_path: Optional[str] = None
    line_range: Optional[tuple[int, int]] = None
    description: Optional[str] = None
    should_be_confirmed: bool = True
    confidence_threshold: float = 0.6


@dataclass
class E2ETestCase:
    """端到端测试用例"""

    test_id: str
    name: str
    category: E2ETestCategory
    description: str
    diff_chunks: List[DiffChunk]
    expected_findings: List[ExpectedFinding]
    pr_context: Optional[Dict[str, Any]] = None
    expected_debate_outcomes: Optional[Dict[str, str]] = None
    expected_final_count: Optional[int] = None
    difficulty: str = "medium"
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.expected_final_count is None:
            confirmed = sum(1 for f in self.expected_findings if f.should_be_confirmed)
            self.expected_final_count = confirmed


SQL_INJECTION_BASIC = E2ETestCase(
    test_id="E2E-SEC-001",
    name="SQL注入基础检测",
    category=E2ETestCategory.SECURITY,
    description="检测简单的字符串拼接SQL注入漏洞",
    diff_chunks=[
        DiffChunk(
            file_path="db/query.py",
            old_start=1,
            old_count=0,
            new_start=1,
            new_count=5,
            context="",
            additions=[
                "def get_user(user_id):",
                "    query = f\"SELECT * FROM users WHERE id = '{user_id}'\"",
                "    return db.execute(query)",
            ],
            deletions=[],
            language="python",
        ),
    ],
    expected_findings=[
        ExpectedFinding(
            title="SQL注入漏洞",
            category="security",
            severity="critical",
            file_path="db/query.py",
            line_range=(2, 2),
            description="使用字符串拼接构造SQL查询，存在注入风险",
            should_be_confirmed=True,
        ),
    ],
    expected_final_count=1,
    difficulty="easy",
    tags=["sql-injection", "security", "input-validation"],
)

XSS_REFLECTED = E2ETestCase(
    test_id="E2E-SEC-002",
    name="反射型XSS检测",
    category=E2ETestCategory.SECURITY,
    description="检测未转义的用户输入直接输出到HTML",
    diff_chunks=[
        DiffChunk(
            file_path="views/profile.py",
            old_start=1,
            old_count=0,
            new_start=1,
            new_count=8,
            context="",
            additions=[
                "def show_profile(request):",
                "    username = request.GET.get('name', '')",
                "    html = f\"<h1>Welcome, {username}!</h1>\"",
                "    return HttpResponse(html)",
            ],
            deletions=[],
            language="python",
        ),
    ],
    expected_findings=[
        ExpectedFinding(
            title="XSS跨站脚本攻击漏洞",
            category="security",
            severity="high",
            file_path="views/profile.py",
            line_range=(3, 3),
            description="用户输入未转义直接输出到HTML",
            should_be_confirmed=True,
        ),
    ],
    expected_final_count=1,
    difficulty="easy",
    tags=["xss", "security", "output-encoding"],
)

HARDCODED_SECRET = E2ETestCase(
    test_id="E2E-SEC-003",
    name="硬编码密钥检测",
    category=E2ETestCategory.SECURITY,
    description="检测代码中硬编码的API密钥",
    diff_chunks=[
        DiffChunk(
            file_path="config/api.py",
            old_start=1,
            old_count=0,
            new_start=1,
            new_count=5,
            context="",
            additions=[
                "API_KEY = 'sk-1234567890abcdef1234567890abcdef'",
                "SECRET_TOKEN = 'ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'",
            ],
            deletions=[],
            language="python",
        ),
    ],
    expected_findings=[
        ExpectedFinding(
            title="硬编码API密钥",
            category="security",
            severity="critical",
            file_path="config/api.py",
            line_range=(1, 2),
            description="敏感凭证硬编码在源代码中",
            should_be_confirmed=True,
        ),
    ],
    expected_final_count=1,
    difficulty="easy",
    tags=["secrets", "security", "credential-exposure"],
)

N_PLUS_ONE_QUERY = E2ETestCase(
    test_id="E2E-PERF-001",
    name="N+1查询问题检测",
    category=E2ETestCategory.PERFORMANCE,
    description="检测循环中的数据库查询",
    diff_chunks=[
        DiffChunk(
            file_path="services/order.py",
            old_start=1,
            old_count=0,
            new_start=1,
            new_count=10,
            context="",
            additions=[
                "def get_order_details(order_ids):",
                "    orders = []",
                "    for oid in order_ids:",
                "        order = Order.query.get(oid)",
                "        items = OrderItem.query.filter_by(order_id=oid).all()",
                "        orders.append((order, items))",
                "    return orders",
            ],
            deletions=[],
            language="python",
        ),
    ],
    expected_findings=[
        ExpectedFinding(
            title="N+1查询性能问题",
            category="performance",
            severity="medium",
            file_path="services/order.py",
            line_range=(4, 5),
            description="循环中执行数据库查询，应使用批量查询",
            should_be_confirmed=True,
        ),
    ],
    expected_final_count=1,
    difficulty="medium",
    tags=["n+1", "performance", "database"],
)

INEFFICIENT_ALGORITHM = E2ETestCase(
    test_id="E2E-PERF-002",
    name="低效算法检测",
    category=E2ETestCategory.PERFORMANCE,
    description="检测嵌套循环导致的O(n²)复杂度",
    diff_chunks=[
        DiffChunk(
            file_path="utils/search.py",
            old_start=1,
            old_count=0,
            new_start=1,
            new_count=12,
            context="",
            additions=[
                "def find_duplicates(items):",
                "    duplicates = []",
                "    for i in range(len(items)):",
                "        for j in range(i + 1, len(items)):",
                "            if items[i] == items[j]:",
                "                duplicates.append(items[i])",
                "    return duplicates",
            ],
            deletions=[],
            language="python",
        ),
    ],
    expected_findings=[
        ExpectedFinding(
            title="O(n²)时间复杂度",
            category="performance",
            severity="medium",
            file_path="utils/search.py",
            line_range=(3, 6),
            description="嵌套循环导致O(n²)复杂度，建议使用集合或字典优化",
            should_be_confirmed=True,
        ),
    ],
    expected_final_count=1,
    difficulty="medium",
    tags=["complexity", "performance", "algorithm"],
)

NULL_POINTER_CHECK = E2ETestCase(
    test_id="E2E-LOGIC-001",
    name="空指针检查缺失",
    category=E2ETestCategory.LOGIC,
    description="检测未检查返回值是否为空",
    diff_chunks=[
        DiffChunk(
            file_path="services/user.py",
            old_start=1,
            old_count=0,
            new_start=1,
            new_count=8,
            context="",
            additions=[
                "def get_user_email(user_id):",
                "    user = User.query.get(user_id)",
                "    return user.email",
            ],
            deletions=[],
            language="python",
        ),
    ],
    expected_findings=[
        ExpectedFinding(
            title="空指针异常风险",
            category="logic",
            severity="high",
            file_path="services/user.py",
            line_range=(2, 3),
            description="未检查user是否为None即访问属性",
            should_be_confirmed=True,
        ),
    ],
    expected_final_count=1,
    difficulty="easy",
    tags=["null-check", "logic", "error-handling"],
)

OFF_BY_ONE = E2ETestCase(
    test_id="E2E-LOGIC-002",
    name="边界条件错误",
    category=E2ETestCategory.LOGIC,
    description="检测数组越界风险",
    diff_chunks=[
        DiffChunk(
            file_path="utils/array.py",
            old_start=1,
            old_count=0,
            new_start=1,
            new_count=8,
            context="",
            additions=[
                "def get_last_n(items, n):",
                "    return items[len(items) - n:]",
            ],
            deletions=[],
            language="python",
        ),
    ],
    expected_findings=[
        ExpectedFinding(
            title="边界条件错误",
            category="logic",
            severity="medium",
            file_path="utils/array.py",
            line_range=(2, 2),
            description="当n大于len(items)时会产生意外结果",
            should_be_confirmed=True,
        ),
    ],
    expected_final_count=1,
    difficulty="medium",
    tags=["boundary", "logic", "off-by-one"],
)

CODE_DUPLICATION = E2ETestCase(
    test_id="E2E-STYLE-001",
    name="代码重复检测",
    category=E2ETestCategory.STYLE,
    description="检测重复代码块",
    diff_chunks=[
        DiffChunk(
            file_path="utils/validation.py",
            old_start=1,
            old_count=0,
            new_start=1,
            new_count=20,
            context="",
            additions=[
                "def validate_email(email):",
                "    if not email:",
                "        raise ValueError('Email is required')",
                "    if '@' not in email:",
                "        raise ValueError('Invalid email format')",
                "    return email.lower()",
                "",
                "def validate_phone(phone):",
                "    if not phone:",
                "        raise ValueError('Phone is required')",
                "    if not phone.isdigit():",
                "        raise ValueError('Invalid phone format')",
                "    return phone",
            ],
            deletions=[],
            language="python",
        ),
    ],
    expected_findings=[
        ExpectedFinding(
            title="代码重复",
            category="style",
            severity="low",
            file_path="utils/validation.py",
            line_range=(1, 13),
            description="验证函数存在重复模式，建议提取公共验证逻辑",
            should_be_confirmed=True,
        ),
    ],
    expected_final_count=1,
    difficulty="medium",
    tags=["duplication", "style", "maintainability"],
)

MIXED_ISSUES = E2ETestCase(
    test_id="E2E-MIXED-001",
    name="多类型问题混合",
    category=E2ETestCategory.MIXED,
    description="包含安全、性能、逻辑多种问题的代码",
    diff_chunks=[
        DiffChunk(
            file_path="api/handler.py",
            old_start=1,
            old_count=0,
            new_start=1,
            new_count=25,
            context="",
            additions=[
                "def process_request(request):",
                "    data = request.json",
                "    user_id = data.get('user_id')",
                "    ",
                "    query = f\"SELECT * FROM users WHERE id = {user_id}\"",
                "    user = db.execute(query).fetchone()",
                "    ",
                "    orders = []",
                "    for oid in user.order_ids:",
                "        order = Order.query.get(oid)",
                "        orders.append(order)",
                "    ",
                "    return {",
                "        'user': user.name,",
                "        'email': user.email,",
                "        'orders': orders",
                "    }",
            ],
            deletions=[],
            language="python",
        ),
    ],
    expected_findings=[
        ExpectedFinding(
            title="SQL注入漏洞",
            category="security",
            severity="critical",
            file_path="api/handler.py",
            line_range=(5, 5),
            should_be_confirmed=True,
        ),
        ExpectedFinding(
            title="N+1查询问题",
            category="performance",
            severity="medium",
            file_path="api/handler.py",
            line_range=(9, 10),
            should_be_confirmed=True,
        ),
        ExpectedFinding(
            title="空指针异常风险",
            category="logic",
            severity="high",
            file_path="api/handler.py",
            line_range=(6, 6),
            should_be_confirmed=True,
        ),
    ],
    expected_final_count=3,
    difficulty="hard",
    tags=["mixed", "security", "performance", "logic"],
)

E2E_TEST_CASES: List[E2ETestCase] = [
    SQL_INJECTION_BASIC,
    XSS_REFLECTED,
    HARDCODED_SECRET,
    N_PLUS_ONE_QUERY,
    INEFFICIENT_ALGORITHM,
    NULL_POINTER_CHECK,
    OFF_BY_ONE,
    CODE_DUPLICATION,
    MIXED_ISSUES,
]


def get_e2e_cases_by_category(category: E2ETestCategory) -> List[E2ETestCase]:
    """按类别获取端到端测试用例"""
    return [c for c in E2E_TEST_CASES if c.category == category]


def get_e2e_cases_by_difficulty(difficulty: str) -> List[E2ETestCase]:
    """按难度获取端到端测试用例"""
    return [c for c in E2E_TEST_CASES if c.difficulty == difficulty]
