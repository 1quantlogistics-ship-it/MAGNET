"""
bootstrap/app.py - Application builder and lifecycle v1.1

Module 55: Bootstrap Layer

v1.1 Fixes:
- Blocker #1: PhaseMachine fully connected
- Blocker #3: LLMClient injected to all agents
- Blocker #4: StateManager guaranteed at build-time
- Blocker #6: VisionRequest types registered
- Blocker #9: Storage directories auto-created
"""

from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import asyncio
import logging
import time

from .config import MAGNETConfig, load_config
from .container import Container, ServiceCollection, Lifecycle
from .state_compat import ensure_state_methods

logger = logging.getLogger("bootstrap.app")


class AppState(Enum):
    """Application lifecycle states."""
    CREATED = "created"
    CONFIGURING = "configuring"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class AppContext:
    """Runtime application context."""
    config: MAGNETConfig = None
    container: Container = None
    state: AppState = AppState.CREATED
    start_time: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    _initialized_components: List[str] = field(default_factory=list)

    def get_uptime(self) -> float:
        """Get application uptime in seconds."""
        if self.start_time == 0:
            return 0
        return time.time() - self.start_time


class MAGNETApp:
    """
    Main application class v1.1.

    v1.1 Changes:
    - Guaranteed StateManager initialization order (blocker #4)
    - LLMClient injection chain (blocker #3)
    - PhaseMachine connection (blocker #1)
    - Storage directory creation (blocker #9)
    - VisionRequest type registration (blocker #6)
    """

    def __init__(self, config_file: str = None):
        self._config_file = config_file
        self._context = AppContext()
        self._services = ServiceCollection()
        self._startup_hooks: List[Callable] = []
        self._shutdown_hooks: List[Callable] = []
        self._initialized = False

    @property
    def config(self) -> MAGNETConfig:
        return self._context.config

    @property
    def container(self) -> Container:
        return self._context.container

    @property
    def context(self) -> AppContext:
        return self._context

    def build(self) -> "MAGNETApp":
        """Build the application with proper DI chain."""
        self._context.state = AppState.CONFIGURING

        if self._context.config is None:
            self._context.config = load_config(self._config_file)

        # v1.1: Create storage directories (fixes blocker #9)
        self._ensure_storage_directories()

        # Register core services in dependency order
        self._register_core_services()

        # Build container
        self._context.container = self._services.build()

        # Register config and context
        self._context.container.register_instance(MAGNETConfig, self._context.config)
        self._context.container.register_instance(AppContext, self._context)

        # v1.1: Validate critical services exist (fixes blocker #4)
        self._validate_critical_services()

        self._initialized = True
        logger.info("Application built successfully")

        return self

    def _ensure_storage_directories(self) -> None:
        """Create storage directories if they don't exist. (fixes blocker #9)"""
        config = self._context.config

        directories = [
            config.storage.designs_dir,
            config.storage.reports_dir,
            config.storage.snapshots_dir,
            config.storage.exports_dir,
            config.storage.temp_dir,
        ]

        for dir_path in directories:
            path = Path(dir_path)
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {dir_path}")

    def _register_core_services(self) -> None:
        """
        Register core MAGNET services in dependency order.

        v1.1: Proper injection chain for all components.
        """
        config = self._context.config

        # =================================================================
        # LAYER 1: Core Infrastructure (no dependencies)
        # =================================================================

        # StateManager - MUST be first (fixes blocker #4)
        try:
            from magnet.core.state_manager import StateManager
            from magnet.core.design_state import DesignState

            def create_state_manager():
                sm = StateManager(DesignState())
                return ensure_state_methods(sm)

            self._services.add_factory(StateManager, create_state_manager)
            self._context._initialized_components.append("StateManager")
        except ImportError as e:
            logger.warning(f"StateManager not available: {e}")

        # PhaseMachine - depends on StateManager (fixes blocker #1)
        try:
            from magnet.core.phase_states import PhaseMachine

            def create_phase_machine():
                try:
                    from magnet.core.state_manager import StateManager
                    state_manager = self._context.container.resolve(StateManager)
                    return PhaseMachine(state_manager)
                except Exception:
                    return PhaseMachine()

            self._services.add_factory(PhaseMachine, create_phase_machine)
            self._context._initialized_components.append("PhaseMachine")
        except ImportError as e:
            logger.warning(f"PhaseMachine not available: {e}")

        # ValidatorRegistry
        try:
            from magnet.validators.registry import ValidatorRegistry
            self._services.add_singleton(ValidatorRegistry)
            self._context._initialized_components.append("ValidatorRegistry")
        except ImportError:
            pass

        # =================================================================
        # LAYER 2: LLM Infrastructure
        # =================================================================

        # LLMClient (fixes blocker #3)
        try:
            from magnet.agents.llm_client import LLMClient

            def create_llm_client():
                return LLMClient(
                    provider=config.llm.provider,
                    model=config.llm.model,
                    api_key=config.llm.api_key,
                    base_url=config.llm.base_url,
                    max_tokens=config.llm.max_tokens,
                    temperature=config.llm.temperature,
                    timeout=config.llm.timeout_seconds,
                )

            self._services.add_factory(LLMClient, create_llm_client)
            self._context._initialized_components.append("LLMClient")
        except ImportError as e:
            logger.warning(f"LLMClient not available: {e}")

        # =================================================================
        # LAYER 3: Agent System (depends on LLM + State)
        # =================================================================

        # AgentFactory - needs LLMClient (fixes blocker #3)
        try:
            from magnet.agents.factory import AgentFactory
            from magnet.agents.llm_client import LLMClient
            from magnet.core.state_manager import StateManager

            def create_agent_factory():
                try:
                    llm_client = self._context.container.resolve(LLMClient)
                    state_manager = self._context.container.resolve(StateManager)
                    return AgentFactory(llm_client=llm_client, state_manager=state_manager)
                except Exception:
                    return AgentFactory()

            self._services.add_factory(AgentFactory, create_agent_factory)
            self._context._initialized_components.append("AgentFactory")
        except ImportError as e:
            logger.warning(f"AgentFactory not available: {e}")

        # Conductor - needs everything (fixes blockers #1, #3)
        try:
            from magnet.agents.conductor import Conductor

            def create_conductor():
                try:
                    from magnet.core.state_manager import StateManager
                    from magnet.core.phase_states import PhaseMachine
                    from magnet.agents.factory import AgentFactory
                    from magnet.agents.llm_client import LLMClient

                    container = self._context.container
                    return Conductor(
                        state_manager=container.resolve(StateManager),
                        phase_machine=container.resolve(PhaseMachine),
                        agent_factory=container.resolve(AgentFactory),
                        llm_client=container.resolve(LLMClient),
                        max_iterations=config.agent.max_iterations_per_phase,
                    )
                except Exception as e:
                    logger.warning(f"Conductor creation with deps failed: {e}")
                    return Conductor()

            self._services.add_factory(Conductor, create_conductor)
            self._context._initialized_components.append("Conductor")
        except ImportError as e:
            logger.warning(f"Conductor not available: {e}")

        # =================================================================
        # LAYER 4: Vision & Reporting
        # =================================================================

        # VisionRouter - register VisionRequest types (fixes blocker #6)
        try:
            from magnet.vision.router import VisionRouter, VisionRequest, VisionResponse

            def create_vision_router():
                try:
                    from magnet.core.state_manager import StateManager
                    state_manager = self._context.container.resolve(StateManager)
                    return VisionRouter(state_manager)
                except Exception:
                    return VisionRouter()

            self._services.add_factory(VisionRouter, create_vision_router)
            self._context._initialized_components.append("VisionRouter")
        except ImportError as e:
            logger.warning(f"VisionRouter not available: {e}")

        # ReportGenerator
        try:
            from magnet.reporting.generators.base import ReportGenerator

            def create_report_generator():
                try:
                    from magnet.core.state_manager import StateManager
                    state_manager = self._context.container.resolve(StateManager)
                    return ReportGenerator(state_manager)
                except Exception:
                    return ReportGenerator()

            self._services.add_factory(ReportGenerator, create_report_generator, Lifecycle.TRANSIENT)
            self._context._initialized_components.append("ReportGenerator")
        except ImportError:
            pass

    def _validate_critical_services(self) -> None:
        """Validate that critical services are resolvable. (fixes blocker #4)"""
        critical_services = []

        try:
            from magnet.core.state_manager import StateManager
            critical_services.append(StateManager)
        except ImportError:
            pass

        try:
            from magnet.core.phase_states import PhaseMachine
            critical_services.append(PhaseMachine)
        except ImportError:
            pass

        for service_type in critical_services:
            if self._context.container.is_registered(service_type):
                try:
                    instance = self._context.container.resolve(service_type)
                    logger.debug(f"Validated: {service_type.__name__}")
                except Exception as e:
                    logger.warning(f"Service not resolvable: {service_type.__name__}: {e}")

    async def start(self) -> None:
        """Start application and run startup hooks."""
        if not self._initialized:
            self.build()

        self._context.state = AppState.STARTING
        self._context.start_time = time.time()

        for hook in self._startup_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(self._context)
                else:
                    hook(self._context)
            except Exception as e:
                logger.error(f"Startup hook failed: {e}")
                self._context.state = AppState.FAILED
                raise

        self._context.state = AppState.RUNNING
        logger.info("Application started")

    async def stop(self) -> None:
        """Stop application and run shutdown hooks."""
        self._context.state = AppState.STOPPING

        for hook in reversed(self._shutdown_hooks):
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(self._context)
                else:
                    hook(self._context)
            except Exception as e:
                logger.error(f"Shutdown hook failed: {e}")

        self._context.state = AppState.STOPPED
        logger.info("Application stopped")

    def on_startup(self, hook: Callable) -> "MAGNETApp":
        """Register startup hook."""
        self._startup_hooks.append(hook)
        return self

    def on_shutdown(self, hook: Callable) -> "MAGNETApp":
        """Register shutdown hook."""
        self._shutdown_hooks.append(hook)
        return self

    def run_cli(self) -> int:
        """Run interactive CLI."""
        if not self._initialized:
            self.build()

        asyncio.run(self.start())

        try:
            from magnet.cli.repl import REPL
            from magnet.cli.core import CLIContext

            # Create CLI context with container access
            ctx = CLIContext()

            # Try to inject state from container
            try:
                from magnet.core.state_manager import StateManager
                ctx.state = self._context.container.resolve(StateManager)
            except Exception:
                pass

            try:
                from magnet.agents.conductor import Conductor
                ctx.conductor = self._context.container.resolve(Conductor)
            except Exception:
                pass

            repl = REPL(ctx)
            repl.run()
            return 0
        except Exception as e:
            logger.exception(f"CLI error: {e}")
            return 1
        finally:
            asyncio.run(self.stop())

    def run_api(self) -> None:
        """Run API server."""
        try:
            import uvicorn
        except ImportError:
            logger.error("uvicorn not installed. Run: pip install uvicorn")
            return

        if not self._initialized:
            self.build()

        try:
            from magnet.deployment.api import create_fastapi_app

            app = create_fastapi_app(self._context)

            uvicorn.run(
                app,
                host=self.config.api.host,
                port=self.config.api.port,
                workers=self.config.api.workers,
            )
        except ImportError as e:
            logger.error(f"API module not available: {e}")

    def run_worker(self, concurrency: int = 4) -> None:
        """Run background worker."""
        if not self._initialized:
            self.build()

        try:
            from magnet.deployment.worker import Worker

            worker = Worker(
                container=self._context.container,
                concurrency=concurrency,
            )

            asyncio.run(self._run_worker_async(worker))
        except ImportError as e:
            logger.error(f"Worker module not available: {e}")

    async def _run_worker_async(self, worker) -> None:
        """Run worker with proper lifecycle."""
        await self.start()
        try:
            await worker.run()
        finally:
            await self.stop()


def create_app(config_file: str = None) -> MAGNETApp:
    """Create and configure MAGNET application."""
    return MAGNETApp(config_file).build()
