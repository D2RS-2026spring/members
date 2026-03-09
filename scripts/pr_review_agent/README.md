# PR Review Agent

A teaching-focused, LLM-powered pull-request review agent for the
`D2RS-2026spring/members` course repository.

---

## How the agent works

```
pull_request_target event
        │
        ▼
pr-rubric-review.yml (GitHub Actions)
        │
        ├── Checks out BASE branch only (never touches fork code)
        ├── Reads  beginner-ds-pr-review-rubric.txt  from the base branch
        │
        ├── Calls scripts/pr_review_agent/pr_review.py
        │       │
        │       ├── Fetches PR diff via GitHub REST API  (/repos/:owner/:repo/pulls/:number/files)
        │       ├── Truncates diff to stay within token limits
        │       ├── Builds a structured prompt (rubric + PR metadata + diff)
        │       ├── Calls GitHub Models API  (https://models.inference.ai.azure.com)
        │       │       model: gpt-4o-mini  (configurable)
        │       └── Posts / updates a single PR comment with the review
        │
        └── Comment contains a unique HTML marker so it is updated (not duplicated)
            on every push to the PR.
```

---

## Why `pull_request_target` is used (and how it is kept safe)

### The problem with `pull_request`

Workflows triggered by `pull_request` from a fork run in the **fork's
context** and do **not** have access to repository secrets (including
`GITHUB_TOKEN` with write permissions).  This means the workflow cannot
post comments back to the PR, and cannot call the GitHub Models API
which requires authentication.

### Why `pull_request_target` solves it

`pull_request_target` runs in the **base repository's context**, giving
the workflow access to repository secrets and a `GITHUB_TOKEN` with
`pull-requests: write` permission.  This is how the bot can post comments.

### How we keep it safe

`pull_request_target` is powerful – if misused it can allow fork code to
run with elevated privileges (a critical supply-chain attack vector).

This workflow applies **all recommended mitigations**:

| Risk | Mitigation |
|------|-----------|
| Running fork code | ✅ We never check out the PR branch. `actions/checkout` is called with `ref: github.event.pull_request.base.ref` (base branch only). |
| Executing attacker scripts | ✅ The Python script only fetches diff text via the API; no eval / exec of user content. |
| Secret exfiltration via environment | ✅ `PR_TITLE` and `PR_BODY` are passed as plain env vars; they are treated as text only, never interpolated into shell commands. |
| Scope creep | ✅ `permissions` block limits the token to `contents: read`, `pull-requests: write`, `models: read` – nothing else. |

References:
- [GitHub Docs – Security hardening for pull_request_target](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions#understanding-the-risk-of-script-injections)
- [GitHub Security Lab – Keeping your GitHub Actions and workflows secure](https://securitylab.github.com/research/github-actions-preventing-pwn-requests/)

---

## Prerequisites

### Repository settings

1. **GitHub Models** must be enabled for the organisation or repository.
   Go to **Settings → Copilot → GitHub Models** and ensure the feature is on.
   The `GITHUB_TOKEN` is used automatically; no additional secrets are needed.

2. The `GITHUB_TOKEN` needs `pull-requests: write` – this is granted by the
   `permissions` block in the workflow file.

### Local setup (optional)

You can run the review script locally for testing:

```bash
# Clone the repo (base branch).
git clone https://github.com/D2RS-2026spring/members.git
cd members

# Install Python dependencies.
pip install requests

# Export required environment variables.
export GITHUB_TOKEN="ghp_your_personal_access_token"   # needs repo + models scope
export PR_REPO="D2RS-2026spring/members"
export PR_NUMBER="42"
export PR_TITLE="Add my analysis notebook"
export PR_BODY="This PR adds my issue-1 analysis."

# Run the script.
python scripts/pr_review_agent/pr_review.py
```

The script will post (or update) a comment on PR #42 in the specified repo.

---

## Configuration

### Changing the model

Edit `pr_review.py` and change the `MODEL_NAME` constant:

```python
MODEL_NAME = "gpt-4o-mini"   # cheap & fast
# MODEL_NAME = "gpt-4o"      # higher quality, higher cost
```

All models available through GitHub Models work as long as `GITHUB_TOKEN`
has access.

### Adjusting diff size limits

In `pr_review.py`:

```python
MAX_DIFF_TOTAL_CHARS = 28_000   # total diff sent to the model
MAX_DIFF_PER_FILE_CHARS = 4_000 # max chars per individual file patch
```

Increase these values for larger PRs; decrease them to reduce token cost
and latency.

### Changing which file types are reviewed

```python
ALLOWED_EXTENSIONS = {
    ".py", ".r", ".rmd", ".qmd", ".md", ".txt", ".csv", ...
}
```

Add or remove extensions as needed.  Binary files (`.png`, `.pdf`, etc.)
are automatically skipped because the GitHub API does not provide a text
diff for them.

### Updating the rubric

Edit `beginner-ds-pr-review-rubric.txt` at the repository root.  The
rubric is read fresh on every workflow run, so changes take effect
immediately on the next PR push without modifying the workflow.

---

## Deterministic PR checks (`pr-checks.yml`)

A separate, fork-safe workflow (`pull_request` trigger, no secrets) runs
lightweight static checks:

| Language | Check |
|----------|-------|
| Python | `ruff` lint (non-blocking) + `python -m compileall` (syntax, blocking) |
| R / Rmd | `Rscript -e "parse(...)"` (syntax, blocking) + `lintr` (non-blocking) |
| Markdown / text | `file --mime-encoding` UTF-8 check (blocking) |

These checks run on **changed files only** to keep CI fast.

---

## Comment format

Every review comment starts with the hidden HTML marker
`<!-- beginner-ds-pr-review-agent -->`.  On subsequent pushes to the same
PR the script searches for this marker and **patches** the existing comment
instead of creating a new one.  Students see a single, always-current
review.

The comment body follows this structure:

```
📋 Summary
🔴 Must Fix
🟡 Should Improve
🟢 Nice to Have
💡 Learning Tip
```
