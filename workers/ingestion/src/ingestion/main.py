from pathlib import Path
import argparse
import shutil

from ingestion.chunk import chunk_pages, chunk_text
from ingestion.embed import Embedder
from ingestion.extract_text import extract_text, extract_text_pages
from ingestion.load import load_document
from ingestion.metadata import load_metadata_for_document


def ingest_file(path: Path) -> list[str]:
    text = extract_text(path)
    return chunk_text(text)


def ingest_file_with_pages(path: Path) -> tuple[list[str], list[int | None]]:
    records = chunk_pages(extract_text_pages(path))
    return [record.text for record in records], [record.page_number for record in records]


def ingest_path(path: Path, move_processed: bool = False, embed: bool = False) -> None:
    from ingestion.config import settings

    files = _iter_supported_files(path)
    embedder = Embedder(model_name=settings.embedding_model) if embed else None

    for file_path in files:
        # Check if document already exists and has embeddings
        if _document_already_embedded(file_path):
            print(f"Skipped {file_path.name}: already embedded in database")
            continue

        try:
            chunks, page_numbers = ingest_file_with_pages(file_path)
        except ValueError as exc:
            print(f"Skipped {file_path.name}: {exc}")
            continue
        if not chunks:
            print(f"Skipped {file_path.name}: no text chunks extracted")
            continue

        metadata = load_metadata_for_document(file_path)
        embeddings = embedder.encode(chunks) if embedder is not None else None
        embedding_model = embedder.model_name if embedder is not None else None
        result = load_document(file_path, chunks, metadata, embeddings, embedding_model, page_numbers)
        print(
            "Imported "
            f"{result.title}: {result.chunk_count} chunks, "
            f"{result.embedding_count} embeddings ({result.document_id})"
        )
        if move_processed:
            processed_dir = Path("data/processed")
            processed_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), processed_dir / file_path.name)
            metadata_path = file_path.with_suffix(".metadata.json")
            if metadata_path.exists():
                shutil.move(str(metadata_path), processed_dir / metadata_path.name)


def _document_already_embedded(file_path: Path) -> bool:
    """Check if document already exists in database with embeddings."""
    from ingestion.config import settings
    import psycopg
    from psycopg.rows import dict_row

    try:
        with psycopg.connect(settings.psycopg_database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                """
                SELECT COUNT(de.id) as embedding_count
                FROM documents d
                JOIN document_chunks dc ON dc.document_id = d.id
                LEFT JOIN document_embeddings de ON de.chunk_id = dc.id
                WHERE d.source_filename = %s
                """,
                (file_path.name,),
            ).fetchone()

            if row and row["embedding_count"] > 0:
                return True
    except Exception:
        pass

    return False


def _iter_supported_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]

    supported_suffixes = {".pdf", ".docx"}
    return sorted(
        child
        for child in path.iterdir()
        if child.is_file() and child.suffix.lower() in supported_suffixes
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import local MPOST documents into Postgres.")
    parser.add_argument("path", type=Path, help="Document file or folder to import.")
    parser.add_argument(
        "--move-processed",
        action="store_true",
        help="Move successfully imported files to data/processed.",
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Generate and store embeddings for each chunk.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    ingest_path(args.path, move_processed=args.move_processed, embed=args.embed)
