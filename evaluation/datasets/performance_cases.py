"""
性能类测试用例数据集

包含 25 条性能相关的测试用例，覆盖：
- O(n²) 或更高复杂度算法
- N+1 查询问题
- 内存问题
- 不必要的循环/重复计算
- 低效的字符串操作
- 缺少缓存
- 同步阻塞操作
"""

from __future__ import annotations

from typing import List

from evaluation.datasets.schemas import (
    DiffChunkSchema,
    InjectedIssue,
    IssueCategory,
    SyntheticTestCase,
)


def get_performance_test_cases() -> List[SyntheticTestCase]:
    """获取性能类测试用例列表"""
    return [
        # ==================== O(n²) 复杂度 (5 条) ====================
        SyntheticTestCase(
            id="PERF-COMPLEX-001",
            name="嵌套循环 O(n²)",
            category=IssueCategory.PERFORMANCE,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/search.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=5,
                    additions=[
                        'def find_duplicates(items):',
                        '    duplicates = []',
                        '    for i in range(len(items)):',
                        '        for j in range(i + 1, len(items)):',
                        '            if items[i] == items[j] and items[i] not in duplicates:',
                        '                duplicates.append(items[i])',
                        '    return duplicates',
                    ],
                    deletions=[
                        'def find_duplicates(items):',
                        '    pass',
                    ],
                    context="查找重复项",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="medium",
                    title="O(n²) 时间复杂度",
                    description="使用嵌套循环查找重复项，时间复杂度为 O(n²)，应使用集合优化",
                    file_path="src/utils/search.py",
                    line_range=(12, 15),
                    detection_hints=["O(n²)", "nested loop", "time complexity", "duplicate check"],
                )
            ],
        ),
        SyntheticTestCase(
            id="PERF-COMPLEX-002",
            name="列表查找 O(n)",
            category=IssueCategory.PERFORMANCE,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/lookup.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=4,
                    additions=[
                        'def check_permission(user_id, allowed_users):',
                        '    for user in allowed_users:',
                        '        if user == user_id:',
                        '            return True',
                        '    return False',
                    ],
                    deletions=[
                        'def check_permission(user_id, allowed_users):',
                        '    pass',
                    ],
                    context="权限检查",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="low",
                    title="O(n) 列表查找",
                    description="使用列表进行成员检查，应转换为集合以获得 O(1) 查找",
                    file_path="src/services/lookup.py",
                    line_range=(16, 18),
                    detection_hints=["O(n)", "list lookup", "membership test", "use set"],
                )
            ],
        ),
        SyntheticTestCase(
            id="PERF-COMPLEX-003",
            name="三层嵌套循环 O(n³)",
            category=IssueCategory.PERFORMANCE,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/analysis/triplets.py",
                    language="python",
                    old_start=20,
                    old_count=2,
                    new_start=20,
                    new_count=7,
                    additions=[
                        'def find_triplets(arr, target):',
                        '    result = []',
                        '    for i in range(len(arr)):',
                        '        for j in range(i + 1, len(arr)):',
                        '            for k in range(j + 1, len(arr)):',
                        '                if arr[i] + arr[j] + arr[k] == target:',
                        '                    result.append((arr[i], arr[j], arr[k]))',
                        '    return result',
                    ],
                    deletions=[
                        'def find_triplets(arr, target):',
                        '    pass',
                    ],
                    context="三元组查找",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="high",
                    title="O(n³) 时间复杂度",
                    description="三层嵌套循环，时间复杂度为 O(n³)，应优化算法",
                    file_path="src/analysis/triplets.py",
                    line_range=(22, 26),
                    detection_hints=["O(n³)", "triple nested loop", "time complexity"],
                )
            ],
        ),
        SyntheticTestCase(
            id="PERF-COMPLEX-004",
            name="字符串拼接 O(n²)",
            category=IssueCategory.PERFORMANCE,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/builder.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=4,
                    additions=[
                        'def build_message(items):',
                        '    result = ""',
                        '    for item in items:',
                        '        result += str(item) + ", "',
                        '    return result',
                    ],
                    deletions=[
                        'def build_message(items):',
                        '    pass',
                    ],
                    context="消息构建",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="medium",
                    title="O(n²) 字符串拼接",
                    description="在循环中使用 += 拼接字符串，应使用 join() 方法",
                    file_path="src/utils/builder.py",
                    line_range=(12, 13),
                    detection_hints=["O(n²)", "string concatenation", "+=", "use join"],
                )
            ],
        ),
        SyntheticTestCase(
            id="PERF-COMPLEX-005",
            name="递归无记忆化 O(2^n)",
            category=IssueCategory.PERFORMANCE,
            difficulty="hard",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/algorithms/fibonacci.py",
                    language="python",
                    old_start=5,
                    old_count=2,
                    new_start=5,
                    new_count=4,
                    additions=[
                        'def fibonacci(n):',
                        '    if n <= 1:',
                        '        return n',
                        '    return fibonacci(n - 1) + fibonacci(n - 2)',
                    ],
                    deletions=[
                        'def fibonacci(n):',
                        '    pass',
                    ],
                    context="斐波那契数列",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="high",
                    title="O(2^n) 指数复杂度",
                    description="递归实现斐波那契数列，无记忆化，时间复杂度为 O(2^n)",
                    file_path="src/algorithms/fibonacci.py",
                    line_range=(5, 8),
                    detection_hints=["O(2^n)", "exponential", "fibonacci", "memoization"],
                )
            ],
        ),

        # ==================== N+1 查询问题 (5 条) ====================
        SyntheticTestCase(
            id="PERF-N1-001",
            name="ORM N+1 查询",
            category=IssueCategory.PERFORMANCE,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/api/users.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=5,
                    additions=[
                        'def get_user_orders():',
                        '    users = User.query.all()',
                        '    result = []',
                        '    for user in users:',
                        '        orders = Order.query.filter_by(user_id=user.id).all()',
                        '        result.append({"user": user, "orders": orders})',
                        '    return result',
                    ],
                    deletions=[
                        'def get_user_orders():',
                        '    pass',
                    ],
                    context="用户订单查询",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="high",
                    title="N+1 查询问题",
                    description="在循环中查询数据库，应使用 eager loading 或 join",
                    file_path="src/api/users.py",
                    line_range=(18, 19),
                    detection_hints=["N+1", "query in loop", "eager loading", "select_related"],
                )
            ],
        ),
        SyntheticTestCase(
            id="PERF-N1-002",
            name="Django N+1 查询",
            category=IssueCategory.PERFORMANCE,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/views/articles.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=5,
                    additions=[
                        'def article_list(request):',
                        '    articles = Article.objects.all()',
                        '    data = []',
                        '    for article in articles:',
                        '        comments = article.comments.all()',
                        '        data.append({"article": article, "comment_count": len(comments)})',
                        '    return JsonResponse(data, safe=False)',
                    ],
                    deletions=[
                        'def article_list(request):',
                        '    pass',
                    ],
                    context="文章列表视图",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="high",
                    title="N+1 查询问题",
                    description="在循环中访问关联对象，应使用 prefetch_related",
                    file_path="src/views/articles.py",
                    line_range=(14, 15),
                    detection_hints=["N+1", "prefetch_related", "query in loop"],
                )
            ],
        ),
        SyntheticTestCase(
            id="PERF-N1-003",
            name="SQLAlchemy N+1 查询",
            category=IssueCategory.PERFORMANCE,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/reports.py",
                    language="python",
                    old_start=20,
                    old_count=2,
                    new_start=20,
                    new_count=5,
                    additions=[
                        'def generate_report():',
                        '    departments = session.query(Department).all()',
                        '    for dept in departments:',
                        '        employees = session.query(Employee).filter_by(dept_id=dept.id).all()',
                        '        print(f"{dept.name}: {len(employees)} employees")',
                    ],
                    deletions=[
                        'def generate_report():',
                        '    pass',
                    ],
                    context="部门报告生成",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="high",
                    title="N+1 查询问题",
                    description="在循环中查询员工，应使用 joinedload",
                    file_path="src/services/reports.py",
                    line_range=(22, 23),
                    detection_hints=["N+1", "joinedload", "query in loop"],
                )
            ],
        ),
        SyntheticTestCase(
            id="PERF-N1-004",
            name="GraphQL N+1 查询",
            category=IssueCategory.PERFORMANCE,
            difficulty="hard",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/graphql/resolvers.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=4,
                    additions=[
                        '@graphql.field("posts")',
                        'def resolve_posts(user, info):',
                        '    return Post.query.filter_by(author_id=user.id).all()',
                        '',
                    ],
                    deletions=[
                        '@graphql.field("posts")',
                        'def resolve_posts(user, info):',
                        '    pass',
                    ],
                    context="GraphQL 解析器",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="high",
                    title="N+1 查询问题",
                    description="GraphQL 解析器在列表查询时会导致 N+1 问题，应使用 DataLoader",
                    file_path="src/graphql/resolvers.py",
                    line_range=(17, 17),
                    detection_hints=["N+1", "GraphQL", "DataLoader", "batch loading"],
                )
            ],
        ),
        SyntheticTestCase(
            id="PERF-N1-005",
            name="REST API N+1 查询",
            category=IssueCategory.PERFORMANCE,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/api/products.py",
                    language="python",
                    old_start=25,
                    old_count=2,
                    new_start=25,
                    new_count=5,
                    additions=[
                        'def get_products_with_reviews():',
                        '    products = Product.query.all()',
                        '    result = []',
                        '    for product in products:',
                        '        reviews = Review.query.filter_by(product_id=product.id).all()',
                        '        result.append({"product": product, "reviews": reviews})',
                        '    return jsonify(result)',
                    ],
                    deletions=[
                        'def get_products_with_reviews():',
                        '    pass',
                    ],
                    context="产品评论 API",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="high",
                    title="N+1 查询问题",
                    description="在循环中查询评论，应使用 eager loading",
                    file_path="src/api/products.py",
                    line_range=(28, 29),
                    detection_hints=["N+1", "eager loading", "query in loop"],
                )
            ],
        ),

        # ==================== 内存问题 (4 条) ====================
        SyntheticTestCase(
            id="PERF-MEM-001",
            name="大文件一次性读取",
            category=IssueCategory.PERFORMANCE,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/file_reader.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=3,
                    additions=[
                        'def read_large_file(filepath):',
                        '    with open(filepath) as f:',
                        '        return f.read()',
                    ],
                    deletions=[
                        'def read_large_file(filepath):',
                        '    pass',
                    ],
                    context="大文件读取",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="medium",
                    title="内存效率问题",
                    description="一次性读取大文件到内存，应使用逐行读取或分块读取",
                    file_path="src/utils/file_reader.py",
                    line_range=(12, 12),
                    detection_hints=["memory", "large file", "read()", "read line by line"],
                )
            ],
        ),
        SyntheticTestCase(
            id="PERF-MEM-002",
            name="列表推导式内存问题",
            category=IssueCategory.PERFORMANCE,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/data/processor.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=3,
                    additions=[
                        'def process_large_dataset(data):',
                        '    return [expensive_transform(item) for item in data]',
                        '',
                    ],
                    deletions=[
                        'def process_large_dataset(data):',
                        '    pass',
                    ],
                    context="大数据集处理",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="medium",
                    title="内存效率问题",
                    description="列表推导式会一次性加载所有结果到内存，应考虑使用生成器",
                    file_path="src/data/processor.py",
                    line_range=(16, 16),
                    detection_hints=["memory", "list comprehension", "generator", "large dataset"],
                )
            ],
        ),
        SyntheticTestCase(
            id="PERF-MEM-003",
            name="全局变量内存泄漏",
            category=IssueCategory.PERFORMANCE,
            difficulty="hard",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/cache/store.py",
                    language="python",
                    old_start=5,
                    old_count=1,
                    new_start=5,
                    new_count=3,
                    additions=[
                        '_cache = {}',
                        '',
                        'def add_to_cache(key, value):',
                        '    _cache[key] = value',
                    ],
                    deletions=["# cache implementation"],
                    context="缓存存储",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="high",
                    title="内存泄漏风险",
                    description="无限制的全局缓存会持续增长，应添加大小限制或过期机制",
                    file_path="src/cache/store.py",
                    line_range=(5, 7),
                    detection_hints=["memory leak", "unbounded cache", "global variable", "LRU cache"],
                )
            ],
        ),
        SyntheticTestCase(
            id="PERF-MEM-004",
            name="循环引用内存泄漏",
            category=IssueCategory.PERFORMANCE,
            difficulty="hard",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/models/graph.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=5,
                    additions=[
                        'class Node:',
                        '    def __init__(self):',
                        '        self.children = []',
                        '        self.parent = None',
                        '',
                        '    def add_child(self, child):',
                        '        self.children.append(child)',
                        '        child.parent = self',
                    ],
                    deletions=[
                        'class Node:',
                        '    pass',
                    ],
                    context="图节点",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="medium",
                    title="循环引用内存泄漏",
                    description="父子节点相互引用可能导致内存泄漏，应使用弱引用",
                    file_path="src/models/graph.py",
                    line_range=(12, 17),
                    detection_hints=["memory leak", "circular reference", "weakref", "parent-child"],
                )
            ],
        ),

        # ==================== 不必要的循环/重复计算 (4 条) ====================
        SyntheticTestCase(
            id="PERF-REDUNDANT-001",
            name="循环内重复计算",
            category=IssueCategory.PERFORMANCE,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/calculate.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=4,
                    additions=[
                        'def process_items(items):',
                        '    for item in items:',
                        '        result = complex_calculation(len(items))',
                        '        process(item, result)',
                    ],
                    deletions=[
                        'def process_items(items):',
                        '    pass',
                    ],
                    context="项目处理",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="low",
                    title="重复计算",
                    description="循环内重复计算 len(items)，应提取到循环外",
                    file_path="src/utils/calculate.py",
                    line_range=(12, 13),
                    detection_hints=["redundant calculation", "loop invariant", "hoist"],
                )
            ],
        ),
        SyntheticTestCase(
            id="PERF-REDUNDANT-002",
            name="重复数据库查询",
            category=IssueCategory.PERFORMANCE,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/user_service.py",
                    language="python",
                    old_start=20,
                    old_count=2,
                    new_start=20,
                    new_count=5,
                    additions=[
                        'def update_user_profile(user_id, data):',
                        '    user = User.query.get(user_id)',
                        '    validate_user(user_id)',
                        '    user.name = data["name"]',
                        '    db.session.commit()',
                        '',
                        'def validate_user(user_id):',
                        '    user = User.query.get(user_id)',
                        '    return user.is_active',
                    ],
                    deletions=[
                        'def update_user_profile(user_id, data):',
                        '    pass',
                    ],
                    context="用户服务",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="medium",
                    title="重复数据库查询",
                    description="同一请求中多次查询同一用户，应复用查询结果",
                    file_path="src/services/user_service.py",
                    line_range=(21, 27),
                    detection_hints=["redundant query", "duplicate query", "cache result"],
                )
            ],
        ),
        SyntheticTestCase(
            id="PERF-REDUNDANT-003",
            name="不必要的类型转换",
            category=IssueCategory.PERFORMANCE,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/transform.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=4,
                    additions=[
                        'def process_list(items):',
                        '    for item in list(items):',
                        '        result = str(str(item))',
                        '        save(result)',
                    ],
                    deletions=[
                        'def process_list(items):',
                        '    pass',
                    ],
                    context="列表处理",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="low",
                    title="不必要的类型转换",
                    description="重复的类型转换 list() 和 str() 是多余的",
                    file_path="src/utils/transform.py",
                    line_range=(16, 17),
                    detection_hints=["redundant conversion", "unnecessary cast", "str(str("],
                )
            ],
        ),
        SyntheticTestCase(
            id="PERF-REDUNDANT-004",
            name="重复的正则编译",
            category=IssueCategory.PERFORMANCE,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/validator.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=4,
                    additions=[
                        'def validate_emails(emails):',
                        '    for email in emails:',
                        '        pattern = re.compile(r"^[\\w.-]+@[\\w.-]+\\.\\w+$")',
                        '        if not pattern.match(email):',
                        '            return False',
                        '    return True',
                    ],
                    deletions=[
                        'def validate_emails(emails):',
                        '    pass',
                    ],
                    context="邮箱验证",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="medium",
                    title="重复的正则编译",
                    description="在循环中重复编译正则表达式，应提取到循环外",
                    file_path="src/utils/validator.py",
                    line_range=(12, 13),
                    detection_hints=["redundant compilation", "regex compile", "loop invariant"],
                )
            ],
        ),

        # ==================== 低效的字符串操作 (3 条) ====================
        SyntheticTestCase(
            id="PERF-STR-001",
            name="字符串格式化效率",
            category=IssueCategory.PERFORMANCE,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/formatter.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=3,
                    additions=[
                        'def format_user_info(user):',
                        '    return "Name: " + user.name + ", Email: " + user.email + ", Age: " + str(user.age)',
                        '',
                    ],
                    deletions=[
                        'def format_user_info(user):',
                        '    pass',
                    ],
                    context="用户信息格式化",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="low",
                    title="低效的字符串拼接",
                    description="使用 + 拼接字符串效率低，应使用 f-string 或 format",
                    file_path="src/utils/formatter.py",
                    line_range=(11, 11),
                    detection_hints=["string concatenation", "f-string", "format method"],
                )
            ],
        ),
        SyntheticTestCase(
            id="PERF-STR-002",
            name="字符串重复操作",
            category=IssueCategory.PERFORMANCE,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/template.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=4,
                    additions=[
                        'def generate_report(data):',
                        '    result = ""',
                        '    for key, value in data.items():',
                        '        result = result + f"{key}: {value}\\n"',
                        '    return result',
                    ],
                    deletions=[
                        'def generate_report(data):',
                        '    pass',
                    ],
                    context="报告生成",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="medium",
                    title="低效的字符串累积",
                    description="在循环中使用 += 累积字符串，应使用列表 join",
                    file_path="src/utils/template.py",
                    line_range=(17, 18),
                    detection_hints=["string accumulation", "list join", "StringBuilder"],
                )
            ],
        ),
        SyntheticTestCase(
            id="PERF-STR-003",
            name="字符串切片效率",
            category=IssueCategory.PERFORMANCE,
            difficulty="hard",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/parsers/text.py",
                    language="python",
                    old_start=20,
                    old_count=2,
                    new_start=20,
                    new_count=4,
                    additions=[
                        'def remove_prefix(text, prefix):',
                        '    while text.startswith(prefix):',
                        '        text = text[len(prefix):]',
                        '    return text',
                    ],
                    deletions=[
                        'def remove_prefix(text, prefix):',
                        '    pass',
                    ],
                    context="文本处理",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="low",
                    title="低效的字符串处理",
                    description="使用循环和切片移除前缀，应使用 str.removeprefix()",
                    file_path="src/parsers/text.py",
                    line_range=(21, 22),
                    detection_hints=["string slicing", "removeprefix", "lstrip"],
                )
            ],
        ),

        # ==================== 缺少缓存 (2 条) ====================
        SyntheticTestCase(
            id="PERF-CACHE-001",
            name="缺少函数结果缓存",
            category=IssueCategory.PERFORMANCE,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/pricing.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=4,
                    additions=[
                        'def calculate_price(product_id):',
                        '    product = get_product_from_db(product_id)',
                        '    base_price = product.price',
                        '    return base_price * get_tax_rate(product.category)',
                    ],
                    deletions=[
                        'def calculate_price(product_id):',
                        '    pass',
                    ],
                    context="价格计算",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="medium",
                    title="缺少缓存",
                    description="频繁调用的函数没有缓存结果，应使用 @lru_cache",
                    file_path="src/services/pricing.py",
                    line_range=(10, 13),
                    detection_hints=["missing cache", "lru_cache", "memoization", "expensive function"],
                )
            ],
        ),
        SyntheticTestCase(
            id="PERF-CACHE-002",
            name="缺少 HTTP 缓存",
            category=IssueCategory.PERFORMANCE,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/api/external.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=3,
                    additions=[
                        'def get_exchange_rate(currency):',
                        '    response = requests.get(f"https://api.example.com/rate/{currency}")',
                        '    return response.json()["rate"]',
                    ],
                    deletions=[
                        'def get_exchange_rate(currency):',
                        '    pass',
                    ],
                    context="汇率查询",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="medium",
                    title="缺少 HTTP 缓存",
                    description="频繁请求外部 API 没有缓存，应添加缓存机制",
                    file_path="src/api/external.py",
                    line_range=(16, 17),
                    detection_hints=["missing cache", "HTTP cache", "external API", "requests"],
                )
            ],
        ),

        # ==================== 同步阻塞操作 (2 条) ====================
        SyntheticTestCase(
            id="PERF-BLOCK-001",
            name="同步 HTTP 请求阻塞",
            category=IssueCategory.PERFORMANCE,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/api/fetcher.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=4,
                    additions=[
                        'def fetch_multiple_urls(urls):',
                        '    results = []',
                        '    for url in urls:',
                        '        results.append(requests.get(url).json())',
                        '    return results',
                    ],
                    deletions=[
                        'def fetch_multiple_urls(urls):',
                        '    pass',
                    ],
                    context="URL 批量获取",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="high",
                    title="同步阻塞操作",
                    description="顺序执行 HTTP 请求效率低，应使用异步或并发",
                    file_path="src/api/fetcher.py",
                    line_range=(12, 13),
                    detection_hints=["blocking I/O", "async", "concurrent", "aiohttp", "ThreadPoolExecutor"],
                )
            ],
        ),
        SyntheticTestCase(
            id="PERF-BLOCK-002",
            name="同步文件 I/O 阻塞",
            category=IssueCategory.PERFORMANCE,
            difficulty="hard",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/importer.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=4,
                    additions=[
                        'def import_files(file_paths):',
                        '    for path in file_paths:',
                        '        with open(path) as f:',
                        '            process_file(f.read())',
                    ],
                    deletions=[
                        'def import_files(file_paths):',
                        '    pass',
                    ],
                    context="文件导入服务",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.PERFORMANCE,
                    severity="medium",
                    title="同步阻塞操作",
                    description="顺序读取文件效率低，应使用异步 I/O 或线程池",
                    file_path="src/services/importer.py",
                    line_range=(16, 18),
                    detection_hints=["blocking I/O", "async file I/O", "aiofiles", "ThreadPoolExecutor"],
                )
            ],
        ),
    ]
