"""
Unit tests for LLM fallback compiler (_compile_intent_with_llm_fallback).
"""

import json
from types import SimpleNamespace
from unittest.mock import Mock

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


def test_deterministic_approved_actions_skip_llm(monkeypatch, state_manager, validator):
    """Deterministic approvals skip LLM call."""
    # Patch deterministic parser to return a SET action
    monkeypatch.setattr(
        "magnet.deployment.intent_parser.parse_intent_to_actions",
        lambda text: [Action(action_type=ActionType.SET, path="hull.loa", value=40.0, unit="m")],
    )
    llm_client = Mock()
    llm_client.complete_json = Mock(side_effect=AssertionError("LLM should not be called"))

    request = SimpleNamespace(text="set hull length to 40m", design_version_before=None)

    resp = _compile_intent_with_llm_fallback(
        design_id="d1",
        request=request,
        state_manager=state_manager,
        validator=validator,
        mode="single",
        llm_client=llm_client,
    )

    assert resp["provenance"] == "deterministic"
    assert resp["approved"]
    assert resp["apply_payload"] is not None
    llm_client.complete_json.assert_not_called()


def test_llm_non_refinable_paths_filtered(monkeypatch, state_manager, validator):
    """Non-refinable LLM proposals are dropped before validation."""
    monkeypatch.setattr(
        "magnet.deployment.intent_parser.parse_intent_to_actions",
        lambda text: [],
    )
    proposals = LLMProposals(actions=[
        LLMActionProposal(action_type="set", path="kernel.session", value=1)
    ])
    llm_client = Mock()
    llm_client.complete_json = Mock(return_value=proposals)

    request = SimpleNamespace(text="nonsense", design_version_before=None)

    resp = _compile_intent_with_llm_fallback(
        design_id="d1",
        request=request,
        state_manager=state_manager,
        validator=validator,
        mode="single",
        llm_client=llm_client,
    )

    assert resp["provenance"] == "llm_guess"
    assert resp["approved"] == []
    assert resp["apply_payload"] is None


def test_llm_paths_not_in_allowlist_filtered(monkeypatch, state_manager, validator):
    """Refinable but not allowlisted paths are filtered out."""
    monkeypatch.setattr(
        "magnet.deployment.intent_parser.parse_intent_to_actions",
        lambda text: [],
    )
    proposals = LLMProposals(actions=[
        LLMActionProposal(action_type="set", path="hull.cb", value=0.8)
    ])
    llm_client = Mock()
    llm_client.complete_json = Mock(return_value=proposals)

    request = SimpleNamespace(text="make it blockier", design_version_before=None)

    resp = _compile_intent_with_llm_fallback(
        design_id="d1",
        request=request,
        state_manager=state_manager,
        validator=validator,
        mode="single",
        llm_client=llm_client,
    )

    assert resp["provenance"] == "llm_guess"
    assert resp["approved"] == []
    assert resp["apply_payload"] is None


def test_llm_called_with_temperature_zero_and_prompt_version(monkeypatch, state_manager, validator):
    """LLM fallback enforces temperature=0 and provides prompt_version."""
    monkeypatch.setattr(
        "magnet.deployment.intent_parser.parse_intent_to_actions",
        lambda text: [],
    )
    proposals = LLMProposals(actions=[
        LLMActionProposal(action_type="set", path="hull.loa", value=35.0)
    ])
    call_kwargs = {}

    def _complete_json(text, schema, **kwargs):
        call_kwargs.update(kwargs)
        return proposals

    llm_client = Mock()
    llm_client.complete_json = _complete_json

    request = SimpleNamespace(text="make it longer", design_version_before=None)

    resp = _compile_intent_with_llm_fallback(
        design_id="d1",
        request=request,
        state_manager=state_manager,
        validator=validator,
        mode="single",
        llm_client=llm_client,
    )

    assert call_kwargs.get("temperature") == 0
    assert "prompt_version" in call_kwargs
    assert resp["provenance"] == "llm_guess"
    assert resp["llm_output_sha256"]

