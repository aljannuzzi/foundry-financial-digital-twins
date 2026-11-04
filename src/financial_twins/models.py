from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DecisionChoice = Literal["accept", "reject", "consider", "request_change"]


class UsageMonth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    twin_id: str
    month: str
    deposits_brl: float = Field(ge=0)
    expenses_brl: float = Field(ge=0)
    average_balance_brl: float
    card_spend_brl: float = Field(ge=0)
    agro_inputs_share: float = Field(ge=0, le=1)
    app_sessions: int = Field(ge=0)
    advisor_contacts: int = Field(ge=0)
    insurance_coverage_ratio: float = Field(ge=0, le=1)
    rewards_earned_brl: float = Field(ge=0)
    rewards_redeemed_brl: float = Field(ge=0)
    offers_shown: int = Field(ge=0)
    offers_accepted: int = Field(ge=0)
    overdraft_days: int = Field(ge=0, le=31)
    support_cases: int = Field(ge=0)
    unresolved_cases: int = Field(ge=0)


class EvidenceValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    value: float | str
    layer: Literal["synthetic_observable", "derived"]
    source_model: str
    observation_window: str


class TraitHypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(min_length=1)
    status: Literal["uncertain"] = "uncertain"
    method_version: str


class TwinProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    segment: Literal["Agro"] = "Agro"
    behavioral_anchor: str
    population_seed: str
    profile_version: str
    specification_hash: str
    observables: list[EvidenceValue]
    derived: list[EvidenceValue]
    hypotheses: list[TraitHypothesis]
    current_products: list[str]
    unknowns: list[str]
    generated_at: datetime

    def evidence_ids(self) -> set[str]:
        return {item.id for item in [*self.observables, *self.derived]}

    def trait(self, name: str) -> TraitHypothesis:
        for trait in self.hypotheses:
            if trait.name == name:
                return trait
        raise KeyError(f"Trait not found: {name}")

    def feature(self, name: str) -> float:
        for feature in [*self.observables, *self.derived]:
            if feature.name == name:
                if isinstance(feature.value, str):
                    raise TypeError(f"Feature {name} is not numeric")
                return float(feature.value)
        raise KeyError(f"Feature not found: {name}")

    def agent_payload(self) -> dict:
        return self.model_dump(mode="json", exclude={"population_seed"})


class AuditRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    twin_id: str
    latent_traits: dict[str, float]
    synthetic_audit_group: Literal["A", "B"]
    generator_version: str


class PopulationManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int
    seed: str
    profile_version: str
    specification_hash: str
    generator_version: str
    profile_digest: str
    artifact_digest: str
    generated_at: datetime
    anchor_counts: dict[str, int]


class PopulationBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest: PopulationManifest
    profiles: list[TwinProfile]
    events: list[UsageMonth]
    audit_sidecar: list[AuditRecord]


class ProductVariant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)
    monthly_fee_brl: float = Field(ge=0, le=200)
    cashback_rate: float = Field(ge=0, le=0.1)
    insurance_bundle: float = Field(ge=0, le=1)
    grace_days: int = Field(ge=0, le=365)
    digital_service: float = Field(ge=0, le=1)
    advisor_access: float = Field(ge=0, le=1)
    reversibility: float = Field(ge=0, le=1)


class DecisionReason(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor: str
    direction: Literal["positive", "negative", "neutral"]
    evidence_ids: list[str] = Field(min_length=1)
    contribution: float = Field(ge=-1, le=1)


class TwinDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    twin_id: str
    variant_id: str
    engine: Literal["deterministic", "foundry"]
    choice: DecisionChoice
    fit_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    reasons: list[DecisionReason] = Field(min_length=1)
    requested_changes: list[str]
    missing_information: list[str]
    unsupported_inferences: list[str]
    policy_flags: list[str]


class VariantSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant: ProductVariant
    decision_counts: dict[DecisionChoice, int]
    mean_fit_score: float
    by_anchor: dict[str, dict[DecisionChoice, int]]


class SimulationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    scenario_hash: str
    engine: Literal["deterministic", "foundry"]
    population_digest: str
    model_deployment: str | None = None
    agent_name: str | None = None
    agent_version: str
    invocation_mode: Literal["deterministic", "direct-model", "prompt-agent"]
    created_at: datetime
    variants: list[ProductVariant]
    decisions: list[TwinDecision]
    summaries: list[VariantSummary]
    disclaimer: str


class GeneratePopulationRequest(BaseModel):
    count: int = Field(default=120, ge=8, le=500)
    seed: str = Field(default="agro-demo-2026", min_length=3, max_length=100)


class SimulateRequest(BaseModel):
    engine: Literal["deterministic", "foundry"] = "deterministic"
    population_size: int = Field(default=120, ge=8, le=500)
    seed: str = Field(default="agro-demo-2026", min_length=3, max_length=100)
    variants: list[ProductVariant] | None = Field(default=None, min_length=1, max_length=3)

    @model_validator(mode="after")
    def validate_workload(self) -> SimulateRequest:
        if self.engine == "foundry" and self.population_size > 24:
            raise ValueError(
                "Interactive Foundry runs are limited to 24 profiles; "
                "use the batch workflow for larger panels"
            )
        if self.variants:
            variant_ids = [variant.id for variant in self.variants]
            if len(variant_ids) != len(set(variant_ids)):
                raise ValueError("Variant identifiers must be unique")
        return self
