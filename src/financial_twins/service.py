from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from .errors import ClientInputError, FoundryProviderError, FoundryResponseError
from .foundry_engine import FoundryTwinEngine
from .models import ProductVariant, SimulationResult, TwinDecision, TwinProfile
from .population import generate_population
from .simulation import (
    DISCLAIMER,
    default_product_variants,
    scenario_hash,
    simulate_population,
    summarize_decisions,
    validate_variants,
)

FOUNDRY_GLOBAL_LIMIT = asyncio.Semaphore(8)


class SimulationService:
    async def simulate_foundry(
        self,
        profiles: list[TwinProfile],
        population_digest: str,
        variants: list[ProductVariant] | None = None,
        concurrency: int = 8,
    ) -> SimulationResult:
        selected_variants = variants or default_product_variants()
        validate_variants(selected_variants)
        engine = FoundryTwinEngine()
        work = [(profile, variant) for variant in selected_variants for profile in profiles]
        decisions: list[TwinDecision] = []
        try:
            for start in range(0, len(work), concurrency):
                batch = work[start : start + concurrency]

                async def evaluate(
                    profile: TwinProfile,
                    variant: ProductVariant,
                ) -> TwinDecision:
                    async with FOUNDRY_GLOBAL_LIMIT:
                        for attempt in range(3):
                            try:
                                return await engine.evaluate(profile, variant)
                            except FoundryResponseError:
                                if attempt == 2:
                                    raise
                        raise FoundryResponseError("Customer-twin response retries were exhausted")

                outcomes = await asyncio.gather(
                    *(evaluate(profile, variant) for profile, variant in batch),
                    return_exceptions=True,
                )
                errors = [outcome for outcome in outcomes if isinstance(outcome, BaseException)]
                if errors:
                    first = errors[0]
                    if isinstance(first, (FoundryProviderError, FoundryResponseError)):
                        raise first
                    raise FoundryProviderError(
                        "A customer-twin evaluation failed unexpectedly"
                    ) from first
                decisions.extend(
                    outcome for outcome in outcomes if isinstance(outcome, TwinDecision)
                )
        finally:
            await engine.close()

        scenario = scenario_hash(
            population_digest,
            selected_variants,
            "foundry",
            engine.agent_version,
            engine.model_deployment,
            engine.agent_name,
            engine.invocation_mode,
        )
        return SimulationResult(
            run_id=f"run-{scenario[:8]}-{uuid4().hex[:12]}",
            scenario_hash=scenario,
            engine="foundry",
            population_digest=population_digest,
            model_deployment=engine.model_deployment,
            agent_name=engine.agent_name,
            agent_version=engine.agent_version,
            invocation_mode=engine.invocation_mode,
            created_at=datetime.now(UTC),
            variants=selected_variants,
            decisions=decisions,
            summaries=summarize_decisions(profiles, selected_variants, decisions),
            disclaimer=DISCLAIMER,
        )

    async def run(
        self,
        population_size: int,
        seed: str,
        engine: str,
        variants: list[ProductVariant] | None = None,
    ) -> tuple:
        bundle = generate_population(population_size, seed)
        if engine == "deterministic":
            result = simulate_population(
                bundle.profiles,
                bundle.manifest.profile_digest,
                variants,
            )
        elif engine == "foundry":
            result = await self.simulate_foundry(
                bundle.profiles,
                bundle.manifest.profile_digest,
                variants,
            )
        else:
            raise ClientInputError(f"Unsupported engine: {engine}")
        return bundle, result
