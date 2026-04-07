import json
from pathlib import Path

from models import ReviewAction
from server.environment import CodeReviewEnvironment


def main() -> int:
    env = CodeReviewEnvironment()
    observation = env.reset(seed=7)
    print("Reset observation:", observation.model_dump())

    data_path = Path("data") / "prs.json"
    prs = json.loads(data_path.read_text(encoding="utf-8"))

    bug_idx = next(i for i, pr in enumerate(prs) if not pr.get("is_clean", False))
    clean_idx = next(i for i, pr in enumerate(prs) if pr.get("is_clean", False))

    # Correct action for a bug PR.
    first = prs[bug_idx]
    bugs = first.get("bugs") or [
        {
            "line": first["bug_line"],
            "severity": first["severity"],
            "description": first["bug_description"],
            "correct_fix": first["correct_fix"],
        }
    ]
    bug = bugs[0]
    env.reset(forced_index=bug_idx)
    correct_action = ReviewAction(
        line_number=bug["line"],
        severity=bug["severity"],
        message=bug["description"],
        suggested_fix=bug["correct_fix"],
        rationale="Exact line and category match.",
    )
    _, correct_reward, _, correct_info = env.step(correct_action)
    print("Correct reward:", correct_reward, "info:", correct_info)

    # Wrong action on same bug PR.
    env.reset(forced_index=bug_idx)
    wrong_action = ReviewAction(
        line_number=0,
        severity="style",
        message="No obvious issue.",
        suggested_fix="rename variable",
        rationale="guess",
    )
    _, wrong_reward, _, wrong_info = env.step(wrong_action)
    print("Wrong reward:", wrong_reward, "info:", wrong_info)

    # True-negative calibration on a clean PR.
    env.reset(forced_index=clean_idx)
    clean_action = ReviewAction(
        line_number=0,
        severity="style",
        message="No bug detected in this diff.",
        suggested_fix="Approve as-is.",
        rationale="Clean refactor with no security or logic issue.",
    )
    _, clean_reward, _, clean_info = env.step(clean_action)
    print("Clean reward:", clean_reward, "info:", clean_info)

    passed = correct_reward > wrong_reward and clean_reward > 0
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
