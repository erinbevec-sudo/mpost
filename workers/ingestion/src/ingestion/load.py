from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from ingestion.config import settings
from ingestion.metadata import DocumentMetadata


@dataclass(frozen=True)
class DocumentLoadResult:
    document_id: UUID
    title: str
    chunk_count: int
    embedding_count: int


def load_document(
    path: Path,
    chunks: list[str],
    metadata: DocumentMetadata,
    embeddings: list[list[float]] | None = None,
    embedding_model: str | None = None,
    page_numbers: list[int | None] | None = None,
    uploader_email: str = settings.default_uploader_email,
) -> DocumentLoadResult:
    if not chunks:
        raise ValueError(f"No chunks extracted from {path}")
    if embeddings is not None and len(embeddings) != len(chunks):
        raise ValueError("Embedding count must match chunk count")
    if page_numbers is not None and len(page_numbers) != len(chunks):
        raise ValueError("Page number count must match chunk count")

    with psycopg.connect(settings.psycopg_database_url, row_factory=dict_row) as conn:
        with conn.transaction():
            uploader_id = _ensure_user(conn, uploader_email)
            document_id = _create_document(conn, path, uploader_id)
            _create_metadata(conn, document_id, metadata)
            chunk_ids = _create_chunks(conn, document_id, chunks, page_numbers)
            if embeddings is not None and embedding_model is not None:
                _create_embeddings(conn, chunk_ids, embeddings, embedding_model)
            _mark_document_ready(conn, document_id)

    return DocumentLoadResult(
        document_id=document_id,
        title=path.stem,
        chunk_count=len(chunks),
        embedding_count=len(embeddings or []),
    )


def _ensure_user(conn: psycopg.Connection, email: str) -> UUID:
    row = conn.execute(
        """
        INSERT INTO users (email, display_name)
        VALUES (%s, %s)
        ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
        RETURNING id
        """,
        (email, email),
    ).fetchone()
    return row["id"]


def _create_document(conn: psycopg.Connection, path: Path, uploader_id: UUID) -> UUID:
    row = conn.execute(
        """
        INSERT INTO documents (title, source_filename, storage_uri, status, uploaded_by)
        VALUES (%s, %s, %s, 'processing', %s)
        RETURNING id
        """,
        (path.stem, path.name, str(path), uploader_id),
    ).fetchone()
    return row["id"]


def _create_metadata(
    conn: psycopg.Connection,
    document_id: UUID,
    metadata: DocumentMetadata,
) -> None:
    conn.execute(
        """
        INSERT INTO document_metadata (
          document_id,
          doctrine_type,
          echelon,
          mp_unit_type,
          operation_type,
          classification_level,
          publication_date,
          tags
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            document_id,
            metadata.doctrine_type,
            metadata.echelon,
            metadata.mp_unit_type,
            metadata.operation_type,
            metadata.classification_level,
            metadata.publication_date,
            metadata.tags,
        ),
    )


def _create_chunks(
    conn: psycopg.Connection,
    document_id: UUID,
    chunks: list[str],
    page_numbers: list[int | None] | None,
) -> list[UUID]:
    chunk_ids: list[UUID] = []
    for index, chunk in enumerate(chunks):
        page_number = page_numbers[index] if page_numbers is not None else None
        row = conn.execute(
            """
            INSERT INTO document_chunks (document_id, chunk_index, page_number, text, token_count)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (document_id, index, page_number, chunk, len(chunk.split())),
        ).fetchone()
        chunk_ids.append(row["id"])
    return chunk_ids


def _create_embeddings(
    conn: psycopg.Connection,
    chunk_ids: list[UUID],
    embeddings: list[list[float]],
    embedding_model: str,
) -> None:
    rows = [
        (chunk_id, _format_vector(embedding), embedding_model)
        for chunk_id, embedding in zip(chunk_ids, embeddings, strict=True)
    ]
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO document_embeddings (chunk_id, embedding, embedding_model)
            VALUES (%s, %s::vector, %s)
            """,
            rows,
        )


def _format_vector(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"


def _mark_document_ready(conn: psycopg.Connection, document_id: UUID) -> None:
    conn.execute(
        """
        UPDATE documents
        SET status = 'ready', updated_at = now()
        WHERE id = %s
        """,
        (document_id,),
    )
