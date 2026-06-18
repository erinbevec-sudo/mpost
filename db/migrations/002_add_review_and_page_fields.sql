ALTER TABLE document_chunks
ADD COLUMN IF NOT EXISTS page_number integer;

CREATE INDEX IF NOT EXISTS documents_status_idx
  ON documents (status);
