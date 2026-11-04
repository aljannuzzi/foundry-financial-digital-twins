from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from uuid import uuid4

from azure.core.exceptions import AzureError
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .errors import (
    ClientInputError,
    FoundryProviderError,
    FoundryResponseError,
    SimulationConfigurationError,
)
from .evaluation import evaluate_population
from .models import GeneratePopulationRequest, SimulateRequest
from .persistence import AzureTwinStore
from .population import generate_population
from .service import SimulationService
from .simulation import default_product_variants, simulate_population

if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    from azure.monitor.opentelemetry import configure_azure_monitor

    configure_azure_monitor()

app = FastAPI(
    title="Foundry Financial Digital Twins",
    version="0.1.0",
    description="Synthetic Agro scenario laboratory. Not a forecasting or decisioning system.",
)
service = SimulationService()
logger = logging.getLogger(__name__)


def _service_error(message: str, exc: BaseException) -> HTTPException:
    correlation_id = uuid4().hex[:12]
    logger.exception("%s correlation_id=%s", message, correlation_id, exc_info=exc)
    return HTTPException(
        status_code=503,
        detail=f"{message} Correlation ID: {correlation_id}",
    )


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "foundry-financial-digital-twins"}


@app.get("/api/config")
def config() -> dict:
    return {
        "defaultPopulation": int(os.getenv("DEFAULT_POPULATION_SIZE", "120")),
        "livePopulation": 24,
        "scalePopulation": 500,
        "defaultSeed": os.getenv("DEFAULT_POPULATION_SEED", "agro-demo-2026"),
        "foundryConfigured": bool(os.getenv("FOUNDRY_PROJECT_ENDPOINT")),
        "variants": [variant.model_dump(mode="json") for variant in default_product_variants()],
    }


@app.post("/api/populations/generate")
def generate(request: GeneratePopulationRequest) -> dict:
    bundle = generate_population(request.count, request.seed)
    report = evaluate_population(bundle)
    return {
        "manifest": bundle.manifest.model_dump(mode="json"),
        "profiles": [profile.model_dump(mode="json") for profile in bundle.profiles],
        "evaluation": report.model_dump(mode="json"),
    }


@app.get("/api/demo")
def demo() -> dict:
    if os.getenv("COSMOS_ENDPOINT"):
        try:
            with AzureTwinStore.from_environment() as store:
                manifest, profiles, evaluation = store.load_latest_population()
        except (AzureError, RuntimeError, ValueError) as exc:
            raise _service_error(
                "The published demo population is temporarily unavailable.",
                exc,
            ) from exc
    else:
        population_size = int(os.getenv("DEFAULT_POPULATION_SIZE", "120"))
        seed = os.getenv("DEFAULT_POPULATION_SEED", "agro-demo-2026")
        bundle = generate_population(population_size, seed)
        manifest = bundle.manifest.model_dump(mode="json")
        profiles = bundle.profiles
        evaluation = evaluate_population(bundle).model_dump(mode="json")
    result = simulate_population(profiles, manifest["profile_digest"])
    return {
        "manifest": manifest,
        "profiles": [profile.model_dump(mode="json") for profile in profiles],
        "simulation": result.model_dump(mode="json"),
        "evaluation": evaluation,
        "foundryConfigured": bool(
            os.getenv("FOUNDRY_PROJECT_ENDPOINT") and os.getenv("FOUNDRY_CUSTOMER_TWIN_AGENT")
        ),
        "livePopulation": 24,
        "standardPopulation": 120,
    }


@app.post("/api/simulations")
async def simulate(request: SimulateRequest) -> dict:
    try:
        async with asyncio.timeout(300):
            bundle, result = await service.run(
                population_size=request.population_size,
                seed=request.seed,
                engine=request.engine,
                variants=request.variants,
            )
    except TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail="The interactive simulation exceeded its five-minute deadline.",
        ) from exc
    except ClientInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SimulationConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (FoundryProviderError, FoundryResponseError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if os.getenv("COSMOS_ENDPOINT"):
        try:

            def persist() -> None:
                with AzureTwinStore.from_environment() as store:
                    store.save_population(bundle, canonical=False)
                    store.save_simulation(result, bundle.manifest)

            await asyncio.to_thread(persist)
        except (AzureError, RuntimeError, ValueError) as exc:
            raise _service_error(
                "The simulation completed but could not be persisted.",
                exc,
            ) from exc
    return {
        "manifest": bundle.manifest.model_dump(mode="json"),
        "profiles": [profile.model_dump(mode="json") for profile in bundle.profiles],
        "simulation": result.model_dump(mode="json"),
        "evaluation": evaluate_population(bundle).model_dump(mode="json"),
    }


STATIC_DIR = Path(os.getenv("STATIC_DIR", Path.cwd() / "ui" / "dist")).resolve()
if STATIC_DIR.exists():
    assets = STATIC_DIR / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str) -> FileResponse:
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        candidate = (STATIC_DIR / full_path).resolve()
        if not candidate.is_relative_to(STATIC_DIR):
            raise HTTPException(status_code=404, detail="File not found")
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
