# MPOST Architecture

MPOST is split into four boundaries:

```text
web UI -> API -> Postgres/pgvector
              -> ingestion worker
```

The POC starts with the API and database. The web UI can be added under `apps/web` later and deployed separately to Vercel.

## Backend

The FastAPI backend owns:

- RBAC enforcement
- document metadata endpoints
- semantic search endpoints
- persona recommendation endpoints

The current auth layer is a development shim based on request headers:

- `X-MPOST-User-Email`
- `X-MPOST-User-Role`

Replace this with OIDC/JWT verification before real deployment.

## Database

Postgres stores:

- users and roles
- document records
- metadata filters
- chunks
- pgvector embeddings
- saved personas

The default embedding size is `384`, matching `BAAI/bge-small-en-v1.5`.

## Ingestion

The ingestion worker should eventually:

1. extract text from PDF/DOCX
2. chunk text
3. embed chunks
4. write chunks and embeddings to Postgres
5. mark the document searchable

The current POC importer writes documents and chunks first. Embedding persistence is intentionally left as the next step so the local drop-folder workflow can be validated before adding model runtime cost.
