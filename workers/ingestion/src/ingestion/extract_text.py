from pathlib import Path


def extract_text(path: Path) -> str:
    return "\n".join(extract_text_pages(path))


def extract_text_pages(path: Path) -> list[str]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_pages(path)
    if suffix == ".docx":
        return [_extract_docx(path)]
    raise ValueError(f"Unsupported document type: {suffix}")


def _extract_pdf_pages(path: Path) -> list[str]:
    from pypdf import PdfReader

    reader = PdfReader(path)
    return [page.extract_text() or "" for page in reader.pages]


def _extract_docx(path: Path) -> str:
    import docx

    document = docx.Document(path)
    return "\n".join(paragraph.text for paragraph in document.paragraphs)
