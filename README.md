# CodeReview-ENV: AI-Powered Security Review Environment

An advanced OpenEnv-compliant reinforcement learning environment that transforms code reviews into a quantifiable challenge for AI agents.


## Table of Contents

| # | Section |
|---|---|
| 1 | [Overview](#overview) |
| 2 | [The Problem and Solution](#the-problem-and-solution) |
| 3 | [Technology Stack](#technology-stack) |
| 4 | [Action and Observation Spaces](#action-and-observation-spaces) |
| 5 | [Tasks and Difficulty](#tasks-and-difficulty) |
| 6 | [Grading and Reward Logic](#grading-and-reward-logic) |
| 7 | [Quick Start](#quick-start) |
| 8 | [Environment Variables](#environment-variables) |
| 9 | [Baseline Performance](#baseline-performance) |
| 10 | [Project Structure](#project-structure) |

---

## Overview
**CodeReview-ENV** is a specialized RL environment designed for the Meta PyTorch Hackathon (OpenEnv). It simulates the complex, real-world task of a Senior Security Engineer reviewing Pull Requests (PRs). 

Unlike "toy" RL games, this environment uses a massive dataset of **650+ real-world code diffs** and **real-world CVE seeds** (including Django, SQLi, and Auth Bypass vulnerabilities) to evaluate if an AI agent can pinpoint risky code, categorize its severity, and suggest precise fixes.

---

## The Problem and Solution

### The Challenge: Grounding AI in Reality
Standard Large Language Models (LLMs) often catch syntax errors but struggle with **context-aware security vulnerabilities**. 

### The Solution:
CodeReview-ENV provides a structured **Step/Reset loop** where:
1. **Reset**: An agent is given a specific PR task (Style, Security, or Logic).
2. **Step**: The agent identifies a line number, severity, and suggested fix.
3. **Reward**: The system provides a **dense reward signal** based on programmatic truth (distance to bug, severity matching, and keyword overlap in the fix).

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Core Framework** | OpenEnv Core (v0.2+) | Environment standards and evaluation |
| **Server Engine** | FastAPI + Uvicorn | High-performance REST/WebSocket API |
| **Logic Layer** | Python 3.12+ | Reward shaping and grading logic |
| **AI Inference** | OpenAI Client | Standardized LLM interaction |
| **LLM Model** | Qwen 2.5 72B Instruct | Default baseline model |
| **Data Storage** | JSON (Manifest-driven) | 650+ PR Diffs and CVE Metadata |
| **Containerization** | Docker | Compliant submission format |

---

## Action and Observation Spaces

### 🕹️ Action Space (`ReviewAction`)
The agent acts by submitting a structured review:
- `line_number` (int): Target line of the bug (0 for clean).
- `severity` (str): `critical`, `medium`, or `style`.
- `message` (str): Brief description of the issue.
- `suggested_fix` (str): Implementation-level advice.
- `rationale` (str): Reasoning behind the review.

### 👁️ Observation Space (`ReviewObservation`)
The agent perceives a rich state:
- `diff`: The code pull request diff.
- `filename`: Target file path.
- `file_context`: Surrounding code snippets for better grounding.
- `bug_categories`: List of potential bug types in the environment.

---

## Tasks and Difficulty

We provide three distinct tracks to challenge frontier models:

| Task Name | Difficulty | Description |
|-----------|------------|-------------|
| **`easy_style`** | 🟢 Easy | Detecting "Clean" PRs. Agent must correctly abstain (`line: 0`). |
| **`medium_security`** | 🟡 Medium | Detecting common vulnerabilities (SQLi, XSS, Insecure Random). |
| **`hard_logic`** | 🔴 Hard | Subtle logic bugs requiring deep understanding of intent and state. |

---

## Grading and Reward Logic
The environment uses a **Programmatic Ground-Truth Grader** (no LLM-judging) to ensure deterministic scores:

1. **Localization (0.0 - 0.5)**: 
   - Exact line hit: `0.5`
   - Within 2 lines: `0.2`
2. **Severity Matching (0.0 - 0.3)**: 
   - Correct severity category: `0.3`
3. **Fix Quality (0.0 - 0.2)**: 
   - Keyword overlap check between AI suggestion and ground truth fixes.
4. **Hallucination Penalty**:
   - Negative reward for flagging clean code (False Positive).

---

## Quick Start

### Method 1: Docker (Standard Submission Compliance)
To stay strictly compliant with the OpenEnv validator, use the following commands:

```bash
# 1. Build the Docker image
docker build -t codereview-env:latest .

# 2. Start the environment server
docker run -p 8000:8000 codereview-env:latest
```

### Method 2: Local Manual Setup (Two-Terminal Process)
For local testing without Docker, use two separate terminal windows:

**Terminal 1: Start the Environment Server**
```bash
# Navigate to the project root
cd AlphaA-Duo---Code-Review

# Start the server
python -m server.app
```
*Wait for "Uvicorn running on http://0.0.0.0:8000"*

**Terminal 2: Run the Agent Inference**
```bash
# Navigate to the project root
cd AlphaA-Duo---Code-Review

# Set credentials
export HF_TOKEN="<YOUR_HUGGINGFACE_TOKEN>"
export API_BASE_URL="https://router.huggingface.co/v1"

# Run the agent
python inference.py
```

---

## Environment Variables

Configure these variables to customize the inference behavior:

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `HF_TOKEN` | Yes | - | API access token for Hugging Face Inference API |
| `API_BASE_URL` | Yes | `https://router.huggingface.co/v1` | LLM API endpoint (OpenAI-compatible) |
| `MODEL_NAME` | Yes | `Qwen/Qwen2.5-72B-Instruct` | The model identifier for inference |
| `ENV_URL` | No | `http://localhost:8000` | URL where the environment server is mapping |

---

## Baseline Performance
Reproducible results obtained from the reference `inference.py` script:

| Task Name | Avg Score (0.0 - 1.0) | Result |
|-----------|-----------------------|--------|
| **easy_style** | **1.000** | ✅ Passed |
| **medium_security** | **0.800** | ✅ Passed |
| **hard_logic** | **0.225** | ✅ Passed |

*Note: Scores represent the normalized task success rate across the dataset.*

---

## Project Structure
```text
AlphaA-Duo---Code-Review/
├── server/
│   ├── app.py           # FastAPI Spec implementation
│   └── environment.py   # Core RL Logic & Automatic Grader
├── data/
│   └── prs.json        # Manifest of 650+ code diffs
├── models.py            # Pydantic schemas for Action/Observation
├── client.py            # Environment Client wrapper
├── inference.py         # Baseline agent evaluation script
├── Dockerfile           # Submission container configuration
├── pyproject.toml       # Python package metadata
├── uv.lock              # Deterministic dependency lockfile
└── openenv.yaml         # OpenEnv framework configuration
```

---

