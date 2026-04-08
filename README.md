# OpenEnv: AI Code Review Environment

This repository contains an OpenEnv environment designed to simulate the real-world task of AI-powered security code review. An AI agent can interact with this environment to learn how to identify, categorize, and suggest fixes for vulnerabilities in code pull requests.

This project was built for the OpenEnv Round 1 competition.

## Environment Description

The `CodeReview-ENV` challenges an AI agent to act as an automated code reviewer. In each episode, the agent is presented with a `diff` from a real-world-style pull request that may contain one or more bugs, ranging from simple style issues to critical security vulnerabilities like SQL Injection or Cross-Site Scripting (XSS).

The agent's task is to submit a structured review action, specifying the line number of the bug, its severity, a descriptive message, and a suggested fix. The environment provides a reward based on the accuracy of the agent's review.

## Action & Observation Spaces

### Action Space

The agent must submit a `ReviewAction` with the following structure:

```python
class ReviewAction(BaseModel):
    line_number: int
    severity: str # "critical", "medium", or "style"
    message: str
    suggested_fix: str
    rationale: str
```

### Observation Space

The environment provides an `Observation` with the following structure:

```python
class ReviewObservation(BaseModel):
    diff: str
    filename: str
    episode_id: int
    file_context: str = ""
    repo_summary: str = ""
    total_bugs: int = 0
    remaining_bugs: int = 0
    is_clean: bool = False
    bug_categories: list[str] = []
```

## Tasks & Difficulty

The environment supports three distinct tasks with increasing difficulty, which can be selected by passing a `task` name to the `reset()` method.

1.  **`easy_style` (Easy)**
    *   **Objective:** The agent is presented with a "clean" pull request that contains no functional or security bugs.
    *   **Success:** The agent correctly identifies that there are no issues by submitting a review with `line_number: 0`. A positive reward is given for correctly identifying a clean PR.

2.  **`medium_security` (Medium)**
    *   **Objective:** The agent must identify a common but clear security vulnerability, such as the use of a non-cryptographic random number generator for a security token.
    *   **Success:** The agent correctly identifies the line number and severity (`medium` or `critical`) of the security flaw.

3.  **`hard_logic` (Hard)**
    *   **Objective:** The agent must identify a subtle, non-obvious logic bug that doesn't fall into a common security category. This requires a deeper understanding of the code's intent.
    *   **Success:** The agent correctly identifies the line number and provides a relevant message for the logic bug.

## Setup and Usage

### 1. Installation

Clone the repository and install the dependencies using `pip`. It is recommended to use a virtual environment.

```bash
git clone https://github.com/ArunN2005/AlphaA-Duo---Code-Review.git
cd AlphaA-Duo---Code-Review
python -m venv .venv
source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
pip install -e .
```

### 2. Running the Environment Server

The environment runs as a web server using FastAPI.

```bash
python -m server.app
```
The server will be available at `http://localhost:8000`.

### 3. Running the Baseline Inference Script

To run the baseline agent and evaluate its performance, set the required environment variables and execute the `inference.py` script.

```bash
# Your API key for the model provider
export OPENAI_API_KEY="<your-api-key>"

# The model you want to use (must be OpenAI compatible)
export MODEL_NAME="gpt-4-turbo"

# The URL of the running environment server
export API_BASE_URL="http://localhost:8000"

python inference.py
```

## Baseline Scores

The following scores were achieved by the baseline `inference.py` script using the `gpt-4-turbo` model. The score represents the total reward accumulated across all steps in an episode.

*   **easy_style:** `0.50`
*   **medium_security:** `1.80`
*   **hard_logic:** `0.90`

*(Note: These scores are representative and may vary slightly based on model responses.)*

| Valid fix suggestion | +0.3 |
| Security bug found exactly | +0.5 bonus |
| False positive penalty | -0.5 |

## How to use
### Remote (no setup needed)
from openenv import CodeReviewEnv
env = CodeReviewEnv(url="https://YOUR-SPACE-URL.hf.space")
obs = env.reset()
obs, reward, done, info = env.step(action)

### Local Docker
docker pull registry.hf.space/YOUR-USERNAME/codereview-env:latest
docker run -p 8000:8000 registry.hf.space/YOUR-USERNAME/codereview-env:latest

## Dataset
50 real-world style PRs across 10 bug categories including SQL injection,
XSS, hardcoded secrets, off-by-one errors, and path traversal.

Current project includes an expanded dataset with 650 entries:
- Multi-bug diffs (episodes can require more than one action)
- Clean calibration diffs for false-positive control
- Mixed Python, JavaScript, and Go patches

Real-world CVE-inspired seed cases are included with provenance metadata
(`source_type=real_cve_seed`), covering:
- Django SQL injection fixes (CVE-2024-53908, CVE-2026-1287)
- python-sql SQL injection (CVE-2024-9774)
- Twisted XSS (CVE-2024-41810)
- aiohttp and youtube-dl traversal patterns
- python-jwt auth bypass (CVE-2022-39227)
- joblib eval() RCE class (CVE-2022-21797)
- GitPython command-sanitization/RCE class (CVE-2023-40267)
- python-multipart ReDoS (CVE-2024-24762)

Ingestion format and loader for real CVE seeds:
- Manifest file: data/cve_manifest.json
- Loader script: ingest_cve_manifest.py

To ingest from manifest:

python ingest_cve_manifest.py

Legacy helper (also idempotent):

python add_real_world_cve_cases.py

## Live web demo
Start the server and open:

http://localhost:8000/web

For judge-facing CVE side-by-side baseline vs reviewer comparison:

http://localhost:8000/web/cve

This UI lets you paste Python/JavaScript/Go snippets and get color-coded
severity badges from the review endpoint.

## Advanced evaluation
Run local smoke test:

python test_local.py

Run interactive HTTP tester:

python interactive_tester.py --url http://localhost:8000

Run policy evaluation with per-class precision/recall/F1:

python evaluate_metrics.py --policy heuristic --episodes 200
python evaluate_metrics.py --policy random --episodes 200

Run full train/eval artifact pipeline (curves + confusion matrices + CSVs):

python train_eval.py --policy both --episodes 300 --out results

Run real CVE seed verification (measured before/after baseline):

python real_cve_check.py

## Action space
line_number: int - which line contains the bug
severity: str - "critical", "medium", or "style"
message: str - description of the bug
suggested_fix: str - how to fix it
rationale: str - optional reasoning text used in reward shaping

## Observation space
diff: str - the pull request diff
filename: str - the file being reviewed
episode_id: int - the PR identifier
file_context: str - local file-level context
repo_summary: str - repository/module-level context

## State space
current_pr_index: int - active PR index in dataset
steps_taken: int - actions taken in the current episode
max_actions: int - action budget for this episode
reviewed_lines: list[int] - lines reviewed so far
session_history: list[dict] - action and reward trail within episode
