import argparse
import random
from statistics import mean

from models import ReviewAction
from server.environment import CodeReviewEnvironment


def random_policy() -> ReviewAction:
    severities = ["critical", "medium", "style"]
    return ReviewAction(
        line_number=random.randint(0, 15),
        severity=random.choice(severities),
        message="Possible issue",
        suggested_fix="check this code",
        rationale="random guess",
    )


def heuristic_policy(obs) -> ReviewAction:
    diff = obs.diff.lower()
    if obs.is_clean:
        return ReviewAction(
            line_number=0,
            severity="style",
            message="No bug detected.",
            suggested_fix="No fix required.",
            rationale="clean calibration",
        )

    if "select" in diff and "where" in diff:
        msg = "Possible SQL injection via string interpolation"
        fix = "Use parameterized query placeholders with bound parameters"
        sev = "critical"
    elif "innerhtml" in diff:
        msg = "Potential XSS from unsanitized HTML output"
        fix = "sanitize untrusted input and use textContent"
        sev = "critical"
    elif "random.randint" in diff or "math.random" in diff:
        msg = "Insecure random token generation"
        fix = "Use cryptographically secure randomness"
        sev = "medium"
    elif "<= arr.length" in diff:
        msg = "Off-by-one loop boundary"
        fix = "use strict less-than length boundary"
        sev = "medium"
    elif "delete_all_users" in diff or "require_admin" in diff:
        msg = "Missing auth check"
        fix = "add authorization guard before operation"
        sev = "critical"
    elif "profile.name.upper" in diff or "nil" in diff:
        msg = "Possible null dereference"
        fix = "check None before dereference"
        sev = "medium"
    else:
        msg = "Logic or safety issue in changed line"
        fix = "restore guard condition and add validation"
        sev = "medium"

    line_number = 6 if "+" in obs.diff else 0
    return ReviewAction(
        line_number=line_number,
        severity=sev,
        message=msg,
        suggested_fix=fix,
        rationale="heuristic category detection",
    )


def run(policy_name: str, episodes: int) -> None:
    env = CodeReviewEnvironment()
    rewards = []
    last_metrics = {}

    for _ in range(episodes):
        obs = env.reset()
        done = False
        while not done:
            action = random_policy() if policy_name == "random" else heuristic_policy(obs)
            obs, reward, done, info = env.step(action)
            rewards.append(reward)
            last_metrics = info.get("class_metrics", {})

    print(f"Policy: {policy_name}")
    print(f"Episodes: {episodes}")
    print(f"Mean reward: {mean(rewards):.4f}")
    print("Per-class metrics (precision/recall/f1):")
    for category in sorted(last_metrics.keys()):
        m = last_metrics[category]
        print(
            f"  - {category}: "
            f"P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f} "
            f"(tp={m['tp']}, fp={m['fp']}, fn={m['fn']})"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate policy quality on CodeReview-ENV")
    parser.add_argument("--policy", choices=["random", "heuristic"], default="heuristic")
    parser.add_argument("--episodes", type=int, default=200)
    args = parser.parse_args()

    run(args.policy, args.episodes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
