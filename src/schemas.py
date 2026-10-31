from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Criterion(BaseModel):
    model_config = ConfigDict(frozen=True)

    criterion_id: int
    name: str
    description: str
    weight: Decimal
    max_score: Decimal
    is_active: bool = True


class SupplierInput(BaseModel):
    supplier_name: str = Field(min_length=1)
    submission_date: date
    experience_rating: Decimal = Field(ge=0, le=10)
    document_name: str
    document_bytes: bytes


class LlmCriterionResult(BaseModel):
    criterion_id: int
    score: Any = None
    max_score: Any = None
    justification: Any = ""
    evidence: Any = ""


class LlmEvaluation(BaseModel):
    supplier_name: Any = ""
    criteria: list[LlmCriterionResult] = Field(default_factory=list)
    risks: Any = Field(default_factory=list)
    overall_summary: Any = ""


class NormalizedCriterionResult(BaseModel):
    criterion_id: int
    score: Decimal
    max_score: Decimal
    justification: str
    evidence: str
    warnings: list[str] = Field(default_factory=list)


class NormalizedEvaluation(BaseModel):
    supplier_name: str
    criteria: list[NormalizedCriterionResult]
    risks: list[str]
    overall_summary: str
    warnings: list[str] = Field(default_factory=list)


class CriterionMetrics(BaseModel):
    criterion_id: int
    score: Decimal
    max_score: Decimal
    weight: Decimal
    benchmark: Decimal
    gap: Decimal
    relative_percent: Decimal
    evidence: str
    justification: str


class RankedSupplier(BaseModel):
    supplier_name: str
    submission_date: date
    experience_rating: Decimal
    absolute_score: Decimal
    ppi: Decimal
    final_rank: int = 0
    criteria: list[CriterionMetrics]
    risks: list[str]
    overall_summary: str
    warnings: list[str]
    ranking_explanation: str = ""
