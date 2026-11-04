import pytest
from pydantic import ValidationError

from financial_twins.models import SimulateRequest
from financial_twins.population import generate_population
from financial_twins.simulation import default_product_variants, simulate_population


def test_simulation_is_paired_across_all_variants() -> None:
    bundle = generate_population(24, "paired")
    variants = default_product_variants()
    result = simulate_population(bundle.profiles, bundle.manifest.profile_digest, variants)

    assert len(result.decisions) == len(bundle.profiles) * len(variants)
    assert len(result.summaries) == len(variants)
    for profile in bundle.profiles:
        profile_decisions = [
            decision for decision in result.decisions if decision.twin_id == profile.id
        ]
        assert {decision.variant_id for decision in profile_decisions} == {
            variant.id for variant in variants
        }


def test_standard_panel_exercises_all_decision_states() -> None:
    bundle = generate_population(120, "agro-demo-2026")
    result = simulate_population(
        bundle.profiles,
        bundle.manifest.profile_digest,
        default_product_variants(),
    )

    for summary in result.summaries:
        assert all(count > 0 for count in summary.decision_counts.values())


def test_reason_codes_only_reference_profile_evidence() -> None:
    bundle = generate_population(24, "reasons")
    result = simulate_population(bundle.profiles, bundle.manifest.profile_digest)
    profiles = {profile.id: profile for profile in bundle.profiles}

    for decision in result.decisions:
        allowed = profiles[decision.twin_id].evidence_ids() | {
            trait.id for trait in profiles[decision.twin_id].hypotheses
        }
        assert all(
            evidence_id in allowed
            for reason in decision.reasons
            for evidence_id in reason.evidence_ids
        )


def test_duplicate_variant_ids_are_rejected() -> None:
    variants = default_product_variants()
    duplicate = variants[0].model_copy(update={"monthly_fee_brl": 99})

    with pytest.raises(ValidationError, match="unique"):
        SimulateRequest(population_size=8, variants=[variants[0], duplicate])


def test_runs_are_unique_but_scenario_hash_is_stable() -> None:
    bundle = generate_population(8, "run-identity")
    first = simulate_population(bundle.profiles, bundle.manifest.profile_digest)
    second = simulate_population(bundle.profiles, bundle.manifest.profile_digest)

    assert first.scenario_hash == second.scenario_hash
    assert first.run_id != second.run_id


def test_interactive_foundry_workload_is_bounded() -> None:
    with pytest.raises(ValidationError, match="24"):
        SimulateRequest(engine="foundry", population_size=120)
