from __future__ import annotations

import json
import os
import time
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Self

from azure.core.exceptions import ResourceExistsError
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from .errors import PersistenceError
from .evaluation import evaluate_population
from .models import (
    PopulationBundle,
    PopulationManifest,
    SimulationResult,
    TwinProfile,
)
from .population import profile_digest


class AzureTwinStore:
    def __init__(
        self,
        cosmos_endpoint: str,
        database_name: str,
        storage_account_url: str | None = None,
        raw_events_container: str = "raw-events",
    ) -> None:
        self._credential = DefaultAzureCredential()
        self._client = CosmosClient(cosmos_endpoint, credential=self._credential)
        database = self._client.get_database_client(database_name)
        self._profiles = database.get_container_client("customerTwins")
        self._runs = database.get_container_client("simulationRuns")
        self._decisions = database.get_container_client("twinDecisions")
        self._blob = (
            BlobServiceClient(storage_account_url, credential=self._credential)
            if storage_account_url
            else None
        )
        self._raw_events_container = raw_events_container

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        if self._blob:
            self._blob.close()
        self._client.close()
        self._credential.close()

    @classmethod
    def from_environment(cls) -> AzureTwinStore:
        endpoint = os.environ.get("COSMOS_ENDPOINT")
        if not endpoint:
            raise ValueError("COSMOS_ENDPOINT is required for Azure persistence")
        return cls(
            cosmos_endpoint=endpoint,
            database_name=os.getenv("COSMOS_DATABASE", "financial-twins"),
            storage_account_url=os.environ.get("STORAGE_ACCOUNT_URL"),
            raw_events_container=os.getenv("RAW_EVENTS_CONTAINER", "raw-events"),
        )

    def save_population(
        self,
        bundle: PopulationBundle,
        *,
        canonical: bool = True,
    ) -> None:
        evaluation = evaluate_population(bundle)
        if not evaluation.passed:
            raise ValueError("Population validation failed; publication was blocked")
        if not self._blob:
            raise ValueError("STORAGE_ACCOUNT_URL is required for Azure population publication")
        digest = bundle.manifest.artifact_digest
        container = self._blob.get_container_client(self._raw_events_container)
        events_payload = "\n".join(
            json.dumps(event.model_dump(mode="json"), separators=(",", ":"))
            for event in bundle.events
        )
        audit_payload = "\n".join(
            json.dumps(record.model_dump(mode="json"), separators=(",", ":"))
            for record in bundle.audit_sidecar
        )
        for name, payload in (
            ("events.jsonl", events_payload),
            ("audit-sidecar.jsonl", audit_payload),
            ("manifest.json", bundle.manifest.model_dump_json(indent=2)),
        ):
            with suppress(ResourceExistsError):
                container.upload_blob(
                    f"{digest}/{name}",
                    payload,
                    overwrite=False,
                )
        for profile in bundle.profiles:
            item = profile.model_dump(mode="json")
            item["documentType"] = "customerTwin"
            item["populationId"] = digest
            self._profiles.upsert_item(item)
        manifest = bundle.manifest.model_dump(mode="json")
        manifest["id"] = f"population-{digest}" if canonical else f"simulation-population-{digest}"
        manifest["documentType"] = (
            "populationManifest" if canonical else "simulationPopulationManifest"
        )
        manifest["status"] = "complete" if canonical else "simulation-only"
        manifest["publishedAt"] = datetime.now(UTC).isoformat()
        manifest["evaluation"] = evaluation.model_dump(mode="json")
        self._runs.upsert_item(manifest)

    def save_simulation(
        self,
        result: SimulationResult,
        population_manifest: PopulationManifest,
    ) -> None:
        run = result.model_dump(mode="json", exclude={"decisions"})
        run["id"] = result.run_id
        run["documentType"] = "simulationRun"
        run["status"] = "pending"
        run["populationManifestId"] = f"simulation-population-{population_manifest.artifact_digest}"
        run["populationManifest"] = population_manifest.model_dump(mode="json")
        self._runs.upsert_item(run)
        try:
            for decision in result.decisions:
                item = decision.model_dump(mode="json")
                item["id"] = f"{result.run_id}:{decision.variant_id}:{decision.twin_id}"
                item["runId"] = result.run_id
                item["documentType"] = "twinDecision"
                self._decisions.upsert_item(item)
        except Exception as exc:
            run["status"] = "failed"
            run["failedAt"] = datetime.now(UTC).isoformat()
            try:
                self._runs.upsert_item(run)
            except Exception as status_exc:
                raise PersistenceError(
                    "Simulation persistence failed and its failed state could not be recorded"
                ) from status_exc
            raise PersistenceError("Simulation decision persistence failed") from exc
        run["status"] = "complete"
        run["publishedAt"] = datetime.now(UTC).isoformat()
        self._runs.upsert_item(run)

    def get_profile(self, twin_id: str) -> TwinProfile:
        item = self._profiles.read_item(item=twin_id, partition_key=twin_id)
        return TwinProfile.model_validate({name: item[name] for name in TwinProfile.model_fields})

    def load_latest_population(self) -> tuple[dict, list[TwinProfile], dict]:
        manifests = list(
            self._runs.query_items(
                query=(
                    "SELECT TOP 5 * FROM c WHERE c.documentType = "
                    "'populationManifest' AND c.status = 'complete' "
                    "ORDER BY c.publishedAt DESC"
                ),
                enable_cross_partition_query=True,
            )
        )
        if not manifests:
            raise RuntimeError("The Azure profile pipeline has not published a population yet")
        for stored_manifest in manifests:
            evaluation = stored_manifest["evaluation"]
            manifest_model = PopulationManifest.model_validate(
                {name: stored_manifest[name] for name in PopulationManifest.model_fields}
            )
            for attempt in range(3):
                profiles: list[TwinProfile] = []
                for item in self._profiles.query_items(
                    query=(
                        "SELECT * FROM c WHERE c.documentType = 'customerTwin' "
                        "AND c.populationId = @populationId"
                    ),
                    parameters=[
                        {
                            "name": "@populationId",
                            "value": manifest_model.artifact_digest,
                        }
                    ],
                    enable_cross_partition_query=True,
                ):
                    profiles.append(
                        TwinProfile.model_validate(
                            {name: item[name] for name in TwinProfile.model_fields}
                        )
                    )
                profiles.sort(key=lambda profile: profile.id)
                if (
                    len(profiles) == manifest_model.count
                    and profile_digest(profiles) == manifest_model.profile_digest
                ):
                    return (
                        manifest_model.model_dump(mode="json"),
                        profiles,
                        evaluation,
                    )
                if attempt < 2:
                    time.sleep(0.5)
        raise RuntimeError("No complete and internally consistent population was found")


def write_local_bundle(bundle: PopulationBundle, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(
        bundle.manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "profiles.jsonl").write_text(
        "\n".join(profile.model_dump_json() for profile in bundle.profiles) + "\n",
        encoding="utf-8",
    )
    (output_dir / "events.jsonl").write_text(
        "\n".join(event.model_dump_json() for event in bundle.events) + "\n",
        encoding="utf-8",
    )
    (output_dir / "audit-sidecar.jsonl").write_text(
        "\n".join(record.model_dump_json() for record in bundle.audit_sidecar) + "\n",
        encoding="utf-8",
    )
