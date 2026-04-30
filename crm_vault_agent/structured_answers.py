from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import Settings


BOGOTA = ZoneInfo("America/Bogota")


def answer_structured_question(question: str, settings: Settings) -> str | None:
    normalized = normalize(question)
    if "llamada" in normalized and any(word in normalized for word in ["ultima", "ultimas", "reciente", "recientes"]):
        limit = extract_limit(normalized, default=5)
        return latest_calls(settings, limit)
    return None


def latest_calls(settings: Settings, limit: int = 5) -> str:
    records = load_latest_records(settings)
    rows = [
        record
        for record in records
        if record.get("Fecha Ultima Llamada") or record.get("Fecha llamada")
    ]
    rows.sort(
        key=lambda record: parse_date(record.get("Fecha Ultima Llamada") or record.get("Fecha llamada")),
        reverse=True,
    )

    if not rows:
        return "No encontre llamadas registradas en el ultimo snapshot del CRM."

    lines = [f"Tus ultimas {limit} llamadas registradas en el CRM son:"]
    for idx, record in enumerate(rows[:limit], start=1):
        date_value = record.get("Fecha Ultima Llamada") or record.get("Fecha llamada")
        name = record.get("Nombre Prospecto") or "(sin nombre)"
        result = record.get("Resultado llamada") or "sin resultado"
        status = record.get("Estado Cliente") or "sin estado"
        recording = record.get("Link Grabacion") or record.get("Link Grabación") or ""
        line = f"{idx}. {name} - {format_date(date_value)} - {result} - {status}"
        if recording:
            line += f"\n   Grabacion: {recording}"
        lines.append(line)
    return "\n".join(lines)


def load_latest_records(settings: Settings) -> list[dict]:
    path = settings.raw_dir / "_latest_crm_query.json"
    if not path.exists():
        raise FileNotFoundError("No existe raw/_latest_crm_query.json. Ejecuta /sync primero.")
    return json.loads(path.read_text(encoding="utf-8"))


def extract_limit(text: str, default: int = 5) -> int:
    match = re.search(r"\b(\d{1,2})\b", text)
    if not match:
        return default
    return max(1, min(int(match.group(1)), 20))


def parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=BOGOTA)
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        parsed = datetime.fromisoformat(f"{text}T00:00:00")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BOGOTA)
    return parsed.astimezone(BOGOTA)


def format_date(value: str | None) -> str:
    parsed = parse_date(value)
    if "T" in str(value):
        return parsed.strftime("%Y-%m-%d %H:%M")
    return parsed.strftime("%Y-%m-%d")


def normalize(text: str) -> str:
    replacements = str.maketrans("áéíóúüñ", "aeiouun")
    return text.lower().translate(replacements)
