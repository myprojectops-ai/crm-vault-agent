from __future__ import annotations

from datetime import date, datetime

from .crm_data import BOGOTA, CRMRecord, display, format_date, format_money, normalize, parse_date


def latest_calls(records: list[CRMRecord], limit: int = 5) -> str:
    rows = sorted(
        [record for record in records if record.effective_call_date],
        key=lambda record: parse_date(record.effective_call_date),
        reverse=True,
    )
    return format_call_rows(rows[:limit], f"Tus ultimas {limit} llamadas registradas en el CRM son:")


def calls_on_date(records: list[CRMRecord], requested_date: str) -> str:
    rows = [
        record
        for record in records
        if record.effective_call_date and parse_date(record.effective_call_date).date().isoformat() == requested_date
    ]
    rows.sort(key=lambda record: parse_date(record.effective_call_date))
    return format_call_rows(rows, f"Llamadas registradas el {requested_date}: {len(rows)}")


def calls_in_period(records: list[CRMRecord], period: tuple[str, str]) -> str:
    start, end = period
    rows = []
    for record in records:
        if not record.effective_call_date:
            continue
        day = parse_date(record.effective_call_date).date().isoformat()
        if start <= day <= end:
            rows.append(record)
    rows.sort(key=lambda record: parse_date(record.effective_call_date))
    return format_call_rows(rows, f"Llamadas registradas entre {start} y {end}: {len(rows)}")


def top_cash_clients(records: list[CRMRecord], limit: int = 5) -> str:
    rows = [record for record in records if record.status == "Cliente Cerrado" and record.cash > 0]
    rows.sort(key=lambda record: record.cash, reverse=True)
    return format_numeric_rows(rows, "Cash collected", "clientes por Cash collected", limit)


def paid_clients(records: list[CRMRecord], period: tuple[str, str] | None = None, limit: int = 20) -> str:
    rows = [record for record in records if record.status == "Cliente Cerrado" and record.cash > 0]
    if period:
        start, end = period
        rows = [
            record
            for record in rows
            if record.call_date and start <= parse_date(record.call_date).date().isoformat() <= end
        ]
    rows.sort(key=lambda record: record.call_date or "", reverse=True)
    total = sum(record.cash for record in rows)

    if period:
        title = f"Clientes con pago registrado entre {period[0]} y {period[1]}: {len(rows)} - Total: {format_money(total)}"
    else:
        title = f"Clientes con pago registrado: {len(rows)} - Total: {format_money(total)}"

    if not rows:
        return title + "\nNo encontre clientes cerrados con Cash collected en ese periodo."

    lines = [title]
    for idx, record in enumerate(rows[:limit], start=1):
        lines.append(
            f"{idx}. {record.name} - {format_money(record.cash)} - "
            f"{display(record.call_date)} - {display(record.result, 'sin resultado')}"
        )
    if len(rows) > limit:
        lines.append(f"... y {len(rows) - limit} mas.")
    lines.append("Nota: el periodo se calcula usando `Fecha llamada`; no hay una fecha separada de pago en el snapshot.")
    return "\n".join(lines)


def top_qualified(records: list[CRMRecord], limit: int = 10) -> str:
    rows = [record for record in records if record.qualified > 0]
    rows.sort(key=lambda record: record.qualified, reverse=True)
    return format_numeric_rows(rows, "Calificado", "prospectos por Calificado", limit)


def closed_clients(records: list[CRMRecord], period: tuple[str, str] | None, limit: int = 10) -> str:
    rows = [record for record in records if record.status == "Cliente Cerrado"]
    if period:
        start, end = period
        rows = [
            record
            for record in rows
            if record.call_date and start <= parse_date(record.call_date).date().isoformat() <= end
        ]
    rows.sort(key=lambda record: record.call_date or "", reverse=True)
    total = sum(record.cash for record in rows)
    title = f"Clientes cerrados: {len(rows)} - Cash collected: {format_money(total)}"
    if period:
        title += f" - periodo {period[0]} a {period[1]}"
    lines = [title]
    for idx, record in enumerate(rows[:limit], start=1):
        lines.append(
            f"{idx}. {record.name} - {format_money(record.cash)} - "
            f"{display(record.call_date)} - {display(record.result, 'sin resultado')}"
        )
    if len(rows) > limit:
        lines.append(f"... y {len(rows) - limit} mas.")
    return "\n".join(lines)


def followups(records: list[CRMRecord], overdue: bool, limit: int = 10) -> str:
    today = datetime.now(BOGOTA).date().isoformat()
    rows = [record for record in records if record.next_contact_date]
    if overdue:
        rows = [record for record in rows if record.next_contact_date <= today]
        title = f"Follow-ups vencidos o para hoy ({today}): {len(rows)}"
    else:
        rows = [record for record in rows if record.next_contact_date > today]
        title = f"Proximos follow-ups: {len(rows)}"
    rows.sort(key=lambda record: record.next_contact_date)
    lines = [title]
    for idx, record in enumerate(rows[:limit], start=1):
        lines.append(
            f"{idx}. {record.name} - {record.next_contact_date} - "
            f"{display(record.priority, 'sin prioridad')} - {display(record.next_action, 'sin accion')}"
        )
    if len(rows) > limit:
        lines.append(f"... y {len(rows) - limit} mas.")
    return "\n".join(lines)


def counts_summary(records: list[CRMRecord]) -> str:
    by_status = count_by(records, lambda record: record.status or "Sin estado")
    by_result = count_by(records, lambda record: record.result or "Sin resultado")
    total_cash = sum(record.cash for record in records)
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


def list_by_result(records: list[CRMRecord], result: str, limit: int = 10) -> str:
    rows = [record for record in records if record.result == result]
    rows.sort(key=lambda record: record.call_date or record.value("created_at") or "", reverse=True)
    return format_record_list(rows, f"Registros con Resultado llamada = {result}: {len(rows)}", limit)


def list_by_status(records: list[CRMRecord], status: str, limit: int = 10) -> str:
    rows = [record for record in records if record.status == status]
    rows.sort(key=lambda record: record.call_date or record.value("created_at") or "", reverse=True)
    return format_record_list(rows, f"Registros con Estado Cliente = {status}: {len(rows)}", limit)


def prospect_detail(records: list[CRMRecord], query: str) -> str:
    needle = normalize(query)
    matches = [record for record in records if needle in normalize(record.name)]
    if not matches:
        return f"No encontre prospectos que coincidan con `{query}`."
    if len(matches) > 1:
        preview = ", ".join(record.name for record in matches[:8])
        return f"Hay {len(matches)} coincidencias. Se mas especifico: {preview}"
    record = matches[0]
    return "\n".join(
        [
            record.name,
            f"- Estado: {display(record.status)}",
            f"- Resultado llamada: {display(record.result)}",
            f"- Fecha llamada: {display(record.call_date)}",
            f"- Fecha ultima llamada: {display(record.last_call_date)}",
            f"- Proximo contacto: {display(record.next_contact_date)}",
            f"- Prioridad: {display(record.priority)}",
            f"- Siguiente accion: {display(record.next_action)}",
            f"- Cash collected: {format_money(record.cash)}",
            f"- Calificado: {format_money(record.qualified)}",
            f"- Telefono: {display(record.value('phone'))}",
            f"- Email: {display(record.value('email'))}",
            f"- Grabacion: {display(record.recording)}",
            f"- Notas / Plan de pago: {display(record.value('payment_notes'))}",
            f"- Notas llamada: {display(record.value('call_notes'))}",
        ]
    )


def format_call_rows(rows: list[CRMRecord], title: str) -> str:
    if not rows:
        return title + "\nNo encontre llamadas registradas para ese criterio."
    lines = [title]
    visible = rows[:20]
    for idx, record in enumerate(visible, start=1):
        line = (
            f"{idx}. {format_date(record.effective_call_date)} - {record.name} - "
            f"{display(record.result, 'sin resultado')} - {display(record.status, 'sin estado')}"
        )
        if record.recording:
            line += f"\n   Grabacion: {record.recording}"
        lines.append(line)
    if len(rows) > len(visible):
        lines.append(f"... y {len(rows) - len(visible)} mas. Pide una fecha exacta o un limite menor para ver una lista mas corta.")
    return "\n".join(lines)


def format_numeric_rows(rows: list[CRMRecord], field: str, label: str, limit: int) -> str:
    if not rows:
        return f"No encontre registros con `{field}` numerico."
    lines = [f"Top {min(limit, len(rows))} {label}:"]
    for idx, record in enumerate(rows[:limit], start=1):
        amount = record.cash if field == "Cash collected" else record.qualified
        lines.append(
            f"{idx}. {record.name} - {format_money(amount)} - "
            f"{display(record.call_date)} - {display(record.result, 'sin resultado')}"
        )
    return "\n".join(lines)


def format_record_list(rows: list[CRMRecord], title: str, limit: int) -> str:
    lines = [title]
    for idx, record in enumerate(rows[:limit], start=1):
        lines.append(
            f"{idx}. {record.name} - llamada {display(record.call_date)} - "
            f"{display(record.status, 'sin estado')} - {format_money(record.cash)}"
        )
    if len(rows) > limit:
        lines.append(f"... y {len(rows) - limit} mas.")
    return "\n".join(lines)


def count_by(records: list[CRMRecord], key_fn) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for record in records:
        key = str(key_fn(record))
        counts[key] = counts.get(key, 0) + 1
    return sorted(counts.items(), key=lambda item: item[1], reverse=True)


def month_range(year: int, month: int) -> tuple[str, str]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        next_month = date(year, month + 1, 1)
        end = date.fromordinal(next_month.toordinal() - 1)
    return start.isoformat(), end.isoformat()
