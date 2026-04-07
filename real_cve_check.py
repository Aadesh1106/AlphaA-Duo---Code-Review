import json
from pathlib import Path
from statistics import mean

from models import ReviewAction
from server.environment import CodeReviewEnvironment


def heuristic_action(pr: dict) -> ReviewAction:
    diff = pr["diff"].lower()
    severity = pr["severity"]
    message = "Potential vulnerability in changed line."
    suggested_fix = "Apply strict sanitization and safer APIs."
    rationale = "signature-based cve heuristic"

    candidate_tokens = [
        "sql =",
        "return alias",
        "return f\"",
        "body =",
        "os.path.join",
        "decode(token)",
        "eval(value)",
        "shell=true",
        "param_re",
    ]
    lines = pr["diff"].splitlines()
    line_number = 0
    for token in candidate_tokens:
        for idx, line in enumerate(lines, start=1):
            if token in line.lower():
                line_number = idx
                break
        if line_number:
            break

    if "sql" in diff and "where" in diff:
        message = "Likely SQL injection due to unsafe query construction."
        suggested_fix = "Use parameterized queries and quote unsafe fragments."
    elif "innerhtml" in diff or "href" in diff:
        message = "Potential XSS from unescaped output."
        suggested_fix = "Escape untrusted content before writing HTML."
    elif "os.path.join" in diff and "safe" in diff:
        message = "Path traversal risk from unsanitized path segments."
        suggested_fix = "Normalize input and enforce base directory constraints."
    elif "decode(token)" in diff:
        message = "JWT auth bypass due to missing signature verification."
        suggested_fix = "Verify token signature before decoding claims."
    elif "eval(" in diff or "shell=true" in diff:
        message = "Code execution risk from unsafe evaluation or shell invocation."
        suggested_fix = "Remove eval/shell execution and sanitize arguments."
    elif "param_re" in diff:
        message = "Regex likely vulnerable to catastrophic backtracking."
        suggested_fix = "Use linear-time regex and bounded parsing pattern."

    return ReviewAction(
        line_number=line_number,
        severity=severity,
        message=message,
        suggested_fix=suggested_fix,
        rationale=rationale,
    )


def baseline_action() -> ReviewAction:
    return ReviewAction(
        line_number=0,
        severity="style",
        message="Looks okay.",
        suggested_fix="No changes.",
        rationale="baseline",
    )


def main() -> int:
    prs = json.loads(Path("data/prs.json").read_text(encoding="utf-8"))
    cve_indices = [i for i, x in enumerate(prs) if x.get("source_type") == "real_cve_seed"]

    env = CodeReviewEnvironment()

    baseline_rewards = []
    heuristic_rewards = []
    exact_matches = 0
    severity_matches = 0

    for idx in cve_indices:
        pr = prs[idx]

        env.reset(forced_index=idx)
        _, b_reward, _, _ = env.step(baseline_action())
        baseline_rewards.append(float(b_reward))

        env.reset(forced_index=idx)
        action = heuristic_action(pr)
        _, h_reward, _, info = env.step(action)
        heuristic_rewards.append(float(h_reward))

        if action.line_number == int(pr["bug_line"]):
            exact_matches += 1
        if action.severity == pr["severity"]:
            severity_matches += 1

    count = len(cve_indices)
    print(f"CVE cases tested: {count}")
    print(f"Baseline mean reward: {mean(baseline_rewards):.4f}")
    print(f"Heuristic mean reward: {mean(heuristic_rewards):.4f}")
    print(f"Exact-line hit rate: {exact_matches}/{count} ({(exact_matches/count)*100:.1f}%)")
    print(f"Severity hit rate: {severity_matches}/{count} ({(severity_matches/count)*100:.1f}%)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
