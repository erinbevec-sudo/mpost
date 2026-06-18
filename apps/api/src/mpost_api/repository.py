from typing import Any

from sqlalchemy import RowMapping, text
from sqlalchemy.orm import Session


VALID_ROLES = {"user", "chief_of_staff", "rbac_admin"}


def row_to_dict(row: RowMapping) -> dict[str, Any]:
    return dict(row)


def ensure_user(db: Session, email: str, display_name: str | None = None) -> str:
    row = db.execute(
        text(
            """
            INSERT INTO users (email, display_name)
            VALUES (:email, :display_name)
            ON CONFLICT (email) DO UPDATE
            SET display_name = COALESCE(EXCLUDED.display_name, users.display_name)
            RETURNING id
            """
        ),
        {"email": email, "display_name": display_name or email},
    ).mappings().one()
    return str(row["id"])


def create_document(
    db: Session,
    *,
    title: str,
    source_filename: str,
    storage_uri: str | None,
    uploaded_by_email: str,
    metadata: dict[str, Any],
    status: str = "pending",
) -> dict[str, Any]:
    uploader_id = ensure_user(db, uploaded_by_email)
    document = db.execute(
        text(
            """
            INSERT INTO documents (title, source_filename, storage_uri, status, uploaded_by)
            VALUES (:title, :source_filename, :storage_uri, :status, :uploaded_by)
            RETURNING id, title, source_filename, storage_uri, status, created_at, updated_at
            """
        ),
        {
            "title": title,
            "source_filename": source_filename,
            "storage_uri": storage_uri,
            "status": status,
            "uploaded_by": uploader_id,
        },
    ).mappings().one()

    db.execute(
        text(
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
            VALUES (
              :document_id,
              :doctrine_type,
              :echelon,
              :mp_unit_type,
              :operation_type,
              :classification_level,
              :publication_date,
              :tags
            )
            """
        ),
        {"document_id": document["id"], **metadata},
    )
    db.commit()
    return row_to_dict(document)


def list_documents(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT
              d.id,
              d.title,
              d.source_filename,
              d.storage_uri,
              d.status,
              d.created_at,
              d.updated_at,
              m.doctrine_type,
              m.echelon,
              m.mp_unit_type,
              m.operation_type,
              m.classification_level,
              m.publication_date,
              m.tags,
              count(c.id) AS chunk_count,
              count(e.id) AS embedding_count
            FROM documents d
            LEFT JOIN document_metadata m ON m.document_id = d.id
            LEFT JOIN document_chunks c ON c.document_id = d.id
            LEFT JOIN document_embeddings e ON e.chunk_id = c.id
            GROUP BY d.id, m.document_id
            ORDER BY d.created_at DESC
            """
        )
    ).mappings().all()
    return [row_to_dict(row) for row in rows]


def get_document(db: Session, document_id: str) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT
              d.id,
              d.title,
              d.source_filename,
              d.storage_uri,
              d.status,
              d.created_at,
              d.updated_at,
              m.doctrine_type,
              m.echelon,
              m.mp_unit_type,
              m.operation_type,
              m.classification_level,
              m.publication_date,
              m.tags,
              count(c.id) AS chunk_count,
              count(e.id) AS embedding_count
            FROM documents d
            LEFT JOIN document_metadata m ON m.document_id = d.id
            LEFT JOIN document_chunks c ON c.document_id = d.id
            LEFT JOIN document_embeddings e ON e.chunk_id = c.id
            WHERE d.id = :document_id
            GROUP BY d.id, m.document_id
            """
        ),
        {"document_id": document_id},
    ).mappings().first()
    return row_to_dict(row) if row else None


def set_document_status(db: Session, document_id: str, status: str) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            UPDATE documents
            SET status = :status, updated_at = now()
            WHERE id = :document_id
            RETURNING id
            """
        ),
        {"document_id": document_id, "status": status},
    ).mappings().first()
    if row is None:
        return None
    db.commit()
    return get_document(db, document_id)


def update_document_metadata(
    db: Session,
    document_id: str,
    metadata: dict[str, Any],
) -> dict[str, Any] | None:
    exists = db.execute(
        text("SELECT 1 FROM documents WHERE id = :document_id"),
        {"document_id": document_id},
    ).first()
    if exists is None:
        return None

    db.execute(
        text(
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
            VALUES (
              :document_id,
              :doctrine_type,
              :echelon,
              :mp_unit_type,
              :operation_type,
              :classification_level,
              :publication_date,
              :tags
            )
            ON CONFLICT (document_id) DO UPDATE
            SET
              doctrine_type = EXCLUDED.doctrine_type,
              echelon = EXCLUDED.echelon,
              mp_unit_type = EXCLUDED.mp_unit_type,
              operation_type = EXCLUDED.operation_type,
              classification_level = EXCLUDED.classification_level,
              publication_date = EXCLUDED.publication_date,
              tags = EXCLUDED.tags
            """
        ),
        {"document_id": document_id, **metadata},
    )
    db.execute(
        text("UPDATE documents SET updated_at = now() WHERE id = :document_id"),
        {"document_id": document_id},
    )
    db.commit()
    return get_document(db, document_id)


def assign_role(db: Session, email: str, role: str) -> None:
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}")
    user_id = ensure_user(db, email)
    db.execute(
        text(
            """
            INSERT INTO user_roles (user_id, role_id)
            SELECT :user_id, id
            FROM roles
            WHERE name = :role
            ON CONFLICT DO NOTHING
            """
        ),
        {"user_id": user_id, "role": role},
    )
    db.commit()


def remove_role(db: Session, email: str, role: str) -> None:
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}")
    db.execute(
        text(
            """
            DELETE FROM user_roles
            WHERE user_id = (SELECT id FROM users WHERE email = :email)
            AND role_id = (SELECT id FROM roles WHERE name = :role)
            """
        ),
        {"email": email, "role": role},
    )
    db.commit()


def set_user_password(db: Session, email: str, password_hash: str) -> None:
    """Set or update a user's password hash."""
    db.execute(
        text(
            """
            UPDATE users
            SET password_hash = :password_hash
            WHERE email = :email
            """
        ),
        {"email": email, "password_hash": password_hash},
    )
    db.commit()


def list_user_roles(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT
              u.email,
              COALESCE(array_remove(array_agg(r.name ORDER BY r.name), NULL), ARRAY[]::text[]) AS roles
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.id
            LEFT JOIN roles r ON r.id = ur.role_id
            GROUP BY u.email
            ORDER BY u.email
            """
        )
    ).mappings().all()
    return [row_to_dict(row) for row in rows]


def vector_search(
    db: Session,
    *,
    query_vector: str,
    limit: int,
    echelon: str | None,
    mp_unit_type: str | None,
    operation_type: str | None,
) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            WITH ranked AS (
              SELECT
                c.id AS chunk_id,
                c.chunk_index,
                c.page_number,
                d.id AS document_id,
                d.title,
                d.source_filename,
                c.text AS snippet,
                m.doctrine_type,
                m.echelon,
                m.mp_unit_type,
                m.operation_type,
                m.classification_level,
                m.tags,
                1 - (e.embedding <=> CAST(:query_vector AS vector)) AS score,
                e.embedding_model
              FROM document_embeddings e
              JOIN document_chunks c ON c.id = e.chunk_id
              JOIN documents d ON d.id = c.document_id
              LEFT JOIN document_metadata m ON m.document_id = d.id
              WHERE d.status = 'ready'
                AND (CAST(:echelon AS text) IS NULL OR m.echelon = CAST(:echelon AS text))
                AND (
                  CAST(:mp_unit_type AS text) IS NULL
                  OR m.mp_unit_type = CAST(:mp_unit_type AS text)
                )
                AND (
                  CAST(:operation_type AS text) IS NULL
                  OR m.operation_type = CAST(:operation_type AS text)
                )
            ),
            deduped AS (
              SELECT DISTINCT ON (source_filename, chunk_index)
                *
              FROM ranked
              ORDER BY source_filename, chunk_index, score DESC
            )
            SELECT *
            FROM deduped
            ORDER BY score DESC
            LIMIT :limit
            """
        ),
        {
            "query_vector": query_vector,
            "limit": limit,
            "echelon": echelon,
            "mp_unit_type": mp_unit_type,
            "operation_type": operation_type,
        },
    ).mappings().all()
    return [row_to_dict(row) for row in rows]
