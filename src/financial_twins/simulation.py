from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from uuid import uuid4

from .models import (
    DecisionReason,
    ProductVariant,
    SimulationResult,
    TwinDecision,
    TwinProfile,
    VariantSummary,
)

DISCLAIMER = (
    "Synthetic scenario output, not a forecast. Results show how a versioned "
    "simulation responded to fictional Agro profiles under stated assumptions; "
    "they do not estimate customer demand, revenue, credit risk, or any individual's behavior."
)
DETERMINISTIC_AGENT_VERSION = "deterministic-utility-v1"


def default_product_variants() -> list[ProductVariant]:
    return [
        ProductVariant(
            id="agro-flex-liquidity",
            name="Agro Flex Liquidez",
            description="Season-aligned grace period and flexible cancellation.",
            monthly_fee_brl=59,
            cashback_rate=0.008,
            insurance_bundle=0.45,
            grace_days=150,
            digital_service=0.72,
            advisor_access=0.62,
            reversibility=0.90,
        ),
        ProductVariant(
            id="agro-flex-protection",
            name="Agro Flex Protecao",
            description="Broad protection bundle with specialist relationship support.",
            monthly_fee_brl=89,
            cashback_rate=0.006,
            insurance_bundle=0.95,
            grace_days=90,
            digital_service=0.58,
            advisor_access=0.95,
            reversibility=0.66,
        ),
        ProductVariant(
            id="agro-flex-digital",
            name="Agro Flex Digital Rewards",
            description="Lower operating cost and cashback in relevant categories.",
            monthly_fee_brl=29,
            cashback_rate=0.025,
            insurance_bundle=0.28,
            grace_days=60,
            digital_service=0.98,
            advisor_access=0.28,
            reversibility=0.78,
        ),
    ]


def _clip(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def deterministic_decision(profile: TwinProfile, variant: ProductVariant) -> TwinDecision:
    traits = {trait.name: trait for trait in profile.hypotheses}
    pressure = profile.feature("working_capital_pressure")

    components = {
        "affordability": 1 - traits["price_sensitivity"].score * (variant.monthly_fee_brl / 100),
        "liquidity_fit": (0.58 * traits["liquidity_preference"].score + 0.42 * pressure)
        * (variant.grace_days / 180),
        "protection_fit": traits["risk_protection_preference"].score * variant.insurance_bundle,
        "rewards_fit": traits["reward_affinity"].score * min(1, variant.cashback_rate / 0.025),
        "digital_fit": traits["digital_autonomy"].score * variant.digital_service,
        "advice_fit": traits["advisor_preference"].score * variant.advisor_access,
        "flexibility_fit": traits["reversibility_preference"].score * variant.reversibility,
        "novelty_fit": traits["novelty_openness"].score
        * (0.55 * variant.digital_service + 0.45 * variant.cashback_rate / 0.025),
    }
    weights = {
        "affordability": 0.18,
        "liquidity_fit": 0.19,
        "protection_fit": 0.14,
        "rewards_fit": 0.12,
        "digital_fit": 0.12,
        "advice_fit": 0.10,
        "flexibility_fit": 0.09,
        "novelty_fit": 0.06,
    }
    contributions = {factor: _clip(value) * weights[factor] for factor, value in components.items()}
    score = 100 * sum(contributions.values())
    if score >= 44:
        choice = "accept"
    elif score >= 40:
        choice = "consider"
    elif score >= 36:
        choice = "request_change"
    else:
        choice = "reject"

    evidence_by_factor = {
        "affordability": ["H2", "O6", "O8"],
        "liquidity_fit": ["H1", "D1", "O1"],
        "protection_fit": ["H4", "O4"],
        "rewards_fit": ["H5", "O5"],
        "digital_fit": ["H3", "O3"],
        "advice_fit": ["H6", "O7"],
        "flexibility_fit": ["H8", "D1"],
        "novelty_fit": ["H7", "O6"],
    }
    sorted_factors = sorted(contributions, key=contributions.get, reverse=True)
    strongest = sorted_factors[:2]
    weakest = sorted_factors[-2:]
    reasons = [
        DecisionReason(
            factor=factor,
            direction="positive" if factor in strongest else "negative",
            evidence_ids=evidence_by_factor[factor],
            contribution=round(contributions[factor], 4),
        )
        for factor in [*strongest, *weakest]
    ]
    requested_changes: list[str] = []
    if "affordability" in weakest:
        requested_changes.append("Reduce the monthly fee or add a fee waiver.")
    if "liquidity_fit" in weakest:
        requested_changes.append("Align the grace period with the production cycle.")
    if "protection_fit" in weakest:
        requested_changes.append("Clarify or expand the protection bundle.")
    if "advice_fit" in weakest:
        requested_changes.append("Offer a clearer specialist-advisor service level.")

    confidence = sum(trait.confidence for trait in profile.hypotheses) / len(profile.hypotheses)
    return TwinDecision(
        twin_id=profile.id,
        variant_id=variant.id,
        engine="deterministic",
        choice=choice,
        fit_score=round(score, 2),
        confidence=round(confidence, 4),
        reasons=reasons,
        requested_changes=requested_changes,
        missing_information=profile.unknowns,
        unsupported_inferences=[],
        policy_flags=[],
    )


def summarize_decisions(
    profiles: list[TwinProfile],
    variants: list[ProductVariant],
    decisions: list[TwinDecision],
) -> list[VariantSummary]:
    profile_by_id = {profile.id: profile for profile in profiles}
    summaries: list[VariantSummary] = []
    for variant in variants:
        variant_decisions = [
            decision for decision in decisions if decision.variant_id == variant.id
        ]
        counts = Counter(decision.choice for decision in variant_decisions)
        by_anchor: dict[str, Counter] = defaultdict(Counter)
        for decision in variant_decisions:
            anchor = profile_by_id[decision.twin_id].behavioral_anchor
            by_anchor[anchor][decision.choice] += 1
        summaries.append(
            VariantSummary(
                variant=variant,
                decision_counts={
                    choice: counts.get(choice, 0)
                    for choice in ["accept", "reject", "consider", "request_change"]
                },
                mean_fit_score=round(
                    sum(decision.fit_score for decision in variant_decisions)
                    / len(variant_decisions),
                    2,
                ),
                by_anchor={
                    anchor: {
                        choice: anchor_counts.get(choice, 0)
                        for choice in ["accept", "reject", "consider", "request_change"]
                    }
                    for anchor, anchor_counts in sorted(by_anchor.items())
                },
            )
        )
    return summaries


def scenario_hash(
    population_digest: str,
    variants: list[ProductVariant],
    engine: str,
    agent_version: str,
    model_deployment: str | None = None,
    agent_name: str | None = None,
    invocation_mode: str = "deterministic",
) -> str:
    material = {
        "population_digest": population_digest,
        "variants": [variant.model_dump(mode="json") for variant in variants],
        "engine": engine,
        "agent_version": agent_version,
        "agent_name": agent_name,
        "invocation_mode": invocation_mode,
        "model_deployment": model_deployment,
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def validate_variants(variants: list[ProductVariant]) -> None:
    if not 1 <= len(variants) <= 3:
        raise ValueError("A simulation requires between one and three variants")
    variant_ids = [variant.id for variant in variants]
    if len(variant_ids) != len(set(variant_ids)):
        raise ValueError("Variant identifiers must be unique")


def simulate_population(
    profiles: list[TwinProfile],
    population_digest: str,
    variants: list[ProductVariant] | None = None,
) -> SimulationResult:
    selected_variants = variants or default_product_variants()
    validate_variants(selected_variants)
    decisions = [
        deterministic_decision(profile, variant)
        for variant in selected_variants
        for profile in profiles
    ]
    scenario = scenario_hash(
        population_digest,
        selected_variants,
        "deterministic",
        DETERMINISTIC_AGENT_VERSION,
    )
    return SimulationResult(
        run_id=f"run-{scenario[:8]}-{uuid4().hex[:12]}",
        scenario_hash=scenario,
        engine="deterministic",
        population_digest=population_digest,
        model_deployment=None,
        agent_name=None,
        agent_version=DETERMINISTIC_AGENT_VERSION,
        invocation_mode="deterministic",
        created_at=datetime.now(UTC),
        variants=selected_variants,
        decisions=decisions,
        summaries=summarize_decisions(profiles, selected_variants, decisions),
        disclaimer=DISCLAIMER,
    )
