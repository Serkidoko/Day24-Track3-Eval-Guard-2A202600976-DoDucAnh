from __future__ import annotations

"""Minimal Day 18 chunking helpers used by the Lab 24 harness.

The original Day 18 code is not present in this workspace, so this module
provides a small local implementation over the markdown corpus.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import DATA_DIR


@dataclass
class Chunk:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    parent_id: str | None = None


def load_documents(data_dir: str = DATA_DIR) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    for path in sorted(Path(data_dir).glob("*.md")):
        text = path.read_text(encoding="utf-8")
        documents.append(
            {
                "text": text,
                "metadata": {
                    "source": path.name,
                    "path": str(path),
                    "title": text.splitlines()[0].lstrip("# ").strip() if text else path.stem,
                },
            }
        )
    return documents


def _split_markdown_sections(text: str) -> list[str]:
    sections: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("## ") and current:
            sections.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append(current)
    return ["\n".join(section).strip() for section in sections if "\n".join(section).strip()]


def chunk_basic(text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
    base_metadata = metadata or {}
    return [Chunk(section, dict(base_metadata)) for section in _split_markdown_sections(text)]


def chunk_hierarchical(
    text: str,
    metadata: dict[str, Any] | None = None,
) -> tuple[list[Chunk], list[Chunk]]:
    base_metadata = metadata or {}
    parent = Chunk(text, dict(base_metadata), parent_id=None)
    parent_id = str(base_metadata.get("source", "document"))
    children = [
        Chunk(section, {**base_metadata, "section_index": idx}, parent_id=parent_id)
        for idx, section in enumerate(_split_markdown_sections(text), start=1)
    ]
    return [parent], children
