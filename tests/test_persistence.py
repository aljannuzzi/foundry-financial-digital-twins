from __future__ import annotations

from financial_twins.persistence import AzureTwinStore
from financial_twins.population import generate_population


class FakeContainer:
    def __init__(self, items: list[dict]) -> None:
        self.items = items

    def query_items(self, **kwargs):
        if "populationManifest" in kwargs["query"]:
            return self.items
        population_id = kwargs["parameters"][0]["value"]
        return [item for item in self.items if item.get("populationId") == population_id]


def test_cosmos_system_fields_are_ignored_when_loading_population() -> None:
    bundle = generate_population(8, "cosmos-metadata")
    manifest = bundle.manifest.model_dump(mode="json")
    manifest.update(
        {
            "id": f"population-{bundle.manifest.profile_digest}",
            "documentType": "populationManifest",
            "status": "complete",
            "publishedAt": "2026-11-04T12:00:00+00:00",
            "evaluation": {"passed": True},
            "_etag": "manifest-etag",
        }
    )
    profiles = []
    for profile in bundle.profiles:
        item = profile.model_dump(mode="json")
        item.update(
            {
                "documentType": "customerTwin",
                "populationId": bundle.manifest.artifact_digest,
                "_etag": "profile-etag",
                "_rid": "rid",
            }
        )
        profiles.append(item)
    store = AzureTwinStore.__new__(AzureTwinStore)
    store._runs = FakeContainer([manifest])
    store._profiles = FakeContainer(profiles)

    loaded_manifest, loaded_profiles, evaluation = store.load_latest_population()

    assert loaded_manifest["profile_digest"] == bundle.manifest.profile_digest
    assert len(loaded_profiles) == 8
    assert evaluation["passed"] is True
