"""
Unit tests for LLM fallback compiler (_compile_intent_with_llm_fallback).
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from magnet.deployment.api import (
    _compile_intent_with_llm_fallback,
    LLMActionProposal,
    LLMProposals,
)
from magnet.kernel.action_validator import ActionPlanValidator
from magnet.kernel.intent_protocol import Action, ActionType


class DummyStateManager:
    """Minimal StateManager stub for validator usage."""

    def __init__(self):
        self.design_version = 0

    def is_locked(self, path):
        return False

    def get(self, path, default=None):
        return None

    def get_strict(self, path):
        return None


@pytest.fixture
def state_manager():
    return DummyStateManager()


@pytest.fixture
def validator():
    return ActionPlanValidator()


@pytest.mark.asyncio
async def test_llm_runs_first_and_skips_deterministic_parser(monkeypatch, state_manager, validator):
    """LLM runs first; deterministic parser is not called when LLM succeeds."""
    # If deterministic parser is called, fail the test
    monkeypatch.setattr(
        "magnet.deployment.intent_parser.parse_intent_to_actions",
        lambda text: (_ for _ in ()).throw(AssertionError("Deterministic parser should not be called")),
    )

    proposals = LLMProposals(actions=[
        LLMActionProposal(action_type="set", path="hull.loa", value=40.0, unit="m")
    ])
    llm_client = Mock()
    llm_client.is_available = Mock(return_value=True)
    llm_client.complete_json = AsyncMock(return_value=proposals)

    request = SimpleNamespace(text="set hull length to 40m", design_version_before=None)

    resp = await _compile_intent_with_llm_fallback(
        design_id="d1",
        request=request,
        state_manager=state_manager,
        validator=validator,
        mode="single",
        llm_client=llm_client,
    )

    assert resp["provenance"] == "llm_guess"
    assert resp["approved"]
    assert resp["apply_payload"] is not None
    llm_client.complete_json.assert_awaited()


@pytest.mark.asyncio
async def test_llm_non_refinable_paths_filtered_then_deterministic_fallback(monkeypatch, state_manager, validator):
    """Non-refinable LLM proposals are dropped; if nothing remains, deterministic fallback runs."""
    monkeypatch.setattr(
        "magnet.deployment.intent_parser.parse_intent_to_actions",
        lambda text: [],
    )
    proposals = LLMProposals(actions=[
        LLMActionProposal(action_type="set", path="kernel.session", value=1)
    ])
    llm_client = Mock()
    llm_client.is_available = Mock(return_value=True)
    llm_client.complete_json = AsyncMock(return_value=proposals)

    request = SimpleNamespace(text="nonsense", design_version_before=None)

    resp = await _compile_intent_with_llm_fallback(
        design_id="d1",
        request=request,
        state_manager=state_manager,
        validator=validator,
        mode="single",
        llm_client=llm_client,
    )

    llm_client.complete_json.assert_awaited()
    assert resp["provenance"] == "deterministic"
    assert resp["approved"] == []
    assert resp["apply_payload"] is None
    assert "guidance" in resp


@pytest.mark.asyncio
async def test_llm_paths_not_in_allowlist_filtered_then_deterministic_fallback(monkeypatch, state_manager, validator):
    """Refinable but not allowlisted paths are filtered out; deterministic fallback runs if empty."""
    monkeypatch.setattr(
        "magnet.deployment.intent_parser.parse_intent_to_actions",
        lambda text: [],
    )
    proposals = LLMProposals(actions=[
        LLMActionProposal(action_type="set", path="hull.cb", value=0.8)
    ])
    llm_client = Mock()
    llm_client.is_available = Mock(return_value=True)
    llm_client.complete_json = AsyncMock(return_value=proposals)

    request = SimpleNamespace(text="make it blockier", design_version_before=None)

    resp = await _compile_intent_with_llm_fallback(
        design_id="d1",
        request=request,
        state_manager=state_manager,
        validator=validator,
        mode="single",
        llm_client=llm_client,
    )

    llm_client.complete_json.assert_awaited()
    assert resp["provenance"] == "deterministic"
    assert resp["approved"] == []
    assert resp["apply_payload"] is None
    assert "guidance" in resp


@pytest.mark.asyncio
async def test_llm_called_with_options_temperature_zero_and_system_prompt(monkeypatch, state_manager, validator):
    """LLM-first enforces options.temperature=0 and injects a minimal translator system prompt."""
    # Ensure deterministic fallback isn't used (LLM returns a valid action)
    proposals = LLMProposals(actions=[
        LLMActionProposal(action_type="set", path="hull.loa", value=35.0)
    ])
    call_kwargs = {}

    async def _complete_json(text, schema, **kwargs):
        call_kwargs.update(kwargs)
        return proposals

    llm_client = Mock()
    llm_client.is_available = Mock(return_value=True)
    llm_client.complete_json = _complete_json

    request = SimpleNamespace(text="make it longer", design_version_before=None)

    resp = await _compile_intent_with_llm_fallback(
        design_id="d1",
        request=request,
        state_manager=state_manager,
        validator=validator,
        mode="single",
        llm_client=llm_client,
    )

    opts = call_kwargs.get("options")
    assert opts is not None
    assert getattr(opts, "temperature", None) == 0
    system_prompt = call_kwargs.get("system_prompt") or ""
    assert "Valid action_type values" in system_prompt
    assert "Bucket vocabulary" in system_prompt
    assert "a_bit" in system_prompt and "normal" in system_prompt and "way" in system_prompt
    # Path + unit injection
    assert "hull.loa" in system_prompt
    assert resp["provenance"] == "llm_guess"
    assert resp["llm_output_sha256"]


@pytest.mark.asyncio
async def test_deterministic_used_when_llm_unavailable(monkeypatch, state_manager, validator):
    """If llm_client is None, deterministic parser runs (fallback)."""
    monkeypatch.setattr(
        "magnet.deployment.intent_parser.parse_intent_to_actions",
        lambda text: [Action(action_type=ActionType.SET, path="hull.loa", value=40.0, unit="m")],
    )
    request = SimpleNamespace(text="set hull length to 40m", design_version_before=None)

    resp = await _compile_intent_with_llm_fallback(
        design_id="d1",
        request=request,
        state_manager=state_manager,
        validator=validator,
        mode="single",
        llm_client=None,
    )

    assert resp["provenance"] == "deterministic"
    assert resp["approved"]
    assert resp["apply_payload"] is not None


@pytest.mark.asyncio
async def test_deterministic_used_when_llm_throws(monkeypatch, state_manager, validator):
    """If LLM call throws, deterministic parser runs (fallback)."""
    monkeypatch.setattr(
        "magnet.deployment.intent_parser.parse_intent_to_actions",
        lambda text: [Action(action_type=ActionType.SET, path="hull.loa", value=42.0, unit="m")],
    )
    llm_client = Mock()
    llm_client.is_available = Mock(return_value=True)
    llm_client.complete_json = AsyncMock(side_effect=RuntimeError("boom"))

    request = SimpleNamespace(text="set hull length to 42m", design_version_before=None)

    resp = await _compile_intent_with_llm_fallback(
        design_id="d1",
        request=request,
        state_manager=state_manager,
        validator=validator,
        mode="single",
        llm_client=llm_client,
    )

    assert resp["provenance"] == "deterministic"
    assert resp["approved"]

