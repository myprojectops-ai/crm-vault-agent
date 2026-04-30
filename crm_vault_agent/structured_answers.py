from __future__ import annotations

import re
from datetime import datetime

from .config import Settings
from .crm_data import BOGOTA, load_records, normalize
from .crm_tools import (
    calls_in_period,
    calls_on_date,
    closed_clients,
    counts_summary,
    followups,
    latest_calls,
    list_by_result,
    list_by_status,
    month_range,
    paid_clients,
    prospect_detail,
    top_cash_clients,
    top_qualified,
)


def answer_structured_question(question: str, settings: Settings) -> str | None:
    text = normalize(question)
    records = load_records(settings)
    requested_date = extract_requested_date(text)
    period = extract_period(text)
    limit = extract_limit(text, default=5)

    if is_help_question(text):
        return help_text()
    if "llamada" in text and requested_date:
        return calls_on_date(records, requested_date)
    if "llamada" in text and period:
        return calls_in_period(records, period)
    if "llamada" in text and any(word in text for word in ["ultima", "ultimas", "reciente", "recientes"]):
        return latest_calls(records, limit)
    if wants_paid_clients_in_period(text) and period:
        return paid_clients(records, period=period, limit=max(limit, 20))
    if wants_cash_ranking(text):
        return top_cash_clients(records, limit)
    if wants_qualified_ranking(text):
        return top_qualified(records, limit=max(limit, 10))
    if wants_closed_clients(text):
        return closed_clients(records, period=period, limit=max(limit, 10) if period else limit)
    if wants_followups(text):
        return followups(records, overdue=("vencid" in text or "hoy" in text), limit=max(limit, 10))
    if wants_counts(text):
        return counts_summary(records)

    result = detect_result(text)
    if result:
        return list_by_result(records, result, limit=max(limit, 10))

    status = detect_status(text)
    if status:
        return list_by_status(records, status, limit=max(limit, 10))

    prospect_query = extract_prospect_query(text)
    if prospect_query:
        return prospect_detail(records, prospect_query)

    return None


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

    date_match = re.search(r"\b(\d{1,2})\s+de\s+([a-z]+)\s+(?:de|del)?\s*(20\d{2})\b", text)
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
    month_match = re.search(
        r"\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(?:de|del)?\s*(20\d{2})\b",
        text,
    )
    if month_match:
        month_name, year = month_match.groups()
        month = month_number(month_name)
        if month:
            return month_range(int(year), month)
    return None


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


def wants_cash_ranking(text: str) -> bool:
    return any(word in text for word in ["dinero", "pago", "pagado", "cash", "collected"]) and any(
        word in text for word in ["cliente", "clientes", "mas", "top", "mayor"]
    )


def wants_paid_clients_in_period(text: str) -> bool:
    return any(word in text for word in ["pagado", "pago", "pagaron", "dinero", "cash"]) and any(
        word in text for word in ["este mes", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    )


def wants_qualified_ranking(text: str) -> bool:
    return "calificado" in text and any(word in text for word in ["top", "mas", "mayor", "prospecto", "prospectos"])


def wants_closed_clients(text: str) -> bool:
    return "cliente cerrado" in text or "clientes cerrados" in text or "cerrados" in text


def wants_followups(text: str) -> bool:
    return "follow" in text or "seguimiento" in text or "proximo contacto" in text


def wants_counts(text: str) -> bool:
    return any(word in text for word in ["cuantos", "cuantas", "conteo", "resumen", "metricas"])


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
        r"(?:dame|muestrame|busca|buscar|quien es|detalle de|info de|informacion de)\s+(.+)",
        r"(?:cliente|prospecto)\s+(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            query = match.group(1).strip(" ?.")
            if query and not any(word in query for word in ["cerrado", "cerrados", "llamada", "llamadas", "dinero"]):
                return query
    return None


def is_help_question(text: str) -> bool:
    return text in {"ayuda", "help", "/ayuda"} or "que puedo preguntar" in text


def help_text() -> str:
    return (
        "Puedes preguntarme cosas como:\n"
        "- ultimas 5 llamadas realizadas\n"
        "- llamadas realizadas el 21 de abril del 2026\n"
        "- llamadas de abril 2026\n"
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
