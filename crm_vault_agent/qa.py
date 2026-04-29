from __future__ import annotations

from openai import OpenAI, OpenAIError

from .config import Settings
from .search import VaultSearch


def answer_question(question: str, settings: Settings) -> str:
    search = VaultSearch(settings.wiki_dir)
    context = search.context(question)
    if not context:
        return "No encontre informacion relacionada en el vault."

    if not settings.openai_api_key:
        return fallback_answer(question, settings, "OpenAI no esta configurado.")

    client = OpenAI(api_key=settings.openai_api_key)
    try:
        response = client.responses.create(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Responde en espanol de forma breve, clara y accionable. "
                        "Usa solo la informacion del contexto del vault. "
                        "Si falta informacion, dilo claramente."
                    ),
                },
                {"role": "user", "content": f"Pregunta: {question}\n\nContexto:\n{context}"},
            ],
        )
        return response.output_text.strip()
    except OpenAIError as exc:
        return fallback_answer(question, settings, f"OpenAI fallo: {short_error(exc)}")


def fallback_answer(question: str, settings: Settings, reason: str) -> str:
    search = VaultSearch(settings.wiki_dir)
    hits = search.search(question, limit=4)
    lines = [f"{reason} Te dejo los resultados mas relevantes del vault:"]
    for hit in hits:
        rel = hit.path.relative_to(settings.vault_root)
        lines.append(f"- {hit.title} ({rel}): {hit.snippet[:300]}")
    return "\n".join(lines)


def short_error(exc: Exception) -> str:
    message = str(exc)
    if "insufficient_quota" in message:
        return "cuota insuficiente o billing pendiente"
    return message[:160]
