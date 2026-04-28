from __future__ import annotations

import base64
import subprocess
from datetime import datetime

from .config import Settings


def publish_to_github(settings: Settings, message: str | None = None) -> str:
    settings.require_github()
    message = message or f"CRM vault sync {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    run_git(settings, ["add", "."])
    status = run_git(settings, ["status", "--porcelain"], capture=True)
    if not status.strip():
        return "No changes to publish."

    run_git(settings, ["commit", "-m", message])
    run_git(settings, ["push", "origin", settings.github_branch], authenticated=True)
    return "Published changes to GitHub."


def run_git(
    settings: Settings,
    args: list[str],
    capture: bool = False,
    authenticated: bool = False,
) -> str:
    command = ["git", "-c", f"safe.directory={settings.vault_root}"]
    if authenticated:
        token_pair = f"x-access-token:{settings.github_token}".encode("ascii")
        header = base64.b64encode(token_pair).decode("ascii")
        command.extend(["-c", f"http.extraheader=AUTHORIZATION: basic {header}"])
    command.extend(args)

    result = subprocess.run(
        command,
        cwd=settings.vault_root,
        check=True,
        text=True,
        capture_output=capture,
    )
    return result.stdout if capture else ""
