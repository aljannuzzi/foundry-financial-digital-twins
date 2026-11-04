from __future__ import annotations

import hashlib
import hmac
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from datetime import UTC, datetime

from .models import (
    AuditRecord,
    EvidenceValue,
    PopulationBundle,
    PopulationManifest,
    TraitHypothesis,
    TwinProfile,
    UsageMonth,
)

GENERATOR_VERSION = "1.0.0"
PROFILE_VERSION = "agro-profile-v1"
METHOD_VERSION = "behavioral-inference-v1"

ANCHOR_PRIORS: dict[str, dict[str, float]] = {
    "Seasonal Liquidity Planner": {
        "liquidity_preference": 0.88,
        "price_sensitivity": 0.62,
        "digital_autonomy": 0.55,
        "risk_protection_preference": 0.62,
        "reward_affinity": 0.45,
        "advisor_preference": 0.57,
        "novelty_openness": 0.48,
        "reversibility_preference": 0.76,
    },
    "Conservative Capital Protector": {
        "liquidity_preference": 0.78,
        "price_sensitivity": 0.65,
        "digital_autonomy": 0.35,
        "risk_protection_preference": 0.88,
        "reward_affinity": 0.30,
        "advisor_preference": 0.78,
        "novelty_openness": 0.22,
        "reversibility_preference": 0.82,
    },
    "Growth Reinvestor": {
        "liquidity_preference": 0.72,
        "price_sensitivity": 0.42,
        "digital_autonomy": 0.70,
        "risk_protection_preference": 0.50,
        "reward_affinity": 0.55,
        "advisor_preference": 0.45,
        "novelty_openness": 0.80,
        "reversibility_preference": 0.52,
    },
    "Risk Hedger": {
        "liquidity_preference": 0.68,
        "price_sensitivity": 0.52,
        "digital_autonomy": 0.48,
        "risk_protection_preference": 0.94,
        "reward_affinity": 0.35,
        "advisor_preference": 0.70,
        "novelty_openness": 0.38,
        "reversibility_preference": 0.72,
    },
    "Digital Efficiency Seeker": {
        "liquidity_preference": 0.62,
        "price_sensitivity": 0.70,
        "digital_autonomy": 0.94,
        "risk_protection_preference": 0.42,
        "reward_affinity": 0.70,
        "advisor_preference": 0.18,
        "novelty_openness": 0.78,
        "reversibility_preference": 0.64,
    },
    "Relationship-Led Advisor": {
        "liquidity_preference": 0.65,
        "price_sensitivity": 0.48,
        "digital_autonomy": 0.25,
        "risk_protection_preference": 0.74,
        "reward_affinity": 0.38,
        "advisor_preference": 0.95,
        "novelty_openness": 0.36,
        "reversibility_preference": 0.70,
    },
    "Rewards Optimizer": {
        "liquidity_preference": 0.55,
        "price_sensitivity": 0.78,
        "digital_autonomy": 0.80,
        "risk_protection_preference": 0.38,
        "reward_affinity": 0.96,
        "advisor_preference": 0.24,
        "novelty_openness": 0.70,
        "reversibility_preference": 0.58,
    },
    "Innovation Explorer": {
        "liquidity_preference": 0.50,
        "price_sensitivity": 0.38,
        "digital_autonomy": 0.88,
        "risk_protection_preference": 0.40,
        "reward_affinity": 0.62,
        "advisor_preference": 0.30,
        "novelty_openness": 0.96,
        "reversibility_preference": 0.48,
    },
}

MONTHS = [
    "2025-11",
    "2025-12",
    "2026-01",
    "2026-02",
    "2026-03",
    "2026-04",
    "2026-05",
    "2026-06",
    "2026-07",
    "2026-08",
    "2026-09",
    "2026-10",
]


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _specification_hash() -> str:
    payload = {
        "anchors": ANCHOR_PRIORS,
        "months": MONTHS,
        "generator_version": GENERATOR_VERSION,
        "profile_version": PROFILE_VERSION,
    }
    return hashlib.sha256(_canonical_json(payload).encode()).hexdigest()


def _rng(seed: str, *parts: object) -> random.Random:
    message = "|".join(str(part) for part in parts).encode()
    digest = hmac.new(seed.encode(), message, hashlib.sha256).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _clip(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _draw(seed: str, profile_id: str, name: str, mean: float, spread: float = 0.09) -> float:
    return _clip(_rng(seed, profile_id, name).gauss(mean, spread))


def _anchor_for_index(index: int) -> str:
    anchors = list(ANCHOR_PRIORS)
    return anchors[index % len(anchors)]


def _latent_traits(seed: str, profile_id: str, anchor: str) -> dict[str, float]:
    traits = {
        name: _draw(seed, profile_id, name, mean) for name, mean in ANCHOR_PRIORS[anchor].items()
    }
    traits["price_sensitivity"] = _clip(
        0.7 * traits["price_sensitivity"] + 0.3 * (1 - traits["novelty_openness"])
    )
    traits["advisor_preference"] = _clip(
        0.75 * traits["advisor_preference"] + 0.25 * (1 - traits["digital_autonomy"])
    )
    return traits


def _generate_usage(
    seed: str,
    profile_id: str,
    traits: dict[str, float],
) -> list[UsageMonth]:
    base_monthly_revenue = _rng(seed, profile_id, "scale").uniform(80_000, 1_250_000)
    peak_month = _rng(seed, profile_id, "peak").randrange(12)
    seasonality = _rng(seed, profile_id, "seasonality").uniform(0.18, 0.72)
    cost_ratio = _rng(seed, profile_id, "cost").uniform(0.55, 0.88)
    events: list[UsageMonth] = []

    for month_index, month in enumerate(MONTHS):
        month_rng = _rng(seed, profile_id, month)
        seasonal_wave = 1 + seasonality * math.cos(2 * math.pi * (month_index - peak_month) / 12)
        deposits = max(10_000, base_monthly_revenue * seasonal_wave * month_rng.uniform(0.88, 1.12))
        expenses = deposits * cost_ratio * month_rng.uniform(0.90, 1.12)
        buffer_ratio = 0.15 + 0.85 * (1 - traits["liquidity_preference"])
        balance = deposits * buffer_ratio * month_rng.uniform(0.72, 1.28)
        working_pressure = _clip(
            0.55 * traits["liquidity_preference"]
            + 0.25 * seasonality
            + 0.20 * max(0, expenses - deposits) / max(expenses, 1)
        )
        card_share = _clip(0.12 + 0.55 * traits["reward_affinity"] + month_rng.uniform(-0.08, 0.08))
        card_spend = expenses * card_share
        app_sessions = max(
            0,
            round(3 + 35 * traits["digital_autonomy"] + month_rng.gauss(0, 3)),
        )
        advisor_contacts = max(
            0,
            round(0.2 + 5.2 * traits["advisor_preference"] + month_rng.gauss(0, 0.8)),
        )
        coverage = _clip(
            0.12 + 0.76 * traits["risk_protection_preference"] + month_rng.uniform(-0.08, 0.08)
        )
        rewards_earned = card_spend * month_rng.uniform(0.005, 0.018)
        rewards_redeemed = rewards_earned * _clip(
            traits["reward_affinity"] + month_rng.uniform(-0.12, 0.12)
        )
        offers_shown = 1 + int(month_rng.random() < 0.45)
        offer_acceptance_chance = _clip(
            0.15
            + 0.45 * traits["novelty_openness"]
            + 0.25 * traits["reward_affinity"]
            - 0.20 * traits["price_sensitivity"]
        )
        offers_accepted = sum(
            1 for _ in range(offers_shown) if month_rng.random() < offer_acceptance_chance
        )
        overdraft_days = round(12 * working_pressure * month_rng.uniform(0.55, 1.25))
        support_cases = int(month_rng.random() < (0.08 + 0.28 * traits["advisor_preference"]))
        unresolved_cases = int(
            support_cases > 0 and month_rng.random() < (0.05 + 0.18 * working_pressure)
        )
        events.append(
            UsageMonth(
                twin_id=profile_id,
                month=month,
                deposits_brl=round(deposits, 2),
                expenses_brl=round(expenses, 2),
                average_balance_brl=round(balance, 2),
                card_spend_brl=round(card_spend, 2),
                agro_inputs_share=round(month_rng.uniform(0.35, 0.82), 4),
                app_sessions=app_sessions,
                advisor_contacts=advisor_contacts,
                insurance_coverage_ratio=round(coverage, 4),
                rewards_earned_brl=round(rewards_earned, 2),
                rewards_redeemed_brl=round(rewards_redeemed, 2),
                offers_shown=offers_shown,
                offers_accepted=offers_accepted,
                overdraft_days=min(31, overdraft_days),
                support_cases=support_cases,
                unresolved_cases=unresolved_cases,
            )
        )
    return events


def _coefficient_of_variation(values: list[float]) -> float:
    mean = statistics.fmean(values)
    return statistics.pstdev(values) / mean if mean else 0.0


def _evidence(
    item_id: str,
    name: str,
    value: float,
    layer: str,
    source: str,
) -> EvidenceValue:
    return EvidenceValue(
        id=item_id,
        name=name,
        value=round(_clip(value), 4),
        layer=layer,
        source_model=source,
        observation_window="TTM ending 2026-10",
    )


def _infer_profile(
    profile_id: str,
    seed: str,
    anchor: str,
    specification_hash: str,
    events: list[UsageMonth],
    generated_at: datetime,
) -> TwinProfile:
    deposits = [event.deposits_brl for event in events]
    balances = [event.average_balance_brl for event in events]
    expenses = [event.expenses_brl for event in events]
    total_sessions = sum(event.app_sessions for event in events)
    total_advisor_contacts = sum(event.advisor_contacts for event in events)
    total_reward_earned = sum(event.rewards_earned_brl for event in events)
    total_reward_redeemed = sum(event.rewards_redeemed_brl for event in events)
    offers_shown = sum(event.offers_shown for event in events)
    offers_accepted = sum(event.offers_accepted for event in events)
    support_cases = sum(event.support_cases for event in events)
    unresolved_cases = sum(event.unresolved_cases for event in events)

    cash_flow_seasonality = _clip(_coefficient_of_variation(deposits) / 0.6)
    balance_volatility = _clip(_coefficient_of_variation(balances) / 0.7)
    digital_share = total_sessions / max(total_sessions + 5 * total_advisor_contacts, 1)
    insurance_gap = 1 - statistics.fmean(event.insurance_coverage_ratio for event in events)
    reward_rate = total_reward_redeemed / max(total_reward_earned, 1)
    offer_acceptance = offers_accepted / max(offers_shown, 1)
    advisor_rate = _clip(total_advisor_contacts / 60)
    overdraft_rate = _clip(sum(event.overdraft_days for event in events) / 120)
    liquidity_buffer = _clip(statistics.fmean(balances) / max(statistics.fmean(expenses), 1) / 1.5)
    service_friction = _clip(
        0.65 * unresolved_cases / max(support_cases, 1) + 0.35 * support_cases / 12
    )
    working_capital_pressure = _clip(
        0.34 * cash_flow_seasonality
        + 0.28 * balance_volatility
        + 0.23 * overdraft_rate
        + 0.15 * (1 - liquidity_buffer)
    )

    observables = [
        _evidence(
            "O1",
            "cash_flow_seasonality",
            cash_flow_seasonality,
            "synthetic_observable",
            "usage-pipeline-v1",
        ),
        _evidence(
            "O2",
            "balance_volatility",
            balance_volatility,
            "synthetic_observable",
            "usage-pipeline-v1",
        ),
        _evidence(
            "O3",
            "digital_channel_share",
            digital_share,
            "synthetic_observable",
            "usage-pipeline-v1",
        ),
        _evidence(
            "O4",
            "insurance_coverage_gap",
            insurance_gap,
            "synthetic_observable",
            "usage-pipeline-v1",
        ),
        _evidence(
            "O5", "reward_redemption_rate", reward_rate, "synthetic_observable", "usage-pipeline-v1"
        ),
        _evidence(
            "O6",
            "offer_acceptance_rate",
            offer_acceptance,
            "synthetic_observable",
            "usage-pipeline-v1",
        ),
        _evidence(
            "O7", "advisor_contact_rate", advisor_rate, "synthetic_observable", "usage-pipeline-v1"
        ),
        _evidence(
            "O8", "overdraft_pressure", overdraft_rate, "synthetic_observable", "usage-pipeline-v1"
        ),
        _evidence(
            "O9", "liquidity_buffer", liquidity_buffer, "synthetic_observable", "usage-pipeline-v1"
        ),
        _evidence(
            "O10", "service_friction", service_friction, "synthetic_observable", "usage-pipeline-v1"
        ),
    ]
    derived = [
        _evidence(
            "D1",
            "working_capital_pressure",
            working_capital_pressure,
            "derived",
            "feature-formulas-v1",
        ),
    ]

    trait_specs = [
        (
            "H1",
            "liquidity_preference",
            _clip(0.62 * working_capital_pressure + 0.38 * cash_flow_seasonality),
            ["D1", "O1", "O8"],
        ),
        (
            "H2",
            "price_sensitivity",
            _clip(0.55 * (1 - offer_acceptance) + 0.30 * overdraft_rate + 0.15 * (1 - reward_rate)),
            ["O6", "O8", "O5"],
        ),
        ("H3", "digital_autonomy", digital_share, ["O3"]),
        (
            "H4",
            "risk_protection_preference",
            _clip(
                0.62 * (1 - insurance_gap) + 0.23 * cash_flow_seasonality + 0.15 * service_friction
            ),
            ["O4", "O1", "O10"],
        ),
        (
            "H5",
            "reward_affinity",
            _clip(0.72 * reward_rate + 0.28 * offer_acceptance),
            ["O5", "O6"],
        ),
        (
            "H6",
            "advisor_preference",
            _clip(0.74 * advisor_rate + 0.26 * (1 - digital_share)),
            ["O7", "O3"],
        ),
        (
            "H7",
            "novelty_openness",
            _clip(0.58 * offer_acceptance + 0.42 * digital_share),
            ["O6", "O3"],
        ),
        (
            "H8",
            "reversibility_preference",
            _clip(
                0.46 * working_capital_pressure
                + 0.34 * (1 - offer_acceptance)
                + 0.20 * service_friction
            ),
            ["D1", "O6", "O10"],
        ),
    ]
    hypotheses = [
        TraitHypothesis(
            id=item_id,
            name=name,
            score=round(score, 4),
            confidence=round(_clip(0.72 + 0.07 * len(evidence_ids)), 4),
            evidence_ids=evidence_ids,
            method_version=METHOD_VERSION,
        )
        for item_id, name, score, evidence_ids in trait_specs
    ]
    current_products = ["checking_account", "debit_card"]
    if insurance_gap < 0.5:
        current_products.append("rural_insurance")
    if statistics.fmean(event.card_spend_brl for event in events) > 25_000:
        current_products.append("credit_card")

    return TwinProfile(
        id=profile_id,
        behavioral_anchor=anchor,
        population_seed=seed,
        profile_version=PROFILE_VERSION,
        specification_hash=specification_hash,
        observables=observables,
        derived=derived,
        hypotheses=hypotheses,
        current_products=current_products,
        unknowns=["household_assets", "off_bank_relationships", "future_weather"],
        generated_at=generated_at,
    )


def profile_digest(profiles: list[TwinProfile]) -> str:
    canonical = [profile.model_dump(mode="json", exclude={"generated_at"}) for profile in profiles]
    return hashlib.sha256(_canonical_json(canonical).encode()).hexdigest()


def artifact_digest(
    profiles: list[TwinProfile],
    events: list[UsageMonth],
    audit_sidecar: list[AuditRecord],
    *,
    count: int,
    seed: str,
    profile_version: str,
    specification_hash: str,
    generator_version: str,
    anchor_counts: dict[str, int],
) -> str:
    material = {
        "profiles": [
            profile.model_dump(mode="json", exclude={"generated_at"}) for profile in profiles
        ],
        "events": [event.model_dump(mode="json") for event in events],
        "audit_sidecar": [record.model_dump(mode="json") for record in audit_sidecar],
        "metadata": {
            "count": count,
            "seed": seed,
            "profile_version": profile_version,
            "specification_hash": specification_hash,
            "generator_version": generator_version,
            "anchor_counts": anchor_counts,
        },
    }
    return hashlib.sha256(_canonical_json(material).encode()).hexdigest()


def generate_population(count: int = 120, seed: str = "agro-demo-2026") -> PopulationBundle:
    if count < len(ANCHOR_PRIORS):
        raise ValueError(f"Population must contain at least {len(ANCHOR_PRIORS)} profiles")
    if count > 500:
        raise ValueError("Population is limited to 500 profiles in this non-production demo")

    specification_hash = _specification_hash()
    population_key = (
        hashlib.sha256(f"{specification_hash}|{seed}|{count}".encode()).hexdigest()[:12].upper()
    )
    generated_at = datetime(2026, 11, 3, 19, 36, tzinfo=UTC)
    profiles: list[TwinProfile] = []
    events: list[UsageMonth] = []
    audit_sidecar: list[AuditRecord] = []
    latent_traits_by_id: dict[str, dict[str, float]] = {}

    for index in range(count):
        anchor = _anchor_for_index(index)
        profile_id = f"AGRO-{population_key}-{index + 1:04d}"
        traits = _latent_traits(seed, profile_id, anchor)
        profile_events = _generate_usage(seed, profile_id, traits)
        profile = _infer_profile(
            profile_id,
            seed,
            anchor,
            specification_hash,
            profile_events,
            generated_at,
        )
        profiles.append(profile)
        events.extend(profile_events)
        latent_traits_by_id[profile_id] = traits

    profiles.sort(key=lambda profile: profile.id)
    for anchor in ANCHOR_PRIORS:
        anchor_ids = [profile.id for profile in profiles if profile.behavioral_anchor == anchor]
        anchor_ids.sort(
            key=lambda profile_id: hmac.new(
                seed.encode(),
                f"audit-group|{profile_id}".encode(),
                hashlib.sha256,
            ).digest()
        )
        for position, profile_id in enumerate(anchor_ids):
            traits = latent_traits_by_id[profile_id]
            audit_sidecar.append(
                AuditRecord(
                    twin_id=profile_id,
                    latent_traits={name: round(value, 4) for name, value in traits.items()},
                    synthetic_audit_group="A" if position % 2 == 0 else "B",
                    generator_version=GENERATOR_VERSION,
                )
            )
    events.sort(key=lambda event: (event.twin_id, event.month))
    audit_sidecar.sort(key=lambda item: item.twin_id)
    anchor_counts = Counter(profile.behavioral_anchor for profile in profiles)
    sorted_anchor_counts = dict(sorted(anchor_counts.items()))
    manifest = PopulationManifest(
        count=count,
        seed=seed,
        profile_version=PROFILE_VERSION,
        specification_hash=specification_hash,
        generator_version=GENERATOR_VERSION,
        profile_digest=profile_digest(profiles),
        artifact_digest=artifact_digest(
            profiles,
            events,
            audit_sidecar,
            count=count,
            seed=seed,
            profile_version=PROFILE_VERSION,
            specification_hash=specification_hash,
            generator_version=GENERATOR_VERSION,
            anchor_counts=sorted_anchor_counts,
        ),
        generated_at=generated_at,
        anchor_counts=sorted_anchor_counts,
    )
    return PopulationBundle(
        manifest=manifest,
        profiles=profiles,
        events=events,
        audit_sidecar=audit_sidecar,
    )


def group_events(events: list[UsageMonth]) -> dict[str, list[UsageMonth]]:
    grouped: dict[str, list[UsageMonth]] = defaultdict(list)
    for event in events:
        grouped[event.twin_id].append(event)
    return dict(grouped)
