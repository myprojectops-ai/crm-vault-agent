from __future__ import annotations

from openai import OpenAI

from .config import Settings
from .search import VaultSearch


def answer_question(question: str, settings: Settings) -> str:
    search = VaultSearch(settings.wiki_dir)
    context = search.context(question)
    if not context:
        return "No encontre informacion relacionada en el vault."

    if not settings.openai_api_key:
        hits = search.search(question, limit=4)
        lines = ["Encontre estas notas relacionadas:"]
        for hit in hits:
            rel = hit.path.relative_to(settings.vault_root)
            lines.append(f"- {hit.title} ({rel}): {hit.snippet[:280]}")
        return "\n".join(lines)

    client = OpenAI(api_key=settings.openai_api_key)
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
