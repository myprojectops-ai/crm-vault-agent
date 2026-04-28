from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any


CALLS_MARKER = "## Llamadas registradas"


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "sin-nombre"


def assign_slugs(records: list[dict[str, Any]]) -> dict[str, str]:
    seen: dict[str, int] = {}
    slugs: dict[str, str] = {}
    for record in records:
        page_id = str(record.get("id") or "")
        base = slugify(str(record.get("Nombre Prospecto") or page_id or "sin-nombre"))
        count = seen.get(base, 0)
        seen[base] = count + 1
        slugs[page_id] = base if count == 0 else f"{base}-{page_id[:8]}"
    return slugs


def format_value(value: Any, money: bool = False) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, bool):
        return "Si" if value else "No"
    if isinstance(value, (int, float)):
        if money:
            return f"${value:,.0f}"
        return f"{value:,.0f}"
    if isinstance(value, str) and "T" in value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            return value
    return str(value)


def preserve_calls(existing_path: Path) -> str:
    if not existing_path.exists():
        return "_(Sin transcripciones importadas todavia.)_"
    text = existing_path.read_text(encoding="utf-8", errors="ignore")
    if CALLS_MARKER not in text:
        return "_(Sin transcripciones importadas todavia.)_"
    calls = text.split(CALLS_MARKER, 1)[1].strip()
    return calls or "_(Sin transcripciones importadas todavia.)_"


def render_prospect(record: dict[str, Any], slug: str, existing_path: Path) -> str:
    name = format_value(record.get("Nombre Prospecto"))
    calls = preserve_calls(existing_path)
    lines = [
        f"# {name}",
        "",
        f"Registro en [[crm-acelera]]. Pagina en Notion: {format_value(record.get('url'))}",
        "",
        "## Key Takeaways",
        "",
        f"- **Estado**: {format_value(record.get('Estado Cliente'))} · **Prioridad follow-up**: {format_value(record.get('Prioridad follow-up'))} · **Resultado llamada**: {format_value(record.get('Resultado llamada'))}",
        f"- **Siguiente accion**: {format_value(record.get('Siguiente acción'))}",
        f"- **Cash collected**: {format_value(record.get('Cash collected'), money=True)} · **Calificado**: {format_value(record.get('Calificado'), money=True)}",
        "",
        "## Contacto",
        "",
        "| Campo | Valor |",
        "|---|---|",
        f"| Correo electronico | {format_value(record.get('Correo electrónico'))} |",
        f"| Telefono | {format_value(record.get('Teléfono'))} |",
        f"| LinkedIn | {format_value(record.get('LinkedIn'))} |",
        "",
        "## Pipeline",
        "",
        "| Campo | Valor |",
        "|---|---|",
        f"| Estado Cliente | {format_value(record.get('Estado Cliente'))} |",
        f"| Resultado llamada | {format_value(record.get('Resultado llamada'))} |",
        f"| Prioridad follow-up | {format_value(record.get('Prioridad follow-up'))} |",
        f"| Siguiente accion | {format_value(record.get('Siguiente acción'))} |",
        f"| Asistio llamada | {format_value(record.get('Asistió llamada'))} |",
        "",
        "## Fechas",
        "",
        "| Campo | Valor |",
        "|---|---|",
        f"| Fecha Agregado | {format_value(record.get('Fecha Agregado'))} |",
        f"| Fecha llamada | {format_value(record.get('Fecha llamada'))} |",
        f"| Fecha Ultima Llamada | {format_value(record.get('Fecha Ultima Llamada'))} |",
        f"| Fecha proximo contacto | {format_value(record.get('Fecha próximo contacto'))} |",
        "",
        "## Metricas",
        "",
        "| Campo | Valor |",
        "|---|---|",
        f"| Cash collected | {format_value(record.get('Cash collected'), money=True)} |",
        f"| Calificado | {format_value(record.get('Calificado'), money=True)} |",
        "",
        "## Notas",
        "",
        f"**Notas / Plan de pago**: {format_value(record.get('Notas / Plan de pago'))}",
        "",
        f"**Notas llamada** (columna): {format_value(record.get('Notas llamada'))}",
        "",
        "## Enlaces",
        "",
        f"- Grabacion: {format_value(record.get('Link Grabacion'))}",
        f"- Carpeta Drive: {format_value(record.get('📁 Link Carpeta Drive'))}",
        f"- Pagina Notion: {format_value(record.get('url'))}",
        "",
        CALLS_MARKER,
        "",
        calls,
        "",
    ]
    return "\n".join(lines)


def render_prospect_index(records: list[dict[str, Any]], slugs: dict[str, str]) -> str:
    sorted_records = sorted(records, key=lambda item: str(item.get("Nombre Prospecto") or "").lower())
    closed = [r for r in sorted_records if r.get("Estado Cliente") == "Cliente Cerrado"]
    explicit = [r for r in sorted_records if r.get("Estado Cliente") == "Prospecto"]
    unset = [r for r in sorted_records if not r.get("Estado Cliente")]
    lines = [
        "# Prospectos (CRM - Acelera)",
        "",
        "Un articulo por registro de la base [[crm-acelera]]. Incluye prospectos y clientes cerrados.",
        "",
        f"- **Total registros**: {len(sorted_records)}",
        f"- **Cliente Cerrado**: {len(closed)}",
        f"- **Prospecto** (estado explicito): {len(explicit)}",
        f"- **Sin estado asignado**: {len(unset)}",
        "",
        "## Listado completo (orden alfabetico)",
        "",
        "| Prospecto | Estado | Resultado llamada | Prioridad | Fecha llamada | Cash collected |",
        "|---|---|---|---|---|---|",
    ]
    for record in sorted_records:
        slug = slugs[str(record.get("id") or "")]
        name = format_value(record.get("Nombre Prospecto"))
        lines.append(
            f"| [[{slug}|{name}]] | {format_value(record.get('Estado Cliente'))} | "
            f"{format_value(record.get('Resultado llamada'))} | {format_value(record.get('Prioridad follow-up'))} | "
            f"{format_value(record.get('Fecha llamada'))} | {format_value(record.get('Cash collected'), money=True)} |"
        )

    lines.extend(["", "## Por estado", ""])
    for title, group in [
        ("Clientes cerrados", closed),
        ("Prospectos activos", explicit),
        ("Sin estado asignado", unset),
    ]:
        lines.extend([f"### {title} ({len(group)})", ""])
        if not group:
            lines.extend(["_(Sin registros.)_", ""])
            continue
        for record in group:
            slug = slugs[str(record.get("id") or "")]
            name = format_value(record.get("Nombre Prospecto"))
            lines.append(
                f"- [[{slug}|{name}]] · {format_value(record.get('Resultado llamada'))} · llamada {format_value(record.get('Fecha llamada'))}"
            )
        lines.append("")
    return "\n".join(lines)


def render_closed_clients(records: list[dict[str, Any]], slugs: dict[str, str]) -> str:
    closed = sorted(
        [record for record in records if record.get("Estado Cliente") == "Cliente Cerrado"],
        key=lambda item: str(item.get("Fecha llamada") or ""),
        reverse=True,
    )
    total_cash = sum(
        record.get("Cash collected") or 0
        for record in closed
        if isinstance(record.get("Cash collected"), (int, float))
    )
    lines = [
        "# Clientes cerrados",
        "",
        "Vista derivada de [[crm-acelera]] filtrada por `Estado Cliente = Cliente Cerrado`.",
        "",
        "## Key Takeaways",
        "",
        "- Vista derivada, no DB nueva: comparte el mismo data source de [[crm-acelera]].",
        "- Criterio de inclusion: `Estado Cliente = Cliente Cerrado`.",
        "- Util para resultados: cash collected, fecha de cierre, grabacion y carpeta Drive.",
        "",
        "## Clientes cerrados actuales",
        "",
        f"Total: **{len(closed)}** registros · Cash collected agregado: **{format_value(total_cash, money=True)}**",
        "",
        "| Cliente | Cash collected | Fecha llamada |",
        "|---|---|---|",
    ]
    for record in closed:
        slug = slugs[str(record.get("id") or "")]
        name = format_value(record.get("Nombre Prospecto"))
        lines.append(
            f"| [[prospectos/{slug}|{name}]] | {format_value(record.get('Cash collected'), money=True)} | {format_value(record.get('Fecha llamada'))} |"
        )
    lines.extend(
        [
            "",
            "_Ordenado por `Fecha llamada` descendente. Actualizado automaticamente por el agente de sincronizacion._",
            "",
            "## Relaciones",
            "",
            "- Source: [[crm-acelera]] - base real de los datos.",
            "- Detalle por registro: [[prospectos/_index|prospectos/]] - un articulo por persona.",
        ]
    )
    return "\n".join(lines)
