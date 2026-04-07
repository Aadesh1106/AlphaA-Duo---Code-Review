import argparse
import csv
import json
import random
import io
import contextlib
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

from models import ReviewAction
from server.environment import CodeReviewEnvironment

def _load_matplotlib():
    """Lazy-load matplotlib and silence compatibility noise if unavailable."""
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            import matplotlib.pyplot as plt  # type: ignore
        return plt
    except Exception:
        return None


CATEGORIES = [
    "clean",
    "sql_injection",
    "xss",
    "hardcoded_secret",
    "off_by_one",
    "null_dereference",
    "missing_auth",
    "insecure_random",
    "path_traversal",
    "integer_overflow",
    "redos",
    "logic_bug",
]


def random_policy() -> ReviewAction:
    return ReviewAction(
        line_number=random.randint(0, 15),
        severity=random.choice(["critical", "medium", "style"]),
        message="Possible issue in this patch.",
        suggested_fix="Validate input and add checks.",
        rationale="random baseline",
    )


def heuristic_policy(obs: Any) -> ReviewAction:
    diff = obs.diff.lower()

    if obs.is_clean:
        return ReviewAction(
            line_number=0,
            severity="style",
            message="No bug detected in this refactor.",
            suggested_fix="No fix required.",
            rationale="clean calibration",
        )

    severity = "medium"
    message = "Potential logic or safety bug."
    fix = "Restore validation and guard conditions."

    if "select" in diff and "where" in diff:
        severity = "critical"
        message = "Likely SQL injection due to string interpolation in query."
        fix = "Use parameterized queries with placeholders and bound parameters."
    elif "innerhtml" in diff:
        severity = "critical"
        message = "Likely XSS due to unsanitized HTML rendering."
        fix = "Sanitize or escape input and use textContent for user data."
    elif "random.randint" in diff or "math.random" in diff or "rand.int" in diff:
        severity = "medium"
        message = "Insecure random generation for token material."
        fix = "Use cryptographically secure random generation."
    elif "delete_all_users" in diff or "require_admin" in diff or "isadmin" in diff:
        severity = "critical"
        message = "Missing authentication or authorization check."
        fix = "Add auth checks before privileged operation."
    elif "profile.name.upper" in diff or "c.name" in diff or "nil" in diff:
        severity = "medium"
        message = "Potential null or None dereference."
        fix = "Add null checks and fallback handling."
    elif "<= arr.length" in diff or "<= len(" in diff:
        severity = "medium"
        message = "Off-by-one index boundary likely out of range."
        fix = "Use strict less-than bounds for indexed loops."

    # A lightweight line heuristic for these synthetic diffs.
    line_number = 6 if "\n+" in obs.diff else 0

    return ReviewAction(
        line_number=line_number,
        severity=severity,
        message=message,
        suggested_fix=fix,
        rationale="heuristic category detection",
    )


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def normalize_confusion(matrix: dict[str, dict[str, int]]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for actual, preds in matrix.items():
        total = sum(preds.values())
        if total == 0:
            out[actual] = {pred: 0.0 for pred in CATEGORIES}
        else:
            out[actual] = {pred: round(preds.get(pred, 0) / total, 4) for pred in CATEGORIES}
    return out


def save_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def plot_reward_curve(path: Path, rewards: list[float], window: int) -> None:
    plt = _load_matplotlib()
    if plt is None:
        return
    xs = list(range(1, len(rewards) + 1))
    smoothed = []
    for i in range(len(rewards)):
        start = max(0, i - window + 1)
        smoothed.append(mean(rewards[start : i + 1]))

    plt.figure(figsize=(10, 4))
    plt.plot(xs, rewards, alpha=0.25, label="episode reward")
    plt.plot(xs, smoothed, linewidth=2, label=f"moving average ({window})")
    plt.xlabel("Episode")
    plt.ylabel("Reward")
    plt.title("Reward Curve")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def plot_confusion_heatmap(path: Path, normalized: dict[str, dict[str, float]]) -> None:
    plt = _load_matplotlib()
    if plt is None:
        return

    import numpy as np

    labels = CATEGORIES
    mat = np.array([[normalized[a].get(p, 0.0) for p in labels] for a in labels])

    plt.figure(figsize=(10, 8))
    plt.imshow(mat, cmap="Blues", aspect="auto")
    plt.colorbar(label="Normalized frequency")
    plt.xticks(range(len(labels)), labels, rotation=45, ha="right")
    plt.yticks(range(len(labels)), labels)
    plt.xlabel("Predicted class")
    plt.ylabel("Actual class")
    plt.title("Confusion Matrix (Normalized)")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def run_policy(policy_name: str, episodes: int, seed: int) -> dict[str, Any]:
    random.seed(seed)
    env = CodeReviewEnvironment()

    episode_rows: list[dict[str, Any]] = []
    step_rows: list[dict[str, Any]] = []

    confusion: dict[str, dict[str, int]] = {
        actual: {pred: 0 for pred in CATEGORIES} for actual in CATEGORIES
    }

    last_class_metrics: dict[str, Any] = {}

    for ep in range(1, episodes + 1):
        obs = env.reset()
        done = False
        ep_rewards: list[float] = []
        ep_steps = 0

        while not done:
            action = random_policy() if policy_name == "random" else heuristic_policy(obs)
            obs, reward, done, info = env.step(action)
            ep_rewards.append(reward)
            ep_steps += 1

            actual = info.get("expected_category", "clean")
            pred = info.get("predicted_category", "clean")
            if actual not in confusion:
                confusion[actual] = {p: 0 for p in CATEGORIES}
            if pred not in confusion[actual]:
                confusion[actual][pred] = 0
            confusion[actual][pred] += 1

            step_rows.append(
                {
                    "episode": ep,
                    "step": ep_steps,
                    "reward": round(float(reward), 4),
                    "done": done,
                    "actual_category": actual,
                    "predicted_category": pred,
                    "expected_severity": info.get("expected_severity", ""),
                    "line_distance": info.get("line_distance", -1),
                }
            )

            if "class_metrics" in info:
                last_class_metrics = info["class_metrics"]

        episode_rows.append(
            {
                "episode": ep,
                "steps": ep_steps,
                "episode_reward": round(sum(ep_rewards), 4),
                "mean_step_reward": round(mean(ep_rewards), 4),
            }
        )

    normalized_confusion = normalize_confusion(confusion)

    summary = {
        "policy": policy_name,
        "episodes": episodes,
        "seed": seed,
        "mean_episode_reward": round(mean([r["episode_reward"] for r in episode_rows]), 4),
        "mean_steps_per_episode": round(mean([r["steps"] for r in episode_rows]), 4),
        "class_metrics": last_class_metrics,
        "confusion_matrix_counts": confusion,
        "confusion_matrix_normalized": normalized_confusion,
        "artifacts": {
            "episodes_csv": "episodes.csv",
            "steps_csv": "steps.csv",
            "summary_json": "summary.json",
            "reward_curve_png": "reward_curve.png",
            "confusion_heatmap_png": "confusion_heatmap.png",
        },
    }

    return {
        "summary": summary,
        "episode_rows": episode_rows,
        "step_rows": step_rows,
    }


def write_results(result: dict[str, Any], out_dir: Path) -> None:
    ensure_dir(out_dir)

    summary_path = out_dir / "summary.json"
    episodes_csv = out_dir / "episodes.csv"
    steps_csv = out_dir / "steps.csv"

    summary_path.write_text(json.dumps(result["summary"], indent=2), encoding="utf-8")
    save_csv(episodes_csv, result["episode_rows"], ["episode", "steps", "episode_reward", "mean_step_reward"])
    save_csv(
        steps_csv,
        result["step_rows"],
        [
            "episode",
            "step",
            "reward",
            "done",
            "actual_category",
            "predicted_category",
            "expected_severity",
            "line_distance",
        ],
    )

    rewards = [r["episode_reward"] for r in result["episode_rows"]]
    plot_reward_curve(out_dir / "reward_curve.png", rewards, window=min(20, max(2, len(rewards) // 10)))
    plot_confusion_heatmap(out_dir / "confusion_heatmap.png", result["summary"]["confusion_matrix_normalized"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Train/eval runner for CodeReview-ENV")
    parser.add_argument("--episodes", type=int, default=300, help="Number of episodes to run")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--policy",
        choices=["heuristic", "random", "both"],
        default="both",
        help="Policy to evaluate",
    )
    parser.add_argument("--out", default="results", help="Output directory root")
    args = parser.parse_args()

    run_policies = [args.policy] if args.policy != "both" else ["heuristic", "random"]

    root = Path(args.out)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for policy in run_policies:
        run_dir = root / f"{stamp}_{policy}_{args.episodes}ep"
        result = run_policy(policy, episodes=args.episodes, seed=args.seed)
        write_results(result, run_dir)

        print(f"\n[{policy}] results written to: {run_dir}")
        print(f"  mean episode reward: {result['summary']['mean_episode_reward']}")
        print(f"  mean steps/episode : {result['summary']['mean_steps_per_episode']}")
        print(f"  summary            : {run_dir / 'summary.json'}")
        print(f"  episodes csv       : {run_dir / 'episodes.csv'}")
        print(f"  steps csv          : {run_dir / 'steps.csv'}")
        if _load_matplotlib() is not None:
            print(f"  reward curve       : {run_dir / 'reward_curve.png'}")
            print(f"  confusion heatmap  : {run_dir / 'confusion_heatmap.png'}")
        else:
            print("  plots              : skipped (matplotlib not installed)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
