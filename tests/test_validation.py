from decimal import Decimal

from src.schemas import Criterion
from src.validation import normalize_evaluation


def test_missing_and_out_of_range_scores_are_normalized() -> None:
    criteria = [
        Criterion(criterion_id=1, name="A", description="", weight=Decimal("50"), max_score=Decimal("10")),
        Criterion(criterion_id=2, name="B", description="", weight=Decimal("50"), max_score=Decimal("10")),
    ]
    result = normalize_evaluation({"supplier_name": "Acme", "criteria": [
        {"criterion_id": 1, "score": 20, "max_score": 20, "justification": "x", "evidence": "y"}
    ], "risks": [], "overall_summary": ""}, criteria, "Acme")
    assert result.criteria[0].score == Decimal("10")
    assert result.criteria[1].score == Decimal("0")
    assert "missing" in result.criteria[1].warnings[0].lower()
