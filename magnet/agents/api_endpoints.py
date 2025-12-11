"""
api_endpoints.py - Agent API routes v1.0
BRAVO OWNS THIS FILE.

V1.4 UI Integration: Agent Clarification Endpoints

Provides:
- POST /api/v1/agents/{agent_id}/clarification/{request_id}/ack
- GET /api/v1/agents/{agent_id}/clarifications
- POST /api/v1/agents/{agent_id}/clarifications
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import logging

try:
    from fastapi import APIRouter, HTTPException, Body
    from pydantic import BaseModel, Field
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    APIRouter = None

from magnet.agents.clarification import (
    AckType,
    AgentPriority,
    ClarificationRequest,
    ClarificationAck,
    ClarificationManager,
)

__all__ = [
    'create_agents_router',
    'AckRequest',
    'AckResponse',
    'ClarificationCreateRequest',
    'ClarificationResponse',
]

logger = logging.getLogger(__name__)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

if HAS_FASTAPI:

    class AckRequest(BaseModel):
        """
        Request to acknowledge a clarification.

        V1.4 spec:
        POST /api/v1/agents/{agent_id}/clarification/{request_id}/ack
        """
        ack_type: str = Field(
            ...,
            description="ACK type: queued, presented, responded, skipped, cancelled"
        )
        request_token: str = Field(
            ...,
            description="Request token for correlation"
        )
        reason: Optional[str] = Field(
            None,
            description="Optional reason for ACK"
        )

    class AckResponse(BaseModel):
        """Response from ACK operation."""
        success: bool
        request_id: str
        agent_id: str
        ack_type: str
        timestamp: str
        message: str = ""

    class ClarificationCreateRequest(BaseModel):
        """Request to create a clarification."""
        message: str = Field(..., description="Clarification message")
        options: List[str] = Field(
            default_factory=list,
            description="Response options"
        )
        default_option: Optional[str] = Field(
            None,
            description="Default option"
        )
        priority: int = Field(
            0,
            description="Priority (0-4, higher is more important)"
        )
        context: Dict[str, Any] = Field(
            default_factory=dict,
            description="Additional context"
        )
        timeout_seconds: int = Field(
            300,
            description="Timeout in seconds"
        )

    class ClarificationResponse(BaseModel):
        """Response with clarification details."""
        request_id: str
        agent_id: str
        request_token: str
        message: str
        options: List[str]
        default_option: Optional[str] = None
        priority: int
        created_at: str
        timeout_seconds: int
        current_ack: str
        response: Optional[str] = None

    class ClarificationListResponse(BaseModel):
        """Response with list of clarifications."""
        clarifications: List[Dict[str, Any]]
        total: int
        pending: int

    class RespondRequest(BaseModel):
        """Request to respond to a clarification."""
        response: str = Field(..., description="User response")
        response_data: Dict[str, Any] = Field(
            default_factory=dict,
            description="Additional response data"
        )

else:
    # Fallback dataclasses
    @dataclass
    class AckRequest:
        ack_type: str = ""
        request_token: str = ""
        reason: Optional[str] = None

    @dataclass
    class AckResponse:
        success: bool = False
        request_id: str = ""
        agent_id: str = ""
        ack_type: str = ""
        timestamp: str = ""
        message: str = ""


# =============================================================================
# ROUTER FACTORY
# =============================================================================

# Global manager instance
_manager: Optional[ClarificationManager] = None


def get_clarification_manager() -> ClarificationManager:
    """Get or create the global clarification manager."""
    global _manager
    if _manager is None:
        _manager = ClarificationManager()
    return _manager


def create_agents_router(
    clarification_manager: Optional[ClarificationManager] = None,
) -> Any:
    """
    Create FastAPI router for agent endpoints.

    Args:
        clarification_manager: Optional manager instance

    Returns:
        FastAPI APIRouter or None if FastAPI not available
    """
    if not HAS_FASTAPI:
        logger.warning("FastAPI not available, cannot create router")
        return None

    # Use provided or global manager
    manager = clarification_manager or get_clarification_manager()

    router = APIRouter(
        prefix="/api/v1/agents",
        tags=["agents"],
    )

    # =========================================================================
    # CLARIFICATION ACK ENDPOINT (V1.4 Priority 3)
    # =========================================================================

    @router.post(
        "/{agent_id}/clarification/{request_id}/ack",
        response_model=AckResponse,
    )
    async def acknowledge_clarification(
        agent_id: str,
        request_id: str,
        request: AckRequest,
    ) -> AckResponse:
        """
        Acknowledge a clarification request.

        V1.4 spec endpoint for clarification lifecycle tracking.
        ACK types: queued, presented, responded, skipped, cancelled

        Args:
            agent_id: Agent identifier
            request_id: Clarification request ID
            request: ACK request body

        Returns:
            ACK response with timestamp
        """
        try:
            # Validate ACK type
            try:
                ack_type = AckType(request.ack_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid ack_type: {request.ack_type}. "
                           f"Valid types: {[t.value for t in AckType]}"
                )

            # Process ACK
            ack = manager.acknowledge(
                agent_id=agent_id,
                request_id=request_id,
                ack_type=ack_type,
                request_token=request.request_token,
                reason=request.reason,
            )

            if not ack:
                raise HTTPException(
                    status_code=404,
                    detail=f"Clarification request {request_id} not found "
                           f"or invalid token/agent"
                )

            return AckResponse(
                success=True,
                request_id=request_id,
                agent_id=agent_id,
                ack_type=ack.ack_type.value,
                timestamp=ack.timestamp,
                message=f"ACK recorded: {ack.ack_type.value}",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"ACK failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # =========================================================================
    # CLARIFICATION MANAGEMENT ENDPOINTS
    # =========================================================================

    @router.get(
        "/{agent_id}/clarifications",
        response_model=ClarificationListResponse,
    )
    async def list_clarifications(
        agent_id: str,
        pending_only: bool = False,
    ) -> ClarificationListResponse:
        """
        List clarification requests for an agent.

        Args:
            agent_id: Agent identifier
            pending_only: Only return pending requests

        Returns:
            List of clarification requests
        """
        requests = manager.get_agent_requests(agent_id)

        if pending_only:
            requests = [r for r in requests if not r.is_terminal()]

        return ClarificationListResponse(
            clarifications=[r.to_dict() for r in requests],
            total=len(requests),
            pending=len([r for r in requests if not r.is_terminal()]),
        )

    @router.post(
        "/{agent_id}/clarifications",
        response_model=ClarificationResponse,
    )
    async def create_clarification(
        agent_id: str,
        request: ClarificationCreateRequest,
    ) -> ClarificationResponse:
        """
        Create a new clarification request.

        Args:
            agent_id: Agent identifier
            request: Clarification details

        Returns:
            Created clarification
        """
        try:
            priority = AgentPriority(request.priority)
        except ValueError:
            priority = AgentPriority.DEFAULT

        clarification = manager.create_request(
            agent_id=agent_id,
            message=request.message,
            options=request.options,
            priority=priority,
            context=request.context,
            timeout_seconds=request.timeout_seconds,
        )

        return ClarificationResponse(
            request_id=clarification.request_id,
            agent_id=clarification.agent_id,
            request_token=clarification.request_token,
            message=clarification.message,
            options=clarification.options,
            default_option=clarification.default_option,
            priority=clarification.priority.value,
            created_at=clarification.created_at,
            timeout_seconds=clarification.timeout_seconds,
            current_ack=clarification.current_ack.value,
            response=clarification.response,
        )

    @router.get(
        "/{agent_id}/clarification/{request_id}",
        response_model=ClarificationResponse,
    )
    async def get_clarification(
        agent_id: str,
        request_id: str,
    ) -> ClarificationResponse:
        """
        Get a specific clarification request.

        Args:
            agent_id: Agent identifier
            request_id: Request identifier

        Returns:
            Clarification details
        """
        clarification = manager.get_request(request_id)

        if not clarification:
            raise HTTPException(
                status_code=404,
                detail=f"Clarification {request_id} not found"
            )

        if clarification.agent_id != agent_id:
            raise HTTPException(
                status_code=403,
                detail=f"Clarification {request_id} belongs to another agent"
            )

        return ClarificationResponse(
            request_id=clarification.request_id,
            agent_id=clarification.agent_id,
            request_token=clarification.request_token,
            message=clarification.message,
            options=clarification.options,
            default_option=clarification.default_option,
            priority=clarification.priority.value,
            created_at=clarification.created_at,
            timeout_seconds=clarification.timeout_seconds,
            current_ack=clarification.current_ack.value,
            response=clarification.response,
        )

    @router.post(
        "/{agent_id}/clarification/{request_id}/respond",
    )
    async def respond_to_clarification(
        agent_id: str,
        request_id: str,
        request: RespondRequest,
    ) -> AckResponse:
        """
        Submit a response to a clarification.

        Args:
            agent_id: Agent identifier
            request_id: Request identifier
            request: Response data

        Returns:
            ACK response
        """
        clarification = manager.get_request(request_id)

        if not clarification:
            raise HTTPException(
                status_code=404,
                detail=f"Clarification {request_id} not found"
            )

        ack = manager.respond(
            request_id=request_id,
            response=request.response,
            response_data=request.response_data,
        )

        if not ack:
            raise HTTPException(
                status_code=500,
                detail="Failed to record response"
            )

        return AckResponse(
            success=True,
            request_id=request_id,
            agent_id=agent_id,
            ack_type=ack.ack_type.value,
            timestamp=ack.timestamp,
            message="Response recorded",
        )

    @router.delete(
        "/{agent_id}/clarification/{request_id}",
    )
    async def cancel_clarification(
        agent_id: str,
        request_id: str,
        reason: str = "user_cancelled",
    ) -> AckResponse:
        """
        Cancel a clarification request.

        Args:
            agent_id: Agent identifier
            request_id: Request identifier
            reason: Cancellation reason

        Returns:
            ACK response
        """
        clarification = manager.get_request(request_id)

        if not clarification:
            raise HTTPException(
                status_code=404,
                detail=f"Clarification {request_id} not found"
            )

        if clarification.agent_id != agent_id:
            raise HTTPException(
                status_code=403,
                detail=f"Clarification {request_id} belongs to another agent"
            )

        ack = manager.cancel(request_id, reason)

        if not ack:
            raise HTTPException(
                status_code=500,
                detail="Failed to cancel request"
            )

        return AckResponse(
            success=True,
            request_id=request_id,
            agent_id=agent_id,
            ack_type=ack.ack_type.value,
            timestamp=ack.timestamp,
            message=f"Cancelled: {reason}",
        )

    # =========================================================================
    # GLOBAL ENDPOINTS
    # =========================================================================

    @router.get("/clarifications/pending")
    async def list_pending_clarifications() -> ClarificationListResponse:
        """
        List all pending clarification requests.

        Returns requests sorted by priority (highest first).
        """
        requests = manager.get_pending_requests()

        return ClarificationListResponse(
            clarifications=[r.to_dict() for r in requests],
            total=len(requests),
            pending=len(requests),
        )

    @router.get("/stats")
    async def get_agent_stats() -> Dict[str, Any]:
        """Get agent/clarification statistics."""
        return manager.get_stats()

    @router.post("/clarifications/cleanup")
    async def cleanup_expired() -> Dict[str, Any]:
        """Clean up expired clarification requests."""
        count = manager.cleanup_expired()
        return {
            "success": True,
            "cleaned_up": count,
        }

    return router
