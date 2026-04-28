from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> None:
        return None


load_dotenv()


@dataclass(frozen=True)
class Settings:
    notion_token: str
    notion_crm_database_id: str
    notion_version: str
    vault_root: Path
    github_repo: str
    github_branch: str
    telegram_bot_token: str
    telegram_allowed_user_id: int | None
    openai_api_key: str
    openai_model: str
    sync_interval_hours: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            notion_token=os.getenv("NOTION_TOKEN", ""),
            notion_crm_database_id=os.getenv(
                "NOTION_CRM_DATABASE_ID",
                "9b8e0b5662a143a7b7bd578722707b94",
            ),
            notion_version=os.getenv("NOTION_VERSION", "2022-06-28"),
            vault_root=Path(os.getenv("VAULT_ROOT", ".")).resolve(),
            github_repo=os.getenv("GITHUB_REPO", "myprojectops-ai/crm-vault-agent"),
            github_branch=os.getenv("GITHUB_BRANCH", "main"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_allowed_user_id=_optional_int(os.getenv("TELEGRAM_ALLOWED_USER_ID")),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            sync_interval_hours=int(os.getenv("SYNC_INTERVAL_HOURS", "24")),
        )

    @property
    def raw_dir(self) -> Path:
        return self.vault_root / "raw"

    @property
    def wiki_dir(self) -> Path:
        return self.vault_root / "wiki"

    def require_notion(self) -> None:
        if not self.notion_token:
            raise RuntimeError("Missing NOTION_TOKEN")

    def require_telegram(self) -> None:
        if not self.telegram_bot_token:
            raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")


def _optional_int(value: str | None) -> int | None:
    if not value:
        return None
    return int(value)
