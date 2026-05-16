"""
逻辑类测试用例数据集

包含 25 条逻辑相关的测试用例，覆盖：
- 空指针/None 检查缺失
- 边界条件错误
- 类型错误
- 条件判断错误
- 异常处理不当
- 并发问题
- 资源泄漏
"""

from __future__ import annotations

from typing import List

from evaluation.datasets.schemas import (
    DiffChunkSchema,
    InjectedIssue,
    IssueCategory,
    SyntheticTestCase,
)


def get_logic_test_cases() -> List[SyntheticTestCase]:
    """获取逻辑类测试用例列表"""
    return [
        # ==================== 空指针/None 检查缺失 (5 条) ====================
        SyntheticTestCase(
            id="LOGIC-NULL-001",
            name="缺少 None 检查",
            category=IssueCategory.LOGIC,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/user.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=3,
                    additions=[
                        'def get_user_name(user_id):',
                        '    user = db.query(User).get(user_id)',
                        '    return user.name',
                    ],
                    deletions=[
                        'def get_user_name(user_id):',
                        '    pass',
                    ],
                    context="用户服务",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="high",
                    title="缺少 None 检查",
                    description="查询结果可能为 None，直接访问属性会导致 AttributeError",
                    file_path="src/services/user.py",
                    line_range=(16, 17),
                    detection_hints=["None check", "null pointer", "AttributeError", "missing validation"],
                )
            ],
        ),
        SyntheticTestCase(
            id="LOGIC-NULL-002",
            name="字典键不存在",
            category=IssueCategory.LOGIC,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/config.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=3,
                    additions=[
                        'def get_config_value(key):',
                        '    config = load_config()',
                        '    return config[key]',
                    ],
                    deletions=[
                        'def get_config_value(key):',
                        '    pass',
                    ],
                    context="配置工具",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="medium",
                    title="缺少键存在检查",
                    description="直接访问字典键可能导致 KeyError，应使用 get() 方法",
                    file_path="src/utils/config.py",
                    line_range=(12, 12),
                    detection_hints=["KeyError", "dict access", "use get()", "key check"],
                )
            ],
        ),
        SyntheticTestCase(
            id="LOGIC-NULL-003",
            name="列表索引越界",
            category=IssueCategory.LOGIC,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/parser.py",
                    language="python",
                    old_start=20,
                    old_count=2,
                    new_start=20,
                    new_count=3,
                    additions=[
                        'def get_first_item(items):',
                        '    return items[0]',
                        '',
                    ],
                    deletions=[
                        'def get_first_item(items):',
                        '    pass',
                    ],
                    context="解析工具",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="medium",
                    title="缺少列表长度检查",
                    description="空列表访问索引 0 会导致 IndexError",
                    file_path="src/utils/parser.py",
                    line_range=(21, 21),
                    detection_hints=["IndexError", "list index", "empty list", "bounds check"],
                )
            ],
        ),
        SyntheticTestCase(
            id="LOGIC-NULL-004",
            name="可选参数未检查",
            category=IssueCategory.LOGIC,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/api/handler.py",
                    language="python",
                    old_start=25,
                    old_count=2,
                    new_start=25,
                    new_count=4,
                    additions=[
                        'def process_request(request, user=None):',
                        '    data = request.json',
                        '    user_id = user.id',
                        '    return process(data, user_id)',
                    ],
                    deletions=[
                        'def process_request(request, user=None):',
                        '    pass',
                    ],
                    context="请求处理",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="high",
                    title="缺少可选参数检查",
                    description="可选参数 user 可能为 None，直接访问属性会导致错误",
                    file_path="src/api/handler.py",
                    line_range=(27, 27),
                    detection_hints=["None check", "optional parameter", "AttributeError"],
                )
            ],
        ),
        SyntheticTestCase(
            id="LOGIC-NULL-005",
            name="API 响应未检查",
            category=IssueCategory.LOGIC,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/api_client.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=3,
                    additions=[
                        'def fetch_user_data(user_id):',
                        '    response = requests.get(f"/api/users/{user_id}")',
                        '    return response.json()["data"]',
                    ],
                    deletions=[
                        'def fetch_user_data(user_id):',
                        '    pass',
                    ],
                    context="API 客户端",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="high",
                    title="缺少响应状态检查",
                    description="未检查 HTTP 响应状态码，可能导致意外错误",
                    file_path="src/services/api_client.py",
                    line_range=(16, 17),
                    detection_hints=["response check", "status code", "raise_for_status", "error handling"],
                )
            ],
        ),

        # ==================== 边界条件错误 (5 条) ====================
        SyntheticTestCase(
            id="LOGIC-BOUND-001",
            name="整数溢出风险",
            category=IssueCategory.LOGIC,
            difficulty="hard",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/calculator.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=3,
                    additions=[
                        'def calculate_total(items):',
                        '    total = 0',
                        '    for item in items:',
                        '        total += item.value * item.quantity',
                        '    return total',
                    ],
                    deletions=[
                        'def calculate_total(items):',
                        '    pass',
                    ],
                    context="计算工具",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="medium",
                    title="整数溢出风险",
                    description="大量数据累加可能导致整数溢出，应考虑使用大整数或检查边界",
                    file_path="src/utils/calculator.py",
                    line_range=(12, 13),
                    detection_hints=["integer overflow", "boundary check", "large numbers"],
                )
            ],
        ),
        SyntheticTestCase(
            id="LOGIC-BOUND-002",
            name="除零错误",
            category=IssueCategory.LOGIC,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/math_utils.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=3,
                    additions=[
                        'def calculate_average(total, count):',
                        '    return total / count',
                        '',
                    ],
                    deletions=[
                        'def calculate_average(total, count):',
                        '    pass',
                    ],
                    context="数学工具",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="high",
                    title="除零错误",
                    description="未检查除数是否为 0，会导致 ZeroDivisionError",
                    file_path="src/utils/math_utils.py",
                    line_range=(16, 16),
                    detection_hints=["ZeroDivisionError", "divide by zero", "check count"],
                )
            ],
        ),
        SyntheticTestCase(
            id="LOGIC-BOUND-003",
            name="数组边界检查缺失",
            category=IssueCategory.LOGIC,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/array_utils.py",
                    language="python",
                    old_start=20,
                    old_count=2,
                    new_start=20,
                    new_count=4,
                    additions=[
                        'def get_neighbors(arr, index):',
                        '    return [arr[index - 1], arr[index + 1]]',
                        '',
                    ],
                    deletions=[
                        'def get_neighbors(arr, index):',
                        '    pass',
                    ],
                    context="数组工具",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="medium",
                    title="数组边界检查缺失",
                    description="访问 index-1 和 index+1 时未检查边界条件",
                    file_path="src/utils/array_utils.py",
                    line_range=(21, 21),
                    detection_hints=["IndexError", "boundary check", "array bounds"],
                )
            ],
        ),
        SyntheticTestCase(
            id="LOGIC-BOUND-004",
            name="循环终止条件错误",
            category=IssueCategory.LOGIC,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/algorithms/search.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=6,
                    additions=[
                        'def binary_search(arr, target):',
                        '    left, right = 0, len(arr)',
                        '    while left < right:',
                        '        mid = (left + right) // 2',
                        '        if arr[mid] == target:',
                        '            return mid',
                        '        elif arr[mid] < target:',
                        '            left = mid',
                        '        else:',
                        '            right = mid',
                        '    return -1',
                    ],
                    deletions=[
                        'def binary_search(arr, target):',
                        '    pass',
                    ],
                    context="二分查找",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="medium",
                    title="循环终止条件错误",
                    description="二分查找边界条件设置错误，可能导致无限循环或漏查",
                    file_path="src/algorithms/search.py",
                    line_range=(11, 19),
                    detection_hints=["infinite loop", "binary search", "boundary condition", "off-by-one"],
                )
            ],
        ),
        SyntheticTestCase(
            id="LOGIC-BOUND-005",
            name="日期边界检查缺失",
            category=IssueCategory.LOGIC,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/date_utils.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=4,
                    additions=[
                        'def get_days_in_month(year, month):',
                        '    return [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]',
                        '',
                    ],
                    deletions=[
                        'def get_days_in_month(year, month):',
                        '    pass',
                    ],
                    context="日期工具",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="medium",
                    title="参数边界检查缺失",
                    description="未检查 month 是否在 1-12 范围内，可能导致 IndexError",
                    file_path="src/utils/date_utils.py",
                    line_range=(16, 16),
                    detection_hints=["IndexError", "parameter validation", "month range"],
                )
            ],
        ),

        # ==================== 类型错误 (4 条) ====================
        SyntheticTestCase(
            id="LOGIC-TYPE-001",
            name="类型比较错误",
            category=IssueCategory.LOGIC,
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
                        'def is_valid_age(age):',
                        '    return age > 0 and age < 150',
                        '',
                    ],
                    deletions=[
                        'def is_valid_age(age):',
                        '    pass',
                    ],
                    context="验证工具",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="medium",
                    title="缺少类型检查",
                    description="未检查 age 是否为数字类型，字符串比较可能导致意外结果",
                    file_path="src/utils/validator.py",
                    line_range=(11, 11),
                    detection_hints=["type check", "TypeError", "isinstance", "numeric comparison"],
                )
            ],
        ),
        SyntheticTestCase(
            id="LOGIC-TYPE-002",
            name="字符串数字混合比较",
            category=IssueCategory.LOGIC,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/comparison.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=3,
                    additions=[
                        'def compare_values(a, b):',
                        '    return a > b',
                        '',
                    ],
                    deletions=[
                        'def compare_values(a, b):',
                        '    pass',
                    ],
                    context="比较服务",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="medium",
                    title="类型不一致比较",
                    description="未检查比较值的类型，可能导致 TypeError 或意外结果",
                    file_path="src/services/comparison.py",
                    line_range=(16, 16),
                    detection_hints=["TypeError", "type mismatch", "comparison", "isinstance"],
                )
            ],
        ),
        SyntheticTestCase(
            id="LOGIC-TYPE-003",
            name="类型转换错误",
            category=IssueCategory.LOGIC,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/converter.py",
                    language="python",
                    old_start=20,
                    old_count=2,
                    new_start=20,
                    new_count=3,
                    additions=[
                        'def to_int(value):',
                        '    return int(value)',
                        '',
                    ],
                    deletions=[
                        'def to_int(value):',
                        '    pass',
                    ],
                    context="转换工具",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="medium",
                    title="缺少异常处理",
                    description="int() 转换可能失败，应添加异常处理",
                    file_path="src/utils/converter.py",
                    line_range=(21, 21),
                    detection_hints=["ValueError", "type conversion", "try-except", "int()"],
                )
            ],
        ),
        SyntheticTestCase(
            id="LOGIC-TYPE-004",
            name="可变默认参数",
            category=IssueCategory.LOGIC,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/container.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=3,
                    additions=[
                        'def add_item(item, items=[]):',
                        '    items.append(item)',
                        '    return items',
                    ],
                    deletions=[
                        'def add_item(item, items=[]):',
                        '    pass',
                    ],
                    context="容器工具",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="high",
                    title="可变默认参数",
                    description="使用可变对象作为默认参数，会导致状态共享问题",
                    file_path="src/utils/container.py",
                    line_range=(10, 12),
                    detection_hints=["mutable default", "default argument", "list default", "None default"],
                )
            ],
        ),

        # ==================== 条件判断错误 (4 条) ====================
        SyntheticTestCase(
            id="LOGIC-COND-001",
            name="错误的布尔逻辑",
            category=IssueCategory.LOGIC,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/auth.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=3,
                    additions=[
                        'def is_admin(user):',
                        '    return user.role == "admin" or "superuser"',
                        '',
                    ],
                    deletions=[
                        'def is_admin(user):',
                        '    pass',
                    ],
                    context="认证工具",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="high",
                    title="布尔逻辑错误",
                    description="'or \"superuser\"' 总是为 True，应使用 'in' 或完整比较",
                    file_path="src/utils/auth.py",
                    line_range=(16, 16),
                    detection_hints=["boolean logic", "always true", "or operator", "comparison error"],
                )
            ],
        ),
        SyntheticTestCase(
            id="LOGIC-COND-002",
            name="赋值与比较混淆",
            category=IssueCategory.LOGIC,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/check.py",
                    language="python",
                    old_start=20,
                    old_count=2,
                    new_start=20,
                    new_count=3,
                    additions=[
                        'def check_status(status):',
                        '    if status = "active":',
                        '        return True',
                        '    return False',
                    ],
                    deletions=[
                        'def check_status(status):',
                        '    pass',
                    ],
                    context="状态检查",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="critical",
                    title="赋值与比较混淆",
                    description="在条件中使用 = 赋值而非 == 比较",
                    file_path="src/services/check.py",
                    line_range=(21, 21),
                    detection_hints=["assignment in condition", "= vs ==", "comparison operator"],
                )
            ],
        ),
        SyntheticTestCase(
            id="LOGIC-COND-003",
            name="错误的短路求值",
            category=IssueCategory.LOGIC,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/validation.py",
                    language="python",
                    old_start=25,
                    old_count=2,
                    new_start=25,
                    new_count=3,
                    additions=[
                        'def validate_input(data):',
                        '    return data and data.get("name") and data.get("age") > 0',
                        '',
                    ],
                    deletions=[
                        'def validate_input(data):',
                        '    pass',
                    ],
                    context="输入验证",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="medium",
                    title="短路求值错误",
                    description="data.get(\"age\") 可能返回 None，与 0 比较会导致 TypeError",
                    file_path="src/utils/validation.py",
                    line_range=(26, 26),
                    detection_hints=["TypeError", "short-circuit", "None comparison", "chained conditions"],
                )
            ],
        ),
        SyntheticTestCase(
            id="LOGIC-COND-004",
            name="switch 缺少 default",
            category=IssueCategory.LOGIC,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/router.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=8,
                    additions=[
                        'def handle_action(action):',
                        '    if action == "create":',
                        '        return create_item()',
                        '    elif action == "update":',
                        '        return update_item()',
                        '    elif action == "delete":',
                        '        return delete_item()',
                        '    # no default case',
                    ],
                    deletions=[
                        'def handle_action(action):',
                        '    pass',
                    ],
                    context="路由处理",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="medium",
                    title="缺少默认分支",
                    description="条件分支没有处理未知 action 的情况",
                    file_path="src/utils/router.py",
                    line_range=(10, 17),
                    detection_hints=["missing default", "unhandled case", "else branch", "unknown action"],
                )
            ],
        ),

        # ==================== 异常处理不当 (3 条) ====================
        SyntheticTestCase(
            id="LOGIC-EXCEPT-001",
            name="裸 except 捕获",
            category=IssueCategory.LOGIC,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/runner.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=4,
                    additions=[
                        'def safe_execute(func):',
                        '    try:',
                        '        return func()',
                        '    except:',
                        '        pass',
                    ],
                    deletions=[
                        'def safe_execute(func):',
                        '    pass',
                    ],
                    context="执行器",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="high",
                    title="裸 except 捕获",
                    description="使用裸 except 会捕获所有异常包括 KeyboardInterrupt，应指定异常类型",
                    file_path="src/utils/runner.py",
                    line_range=(17, 18),
                    detection_hints=["bare except", "Exception", "specific exception", "KeyboardInterrupt"],
                )
            ],
        ),
        SyntheticTestCase(
            id="LOGIC-EXCEPT-002",
            name="异常被静默忽略",
            category=IssueCategory.LOGIC,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/processor.py",
                    language="python",
                    old_start=20,
                    old_count=2,
                    new_start=20,
                    new_count=5,
                    additions=[
                        'def process_data(data):',
                        '    try:',
                        '        result = transform(data)',
                        '    except ValueError:',
                        '        pass',
                        '    return result',
                    ],
                    deletions=[
                        'def process_data(data):',
                        '    pass',
                    ],
                    context="数据处理",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="medium",
                    title="异常被静默忽略",
                    description="捕获异常后未记录或处理，可能导致问题难以排查",
                    file_path="src/services/processor.py",
                    line_range=(22, 24),
                    detection_hints=["silent exception", "pass in except", "log exception", "error handling"],
                )
            ],
        ),
        SyntheticTestCase(
            id="LOGIC-EXCEPT-003",
            name="异常处理范围过大",
            category=IssueCategory.LOGIC,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/api/endpoint.py",
                    language="python",
                    old_start=25,
                    old_count=2,
                    new_start=25,
                    new_count=6,
                    additions=[
                        'def handle_request(request):',
                        '    try:',
                        '        data = parse_request(request)',
                        '        result = process(data)',
                        '        save(result)',
                        '        return result',
                        '    except Exception as e:',
                        '        return {"error": str(e)}',
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
                    category=IssueCategory.LOGIC,
                    severity="medium",
                    title="异常处理范围过大",
                    description="try 块包含过多代码，应缩小异常捕获范围",
                    file_path="src/api/endpoint.py",
                    line_range=(26, 31),
                    detection_hints=["broad except", "large try block", "narrow exception scope"],
                )
            ],
        ),

        # ==================== 并发问题 (2 条) ====================
        SyntheticTestCase(
            id="LOGIC-CONC-001",
            name="竞态条件",
            category=IssueCategory.LOGIC,
            difficulty="hard",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/counter.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=4,
                    additions=[
                        'counter = 0',
                        '',
                        'def increment():',
                        '    global counter',
                        '    current = counter',
                        '    counter = current + 1',
                    ],
                    deletions=[
                        'def increment():',
                        '    pass',
                    ],
                    context="计数器服务",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="high",
                    title="竞态条件",
                    description="非原子操作在多线程环境下会导致竞态条件，应使用锁",
                    file_path="src/services/counter.py",
                    line_range=(10, 15),
                    detection_hints=["race condition", "thread safety", "lock", "atomic operation"],
                )
            ],
        ),
        SyntheticTestCase(
            id="LOGIC-CONC-002",
            name="死锁风险",
            category=IssueCategory.LOGIC,
            difficulty="hard",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/transfer.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=8,
                    additions=[
                        'def transfer(from_account, to_account, amount):',
                        '    lock_a = get_lock(from_account)',
                        '    lock_a.acquire()',
                        '    lock_b = get_lock(to_account)',
                        '    lock_b.acquire()',
                        '    # transfer logic',
                        '    lock_a.release()',
                        '    lock_b.release()',
                    ],
                    deletions=[
                        'def transfer(from_account, to_account, amount):',
                        '    pass',
                    ],
                    context="转账服务",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="critical",
                    title="死锁风险",
                    description="按不同顺序获取锁可能导致死锁，应使用锁排序或超时",
                    file_path="src/services/transfer.py",
                    line_range=(16, 22),
                    detection_hints=["deadlock", "lock ordering", "lock timeout", "circular wait"],
                )
            ],
        ),

        # ==================== 资源泄漏 (2 条) ====================
        SyntheticTestCase(
            id="LOGIC-RESOURCE-001",
            name="文件资源泄漏",
            category=IssueCategory.LOGIC,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/file_handler.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=4,
                    additions=[
                        'def read_file(path):',
                        '    f = open(path)',
                        '    content = f.read()',
                        '    return content',
                    ],
                    deletions=[
                        'def read_file(path):',
                        '    pass',
                    ],
                    context="文件处理",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="medium",
                    title="资源泄漏",
                    description="文件未关闭，应使用 with 语句",
                    file_path="src/utils/file_handler.py",
                    line_range=(11, 13),
                    detection_hints=["resource leak", "file not closed", "use with", "close()"],
                )
            ],
        ),
        SyntheticTestCase(
            id="LOGIC-RESOURCE-002",
            name="数据库连接泄漏",
            category=IssueCategory.LOGIC,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/db/connection.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=4,
                    additions=[
                        'def get_user(user_id):',
                        '    conn = create_connection()',
                        '    cursor = conn.cursor()',
                        '    return cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()',
                    ],
                    deletions=[
                        'def get_user(user_id):',
                        '    pass',
                    ],
                    context="数据库连接",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.LOGIC,
                    severity="high",
                    title="资源泄漏",
                    description="数据库连接未关闭，应使用 context manager 或 try-finally",
                    file_path="src/db/connection.py",
                    line_range=(16, 18),
                    detection_hints=["resource leak", "connection not closed", "context manager", "try-finally"],
                )
            ],
        ),
    ]
