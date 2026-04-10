import asyncio
import os
import textwrap
import traceback
import sys
from typing import List, Optional

# Ensure we can import from the current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from openai import OpenAI
except ImportError:
    # Fallback if openai is not installed (should be in the environment)
    OpenAI = None

from client import CodeReviewEnv
from models import ReviewAction

# --- Configuration ---
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY") or "EMPTY"

BENCHMARK = "codereview_env"
MAX_STEPS = 5 
IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME") or os.getenv("IMAGE_NAME")
ENV_URL = os.getenv("ENV_URL", "http://localhost:8000")

# --- Logging Functions (STRICT FORMAT) ---
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    # Ensure score is formatted to 3 decimal places for precision, but instructions show 2 in one place and 3 in another.
    # The example [END] line shows score=1.00, but sample main shows score:.3f. We'll use .3f to be safe.
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

# --- LLM Interaction ---
def get_review_action_from_llm(client: OpenAI, observation: dict) -> ReviewAction:
    if not client:
        return ReviewAction(line_number=0, severity="style", message="OpenAI client missing", suggested_fix="N/A", rationale="fallback")
    
    system_prompt = textwrap.dedent("""
        You are an expert AI code reviewer. Locate bugs in the provided code diff.
        Respond ONLY with a JSON object:
        {"line_number": <int>, "severity": "critical"|"medium"|"style", "message": "<string>", "suggested_fix": "<string>", "rationale": "<string>"}
        Use line_number 0 if the code is clean.
    """).strip()
    
    user_prompt = f"File: {observation.get('filename')}\nDiff:\n{observation.get('diff')}"
    
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=256
        )
        response_text = completion.choices[0].message.content or "{}"
        return ReviewAction.model_validate_json(response_text)
    except Exception as exc:
        print(f"[DEBUG] LLM call failed: {exc}", flush=True)
        return ReviewAction(line_number=0, severity="style", message="LLM fallback", suggested_fix="N/A", rationale="error")

async def run_task(task_name: str) -> None:
    """Runs a single episode for the given task."""
    env = None
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        # 1. Initialize API Client
        client = None
        if OpenAI:
            try:
                client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
            except Exception as e:
                print(f"[DEBUG] OpenAI client init failed: {e}", flush=True)

        # 2. Initialize Environment
        if IMAGE_NAME:
            env = await CodeReviewEnv.from_docker_image(IMAGE_NAME)
        else:
            env = CodeReviewEnv(base_url=ENV_URL)

        # 3. Reset Environment
        result = await env.reset(task=task_name)
        obs = result.observation

        # 4. Interaction Loop
        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            # Compatible with Pydantic v1 and v2
            obs_dict = obs.model_dump() if hasattr(obs, 'model_dump') else obs.dict()
            action = get_review_action_from_llm(client, obs_dict)
            
            action_desc = f"review(line={action.line_number},sev={action.severity})"
            
            result = await env.step(action)
            obs = result.observation
            reward = result.reward or 0.0
            done = result.done

            rewards.append(reward)
            steps_taken = step
            log_step(step=step, action=action_desc, reward=reward, done=done, error=None)

            if done:
                break

        # 5. Score Calculation
        # The reward per step is [0, 1]. So sum(rewards) can be up to MAX_STEPS.
        # A fair score is average reward if success means finding any bug.
        # We'll use sum(rewards) / steps_taken to get score in [0, 1].
        if steps_taken > 0:
            score = sum(rewards) / steps_taken
        score = min(max(score, 0.0), 1.0)
        success = score >= 0.1

    except Exception as e:
        print(f"[DEBUG] Unhandled error in run_task: {e}", flush=True)
        traceback.print_exc()
    finally:
        if env:
            try:
                await env.close()
            except Exception as ce:
                print(f"[DEBUG] Env close error: {ce}", flush=True)
        
        # ALWAYS emit [END] exactly once per [START]
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

async def main() -> None:
    # Identify task
    task = os.getenv("TASK_NAME") or os.getenv("MY_ENV_V4_TASK")
    
    if task:
        await run_task(task)
    else:
        # If no task specified, run a default sequence
        for t in ["easy_style", "medium_security", "hard_logic"]:
            await run_task(t)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"CRITICAL: Main execution failed: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

