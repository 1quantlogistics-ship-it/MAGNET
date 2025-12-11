"""
magnet/llm/safety/sanitizer.py - Input Sanitization

Sanitizes user input to prevent prompt injection attacks.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger("llm.sanitizer")


# Patterns that could indicate prompt injection attempts
INJECTION_PATTERNS = [
    # Instruction override attempts
    r"(?i)ignore\s+(previous|all|above|prior)\s+instructions?",
    r"(?i)disregard\s+(previous|all|above|prior)\s+instructions?",
    r"(?i)forget\s+(previous|all|above|prior)\s+instructions?",
    r"(?i)new\s+instructions?\s*:",
    # Role/persona manipulation
    r"(?i)you\s+are\s+now\s+",
    r"(?i)pretend\s+to\s+be\s+",
    r"(?i)act\s+as\s+(if\s+you\s+are\s+)?",
    r"(?i)roleplay\s+as\s+",
    # System prompt markers
    r"(?i)system\s*:",
    r"(?i)assistant\s*:",
    r"(?i)user\s*:",
    r"(?i)human\s*:",
    # Special tokens (various LLM formats)
    r"(?i)\[INST\]",
    r"(?i)\[/INST\]",
    r"(?i)<\|system\|>",
    r"(?i)<\|user\|>",
    r"(?i)<\|assistant\|>",
    r"(?i)<<SYS>>",
    r"(?i)<</SYS>>",
    # Delimiter injection
    r"(?i)###\s*(system|instruction|response)",
    r"(?i)---\s*(system|instruction|response)",
]


def sanitize_user_input(text: str, strict: bool = True) -> str:
    """
    Sanitize user input to prevent prompt injection.

    Args:
        text: User input to sanitize
        strict: If True, replace patterns with [FILTERED]. If False, just log.

    Returns:
        Sanitized text
    """
    if not text:
        return text

    original = text
    filtered_count = 0

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text):
            if strict:
                text = re.sub(pattern, "[FILTERED]", text)
                filtered_count += 1
            else:
                logger.warning(f"Potential injection pattern detected: {pattern}")

    # Escape code blocks that might confuse the model
    text = text.replace("```", "'''")

    # Escape potential XML-like tags that might be interpreted as special
    text = re.sub(r"<(/?)(?:system|assistant|user|human|bot)>", r"[\1\2]", text, flags=re.IGNORECASE)

    if filtered_count > 0:
        logger.warning(
            f"Sanitized {filtered_count} potential injection patterns from user input. "
            f"Original length: {len(original)}, sanitized length: {len(text)}"
        )

    return text


def create_safe_prompt(
    system_instruction: str,
    user_content: str,
    context: Optional[str] = None,
    sanitize: bool = True,
) -> str:
    """
    Create a prompt with clear boundaries between system and user content.

    The structure prevents user content from being interpreted as instructions.

    Args:
        system_instruction: System-level instructions (trusted)
        user_content: User-provided content (untrusted)
        context: Optional context data
        sanitize: Whether to sanitize user content

    Returns:
        Structured prompt with clear boundaries
    """
    if sanitize:
        user_content = sanitize_user_input(user_content)

    parts = [system_instruction.strip()]

    if context:
        parts.append("\n\n[CONTEXT]:")
        parts.append(context.strip())

    parts.append("\n\n[USER INPUT]:")
    parts.append(user_content.strip())

    parts.append("\n\n[END USER INPUT]")
    parts.append("\nRespond to the user input above following the system instructions.")

    return "\n".join(parts)


def escape_for_json(text: str) -> str:
    """
    Escape text for safe inclusion in JSON prompts.

    Args:
        text: Text to escape

    Returns:
        JSON-safe text
    """
    # Standard JSON escapes
    text = text.replace("\\", "\\\\")
    text = text.replace('"', '\\"')
    text = text.replace("\n", "\\n")
    text = text.replace("\r", "\\r")
    text = text.replace("\t", "\\t")
    return text


def is_safe_input(text: str) -> bool:
    """
    Check if input appears safe (no injection patterns detected).

    Args:
        text: Text to check

    Returns:
        True if no injection patterns detected
    """
    if not text:
        return True

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text):
            return False

    return True
