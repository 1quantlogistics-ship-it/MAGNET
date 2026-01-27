"""
MAGNET Control Plane v1.1 — Why Query Router

Routes natural language "why" queries to Control Plane explain endpoints.

Architecture:
1. Pattern match (fast, deterministic) → dispatch if confident
2. LLM extraction (slow, flexible) → only when deterministic fails
3. Path validation → reject hallucinated paths
4. Clarification → when unsure, ask don't guess

LLM Fallback Rules (Non-Negotiable):
- LLM produces only structured extraction (WhyQueryExtraction), never answers
- Every extracted path validated against PathRegistry
- LLM only runs when deterministic routing fails
- Low confidence → clarify, don't guess
- All LLM extractions are logged (no auto-promote)

This endpoint is READ-ONLY. It can never change state.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple, TYPE_CHECKING
import hashlib
import json
import logging
import re

from magnet.control_plane.path_registry import (
    PathRegistry,
    PathMetadata,
    get_path_registry,
)
from magnet.control_plane.query import (
    query_explain,
    query_history,
    query_impact,
    DualOutput,
)

if TYPE_CHECKING:
    from magnet.llm.client import LLMClient

logger = logging.getLogger("control_plane.why_router")


# =============================================================================
# DETERMINISM AUDIT COUNTERS (C. Determinism Audit)
# =============================================================================

class RouterMetrics:
    """
    Metrics counters for determinism audit.
    
    Tracks fast path vs LLM fallback rates to ensure pattern/alias
    matching dominates in production.
    
    Usage:
        ROUTER_METRICS.fast_path_hit += 1
        logger.info(f"Metrics: {ROUTER_METRICS.to_dict()}")
    """
    
    def __init__(self):
        self.fast_path_hit = 0       # Pattern/alias match succeeded
        self.llm_fallback_used = 0   # LLM extraction was required
        self.clarify_returned = 0    # Clarification returned (not dispatch)
        self.cache_hit = 0           # Query resolved from cache
        self.total_queries = 0       # Total queries processed
    
    def to_dict(self):
        """Return metrics as dictionary for logging/export."""
        total = self.total_queries or 1  # Avoid division by zero
        return {
            "fast_path_hit": self.fast_path_hit,
            "llm_fallback_used": self.llm_fallback_used,
            "clarify_returned": self.clarify_returned,
            "cache_hit": self.cache_hit,
            "total_queries": self.total_queries,
            "fast_path_rate": round(self.fast_path_hit / total, 3),
            "llm_fallback_rate": round(self.llm_fallback_used / total, 3),
            "cache_hit_rate": round(self.cache_hit / total, 3),
        }
    
    def reset(self):
        """Reset all counters (for testing)."""
        self.fast_path_hit = 0
        self.llm_fallback_used = 0
        self.clarify_returned = 0
        self.cache_hit = 0
        self.total_queries = 0


# Global metrics instance
ROUTER_METRICS = RouterMetrics()


def get_router_metrics() -> RouterMetrics:
    """Get the global router metrics instance."""
    return ROUTER_METRICS


# =============================================================================
# INTENT TYPES
# =============================================================================

class WhyIntent(str, Enum):
    """All supported query intents."""
    EXPLAIN = "explain"      # "Why did X change?" → query_explain
    HISTORY = "history"      # "When did X change?" → query_history
    IMPACT = "impact"        # "What changed in v5?" → query_impact
    DEFINE = "define"        # "What is X?" → PathRegistry lookup
    CLARIFY = "clarify"      # Ambiguous → ask user
    UNKNOWN = "unknown"      # Can't determine


# =============================================================================
# INTENT PATTERNS (Deterministic)
# =============================================================================

# Order matters! More specific patterns should be checked first.
# IMPACT and HISTORY patterns are more specific than EXPLAIN/DEFINE,
# so they should be checked earlier.
INTENT_PATTERNS: Dict[WhyIntent, List[re.Pattern]] = {}

# Define patterns in priority order (more specific first)
_INTENT_PATTERNS_ORDERED = [
    # 1. IMPACT - Most specific (requires version number)
    (WhyIntent.IMPACT, [
        re.compile(r"what (?:changed|happened) in (?:version|v)?\s*(\d+)", re.I),
        re.compile(r"(?:show|get) (?:version|v)\s*(\d+)", re.I),
        re.compile(r"impact (?:of|for) (?:version|v)?\s*(\d+)", re.I),
        re.compile(r"what did (?:version|v)?\s*(\d+) (?:change|do)", re.I),
    ]),
    # 2. HISTORY - More specific (requires history/when keywords)
    (WhyIntent.HISTORY, [
        re.compile(r"(?:show|get|what is) (?:the )?history (?:of|for) .+", re.I),
        re.compile(r"when did .+ (?:change|update)", re.I),
        re.compile(r"how (?:many times|often) (?:did|has) .+ change", re.I),
        re.compile(r"(?:all )?changes (?:to|for|of) .+", re.I),
    ]),
    # 3. EXPLAIN - General why questions
    (WhyIntent.EXPLAIN, [
        re.compile(r"why (?:did|does|is|was|has) .+", re.I),
        re.compile(r"what (?:caused|changed) .+", re.I),
        re.compile(r"explain (?:why|the|this)? ?.+", re.I),
        re.compile(r"how did .+ (?:change|get|become)", re.I),
    ]),
    # 4. DEFINE - Definitions (most general "what is" patterns)
    (WhyIntent.DEFINE, [
        re.compile(r"what (?:is|are|does) .+\??", re.I),
        re.compile(r"define .+", re.I),
        re.compile(r"tell me about .+", re.I),
        re.compile(r"what does .+ mean", re.I),
        re.compile(r"explain .+ to me", re.I),
    ]),
]

# Build the dict preserving order (Python 3.7+ dicts are ordered)
for intent, patterns in _INTENT_PATTERNS_ORDERED:
    INTENT_PATTERNS[intent] = patterns


# =============================================================================
# REQUEST/RESPONSE TYPES
# =============================================================================

@dataclass
class WhyQueryRequest:
    """Request for /why endpoint."""
    query: str                                  # Natural language query
    design_id: str                              # Design to query
    context_paths: Optional[List[str]] = None   # Last paths discussed (stateless)
    context_version: Optional[int] = None       # Last version mentioned


@dataclass
class WhyQueryExtraction:
    """
    Structured extraction from query (deterministic or LLM).
    
    LLM output MUST match this schema. No freeform text.
    """
    intent: WhyIntent
    paths: List[str]                            # Validated paths
    version: Optional[int] = None               # For impact queries
    confidence: float = 0.0                     # 0.0-1.0
    clarification_needed: Optional[str] = None  # If ambiguous
    source: Literal["pattern", "llm", "context"] = "pattern"


@dataclass
class SingleResult:
    """Result for a single path/version query."""
    path: Optional[str]
    version: Optional[int]
    output: DualOutput


@dataclass
class WhyQueryResult:
    """Response from /why endpoint."""
    intent: WhyIntent
    results: List[SingleResult]
    truncated: bool = False
    clarification: Optional[str] = None
    extraction: Optional[WhyQueryExtraction] = None


@dataclass
class DefineResult:
    """Result for "What is X?" queries."""
    found: bool
    path: str
    label: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    group: Optional[str] = None
    is_derived: Optional[bool] = None
    synonyms: Optional[List[str]] = None


# =============================================================================
# PATTERN CANDIDATE LOGGING (for review, never auto-promote)
# =============================================================================

@dataclass
class PatternCandidate:
    """A candidate pattern learned from LLM extraction."""
    query: str
    extracted_intent: str
    extracted_paths: List[str]
    confidence: float
    timestamp: str
    design_id: str


# In-memory log for this session (would be persisted in production)
PATTERN_CANDIDATES_LOG: List[PatternCandidate] = []


def log_llm_extraction(
    query: str,
    extraction: WhyQueryExtraction,
    design_id: str,
) -> None:
    """
    Log successful LLM extractions as pattern candidates.
    
    These are NEVER auto-promoted. A human must review.
    """
    candidate = PatternCandidate(
        query=query,
        extracted_intent=extraction.intent.value,
        extracted_paths=extraction.paths,
        confidence=extraction.confidence,
        timestamp=datetime.now(timezone.utc).isoformat(),
        design_id=design_id,
    )
    PATTERN_CANDIDATES_LOG.append(candidate)
    
    logger.info(
        f"LLM extraction logged for review: "
        f"query={query!r}, intent={extraction.intent.value}, "
        f"paths={extraction.paths}, confidence={extraction.confidence}"
    )


# =============================================================================
# WHY QUERY ROUTER
# =============================================================================

class WhyQueryRouter:
    """
    Routes natural language queries to Control Plane endpoints.
    
    Resolution order:
    1. Pattern match + alias lookup (fast, deterministic)
    2. LLM extraction if deterministic fails (slow, flexible)
    3. Path validation against PathRegistry
    4. Clarification if confidence < threshold
    """
    
    CONFIDENCE_THRESHOLD = 0.7
    MAX_PATHS = 3
    
    def __init__(
        self,
        registry: Optional[PathRegistry] = None,
        llm_client: Optional["LLMClient"] = None,
    ):
        self._registry = registry or get_path_registry()
        self._llm_client = llm_client
        self._cache: Dict[str, WhyQueryExtraction] = {}  # query_hash → extraction
        self._cache_ttl_seconds = 300  # 5 minutes
    
    def resolve(self, request: WhyQueryRequest) -> WhyQueryResult:
        """
        Resolve a natural language query and dispatch to appropriate endpoint.
        
        This is the main entry point.
        """
        # Track total queries
        ROUTER_METRICS.total_queries += 1
        
        query = request.query.strip()
        if not query:
            ROUTER_METRICS.clarify_returned += 1
            logger.debug("router.clarify_returned: empty query")
            return WhyQueryResult(
                intent=WhyIntent.CLARIFY,
                results=[],
                clarification="Please enter a question.",
            )
        
        # 1. Check cache
        cache_key = self._cache_key(request.design_id, query)
        cached = self._cache.get(cache_key)
        if cached and cached.confidence >= self.CONFIDENCE_THRESHOLD:
            ROUTER_METRICS.cache_hit += 1
            logger.debug(f"router.cache_hit: query={query!r}")
            return self._dispatch(cached, request.design_id)
        
        # 2. Try deterministic extraction
        extraction = self._extract_deterministic(query, request)
        used_llm = False
        
        # 3. If deterministic fails or low confidence, try LLM
        if extraction.intent == WhyIntent.UNKNOWN or extraction.confidence < self.CONFIDENCE_THRESHOLD:
            if self._llm_client:
                llm_extraction = self._extract_with_llm(query, request)
                if llm_extraction and llm_extraction.confidence > extraction.confidence:
                    extraction = llm_extraction
                    used_llm = True
                    # Log for review (never auto-promote)
                    log_llm_extraction(query, extraction, request.design_id)
        
        # Track fast path vs LLM fallback
        if used_llm:
            ROUTER_METRICS.llm_fallback_used += 1
            logger.info(f"router.llm_fallback_used: query={query!r}")
        else:
            ROUTER_METRICS.fast_path_hit += 1
            logger.debug(f"router.fast_path_hit: query={query!r}, intent={extraction.intent.value}")
        
        # 4. Validate paths
        extraction = self._validate_paths(extraction)
        
        # 5. Cache if confident
        if extraction.confidence >= self.CONFIDENCE_THRESHOLD:
            self._cache[cache_key] = extraction
        
        # 6. Dispatch or clarify
        if extraction.confidence < self.CONFIDENCE_THRESHOLD or extraction.intent == WhyIntent.CLARIFY:
            ROUTER_METRICS.clarify_returned += 1
            logger.debug(
                f"router.clarify_returned: query={query!r}, confidence={extraction.confidence:.2f}"
            )
            return self._build_clarification(extraction, query)
        
        # Log metrics periodically
        if ROUTER_METRICS.total_queries % 100 == 0:
            logger.info(f"router.metrics: {ROUTER_METRICS.to_dict()}")
        
        return self._dispatch(extraction, request.design_id)
    
    def _cache_key(self, design_id: str, query: str) -> str:
        """Generate cache key for a query."""
        normalized = query.lower().strip()
        h = hashlib.sha256(f"{design_id}:{normalized}".encode()).hexdigest()[:16]
        return h
    
    # =========================================================================
    # DETERMINISTIC EXTRACTION
    # =========================================================================
    
    def _extract_deterministic(
        self,
        query: str,
        request: WhyQueryRequest,
    ) -> WhyQueryExtraction:
        """
        Extract intent and entities using patterns and aliases.
        
        This is the fast path—no LLM involved.
        """
        intent = WhyIntent.UNKNOWN
        version: Optional[int] = None
        confidence = 0.0
        
        # 1. Match intent patterns
        for candidate_intent, patterns in INTENT_PATTERNS.items():
            for pattern in patterns:
                match = pattern.search(query)
                if match:
                    intent = candidate_intent
                    confidence = 0.8  # Pattern match is fairly confident
                    
                    # Extract version number for IMPACT
                    if candidate_intent == WhyIntent.IMPACT and match.groups():
                        try:
                            version = int(match.group(1))
                        except (ValueError, IndexError):
                            pass
                    break
            if intent != WhyIntent.UNKNOWN:
                break
        
        # 2. Extract paths from query
        paths = self._extract_paths_from_query(query, request.context_paths)
        
        # 3. Adjust confidence based on path extraction
        if not paths and intent not in (WhyIntent.IMPACT, WhyIntent.UNKNOWN):
            # Need paths but didn't find any
            confidence *= 0.5
        
        if paths:
            confidence = min(1.0, confidence + 0.1 * len(paths))
        
        # 4. Handle context for follow-ups
        if not paths and request.context_paths:
            # "What else changed?" with context
            context_keywords = ["else", "other", "another", "more", "that"]
            if any(kw in query.lower() for kw in context_keywords):
                paths = request.context_paths[:1]  # Use last context
                confidence = 0.6  # Lower confidence for context-based
        
        return WhyQueryExtraction(
            intent=intent,
            paths=paths,
            version=version,
            confidence=confidence,
            source="pattern",
        )
    
    def _extract_paths_from_query(
        self,
        query: str,
        context_paths: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Extract path references from natural language query.
        
        Uses PathRegistry aliases and fuzzy matching.
        """
        # Get candidate paths from registry
        candidates = self._registry.get_candidates_for_query(query, limit=10)
        
        if not candidates:
            return []
        
        # If only one high-confidence candidate, use it
        if len(candidates) == 1:
            return [candidates[0].path]
        
        # Try to narrow down using query words
        query_lower = query.lower()
        matched_paths = []
        
        for meta in candidates:
            # Check if any synonym appears in query
            for syn in meta.synonyms:
                if syn.lower() in query_lower:
                    matched_paths.append(meta.path)
                    break
            else:
                # Check path segments
                path_lower = meta.path.lower()
                last_segment = path_lower.split(".")[-1]
                if last_segment in query_lower:
                    matched_paths.append(meta.path)
        
        # Dedupe while preserving order
        seen = set()
        result = []
        for p in matched_paths:
            if p not in seen:
                seen.add(p)
                result.append(p)
        
        return result[:self.MAX_PATHS]
    
    # =========================================================================
    # LLM EXTRACTION (Disciplined Fallback)
    # =========================================================================
    
    def _extract_with_llm(
        self,
        query: str,
        request: WhyQueryRequest,
    ) -> Optional[WhyQueryExtraction]:
        """
        Extract intent and entities using LLM.
        
        Rules:
        - Only runs when deterministic fails
        - LLM chooses from candidate list (no hallucination)
        - Output must be JSON matching WhyQueryExtraction
        - All extractions logged for review
        """
        if not self._llm_client:
            return None
        
        try:
            # 1. Get top candidates via fuzzy match (constrain LLM choices)
            candidates = self._registry.get_candidates_for_query(query, limit=20)
            candidate_paths = [c.path for c in candidates]
            
            if not candidate_paths:
                # No candidates = nothing for LLM to choose from
                return None
            
            # 2. Build prompt
            prompt = self._build_llm_prompt(query, candidate_paths, request.context_paths)
            
            # 3. Call LLM with structured output
            response = self._call_llm(prompt)
            
            if not response:
                return None
            
            # 4. Parse response
            extraction = self._parse_llm_response(response, candidate_paths)
            
            return extraction
            
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            # Degrade gracefully—don't fail the whole request
            return None
    
    def _build_llm_prompt(
        self,
        query: str,
        candidate_paths: List[str],
        context_paths: Optional[List[str]],
    ) -> str:
        """
        Build LLM prompt for extraction.
        
        Key constraints:
        - LLM must choose from candidate_paths only
        - Output must be JSON only
        - Must include confidence score
        """
        # Format candidates with labels for better LLM understanding
        candidates_formatted = []
        for path in candidate_paths:
            meta = self._registry.get(path)
            if meta:
                candidates_formatted.append(f"  - {path}: {meta.label} ({meta.description or 'no description'})")
            else:
                candidates_formatted.append(f"  - {path}")
        
        candidates_str = "\n".join(candidates_formatted)
        
        context_str = ""
        if context_paths:
            context_str = f"\nRecent context paths: {', '.join(context_paths)}"
        
        return f"""You are a query router for a ship design system. Extract the user's intent and the relevant paths from their question.

ALLOWED INTENTS:
- "explain": User asks why something changed or what caused a change
- "history": User asks about change history over time
- "impact": User asks what changed in a specific version number
- "define": User asks what something means or is
- "clarify": You cannot determine what the user wants

ALLOWED PATHS (you MUST choose from this list only):
{candidates_str}
{context_str}

USER QUERY: {query}

Respond with JSON only, no other text. Schema:
{{
  "intent": "explain" | "history" | "impact" | "define" | "clarify",
  "paths": ["path1", "path2"],  // From allowed list only. Empty if clarify.
  "version": null | number,  // Only for impact intent
  "confidence": 0.0-1.0,  // How confident you are
  "clarification_needed": null | "question to ask user"  // If clarify
}}

JSON:"""
    
    def _call_llm(self, prompt: str) -> Optional[str]:
        """Call LLM and get response. Returns None if unavailable."""
        if not self._llm_client:
            return None
        
        try:
            # Check availability
            if hasattr(self._llm_client, 'is_available'):
                if not self._llm_client.is_available():
                    logger.debug("LLM not available")
                    return None
            
            # Call LLM (synchronous for now)
            import asyncio
            
            async def _async_call():
                return await self._llm_client.complete(
                    prompt,
                    max_tokens=200,
                    temperature=0,
                )
            
            # Run in event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an async context, create a task
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        future = pool.submit(asyncio.run, _async_call())
                        response = future.result(timeout=5)
                else:
                    response = loop.run_until_complete(_async_call())
            except RuntimeError:
                response = asyncio.run(_async_call())
            
            return response
            
        except Exception as e:
            logger.warning(f"LLM call failed: {e}")
            return None
    
    def _parse_llm_response(
        self,
        response: str,
        candidate_paths: List[str],
    ) -> Optional[WhyQueryExtraction]:
        """
        Parse LLM response into WhyQueryExtraction.
        
        Validates that paths are from candidate list.
        """
        try:
            # Extract JSON from response
            response = response.strip()
            if response.startswith("```"):
                # Remove markdown code block
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
            data = json.loads(response)
            
            # Validate intent
            intent_str = data.get("intent", "unknown")
            try:
                intent = WhyIntent(intent_str)
            except ValueError:
                intent = WhyIntent.UNKNOWN
            
            # Validate paths (MUST be from candidate list)
            raw_paths = data.get("paths", [])
            valid_paths = []
            candidate_set = set(candidate_paths)
            
            for p in raw_paths:
                if p in candidate_set:
                    valid_paths.append(p)
                else:
                    logger.warning(f"LLM hallucinated path {p!r}, rejecting")
            
            confidence = float(data.get("confidence", 0.5))
            
            # Lower confidence if we rejected paths
            if len(valid_paths) < len(raw_paths):
                confidence *= 0.7
            
            return WhyQueryExtraction(
                intent=intent,
                paths=valid_paths,
                version=data.get("version"),
                confidence=confidence,
                clarification_needed=data.get("clarification_needed"),
                source="llm",
            )
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return None
    
    # =========================================================================
    # PATH VALIDATION
    # =========================================================================
    
    def _validate_paths(self, extraction: WhyQueryExtraction) -> WhyQueryExtraction:
        """
        Validate all paths against PathRegistry.
        
        Rejects any path not in registry.
        """
        valid_paths = []
        
        for path in extraction.paths:
            if self._registry.exists(path):
                valid_paths.append(path)
            else:
                # Try to resolve as alias
                resolved = self._registry.resolve_alias(path)
                if resolved:
                    valid_paths.append(resolved)
                else:
                    logger.warning(f"Rejected invalid path: {path!r}")
        
        # Adjust confidence if we rejected paths
        confidence = extraction.confidence
        if len(valid_paths) < len(extraction.paths):
            confidence *= 0.8
        
        return WhyQueryExtraction(
            intent=extraction.intent,
            paths=valid_paths,
            version=extraction.version,
            confidence=confidence,
            clarification_needed=extraction.clarification_needed,
            source=extraction.source,
        )
    
    # =========================================================================
    # CLARIFICATION
    # =========================================================================
    
    def _build_clarification(
        self,
        extraction: WhyQueryExtraction,
        original_query: str,
    ) -> WhyQueryResult:
        """Build a clarification response when unsure."""
        if extraction.clarification_needed:
            clarification = extraction.clarification_needed
        elif not extraction.paths:
            clarification = (
                "I'm not sure which parameter you're asking about. "
                "Could you be more specific? For example:\n"
                "• \"Why did the beam change?\"\n"
                "• \"What is GM?\"\n"
                "• \"What changed in version 3?\""
            )
        elif len(extraction.paths) > 1:
            path_labels = []
            for p in extraction.paths:
                meta = self._registry.get(p)
                label = meta.label if meta else p.split(".")[-1]
                path_labels.append(f"{label} ({p})")
            
            clarification = (
                f"Did you mean one of these?\n"
                f"• " + "\n• ".join(path_labels)
            )
        else:
            clarification = "I'm not confident I understood that. Could you rephrase?"
        
        return WhyQueryResult(
            intent=WhyIntent.CLARIFY,
            results=[],
            clarification=clarification,
            extraction=extraction,
        )
    
    # =========================================================================
    # DISPATCH
    # =========================================================================
    
    def _dispatch(
        self,
        extraction: WhyQueryExtraction,
        design_id: str,
    ) -> WhyQueryResult:
        """Dispatch extraction to appropriate query endpoint."""
        results: List[SingleResult] = []
        truncated = False
        clarification = None
        
        # Cap paths
        paths = extraction.paths[:self.MAX_PATHS]
        if len(extraction.paths) > self.MAX_PATHS:
            truncated = True
            clarification = (
                f"Found {len(extraction.paths)} matching paths. "
                f"Showing first {self.MAX_PATHS}."
            )
        
        if extraction.intent == WhyIntent.EXPLAIN:
            for path in paths:
                output = query_explain(path, design_id)
                results.append(SingleResult(path=path, version=None, output=output))
        
        elif extraction.intent == WhyIntent.HISTORY:
            for path in paths:
                output = query_history(path, design_id)
                results.append(SingleResult(path=path, version=None, output=output))
        
        elif extraction.intent == WhyIntent.IMPACT:
            if extraction.version is not None:
                output = query_impact(extraction.version, design_id)
                results.append(SingleResult(path=None, version=extraction.version, output=output))
            else:
                return WhyQueryResult(
                    intent=WhyIntent.CLARIFY,
                    results=[],
                    clarification="Which version would you like to know about?",
                )
        
        elif extraction.intent == WhyIntent.DEFINE:
            for path in paths:
                meta = self._registry.get(path)
                if meta:
                    # Build narrative for define
                    narrative = self._build_define_narrative(meta)
                    schema = meta.to_dict()
                    output = DualOutput(
                        narrative=narrative,
                        schema=schema,
                        query_type="define",
                        query_params={"path": path},
                        record_count=1,
                    )
                    results.append(SingleResult(path=path, version=None, output=output))
        
        return WhyQueryResult(
            intent=extraction.intent,
            results=results,
            truncated=truncated,
            clarification=clarification,
            extraction=extraction,
        )
    
    def _build_define_narrative(self, meta: PathMetadata) -> str:
        """Build narrative for "What is X?" queries."""
        parts = [f"**{meta.label}** (`{meta.path}`)"]
        
        if meta.description:
            parts.append(f"\n{meta.description}")
        
        if meta.unit:
            parts.append(f"\n• Unit: {meta.unit}")
        
        if meta.is_derived:
            parts.append("\n• This is a *derived* value (computed from other parameters)")
        else:
            parts.append("\n• This is a *primary* parameter (user-settable)")
        
        if meta.synonyms:
            parts.append(f"\n• Also known as: {', '.join(meta.synonyms[:5])}")
        
        return "".join(parts)


# =============================================================================
# SINGLETON
# =============================================================================

_router: Optional[WhyQueryRouter] = None


def get_why_router(llm_client: Optional["LLMClient"] = None) -> WhyQueryRouter:
    """Get the global WhyQueryRouter singleton."""
    global _router
    if _router is None:
        _router = WhyQueryRouter(llm_client=llm_client)
    return _router


def reset_why_router() -> None:
    """Reset the global WhyQueryRouter (for testing)."""
    global _router
    _router = None

