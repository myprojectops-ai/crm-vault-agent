from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from .config import Settings
from .notion_client import NotionClient, page_to_flat_record


def fetch_crm_records(settings: Settings) -> list[dict[str, Any]]:
    settings.require_notion()
    client = NotionClient(settings.notion_token, settings.notion_version)
    pages = client.query_database(settings.notion_crm_database_id)
    return [page_to_flat_record(page) for page in pages]


def build_dry_run_report(records: list[dict[str, Any]]) -> str:
    statuses = Counter(str(record.get("Estado Cliente") or "Sin estado") for record in records)
    results = Counter(str(record.get("Resultado llamada") or "Sin resultado") for record in records)
    closed = [record for record in records if record.get("Estado Cliente") == "Cliente Cerrado"]

    lines = [
        "# CRM Sync Dry Run",
        "",
        f"- Ejecutado: {datetime.now(timezone.utc).isoformat()}",
        f"- Total registros: {len(records)}",
        f"- Clientes cerrados: {len(closed)}",
        "",
        "## Estado Cliente",
        "",
    ]
    for status, count in statuses.most_common():
        lines.append(f"- {status}: {count}")

    lines.extend(["", "## Resultado llamada", ""])
    for result, count in results.most_common():
        lines.append(f"- {result}: {count}")

    lines.extend(["", "## Clientes cerrados detectados", ""])
    for record in sorted(closed, key=lambda item: str(item.get("Fecha llamada") or ""), reverse=True):
        name = record.get("Nombre Prospecto") or "(sin nombre)"
        cash = record.get("Cash collected") or "-"
        date = record.get("Fecha llamada") or "-"
        lines.append(f"- {name} · {cash} · {date}")

    return "\n".join(lines)


def write_dry_run_outputs(settings: Settings, records: list[dict[str, Any]]) -> None:
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    (settings.raw_dir / "_latest_crm_query.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (settings.raw_dir / "_sync_dry_run.md").write_text(
        build_dry_run_report(records),
        encoding="utf-8",
    )
