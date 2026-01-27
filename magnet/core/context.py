"""
magnet/core/context.py - Single source of truth for AppContext creation.

Goal:
- Ensure MAGNET FastAPI app works identically whether started via:
  - `python3 -m magnet.bootstrap.app --api` (bootstrap path)
  - `uvicorn magnet.deployment.api:app ...` (direct uvicorn import)

This module is the only place that:
- loads `.env` (python-dotenv)
- validates required env/config values up-front (startup, not first request)
- performs quick DB connectivity health checks (non-driver socket probe)
- returns an initialized AppContext with DI container wired
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any
import os
import socket
from urllib.parse import urlparse
import logging

logger = logging.getLogger("core.context")

# Singleton cache for process lifetime (uvicorn single-worker / per-worker process)
_CTX = None


class ContextValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ContextBuildInfo:
    startup_path: str  # "bootstrap" | "uvicorn"
    dotenv_loaded: bool
    required_env: tuple[str, ...]
    db_url: Optional[str]


def _load_dotenv_if_present() -> bool:
    """Load .env if present. Returns True if a .env file was loaded."""
    try:
        from dotenv import load_dotenv, find_dotenv
    except Exception as e:
        raise ContextValidationError(
            "python-dotenv is required for MAGNET startup. "
            "Install dependency `python-dotenv`."
        ) from e

    env_path = find_dotenv(usecwd=True)
    if not env_path:
        return False
    load_dotenv(env_path, override=False)
    return True


def _required_env_vars() -> list[str]:
    """
    Required env var list.

    Defaults are intentionally minimal to avoid false negatives in dev/tests.
    If you want strict enforcement, set:
      MAGNET_REQUIRED_ENV_VARS="ANTHROPIC_API_KEY,DATABASE_URL"
    """
    raw = (os.getenv("MAGNET_REQUIRED_ENV_VARS") or "").strip()
    if raw:
        return [v.strip() for v in raw.split(",") if v.strip()]
    # Default: require Anthropic key only if provider is anthropic (config validation handles this).
    return []


def _resolve_db_url_from_env() -> Optional[str]:
    """
    Resolve a DB URL from environment.
    Supports:
    - DATABASE_URL (preferred)
    - MAGNET_DATABASE_URL (alias)
    - MAGNET_DB_* fields (bootstrap config builds a connection_string too, but
      this function is used before config is built).
    """
    db_url = os.getenv("DATABASE_URL") or os.getenv("MAGNET_DATABASE_URL")
    if db_url:
        return db_url

    # Construct from MAGNET_DB_* if explicitly set
    host = os.getenv("MAGNET_DB_HOST")
    name = os.getenv("MAGNET_DB_NAME")
    user = os.getenv("MAGNET_DB_USER")
    password = os.getenv("MAGNET_DB_PASSWORD", "")
    port = os.getenv("MAGNET_DB_PORT", "5432")
    if host and name and user:
        return f"postgresql://{user}:{password}@{host}:{port}/{name}"
    return None


def _validate_required_env() -> tuple[str, ...]:
    missing = [v for v in _required_env_vars() if not os.getenv(v)]
    if missing:
        raise ContextValidationError(f"Missing required env vars: {missing}")
    return tuple(_required_env_vars())


def _validate_llm_config(config) -> None:
    """
    Validate LLM config. If the provider is anthropic, require a key.
    This is a startup-time check (fail fast).
    """
    try:
        provider = getattr(getattr(config, "llm", None), "provider", "") or ""
        api_key = getattr(getattr(config, "llm", None), "api_key", "") or ""
    except Exception:
        provider = ""
        api_key = ""

    if provider.lower() == "anthropic" and not api_key:
        raise ContextValidationError(
            "Missing ANTHROPIC_API_KEY (or MAGNET_LLM_API_KEY) for anthropic provider."
        )


def _db_socket_healthcheck(db_url: str, timeout_s: float = 1.0) -> None:
    """
    Driver-free DB connectivity check.
    This verifies DNS + TCP connectivity only (not auth).
    """
    try:
        u = urlparse(db_url)
        host = u.hostname
        port = u.port or (5432 if (u.scheme or "").startswith("postgres") else None)
        if not host or not port:
            raise ContextValidationError(f"Invalid DATABASE_URL (missing host/port): {db_url!r}")
        with socket.create_connection((host, int(port)), timeout=timeout_s):
            return
    except ContextValidationError:
        raise
    except Exception as e:
        raise ContextValidationError(f"DB connectivity check failed for {db_url!r}: {e}") from e


def validate_context(context) -> ContextBuildInfo:
    """
    Validate an already-built context (bootstrap path).
    Ensures required services resolve and optional DB connectivity is OK if configured.
    """
    dotenv_loaded = _load_dotenv_if_present()
    required_env = _validate_required_env()

    if context is None or getattr(context, "container", None) is None:
        raise ContextValidationError("AppContext/container not initialized")

    # Validate LLM env/config
    if getattr(context, "config", None) is not None:
        _validate_llm_config(context.config)

    # DB URL resolution:
    # - prefer DATABASE_URL if set
    # - else fall back to bootstrap config.database.connection_string
    db_url = _resolve_db_url_from_env()
    if not db_url:
        try:
            db_url = getattr(getattr(context.config, "database", None), "connection_string", None)
        except Exception:
            db_url = None

    # If DATABASE_URL is explicitly configured or listed as required, enforce connectivity.
    strict_db = ("DATABASE_URL" in required_env) or bool(os.getenv("DATABASE_URL") or os.getenv("MAGNET_DATABASE_URL"))
    if strict_db:
        if not db_url:
            raise ContextValidationError("DATABASE_URL is required but not set")
        _db_socket_healthcheck(db_url)

    return ContextBuildInfo(
        startup_path="bootstrap",
        dotenv_loaded=dotenv_loaded,
        required_env=required_env,
        db_url=db_url,
    )


def get_or_create_context(existing_context=None, *, config_file: Optional[str] = None, startup_path: str = "uvicorn"):
    """
    Create (or validate and return) an AppContext.

    - If `existing_context` is provided, it is validated and returned (no duplicates).
    - Else, a single process-global context is created, validated, cached, and returned.
    """
    global _CTX

    if existing_context is not None:
        info = validate_context(existing_context)
        try:
            existing_context.metadata["startup"] = {
                **(existing_context.metadata.get("startup") or {}),
                "path": startup_path,
                "dotenv_loaded": info.dotenv_loaded,
                "required_env": list(info.required_env),
                "db_url": info.db_url,
            }
        except Exception:
            pass
        return existing_context

    if _CTX is not None:
        return _CTX

    # Load env + validate required vars before building container (fail-fast)
    dotenv_loaded = _load_dotenv_if_present()
    required_env = _validate_required_env()

    try:
        from magnet.bootstrap.app import MAGNETApp
    except Exception as e:
        raise ContextValidationError(f"Failed to import bootstrap MAGNETApp: {e}") from e

    app = MAGNETApp(config_file).build()
    ctx = app.context

    # Validate config-based requirements (e.g., LLM provider key)
    if getattr(ctx, "config", None) is not None:
        _validate_llm_config(ctx.config)

    db_url = _resolve_db_url_from_env()
    if not db_url:
        try:
            db_url = getattr(getattr(ctx.config, "database", None), "connection_string", None)
        except Exception:
            db_url = None

    strict_db = ("DATABASE_URL" in required_env) or bool(os.getenv("DATABASE_URL") or os.getenv("MAGNET_DATABASE_URL"))
    if strict_db:
        if not db_url:
            raise ContextValidationError("DATABASE_URL is required but not set")
        _db_socket_healthcheck(db_url)

    try:
        ctx.metadata["startup"] = {
            "path": startup_path,
            "dotenv_loaded": dotenv_loaded,
            "required_env": list(required_env),
            "db_url": db_url,
        }
    except Exception:
        pass

    _CTX = ctx
    logger.info(f"AppContext initialized via {startup_path} (dotenv_loaded={dotenv_loaded})")
    return _CTX

