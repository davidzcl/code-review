"""
风格类测试用例数据集

包含 20 条代码风格相关的测试用例，覆盖：
- 命名规范问题
- 代码重复
- 过长函数
- 缺少文档
- 未使用的导入/变量
- 魔法数字
- 过深的嵌套
"""

from __future__ import annotations

from typing import List

from evaluation.datasets.schemas import (
    DiffChunkSchema,
    InjectedIssue,
    IssueCategory,
    SyntheticTestCase,
)


def get_style_test_cases() -> List[SyntheticTestCase]:
    """获取风格类测试用例列表"""
    return [
        # ==================== 命名规范问题 (4 条) ====================
        SyntheticTestCase(
            id="STYLE-NAME-001",
            name="单字母变量名",
            category=IssueCategory.STYLE,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/calculator.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=4,
                    additions=[
                        'def calculate(x, y, z):',
                        '    a = x + y',
                        '    b = a * z',
                        '    return b',
                    ],
                    deletions=[
                        'def calculate(x, y, z):',
                        '    pass',
                    ],
                    context="计算器",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.STYLE,
                    severity="low",
                    title="变量命名不规范",
                    description="使用单字母变量名，应使用有意义的名称",
                    file_path="src/utils/calculator.py",
                    line_range=(10, 13),
                    detection_hints=["naming convention", "single letter", "variable name", "meaningful name"],
                )
            ],
        ),
        SyntheticTestCase(
            id="STYLE-NAME-002",
            name="驼峰命名不一致",
            category=IssueCategory.STYLE,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/models/user.py",
                    language="python",
                    old_start=5,
                    old_count=2,
                    new_start=5,
                    new_count=4,
                    additions=[
                        'class usermodel:',
                        '    def __init__(self):',
                        '        self.UserName = ""',
                        '        self.user_email = ""',
                    ],
                    deletions=[
                        'class usermodel:',
                        '    pass',
                    ],
                    context="用户模型",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.STYLE,
                    severity="low",
                    title="命名风格不一致",
                    description="类名应使用 PascalCase，属性名应使用 snake_case",
                    file_path="src/models/user.py",
                    line_range=(5, 8),
                    detection_hints=["naming convention", "PascalCase", "snake_case", "inconsistent naming"],
                )
            ],
        ),
        SyntheticTestCase(
            id="STYLE-NAME-003",
            name="函数名不清晰",
            category=IssueCategory.STYLE,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/processor.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=3,
                    additions=[
                        'def process(data):',
                        '    return data',
                        '',
                    ],
                    deletions=[
                        'def process(data):',
                        '    pass',
                    ],
                    context="处理器服务",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.STYLE,
                    severity="low",
                    title="函数名过于通用",
                    description="函数名 'process' 过于通用，应使用更具体的名称",
                    file_path="src/services/processor.py",
                    line_range=(15, 16),
                    detection_hints=["naming convention", "function name", "descriptive name", "too generic"],
                )
            ],
        ),
        SyntheticTestCase(
            id="STYLE-NAME-004",
            name="布尔变量命名",
            category=IssueCategory.STYLE,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/validator.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=3,
                    additions=[
                        'def check_user(user):',
                        '    flag = user.is_active',
                        '    return flag',
                    ],
                    deletions=[
                        'def check_user(user):',
                        '    pass',
                    ],
                    context="验证工具",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.STYLE,
                    severity="low",
                    title="布尔变量命名不规范",
                    description="布尔变量应使用 is_/has_ 前缀，如 is_active",
                    file_path="src/utils/validator.py",
                    line_range=(11, 11),
                    detection_hints=["naming convention", "boolean variable", "is_ prefix", "has_ prefix"],
                )
            ],
        ),

        # ==================== 代码重复 (3 条) ====================
        SyntheticTestCase(
            id="STYLE-DUP-001",
            name="重复的代码块",
            category=IssueCategory.STYLE,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/user_service.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=12,
                    additions=[
                        'def create_user(name, email):',
                        '    user = User()',
                        '    user.name = name',
                        '    user.email = email',
                        '    user.save()',
                        '    return user',
                        '',
                        'def update_user(user, name, email):',
                        '    user.name = name',
                        '    user.email = email',
                        '    user.save()',
                        '    return user',
                    ],
                    deletions=[
                        'def create_user(name, email):',
                        '    pass',
                    ],
                    context="用户服务",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.STYLE,
                    severity="medium",
                    title="代码重复",
                    description="create_user 和 update_user 有重复的属性赋值逻辑，应提取公共方法",
                    file_path="src/services/user_service.py",
                    line_range=(10, 21),
                    detection_hints=["code duplication", "DRY", "extract method", "duplicate code"],
                )
            ],
        ),
        SyntheticTestCase(
            id="STYLE-DUP-002",
            name="重复的条件判断",
            category=IssueCategory.STYLE,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/handler.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=10,
                    additions=[
                        'def handle_create(data):',
                        '    if not data:',
                        '        return None',
                        '    return create(data)',
                        '',
                        'def handle_update(data):',
                        '    if not data:',
                        '        return None',
                        '    return update(data)',
                    ],
                    deletions=[
                        'def handle_create(data):',
                        '    pass',
                    ],
                    context="处理器",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.STYLE,
                    severity="low",
                    title="重复的条件判断",
                    description="相同的空值检查重复出现，应提取为装饰器或辅助函数",
                    file_path="src/utils/handler.py",
                    line_range=(16, 23),
                    detection_hints=["code duplication", "DRY", "duplicate condition", "extract function"],
                )
            ],
        ),
        SyntheticTestCase(
            id="STYLE-DUP-003",
            name="重复的日志记录",
            category=IssueCategory.STYLE,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/api.py",
                    language="python",
                    old_start=20,
                    old_count=2,
                    new_start=20,
                    new_count=8,
                    additions=[
                        'def fetch_user(user_id):',
                        '    logger.info(f"Fetching user {user_id}")',
                        '    user = api.get(user_id)',
                        '    logger.info(f"Fetched user {user_id}")',
                        '    return user',
                        '',
                        'def fetch_order(order_id):',
                        '    logger.info(f"Fetching order {order_id}")',
                        '    order = api.get(order_id)',
                        '    logger.info(f"Fetched order {order_id}")',
                        '    return order',
                    ],
                    deletions=[
                        'def fetch_user(user_id):',
                        '    pass',
                    ],
                    context="API 服务",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.STYLE,
                    severity="low",
                    title="重复的日志模式",
                    description="日志记录模式重复，应提取为装饰器或上下文管理器",
                    file_path="src/services/api.py",
                    line_range=(20, 29),
                    detection_hints=["code duplication", "logging pattern", "decorator", "context manager"],
                )
            ],
        ),

        # ==================== 过长函数 (3 条) ====================
        SyntheticTestCase(
            id="STYLE-LONG-001",
            name="过长函数",
            category=IssueCategory.STYLE,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/processor.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=25,
                    additions=[
                        'def process_order(order):',
                        '    # validate order',
                        '    if not order.items:',
                        '        return None',
                        '    if not order.customer:',
                        '        return None',
                        '    # calculate total',
                        '    total = 0',
                        '    for item in order.items:',
                        '        total += item.price * item.quantity',
                        '    # apply discount',
                        '    if order.customer.is_vip:',
                        '        total *= 0.9',
                        '    # create invoice',
                        '    invoice = Invoice()',
                        '    invoice.total = total',
                        '    invoice.items = order.items',
                        '    # send notification',
                        '    send_email(order.customer.email, invoice)',
                        '    # update inventory',
                        '    for item in order.items:',
                        '        inventory.decrease(item.product, item.quantity)',
                        '    # save order',
                        '    order.status = "completed"',
                        '    order.save()',
                        '    return order',
                    ],
                    deletions=[
                        'def process_order(order):',
                        '    pass',
                    ],
                    context="订单处理",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.STYLE,
                    severity="medium",
                    title="函数过长",
                    description="函数超过 20 行，应拆分为多个小函数",
                    file_path="src/services/processor.py",
                    line_range=(10, 34),
                    detection_hints=["long function", "function length", "refactor", "extract method"],
                )
            ],
        ),
        SyntheticTestCase(
            id="STYLE-LONG-002",
            name="过深的嵌套",
            category=IssueCategory.STYLE,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/validator.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=15,
                    additions=[
                        'def validate_user(user):',
                        '    if user:',
                        '        if user.profile:',
                        '            if user.profile.address:',
                        '                if user.profile.address.city:',
                        '                    if user.profile.address.zip:',
                        '                        return True',
                        '    return False',
                    ],
                    deletions=[
                        'def validate_user(user):',
                        '    pass',
                    ],
                    context="验证工具",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.STYLE,
                    severity="medium",
                    title="嵌套过深",
                    description="条件嵌套超过 3 层，应使用提前返回或提取方法",
                    file_path="src/utils/validator.py",
                    line_range=(15, 22),
                    detection_hints=["deep nesting", "early return", "guard clause", "extract method"],
                )
            ],
        ),
        SyntheticTestCase(
            id="STYLE-LONG-003",
            name="过长的参数列表",
            category=IssueCategory.STYLE,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/user.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=3,
                    additions=[
                        'def create_user(name, email, phone, address, city, country, zip_code, age, gender, occupation):',
                        '    pass',
                        '',
                    ],
                    deletions=[
                        'def create_user(name, email):',
                        '    pass',
                    ],
                    context="用户服务",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.STYLE,
                    severity="low",
                    title="参数列表过长",
                    description="函数参数超过 5 个，应使用配置对象或字典",
                    file_path="src/services/user.py",
                    line_range=(10, 10),
                    detection_hints=["long parameter list", "parameter object", "kwargs", "config object"],
                )
            ],
        ),

        # ==================== 缺少文档 (3 条) ====================
        SyntheticTestCase(
            id="STYLE-DOC-001",
            name="缺少函数文档",
            category=IssueCategory.STYLE,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/helper.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=4,
                    additions=[
                        'def calculate_discount(price, customer_type):',
                        '    if customer_type == "vip":',
                        '        return price * 0.8',
                        '    return price',
                    ],
                    deletions=[
                        'def calculate_discount(price, customer_type):',
                        '    pass',
                    ],
                    context="帮助工具",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.STYLE,
                    severity="low",
                    title="缺少函数文档",
                    description="函数缺少 docstring，应添加文档说明",
                    file_path="src/utils/helper.py",
                    line_range=(10, 13),
                    detection_hints=["missing docstring", "documentation", "docstring", "function documentation"],
                )
            ],
        ),
        SyntheticTestCase(
            id="STYLE-DOC-002",
            name="缺少类文档",
            category=IssueCategory.STYLE,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/models/payment.py",
                    language="python",
                    old_start=5,
                    old_count=2,
                    new_start=5,
                    new_count=4,
                    additions=[
                        'class PaymentProcessor:',
                        '    def __init__(self, api_key):',
                        '        self.api_key = api_key',
                        '',
                    ],
                    deletions=[
                        'class PaymentProcessor:',
                        '    pass',
                    ],
                    context="支付模型",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.STYLE,
                    severity="low",
                    title="缺少类文档",
                    description="类缺少 docstring，应添加类说明",
                    file_path="src/models/payment.py",
                    line_range=(5, 7),
                    detection_hints=["missing docstring", "class documentation", "docstring"],
                )
            ],
        ),
        SyntheticTestCase(
            id="STYLE-DOC-003",
            name="缺少模块文档",
            category=IssueCategory.STYLE,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/constants.py",
                    language="python",
                    old_start=1,
                    old_count=1,
                    new_start=1,
                    new_count=3,
                    additions=[
                        'MAX_RETRIES = 3',
                        'TIMEOUT = 30',
                        'DEFAULT_PAGE_SIZE = 10',
                    ],
                    deletions=["# constants"],
                    context="常量模块",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.STYLE,
                    severity="low",
                    title="缺少模块文档",
                    description="模块缺少 docstring，应添加模块说明",
                    file_path="src/utils/constants.py",
                    line_range=(1, 3),
                    detection_hints=["missing docstring", "module documentation", "docstring"],
                )
            ],
        ),

        # ==================== 未使用的导入/变量 (3 条) ====================
        SyntheticTestCase(
            id="STYLE-UNUSED-001",
            name="未使用的导入",
            category=IssueCategory.STYLE,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/api.py",
                    language="python",
                    old_start=1,
                    old_count=1,
                    new_start=1,
                    new_count=5,
                    additions=[
                        'import os',
                        'import sys',
                        'import json',
                        'from datetime import datetime',
                        '',
                    ],
                    deletions=["# imports"],
                    context="API 服务",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.STYLE,
                    severity="low",
                    title="未使用的导入",
                    description="导入的模块未在代码中使用，应删除",
                    file_path="src/services/api.py",
                    line_range=(1, 4),
                    detection_hints=["unused import", "import cleanup", "remove import"],
                )
            ],
        ),
        SyntheticTestCase(
            id="STYLE-UNUSED-002",
            name="未使用的变量",
            category=IssueCategory.STYLE,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/processor.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=4,
                    additions=[
                        'def process(data):',
                        '    result = transform(data)',
                        '    unused = data.copy()',
                        '    return result',
                    ],
                    deletions=[
                        'def process(data):',
                        '    pass',
                    ],
                    context="处理器",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.STYLE,
                    severity="low",
                    title="未使用的变量",
                    description="变量 'unused' 已定义但未使用，应删除或使用",
                    file_path="src/utils/processor.py",
                    line_range=(12, 12),
                    detection_hints=["unused variable", "variable cleanup", "remove variable"],
                )
            ],
        ),
        SyntheticTestCase(
            id="STYLE-UNUSED-003",
            name="未使用的参数",
            category=IssueCategory.STYLE,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/handlers/callback.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=3,
                    additions=[
                        'def handle_event(event, context, unused_param):',
                        '    return process(event)',
                        '',
                    ],
                    deletions=[
                        'def handle_event(event, context):',
                        '    pass',
                    ],
                    context="回调处理器",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.STYLE,
                    severity="low",
                    title="未使用的参数",
                    description="参数 'unused_param' 未在函数中使用，应删除或使用",
                    file_path="src/handlers/callback.py",
                    line_range=(15, 15),
                    detection_hints=["unused parameter", "parameter cleanup", "remove parameter"],
                )
            ],
        ),

        # ==================== 魔法数字 (2 条) ====================
        SyntheticTestCase(
            id="STYLE-MAGIC-001",
            name="魔法数字",
            category=IssueCategory.STYLE,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/calculator.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=3,
                    additions=[
                        'def calculate_discount(price):',
                        '    return price * 0.85',
                        '',
                    ],
                    deletions=[
                        'def calculate_discount(price):',
                        '    pass',
                    ],
                    context="计算器",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.STYLE,
                    severity="low",
                    title="魔法数字",
                    description="数字 0.85 应定义为常量并添加说明",
                    file_path="src/utils/calculator.py",
                    line_range=(11, 11),
                    detection_hints=["magic number", "constant", "named constant", "hardcoded value"],
                )
            ],
        ),
        SyntheticTestCase(
            id="STYLE-MAGIC-002",
            name="魔法字符串",
            category=IssueCategory.STYLE,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/status.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=3,
                    additions=[
                        'def get_status_label(status):',
                        '    if status == "pending_approval":',
                        '        return "等待审批"',
                        '    return status',
                    ],
                    deletions=[
                        'def get_status_label(status):',
                        '    pass',
                    ],
                    context="状态服务",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.STYLE,
                    severity="low",
                    title="魔法字符串",
                    description="字符串 \"pending_approval\" 应定义为常量",
                    file_path="src/services/status.py",
                    line_range=(16, 16),
                    detection_hints=["magic string", "constant", "named constant", "hardcoded string"],
                )
            ],
        ),

        # ==================== 过深的嵌套 (2 条) - 补充 ====================
        SyntheticTestCase(
            id="STYLE-NEST-001",
            name="for 循环嵌套过深",
            category=IssueCategory.STYLE,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/analysis/data.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=10,
                    additions=[
                        'def process_data(data):',
                        '    for item in data:',
                        '        for sub_item in item.children:',
                        '            for attr in sub_item.attributes:',
                        '                for value in attr.values:',
                        '                    if value.valid:',
                        '                        process(value)',
                    ],
                    deletions=[
                        'def process_data(data):',
                        '    pass',
                    ],
                    context="数据分析",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.STYLE,
                    severity="medium",
                    title="嵌套过深",
                    description="循环嵌套超过 3 层，应提取为独立函数",
                    file_path="src/analysis/data.py",
                    line_range=(10, 17),
                    detection_hints=["deep nesting", "nested loops", "extract method", "refactor"],
                )
            ],
        ),
        SyntheticTestCase(
            id="STYLE-NEST-002",
            name="try-except 嵌套过深",
            category=IssueCategory.STYLE,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/handler.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=12,
                    additions=[
                        'def handle_request(request):',
                        '    try:',
                        '        try:',
                        '            data = parse(request)',
                        '            try:',
                        '                result = process(data)',
                        '                return result',
                        '            except ProcessingError:',
                        '                return None',
                        '        except ParseError:',
                        '            return None',
                        '    except Exception:',
                        '        return None',
                    ],
                    deletions=[
                        'def handle_request(request):',
                        '    pass',
                    ],
                    context="请求处理",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.STYLE,
                    severity="medium",
                    title="嵌套过深",
                    description="try-except 嵌套过深，应合并或提取函数",
                    file_path="src/services/handler.py",
                    line_range=(15, 26),
                    detection_hints=["deep nesting", "nested try-except", "flatten", "refactor"],
                )
            ],
        ),
    ]
