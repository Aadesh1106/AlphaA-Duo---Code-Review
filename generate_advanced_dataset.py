import json
import random
from pathlib import Path
from typing import Any

random.seed(7)

CATEGORIES = [
    "sql_injection",
    "xss",
    "hardcoded_secret",
    "off_by_one",
    "null_dereference",
    "missing_auth",
    "insecure_random",
    "path_traversal",
    "integer_overflow",
    "logic_bug",
]

COUNTS = {
    "sql_injection": 52,
    "xss": 52,
    "hardcoded_secret": 52,
    "off_by_one": 52,
    "null_dereference": 52,
    "missing_auth": 52,
    "insecure_random": 40,
    "path_traversal": 40,
    "integer_overflow": 40,
    "logic_bug": 60,
}

MULTI_BUG_COUNT = 68
CLEAN_COUNT = 80


def diff_header(path: str) -> list[str]:
    return [
        f"diff --git a/{path} b/{path}",
        f"--- a/{path}",
        f"+++ b/{path}",
        "@@ -1,8 +1,8 @@",
    ]


def compose_entry(
    idx: int,
    filename: str,
    body: list[str],
    bugs: list[dict[str, Any]],
    is_clean: bool = False,
) -> dict[str, Any]:
    diff = "\n".join(diff_header(filename) + body)
    if is_clean:
        primary = {
            "line": 0,
            "severity": "style",
            "description": "No bug in this diff.",
            "correct_fix": "No fix needed; approve the change.",
            "category": "clean",
        }
    else:
        primary = bugs[0]
    return {
        "id": idx,
        "filename": filename,
        "diff": diff,
        "bug_line": int(primary["line"]),
        "severity": primary["severity"],
        "bug_description": primary["description"],
        "correct_fix": primary["correct_fix"],
        "bug_category": primary["category"],
        "bugs": bugs,
        "is_clean": is_clean,
    }


def line_of(content_lines: list[str], token: str) -> int:
    full = diff_header("tmp") + content_lines
    for i, line in enumerate(full, start=1):
        if token in line:
            return i
    raise ValueError(token)


def mk_sql(i: int) -> tuple[str, list[str], list[dict[str, Any]]]:
    file = f"services/query_{i % 18}.py"
    table = ["users", "orders", "sessions", "payments", "logs"][i % 5]
    field = ["email", "id", "status", "name", "tenant_id"][i % 5]
    token = "SELECT"
    body = [
        " def find(conn, raw):",
        f"-    return conn.execute(\"SELECT * FROM {table} WHERE {field} = %s\", (raw,)).fetchall()",
        f"+    sql = f\"SELECT * FROM {table} WHERE {field} = '{'{'}raw{'}'}'\"",
        "+    return conn.execute(sql).fetchall()",
    ]
    bug = {
        "line": line_of(body, token),
        "severity": "critical",
        "description": "SQL query concatenates user input and is injectable.",
        "correct_fix": "Use parameterized queries with placeholders and bound parameters.",
        "category": "sql_injection",
    }
    return file, body, [bug]


def mk_xss(i: int) -> tuple[str, list[str], list[dict[str, Any]]]:
    file = f"web/render_{i % 17}.js"
    token = "innerHTML"
    body = [
        " export function paint(input) {",
        "-  node.textContent = input;",
        "+  node.innerHTML = input;",
        "   return node;",
        " }",
    ]
    bug = {
        "line": line_of(body, token),
        "severity": "critical",
        "description": "Untrusted content is rendered as HTML leading to XSS.",
        "correct_fix": "Escape or sanitize input and prefer textContent for user data.",
        "category": "xss",
    }
    return file, body, [bug]


def mk_secret(i: int) -> tuple[str, list[str], list[dict[str, Any]]]:
    file = f"config/keys_{i % 16}.go"
    token = "sk_live"
    body = [
        " package config",
        "-var ApiKey = os.Getenv(\"PAYMENT_API_KEY\")",
        f"+var ApiKey = \"sk_live_{1000 + i}\"",
    ]
    bug = {
        "line": line_of(body, token),
        "severity": "critical",
        "description": "Production secret is hardcoded in source control.",
        "correct_fix": "Load secrets from environment or a secret manager and rotate exposed keys.",
        "category": "hardcoded_secret",
    }
    return file, body, [bug]


def mk_off_by_one(i: int) -> tuple[str, list[str], list[dict[str, Any]]]:
    file = f"algo/window_{i % 19}.js"
    token = "<= arr.length"
    body = [
        " export function sum(arr) {",
        "   let s = 0;",
        "-  for (let i = 0; i < arr.length; i++) s += arr[i];",
        "+  for (let i = 0; i <= arr.length; i++) s += arr[i];",
        "   return s;",
        " }",
    ]
    bug = {
        "line": line_of(body, token),
        "severity": "medium",
        "description": "Loop boundary is off by one and can read past the array.",
        "correct_fix": "Use i < arr.length for indexed iteration.",
        "category": "off_by_one",
    }
    return file, body, [bug]


def mk_null(i: int) -> tuple[str, list[str], list[dict[str, Any]]]:
    file = f"api/user_{i % 18}.py"
    token = "profile.name"
    body = [
        " def display(profile):",
        "-    return profile.name if profile else 'guest'",
        "+    return profile.name.upper()",
    ]
    bug = {
        "line": line_of(body, token),
        "severity": "medium",
        "description": "Potential None dereference on profile object.",
        "correct_fix": "Check for None before dereference and return a safe fallback.",
        "category": "null_dereference",
    }
    return file, body, [bug]


def mk_auth(i: int) -> tuple[str, list[str], list[dict[str, Any]]]:
    file = f"routes/admin_{i % 15}.py"
    token = "delete_all_users"
    body = [
        " def remove_everything(request):",
        "-    require_admin(request.user)",
        "+    return delete_all_users()",
    ]
    bug = {
        "line": line_of(body, token),
        "severity": "critical",
        "description": "Missing authentication check on privileged endpoint.",
        "correct_fix": "Reintroduce authentication and authorization checks before execution.",
        "category": "missing_auth",
    }
    return file, body, [bug]


def mk_rng(i: int) -> tuple[str, list[str], list[dict[str, Any]]]:
    file = f"security/token_{i % 14}.py"
    token = "random.randint"
    body = [
        " import random",
        " def token():",
        "-    return secrets.token_hex(16)",
        "+    return str(random.randint(100000, 999999))",
    ]
    bug = {
        "line": line_of(body, token),
        "severity": "medium",
        "description": "Token generation uses predictable non-cryptographic randomness.",
        "correct_fix": "Use cryptographically secure RNG such as secrets.token_hex.",
        "category": "insecure_random",
    }
    return file, body, [bug]


def mk_path(i: int) -> tuple[str, list[str], list[dict[str, Any]]]:
    file = f"files/read_{i % 14}.js"
    token = "path.join(ROOT, name)"
    body = [
        " export function readUserFile(name) {",
        "-  const safe = path.basename(name);",
        "-  return fs.readFileSync(path.join(ROOT, safe), 'utf8');",
        "+  return fs.readFileSync(path.join(ROOT, name), 'utf8');",
        " }",
    ]
    bug = {
        "line": line_of(body, token),
        "severity": "critical",
        "description": "Path traversal possible via user-controlled file name.",
        "correct_fix": "Normalize and validate path input and enforce a base directory.",
        "category": "path_traversal",
    }
    return file, body, [bug]


def mk_overflow(i: int) -> tuple[str, list[str], list[dict[str, Any]]]:
    file = f"math/grow_{i % 13}.go"
    token = "return a + b"
    body = [
        " func add(a int32, b int32) int32 {",
        "-    if b > 0 && a > math.MaxInt32-b { return math.MaxInt32 }",
        "+    return a + b",
        " }",
    ]
    bug = {
        "line": line_of(body, token),
        "severity": "medium",
        "description": "Unchecked arithmetic can overflow and wrap.",
        "correct_fix": "Use bounds checks or checked arithmetic before addition.",
        "category": "integer_overflow",
    }
    return file, body, [bug]


def mk_logic(i: int) -> tuple[str, list[str], list[dict[str, Any]]]:
    file = f"logic/retry_{i % 20}.js"
    token = "code < 500"
    body = [
        " export function shouldRetry(code) {",
        "-  return code >= 500;",
        "+  return code < 500;",
        " }",
    ]
    bug = {
        "line": line_of(body, token),
        "severity": "style" if i % 3 == 0 else "medium",
        "description": "Retry condition is inverted causing incorrect behavior.",
        "correct_fix": "Retry only on transient server failures, not successful responses.",
        "category": "logic_bug",
    }
    return file, body, [bug]


def mk_clean(i: int) -> tuple[str, list[str], list[dict[str, Any]]]:
    file = f"cleanup/refactor_{i % 25}.py"
    body = [
        " def normalize_name(name):",
        "-    return name.strip().lower()",
        "+    return name.strip().casefold()",
        "",
        " def is_empty(value):",
        "-    return value == ''",
        "+    return not value",
    ]
    return file, body, []


def mk_multi(i: int) -> tuple[str, list[str], list[dict[str, Any]]]:
    file = f"mixed/review_{i % 30}.py"
    body = [
        " def find_user(conn, username, profile):",
        "-    sql = \"SELECT * FROM users WHERE username = %s\"",
        "+    sql = f\"SELECT * FROM users WHERE username = '{username}'\"",
        "-    return profile.name if profile else 'guest'",
        "+    return profile.name.upper()",
    ]
    bugs = [
        {
            "line": line_of(body, "SELECT * FROM"),
            "severity": "critical",
            "description": "SQL injection via string interpolation.",
            "correct_fix": "Use placeholders and pass username as a bound parameter.",
            "category": "sql_injection",
        },
        {
            "line": line_of(body, "profile.name.upper()"),
            "severity": "medium",
            "description": "Potential None dereference for profile.",
            "correct_fix": "Guard profile with a None check before dereference.",
            "category": "null_dereference",
        },
    ]
    return file, body, bugs


BUILDERS = {
    "sql_injection": mk_sql,
    "xss": mk_xss,
    "hardcoded_secret": mk_secret,
    "off_by_one": mk_off_by_one,
    "null_dereference": mk_null,
    "missing_auth": mk_auth,
    "insecure_random": mk_rng,
    "path_traversal": mk_path,
    "integer_overflow": mk_overflow,
    "logic_bug": mk_logic,
}


entries: list[dict[str, Any]] = []
entry_id = 1

for category in CATEGORIES:
    for i in range(COUNTS[category]):
        filename, body, bugs = BUILDERS[category](i)
        entries.append(compose_entry(entry_id, filename, body, bugs, is_clean=False))
        entry_id += 1

for i in range(MULTI_BUG_COUNT):
    filename, body, bugs = mk_multi(i)
    entries.append(compose_entry(entry_id, filename, body, bugs, is_clean=False))
    entry_id += 1

for i in range(CLEAN_COUNT):
    filename, body, bugs = mk_clean(i)
    entries.append(compose_entry(entry_id, filename, body, bugs, is_clean=True))
    entry_id += 1

random.shuffle(entries)
for i, item in enumerate(entries, start=1):
    item["id"] = i

required = {"id", "filename", "diff", "bug_line", "severity", "bug_description", "correct_fix"}
for item in entries:
    assert required.issubset(set(item.keys()))

Path("data").mkdir(parents=True, exist_ok=True)
with Path("data/prs.json").open("w", encoding="utf-8") as f:
    json.dump(entries, f, indent=2)

print(f"Wrote {len(entries)} entries to data/prs.json")
