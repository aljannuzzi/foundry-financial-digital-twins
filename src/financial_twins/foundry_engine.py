from __future__ import annotations

import json
import os
from typing import Any

from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
from openai import OpenAIError
from pydantic import ValidationError

from .agents import (
    AGENT_INSTRUCTIONS,
    AGENT_SEMANTIC_VERSION,
    agent_definition_hash,
)
from .errors import (
    FoundryProviderError,
    FoundryResponseError,
    SimulationConfigurationError,
)
from .models import ProductVariant, TwinDecision, TwinProfile
from .simulation import DISCLAIMER


class FoundryTwinEngine:
    def __init__(
        self,
        project_endpoint: str | None = None,
        model_deployment: str | None = None,
    ) -> None:
        endpoint = project_endpoint or os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
        model = model_deployment or os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME")
        agent_name = os.environ.get("FOUNDRY_CUSTOMER_TWIN_AGENT")
        if not endpoint:
            raise SimulationConfigurationError(
                "FOUNDRY_PROJECT_ENDPOINT is required for Foundry simulation"
            )
        if not model:
            raise SimulationConfigurationError(
                "AZURE_AI_MODEL_DEPLOYMENT_NAME is required for Foundry simulation"
            )
        self._model = model
        self._agent_name = agent_name
        self._agent_version = (
            f"{AGENT_SEMANTIC_VERSION}:"
            f"{agent_definition_hash(model, AGENT_INSTRUCTIONS['customer-twin'])[:12]}"
            if agent_name
            else "direct-model-v1"
        )
        self._credential = DefaultAzureCredential()
        self._project = AIProjectClient(
            endpoint=endpoint,
            credential=self._credential,
            allow_preview=bool(agent_name),
        )
        self._client = self._project.get_openai_client(
            agent_name=agent_name,
            timeout=45.0,
            max_retries=1,
        )

    @property
    def model_deployment(self) -> str:
        return self._model

    @property
    def agent_name(self) -> str | None:
        return self._agent_name

    @property
    def agent_version(self) -> str:
        return self._agent_version

    @property
    def invocation_mode(self) -> str:
        return "prompt-agent" if self._agent_name else "direct-model"

    async def close(self) -> None:
        await self._client.close()
        await self._project.close()
        await self._credential.close()

    async def evaluate(
        self,
        profile: TwinProfile,
        variant: ProductVariant,
    ) -> TwinDecision:
        allowed_evidence = sorted(
            profile.evidence_ids() | {trait.id for trait in profile.hypotheses}
        )
        instruction = (
            "You simulate a fictional customer's response to a financial product scenario. "
            "The record is synthetic and scenario-bound. Never invent missing history, infer "
            "protected or sensitive attributes, or treat a hypothesis as observed fact. "
            "Return JSON only. fit_score is a scenario affinity score, never a purchase "
            "probability. Cite only supplied evidence IDs. "
            f"Required disclosure: {DISCLAIMER}"
        )
        payload = {
            "profile": profile.agent_payload(),
            "product_variant": variant.model_dump(mode="json"),
            "allowed_evidence_ids": allowed_evidence,
            "required_output": {
                "twin_id": profile.id,
                "variant_id": variant.id,
                "engine": "foundry",
                "choice": "accept|reject|consider|request_change",
                "fit_score": "number 0..100",
                "confidence": "number 0..1",
                "reasons": [
                    {
                        "factor": "short identifier",
                        "direction": "positive|negative|neutral",
                        "evidence_ids": ["allowed IDs only"],
                        "contribution": "number -1..1",
                    }
                ],
                "requested_changes": [],
                "missing_information": [],
                "unsupported_inferences": [],
                "policy_flags": [],
            },
        }
        try:
            request: dict[str, Any] = {
                "input": json.dumps(
                    payload,
                    separators=(",", ":"),
                    ensure_ascii=True,
                ),
                "max_output_tokens": 800,
                "store": False,
            }
            if not self._agent_name:
                request["model"] = self._model
                request["instructions"] = instruction
            response = await self._client.responses.create(**request)
        except OpenAIError as exc:
            raise FoundryProviderError("Microsoft Foundry invocation failed") from exc
        try:
            data: dict[str, Any] = json.loads(response.output_text)
            decision = TwinDecision.model_validate(data)
        except (json.JSONDecodeError, TypeError, ValidationError) as exc:
            raise FoundryResponseError(
                "Microsoft Foundry returned an invalid customer-twin response"
            ) from exc
        if decision.twin_id != profile.id or decision.variant_id != variant.id:
            raise FoundryResponseError(
                "Microsoft Foundry changed the requested twin or variant identifier"
            )
        if decision.engine != "foundry":
            raise FoundryResponseError("Microsoft Foundry returned incorrect engine provenance")
        invalid_evidence = {
            evidence_id
            for reason in decision.reasons
            for evidence_id in reason.evidence_ids
            if evidence_id not in allowed_evidence
        }
        if invalid_evidence:
            raise FoundryResponseError(
                f"Microsoft Foundry cited invalid evidence: {invalid_evidence}"
            )
        return decision
