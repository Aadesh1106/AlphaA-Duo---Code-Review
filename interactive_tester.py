import argparse
import json
from typing import Any

import requests


def pretty_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2)


def reset_episode(base_url: str) -> dict[str, Any]:
    response = requests.post(f"{base_url}/reset", json={}, timeout=20)
    response.raise_for_status()
    return response.json()


def submit_action(base_url: str, action: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(f"{base_url}/step", json={"action": action}, timeout=20)
    response.raise_for_status()
    return response.json()


def read_int(prompt: str) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            return int(raw)
        except ValueError:
            print("Please enter a valid integer.")


def run_cli(base_url: str) -> None:
    print(f"Connecting to {base_url}")
    print("Commands: [a]ction, [r]eset, [m]etrics, [q]uit")

    current = reset_episode(base_url)
    print("\nInitial observation:")
    print(pretty_json(current))

    while True:
        cmd = input("\nChoose command (a/r/m/q): ").strip().lower()

        if cmd == "q":
            print("Exiting tester.")
            return

        if cmd == "r":
            current = reset_episode(base_url)
            print("\nReset observation:")
            print(pretty_json(current))
            continue

        if cmd == "m":
            print("\nHTTP endpoint is stateless per request, so running class metrics are not retained here.")
            print("Use local evaluator for persistent metrics:")
            print("  python evaluate_metrics.py --policy heuristic --episodes 200")
            continue

        if cmd != "a":
            print("Unknown command. Use a, r, m, or q.")
            continue

        line_number = read_int("line_number (int): ")
        severity = input("severity (critical/medium/style): ").strip()
        message = input("message: ").strip()
        suggested_fix = input("suggested_fix: ").strip()
        rationale = input("rationale (optional): ").strip()

        payload = {
            "line_number": line_number,
            "severity": severity,
            "message": message,
            "suggested_fix": suggested_fix,
            "rationale": rationale,
        }

        result = submit_action(base_url, payload)
        print("\nStep result:")
        print(pretty_json(result))

        done = bool(result.get("done", False))
        if done:
            print("\nEpisode is done (one action per episode). Auto-resetting...")
            current = reset_episode(base_url)
            print(pretty_json(current))


def main() -> int:
    parser = argparse.ArgumentParser(description="Interactive tester for CodeReview-ENV")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL for environment server")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")

    try:
        health = requests.get(f"{base_url}/health", timeout=10)
        health.raise_for_status()
    except requests.RequestException as exc:
        print(f"Could not reach server at {base_url}: {exc}")
        print("Start it with: docker run -p 8000:8000 codereview-env")
        return 1

    run_cli(base_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
