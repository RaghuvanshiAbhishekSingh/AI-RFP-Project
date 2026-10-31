from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path = Path(os.getenv("RFP_DATABASE_PATH", "rfp_evaluation.sqlite3"))
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    llm_model: str = os.getenv("RFP_LLM_MODEL", "gpt-4o-mini")
    max_pdf_bytes: int = int(os.getenv("RFP_MAX_PDF_BYTES", str(10 * 1024 * 1024)))
    max_document_characters: int = int(os.getenv("RFP_MAX_DOCUMENT_CHARS", "60000"))


settings = Settings()
