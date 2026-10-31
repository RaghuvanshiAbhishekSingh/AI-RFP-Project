from __future__ import annotations

from decimal import Decimal

from .schemas import Criterion, CriterionMetrics, NormalizedEvaluation, RankedSupplier, SupplierInput


def score_suppliers(
    inputs: list[SupplierInput], evaluations: list[NormalizedEvaluation], criteria: list[Criterion]
) -> list[RankedSupplier]:
    if len(inputs) != len(evaluations):
        raise ValueError("Each supplier input must have exactly one evaluation.")
    criteria_by_id = {criterion.criterion_id: criterion for criterion in criteria}
    scorecards = [{item.criterion_id: item for item in evaluation.criteria} for evaluation in evaluations]
    benchmarks = {
        criterion.criterion_id: max((card[criterion.criterion_id].score for card in scorecards), default=Decimal("0"))
        for criterion in criteria
    }
    suppliers: list[RankedSupplier] = []
    total_weight = sum((criterion.weight for criterion in criteria), Decimal("0"))
    for supplier_input, evaluation, card in zip(inputs, evaluations, scorecards, strict=True):
        metrics: list[CriterionMetrics] = []
        absolute_score = Decimal("0")
        ppi_total = Decimal("0")
        warnings = list(evaluation.warnings)
        for criterion_id, result in card.items():
            criterion = criteria_by_id[criterion_id]
            benchmark = benchmarks[criterion_id]
            relative = Decimal("0") if benchmark == 0 else Decimal("100") * result.score / benchmark
            if benchmark == 0:
                warnings.append(f"Criterion {criterion.name} had a zero peer benchmark; relative performance is 0.")
            absolute_score += result.score / criterion.max_score * criterion.weight
            ppi_total += relative * criterion.weight
            metrics.append(CriterionMetrics(
                criterion_id=criterion_id, score=result.score, max_score=criterion.max_score, weight=criterion.weight,
                benchmark=benchmark, gap=result.score - benchmark, relative_percent=relative,
                evidence=result.evidence, justification=result.justification,
            ))
            warnings.extend(result.warnings)
        suppliers.append(RankedSupplier(
            supplier_name=supplier_input.supplier_name.strip(), submission_date=supplier_input.submission_date,
            experience_rating=supplier_input.experience_rating, absolute_score=absolute_score,
            ppi=ppi_total / total_weight, criteria=metrics, risks=evaluation.risks,
            overall_summary=evaluation.overall_summary, warnings=warnings,
        ))
    return suppliers
