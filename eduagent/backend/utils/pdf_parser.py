from dataclasses import dataclass


@dataclass
class ParsedPDF:
    text: str
    pages: int = 1


def extract_pdf_text(data: bytes) -> ParsedPDF:
    # Lightweight recovery-friendly parser. It handles text PDFs poorly but safely;
    # uploaded notes still get stored and the filename/context can be used.
    try:
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        text = ""
    text = " ".join(text.replace("\x00", " ").split())
    return ParsedPDF(text=text[:120_000], pages=max(1, data.count(b"/Page")))
