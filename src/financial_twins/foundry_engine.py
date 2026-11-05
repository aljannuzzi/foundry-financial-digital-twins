from __future__ import annotations

import asyncio
import json
import os

from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
from openai import OpenAIError, RateLimitError
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


def parse_agent_output(output_text: str) -> TwinDecision:
    normalized = output_text.strip()
    if normalized.startswith("```"):
        normalized = normalized.removeprefix("```json")
        normalized = normalized.removeprefix("```")
        normalized = normalized.removesuffix("```").strip()
    start = normalized.find("{")
    if start < 0:
        raise ValueError("Agent output did not contain a JSON object")
    data, end = json.JSONDecoder().raw_decode(normalized[start:])
    decision = TwinDecision.model_validate(data)
    trailing = normalized[start + end :].strip()
    if trailing:
        decision = decision.model_copy(
            update={
                "policy_flags": [
                    *decision.policy_flags,
                    "agent_output_trailing_content",
                ]
            }
        )
    return decision


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
                "requested_changes": [
                    {
                        "item": "product parameter",
                        "requested_value": "specific requested adjustment",
                        "evidence_ids": ["allowed IDs only"],
                    }
                ],
                "missing_information": [],
                "unsupported_inferences": [],
                "policy_flags": [],
            },
        }
        input_text = json.dumps(
            payload,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        response = None
        for attempt in range(8):
            try:
                if self._agent_name:
                    response = await self._client.responses.create(input=input_text)
                else:
                    response = await self._client.responses.parse(
                        model=self._model,
                        instructions=instruction,
                        input=input_text,
                        max_output_tokens=800,
                        store=False,
                        text_format=TwinDecision,
                    )
                break
            except RateLimitError as exc:
                if attempt == 7:
                    raise FoundryProviderError(
                        "Microsoft Foundry rate limit persisted after retries"
                    ) from exc
                retry_after = exc.response.headers.get("retry-after")
                retry_after_ms = exc.response.headers.get("retry-after-ms")
                delay = (
                    float(retry_after)
                    if retry_after
                    else float(retry_after_ms) / 1000
                    if retry_after_ms
                    else min(60.0, float(2 ** (attempt + 1)))
                )
                await asyncio.sleep(max(1.0, delay))
            except OpenAIError as exc:
                raise FoundryProviderError("Microsoft Foundry invocation failed") from exc
        if response is None:
            raise FoundryProviderError("Microsoft Foundry invocation returned no response")
        try:
            if self._agent_name:
                decision = parse_agent_output(response.output_text)
            else:
                decision = response.output_parsed
                if decision is None:
                    raise ValueError("Structured response contained no parsed output")
                decision = TwinDecision.model_validate(decision)
        except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as exc:
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
        invalid_evidence.update(
            evidence_id
            for change in decision.requested_changes
            for evidence_id in change.evidence_ids
            if evidence_id not in allowed_evidence
        )
        if invalid_evidence:
            raise FoundryResponseError(
                f"Microsoft Foundry cited invalid evidence: {invalid_evidence}"
            )
        return decision
