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
    if any(word in normalized for word in ["dinero", "pago", "pagado", "cash", "collected"]) and any(
        word in normalized for word in ["cliente", "clientes", "mas", "top", "mayor"]
    ):
        limit = extract_limit(normalized, default=5)
        return top_paid_clients(settings, limit)
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


def top_paid_clients(settings: Settings, limit: int = 5) -> str:
    records = load_latest_records(settings)
    rows = [
        record
        for record in records
        if record.get("Estado Cliente") == "Cliente Cerrado"
        and isinstance(record.get("Cash collected"), (int, float))
        and record.get("Cash collected")
    ]
    rows.sort(key=lambda record: record.get("Cash collected") or 0, reverse=True)

    if not rows:
        return "No encontre clientes cerrados con `Cash collected` registrado."

    lines = [f"Top {min(limit, len(rows))} clientes por Cash collected:"]
    for idx, record in enumerate(rows[:limit], start=1):
        name = record.get("Nombre Prospecto") or "(sin nombre)"
        cash = record.get("Cash collected") or 0
        date_value = record.get("Fecha llamada") or "-"
        result = record.get("Resultado llamada") or "sin resultado"
        lines.append(f"{idx}. {name} - {format_money(cash)} - {date_value} - {result}")

    if len(rows) < limit:
        lines.append(f"Solo hay {len(rows)} clientes cerrados con Cash collected numerico.")
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


def format_money(value: int | float) -> str:
    return f"${value:,.0f}"


def normalize(text: str) -> str:
    replacements = str.maketrans("áéíóúüñ", "aeiouun")
    return text.lower().translate(replacements)
