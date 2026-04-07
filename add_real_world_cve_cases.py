import json
from pathlib import Path
from typing import Any


def build_diff(path: str, body_lines: list[str]) -> str:
    header = [
        f"diff --git a/{path} b/{path}",
        f"--- a/{path}",
        f"+++ b/{path}",
        "@@ -1,8 +1,8 @@",
    ]
    return "\n".join(header + body_lines)


def line_of(diff: str, token: str) -> int:
    for idx, line in enumerate(diff.splitlines(), start=1):
        if token in line:
            return idx
    raise ValueError(f"Token not found: {token}")


def make_entry(
    filename: str,
    diff: str,
    marker: str,
    severity: str,
    bug_description: str,
    correct_fix: str,
    category: str,
    cve: str,
    repo: str,
    source_url: str,
) -> dict[str, Any]:
    bug_line = line_of(diff, marker)
    return {
        "id": 0,
        "filename": filename,
        "diff": diff,
        "bug_line": bug_line,
        "severity": severity,
        "bug_description": bug_description,
        "correct_fix": correct_fix,
        "bug_category": category,
        "bugs": [
            {
                "line": bug_line,
                "severity": severity,
                "description": bug_description,
                "correct_fix": correct_fix,
                "category": category,
            }
        ],
        "is_clean": False,
        "source_type": "real_cve_seed",
        "source": {
            "cve": cve,
            "repo": repo,
            "url": source_url,
            "note": "Diff-inspired case derived from public vulnerability fix information.",
        },
    }


def seeds() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    d1 = build_diff(
        "django/db/models/lookups.py",
        [
            " class HasKeyLookup(Lookup):",
            "-    sql = f\"... ? {rhs_key}\"",
            "+    escaped_key = connection.ops.quote_name(rhs_key)",
            "+    sql = f\"... ? {escaped_key}\"",
        ],
    )
    out.append(
        make_entry(
            "django/db/models/lookups.py",
            d1,
            "sql =",
            "critical",
            "Unsanitized key data reaches SQL in Oracle HasKeyLookup path.",
            "Escape or quote key fragments before interpolation into SQL expressions.",
            "sql_injection",
            "CVE-2024-53908",
            "django/django",
            "https://github.com/django/django/commit/8f8dc5a1fca7d076e749f307f6573af3512e7e99",
        )
    )

    d2 = build_diff(
        "django/db/models/sql/query.py",
        [
            " def set_alias(alias):",
            "-    return alias",
            "+    alias = alias.translate(CONTROL_CHAR_FILTER)",
            "+    return alias",
        ],
    )
    out.append(
        make_entry(
            "django/db/models/sql/query.py",
            d2,
            "return alias",
            "critical",
            "Control characters in SQL aliases enable injection primitives.",
            "Strip or reject control characters in aliases used by query builders.",
            "sql_injection",
            "CVE-2026-1287",
            "django/django",
            "https://github.com/django/django/commit/e891a84c7ef9962bfcc3b4685690219542f86a22",
        )
    )

    d3 = build_diff(
        "sql/operators.py",
        [
            " class UnaryOperator(Expression):",
            "-    return f\"{self.op} {self.value}\"",
            "+    value = self._escape_non_expression(self.value)",
            "+    return f\"{self.op} {value}\"",
        ],
    )
    out.append(
        make_entry(
            "sql/operators.py",
            d3,
            "return f",
            "critical",
            "Unary operator path does not escape non-expression values.",
            "Escape or parameterize non-expression values before SQL composition.",
            "sql_injection",
            "CVE-2024-9774",
            "tryton/python-sql",
            "https://foss.heptapod.net/tryton/python-sql/-/commit/f20551bbb8b3b4c4dd0a2c3d36f377bff6f2f349",
        )
    )

    d4 = build_diff(
        "twisted/web/util.py",
        [
            " def redirectTo(url, request):",
            "-    body = f\"<a href='{url}'>redirect</a>\"",
            "+    safe_url = html.escape(url, quote=True)",
            "+    body = f\"<a href='{safe_url}'>redirect</a>\"",
        ],
    )
    out.append(
        make_entry(
            "twisted/web/util.py",
            d4,
            "body =",
            "critical",
            "Redirect response includes unescaped attacker-controlled URL in HTML.",
            "Escape URL before embedding in HTML response body.",
            "xss",
            "CVE-2024-41810",
            "twisted/twisted",
            "https://github.com/twisted/twisted",
        )
    )

    d5 = build_diff(
        "aiohttp/web_fileresponse.py",
        [
            " def resolve_path(root, rel):",
            "-    return os.path.join(root, rel)",
            "+    clean = rel.replace('..', '')",
            "+    return os.path.join(root, clean)",
        ],
    )
    out.append(
        make_entry(
            "aiohttp/web_fileresponse.py",
            d5,
            "os.path.join",
            "critical",
            "File-serving path resolution allows traversal outside root.",
            "Normalize and validate relative paths, then enforce base directory.",
            "path_traversal",
            "CVE-unknown-aiohttp-traversal",
            "aio-libs/aiohttp",
            "https://github.com/aio-libs/aiohttp",
        )
    )

    d6 = build_diff(
        "youtube_dl/downloader/subtitles.py",
        [
            " def subtitle_path(name):",
            "-    return os.path.join(out_dir, name)",
            "+    safe = sanitize_ext(name)",
            "+    return os.path.join(out_dir, safe)",
        ],
    )
    out.append(
        make_entry(
            "youtube_dl/downloader/subtitles.py",
            d6,
            "os.path.join",
            "critical",
            "Subtitle filename components can lead to arbitrary path writes on Windows.",
            "Validate subtitle extension and sanitize output filename segments.",
            "path_traversal",
            "GHSL-youtube-dl-subtitle-traversal",
            "youtube-dl",
            "https://securitylab.github.com/advisories/",
        )
    )

    d7 = build_diff(
        "python_jwt/jwt.py",
        [
            " def process_jwt(token):",
            "-    return decode(token)",
            "+    if not verify_signature(token):",
            "+        raise InvalidToken()",
            "+    return decode(token)",
        ],
    )
    out.append(
        make_entry(
            "python_jwt/jwt.py",
            d7,
            "decode(token)",
            "critical",
            "Missing critical signature validation allows JWT claim forgery.",
            "Require cryptographic signature verification before decoding claims.",
            "missing_auth",
            "CVE-2022-39227",
            "davedoesdev/python-jwt",
            "https://github.com/davedoesdev/python-jwt/commit/88ad9e6",
        )
    )

    d8 = build_diff(
        "joblib/parallel.py",
        [
            " def _parse_pre_dispatch(value):",
            "-    return eval(value)",
            "+    return safe_parse_pre_dispatch(value)",
        ],
    )
    out.append(
        make_entry(
            "joblib/parallel.py",
            d8,
            "eval(value)",
            "critical",
            "User-controlled pre_dispatch reaches eval and enables code execution.",
            "Remove eval and use a constrained parser for accepted dispatch formats.",
            "logic_bug",
            "CVE-2022-21797",
            "joblib/joblib",
            "https://github.com/joblib/joblib/commit/b90f10e",
        )
    )

    d9 = build_diff(
        "git/repo/base.py",
        [
            " def run_git(args):",
            "-    cmd = f\"git {args}\"",
            "-    return subprocess.check_output(cmd, shell=True)",
            "+    argv = sanitize_git_args(args)",
            "+    return subprocess.check_output([\"git\", *argv], shell=False)",
        ],
    )
    out.append(
        make_entry(
            "git/repo/base.py",
            d9,
            "shell=True",
            "critical",
            "Insufficient argument sanitization enables command execution primitives.",
            "Use argument lists without shell and validate/escape user-controlled arguments.",
            "logic_bug",
            "CVE-2023-40267",
            "gitpython-developers/GitPython",
            "https://github.com/gitpython-developers/GitPython",
        )
    )

    d10 = build_diff(
        "python_multipart/content_type.py",
        [
            " TOKEN_RE = re.compile(...)",
            "-PARAM_RE = re.compile(r\"([; ]*[^=]+=[^;]+)+\")",
            "+PARAM_RE = re.compile(r\"[; ]*([A-Za-z0-9_-]+)=([^;]+)\")",
        ],
    )
    out.append(
        make_entry(
            "python_multipart/content_type.py",
            d10,
            "PARAM_RE",
            "critical",
            "Catastrophic regex backtracking allows ReDoS on crafted Content-Type headers.",
            "Replace vulnerable regex with bounded linear-time parsing pattern.",
            "redos",
            "CVE-2024-24762",
            "Kludex/python-multipart",
            "https://github.com/Kludex/python-multipart/commit/20f0ef6b4e4caf7d69a667c54dff57fe467109a4",
        )
    )

    return out


def main() -> None:
    data_path = Path("data") / "prs.json"
    prs = json.loads(data_path.read_text(encoding="utf-8"))

    # Remove prior seeded real-CVE cases so reruns stay idempotent.
    prs = [x for x in prs if x.get("source_type") != "real_cve_seed"]

    inserts = seeds()
    prs.extend(inserts)

    for idx, item in enumerate(prs, start=1):
        item["id"] = idx

    data_path.write_text(json.dumps(prs, indent=2), encoding="utf-8")
    print(f"Injected {len(inserts)} real-world CVE seed entries. Dataset size: {len(prs)}")


if __name__ == "__main__":
    main()
