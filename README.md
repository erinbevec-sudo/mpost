# M-POST

Military Police Operations Search Tool.

This repository is a parsimonious proof of concept for a RAG-backed document search system. The first build focuses on the backend, database schema, and ingestion boundaries.

## Current Scope

- FastAPI backend
- PostgreSQL with pgvector
- RBAC roles:
  - `user`
  - `chief_of_staff`
  - `rbac_admin`
- Document metadata and chunk storage
- Vector search API surface
- Persona-based recommendation API surface

## Local Services

```text
apps/api      FastAPI application
apps/web      Vite React frontend
db            SQL migrations and seed data
workers       document ingestion pipeline
infra         Dockerfiles and service config
docs          architecture notes
```

## Quick Start

Copy the example environment file:

```bash
cp .env.example .env
```

Start local infrastructure:

```bash
just up
```

Local Postgres is published on port `55432` to avoid colliding with other local Postgres containers.

API health check:

```bash
just health
```

Start the frontend:

```bash
just web-dev
```

## Local Document Import

Drop demo PDFs or DOCX files into:

```text
data/inbox
```

Then run the ingestion worker with a database URL that points at local Postgres:

```bash
just ingest
```

To move successfully imported files out of the inbox:

```bash
just ingest-move
```

To generate and store embeddings too:

```bash
just ingest-embed
```

Each document can have a sidecar metadata file named after the document:

```text
data/inbox/fm3-39-2013.pdf
data/inbox/fm3-39-2013.metadata.json
```

Example metadata:

```json
{
  "doctrine_type": "field_manual",
  "echelon": null,
  "mp_unit_type": "military_police",
  "operation_type": null,
  "classification_level": "unclassified",
  "publication_date": null,
  "tags": ["military police", "doctrine"]
}
```

Check what was stored:

```bash
just db-counts
just db-documents
```

## Executive Summaries

The search API can generate executive summaries from search results using:
1. **Hugging Face Inference API** (recommended for deployments) - Cloud-based, free tier available
2. **Ollama** (local alternative) - Local LLM for offline/air-gapped environments
3. **Extractive fallback** - Intelligent sentence extraction when LLM is unavailable

### Hugging Face Setup (Recommended)

Create a free Hugging Face account and get an API token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).

Configure in `.env`:

```bash
LLM_PROVIDER=huggingface
HF_MODEL=meta-llama/Llama-3.2-3B-Instruct
HF_API_TOKEN=your_token_here
```

**Benefits:**
- No local model download (works anywhere)
- Free tier available
- Easy deployment to cloud platforms
- Automatic model updates

**Recommended free models:**
- `meta-llama/Llama-3.2-3B-Instruct` - Best quality (may have cold start delay)
- `Qwen/Qwen2.5-3B-Instruct` - Good alternative
- `microsoft/Phi-3-mini-4k-instruct` - Fast, lightweight

**Note:** First request may take 20-30 seconds while the model loads (cold start). Subsequent requests are fast.

### Ollama Setup (Local Alternative)

For air-gapped or offline environments, install [Ollama](https://ollama.com):

```bash
# Install Ollama, then pull a model:
ollama pull llama3.2:3b
```

Configure in `.env`:

```bash
LLM_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

### Extractive Fallback

To use extractive summaries only (no LLM, no external API):

```bash
LLM_PROVIDER=fallback
```

The extractive summarizer uses query-aware sentence scoring to extract the most relevant statements from search results.

## Commands

Project commands are defined in [justfile](/Users/erin.bevec/mpost/justfile).

Install Python dependencies from the package `pyproject.toml` files:

```bash
just install
```

For embedding ingestion and API semantic search together:

```bash
just install-search
```

The default POC embedder is `mpost-hash-384`, a dependency-free local hash embedder. It is good enough to verify vector storage and search plumbing, but it is not a high-quality semantic model.

Run local checks:

```bash
just check
```

## Security Note

Use only public, synthetic, or explicitly approved demo documents in this POC. Do not upload controlled, classified, sensitive, or operational military documents to free-tier commercial hosting.
