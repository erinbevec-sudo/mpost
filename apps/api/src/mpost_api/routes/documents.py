from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from mpost_api.db import get_db
from mpost_api.repository import create_document as create_document_record
from mpost_api.repository import get_document as get_document_record
from mpost_api.repository import list_documents as list_document_records
from mpost_api.repository import set_document_status
from mpost_api.repository import update_document_metadata

router = APIRouter()


class DocumentCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    source_filename: str = Field(min_length=1)
    storage_uri: str | None = None
    doctrine_type: str | None = None
    echelon: str | None = None
    mp_unit_type: str | None = None
    operation_type: str | None = None
    classification_level: str | None = None
    publication_date: date | None = None
    tags: list[str] = Field(default_factory=list)


class DocumentResponse(BaseModel):
    id: str
    title: str
    source_filename: str
    storage_uri: str | None = None
    status: str
    doctrine_type: str | None = None
    echelon: str | None = None
    mp_unit_type: str | None = None
    operation_type: str | None = None
    classification_level: str | None = None
    publication_date: date | None = None
    tags: list[str] = Field(default_factory=list)
    chunk_count: int = 0
    embedding_count: int = 0


class DocumentReviewRequest(BaseModel):
    status: str = Field(pattern="^(approved|denied)$")


class DocumentMetadataUpdateRequest(BaseModel):
    doctrine_type: str | None = None
    echelon: str | None = None
    mp_unit_type: str | None = None
    operation_type: str | None = None
    classification_level: str | None = None
    publication_date: date | None = None
    tags: list[str] = Field(default_factory=list)


@router.post("", response_model=DocumentResponse)
def create_document(
    request: DocumentCreateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> DocumentResponse:
    document = create_document_record(
        db,
        title=request.title,
        source_filename=request.source_filename,
        storage_uri=request.storage_uri,
        uploaded_by_email="system",
        metadata=_metadata_payload(request),
    )
    return _document_response(document, _metadata_payload(request))


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(),
    title: str = Form(""),
    doctrine_type: str | None = Form(None),
    mp_unit_type: str | None = Form(None),
    tags: str = Form(""),
) -> DocumentResponse:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Filename required")

    uploads_dir = Path("/app/data/uploads")
    if not uploads_dir.exists():
        uploads_dir = Path("data/uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = Path(file.filename).name
    storage_path = uploads_dir / safe_filename
    contents = await file.read()
    storage_path.write_bytes(contents)

    metadata = {
        "doctrine_type": doctrine_type or "user_submission",
        "echelon": None,
        "mp_unit_type": mp_unit_type,
        "operation_type": None,
        "classification_level": "unreviewed",
        "publication_date": None,
        "tags": [item.strip() for item in tags.split(",") if item.strip()],
    }
    document = create_document_record(
        db,
        title=title or storage_path.stem,
        source_filename=safe_filename,
        storage_uri=str(storage_path),
        uploaded_by_email="system",
        metadata=metadata,
        status="submitted",
    )
    return _document_response(document, metadata)


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    db: Annotated[Session, Depends(get_db)],
) -> list[DocumentResponse]:
    return [_document_response(document) for document in list_document_records(db)]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> DocumentResponse:
    document = get_document_record(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return _document_response(document)


@router.get("/{document_id}/file")
def get_document_file(
    document_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    document = get_document_record(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    storage_uri = document.get("storage_uri")
    if not storage_uri:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No document file stored")

    path = Path(str(storage_uri)).resolve()
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found")

    return FileResponse(path, media_type="application/pdf", filename=str(document["source_filename"]))


@router.post("/{document_id}/review", response_model=DocumentResponse)
def review_document(
    document_id: str,
    request: DocumentReviewRequest,
    db: Annotated[Session, Depends(get_db)],
) -> DocumentResponse:
    document = set_document_status(db, document_id, request.status)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return _document_response(document)


@router.patch("/{document_id}/metadata", response_model=DocumentResponse)
def patch_document_metadata(
    document_id: str,
    request: DocumentMetadataUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> DocumentResponse:
    document = update_document_metadata(db, document_id, _metadata_payload(request))
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return _document_response(document)


def _metadata_payload(
    request: DocumentCreateRequest | DocumentMetadataUpdateRequest,
) -> dict[str, object]:
    return {
        "doctrine_type": request.doctrine_type,
        "echelon": request.echelon,
        "mp_unit_type": request.mp_unit_type,
        "operation_type": request.operation_type,
        "classification_level": request.classification_level,
        "publication_date": request.publication_date,
        "tags": request.tags,
    }


def _document_response(
    document: dict[str, object],
    metadata: dict[str, object] | None = None,
) -> DocumentResponse:
    payload = {**document, **(metadata or {})}
    payload["id"] = str(payload["id"])
    return DocumentResponse(**payload)
