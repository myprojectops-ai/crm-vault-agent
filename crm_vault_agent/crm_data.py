from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .config import Settings


BOGOTA = ZoneInfo("America/Bogota")


FIELD_ALIASES = {
    "name": ["Nombre Prospecto"],
    "email": ["Correo electr\u00f3nico", "Correo electronico"],
    "phone": ["Tel\u00e9fono", "Telefono"],
    "linkedin": ["LinkedIn"],
    "status": ["Estado Cliente"],
    "result": ["Resultado llamada"],
    "priority": ["Prioridad follow-up"],
    "next_action": ["Siguiente acci\u00f3n", "Siguiente accion"],
    "attended": ["Asisti\u00f3 llamada", "Asistio llamada"],
    "created_at": ["Fecha Agregado"],
    "call_date": ["Fecha llamada"],
    "last_call_date": ["Fecha Ultima Llamada", "Fecha \u00daltima Llamada"],
    "next_contact_date": ["Fecha pr\u00f3ximo contacto", "Fecha proximo contacto"],
    "cash": ["Cash collected"],
    "qualified": ["Calificado"],
    "payment_notes": ["Notas / Plan de pago"],
    "call_notes": ["Notas llamada"],
    "recording": ["Link Grabacion", "Link Grabaci\u00f3n"],
    "drive_folder": ["\U0001f4c1 Link Carpeta Drive"],
    "url": ["url"],
    "id": ["id"],
}


@dataclass(frozen=True)
class CRMRecord:
    raw: dict[str, Any]

    @property
    def id(self) -> str:
        return str(get_first(self.raw, "id") or "")

    @property
    def name(self) -> str:
        return str(get_first(self.raw, "name") or "(sin nombre)")

    @property
    def status(self) -> str:
        return str(get_first(self.raw, "status") or "")

    @property
    def result(self) -> str:
        return str(get_first(self.raw, "result") or "")

    @property
    def priority(self) -> str:
        return str(get_first(self.raw, "priority") or "")

    @property
    def next_action(self) -> str:
        return str(get_first(self.raw, "next_action") or "")

    @property
    def call_date(self) -> str:
        return str(get_first(self.raw, "call_date") or "")

    @property
    def last_call_date(self) -> str:
        return str(get_first(self.raw, "last_call_date") or "")

    @property
    def effective_call_date(self) -> str:
        return self.last_call_date or self.call_date

    @property
    def next_contact_date(self) -> str:
        return str(get_first(self.raw, "next_contact_date") or "")

    @property
    def cash(self) -> float:
        return number(get_first(self.raw, "cash"))

    @property
    def qualified(self) -> float:
        return number(get_first(self.raw, "qualified"))

    @property
    def recording(self) -> str:
        return str(get_first(self.raw, "recording") or "")

    @property
    def url(self) -> str:
        return str(get_first(self.raw, "url") or "")

    def value(self, canonical: str) -> Any:
        return get_first(self.raw, canonical)


def load_records(settings: Settings) -> list[CRMRecord]:
    path = settings.raw_dir / "_latest_crm_query.json"
    if not path.exists():
        raise FileNotFoundError("No existe raw/_latest_crm_query.json. Ejecuta /sync primero.")
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [CRMRecord(row) for row in rows]


def get_first(row: dict[str, Any], canonical: str) -> Any:
    for key in FIELD_ALIASES[canonical]:
        if key in row:
            return row[key]
    return ""


def number(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if value in {None, ""}:
        return 0.0
    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except ValueError:
        return 0.0


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()


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


def display(value: Any, empty: str = "-") -> str:
    if value in {None, ""}:
        return empty
    if isinstance(value, bool):
        return "Si" if value else "No"
    return str(value)
