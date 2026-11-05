from __future__ import annotations

import asyncio

from financial_twins.foundry_engine import FoundryTwinEngine
from financial_twins.population import generate_population
from financial_twins.simulation import default_product_variants


async def main() -> None:
    bundle = generate_population(8, "foundry-smoke")
    engine = FoundryTwinEngine()
    try:
        decision = await engine.evaluate(
            bundle.profiles[0],
            default_product_variants()[0],
        )
    finally:
        await engine.close()
    print(decision.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
