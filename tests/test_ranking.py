from datetime import date
from decimal import Decimal

from src.ranking import rank_suppliers
from src.schemas import RankedSupplier


def supplier(name: str, day: int, experience: str) -> RankedSupplier:
    return RankedSupplier(supplier_name=name, submission_date=date(2026, 1, day), experience_rating=Decimal(experience), absolute_score=Decimal("70"), ppi=Decimal("80"), criteria=[], risks=[], overall_summary="", warnings=[])


def test_required_tie_break_order() -> None:
    result = rank_suppliers([supplier("Zulu", 2, "9"), supplier("Beta", 1, "2"), supplier("Alpha", 1, "2")])
    assert [item.supplier_name for item in result] == ["Alpha", "Beta", "Zulu"]
    assert [item.final_rank for item in result] == [1, 2, 3]
