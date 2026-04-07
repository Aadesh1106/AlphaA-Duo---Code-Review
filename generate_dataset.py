import json
from pathlib import Path


def build_diff(path: str, body_lines: list[str]) -> str:
    header = [
        f"diff --git a/{path} b/{path}",
        f"--- a/{path}",
        f"+++ b/{path}",
        "@@ -1,6 +1,6 @@",
    ]
    return "\n".join(header + body_lines)


def bug_line_for(diff: str, marker: str) -> int:
    for idx, line in enumerate(diff.splitlines(), start=1):
        if marker in line:
            return idx
    raise ValueError(f"Marker not found: {marker}")


entries = []
next_id = 1


def add_entry(filename: str, diff: str, marker: str, severity: str, bug_description: str, correct_fix: str):
    global next_id
    entries.append(
        {
            "id": next_id,
            "filename": filename,
            "diff": diff,
            "bug_line": bug_line_for(diff, marker),
            "severity": severity,
            "bug_description": bug_description,
            "correct_fix": correct_fix,
        }
    )
    next_id += 1


# SQL Injection (6)
sql_cases = [
    ("backend/user_repo.py", "users", "username"),
    ("backend/order_lookup.py", "orders", "order_id"),
    ("services/audit.py", "audit_log", "actor"),
    ("api/reporting.py", "reports", "status"),
    ("internal/search.go", "customers", "email"),
    ("controllers/search.js", "tickets", "query"),
]
for filename, table, user_field in sql_cases:
    if filename.endswith(".py"):
        marker = f'+    sql = f"SELECT * FROM {table} WHERE {user_field} = \'{'+user_field+'}\'"'
        diff = build_diff(
            filename,
            [
                " def find_record(conn, value):",
                f"-    sql = \"SELECT * FROM {table} WHERE {user_field} = %s\"",
                "-    return conn.execute(sql, (value,)).fetchall()",
                f"+    {user_field} = value",
                f"+    sql = f\"SELECT * FROM {table} WHERE {user_field} = '{'{'}{user_field}{'}'}'\"",
                "+    return conn.execute(sql).fetchall()",
            ],
        )
        marker = "SELECT * FROM"
    elif filename.endswith(".go"):
        diff = build_diff(
            filename,
            [
                " func findCustomer(db *sql.DB, email string) (*sql.Rows, error) {",
                "-    return db.Query(\"SELECT * FROM customers WHERE email = ?\", email)",
                "+    query := \"SELECT * FROM customers WHERE email = '\" + email + \"'\"",
                "+    return db.Query(query)",
                " }",
            ],
        )
        marker = "query :="
    else:
        diff = build_diff(
            filename,
            [
                " function findTickets(db, query) {",
                "-  return db.query('SELECT * FROM tickets WHERE subject = ?', [query]);",
                "+  const sql = `SELECT * FROM tickets WHERE subject = '${query}'`;",
                "+  return db.query(sql);",
                " }",
            ],
        )
        marker = "const sql"
    add_entry(
        filename,
        diff,
        marker,
        "critical",
        "User input is concatenated into SQL and allows injection.",
        "Use parameterized query placeholders and pass user input as bound parameters.",
    )

# XSS (6)
xss_cases = [
    "web/profile.js",
    "web/comments.js",
    "frontend/chat.js",
    "templates/render.py",
    "views/preview.py",
    "ui/messages.go",
]
for filename in xss_cases:
    if filename.endswith(".js"):
        diff = build_diff(
            filename,
            [
                " export function renderComment(input) {",
                "-  el.textContent = input;",
                "+  el.innerHTML = input;",
                "   return el;",
                " }",
            ],
        )
        marker = "innerHTML"
    elif filename.endswith(".py"):
        diff = build_diff(
            filename,
            [
                " def render_preview(user_text):",
                "-    return html.escape(user_text)",
                "+    return f\"<div>{user_text}</div>\"",
            ],
        )
        marker = "<div>"
    else:
        diff = build_diff(
            filename,
            [
                " func renderMessage(input string) string {",
                "-    return html.EscapeString(input)",
                "+    return \"<p>\" + input + \"</p>\"",
                " }",
            ],
        )
        marker = "<p>"
    add_entry(
        filename,
        diff,
        marker,
        "critical",
        "Unsanitized user-controlled content is rendered as HTML.",
        "Escape or sanitize untrusted input before rendering and prefer textContent style APIs.",
    )

# Hardcoded secrets (6)
secret_cases = [
    ("config/settings.py", "OPENAI_API_KEY", "sk-live-123456789"),
    ("config/auth.py", "JWT_SECRET", "super-secret-signing-key"),
    ("services/payments.js", "STRIPE_KEY", "sk_test_123456"),
    ("infra/deploy.js", "AWS_SECRET", "AKIASECRETKEY123"),
    ("cmd/server.go", "dbPassword", "P@ssword123!"),
    ("pkg/mail.go", "smtpToken", "smtp-prod-token-abc"),
]
for filename, key, val in secret_cases:
    if filename.endswith(".py"):
        diff = build_diff(
            filename,
            [
                " import os",
                f"- {key} = os.getenv('{key}')",
                f"+ {key} = \"{val}\"",
            ],
        )
        marker = val
    elif filename.endswith(".js"):
        diff = build_diff(
            filename,
            [
                " const fs = require('fs');",
                f"-const {key} = process.env.{key};",
                f"+const {key} = '{val}';",
            ],
        )
        marker = val
    else:
        diff = build_diff(
            filename,
            [
                " package main",
                f"-var {key} = os.Getenv(\"{key}\")",
                f"+var {key} = \"{val}\"",
            ],
        )
        marker = val
    add_entry(
        filename,
        diff,
        marker,
        "critical",
        "A secret key is hardcoded in source code and can leak through version control.",
        "Load secrets from environment variables or secret manager and rotate the exposed credential.",
    )

# Off-by-one (6)
off_by_one = [
    "algo/paging.py",
    "algo/window.py",
    "utils/range.js",
    "utils/chunk.js",
    "calc/limits.go",
    "calc/index.go",
]
for filename in off_by_one:
    if filename.endswith(".py"):
        diff = build_diff(
            filename,
            [
                " def iterate(items):",
                "-    for i in range(len(items)):",
                "+    for i in range(len(items) + 1):",
                "         process(items[i])",
            ],
        )
        marker = "+    for i in range(len(items) + 1):"
    elif filename.endswith(".js"):
        diff = build_diff(
            filename,
            [
                " export function sum(arr) {",
                "   let total = 0;",
                "-  for (let i = 0; i < arr.length; i++) {",
                "+  for (let i = 0; i <= arr.length; i++) {",
                "     total += arr[i];",
                "   }",
                "   return total;",
                " }",
            ],
        )
        marker = "<= arr.length"
    else:
        diff = build_diff(
            filename,
            [
                " func total(values []int) int {",
                "     sum := 0",
                "-    for i := 0; i < len(values); i++ {",
                "+    for i := 0; i <= len(values); i++ {",
                "         sum += values[i]",
                "     }",
                "     return sum",
                " }",
            ],
        )
        marker = "<= len(values)"
    add_entry(
        filename,
        diff,
        marker,
        "medium",
        "Loop boundary includes one element too many and can access out-of-range index.",
        "Use a strict less-than boundary for indexes and avoid reading past the final element.",
    )

# Null / None dereference (6)
null_cases = [
    "service/user.py",
    "service/account.py",
    "api/profile.js",
    "api/cart.js",
    "handler/order.go",
    "handler/item.go",
]
for filename in null_cases:
    if filename.endswith(".py"):
        diff = build_diff(
            filename,
            [
                " def user_name(user):",
                "-    return user.name if user else \"guest\"",
                "+    return user.name.upper()",
            ],
        )
        marker = "user.name.upper()"
    elif filename.endswith(".js"):
        diff = build_diff(
            filename,
            [
                " export function cartTotal(cart) {",
                "-  if (!cart) return 0;",
                "+  return cart.items.reduce((a, b) => a + b.price, 0);",
                " }",
            ],
        )
        marker = "cart.items"
    else:
        diff = build_diff(
            filename,
            [
                " func customerName(c *Customer) string {",
                "-    if c == nil { return \"guest\" }",
                "+    return strings.ToUpper(c.Name)",
                " }",
            ],
        )
        marker = "c.Name"
    add_entry(
        filename,
        diff,
        marker,
        "medium",
        "Code dereferences a value that may be null or None without a guard.",
        "Add a null check before dereference and return a safe fallback when object is missing.",
    )

# Missing authentication checks (6)
auth_cases = [
    "api/admin.py",
    "api/export.py",
    "routes/billing.js",
    "routes/audit.js",
    "server/delete.go",
    "server/admin.go",
]
for filename in auth_cases:
    if filename.endswith(".py"):
        diff = build_diff(
            filename,
            [
                " def delete_user(request, user_id):",
                "-    require_admin(request.user)",
                "-    return db.delete_user(user_id)",
                "+    return db.delete_user(user_id)",
            ],
        )
        marker = "db.delete_user"
    elif filename.endswith(".js"):
        diff = build_diff(
            filename,
            [
                " router.post('/billing/refund', async (req, res) => {",
                "-  if (!req.user || !req.user.isAdmin) return res.status(403).end();",
                "+  await issueRefund(req.body.id);",
                "+  res.status(200).end();",
                " });",
            ],
        )
        marker = "issueRefund"
    else:
        diff = build_diff(
            filename,
            [
                " func DeleteAll(w http.ResponseWriter, r *http.Request) {",
                "-    if !isAdmin(r) { http.Error(w, \"forbidden\", 403); return }",
                "+    _ = purgeAllAccounts()",
                " }",
            ],
        )
        marker = "purgeAllAccounts"
    add_entry(
        filename,
        diff,
        marker,
        "critical",
        "Sensitive endpoint removed authorization checks and allows unauthenticated actions.",
        "Reintroduce authentication and role authorization checks before performing privileged operations.",
    )

# Insecure random number generation (4)
rng_cases = [
    "security/token.py",
    "security/reset.py",
    "auth/session.js",
    "auth/nonce.go",
]
for filename in rng_cases:
    if filename.endswith(".py"):
        diff = build_diff(
            filename,
            [
                " import random",
                " def make_token():",
                "-    return secrets.token_hex(16)",
                "+    return hex(random.randint(100000, 999999))[2:]",
            ],
        )
        marker = "random.randint"
    elif filename.endswith(".js"):
        diff = build_diff(
            filename,
            [
                " export function createSessionId() {",
                "-  return crypto.randomUUID();",
                "+  return Math.random().toString(36).slice(2);",
                " }",
            ],
        )
        marker = "Math.random"
    else:
        diff = build_diff(
            filename,
            [
                " func nonce() string {",
                "-    b := make([]byte, 16); rand.Read(b)",
                "+    return fmt.Sprintf(\"%d\", rand.Int())",
                " }",
            ],
        )
        marker = "rand.Int()"
    add_entry(
        filename,
        diff,
        marker,
        "medium",
        "Predictable RNG is used for security-sensitive token generation.",
        "Use cryptographically secure randomness for tokens and nonces.",
    )

# Path traversal (4)
path_cases = [
    "files/download.py",
    "files/render.py",
    "files/fetch.js",
    "files/read.go",
]
for filename in path_cases:
    if filename.endswith(".py"):
        diff = build_diff(
            filename,
            [
                " def read_file(name):",
                "-    safe = os.path.basename(name)",
                "-    return open(os.path.join(BASE, safe)).read()",
                "+    return open(os.path.join(BASE, name)).read()",
            ],
        )
        marker = "os.path.join(BASE, name)"
    elif filename.endswith(".js"):
        diff = build_diff(
            filename,
            [
                " export const fetchFile = (name) => {",
                "-  const safe = path.basename(name);",
                "-  return fs.readFileSync(path.join(ROOT, safe), 'utf8');",
                "+  return fs.readFileSync(path.join(ROOT, name), 'utf8');",
                " };",
            ],
        )
        marker = "path.join(ROOT, name)"
    else:
        diff = build_diff(
            filename,
            [
                " func read(name string) string {",
                "-    safe := filepath.Base(name)",
                "-    b, _ := os.ReadFile(filepath.Join(rootDir, safe))",
                "+    b, _ := os.ReadFile(filepath.Join(rootDir, name))",
                "     return string(b)",
                " }",
            ],
        )
        marker = "filepath.Join(rootDir, name)"
    add_entry(
        filename,
        diff,
        marker,
        "critical",
        "User-controlled path segments can escape the intended directory.",
        "Normalize and validate paths, reject traversal patterns, and enforce a fixed base directory.",
    )

# Integer overflow (3)
overflow_cases = [
    "math/accumulator.py",
    "math/buffer.js",
    "math/limit.go",
]
for filename in overflow_cases:
    if filename.endswith(".py"):
        diff = build_diff(
            filename,
            [
                " def grow(counter, delta):",
                "-    return min(counter + delta, 2**31 - 1)",
                "+    return (counter + delta) & 0xFFFFFFFF",
            ],
        )
        marker = "0xFFFFFFFF"
    elif filename.endswith(".js"):
        diff = build_diff(
            filename,
            [
                " export function nextSize(size, add) {",
                "-  return Math.min(size + add, Number.MAX_SAFE_INTEGER);",
                "+  return (size + add) | 0;",
                " }",
            ],
        )
        marker = "| 0"
    else:
        diff = build_diff(
            filename,
            [
                " func add(a int32, b int32) int32 {",
                "-    if b > 0 && a > math.MaxInt32-b { return math.MaxInt32 }",
                "+    return a + b",
                " }",
            ],
        )
        marker = "return a + b"
    add_entry(
        filename,
        diff,
        marker,
        "medium",
        "Arithmetic operation can overflow and produce incorrect or wrapped values.",
        "Use checked arithmetic or explicit bounds validation before addition.",
    )

# Misc logic bugs (5)
misc_cases = [
    ("logic/discount.py", "style"),
    ("logic/status.py", "medium"),
    ("logic/cache.js", "style"),
    ("logic/priority.go", "medium"),
    ("logic/retry.js", "medium"),
]
for filename, severity in misc_cases:
    if filename.endswith(".py"):
        diff = build_diff(
            filename,
            [
                " def apply_discount(total, pct):",
                "-    return total * (1 - pct)",
                "+    return total * (1 + pct)",
            ],
        )
        marker = "(1 + pct)"
        bug = "Discount logic increases price instead of decreasing it."
        fix = "Apply discount by subtracting the percentage from one before multiplying the total."
    elif filename.endswith(".js"):
        diff = build_diff(
            filename,
            [
                " export function shouldRetry(code) {",
                "-  return code >= 500;",
                "+  return code < 500;",
                " }",
            ],
        )
        marker = "code < 500"
        bug = "Conditional logic is inverted and retries successful responses."
        fix = "Restore condition to retry only transient server errors and not successful calls."
    else:
        diff = build_diff(
            filename,
            [
                " func pickPriority(queue []Task) Task {",
                "-    sort.Slice(queue, func(i, j int) bool { return queue[i].Score > queue[j].Score })",
                "+    sort.Slice(queue, func(i, j int) bool { return queue[i].Score < queue[j].Score })",
                "     return queue[0]",
                " }",
            ],
        )
        marker = "Score <"
        bug = "Sorting direction is reversed, selecting lowest priority first."
        fix = "Sort tasks in descending order so highest score appears first."
    add_entry(filename, diff, marker, severity, bug, fix)

# Validate schema and counts
required = {"id", "filename", "diff", "bug_line", "severity", "bug_description", "correct_fix"}
for item in entries:
    assert set(item.keys()) == required

assert len(entries) >= 50

out_dir = Path("data")
out_dir.mkdir(parents=True, exist_ok=True)
with (out_dir / "prs.json").open("w", encoding="utf-8") as f:
    json.dump(entries, f, indent=2)

print(f"Wrote {len(entries)} entries to data/prs.json")
