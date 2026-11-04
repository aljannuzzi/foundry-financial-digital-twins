from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict

from pydantic import BaseModel, ConfigDict

from .models import PopulationBundle
from .population import (
    ANCHOR_PRIORS,
    MONTHS,
    artifact_digest,
    generate_population,
    profile_digest,
)


class EvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool
    population_count: int
    duplicate_profiles: int
    anchors_covered: int
    evidence_violations: int
    bounds_violations: int
    audit_leakage_violations: int
    event_integrity_violations: int
    audit_integrity_violations: int
    manifest_digest_matches: bool
    artifact_digest_matches: bool
    structural_violations: int
    minimum_pairwise_trait_distance: float
    mean_pairwise_trait_distance: float
    reproducible: bool
    checks: dict[str, bool]


def _trait_vector(profile) -> list[float]:
    return [trait.score for trait in sorted(profile.hypotheses, key=lambda item: item.id)]


def _profile_fingerprint(profile) -> str:
    payload = profile.model_dump(
        mode="json",
        exclude={"id", "population_seed", "generated_at"},
    )
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def evaluate_population(bundle: PopulationBundle) -> EvaluationReport:
    fingerprints = Counter(_profile_fingerprint(profile) for profile in bundle.profiles)
    duplicate_profiles = sum(count - 1 for count in fingerprints.values() if count > 1)
    evidence_violations = 0
    bounds_violations = 0
    audit_leakage_violations = 0
    event_integrity_violations = 0
    audit_integrity_violations = 0
    structural_violations = 0
    pairwise_distances: list[float] = []
    profile_ids = {profile.id for profile in bundle.profiles}

    for profile in bundle.profiles:
        structural_violations += int(len(profile.hypotheses) != 8)
        structural_violations += int(
            len({trait.id for trait in profile.hypotheses}) != len(profile.hypotheses)
        )
        available = profile.evidence_ids()
        for trait in profile.hypotheses:
            evidence_violations += sum(
                evidence_id not in available for evidence_id in trait.evidence_ids
            )
            bounds_violations += int(not 0 <= trait.score <= 1)
            bounds_violations += int(not 0 <= trait.confidence <= 1)
        serialized = json.dumps(profile.agent_payload(), sort_keys=True)
        audit_leakage_violations += int("synthetic_audit_group" in serialized)
        audit_leakage_violations += int("latent_traits" in serialized)

    vectors = [_trait_vector(profile) for profile in bundle.profiles]
    for left_index, left in enumerate(vectors):
        for right in vectors[left_index + 1 :]:
            if len(left) != len(right):
                structural_violations += 1
            else:
                pairwise_distances.append(
                    math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right, strict=True)))
                )
    event_counts = Counter(event.twin_id for event in bundle.events)
    event_keys = Counter((event.twin_id, event.month) for event in bundle.events)
    event_integrity_violations += sum(count != len(MONTHS) for count in event_counts.values())
    event_integrity_violations += sum(count != 1 for count in event_keys.values())
    event_integrity_violations += len(set(event_counts) - profile_ids)
    event_integrity_violations += len(profile_ids - set(event_counts))
    for profile_id in profile_ids:
        actual_months = {month for twin_id, month in event_keys if twin_id == profile_id}
        event_integrity_violations += int(actual_months != set(MONTHS))

    audit_counts = Counter(record.twin_id for record in bundle.audit_sidecar)
    audit_integrity_violations += sum(count != 1 for count in audit_counts.values())
    audit_integrity_violations += len(set(audit_counts) - profile_ids)
    audit_integrity_violations += len(profile_ids - set(audit_counts))
    anchors = {profile.id: profile.behavioral_anchor for profile in bundle.profiles}
    groups_by_anchor: dict[str, Counter] = defaultdict(Counter)
    for record in bundle.audit_sidecar:
        if record.twin_id in anchors:
            groups_by_anchor[anchors[record.twin_id]][record.synthetic_audit_group] += 1
    audit_integrity_violations += sum(
        abs(groups["A"] - groups["B"]) > 1 for groups in groups_by_anchor.values()
    )

    actual_digest = profile_digest(bundle.profiles)
    manifest_digest_matches = actual_digest == bundle.manifest.profile_digest
    actual_anchor_counts = Counter(profile.behavioral_anchor for profile in bundle.profiles)
    sorted_anchor_counts = dict(sorted(actual_anchor_counts.items()))
    actual_artifact_digest = artifact_digest(
        bundle.profiles,
        bundle.events,
        bundle.audit_sidecar,
        count=len(bundle.profiles),
        seed=bundle.manifest.seed,
        profile_version=bundle.manifest.profile_version,
        specification_hash=bundle.manifest.specification_hash,
        generator_version=bundle.manifest.generator_version,
        anchor_counts=sorted_anchor_counts,
    )
    artifact_digest_matches = actual_artifact_digest == bundle.manifest.artifact_digest
    rerun_matches = False
    if len(ANCHOR_PRIORS) <= bundle.manifest.count <= 500:
        try:
            rerun = generate_population(
                bundle.manifest.count,
                bundle.manifest.seed,
            )
            rerun_matches = (
                rerun.manifest.profile_digest == actual_digest
                and rerun.manifest.artifact_digest == actual_artifact_digest
            )
        except ValueError:
            structural_violations += 1
    reproducible = manifest_digest_matches and artifact_digest_matches and rerun_matches
    anchors_covered = len(actual_anchor_counts)
    anchor_manifest_matches = sorted_anchor_counts == bundle.manifest.anchor_counts
    minimum_distance = min(pairwise_distances, default=0.0)
    mean_distance = sum(pairwise_distances) / len(pairwise_distances) if pairwise_distances else 0.0
    checks = {
        "count_matches": len(bundle.profiles) == bundle.manifest.count,
        "structure_is_valid": structural_violations == 0,
        "manifest_digest_matches": manifest_digest_matches,
        "artifact_digest_matches": artifact_digest_matches,
        "anchor_manifest_matches": anchor_manifest_matches,
        "no_duplicates": duplicate_profiles == 0,
        "all_anchors_covered": anchors_covered == len(ANCHOR_PRIORS),
        "evidence_is_valid": evidence_violations == 0,
        "values_are_bounded": bounds_violations == 0,
        "audit_sidecar_is_isolated": audit_leakage_violations == 0,
        "events_are_complete": event_integrity_violations == 0,
        "audit_sidecar_is_balanced": audit_integrity_violations == 0,
        "population_is_reproducible": reproducible,
        "population_is_diverse": minimum_distance > 0.01 and mean_distance > 0.15,
    }
    return EvaluationReport(
        passed=all(checks.values()),
        population_count=len(bundle.profiles),
        duplicate_profiles=duplicate_profiles,
        anchors_covered=anchors_covered,
        evidence_violations=evidence_violations,
        bounds_violations=bounds_violations,
        audit_leakage_violations=audit_leakage_violations,
        event_integrity_violations=event_integrity_violations,
        audit_integrity_violations=audit_integrity_violations,
        manifest_digest_matches=manifest_digest_matches,
        artifact_digest_matches=artifact_digest_matches,
        structural_violations=structural_violations,
        minimum_pairwise_trait_distance=round(minimum_distance, 4),
        mean_pairwise_trait_distance=round(mean_distance, 4),
        reproducible=reproducible,
        checks=checks,
    )
