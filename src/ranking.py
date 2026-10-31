from __future__ import annotations

from .schemas import RankedSupplier


def rank_suppliers(suppliers: list[RankedSupplier]) -> list[RankedSupplier]:
    ordered = sorted(
        suppliers,
        key=lambda item: (-item.ppi, item.submission_date, -item.experience_rating, item.supplier_name.casefold()),
    )
    for index, supplier in enumerate(ordered, start=1):
        supplier.final_rank = index
        supplier.ranking_explanation = (
            "Ordered by PPI (descending), submission date (ascending), historical experience "
            "rating (descending), then supplier name (ascending)."
        )
    return ordered
