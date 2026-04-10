# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""CodeReview-ENV client wrapper."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult

try:
    from .models import ReviewAction, ReviewObservation, ReviewState
except ImportError:
    from models import ReviewAction, ReviewObservation, ReviewState


class CodeReviewEnv(EnvClient[ReviewAction, ReviewObservation, ReviewState]):
    """
    Client for CodeReview-ENV.

    This client maintains a persistent WebSocket connection to the environment server,
    enabling efficient multi-step interactions with lower latency.
    Each client instance has its own dedicated environment session on the server.

    Example:
        >>> # Connect to a running server
        >>> with CodereviewEnv(base_url="http://localhost:8000") as client:
        ...     result = client.reset()
        ...     print(result.observation.echoed_message)
        ...
        ...     result = client.step(CodereviewAction(message="Hello!"))
        ...     print(result.observation.echoed_message)

    Example with Docker:
        >>> # Automatically start container and connect
        >>> client = CodereviewEnv.from_docker_image("codereview_env-env:latest")
        >>> try:
        ...     result = client.reset()
        ...     result = client.step(CodereviewAction(message="Test"))
        ... finally:
        ...     client.close()
    """

    def _step_payload(self, action: ReviewAction) -> Dict:
        """
        Convert ReviewAction to JSON payload for step message.

        Args:
            action: ReviewAction instance

        Returns:
            Dictionary representation suitable for JSON encoding
        """
        return {
            "line_number": action.line_number,
            "severity": action.severity,
            "message": action.message,
            "suggested_fix": action.suggested_fix,
            "rationale": action.rationale,
        }

    def _parse_result(self, payload: dict) -> StepResult[ReviewObservation]:
        """
        Parse server response into StepResult[ReviewObservation].
        """
        obs_data = payload.get("observation", {})
        observation = ReviewObservation(
            diff=obs_data.get("diff", ""),
            filename=obs_data.get("filename", ""),
            episode_id=obs_data.get("episode_id", -1),
            file_context=obs_data.get("file_context", ""),
            repo_summary=obs_data.get("repo_summary", ""),
            total_bugs=obs_data.get("total_bugs", 0),
            remaining_bugs=obs_data.get("remaining_bugs", 0),
            is_clean=obs_data.get("is_clean", False),
            bug_categories=obs_data.get("bug_categories", []),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict) -> ReviewState:
        """
        Parse server response into ReviewState object.
        """
        return ReviewState(
            current_pr_index=payload.get("current_pr_index", 0),
            done=payload.get("done", False),
            steps_taken=payload.get("steps_taken", 0),
            max_actions=payload.get("max_actions", 1),
            found_bug_count=payload.get("found_bug_count", 0),
            total_bug_count=payload.get("total_bug_count", 0),
            reviewed_lines=payload.get("reviewed_lines", []),
            session_history=payload.get("session_history", []),
        )


CodereviewEnv = CodeReviewEnv
