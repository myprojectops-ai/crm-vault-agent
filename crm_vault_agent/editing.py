from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import Settings
from .dry_run import fetch_crm_records
from .notion_client import NotionClient, notion_update_property


EDITABLE_FIELDS = {
    "Estado Cliente",
    "Resultado llamada",
    "Prioridad follow-up",
    "Siguiente acción",
    "Fecha próximo contacto",
    "Notas / Plan de pago",
    "Notas llamada",
    "Cash collected",
    "Asistió llamada",
}


@dataclass(frozen=True)
class PendingEdit:
    page_id: str
    prospect_name: str
    field: str
    old_value: Any
    new_value: str


def parse_edit_command(text: str) -> tuple[str, str, str]:
    payload = text.removeprefix("/editar").strip()
    parts = [part.strip() for part in payload.split("|")]
    if len(parts) != 3:
        raise ValueError("Formato: /editar Nombre Prospecto | Campo | Nuevo valor")
    return parts[0], parts[1], parts[2]


def find_record(records: list[dict[str, Any]], name_query: str) -> dict[str, Any]:
    needle = name_query.strip().lower()
    exact = [record for record in records if str(record.get("Nombre Prospecto") or "").lower() == needle]
    if len(exact) == 1:
        return exact[0]
    contains = [record for record in records if needle in str(record.get("Nombre Prospecto") or "").lower()]
    if len(contains) == 1:
        return contains[0]
    if not contains:
        raise ValueError(f"No encontre prospecto para: {name_query}")
    names = ", ".join(str(record.get("Nombre Prospecto") or "-") for record in contains[:8])
    raise ValueError(f"Hay varios prospectos que coinciden. Se mas especifico: {names}")


def prepare_edit(settings: Settings, text: str) -> PendingEdit:
    name_query, field, value = parse_edit_command(text)
    if field not in EDITABLE_FIELDS:
        allowed = ", ".join(sorted(EDITABLE_FIELDS))
        raise ValueError(f"Campo no editable. Permitidos: {allowed}")
    records = fetch_crm_records(settings)
    record = find_record(records, name_query)
    return PendingEdit(
        page_id=str(record["id"]),
        prospect_name=str(record.get("Nombre Prospecto") or name_query),
        field=field,
        old_value=record.get(field) or "-",
        new_value=value,
    )


def apply_edit(settings: Settings, pending: PendingEdit) -> None:
    client = NotionClient(settings.notion_token, settings.notion_version)
    client.update_page_properties(
        pending.page_id,
        notion_update_property(pending.field, pending.new_value),
    )
