# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""Devin API integration for automated cosmetic bug fixes.

Triggered by a GitHub Actions workflow when an issue is labeled
with `bug:cosmetic` or `cosmetic-issue`. Validates the issue,
constructs a prompt, and starts a Devin session to fix the bug.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import requests

DEVIN_API_BASE = "https://api.devin.ai/v3"
GITHUB_API_BASE = "https://api.github.com"


def get_env(name: str) -> str:
    """Retrieve a required environment variable or exit with an error."""
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"ERROR: Missing required environment variable: {name}")
        sys.exit(1)
    return value


def validate_issue(title: str, body: str) -> tuple[bool, str]:
    """Check that the issue has enough information for an automated fix.

    Returns a tuple of (is_valid, reason).
    """
    if not body or len(body.strip()) < 30:
        return False, "Issue description is too short for automated fixing."

    cosmetic_keywords = [
        "css",
        "style",
        "layout",
        "color",
        "font",
        "spacing",
        "margin",
        "padding",
        "alignment",
        "position",
        "overflow",
        "display",
        "border",
        "shadow",
        "opacity",
        "z-index",
        "responsive",
        "mobile",
        "icon",
        "text",
        "label",
        "tooltip",
        "hover",
        "transition",
        "animation",
        "theme",
        "dark mode",
        "light mode",
        "width",
        "height",
        "size",
        "truncat",
        "wrap",
        "scroll",
        "visibility",
        "hidden",
        "overlap",
        "ui",
        "visual",
        "cosmetic",
        "pixel",
        "render",
    ]

    combined = f"{title} {body}".lower()
    has_cosmetic_context = any(kw in combined for kw in cosmetic_keywords)

    if not has_cosmetic_context:
        return False, (
            "Issue does not appear to describe a cosmetic/UI problem. "
            "Skipping automated fix."
        )

    return True, ""


def build_prompt(
    issue_number: int,
    issue_title: str,
    issue_body: str,
    issue_url: str,
    repo_full_name: str,
) -> str:
    """Build the Devin session prompt from the template and issue context."""
    template_path = Path(__file__).parent.parent / "templates" / "devin_prompt.txt"
    template = template_path.read_text()

    return template.format(
        issue_number=issue_number,
        issue_title=issue_title,
        issue_body=issue_body,
        issue_url=issue_url,
        repo_full_name=repo_full_name,
    )


def create_devin_session(
    api_key: str,
    org_id: str,
    prompt: str,
    issue_number: int,
    repo_full_name: str,
) -> dict[str, Any]:
    """Create a Devin session via the v3 API."""
    url = f"{DEVIN_API_BASE}/organizations/{org_id}/sessions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "title": f"Fix cosmetic issue #{issue_number}",
        "repos": [repo_full_name],
        "tags": ["cosmetic-fix", "automated"],
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def post_github_comment(
    token: str,
    repo_full_name: str,
    issue_number: int,
    body: str,
) -> None:
    """Post a comment on the GitHub issue."""
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues/{issue_number}/comments"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    response = requests.post(url, headers=headers, json={"body": body}, timeout=30)
    response.raise_for_status()


def main() -> None:
    """Entry point: validate issue, create Devin session, report status."""
    devin_api_key = get_env("DEVIN_API_KEY")
    devin_org_id = get_env("DEVIN_ORG_ID")
    gh_token = get_env("GH_TOKEN")
    issue_number = int(get_env("ISSUE_NUMBER"))
    issue_title = get_env("ISSUE_TITLE")
    issue_body = os.environ.get("ISSUE_BODY", "")
    issue_url = get_env("ISSUE_URL")
    repo_full_name = get_env("REPO_FULL_NAME")

    # Validate the issue
    is_valid, reason = validate_issue(issue_title, issue_body)
    if not is_valid:
        print(f"Skipping: {reason}")
        post_github_comment(
            gh_token,
            repo_full_name,
            issue_number,
            (
                f"**Automated Cosmetic Fix - Skipped**\n\n{reason}\n\n"
                "Please add more detail to the issue description "
                "(screenshots, affected components, reproduction steps) "
                "and re-apply the label to retry."
            ),
        )
        return

    # Build the prompt
    prompt = build_prompt(
        issue_number, issue_title, issue_body, issue_url, repo_full_name
    )

    # Create the Devin session
    try:
        result = create_devin_session(
            devin_api_key, devin_org_id, prompt, issue_number, repo_full_name
        )
    except requests.HTTPError as e:
        error_msg = f"Failed to create Devin session: {e}"
        print(f"ERROR: {error_msg}")
        post_github_comment(
            gh_token,
            repo_full_name,
            issue_number,
            (
                "**Automated Cosmetic Fix - Error**\n\n"
                "Failed to start the automation session. "
                "A maintainer will investigate."
            ),
        )
        sys.exit(1)

    session_id = result.get("session_id", "unknown")
    session_url = f"https://app.devin.ai/sessions/{session_id}"

    # Post status comment
    post_github_comment(
        gh_token,
        repo_full_name,
        issue_number,
        (
            "**Automated Cosmetic Fix - Started**\n\n"
            f"Devin is working on fixing this cosmetic issue.\n\n"
            f"- **Session**: [{session_id}]({session_url})\n"
            f"- **Status**: In progress\n\n"
            "A PR with before/after screenshots will be opened once the fix "
            "is ready. You can monitor progress at the session link above."
        ),
    )

    print(f"Devin session created: {session_id}")
    print(f"Session URL: {session_url}")
    print(result)


if __name__ == "__main__":
    main()
