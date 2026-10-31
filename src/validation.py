from __future__ import annotations

from decimal import Decimal, InvalidOperation

from pydantic import ValidationError

from .schemas import Criterion, LlmEvaluation, NormalizedCriterionResult, NormalizedEvaluation


def _text(value: object) -> tuple[str, bool]:
    if isinstance(value, str):
        return value.strip(), False
    if value is None:
        return "", True
    return str(value).strip(), True


def _score(value: object, maximum: Decimal) -> tuple[Decimal, str | None]:
    if isinstance(value, bool) or value is None:
        return Decimal("0"), "Score was invalid and was replaced with 0."
    try:
        score = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0"), "Score was invalid and was replaced with 0."
    if not score.is_finite():
        return Decimal("0"), "Score was not finite and was replaced with 0."
    warning = "Score was converted from text." if isinstance(value, str) else None
    if score < 0:
        return Decimal("0"), "Score was below 0 and was clipped."
    if score > maximum:
        return maximum, f"Score exceeded {maximum} and was clipped."
    return score, warning


def normalize_evaluation(
    response: object,
    criteria: list[Criterion],
    supplier_name: str,
) -> NormalizedEvaluation:
    """Normalize an LLM response against authoritative criteria and form metadata."""
    try:
        parsed = LlmEvaluation.model_validate(response)
    except ValidationError as exc:
        raise ValueError(f"LLM response did not match the required top-level schema: {exc}") from exc

    warnings: list[str] = []
    supplied_name, coerced = _text(parsed.supplier_name)
    if supplied_name.casefold() != supplier_name.strip().casefold():
        warnings.append("LLM supplier name did not match form metadata; form metadata was used.")
    if coerced:
        warnings.append("LLM supplier name was not text; form metadata was used.")

    expected = {criterion.criterion_id: criterion for criterion in criteria}
    received: dict[int, object] = {}
    for result in parsed.criteria:
        if result.criterion_id not in expected:
            warnings.append(f"Unknown criterion {result.criterion_id} was ignored.")
        elif result.criterion_id in received:
            warnings.append(f"Duplicate criterion {result.criterion_id} was ignored after its first result.")
        else:
            received[result.criterion_id] = result

    normalized: list[NormalizedCriterionResult] = []
    for criterion in criteria:
        criterion_warnings: list[str] = []
        result = received.get(criterion.criterion_id)
        if result is None:
            criterion_warnings.append("Criterion was missing from LLM output; score was set to 0.")
            normalized.append(NormalizedCriterionResult(
                criterion_id=criterion.criterion_id, score=Decimal("0"), max_score=criterion.max_score,
                justification="Evaluation result was missing.", evidence="", warnings=criterion_warnings,
            ))
            continue
        score, score_warning = _score(result.score, criterion.max_score)
        if score_warning:
            criterion_warnings.append(score_warning)
        try:
            model_maximum = Decimal(str(result.max_score))
            if model_maximum != criterion.max_score:
                criterion_warnings.append("LLM maximum score differed from configured maximum; configured value was used.")
        except (InvalidOperation, ValueError):
            criterion_warnings.append("LLM maximum score was invalid; configured value was used.")
        justification, justification_coerced = _text(result.justification)
        evidence, evidence_coerced = _text(result.evidence)
        if justification_coerced:
            criterion_warnings.append("Justification was invalid and normalized to text.")
        if evidence_coerced:
            criterion_warnings.append("Evidence was invalid and normalized to text.")
        normalized.append(NormalizedCriterionResult(
            criterion_id=criterion.criterion_id, score=score, max_score=criterion.max_score,
            justification=justification, evidence=evidence, warnings=criterion_warnings,
        ))

    if isinstance(parsed.risks, list):
        risks = [str(item).strip() for item in parsed.risks if str(item).strip()]
    else:
        risks = []
        warnings.append("Risks were invalid and normalized to an empty list.")
    summary, summary_coerced = _text(parsed.overall_summary)
    if summary_coerced:
        warnings.append("Overall summary was invalid and normalized to text.")
    return NormalizedEvaluation(
        supplier_name=supplier_name.strip(), criteria=normalized, risks=risks,
        overall_summary=summary, warnings=warnings,
    )
