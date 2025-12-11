"""
magnet/llm/services/clarification_service.py - Clarification Service

High-level service for generating clarification questions and parsing responses.
Wraps LLM interactions with domain logic and deterministic fallbacks.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..prompts.schemas import ClarificationResponse, UserIntentResponse
from ..prompts.clarification import (
    CLARIFICATION_SYSTEM_PROMPT,
    INTENT_PARSING_SYSTEM_PROMPT,
    create_clarification_prompt,
    create_intent_parsing_prompt,
    create_batch_clarification_prompt,
    get_fallback_clarification,
    get_fallback_intent,
)

if TYPE_CHECKING:
    from ..protocol import LLMProviderProtocol

logger = logging.getLogger("llm.services.clarification")


class ClarificationService:
    """
    Service for generating clarification questions and parsing user responses.

    Features:
    - LLM-powered question generation with context awareness
    - Intent parsing from natural language responses
    - Automatic fallback to deterministic behavior
    - Batch processing for multiple issues
    """

    def __init__(
        self,
        llm: Optional["LLMProviderProtocol"] = None,
        use_fallback: bool = True,
    ):
        """
        Initialize the clarification service.

        Args:
            llm: LLM provider instance (optional)
            use_fallback: Whether to use fallback when LLM unavailable
        """
        self.llm = llm
        self.use_fallback = use_fallback

    async def generate_clarification(
        self,
        parameter_path: str,
        validation_message: str,
        context: Optional[Dict[str, Any]] = None,
        option_count: int = 3,
    ) -> ClarificationResponse:
        """
        Generate a clarification question for a validation issue.

        Args:
            parameter_path: The parameter needing clarification
            validation_message: The validation failure message
            context: Additional design context
            option_count: Number of options to generate

        Returns:
            ClarificationResponse with question and options
        """
        if self.llm is None:
            logger.debug("No LLM available, using fallback")
            return self._fallback_clarification(parameter_path, validation_message)

        prompt = create_clarification_prompt(
            parameter_path=parameter_path,
            validation_message=validation_message,
            context=context,
            option_count=option_count,
        )

        try:
            response = await self.llm.complete_with_fallback(
                prompt=prompt,
                fallback_fn=lambda: self._fallback_clarification(
                    parameter_path, validation_message
                ),
                system_prompt=CLARIFICATION_SYSTEM_PROMPT,
            )

            # If we got a fallback dict, convert it
            if isinstance(response, dict):
                return ClarificationResponse(**response)

            # Parse LLM response into schema
            return await self.llm.complete_json(
                prompt=prompt,
                response_model=ClarificationResponse,
                system_prompt=CLARIFICATION_SYSTEM_PROMPT,
            )

        except Exception as e:
            logger.warning(f"LLM clarification failed: {e}, using fallback")
            if self.use_fallback:
                return self._fallback_clarification(parameter_path, validation_message)
            raise

    async def parse_user_intent(
        self,
        original_question: str,
        options: List[Dict[str, str]],
        user_response: str,
    ) -> UserIntentResponse:
        """
        Parse user intent from their response to a clarification question.

        Args:
            original_question: The question that was asked
            options: The options that were provided
            user_response: The user's response text

        Returns:
            UserIntentResponse with parsed value and confidence
        """
        # First try simple matching (no LLM needed for exact matches)
        fallback = get_fallback_intent(user_response, options)
        if fallback["confidence"] >= 0.9:
            return UserIntentResponse(**fallback)

        # Use LLM for ambiguous responses
        if self.llm is None:
            logger.debug("No LLM available, using fallback intent parsing")
            return UserIntentResponse(**fallback)

        prompt = create_intent_parsing_prompt(
            original_question=original_question,
            options=options,
            user_response=user_response,
        )

        try:
            return await self.llm.complete_json(
                prompt=prompt,
                response_model=UserIntentResponse,
                system_prompt=INTENT_PARSING_SYSTEM_PROMPT,
            )

        except Exception as e:
            logger.warning(f"LLM intent parsing failed: {e}, using fallback")
            if self.use_fallback:
                return UserIntentResponse(**fallback)
            raise

    async def generate_batch_clarifications(
        self,
        issues: List[Dict[str, Any]],
        max_questions: int = 5,
    ) -> List[ClarificationResponse]:
        """
        Generate clarification questions for multiple issues.

        Args:
            issues: List of validation issues
            max_questions: Maximum questions to generate

        Returns:
            List of ClarificationResponse objects
        """
        if not issues:
            return []

        if self.llm is None:
            logger.debug("No LLM available, using fallback for batch")
            return [
                self._fallback_clarification(
                    issue.get("parameter", "unknown"),
                    issue.get("message", "Clarification needed"),
                )
                for issue in issues[:max_questions]
            ]

        prompt = create_batch_clarification_prompt(issues, max_questions)

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=CLARIFICATION_SYSTEM_PROMPT,
            )

            # Parse JSON array response
            import json
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            data = json.loads(content)

            return [
                ClarificationResponse(**item)
                for item in data
                if isinstance(item, dict)
            ]

        except Exception as e:
            logger.warning(f"LLM batch clarification failed: {e}, using fallback")
            if self.use_fallback:
                return [
                    self._fallback_clarification(
                        issue.get("parameter", "unknown"),
                        issue.get("message", "Clarification needed"),
                    )
                    for issue in issues[:max_questions]
                ]
            raise

    async def prioritize_clarifications(
        self,
        clarifications: List[ClarificationResponse],
    ) -> List[ClarificationResponse]:
        """
        Sort clarifications by priority (LLM-enhanced if available).

        Args:
            clarifications: List of clarification responses

        Returns:
            Sorted list with highest priority first
        """
        # Simple sort by priority field
        return sorted(clarifications, key=lambda c: c.priority)

    def _fallback_clarification(
        self,
        parameter_path: str,
        message: str,
    ) -> ClarificationResponse:
        """
        Generate deterministic fallback clarification.

        Args:
            parameter_path: The parameter needing clarification
            message: The validation message

        Returns:
            Static ClarificationResponse
        """
        fallback_data = get_fallback_clarification(parameter_path, message)

        # Convert options to proper schema format
        from ..prompts.schemas import ClarificationOption
        options = [
            ClarificationOption(**opt)
            for opt in fallback_data.get("options", [])
        ]

        return ClarificationResponse(
            question=fallback_data["question"],
            options=options,
            default=fallback_data.get("default"),
            context=fallback_data.get("context"),
            priority=fallback_data.get("priority", 5),
        )

    # =========================================================================
    # Context-Aware Methods
    # =========================================================================

    async def clarify_vessel_type(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> ClarificationResponse:
        """
        Generate vessel type clarification question.

        Args:
            context: Design context

        Returns:
            ClarificationResponse for vessel type
        """
        return await self.generate_clarification(
            parameter_path="mission.vessel_type",
            validation_message="Vessel type not specified or ambiguous",
            context=context,
            option_count=5,
        )

    async def clarify_dimension(
        self,
        dimension: str,
        current_value: Optional[float] = None,
        constraints: Optional[Dict[str, float]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ClarificationResponse:
        """
        Generate dimension clarification question.

        Args:
            dimension: The dimension (length, beam, draft)
            current_value: Current value if any
            constraints: Min/max constraints
            context: Additional context

        Returns:
            ClarificationResponse for the dimension
        """
        full_context = context or {}
        if current_value is not None:
            full_context["current_value"] = current_value
        if constraints:
            full_context["constraints"] = constraints

        return await self.generate_clarification(
            parameter_path=f"hull.{dimension}",
            validation_message=f"{dimension.title()} requires clarification",
            context=full_context,
            option_count=4,
        )

    async def clarify_material(
        self,
        component: str,
        suggested_materials: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ClarificationResponse:
        """
        Generate material selection clarification.

        Args:
            component: Component needing material selection
            suggested_materials: List of suggested materials
            context: Additional context

        Returns:
            ClarificationResponse for material selection
        """
        full_context = context or {}
        if suggested_materials:
            full_context["suggested_materials"] = suggested_materials

        return await self.generate_clarification(
            parameter_path=f"materials.{component}",
            validation_message=f"Material selection needed for {component}",
            context=full_context,
            option_count=4,
        )
