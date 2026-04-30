from __future__ import annotations

import json
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import Settings


BOGOTA = ZoneInfo("America/Bogota")


def answer_structured_question(question: str, settings: Settings) -> str | None:
    text = normalize(question)
    records = load_latest_records(settings)

    requested_date = extract_requested_date(text)
    period = extract_period(text)
    limit = extract_limit(text, default=5)

    if is_help_question(text):
        return help_text()

    if is_latest_calls_question(text):
        return latest_calls(records, limit)

    if "llamada" in text and requested_date:
        return calls_on_date(records, requested_date)

    if "llamada" in text and period:
        return calls_in_period(records, period)

    if is_top_cash_question(text):
        return top_numeric(records, "Cash collected", "Cliente Cerrado", limit, "clientes por Cash collected")

    if is_top_qualified_question(text):
        return top_numeric(records, "Calificado", None, limit, "prospectos por Calificado")

    if is_closed_clients_question(text):
        return closed_clients(records, period=period, limit=limit)

    if is_followup_question(text):
        return followups(records, overdue=("vencid" in text or "hoy" in text), limit=max(limit, 10))

    if is_count_question(text):
        return counts_summary(records)

    if is_result_question(text):
        result = detect_result(text)
        if result:
            return list_by_field(records, "Resultado llamada", result, limit=max(limit, 10))

    if is_status_question(text):
        status = detect_status(text)
        if status:
            return list_by_field(records, "Estado Cliente", status, limit=max(limit, 10))

    prospect_query = extract_prospect_query(text)
    if prospect_query:
        return prospect_detail(records, prospect_query)

    return None


def latest_calls(records: list[dict], limit: int = 5) -> str:
    rows = sorted(
        [record for record in records if call_date(record)],
        key=lambda record: parse_date(call_date(record)),
        reverse=True,
    )
    return format_call_rows(rows[:limit], f"Tus ultimas {limit} llamadas registradas en el CRM son:")


def calls_on_date(records: list[dict], requested_date: str) -> str:
    rows = [
        record
        for record in records
        if call_date(record) and parse_date(call_date(record)).date().isoformat() == requested_date
    ]
    rows.sort(key=lambda record: parse_date(call_date(record)))
    return format_call_rows(rows, f"Llamadas registradas el {requested_date}: {len(rows)}")


def calls_in_period(records: list[dict], period: tuple[str, str]) -> str:
    start, end = period
    rows = []
    for record in records:
        value = call_date(record)
        if not value:
            continue
        day = parse_date(value).date().isoformat()
        if start <= day <= end:
            rows.append(record)
    rows.sort(key=lambda record: parse_date(call_date(record)))
    return format_call_rows(rows, f"Llamadas registradas entre {start} y {end}: {len(rows)}")


def top_numeric(records: list[dict], field: str, status: str | None, limit: int, label: str) -> str:
    rows = [
        record
        for record in records
        if isinstance(record.get(field), (int, float))
        and record.get(field)
        and (status is None or record.get("Estado Cliente") == status)
    ]
    rows.sort(key=lambda record: record.get(field) or 0, reverse=True)
    if not rows:
        return f"No encontre registros con `{field}` numerico."

    lines = [f"Top {min(limit, len(rows))} {label}:"]
    for idx, record in enumerate(rows[:limit], start=1):
        lines.append(
            f"{idx}. {name(record)} - {format_money(record.get(field) or 0)} - "
            f"{format_value(record.get('Fecha llamada'))} - {format_value(record.get('Resultado llamada'))}"
        )
    return "\n".join(lines)


def closed_clients(records: list[dict], period: tuple[str, str] | None, limit: int) -> str:
    rows = [record for record in records if record.get("Estado Cliente") == "Cliente Cerrado"]
    if period:
        start, end = period
        rows = [
            record
            for record in rows
            if record.get("Fecha llamada") and start <= parse_date(record.get("Fecha llamada")).date().isoformat() <= end
        ]
    rows.sort(key=lambda record: str(record.get("Fecha llamada") or ""), reverse=True)
    total = sum(record.get("Cash collected") or 0 for record in rows if isinstance(record.get("Cash collected"), (int, float)))
    title = f"Clientes cerrados: {len(rows)} · Cash collected: {format_money(total)}"
    if period:
        title += f" · periodo {period[0]} a {period[1]}"
    lines = [title]
    for idx, record in enumerate(rows[:limit], start=1):
        lines.append(
            f"{idx}. {name(record)} - {format_money(record.get('Cash collected') or 0)} - "
            f"{format_value(record.get('Fecha llamada'))} - {format_value(record.get('Resultado llamada'))}"
        )
    if len(rows) > limit:
        lines.append(f"... y {len(rows) - limit} mas.")
    return "\n".join(lines)


def followups(records: list[dict], overdue: bool, limit: int) -> str:
    today = datetime.now(BOGOTA).date().isoformat()
    rows = [record for record in records if record.get("Fecha próximo contacto")]
    if overdue:
        rows = [record for record in rows if str(record.get("Fecha próximo contacto")) <= today]
        title = f"Follow-ups vencidos o para hoy ({today}): {len(rows)}"
    else:
        rows = [record for record in rows if str(record.get("Fecha próximo contacto")) > today]
        title = f"Proximos follow-ups: {len(rows)}"
    rows.sort(key=lambda record: str(record.get("Fecha próximo contacto") or ""))
    lines = [title]
    for idx, record in enumerate(rows[:limit], start=1):
        lines.append(
            f"{idx}. {name(record)} - {record.get('Fecha próximo contacto')} - "
            f"{format_value(record.get('Prioridad follow-up'))} - {format_value(record.get('Siguiente acción'))}"
        )
    if len(rows) > limit:
        lines.append(f"... y {len(rows) - limit} mas.")
    return "\n".join(lines)


def counts_summary(records: list[dict]) -> str:
    by_status = count_by(records, "Estado Cliente", empty="Sin estado")
    by_result = count_by(records, "Resultado llamada", empty="Sin resultado")
    total_cash = sum(record.get("Cash collected") or 0 for record in records if isinstance(record.get("Cash collected"), (int, float)))
    lines = [
        f"Resumen CRM: {len(records)} registros",
        f"Cash collected total registrado: {format_money(total_cash)}",
        "",
        "Por Estado Cliente:",
    ]
    lines.extend(f"- {key}: {value}" for key, value in by_status)
    lines.append("")
    lines.append("Por Resultado llamada:")
    lines.extend(f"- {key}: {value}" for key, value in by_result)
    return "\n".join(lines)


def list_by_field(records: list[dict], field: str, value: str, limit: int) -> str:
    rows = [record for record in records if record.get(field) == value]
    rows.sort(key=lambda record: str(record.get("Fecha llamada") or record.get("Fecha Agregado") or ""), reverse=True)
    lines = [f"Registros con {field} = {value}: {len(rows)}"]
    for idx, record in enumerate(rows[:limit], start=1):
        lines.append(
            f"{idx}. {name(record)} - llamada {format_value(record.get('Fecha llamada'))} - "
            f"{format_value(record.get('Estado Cliente'))} - {format_money(record.get('Cash collected') or 0)}"
        )
    if len(rows) > limit:
        lines.append(f"... y {len(rows) - limit} mas.")
    return "\n".join(lines)


def prospect_detail(records: list[dict], query: str) -> str:
    matches = [record for record in records if query in normalize(name(record))]
    if not matches:
        return f"No encontre prospectos que coincidan con `{query}`."
    if len(matches) > 1:
        preview = ", ".join(name(record) for record in matches[:8])
        return f"Hay {len(matches)} coincidencias. Se mas especifico: {preview}"
    record = matches[0]
    lines = [
        f"{name(record)}",
        f"- Estado: {format_value(record.get('Estado Cliente'))}",
        f"- Resultado llamada: {format_value(record.get('Resultado llamada'))}",
        f"- Fecha llamada: {format_value(record.get('Fecha llamada'))}",
        f"- Fecha ultimo contacto: {format_value(record.get('Fecha Ultima Llamada'))}",
        f"- Proximo contacto: {format_value(record.get('Fecha próximo contacto'))}",
        f"- Prioridad: {format_value(record.get('Prioridad follow-up'))}",
        f"- Siguiente accion: {format_value(record.get('Siguiente acción'))}",
        f"- Cash collected: {format_money(record.get('Cash collected') or 0)}",
        f"- Calificado: {format_money(record.get('Calificado') or 0)}",
        f"- Telefono: {format_value(record.get('Teléfono'))}",
        f"- Email: {format_value(record.get('Correo electrónico'))}",
        f"- Grabacion: {format_value(record.get('Link Grabacion'))}",
        f"- Notas / Plan de pago: {format_value(record.get('Notas / Plan de pago'))}",
        f"- Notas llamada: {format_value(record.get('Notas llamada'))}",
    ]
    return "\n".join(lines)


def format_call_rows(rows: list[dict], title: str) -> str:
    if not rows:
        return title + "\nNo encontre llamadas registradas para ese criterio."
    lines = [title]
    for idx, record in enumerate(rows, start=1):
        value = call_date(record)
        line = (
            f"{idx}. {format_date(value)} - {name(record)} - "
            f"{display_result(record)} - {display_status(record)}"
        )
        recording = record.get("Link Grabacion") or record.get("Link Grabación") or ""
        if recording:
            line += f"\n   Grabacion: {recording}"
        lines.append(line)
    return "\n".join(lines)


def call_date(record: dict) -> str | None:
    return record.get("Fecha Ultima Llamada") or record.get("Fecha llamada")


def load_latest_records(settings: Settings) -> list[dict]:
    path = settings.raw_dir / "_latest_crm_query.json"
    if not path.exists():
        raise FileNotFoundError("No existe raw/_latest_crm_query.json. Ejecuta /sync primero.")
    return json.loads(path.read_text(encoding="utf-8"))


def count_by(records: list[dict], field: str, empty: str) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for record in records:
        key = record.get(field) or empty
        counts[str(key)] = counts.get(str(key), 0) + 1
    return sorted(counts.items(), key=lambda item: item[1], reverse=True)


def extract_limit(text: str, default: int = 5) -> int:
    match = re.search(r"\b(\d{1,2})\b", text)
    if not match:
        return default
    return max(1, min(int(match.group(1)), 50))


def extract_requested_date(text: str) -> str | None:
    iso_match = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", text)
    if iso_match:
        year, month, day = iso_match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    date_match = re.search(
        r"\b(\d{1,2})\s+de\s+([a-z]+)\s+(?:de|del)?\s*(20\d{2})\b",
        text,
    )
    if not date_match:
        return None
    day, month_name, year = date_match.groups()
    month = month_number(month_name)
    if not month:
        return None
    return f"{int(year):04d}-{month:02d}-{int(day):02d}"


def extract_period(text: str) -> tuple[str, str] | None:
    if "este mes" in text:
        now = datetime.now(BOGOTA).date()
        return month_range(now.year, now.month)

    month_match = re.search(r"\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(?:de|del)?\s*(20\d{2})\b", text)
    if month_match:
        month_name, year = month_match.groups()
        month = month_number(month_name)
        if month:
            return month_range(int(year), month)

    year_match = re.search(r"\b(20\d{2})\b", text)
    if year_match and any(word in text for word in ["ano", "año", "year"]):
        year = int(year_match.group(1))
        return f"{year}-01-01", f"{year}-12-31"

    return None


def month_range(year: int, month: int) -> tuple[str, str]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1)
        end = date.fromordinal(end.toordinal() - 1)
    return start.isoformat(), end.isoformat()


def month_number(month_name: str) -> int | None:
    return {
        "enero": 1,
        "febrero": 2,
        "marzo": 3,
        "abril": 4,
        "mayo": 5,
        "junio": 6,
        "julio": 7,
        "agosto": 8,
        "septiembre": 9,
        "setiembre": 9,
        "octubre": 10,
        "noviembre": 11,
        "diciembre": 12,
    }.get(month_name)


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


def format_value(value) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, bool):
        return "Si" if value else "No"
    return str(value)


def display_result(record: dict) -> str:
    return str(record.get("Resultado llamada") or "sin resultado")


def display_status(record: dict) -> str:
    return str(record.get("Estado Cliente") or "sin estado")


def name(record: dict) -> str:
    return str(record.get("Nombre Prospecto") or "(sin nombre)")


def normalize(text: str) -> str:
    text = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    return text.lower()


def is_help_question(text: str) -> bool:
    return text in {"ayuda", "help", "/ayuda"} or "que puedo preguntar" in text


def is_latest_calls_question(text: str) -> bool:
    return "llamada" in text and any(word in text for word in ["ultima", "ultimas", "reciente", "recientes"])


def is_top_cash_question(text: str) -> bool:
    return any(word in text for word in ["dinero", "pago", "pagado", "cash", "collected"]) and any(
        word in text for word in ["cliente", "clientes", "mas", "top", "mayor"]
    )


def is_top_qualified_question(text: str) -> bool:
    return "calificado" in text and any(word in text for word in ["top", "mas", "mayor", "prospecto", "prospectos"])


def is_closed_clients_question(text: str) -> bool:
    return "cerrado" in text or "cerrados" in text or "clientes cerrados" in text


def is_followup_question(text: str) -> bool:
    return "follow" in text or "seguimiento" in text or "proximo contacto" in text or "próximo contacto" in text


def is_count_question(text: str) -> bool:
    return any(word in text for word in ["cuantos", "cuantas", "conteo", "resumen", "metricas", "métricas"])


def is_result_question(text: str) -> bool:
    return "resultado" in text or any(result in text for result in RESULT_MAP)


def is_status_question(text: str) -> bool:
    return "estado" in text or "prospecto" in text or "cliente cerrado" in text


def detect_result(text: str) -> str | None:
    for key, value in RESULT_MAP.items():
        if key in text:
            return value
    return None


def detect_status(text: str) -> str | None:
    if "cliente cerrado" in text or "cerrados" in text:
        return "Cliente Cerrado"
    if "prospecto" in text:
        return "Prospecto"
    return None


def extract_prospect_query(text: str) -> str | None:
    patterns = [
        r"(?:dame|muestrame|mu[eé]strame|busca|buscar|quien es|quién es|detalle de|info de|informacion de|información de)\s+(.+)",
        r"(?:cliente|prospecto)\s+(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            query = match.group(1).strip(" ?.")
            if query and not any(word in query for word in ["cerrado", "cerrados", "llamada", "llamadas", "dinero"]):
                return query
    return None


def help_text() -> str:
    return (
        "Puedes preguntarme cosas como:\n"
        "- ultimas 5 llamadas realizadas\n"
        "- llamadas realizadas el 21 de abril del 2026\n"
        "- clientes cerrados de abril 2026\n"
        "- cliente que mas dinero ha pagado\n"
        "- top prospectos por calificado\n"
        "- follow-ups vencidos\n"
        "- cuantos clientes cerrados tengo\n"
        "- prospectos con resultado No show\n"
        "- detalle de Paola Alvarez\n"
        "Para editar: /editar Nombre | Campo | Nuevo valor"
    )


RESULT_MAP = {
    "consiguiendo dinero": "Consiguiendo dinero",
    "seguimiento": "Seguimiento",
    "agendar": "Agendar",
    "reagendada": "Reagendada",
    "reagendadas": "Reagendada",
    "no contesto": "No contesto",
    "no contestó": "No contesto",
    "no dinero": "No dinero",
    "descartado": "Descartado",
    "descartados": "Descartado",
    "cerrada": "Cerrada",
    "cerradas": "Cerrada",
    "no show": "No show",
    "agendado": "Agendado",
    "perdida": "Perdida",
    "perdidas": "Perdida",
}
