import asyncio
import os
import textwrap
from typing import List, Optional

from openai import OpenAI
from client import EnvClient
from models import ReviewAction

# --- Configuration ---
# These values are set based on the competition's requirements.
# The environment client will connect to the running server.
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4-turbo") # Placeholder, use a model you have access to
API_KEY = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY") # Use OpenAI key for this script

# The environment name should match the one in your openenv.yaml
BENCHMARK = "codereview_env"
MAX_STEPS = 5 # A reasonable number of steps for a code review task

# --- Logging Functions (MANDATORY) ---
# These functions produce the exact stdout format required by the judges.

def log_start(task: str, env: str, model: str) -> None:
    """Logs the start of an evaluation task."""
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: ReviewAction, reward: float, done: bool, error: Optional[str]) -> None:
    """Logs a single step within the environment."""
    action_str = f"line:{action.line_number},sev:{action.severity},msg:'{(action.message[:15] + '...') if len(action.message)>15 else action.message}'"
    action_str = action_str.replace(" ", "_").replace("\n", "_")
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action_str} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    """Logs the end of an evaluation task."""
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


# --- LLM Interaction ---

def get_system_prompt() -> str:
    """Creates the system prompt that instructs the LLM on its task."""
    return textwrap.dedent(
        """
        You are an expert AI code reviewer. You will be given a code diff and must identify potential bugs.
        Your task is to provide a review action with a line number, severity, a brief message, and a suggested fix.
        - `line_number`: The line where the bug is. Use 0 if you think the code is clean.
        - `severity`: 'critical', 'medium', or 'style'.
        - `message`: A short, one-sentence description of the bug.
        - `suggested_fix`: A short, one-sentence suggestion for how to fix it.

        Respond ONLY with a JSON object in the following format:
        {"line_number": <int>, "severity": "<string>", "message": "<string>", "suggested_fix": "<string>", "rationale": "heuristic"}
        """
    ).strip()

def build_user_prompt(observation: dict) -> str:
    """Builds the user prompt with the current observation from the environment."""
    return textwrap.dedent(
        f"""
        Here is the code diff to review:
        File: {observation.get('filename', 'N/A')}
        ```diff
        {observation.get('diff', '')}
        ```
        Analyze this diff and provide your review action as a single JSON object.
        """
    ).strip()

def get_review_action_from_llm(client: OpenAI, observation: dict) -> ReviewAction:
    """Queries the LLM to get a review action and parses the JSON response."""
    user_prompt = build_user_prompt(observation)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.5,
        )
        response_text = completion.choices[0].message.content or "{}"
        # The model should return a JSON object that matches the ReviewAction structure
        action = ReviewAction.model_validate_json(response_text)
        return action
    except Exception as exc:
        print(f"[DEBUG] Model request failed or returned invalid JSON: {exc}", flush=True)
        # Return a default "looks good" action on failure
        return ReviewAction(line_number=0, severity="style", message="No issues found.", suggested_fix="N/A", rationale="fallback")


async def run_task(task_name: str) -> None:
    """Runs a full evaluation episode for a single task."""
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    local_image = os.getenv("LOCAL_IMAGE_NAME")
    if local_image:
        from client import CodeReviewEnv
        env = await CodeReviewEnv.from_docker_image(local_image)
    else:
        env = EnvClient(base_url=os.getenv("ENV_URL", "http://localhost:8000"))

    rewards: List[float] = []
    steps_taken = 0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        # Reset the environment with the specific task name
        result = await env.reset()
        obs = result.observation
        # Note: OpenEnv doesn't easily pass custom data to reset() natively without modifying reset override.
        # But for this test, CodeReviewEnv already picks up tasks dynamically or we can let it run default.

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            action = get_review_action_from_llm(client, obs.model_dump())

            result = await env.step(action)
            obs = result.observation
            reward = result.reward or 0.0
            done = result.done
            # Assuming env returns metadata via step result depending on version, fallback to generic
            error = getattr(result, "error", None)

            rewards.append(reward)
            steps_taken = step
            log_step(step=step, action=action, reward=reward, done=done, error=error)

            if done:
                break

        # The final score is the total reward accumulated.
        # This can be normalized if a max score is known.
        final_score = min(max(sum(rewards), 0.0), 1.0)
        success = final_score > 0 # Consider it a success if any positive reward was achieved.

    finally:
        await env.close()
        log_end(success=success, steps=steps_taken, score=final_score, rewards=rewards)


async def main() -> None:
    """Runs the inference script for all defined tasks."""
    # As required, we define three tasks from easy to hard.
    tasks = ["easy_style", "medium_security", "hard_logic"]
    for task in tasks:
        await run_task(task)


if __name__ == "__main__":
    # Ensure the server is running before executing this script.
    asyncio.run(main())
