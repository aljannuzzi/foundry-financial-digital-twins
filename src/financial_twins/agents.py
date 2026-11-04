from __future__ import annotations

import hashlib
import json
import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential

AGENT_INSTRUCTIONS = {
    "customer-twin": (
        "You simulate a fictional Agro customer's response to a financial product "
        "scenario. Treat observables, derived values, and uncertain hypotheses as "
        "different epistemic layers. Never invent missing history, infer protected "
        "or sensitive attributes, or treat a hypothesis as fact. Return only the "
        "requested structured JSON, cite supplied evidence IDs, and never describe "
        "a fit score as purchase probability."
    ),
    "product-expert": (
        "You review a fictional financial product scenario for completeness and "
        "internal consistency. Identify missing price, benefit, eligibility, "
        "service, reversibility, and disclosure fields. Do not approve credit, "
        "price a real customer, or make legal conclusions."
    ),
    "risk-policy-critic": (
        "You critique synthetic financial-product simulation artifacts for "
        "unsupported inferences, proxy leakage, unfair treatment, manipulation, "
        "false precision, and prohibited consequential use. Prefer abstention and "
        "explicit evidence gaps over speculation."
    ),
    "scenario-designer": (
        "You help design controlled product variants for a synthetic scenario "
        "laboratory. Change only preregistered treatment parameters, preserve the "
        "paired population, and separate hypotheses from market forecasts."
    ),
    "portfolio-analyst": (
        "You summarize structured synthetic decisions across product variants. "
        "Report scenario signals, heterogeneity, objections, uncertainty, and "
        "recommended real-world validation. Never claim demand, revenue, or "
        "product-market-fit forecasts without external calibration."
    ),
}
AGENT_SEMANTIC_VERSION = "1.0.0"


def agent_definition_hash(model: str, instructions: str) -> str:
    return hashlib.sha256(
        json.dumps(
            {"model": model, "instructions": instructions},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def provision_agents(
    project_endpoint: str | None = None,
    model_deployment: str | None = None,
) -> list[dict[str, str]]:
    endpoint = project_endpoint or os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
    model = model_deployment or os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    if not endpoint or not model:
        raise ValueError("FOUNDRY_PROJECT_ENDPOINT and AZURE_AI_MODEL_DEPLOYMENT_NAME are required")
    credential = DefaultAzureCredential()
    project = AIProjectClient(
        endpoint=endpoint,
        credential=credential,
        allow_preview=True,
    )
    provisioned: list[dict[str, str]] = []
    try:
        for name, instructions in AGENT_INSTRUCTIONS.items():
            definition_hash = agent_definition_hash(model, instructions)
            try:
                latest = next(
                    iter(
                        project.agents.list_versions(
                            name,
                            limit=1,
                            order="desc",
                        )
                    ),
                    None,
                )
            except ResourceNotFoundError:
                latest = None
            if latest and (latest.metadata or {}).get("definitionHash") == definition_hash:
                agent = latest
            else:
                agent = project.agents.create_version(
                    agent_name=name,
                    definition=PromptAgentDefinition(
                        model=model,
                        instructions=instructions,
                    ),
                    metadata={
                        "definitionHash": definition_hash,
                        "semanticVersion": AGENT_SEMANTIC_VERSION,
                    },
                    description="Financial Digital Twins non-production agent",
                )
            provisioned.append(
                {
                    "name": agent.name,
                    "version": str(agent.version),
                    "id": agent.id,
                }
            )
    finally:
        project.close()
        credential.close()
    return provisioned
