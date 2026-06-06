from dataclasses import dataclass
from io import BytesIO

from agents.fallbacks import sanitize_document_text


@dataclass
class ParsedPDF:
    text: str
    pages: int = 1


def extract_pdf_text(data: bytes) -> ParsedPDF:
    if data.lstrip().startswith(b"%PDF"):
        return _extract_with_pypdf(data)
    try:
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        text = ""
    return ParsedPDF(text=sanitize_document_text(text), pages=1)


def _extract_with_pypdf(data: bytes) -> ParsedPDF:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF support requires pypdf. Run pip install -r requirements.txt.") from exc

    reader = PdfReader(BytesIO(data))
    pages = max(1, len(reader.pages))
    chunks: list[str] = []
    for page in reader.pages:
        try:
            chunks.append(page.extract_text() or "")
        except Exception:
            continue
    return ParsedPDF(text=sanitize_document_text("\n".join(chunks)), pages=pages)
