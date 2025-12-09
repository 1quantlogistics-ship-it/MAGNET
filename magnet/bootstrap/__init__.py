"""
bootstrap/ - Bootstrap Layer (Module 55)

Provides application initialization, configuration, and dependency injection.

v1.1 Changes:
- State compatibility layer (fixes blocker #2)
- Proper DI registration order (fixes blockers #1, #3, #4)
- Storage directory creation (fixes blocker #9)
- VisionRequest type registration (fixes blocker #6)
"""

from .config import (
    MAGNETConfig,
    LLMConfig,
    APIConfig,
    StorageConfig,
    AgentConfig,
    LoggingConfig,
    load_config,
    get_config,
)

from .state_compat import (
    ensure_state_methods,
    StateManagerProxy,
    create_compatible_state_manager,
)

from .container import (
    Lifecycle,
    ServiceDescriptor,
    ServiceCollection,
    Container,
)

from .app import (
    AppState,
    AppContext,
    MAGNETApp,
    create_app,
)

from .entrypoints import (
    cli_main,
    api_main,
    run_worker,
    setup_logging,
)


__all__ = [
    # Config
    "MAGNETConfig",
    "LLMConfig",
    "APIConfig",
    "StorageConfig",
    "AgentConfig",
    "LoggingConfig",
    "load_config",
    "get_config",
    # State Compat
    "ensure_state_methods",
    "StateManagerProxy",
    "create_compatible_state_manager",
    # Container
    "Lifecycle",
    "ServiceDescriptor",
    "ServiceCollection",
    "Container",
    # App
    "AppState",
    "AppContext",
    "MAGNETApp",
    "create_app",
    # Entry Points
    "cli_main",
    "api_main",
    "run_worker",
    "setup_logging",
]
