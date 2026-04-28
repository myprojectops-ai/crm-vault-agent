from __future__ import annotations

from typing import Any

from .config import Settings
from .markdown import assign_slugs, render_closed_clients, render_prospect, render_prospect_index


def write_vault(settings: Settings, records: list[dict[str, Any]]) -> dict[str, int]:
    prospectos_dir = settings.wiki_dir / "crm" / "prospectos"
    prospectos_dir.mkdir(parents=True, exist_ok=True)
    (settings.wiki_dir / "crm").mkdir(parents=True, exist_ok=True)

    slugs = assign_slugs(records)

    written = 0
    for record in records:
        slug = slugs[str(record.get("id") or "")]
        path = prospectos_dir / f"{slug}.md"
        path.write_text(render_prospect(record, slug, path), encoding="utf-8")
        written += 1

    (prospectos_dir / "_index.md").write_text(
        render_prospect_index(records, slugs),
        encoding="utf-8",
    )
    (settings.wiki_dir / "crm" / "clientes-cerrados.md").write_text(
        render_closed_clients(records, slugs),
        encoding="utf-8",
    )

    return {
        "prospect_notes": written,
        "closed_clients": len([r for r in records if r.get("Estado Cliente") == "Cliente Cerrado"]),
    }
