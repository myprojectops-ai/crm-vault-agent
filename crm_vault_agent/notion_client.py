from __future__ import annotations

from typing import Any

import requests


class NotionClient:
    def __init__(self, token: str, version: str = "2022-06-28") -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Notion-Version": version,
                "Content-Type": "application/json",
            }
        )

    def query_database(self, database_id: str) -> list[dict[str, Any]]:
        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        payload: dict[str, Any] = {"page_size": 100}
        results: list[dict[str, Any]] = []

        while True:
            response = self.session.post(url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            results.extend(data.get("results", []))

            if not data.get("has_more"):
                return results

            payload["start_cursor"] = data.get("next_cursor")

    def update_page_properties(self, page_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        url = f"https://api.notion.com/v1/pages/{page_id}"
        response = self.session.patch(url, json={"properties": properties}, timeout=60)
        response.raise_for_status()
        return response.json()


def extract_property(prop: dict[str, Any] | None) -> Any:
    if not prop:
        return ""

    prop_type = prop.get("type")
    value = prop.get(prop_type)

    if prop_type == "title":
        return "".join(part.get("plain_text", "") for part in value or []).strip()
    if prop_type == "rich_text":
        return "".join(part.get("plain_text", "") for part in value or []).strip()
    if prop_type == "select":
        return value.get("name", "") if value else ""
    if prop_type == "multi_select":
        return ", ".join(item.get("name", "") for item in value or [])
    if prop_type in {"email", "phone_number", "url", "created_time"}:
        return value or ""
    if prop_type == "date":
        return (value or {}).get("start", "")
    if prop_type == "number":
        return value
    if prop_type == "checkbox":
        return bool(value)

    return value or ""


def page_to_flat_record(page: dict[str, Any]) -> dict[str, Any]:
    properties = page.get("properties", {})
    record = {
        "id": page.get("id", ""),
        "url": page.get("url", ""),
    }
    for name, prop in properties.items():
        record[name] = extract_property(prop)
    return record


def notion_update_property(field: str, value: str) -> dict[str, Any]:
    if field in {"Estado Cliente", "Resultado llamada", "Prioridad follow-up", "Siguiente acción"}:
        return {field: {"select": {"name": value}}}
    if field in {"Notas / Plan de pago", "Notas llamada"}:
        return {field: {"rich_text": [{"text": {"content": value}}]}}
    if field == "Fecha próximo contacto":
        return {field: {"date": {"start": value}}}
    if field == "Cash collected":
        return {field: {"number": float(value.replace(",", "").replace("$", "").strip())}}
    if field == "Asistió llamada":
        normalized = value.strip().lower()
        return {field: {"checkbox": normalized in {"si", "sí", "true", "1", "yes"}}}
    raise ValueError(f"Field is not editable: {field}")
