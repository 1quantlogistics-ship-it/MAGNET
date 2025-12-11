"""
bootstrap/config.py - Application configuration v1.1

Module 55: Bootstrap Layer

Provides configuration loading from files, environment variables, and defaults.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path
import os
import json
import logging

logger = logging.getLogger("bootstrap.config")


@dataclass
class LLMConfig:
    """LLM provider configuration with safety features."""

    # Provider settings
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    api_key: str = ""
    base_url: Optional[str] = None  # For local LLM (Ollama)
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout_seconds: int = 120

    # Safety & Cost Control
    fallback_to_deterministic: bool = True  # Use fallback if LLM fails
    retry_attempts: int = 2  # Retry on transient errors
    retry_delay_ms: int = 1000  # Delay between retries
    max_requests_per_minute: int = 60  # Rate limit
    max_cost_per_session_usd: float = 5.0  # Cost cap

    # Caching
    enable_caching: bool = True  # Enable response caching
    cache_ttl_seconds: int = 3600  # Cache TTL (1 hour)

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            # Provider settings
            provider=os.getenv("MAGNET_LLM_PROVIDER", "anthropic"),
            model=os.getenv("MAGNET_LLM_MODEL", "claude-sonnet-4-20250514"),
            api_key=os.getenv("MAGNET_LLM_API_KEY", os.getenv("ANTHROPIC_API_KEY", "")),
            base_url=os.getenv("MAGNET_LLM_BASE_URL"),
            max_tokens=int(os.getenv("MAGNET_LLM_MAX_TOKENS", "4096")),
            temperature=float(os.getenv("MAGNET_LLM_TEMPERATURE", "0.7")),
            timeout_seconds=int(os.getenv("MAGNET_LLM_TIMEOUT", "120")),
            # Safety & Cost Control
            fallback_to_deterministic=os.getenv("MAGNET_LLM_FALLBACK", "true").lower() == "true",
            retry_attempts=int(os.getenv("MAGNET_LLM_RETRY_ATTEMPTS", "2")),
            retry_delay_ms=int(os.getenv("MAGNET_LLM_RETRY_DELAY_MS", "1000")),
            max_requests_per_minute=int(os.getenv("MAGNET_LLM_RATE_LIMIT", "60")),
            max_cost_per_session_usd=float(os.getenv("MAGNET_LLM_MAX_COST", "5.0")),
            # Caching
            enable_caching=os.getenv("MAGNET_LLM_CACHE", "true").lower() == "true",
            cache_ttl_seconds=int(os.getenv("MAGNET_LLM_CACHE_TTL", "3600")),
        )


@dataclass
class APIConfig:
    """API server configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    enable_docs: bool = True
    docs_url: str = "/docs"
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    rate_limit_rpm: int = 60

    @classmethod
    def from_env(cls) -> "APIConfig":
        cors = os.getenv("MAGNET_API_CORS_ORIGINS", "*")
        return cls(
            host=os.getenv("MAGNET_API_HOST", "0.0.0.0"),
            port=int(os.getenv("MAGNET_API_PORT", "8000")),
            workers=int(os.getenv("MAGNET_API_WORKERS", "4")),
            enable_docs=os.getenv("MAGNET_API_ENABLE_DOCS", "true").lower() == "true",
            docs_url=os.getenv("MAGNET_API_DOCS_URL", "/docs"),
            cors_origins=cors.split(",") if cors else ["*"],
            rate_limit_rpm=int(os.getenv("MAGNET_API_RATE_LIMIT", "60")),
        )


@dataclass
class StorageConfig:
    """Storage paths configuration."""

    base_dir: str = "./storage"
    designs_dir: str = "./storage/designs"
    reports_dir: str = "./storage/reports"
    snapshots_dir: str = "./storage/snapshots"
    exports_dir: str = "./storage/exports"
    temp_dir: str = "./storage/temp"

    @classmethod
    def from_env(cls) -> "StorageConfig":
        base = os.getenv("MAGNET_STORAGE_DIR", "./storage")
        return cls(
            base_dir=base,
            designs_dir=os.getenv("MAGNET_DESIGNS_DIR", f"{base}/designs"),
            reports_dir=os.getenv("MAGNET_REPORTS_DIR", f"{base}/reports"),
            snapshots_dir=os.getenv("MAGNET_SNAPSHOTS_DIR", f"{base}/snapshots"),
            exports_dir=os.getenv("MAGNET_EXPORTS_DIR", f"{base}/exports"),
            temp_dir=os.getenv("MAGNET_TEMP_DIR", f"{base}/temp"),
        )


@dataclass
class AgentConfig:
    """Agent system configuration."""

    max_iterations_per_phase: int = 5
    max_total_iterations: int = 50
    parallel_agents: bool = False
    agent_timeout_seconds: int = 300
    enable_explanations: bool = True

    @classmethod
    def from_env(cls) -> "AgentConfig":
        return cls(
            max_iterations_per_phase=int(os.getenv("MAGNET_AGENT_MAX_ITER", "5")),
            max_total_iterations=int(os.getenv("MAGNET_AGENT_MAX_TOTAL", "50")),
            parallel_agents=os.getenv("MAGNET_AGENT_PARALLEL", "false").lower() == "true",
            agent_timeout_seconds=int(os.getenv("MAGNET_AGENT_TIMEOUT", "300")),
            enable_explanations=os.getenv("MAGNET_AGENT_EXPLAIN", "true").lower() == "true",
        )


@dataclass
class DatabaseConfig:
    """Database configuration."""

    host: str = "localhost"
    port: int = 5432
    name: str = "magnet"
    user: str = "magnet"
    password: str = ""
    pool_size: int = 5

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        return cls(
            host=os.getenv("MAGNET_DB_HOST", "localhost"),
            port=int(os.getenv("MAGNET_DB_PORT", "5432")),
            name=os.getenv("MAGNET_DB_NAME", "magnet"),
            user=os.getenv("MAGNET_DB_USER", "magnet"),
            password=os.getenv("MAGNET_DB_PASSWORD", ""),
            pool_size=int(os.getenv("MAGNET_DB_POOL_SIZE", "5")),
        )

    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: Optional[str] = None
    json_logs: bool = False

    @classmethod
    def from_env(cls) -> "LoggingConfig":
        return cls(
            level=os.getenv("MAGNET_LOG_LEVEL", "INFO"),
            format=os.getenv("MAGNET_LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            log_file=os.getenv("MAGNET_LOG_FILE"),
            json_logs=os.getenv("MAGNET_JSON_LOGS", "false").lower() == "true",
        )


@dataclass
class MAGNETConfig:
    """Root configuration for MAGNET application."""

    environment: str = "development"
    debug: bool = False
    version: str = "1.1.0"

    llm: LLMConfig = field(default_factory=LLMConfig)
    api: APIConfig = field(default_factory=APIConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # Additional settings
    settings: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "MAGNETConfig":
        """Create configuration from environment variables."""
        return cls(
            environment=os.getenv("MAGNET_ENVIRONMENT", "development"),
            debug=os.getenv("MAGNET_DEBUG", "false").lower() == "true",
            llm=LLMConfig.from_env(),
            api=APIConfig.from_env(),
            storage=StorageConfig.from_env(),
            agent=AgentConfig.from_env(),
            database=DatabaseConfig.from_env(),
            logging=LoggingConfig.from_env(),
        )

    @classmethod
    def from_file(cls, filepath: str) -> "MAGNETConfig":
        """Load configuration from JSON file."""
        path = Path(filepath)
        if not path.exists():
            logger.warning(f"Config file not found: {filepath}, using defaults")
            return cls.from_env()

        with open(path) as f:
            data = json.load(f)

        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "MAGNETConfig":
        """Create config from dictionary."""
        config = cls.from_env()

        # Override with file values
        if "environment" in data:
            config.environment = data["environment"]
        if "debug" in data:
            config.debug = data["debug"]

        if "llm" in data:
            for key, value in data["llm"].items():
                if hasattr(config.llm, key):
                    setattr(config.llm, key, value)

        if "api" in data:
            for key, value in data["api"].items():
                if hasattr(config.api, key):
                    setattr(config.api, key, value)

        if "storage" in data:
            for key, value in data["storage"].items():
                if hasattr(config.storage, key):
                    setattr(config.storage, key, value)

        if "agent" in data:
            for key, value in data["agent"].items():
                if hasattr(config.agent, key):
                    setattr(config.agent, key, value)

        if "database" in data:
            for key, value in data["database"].items():
                if hasattr(config.database, key):
                    setattr(config.database, key, value)

        if "logging" in data:
            for key, value in data["logging"].items():
                if hasattr(config.logging, key):
                    setattr(config.logging, key, value)

        if "settings" in data:
            config.settings.update(data["settings"])

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Serialize config to dictionary."""
        return {
            "environment": self.environment,
            "debug": self.debug,
            "version": self.version,
            "llm": {
                "provider": self.llm.provider,
                "model": self.llm.model,
                "max_tokens": self.llm.max_tokens,
                "temperature": self.llm.temperature,
            },
            "api": {
                "host": self.api.host,
                "port": self.api.port,
                "workers": self.api.workers,
            },
            "storage": {
                "base_dir": self.storage.base_dir,
                "designs_dir": self.storage.designs_dir,
            },
            "agent": {
                "max_iterations_per_phase": self.agent.max_iterations_per_phase,
                "max_total_iterations": self.agent.max_total_iterations,
            },
        }


# Global config instance
_config: Optional[MAGNETConfig] = None


def load_config(filepath: str = None) -> MAGNETConfig:
    """
    Load configuration from file or environment.

    Args:
        filepath: Optional path to JSON config file

    Returns:
        MAGNETConfig instance
    """
    global _config

    if filepath:
        _config = MAGNETConfig.from_file(filepath)
    else:
        # Try default locations
        default_paths = [
            "./magnet.json",
            "./config/magnet.json",
            os.path.expanduser("~/.magnet/config.json"),
        ]

        for path in default_paths:
            if Path(path).exists():
                logger.info(f"Loading config from: {path}")
                _config = MAGNETConfig.from_file(path)
                return _config

        # Fall back to environment
        _config = MAGNETConfig.from_env()

    logger.info(f"Configuration loaded: environment={_config.environment}")
    return _config


def get_config() -> MAGNETConfig:
    """Get current configuration, loading if needed."""
    global _config
    if _config is None:
        _config = load_config()
    return _config
