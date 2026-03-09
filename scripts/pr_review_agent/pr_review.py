#!/usr/bin/env python3
"""
PR Review Agent for D2RS-2026spring/members.

Reads the beginner-DS rubric, fetches the PR diff via GitHub REST API,
calls the GitHub Copilot / GitHub Models LLM, and posts (or updates) a
single review comment on the PR.

Security note
-------------
This script is designed to run in a pull_request_target workflow where:
  - Only BASE-branch code is checked out.
  - No fork code is executed.
  - All PR data comes from the GitHub REST API (diff as text only).
"""

import os
import sys
import textwrap
from typing import Optional

import requests

# ---------------------------------------------------------------------------
# Constants / configuration
# ---------------------------------------------------------------------------

# Unique HTML marker so we can find and update our comment instead of
# posting a new one on each push.
COMMENT_MARKER = "<!-- beginner-ds-pr-review-agent -->"

# GitHub Models / Copilot inference endpoint (GitHub-hosted, uses GITHUB_TOKEN).
GITHUB_MODELS_API = "https://models.inference.ai.azure.com"
MODEL_NAME = "gpt-4o-mini"  # Lightweight model available via GitHub Models

# Diff truncation limits (characters).
# These limits apply to the diff portion of the prompt only.
# The full prompt also includes the rubric (~6 000 chars), PR title/body,
# and system instructions, so the effective total is roughly:
#   MAX_DIFF_TOTAL_CHARS + ~8 000 chars overhead ≈ 36 000 chars (~9 000 tokens).
# gpt-4o-mini supports 128 k tokens, so this leaves ample headroom.
# Reduce MAX_DIFF_TOTAL_CHARS if you switch to a smaller-context model.
MAX_DIFF_TOTAL_CHARS = 28_000
MAX_DIFF_PER_FILE_CHARS = 4_000

# File extensions to include in the diff (skip binary / generated files).
ALLOWED_EXTENSIONS = {
    ".py", ".r", ".rmd", ".qmd", ".md", ".txt", ".csv", ".yaml", ".yml",
    ".json", ".toml", ".cfg", ".ini",
}

# ---------------------------------------------------------------------------
# Helper: GitHub REST API
# ---------------------------------------------------------------------------


def gh_get(path: str, token: str, accept: str = "application/vnd.github+json") -> dict:
    """GET a GitHub API endpoint and return parsed JSON."""
    url = f"https://api.github.com{path}"
    resp = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def gh_get_text(path: str, token: str, accept: str) -> str:
    """GET a GitHub API endpoint and return raw text."""
    url = f"https://api.github.com{path}"
    resp = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.text


def gh_post(path: str, token: str, payload: dict) -> dict:
    """POST to a GitHub API endpoint and return parsed JSON."""
    url = f"https://api.github.com{path}"
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def gh_patch(path: str, token: str, payload: dict) -> dict:
    """PATCH a GitHub API endpoint and return parsed JSON."""
    url = f"https://api.github.com{path}"
    resp = requests.patch(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Helper: fetch and truncate the PR diff
# ---------------------------------------------------------------------------


def fetch_pr_diff(repo: str, pr_number: int, token: str) -> str:
    """
    Fetch the unified diff for a PR via the GitHub API.

    Returns a truncated string that fits within MAX_DIFF_TOTAL_CHARS,
    prioritising the first N lines of each file's patch.
    """
    files = gh_get(f"/repos/{repo}/pulls/{pr_number}/files", token)

    chunks = []
    total_chars = 0

    for file_info in files:
        filename: str = file_info.get("filename", "")
        status: str = file_info.get("status", "")
        patch: str = file_info.get("patch", "")

        # Skip binary files and files we cannot meaningfully review.
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            chunks.append(f"--- {filename} [{status}] (skipped: unsupported type) ---\n")
            continue

        if not patch:
            chunks.append(f"--- {filename} [{status}] (no text diff) ---\n")
            continue

        header = f"--- {filename} [{status}] ---\n"
        if len(patch) > MAX_DIFF_PER_FILE_CHARS:
            patch = patch[:MAX_DIFF_PER_FILE_CHARS] + "\n... [truncated] ..."

        chunk = header + patch + "\n"

        if total_chars + len(chunk) > MAX_DIFF_TOTAL_CHARS:
            chunks.append("\n... [remaining files truncated due to size limit] ...\n")
            break

        chunks.append(chunk)
        total_chars += len(chunk)

    return "\n".join(chunks)


# ---------------------------------------------------------------------------
# Helper: read the rubric
# ---------------------------------------------------------------------------


def read_rubric() -> str:
    """Read the rubric file from the repository root."""
    rubric_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "beginner-ds-pr-review-rubric.txt",
    )
    if not os.path.exists(rubric_path):
        return "(Rubric file not found – proceeding without it.)"
    with open(rubric_path, encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Helper: call the LLM via GitHub Models API
# ---------------------------------------------------------------------------


def call_llm(prompt: str, token: str) -> str:
    """
    Call the GitHub Models / Copilot inference API.

    Uses the OpenAI-compatible chat completions endpoint provided by
    GitHub Models (https://models.inference.ai.azure.com).
    """
    url = f"{GITHUB_MODELS_API}/chat/completions"
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a helpful, encouraging code-review assistant for a "
                    "beginner data-science course. "
                    "Provide constructive, teaching-focused feedback. "
                    "Be concise and kind. Use Markdown formatting in your response."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1500,
        "temperature": 0.3,
    }
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )

    if not resp.ok:
        # Surface a useful error message instead of a raw exception.
        raise RuntimeError(
            f"LLM API call failed ({resp.status_code}): {resp.text[:500]}"
        )

    data = resp.json()
    return data["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Helper: find or create the bot comment
# ---------------------------------------------------------------------------


def find_existing_comment(repo: str, pr_number: int, token: str) -> Optional[int]:
    """Return the comment ID of an existing bot comment, or None."""
    comments = gh_get(f"/repos/{repo}/issues/{pr_number}/comments", token)
    for comment in comments:
        if COMMENT_MARKER in comment.get("body", ""):
            return comment["id"]
    return None


def post_or_update_comment(repo: str, pr_number: int, token: str, body: str) -> None:
    """Post a new comment or update the existing bot comment."""
    comment_id = find_existing_comment(repo, pr_number, token)
    if comment_id:
        gh_patch(f"/repos/{repo}/issues/comments/{comment_id}", token, {"body": body})
        print(f"Updated existing comment {comment_id}.")
    else:
        gh_post(f"/repos/{repo}/issues/{pr_number}/comments", token, {"body": body})
        print("Posted new comment.")


# ---------------------------------------------------------------------------
# Helper: build the LLM prompt
# ---------------------------------------------------------------------------


def build_prompt(pr_title: str, pr_body: str, diff: str, rubric: str) -> str:
    return textwrap.dedent(f"""
        You are reviewing a student pull request for a beginner data-science course.
        Use the rubric below to guide your feedback.

        ## Rubric
        {rubric}

        ---

        ## Pull Request Information
        **Title:** {pr_title}

        **Description:**
        {pr_body or "(no description provided)"}

        ---

        ## Changed Files (diff / patch)
        ```diff
        {diff}
        ```

        ---

        ## Instructions
        Please provide a structured review with the following sections:

        ### 📋 Summary
        One or two sentences summarising what the PR does and your overall impression.

        ### 🔴 Must Fix
        List issues that need to be corrected before the work is complete.
        Reference the relevant rubric section where applicable.

        ### 🟡 Should Improve
        List suggestions that would significantly improve the quality of the work.

        ### 🟢 Nice to Have
        Optional improvements or ideas for the student to explore further.

        ### 💡 Learning Tip
        One short, encouraging teaching tip tailored to this specific PR.

        Be concise, kind, and constructive. If there are no issues in a section,
        write "None – great work!" for that section.
    """).strip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN", "")
    pr_number_str = os.environ.get("PR_NUMBER", "")
    repo = os.environ.get("PR_REPO", "")
    pr_title = os.environ.get("PR_TITLE", "(no title)")
    pr_body = os.environ.get("PR_BODY", "")

    if not token:
        print("ERROR: GITHUB_TOKEN is not set.", file=sys.stderr)
        sys.exit(1)
    if not pr_number_str or not repo:
        print("ERROR: PR_NUMBER or PR_REPO env vars are missing.", file=sys.stderr)
        sys.exit(1)

    pr_number = int(pr_number_str)

    print(f"Reviewing PR #{pr_number} in {repo} …")

    # 1. Read the rubric from the checked-out base branch.
    rubric = read_rubric()
    print(f"Rubric loaded ({len(rubric)} chars).")

    # 2. Fetch the PR diff via API (no fork code is executed).
    diff = fetch_pr_diff(repo, pr_number, token)
    print(f"Diff fetched ({len(diff)} chars after truncation).")

    # 3. Build the prompt and call the LLM.
    prompt = build_prompt(pr_title, pr_body, diff, rubric)
    print(f"Calling LLM ({MODEL_NAME}) …")

    try:
        review_text = call_llm(prompt, token)
    except RuntimeError as exc:
        # Post a fallback comment so the student knows the review ran.
        review_text = textwrap.dedent(f"""
            ⚠️ The automated review could not be completed because the LLM API
            returned an error:

            ```
            {exc}
            ```

            Please ask your instructor for a manual review.
        """).strip()
        print(f"LLM error: {exc}", file=sys.stderr)

    # 4. Wrap with the marker and post / update the comment.
    full_comment = f"{COMMENT_MARKER}\n\n{review_text}"
    post_or_update_comment(repo, pr_number, token, full_comment)
    print("Done.")


if __name__ == "__main__":
    main()
