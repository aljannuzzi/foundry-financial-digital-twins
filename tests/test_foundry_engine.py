from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from financial_twins.errors import FoundryResponseError
from financial_twins.foundry_engine import FoundryTwinEngine, parse_agent_output
from financial_twins.models import DecisionReason, TwinDecision
from financial_twins.population import generate_population
from financial_twins.simulation import default_product_variants


class FakeResponses:
    def __init__(self, engine: str) -> None:
        self.engine = engine
        self.request: dict | None = None

    def _decision(self) -> TwinDecision:
        profile = generate_population(8, "fake-foundry").profiles[0]
        variant = default_product_variants()[0]
        return TwinDecision.model_validate(
            {
                "twin_id": profile.id,
                "variant_id": variant.id,
                "engine": self.engine,
                "choice": "consider",
                "fit_score": 55,
                "confidence": 0.8,
                "reasons": [
                    {
                        "factor": "liquidity_fit",
                        "direction": "positive",
                        "evidence_ids": ["H1", "D1"],
                        "contribution": 0.2,
                    }
                ],
                "requested_changes": [],
                "missing_information": [],
                "unsupported_inferences": [],
                "policy_flags": [],
            }
        )

    async def create(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(output_text=self._decision().model_dump_json())

    async def parse(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(output_parsed=self._decision())


class FakeClient:
    def __init__(self, engine: str) -> None:
        self.responses = FakeResponses(engine)


def engine_with_response(engine_name: str) -> FoundryTwinEngine:
    engine = FoundryTwinEngine.__new__(FoundryTwinEngine)
    engine._model = "chat"
    engine._agent_name = "customer-twin"
    engine._agent_version = "1.0.0:test"
    engine._client = FakeClient(engine_name)
    return engine


def test_bound_agent_uses_agent_endpoint_contract() -> None:
    profile = generate_population(8, "fake-foundry").profiles[0]
    variant = default_product_variants()[0]
    engine = engine_with_response("foundry")

    decision = asyncio.run(engine.evaluate(profile, variant))

    assert decision.engine == "foundry"
    assert "model" not in engine._client.responses.request
    assert "max_output_tokens" not in engine._client.responses.request


def test_direct_model_uses_structured_output_and_token_bound() -> None:
    profile = generate_population(8, "fake-foundry").profiles[0]
    variant = default_product_variants()[0]
    engine = engine_with_response("foundry")
    engine._agent_name = None

    decision = asyncio.run(engine.evaluate(profile, variant))

    assert decision.engine == "foundry"
    assert engine._client.responses.request["model"] == "chat"
    assert engine._client.responses.request["max_output_tokens"] == 800
    assert engine._client.responses.request["text_format"] is TwinDecision


def test_false_engine_provenance_is_rejected() -> None:
    profile = generate_population(8, "fake-foundry").profiles[0]
    variant = default_product_variants()[0]
    engine = engine_with_response("deterministic")

    with pytest.raises(FoundryResponseError, match="provenance"):
        asyncio.run(engine.evaluate(profile, variant))


def test_decisions_require_grounded_reasons() -> None:
    with pytest.raises(ValidationError):
        DecisionReason(
            factor="liquidity_fit",
            direction="positive",
            evidence_ids=[],
            contribution=0.2,
        )
    with pytest.raises(ValidationError):
        TwinDecision(
            twin_id="AGRO-TEST-0001",
            variant_id="agro-flex-liquidity",
            engine="foundry",
            choice="consider",
            fit_score=55,
            confidence=0.8,
            reasons=[],
            requested_changes=[],
            missing_information=[],
            unsupported_inferences=[],
            policy_flags=[],
        )


def test_real_engine_constructor_has_async_transport(monkeypatch) -> None:
    monkeypatch.setenv("FOUNDRY_CUSTOMER_TWIN_AGENT", "customer-twin")
    engine = FoundryTwinEngine(
        project_endpoint=("https://example.services.ai.azure.com/api/projects/test-project"),
        model_deployment="chat",
    )

    assert engine.agent_name == "customer-twin"
    assert engine.agent_version.startswith("1.0.0:")
    asyncio.run(engine.close())


def test_agent_parser_accepts_first_object_and_flags_trailing_content() -> None:
    decision = FakeResponses("foundry")._decision()

    parsed = parse_agent_output(f"{decision.model_dump_json()}]")

    assert parsed.twin_id == decision.twin_id
    assert "agent_output_trailing_content" in parsed.policy_flags
