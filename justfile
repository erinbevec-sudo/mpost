set dotenv-load

python := ".venv/bin/python"
pip := ".venv/bin/pip"

default:
    just --list

venv:
    python3 -m venv .venv

install-api: venv
    {{pip}} install -e "apps/api[dev]"

install-api-search: venv
    {{pip}} install -e "apps/api[dev,search]"

install-ingestion: venv
    {{pip}} install -e "workers/ingestion[dev]"

install-ingestion-embed: install-ingestion

install-search: install-api install-ingestion

install-web:
    cd apps/web && npm install

install: install-api install-ingestion install-web

up:
    docker compose up --build

up-detached:
    docker compose up --build -d

down:
    docker compose down

db-shell:
    psql "${LOCAL_DATABASE_URL:-postgresql://mpost:mpost@localhost:55432/mpost}"

db-counts:
    psql "${LOCAL_DATABASE_URL:-postgresql://mpost:mpost@localhost:55432/mpost}" -c "SELECT 'documents' AS table_name, count(*) FROM documents UNION ALL SELECT 'document_metadata', count(*) FROM document_metadata UNION ALL SELECT 'document_chunks', count(*) FROM document_chunks UNION ALL SELECT 'document_embeddings', count(*) FROM document_embeddings;"

db-documents:
    psql "${LOCAL_DATABASE_URL:-postgresql://mpost:mpost@localhost:55432/mpost}" -c "SELECT d.id, d.title, d.status, m.doctrine_type, m.mp_unit_type, m.classification_level, m.tags FROM documents d LEFT JOIN document_metadata m ON m.document_id = d.id ORDER BY d.created_at DESC;"

db-migrate:
    psql "${LOCAL_DATABASE_URL:-postgresql://mpost:mpost@localhost:55432/mpost}" -f db/migrations/002_add_review_and_page_fields.sql

api-dev:
    PYTHONPATH=apps/api/src {{python}} -m uvicorn mpost_api.main:app --reload --host 0.0.0.0 --port 8000

web-dev:
    cd apps/web && npm run dev

web-build:
    cd apps/web && npm run build

web-typecheck:
    cd apps/web && npm run typecheck

health:
    curl http://localhost:8000/health

ingest path="data/inbox":
    PYTHONPATH=workers/ingestion/src DATABASE_URL="${LOCAL_DATABASE_URL:-postgresql://mpost:mpost@localhost:55432/mpost}" {{python}} -m ingestion.main "{{path}}"

ingest-embed path="data/inbox":
    PYTHONPATH=workers/ingestion/src DATABASE_URL="${LOCAL_DATABASE_URL:-postgresql://mpost:mpost@localhost:55432/mpost}" {{python}} -m ingestion.main "{{path}}" --embed

ingest-move path="data/inbox":
    PYTHONPATH=workers/ingestion/src DATABASE_URL="${LOCAL_DATABASE_URL:-postgresql://mpost:mpost@localhost:55432/mpost}" {{python}} -m ingestion.main "{{path}}" --move-processed

ingest-embed-move path="data/inbox":
    PYTHONPATH=workers/ingestion/src DATABASE_URL="${LOCAL_DATABASE_URL:-postgresql://mpost:mpost@localhost:55432/mpost}" {{python}} -m ingestion.main "{{path}}" --embed --move-processed

compile:
    python3 -m compileall apps/api/src workers/ingestion/src

lint:
    {{python}} -m ruff check apps/api/src workers/ingestion/src

test:
    {{python}} -m pytest apps/api workers/ingestion

check: compile
    docker compose config
