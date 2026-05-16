"""
安全类测试用例数据集

包含 30 条安全相关的测试用例，覆盖：
- SQL 注入
- XSS (跨站脚本攻击)
- 硬编码密钥/密码
- 命令注入
- 路径遍历
- 不安全的反序列化
- 敏感信息泄露
- SSRF (服务器端请求伪造)
"""

from __future__ import annotations

from typing import List

from evaluation.datasets.schemas import (
    DiffChunkSchema,
    InjectedIssue,
    IssueCategory,
    SyntheticTestCase,
)


def get_security_test_cases() -> List[SyntheticTestCase]:
    """获取安全类测试用例列表"""
    return [
        # ==================== SQL 注入 (5 条) ====================
        SyntheticTestCase(
            id="SEC-SQL-001",
            name="f-string SQL 注入",
            category=IssueCategory.SECURITY,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/db/query.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=3,
                    additions=[
                        'def get_user(user_id):',
                        '    query = f"SELECT * FROM users WHERE id = {user_id}"',
                        '    return db.execute(query)',
                    ],
                    deletions=[
                        'def get_user(user_id):',
                        '    pass',
                    ],
                    context="数据库查询函数",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="critical",
                    title="SQL 注入漏洞",
                    description="用户输入直接拼接到 SQL 语句，可能导致 SQL 注入攻击",
                    file_path="src/db/query.py",
                    line_range=(11, 11),
                    detection_hints=["SQL injection", "f-string", "string concatenation"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-SQL-002",
            name="字符串拼接 SQL 注入",
            category=IssueCategory.SECURITY,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/models/user.py",
                    language="python",
                    old_start=25,
                    old_count=1,
                    new_start=25,
                    new_count=2,
                    additions=[
                        'query = "SELECT * FROM users WHERE name = \'" + username + "\'"',
                        'cursor.execute(query)',
                    ],
                    deletions=["# TODO: implement query"],
                    context="用户查询",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="critical",
                    title="SQL 注入漏洞",
                    description="使用字符串拼接构造 SQL 语句，存在注入风险",
                    file_path="src/models/user.py",
                    line_range=(25, 25),
                    detection_hints=["SQL injection", "string concatenation", "+ username"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-SQL-003",
            name="format 方法 SQL 注入",
            category=IssueCategory.SECURITY,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/api/search.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=3,
                    additions=[
                        'def search_products(keyword):',
                        '    sql = "SELECT * FROM products WHERE name LIKE \'%{}%\'".format(keyword)',
                        '    return db.query(sql)',
                    ],
                    deletions=[
                        'def search_products(keyword):',
                        '    pass',
                    ],
                    context="产品搜索 API",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="critical",
                    title="SQL 注入漏洞",
                    description="使用 format 方法构造 SQL 语句，存在注入风险",
                    file_path="src/api/search.py",
                    line_range=(16, 16),
                    detection_hints=["SQL injection", ".format(", "LIKE"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-SQL-004",
            name="% 格式化 SQL 注入",
            category=IssueCategory.SECURITY,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/auth.py",
                    language="python",
                    old_start=30,
                    old_count=1,
                    new_start=30,
                    new_count=2,
                    additions=[
                        'query = "SELECT * FROM users WHERE email = \'%s\'" % email',
                        'result = db.execute(query)',
                    ],
                    deletions=["# authentication query"],
                    context="认证服务",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="critical",
                    title="SQL 注入漏洞",
                    description="使用 % 格式化构造 SQL 语句，存在注入风险",
                    file_path="src/services/auth.py",
                    line_range=(30, 30),
                    detection_hints=["SQL injection", "%s", "% email"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-SQL-005",
            name="ORDER BY SQL 注入",
            category=IssueCategory.SECURITY,
            difficulty="hard",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/api/list.py",
                    language="python",
                    old_start=20,
                    old_count=2,
                    new_start=20,
                    new_count=3,
                    additions=[
                        'def get_sorted_users(sort_field):',
                        '    query = f"SELECT * FROM users ORDER BY {sort_field}"',
                        '    return db.execute(query)',
                    ],
                    deletions=[
                        'def get_sorted_users(sort_field):',
                        '    pass',
                    ],
                    context="用户列表排序",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="high",
                    title="SQL 注入漏洞 (ORDER BY)",
                    description="ORDER BY 子句使用用户输入，可能导致 SQL 注入",
                    file_path="src/api/list.py",
                    line_range=(21, 21),
                    detection_hints=["SQL injection", "ORDER BY", "f-string"],
                )
            ],
        ),

        # ==================== XSS (5 条) ====================
        SyntheticTestCase(
            id="SEC-XSS-001",
            name="innerHTML XSS",
            category=IssueCategory.SECURITY,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/frontend/display.js",
                    language="javascript",
                    old_start=10,
                    old_count=1,
                    new_start=10,
                    new_count=2,
                    additions=[
                        'function showComment(comment) {',
                        '    document.getElementById("comments").innerHTML = comment;',
                    ],
                    deletions=["// display comment"],
                    context="评论显示",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="high",
                    title="XSS 漏洞",
                    description="使用 innerHTML 直接插入用户输入，可能导致 XSS 攻击",
                    file_path="src/frontend/display.js",
                    line_range=(11, 11),
                    detection_hints=["XSS", "innerHTML", "cross-site scripting"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-XSS-002",
            name="document.write XSS",
            category=IssueCategory.SECURITY,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/frontend/render.js",
                    language="javascript",
                    old_start=5,
                    old_count=1,
                    new_start=5,
                    new_count=2,
                    additions=[
                        'function renderUserInput(input) {',
                        '    document.write("<div>" + input + "</div>");',
                    ],
                    deletions=["// render function"],
                    context="用户输入渲染",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="high",
                    title="XSS 漏洞",
                    description="使用 document.write 插入用户输入，存在 XSS 风险",
                    file_path="src/frontend/render.js",
                    line_range=(6, 6),
                    detection_hints=["XSS", "document.write", "cross-site scripting"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-XSS-003",
            name="eval XSS",
            category=IssueCategory.SECURITY,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/frontend/calculator.js",
                    language="javascript",
                    old_start=15,
                    old_count=1,
                    new_start=15,
                    new_count=2,
                    additions=[
                        'function calculate(expression) {',
                        '    return eval(expression);',
                    ],
                    deletions=["// calculator"],
                    context="计算器功能",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="critical",
                    title="代码注入漏洞",
                    description="使用 eval 执行用户输入，可能导致任意代码执行",
                    file_path="src/frontend/calculator.js",
                    line_range=(16, 16),
                    detection_hints=["XSS", "eval", "code injection", "arbitrary code execution"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-XSS-004",
            name="React dangerouslySetInnerHTML XSS",
            category=IssueCategory.SECURITY,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/components/Comment.jsx",
                    language="javascript",
                    old_start=8,
                    old_count=2,
                    new_start=8,
                    new_count=4,
                    additions=[
                        'function Comment({ content }) {',
                        '    return (',
                        '        <div dangerouslySetInnerHTML={{ __html: content }} />',
                        '    );',
                    ],
                    deletions=[
                        'function Comment({ content }) {',
                        '    // render comment',
                    ],
                    context="React 评论组件",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="high",
                    title="XSS 漏洞",
                    description="使用 dangerouslySetInnerHTML 渲染用户内容，存在 XSS 风险",
                    file_path="src/components/Comment.jsx",
                    line_range=(10, 10),
                    detection_hints=["XSS", "dangerouslySetInnerHTML", "__html"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-XSS-005",
            name="jQuery html() XSS",
            category=IssueCategory.SECURITY,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/frontend/jquery_utils.js",
                    language="javascript",
                    old_start=20,
                    old_count=1,
                    new_start=20,
                    new_count=2,
                    additions=[
                        'function displayMessage(msg) {',
                        '    $("#message").html(msg);',
                    ],
                    deletions=["// display message"],
                    context="消息显示",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="high",
                    title="XSS 漏洞",
                    description="使用 jQuery html() 方法插入用户输入，存在 XSS 风险",
                    file_path="src/frontend/jquery_utils.js",
                    line_range=(21, 21),
                    detection_hints=["XSS", ".html(", "jQuery", "cross-site scripting"],
                )
            ],
        ),

        # ==================== 硬编码密钥/密码 (5 条) ====================
        SyntheticTestCase(
            id="SEC-KEY-001",
            name="硬编码 API 密钥",
            category=IssueCategory.SECURITY,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/config/api.py",
                    language="python",
                    old_start=1,
                    old_count=1,
                    new_start=1,
                    new_count=2,
                    additions=[
                        'API_KEY = "sk-1234567890abcdef1234567890abcdef"',
                        'API_URL = "https://api.example.com"',
                    ],
                    deletions=["# API configuration"],
                    context="API 配置",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="critical",
                    title="硬编码 API 密钥",
                    description="API 密钥直接硬编码在源代码中，存在泄露风险",
                    file_path="src/config/api.py",
                    line_range=(1, 1),
                    detection_hints=["hardcoded secret", "API key", "sk-"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-KEY-002",
            name="硬编码数据库密码",
            category=IssueCategory.SECURITY,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/config/database.py",
                    language="python",
                    old_start=5,
                    old_count=1,
                    new_start=5,
                    new_count=2,
                    additions=[
                        'DB_PASSWORD = "admin123"',
                        'DB_HOST = "localhost"',
                    ],
                    deletions=["# database config"],
                    context="数据库配置",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="critical",
                    title="硬编码数据库密码",
                    description="数据库密码直接硬编码在源代码中",
                    file_path="src/config/database.py",
                    line_range=(5, 5),
                    detection_hints=["hardcoded secret", "password", "DB_PASSWORD"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-KEY-003",
            name="硬编码 JWT 密钥",
            category=IssueCategory.SECURITY,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/auth/jwt.py",
                    language="python",
                    old_start=10,
                    old_count=1,
                    new_start=10,
                    new_count=2,
                    additions=[
                        'SECRET_KEY = "my-secret-key-12345"',
                        'ALGORITHM = "HS256"',
                    ],
                    deletions=["# JWT configuration"],
                    context="JWT 配置",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="critical",
                    title="硬编码 JWT 密钥",
                    description="JWT 签名密钥硬编码在源代码中",
                    file_path="src/auth/jwt.py",
                    line_range=(10, 10),
                    detection_hints=["hardcoded secret", "SECRET_KEY", "JWT"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-KEY-004",
            name="硬编码 AWS 凭证",
            category=IssueCategory.SECURITY,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/config/aws.py",
                    language="python",
                    old_start=1,
                    old_count=1,
                    new_start=1,
                    new_count=4,
                    additions=[
                        'AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"',
                        'AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"',
                        'AWS_REGION = "us-east-1"',
                        '',
                    ],
                    deletions=["# AWS configuration"],
                    context="AWS 配置",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="critical",
                    title="硬编码 AWS 凭证",
                    description="AWS 访问密钥和秘密密钥硬编码在源代码中",
                    file_path="src/config/aws.py",
                    line_range=(1, 2),
                    detection_hints=["hardcoded secret", "AWS", "ACCESS_KEY", "SECRET_ACCESS_KEY"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-KEY-005",
            name="硬编码私钥",
            category=IssueCategory.SECURITY,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/crypto/keys.py",
                    language="python",
                    old_start=5,
                    old_count=1,
                    new_start=5,
                    new_count=6,
                    additions=[
                        'PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----',
                        'MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MbzYLdZ7ZvVy7F7V',
                        '...',
                        '-----END RSA PRIVATE KEY-----"""',
                        '',
                        'PUBLIC_KEY = "..."',
                    ],
                    deletions=["# RSA keys"],
                    context="RSA 密钥配置",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="critical",
                    title="硬编码私钥",
                    description="RSA 私钥硬编码在源代码中",
                    file_path="src/crypto/keys.py",
                    line_range=(5, 8),
                    detection_hints=["hardcoded secret", "PRIVATE_KEY", "RSA PRIVATE KEY", "BEGIN RSA"],
                )
            ],
        ),

        # ==================== 命令注入 (4 条) ====================
        SyntheticTestCase(
            id="SEC-CMD-001",
            name="os.system 命令注入",
            category=IssueCategory.SECURITY,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/shell.py",
                    language="python",
                    old_start=10,
                    old_count=1,
                    new_start=10,
                    new_count=2,
                    additions=[
                        'def ping_host(host):',
                        '    os.system(f"ping -c 4 {host}")',
                    ],
                    deletions=["# ping function"],
                    context="主机 ping 功能",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="critical",
                    title="命令注入漏洞",
                    description="使用 os.system 执行包含用户输入的命令，可能导致命令注入",
                    file_path="src/utils/shell.py",
                    line_range=(11, 11),
                    detection_hints=["command injection", "os.system", "f-string"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-CMD-002",
            name="subprocess shell=True 命令注入",
            category=IssueCategory.SECURITY,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/process.py",
                    language="python",
                    old_start=15,
                    old_count=1,
                    new_start=15,
                    new_count=2,
                    additions=[
                        'def run_command(cmd):',
                        '    subprocess.run(cmd, shell=True)',
                    ],
                    deletions=["# run command"],
                    context="命令执行工具",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="critical",
                    title="命令注入漏洞",
                    description="使用 subprocess.run 并设置 shell=True，存在命令注入风险",
                    file_path="src/utils/process.py",
                    line_range=(16, 16),
                    detection_hints=["command injection", "subprocess", "shell=True"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-CMD-003",
            name="eval 命令注入",
            category=IssueCategory.SECURITY,
            difficulty="hard",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/executor.py",
                    language="python",
                    old_start=20,
                    old_count=1,
                    new_start=20,
                    new_count=2,
                    additions=[
                        'def execute_user_code(code):',
                        '    result = eval(code)',
                    ],
                    deletions=["# code executor"],
                    context="代码执行器",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="critical",
                    title="代码注入漏洞",
                    description="使用 eval 执行用户提供的代码，可能导致任意代码执行",
                    file_path="src/utils/executor.py",
                    line_range=(21, 21),
                    detection_hints=["code injection", "eval", "arbitrary code execution"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-CMD-004",
            name="exec 命令注入",
            category=IssueCategory.SECURITY,
            difficulty="hard",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/plugins/loader.py",
                    language="python",
                    old_start=10,
                    old_count=1,
                    new_start=10,
                    new_count=2,
                    additions=[
                        'def load_plugin(plugin_code):',
                        '    exec(plugin_code)',
                    ],
                    deletions=["# plugin loader"],
                    context="插件加载器",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="critical",
                    title="代码注入漏洞",
                    description="使用 exec 执行用户提供的代码，可能导致任意代码执行",
                    file_path="src/plugins/loader.py",
                    line_range=(11, 11),
                    detection_hints=["code injection", "exec", "arbitrary code execution"],
                )
            ],
        ),

        # ==================== 路径遍历 (3 条) ====================
        SyntheticTestCase(
            id="SEC-PATH-001",
            name="路径遍历漏洞",
            category=IssueCategory.SECURITY,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/api/files.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=3,
                    additions=[
                        'def read_file(filename):',
                        '    path = os.path.join("/var/www/files", filename)',
                        '    with open(path) as f: return f.read()',
                    ],
                    deletions=[
                        'def read_file(filename):',
                        '    pass',
                    ],
                    context="文件读取 API",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="high",
                    title="路径遍历漏洞",
                    description="未对用户输入的文件名进行验证，可能导致路径遍历攻击",
                    file_path="src/api/files.py",
                    line_range=(11, 12),
                    detection_hints=["path traversal", "os.path.join", "directory traversal"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-PATH-002",
            name="路径遍历 (直接拼接)",
            category=IssueCategory.SECURITY,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/download.py",
                    language="python",
                    old_start=15,
                    old_count=1,
                    new_start=15,
                    new_count=2,
                    additions=[
                        'def download_file(file_path):',
                        '    return send_file("/uploads/" + file_path)',
                    ],
                    deletions=["# download handler"],
                    context="文件下载服务",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="high",
                    title="路径遍历漏洞",
                    description="直接拼接用户输入到文件路径，可能导致路径遍历攻击",
                    file_path="src/services/download.py",
                    line_range=(16, 16),
                    detection_hints=["path traversal", "string concatenation", "send_file"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-PATH-003",
            name="路径遍历 (未验证扩展名)",
            category=IssueCategory.SECURITY,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/api/avatar.py",
                    language="python",
                    old_start=20,
                    old_count=2,
                    new_start=20,
                    new_count=3,
                    additions=[
                        'def get_avatar(filename):',
                        '    path = f"/static/avatars/{filename}"',
                        '    return send_file(path)',
                    ],
                    deletions=[
                        'def get_avatar(filename):',
                        '    pass',
                    ],
                    context="头像获取 API",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="high",
                    title="路径遍历漏洞",
                    description="未验证文件名和扩展名，可能导致路径遍历攻击",
                    file_path="src/api/avatar.py",
                    line_range=(21, 22),
                    detection_hints=["path traversal", "f-string", "send_file"],
                )
            ],
        ),

        # ==================== 不安全的反序列化 (3 条) ====================
        SyntheticTestCase(
            id="SEC-DESER-001",
            name="pickle 反序列化漏洞",
            category=IssueCategory.SECURITY,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/cache.py",
                    language="python",
                    old_start=10,
                    old_count=1,
                    new_start=10,
                    new_count=2,
                    additions=[
                        'def load_cache(data):',
                        '    return pickle.loads(data)',
                    ],
                    deletions=["# cache loader"],
                    context="缓存加载器",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="critical",
                    title="不安全的反序列化",
                    description="使用 pickle.loads 反序列化不受信任的数据，可能导致任意代码执行",
                    file_path="src/utils/cache.py",
                    line_range=(11, 11),
                    detection_hints=["insecure deserialization", "pickle.loads", "arbitrary code execution"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-DESER-002",
            name="yaml.load 反序列化漏洞",
            category=IssueCategory.SECURITY,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/config/loader.py",
                    language="python",
                    old_start=15,
                    old_count=1,
                    new_start=15,
                    new_count=2,
                    additions=[
                        'def load_config(yaml_str):',
                        '    return yaml.load(yaml_str)',
                    ],
                    deletions=["# config loader"],
                    context="配置加载器",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="high",
                    title="不安全的 YAML 反序列化",
                    description="使用 yaml.load 而非 yaml.safe_load，可能导致任意代码执行",
                    file_path="src/config/loader.py",
                    line_range=(16, 16),
                    detection_hints=["insecure deserialization", "yaml.load", "yaml.safe_load"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-DESER-003",
            name="marshal 反序列化漏洞",
            category=IssueCategory.SECURITY,
            difficulty="hard",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/utils/serializer.py",
                    language="python",
                    old_start=20,
                    old_count=1,
                    new_start=20,
                    new_count=2,
                    additions=[
                        'def deserialize(data):',
                        '    return marshal.loads(data)',
                    ],
                    deletions=["# deserializer"],
                    context="序列化工具",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="high",
                    title="不安全的反序列化",
                    description="使用 marshal.loads 反序列化不受信任的数据",
                    file_path="src/utils/serializer.py",
                    line_range=(21, 21),
                    detection_hints=["insecure deserialization", "marshal.loads"],
                )
            ],
        ),

        # ==================== 敏感信息泄露 (3 条) ====================
        SyntheticTestCase(
            id="SEC-LEAK-001",
            name="错误信息泄露敏感数据",
            category=IssueCategory.SECURITY,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/api/handler.py",
                    language="python",
                    old_start=25,
                    old_count=2,
                    new_start=25,
                    new_count=3,
                    additions=[
                        'def handle_error(e):',
                        '    return {"error": str(e), "stack_trace": traceback.format_exc()}',
                        '',
                    ],
                    deletions=[
                        'def handle_error(e):',
                        '    pass',
                    ],
                    context="错误处理",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="medium",
                    title="敏感信息泄露",
                    description="错误响应中包含详细的堆栈跟踪信息，可能泄露敏感信息",
                    file_path="src/api/handler.py",
                    line_range=(26, 26),
                    detection_hints=["information disclosure", "stack trace", "traceback"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-LEAK-002",
            name="日志记录敏感信息",
            category=IssueCategory.SECURITY,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/auth/login.py",
                    language="python",
                    old_start=30,
                    old_count=2,
                    new_start=30,
                    new_count=3,
                    additions=[
                        'def login(username, password):',
                        '    logger.info(f"Login attempt: {username}:{password}")',
                        '    # authenticate user',
                    ],
                    deletions=[
                        'def login(username, password):',
                        '    # authenticate user',
                    ],
                    context="登录功能",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="high",
                    title="敏感信息泄露",
                    description="日志中记录了用户密码，存在敏感信息泄露风险",
                    file_path="src/auth/login.py",
                    line_range=(31, 31),
                    detection_hints=["information disclosure", "password in log", "sensitive data"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-LEAK-003",
            name="调试信息泄露",
            category=IssueCategory.SECURITY,
            difficulty="easy",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/api/debug.py",
                    language="python",
                    old_start=10,
                    old_count=1,
                    new_start=10,
                    new_count=2,
                    additions=[
                        '@app.route("/debug")',
                        'def debug_info(): return {"env": dict(os.environ), "config": app.config}',
                    ],
                    deletions=["# debug endpoint"],
                    context="调试接口",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="critical",
                    title="敏感信息泄露",
                    description="调试接口暴露了环境变量和配置信息",
                    file_path="src/api/debug.py",
                    line_range=(11, 11),
                    detection_hints=["information disclosure", "debug endpoint", "os.environ", "app.config"],
                )
            ],
        ),

        # ==================== SSRF (2 条) ====================
        SyntheticTestCase(
            id="SEC-SSRF-001",
            name="SSRF 漏洞",
            category=IssueCategory.SECURITY,
            difficulty="medium",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/api/proxy.py",
                    language="python",
                    old_start=10,
                    old_count=2,
                    new_start=10,
                    new_count=3,
                    additions=[
                        'def fetch_url(url):',
                        '    response = requests.get(url)',
                        '    return response.text',
                    ],
                    deletions=[
                        'def fetch_url(url):',
                        '    pass',
                    ],
                    context="URL 代理服务",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="high",
                    title="SSRF 漏洞",
                    description="未验证用户提供的 URL，可能导致服务器端请求伪造攻击",
                    file_path="src/api/proxy.py",
                    line_range=(11, 12),
                    detection_hints=["SSRF", "Server-Side Request Forgery", "requests.get"],
                )
            ],
        ),
        SyntheticTestCase(
            id="SEC-SSRF-002",
            name="SSRF (URL 验证不足)",
            category=IssueCategory.SECURITY,
            difficulty="hard",
            diff_chunks=[
                DiffChunkSchema(
                    file_path="src/services/webhook.py",
                    language="python",
                    old_start=15,
                    old_count=2,
                    new_start=15,
                    new_count=4,
                    additions=[
                        'def send_webhook(webhook_url, data):',
                        '    if webhook_url.startswith("http"):',
                        '        return requests.post(webhook_url, json=data)',
                        '    return None',
                    ],
                    deletions=[
                        'def send_webhook(webhook_url, data):',
                        '    pass',
                    ],
                    context="Webhook 服务",
                )
            ],
            injected_issues=[
                InjectedIssue(
                    category=IssueCategory.SECURITY,
                    severity="high",
                    title="SSRF 漏洞",
                    description="URL 验证不足，仅检查 http 前缀，仍可能导致 SSRF 攻击",
                    file_path="src/services/webhook.py",
                    line_range=(16, 17),
                    detection_hints=["SSRF", "startswith", "requests.post"],
                )
            ],
        ),
    ]
