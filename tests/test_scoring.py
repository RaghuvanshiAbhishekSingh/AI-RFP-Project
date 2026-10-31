from datetime import date
from decimal import Decimal

from src.schemas import Criterion, NormalizedCriterionResult, NormalizedEvaluation, SupplierInput
from src.scoring import score_suppliers


def test_scores_and_peer_metrics() -> None:
    criteria = [
        Criterion(criterion_id=1, name="A", description="", weight=Decimal("60"), max_score=Decimal("10")),
        Criterion(criterion_id=2, name="B", description="", weight=Decimal("40"), max_score=Decimal("10")),
    ]
    inputs = [
        SupplierInput(supplier_name="One", submission_date=date(2026, 1, 1), experience_rating=Decimal("5"), document_name="a.pdf", document_bytes=b"a"),
        SupplierInput(supplier_name="Two", submission_date=date(2026, 1, 2), experience_rating=Decimal("5"), document_name="b.pdf", document_bytes=b"b"),
    ]
    def evaluation(name: str, a: str, b: str) -> NormalizedEvaluation:
        return NormalizedEvaluation(supplier_name=name, criteria=[
            NormalizedCriterionResult(criterion_id=1, score=Decimal(a), max_score=Decimal("10"), justification="", evidence=""),
            NormalizedCriterionResult(criterion_id=2, score=Decimal(b), max_score=Decimal("10"), justification="", evidence=""),
        ], risks=[], overall_summary="")
    result = score_suppliers(inputs, [evaluation("One", "8", "5"), evaluation("Two", "4", "10")], criteria)
    assert result[0].absolute_score == Decimal("68")
    assert result[1].absolute_score == Decimal("64")
    assert result[0].ppi == Decimal("80")
    assert result[1].ppi == Decimal("70")
