# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Data models for the Codereview Env Environment.

The codereview_env environment is a simple test environment that echoes back messages.
"""

from pydantic import BaseModel, Field


class ReviewAction(BaseModel):
    line_number: int
    severity: str  # "critical", "medium", or "style"
    message: str
    suggested_fix: str
    rationale: str = Field(default="")


class ReviewObservation(BaseModel):
    diff: str
    filename: str
    episode_id: int
    file_context: str = ""
    repo_summary: str = ""
    total_bugs: int = 0
    remaining_bugs: int = 0
    is_clean: bool = False
    bug_categories: list[str] = Field(default_factory=list)


class ReviewState(BaseModel):
    current_pr_index: int
    done: bool
    steps_taken: int = 0
    max_actions: int = 1
    found_bug_count: int = 0
    total_bug_count: int = 0
    reviewed_lines: list[int] = Field(default_factory=list)
    session_history: list[dict] = Field(default_factory=list)
