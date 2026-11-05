from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .agents import provision_agents
from .evaluation import evaluate_population
from .persistence import AzureTwinStore, write_local_bundle
from .population import generate_population
from .service import SimulationService
from .simulation import simulate_population


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Synthetic Agro customer-agent scenario laboratory."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate the synthetic population")
    generate.add_argument("--count", type=int, default=120)
    generate.add_argument("--seed", default="agro-demo-2026")
    generate.add_argument("--output", type=Path, default=Path("output"))
    generate.add_argument("--azure", action="store_true")

    simulate = subparsers.add_parser("simulate", help="Run deterministic scenarios")
    simulate.add_argument("--count", type=int, default=120)
    simulate.add_argument("--seed", default="agro-demo-2026")
    simulate.add_argument("--output", type=Path, default=Path("output/simulation.json"))

    foundry = subparsers.add_parser(
        "simulate-foundry",
        help="Run the bounded Foundry batch workflow",
    )
    foundry.add_argument("--count", type=int, default=120)
    foundry.add_argument("--seed", default="agro-demo-2026")
    foundry.add_argument(
        "--output",
        type=Path,
        default=Path("output/foundry-simulation.json"),
    )
    foundry.add_argument("--azure", action="store_true")
    foundry.add_argument(
        "--concurrency",
        type=int,
        choices=range(1, 9),
        default=2,
    )

    validate = subparsers.add_parser("validate", help="Validate population invariants")
    validate.add_argument("--count", type=int, default=120)
    validate.add_argument("--seed", default="agro-demo-2026")

    subparsers.add_parser(
        "provision-agents",
        help="Create or reuse the governed Foundry prompt-agent versions",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "provision-agents":
        print(json.dumps(provision_agents(), indent=2))
        return
    bundle = generate_population(args.count, args.seed)
    if args.command == "generate":
        write_local_bundle(bundle, args.output)
        if args.azure:
            with AzureTwinStore.from_environment() as store:
                store.save_population(bundle)
        print(bundle.manifest.model_dump_json(indent=2))
    elif args.command == "simulate":
        result = simulate_population(bundle.profiles, bundle.manifest.profile_digest)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        print(json.dumps({"runId": result.run_id, "output": str(args.output)}, indent=2))
    elif args.command == "simulate-foundry":
        service = SimulationService()
        result = asyncio.run(
            service.simulate_foundry(
                bundle.profiles,
                bundle.manifest.profile_digest,
                concurrency=args.concurrency,
            )
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        if args.azure:
            with AzureTwinStore.from_environment() as store:
                store.save_population(bundle, canonical=False)
                store.save_simulation(result, bundle.manifest)
        print(json.dumps({"runId": result.run_id, "output": str(args.output)}, indent=2))
    elif args.command == "validate":
        report = evaluate_population(bundle)
        print(report.model_dump_json(indent=2))
        if not report.passed:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
