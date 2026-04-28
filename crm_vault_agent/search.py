from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SearchHit:
    path: Path
    score: int
    title: str
    snippet: str


class VaultSearch:
    def __init__(self, wiki_dir: Path) -> None:
        self.wiki_dir = wiki_dir

    def search(self, query: str, limit: int = 6) -> list[SearchHit]:
        terms = tokenize(query)
        if not terms:
            return []

        hits: list[SearchHit] = []
        for path in self.wiki_dir.rglob("*.md"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            lower = text.lower()
            score = sum(lower.count(term) for term in terms)
            if score <= 0:
                continue
            hits.append(
                SearchHit(
                    path=path,
                    score=score,
                    title=first_heading(text) or path.stem,
                    snippet=best_snippet(text, terms),
                )
            )

        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:limit]

    def context(self, query: str, limit: int = 5, max_chars: int = 12000) -> str:
        chunks: list[str] = []
        total = 0
        for hit in self.search(query, limit=limit):
            text = hit.path.read_text(encoding="utf-8", errors="ignore")
            rel = hit.path.relative_to(self.wiki_dir)
            chunk = f"Fuente: {rel}\n{text[:3000]}"
            if total + len(chunk) > max_chars:
                break
            chunks.append(chunk)
            total += len(chunk)
        return "\n\n---\n\n".join(chunks)


def tokenize(query: str) -> list[str]:
    return [term for term in re.findall(r"[\wáéíóúñü]+", query.lower()) if len(term) > 2]


def first_heading(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def best_snippet(text: str, terms: list[str], width: int = 650) -> str:
    lower = text.lower()
    positions = [lower.find(term) for term in terms if lower.find(term) >= 0]
    start = max(min(positions) - 150, 0) if positions else 0
    return re.sub(r"\s+", " ", text[start : start + width]).strip()
