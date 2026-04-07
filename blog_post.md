Title: Teaching AI to Catch Bugs Like a Senior Engineer

A few weeks ago, we pasted this into a plain baseline model and asked for a review:

```python
def run_job(pre_dispatch):
    # user-controlled string from request payload
    workers = eval(pre_dispatch)
    return workers
```

The answer was basically, "Looks fine, maybe add type hints." That code is dangerous: evaluating user-controlled input is a direct code execution footgun. In CodeReview-ENV, we train an agent to point at the exact risky line, mark severity correctly, and propose a concrete fix. On our real CVE seed set, the baseline policy scored a negative average reward while the trained heuristic policy consistently identified the vulnerable lines.

Section 1 - What is CodeReview-ENV

CodeReview-ENV is an OpenENV reinforcement-learning environment for code review. Each episode gives the agent a pull request diff plus context fields: file context and a repo/module summary. The agent submits a structured review action: line number, severity, explanation, suggested fix, and optional rationale. That means the action looks like a real code-review comment, not a toy classification label.

The environment now supports both single-bug and multi-bug pull requests. It also includes clean calibration diffs so the model learns to abstain when there is no bug. This matters a lot in practice. A reviewer that flags everything creates noise and burns trust. We score precision behavior directly so the model is rewarded for being right, not loud.

Section 2 - Why code review is a perfect RL task

Code review works well for RL because the reward is testable. There is a real target line. There is a known severity expectation. There is a fix pattern that can be validated against reference guidance. You do not need a subjective LLM judge for every step.

That objectivity gives fast iteration loops. We can compare policies with the same episodes and produce precision/recall/F1 by category, not just one big reward number. In this project, we track classes like SQL injection, XSS, path traversal, insecure randomness, auth bypass style bugs, and clean/no-bug cases. This gives concrete feedback about where the policy is weak.

Section 3 - The reward function

The reward signal is intentionally multi-dimensional. Exact line match gets the highest localization score, with partial credit for near misses. Correct severity gets additional reward. Suggested fixes are checked by keyword overlap with ground-truth fixes. We also include reasoning quality signals for conciseness, correctness, and non-hallucination behavior.

The false-positive penalty is still the backbone of the system. If the model flags clean code, it is penalized. That avoids the classic degenerate strategy where the policy marks every line as critical just to hit occasional true bugs. In real teams, false positives are expensive. We wanted the reward function to reflect real reviewer ergonomics, not just benchmark gaming.

Section 4 - What we learned building this

The hardest part was not writing the environment class. The hard part was data discipline: making diffs realistic, adding provenance metadata, and balancing categories so one class does not dominate policy behavior. The other surprise was how much calibration data changes outcomes. Adding clean diffs and explicit abstention signals made behavior noticeably more trustworthy.

We also added a real-CVE seed pipeline with manifest-driven ingestion. The seed set includes Django SQL injection fixes, Twisted XSS, python-jwt auth bypass, joblib eval-based RCE class, and python-multipart ReDoS. In our measured check over these seeded CVE cases, the baseline policy averaged -0.55 reward while the heuristic policy averaged +2.31, with 100% exact-line hits on the current seed set.

Closing: Link to the Hugging Face Space. Invite people to try it.

If you want to test it yourself, open the Hugging Face Space and try the live demo: https://huggingface.co/spaces/YOUR-USERNAME/codereview-env. Paste a snippet, inspect the severity badges, and run the local eval scripts if you want the full metrics trail. If you build a better policy, share it. This environment was made to be pushed and improved.