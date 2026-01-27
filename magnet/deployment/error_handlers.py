"""
TASK-022: Error UX — Failures Show Actionable Messages

Maps internal exceptions to user-friendly error messages.
Ensures no Python exception names or stack traces are visible to users.

Error Response Format:
{
    "error": "Human-readable error message",
    "suggestion": "What the user can do to fix it",
    "code": "E001",  # Machine-readable error code
    "details": {}    # Optional additional context
}
"""

import logging
import traceback
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Type
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """Machine-readable error codes."""
    # Geometry errors (E1xx)
    E100_INVALID_GEOMETRY = "E100"
    E101_ZERO_VOLUME = "E101"
    E102_NEGATIVE_DIMENSION = "E102"
    E103_SECTION_ERROR = "E103"
    E104_MESH_ERROR = "E104"
    
    # Physics errors (E2xx)
    E200_NEGATIVE_GM = "E200"
    E201_HYDROSTATICS_FAILED = "E201"
    E202_RESISTANCE_FAILED = "E202"
    E203_STABILITY_FAILED = "E203"
    
    # API errors (E3xx)
    E300_RATE_LIMIT = "E300"
    E301_TIMEOUT = "E301"
    E302_LLM_ERROR = "E302"
    E303_NOT_FOUND = "E303"
    E304_VALIDATION_ERROR = "E304"
    
    # System errors (E4xx)
    E400_INTERNAL_ERROR = "E400"
    E401_STATE_CORRUPTION = "E401"
    E402_PERSISTENCE_ERROR = "E402"
    
    # Unknown
    E999_UNKNOWN = "E999"


@dataclass
class UserFriendlyError:
    """User-friendly error response."""
    error: str
    suggestion: str
    code: str
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "error": self.error,
            "suggestion": self.suggestion,
            "code": self.code,
        }
        if self.details:
            result["details"] = self.details
        return result


# =============================================================================
# ERROR MAPPING
# =============================================================================

# Maps exception types to user-friendly messages
EXCEPTION_MAP: Dict[str, UserFriendlyError] = {
    # Standard Python exceptions
    "ZeroDivisionError": UserFriendlyError(
        error="Hull has no submerged volume at this draft.",
        suggestion="Increase draft or check that hull dimensions are valid.",
        code=ErrorCode.E101_ZERO_VOLUME,
    ),
    "ValueError": UserFriendlyError(
        error="Invalid value provided.",
        suggestion="Check that all dimensions are positive and within realistic ranges.",
        code=ErrorCode.E304_VALIDATION_ERROR,
    ),
    "KeyError": UserFriendlyError(
        error="Required data is missing.",
        suggestion="Ensure all required parameters are provided.",
        code=ErrorCode.E304_VALIDATION_ERROR,
    ),
    "TimeoutError": UserFriendlyError(
        error="The operation took too long.",
        suggestion="Try a simpler request or wait a moment and try again.",
        code=ErrorCode.E301_TIMEOUT,
    ),
    
    # Custom exceptions
    "GeometryError": UserFriendlyError(
        error="Sections don't form a valid hull.",
        suggestion="Check section ordering and ensure points are properly defined.",
        code=ErrorCode.E100_INVALID_GEOMETRY,
    ),
    "MeshError": UserFriendlyError(
        error="Failed to create hull mesh.",
        suggestion="Ensure hull geometry is valid and sections are properly ordered.",
        code=ErrorCode.E104_MESH_ERROR,
    ),
    "HydrostaticsError": UserFriendlyError(
        error="Failed to calculate hydrostatics.",
        suggestion="Check that hull is properly submerged and has valid geometry.",
        code=ErrorCode.E201_HYDROSTATICS_FAILED,
    ),
    "DesignNotFound": UserFriendlyError(
        error="Design not found.",
        suggestion="Check the design ID or create a new design.",
        code=ErrorCode.E303_NOT_FOUND,
    ),
    "MutationEnforcementError": UserFriendlyError(
        error="Cannot modify this value directly.",
        suggestion="Use the design spiral to modify hull parameters.",
        code=ErrorCode.E304_VALIDATION_ERROR,
    ),
    "InvalidPathError": UserFriendlyError(
        error="Invalid parameter path.",
        suggestion="Check that the parameter name is correct.",
        code=ErrorCode.E304_VALIDATION_ERROR,
    ),
    
    # TASK-026: LLM-specific exceptions
    "LLMError": UserFriendlyError(
        error="AI service encountered an error.",
        suggestion="Try rephrasing your request or wait a moment.",
        code=ErrorCode.E302_LLM_ERROR,
    ),
    "RateLimitError": UserFriendlyError(
        error="Too many requests to AI service.",
        suggestion="Please wait 30 seconds before trying again.",
        code=ErrorCode.E300_RATE_LIMIT,
    ),
    "CostLimitError": UserFriendlyError(
        error="AI usage limit reached for this session.",
        suggestion="Start a new session or contact support.",
        code=ErrorCode.E302_LLM_ERROR,
    ),
    "ProviderUnavailableError": UserFriendlyError(
        error="AI service not configured.",
        suggestion="Check ANTHROPIC_API_KEY environment variable.",
        code=ErrorCode.E302_LLM_ERROR,
    ),
    "TimeoutError": UserFriendlyError(
        error="AI is not responding.",
        suggestion="Try again or simplify your request.",
        code=ErrorCode.E301_TIMEOUT,
    ),
    "TransientError": UserFriendlyError(
        error="Temporary AI service issue.",
        suggestion="Please try again in a moment.",
        code=ErrorCode.E302_LLM_ERROR,
    ),
}

# Pattern-based error detection (for exception messages)
MESSAGE_PATTERNS = [
    {
        "pattern": "math domain error",
        "error": UserFriendlyError(
            error="Hull is unstable (negative stability).",
            suggestion="Increase beam or reduce vertical center of gravity (VCG).",
            code=ErrorCode.E200_NEGATIVE_GM,
        ),
    },
    {
        "pattern": "rate limit",
        "error": UserFriendlyError(
            error="Too many requests.",
            suggestion="Please wait 30 seconds before trying again.",
            code=ErrorCode.E300_RATE_LIMIT,
        ),
    },
    {
        "pattern": "timeout",
        "error": UserFriendlyError(
            error="AI is taking too long.",
            suggestion="Try a simpler request or wait a moment.",
            code=ErrorCode.E301_TIMEOUT,
        ),
    },
    {
        "pattern": "connection error",
        "error": UserFriendlyError(
            error="Could not connect to AI service.",
            suggestion="Check your internet connection and try again.",
            code=ErrorCode.E302_LLM_ERROR,
        ),
    },
    {
        "pattern": "llm error",  # lowercase for case-insensitive matching
        "error": UserFriendlyError(
            error="AI service encountered an error.",
            suggestion="Try rephrasing your request or wait a moment.",
            code=ErrorCode.E302_LLM_ERROR,
        ),
    },
]


def map_exception_to_user_error(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
) -> UserFriendlyError:
    """
    Map an exception to a user-friendly error.
    
    Args:
        exception: The exception that occurred
        context: Optional context about what was being done
        
    Returns:
        UserFriendlyError with user-friendly message
    """
    exc_type = type(exception).__name__
    exc_message = str(exception).lower()
    
    # Log full exception for debugging
    logger.error(
        f"Exception occurred: {exc_type}: {exception}",
        exc_info=True,
    )
    
    # Check message patterns FIRST (more specific than type)
    for pattern_info in MESSAGE_PATTERNS:
        if pattern_info["pattern"] in exc_message:
            error = pattern_info["error"]
            if context:
                error = UserFriendlyError(
                    error=error.error,
                    suggestion=error.suggestion,
                    code=error.code,
                    details=context,
                )
            return error
    
    # Then check exception type
    if exc_type in EXCEPTION_MAP:
        error = EXCEPTION_MAP[exc_type]
        if context:
            error = UserFriendlyError(
                error=error.error,
                suggestion=error.suggestion,
                code=error.code,
                details=context,
            )
        return error
    
    # Default fallback
    return UserFriendlyError(
        error="An unexpected error occurred.",
        suggestion="Please try again or contact support if the problem persists.",
        code=ErrorCode.E999_UNKNOWN,
        details=context,
    )


def create_error_response(
    error_message: str,
    suggestion: str,
    code: str = ErrorCode.E999_UNKNOWN,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        error_message: Human-readable error message
        suggestion: What the user can do to fix it
        code: Machine-readable error code
        details: Optional additional context
        
    Returns:
        Dictionary suitable for JSON response
    """
    return UserFriendlyError(
        error=error_message,
        suggestion=suggestion,
        code=code,
        details=details,
    ).to_dict()


def sanitize_error_for_user(error_message: str) -> str:
    """
    Remove technical details from error messages.
    
    Ensures no Python exception names, file paths, or stack traces
    are visible to users.
    """
    # List of patterns to remove
    technical_patterns = [
        "Traceback",
        "File \"",
        "line ",
        "Exception:",
        "Error:",
        ".py",
        "__",
        "module",
        "import",
    ]
    
    result = error_message
    for pattern in technical_patterns:
        if pattern in result:
            # If technical content found, return generic message
            return "An error occurred while processing your request."
    
    return result
