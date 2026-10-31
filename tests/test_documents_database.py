from datetime import date
from decimal import Decimal
from pathlib import Path

from src.database import (
    active_criteria, complete_run, create_run, document_sha256, find_saved_documents,
    initialize_database, list_run_documents,
)
from src.schemas import RankedSupplier, SupplierInput


def test_every_uploaded_pdf_is_persisted_and_detectable(tmp_path: Path) -> None:
    database = tmp_path / "rfp.sqlite3"
    initialize_database(database)
    run_id = create_run(database, active_criteria(database), {})
    inputs = [
        SupplierInput(supplier_name="Apex", submission_date=date(2026, 1, 1), experience_rating=Decimal("8"), document_name="apex.pdf", document_bytes=b"apex"),
        SupplierInput(supplier_name="Nexa", submission_date=date(2026, 1, 2), experience_rating=Decimal("7"), document_name="nexa.pdf", document_bytes=b"nexa"),
    ]
    results = [
        RankedSupplier(supplier_name=item.supplier_name, submission_date=item.submission_date, experience_rating=item.experience_rating,
                       absolute_score=Decimal("80"), ppi=Decimal("80"), final_rank=index, criteria=[], risks=[],
                       overall_summary="", warnings=[], ranking_explanation="")
        for index, item in enumerate(inputs, start=1)
    ]
    complete_run(database, run_id, results, inputs)
    assert {row["file_name"] for row in list_run_documents(database, run_id)} == {"apex.pdf", "nexa.pdf"}
    duplicates = find_saved_documents(database, [document_sha256(b"apex")])
    assert len(duplicates) == 1
    assert duplicates[0]["supplier_name"] == "Apex"
