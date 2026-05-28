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
"""Screenshot capture utilities for Superset cosmetic bug automation.

Provides helpers to start the dev environment, wait for it to be
healthy, and capture before/after screenshots using Playwright.
These functions are intended to be called from within a Devin session.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SUPERSET_URL = "http://localhost:8088"
SUPERSET_LOGIN_URL = f"{SUPERSET_URL}/login/"
SCREENSHOTS_DIR = Path("screenshots")
HEALTH_CHECK_URL = f"{SUPERSET_URL}/health"

DEFAULT_CREDENTIALS = {"username": "admin", "password": "admin"}

DOCKER_COMPOSE_FILES = [
    "docker-compose-light.yml",
    "docker-compose-non-dev.yml",
    "docker-compose.yml",
]

MAX_HEALTH_WAIT_SECONDS = 300
HEALTH_POLL_INTERVAL = 10


def run_command(
    cmd: list[str],
    check: bool = True,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a shell command and return the result."""
    return subprocess.run(  # noqa: S603
        cmd,
        check=check,
        capture_output=capture,
        text=True,
    )


def start_docker_compose(compose_file: str = "docker-compose-non-dev.yml") -> bool:
    """Start Docker Compose services and return True on success."""
    print(f"Starting Docker Compose with {compose_file}...")
    try:
        run_command(
            ["docker", "compose", "-f", compose_file, "up", "-d"],
            capture=False,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to start Docker Compose: {e}")
        return False


def wait_for_healthy(timeout: int = MAX_HEALTH_WAIT_SECONDS) -> bool:
    """Poll the Superset health endpoint until it responds or times out."""
    print(f"Waiting for Superset to be healthy at {HEALTH_CHECK_URL}...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            result = run_command(
                ["curl", "-sf", HEALTH_CHECK_URL],
                check=False,
            )
            if result.returncode == 0:
                print("Superset is healthy.")
                return True
        except Exception:  # noqa: S110
            pass
        time.sleep(HEALTH_POLL_INTERVAL)

    print(f"Timeout: Superset did not become healthy within {timeout}s.")
    return False


def stop_docker_compose(compose_file: str = "docker-compose-non-dev.yml") -> None:
    """Tear down Docker Compose services."""
    print("Stopping Docker Compose services...")
    run_command(
        ["docker", "compose", "-f", compose_file, "down"],
        check=False,
        capture=False,
    )


def capture_screenshot(
    url: str,
    output_path: Path,
    viewport_width: int = 1920,
    viewport_height: int = 1080,
    login: bool = True,
) -> bool:
    """Capture a screenshot of the given URL using Playwright.

    Returns True on success, False on failure.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "Playwright is not installed. "
            "Install it with: pip install playwright && playwright install chromium"
        )
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": viewport_width, "height": viewport_height},
            )
            page = context.new_page()

            if login:
                _perform_login(page)

            page.goto(url, wait_until="networkidle", timeout=60_000)
            page.wait_for_timeout(2000)
            page.screenshot(path=str(output_path), full_page=True)
            browser.close()

        print(f"Screenshot saved: {output_path}")
        return True

    except Exception as e:
        print(f"Screenshot capture failed: {e}")
        return False


def _perform_login(page: Any) -> None:
    """Log into Superset with default credentials."""
    page.goto(SUPERSET_LOGIN_URL, wait_until="networkidle", timeout=30_000)
    page.fill('input[name="username"]', DEFAULT_CREDENTIALS["username"])
    page.fill('input[name="password"]', DEFAULT_CREDENTIALS["password"])
    page.click('input[type="submit"]')
    page.wait_for_load_state("networkidle")


def capture_before_after(
    url: str,
    label: str = "cosmetic-fix",
) -> dict[str, Path]:
    """Capture before and after screenshots for the given URL.

    The caller is responsible for applying the fix between the two calls.
    This function captures only the "before" state. Call
    ``capture_screenshot`` again for the "after" state after the fix is
    applied.
    """
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    before_path = SCREENSHOTS_DIR / f"{label}-before.png"
    after_path = SCREENSHOTS_DIR / f"{label}-after.png"

    capture_screenshot(url, before_path)

    return {"before": before_path, "after": after_path}


def main() -> None:
    """CLI entry point for manual testing."""
    if len(sys.argv) < 2:
        print("Usage: capture_screenshots.py <url> [label]")
        print("Example: capture_screenshots.py http://localhost:8088/dashboard/1/")
        sys.exit(1)

    url = sys.argv[1]
    label = sys.argv[2] if len(sys.argv) > 2 else "test"

    if not wait_for_healthy(timeout=30):
        print("Superset is not running. Start it first.")
        sys.exit(1)

    output = SCREENSHOTS_DIR / f"{label}.png"
    success = capture_screenshot(url, output)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
