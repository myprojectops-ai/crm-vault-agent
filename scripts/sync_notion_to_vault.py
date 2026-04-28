from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crm_vault_agent.config import Settings
from crm_vault_agent.dry_run import fetch_crm_records, write_dry_run_outputs
from crm_vault_agent.git_publish import publish_to_github
from crm_vault_agent.vault_writer import write_vault


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Notion CRM into the vault.")
    parser.add_argument("--write", action="store_true", help="Write markdown files into wiki/.")
    parser.add_argument("--push", action="store_true", help="Commit and push changes to GitHub.")
    args = parser.parse_args()

    settings = Settings.from_env()
    records = fetch_crm_records(settings)
    write_dry_run_outputs(settings, records)
    print(f"Dry run complete. Fetched {len(records)} CRM records.")
    print("Wrote raw/_latest_crm_query.json and raw/_sync_dry_run.md")
    if args.write:
        summary = write_vault(settings, records)
        print(
            f"Wrote {summary['prospect_notes']} prospect notes "
            f"and {summary['closed_clients']} closed clients."
        )
    if args.push:
        print(publish_to_github(settings))


if __name__ == "__main__":
    main()
