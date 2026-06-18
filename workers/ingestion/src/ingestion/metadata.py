import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DocumentMetadata:
    doctrine_type: str | None = None
    echelon: str | None = None
    mp_unit_type: str | None = None
    operation_type: str | None = None
    classification_level: str | None = None
    publication_date: date | None = None
    tags: list[str] = field(default_factory=list)


def load_metadata_for_document(path: Path) -> DocumentMetadata:
    metadata_path = path.with_suffix(".metadata.json")
    if not metadata_path.exists():
        return DocumentMetadata()

    raw = json.loads(metadata_path.read_text())
    return parse_metadata(raw)


def parse_metadata(raw: dict[str, Any]) -> DocumentMetadata:
    publication_date = raw.get("publication_date")
    tags = raw.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]

    return DocumentMetadata(
        doctrine_type=raw.get("doctrine_type"),
        echelon=raw.get("echelon"),
        mp_unit_type=raw.get("mp_unit_type"),
        operation_type=raw.get("operation_type"),
        classification_level=raw.get("classification_level"),
        publication_date=date.fromisoformat(publication_date) if publication_date else None,
        tags=list(tags),
    )
