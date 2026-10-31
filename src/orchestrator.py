from __future__ import annotations

from collections.abc import Callable

from .config import Settings
from .database import active_criteria, create_run, fail_run
from .documents import extract_pdf_text
from .prompts import build_evaluation_prompt
from .ranking import rank_suppliers
from .schemas import RankedSupplier, SupplierInput
from .scoring import score_suppliers
from .validation import normalize_evaluation


def evaluate_batch(
    suppliers: list[SupplierInput],
    settings: Settings,
    evaluate_prompt: Callable[[str], dict[str, object]],
) -> tuple[str, list[RankedSupplier]]:
    if len(suppliers) < 1:
        raise ValueError("Add at least one supplier proposal.")
    names = [item.supplier_name.strip().casefold() for item in suppliers]
    if len(names) != len(set(names)):
        raise ValueError("Supplier names must be unique within a run.")
    for supplier in suppliers:
        if len(supplier.document_bytes) > settings.max_pdf_bytes:
            raise ValueError(f"{supplier.document_name} exceeds the allowed file size.")

    criteria = active_criteria(settings.database_path)
    run_id = create_run(settings.database_path, criteria, {"model": settings.llm_model, "prompt_version": "1"})
    try:
        evaluations = []
        for supplier in suppliers:
            document_text = extract_pdf_text(supplier.document_bytes, settings.max_document_characters)
            prompt = build_evaluation_prompt(criteria, supplier.supplier_name, document_text)
            evaluations.append(normalize_evaluation(evaluate_prompt(prompt), criteria, supplier.supplier_name))
        ranked = rank_suppliers(score_suppliers(suppliers, evaluations, criteria))
        # Results remain in the Streamlit session until the user downloads the
        # completed run. The download action persists them atomically.
        return run_id, ranked
    except Exception as exc:
        fail_run(settings.database_path, run_id, str(exc))
        raise
