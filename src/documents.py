from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader


def extract_pdf_text(document_bytes: bytes, max_characters: int) -> str:
    try:
        reader = PdfReader(BytesIO(document_bytes))
    except Exception as exc:
        raise ValueError("The uploaded file could not be read as a PDF.") from exc
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs are not supported.")
    pages: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(f"[Page {page_number}]\n{text}")
    extracted = "\n\n".join(pages)
    if not extracted:
        raise ValueError("The PDF contains no extractable text. Use a text-based PDF; OCR is not enabled.")
    if len(extracted) > max_characters:
        raise ValueError(f"Extracted text exceeds the {max_characters:,}-character limit.")
    return extracted
