from collections import Counter, defaultdict
from copy import deepcopy

from financial_twins.evaluation import evaluate_population
from financial_twins.population import ANCHOR_PRIORS, generate_population


def test_population_is_reproducible_and_diverse() -> None:
    first = generate_population(120, "agro-demo-2026")
    second = generate_population(120, "agro-demo-2026")

    assert first.manifest.profile_digest == second.manifest.profile_digest
    assert len(first.profiles) == 120
    assert len(first.events) == 120 * 12
    assert set(first.manifest.anchor_counts) == set(ANCHOR_PRIORS)
    assert all(count == 15 for count in first.manifest.anchor_counts.values())

    report = evaluate_population(first)
    assert report.passed, report.model_dump()


def test_audit_fields_never_enter_agent_payload() -> None:
    bundle = generate_population(24, "audit-isolation")
    for profile in bundle.profiles:
        payload = profile.agent_payload()
        assert "latent_traits" not in payload
        assert "synthetic_audit_group" not in payload
        assert profile.population_seed not in str(payload)


def test_every_hypothesis_has_valid_evidence() -> None:
    bundle = generate_population(24, "evidence")
    for profile in bundle.profiles:
        available = profile.evidence_ids()
        for hypothesis in profile.hypotheses:
            assert set(hypothesis.evidence_ids) <= available


def test_validation_rejects_profile_mutation() -> None:
    bundle = generate_population(24, "integrity")
    corrupted = deepcopy(bundle)
    corrupted.profiles[0].hypotheses[0].score = 0.01

    report = evaluate_population(corrupted)

    assert report.passed is False
    assert report.manifest_digest_matches is False
    assert report.checks["population_is_reproducible"] is False


def test_validation_rejects_event_audit_and_manifest_mutation() -> None:
    bundle = generate_population(24, "artifact-integrity")

    corrupted_event = deepcopy(bundle)
    corrupted_event.events[0].deposits_brl += 1
    assert evaluate_population(corrupted_event).passed is False

    corrupted_audit = deepcopy(bundle)
    corrupted_audit.audit_sidecar[0].latent_traits["price_sensitivity"] = 0.01
    assert evaluate_population(corrupted_audit).passed is False

    corrupted_manifest = deepcopy(bundle)
    corrupted_manifest.manifest.generator_version = "tampered"
    assert evaluate_population(corrupted_manifest).passed is False


def test_validation_rejects_duplicate_or_missing_months() -> None:
    bundle = generate_population(24, "event-integrity")
    corrupted = deepcopy(bundle)
    corrupted.events[1].month = corrupted.events[0].month

    report = evaluate_population(corrupted)

    assert report.passed is False
    assert report.event_integrity_violations > 0


def test_validation_returns_failure_for_structurally_malformed_bundle() -> None:
    bundle = generate_population(8, "malformed")
    malformed = deepcopy(bundle)
    malformed.profiles = malformed.profiles[:1]
    malformed.profiles[0].hypotheses = malformed.profiles[0].hypotheses[:2]

    report = evaluate_population(malformed)

    assert report.passed is False
    assert report.structural_violations > 0


def test_audit_groups_are_balanced_within_each_anchor() -> None:
    bundle = generate_population(120, "audit-balance")
    anchors = {profile.id: profile.behavioral_anchor for profile in bundle.profiles}
    groups: dict[str, Counter] = defaultdict(Counter)
    for record in bundle.audit_sidecar:
        groups[anchors[record.twin_id]][record.synthetic_audit_group] += 1

    assert all(abs(values["A"] - values["B"]) <= 1 for values in groups.values())
    assert all(set(values) == {"A", "B"} for values in groups.values())


def test_different_seeds_produce_disjoint_profile_ids() -> None:
    first = generate_population(24, "seed-a")
    second = generate_population(24, "seed-b")

    assert {profile.id for profile in first.profiles}.isdisjoint(
        profile.id for profile in second.profiles
    )
