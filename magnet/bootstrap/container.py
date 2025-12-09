"""
bootstrap/container.py - Dependency injection container v1.1

Module 55: Bootstrap Layer

Provides dependency injection with lifecycle management and cycle detection.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union
from enum import Enum
import logging
import threading

logger = logging.getLogger("bootstrap.container")

T = TypeVar('T')


class Lifecycle(Enum):
    """Service lifecycle modes."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


@dataclass
class ServiceDescriptor:
    """Describes a registered service."""

    service_type: Type
    implementation: Optional[Type] = None
    factory: Optional[Callable] = None
    instance: Any = None
    lifecycle: Lifecycle = Lifecycle.SINGLETON
    dependencies: List[Type] = field(default_factory=list)


class CircularDependencyError(Exception):
    """Raised when a circular dependency is detected."""
    pass


class ServiceNotFoundError(Exception):
    """Raised when a service is not registered."""
    pass


class Container:
    """
    Dependency injection container with lifecycle management.

    Features:
    - Singleton, transient, and scoped lifecycles
    - Circular dependency detection
    - Factory function support
    - Instance registration
    """

    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._resolving: Set[Type] = set()
        self._lock = threading.RLock()
        self._scopes: Dict[str, Dict[Type, Any]] = {}

    def register(
        self,
        service_type: Type[T],
        implementation: Type[T] = None,
        lifecycle: Lifecycle = Lifecycle.SINGLETON,
    ) -> "Container":
        """
        Register a service type with implementation.

        Args:
            service_type: The service interface/type
            implementation: The implementation class
            lifecycle: Service lifecycle

        Returns:
            Self for chaining
        """
        with self._lock:
            self._services[service_type] = ServiceDescriptor(
                service_type=service_type,
                implementation=implementation or service_type,
                lifecycle=lifecycle,
            )
        return self

    def register_factory(
        self,
        service_type: Type[T],
        factory: Callable[..., T],
        lifecycle: Lifecycle = Lifecycle.SINGLETON,
    ) -> "Container":
        """
        Register a service with a factory function.

        Args:
            service_type: The service type
            factory: Factory function to create instance
            lifecycle: Service lifecycle

        Returns:
            Self for chaining
        """
        with self._lock:
            self._services[service_type] = ServiceDescriptor(
                service_type=service_type,
                factory=factory,
                lifecycle=lifecycle,
            )
        return self

    def register_instance(
        self,
        service_type: Type[T],
        instance: T,
    ) -> "Container":
        """
        Register an existing instance as singleton.

        Args:
            service_type: The service type
            instance: The instance to register

        Returns:
            Self for chaining
        """
        with self._lock:
            self._services[service_type] = ServiceDescriptor(
                service_type=service_type,
                instance=instance,
                lifecycle=Lifecycle.SINGLETON,
            )
        return self

    def resolve(self, service_type: Type[T], scope_id: str = None) -> T:
        """
        Resolve a service instance.

        Args:
            service_type: The service type to resolve
            scope_id: Optional scope for scoped services

        Returns:
            Service instance

        Raises:
            ServiceNotFoundError: If service not registered
            CircularDependencyError: If circular dependency detected
        """
        with self._lock:
            if service_type not in self._services:
                raise ServiceNotFoundError(f"Service not registered: {service_type.__name__}")

            descriptor = self._services[service_type]

            # Check for circular dependency
            if service_type in self._resolving:
                chain = " -> ".join(t.__name__ for t in self._resolving)
                raise CircularDependencyError(
                    f"Circular dependency detected: {chain} -> {service_type.__name__}"
                )

            # Return cached singleton
            if descriptor.lifecycle == Lifecycle.SINGLETON and descriptor.instance is not None:
                return descriptor.instance

            # Return cached scoped instance
            if descriptor.lifecycle == Lifecycle.SCOPED and scope_id:
                if scope_id in self._scopes and service_type in self._scopes[scope_id]:
                    return self._scopes[scope_id][service_type]

            # Mark as resolving for cycle detection
            self._resolving.add(service_type)

            try:
                instance = self._create_instance(descriptor)

                # Cache based on lifecycle
                if descriptor.lifecycle == Lifecycle.SINGLETON:
                    descriptor.instance = instance
                elif descriptor.lifecycle == Lifecycle.SCOPED and scope_id:
                    if scope_id not in self._scopes:
                        self._scopes[scope_id] = {}
                    self._scopes[scope_id][service_type] = instance

                return instance
            finally:
                self._resolving.discard(service_type)

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create a service instance."""
        # Use existing instance
        if descriptor.instance is not None:
            return descriptor.instance

        # Use factory
        if descriptor.factory is not None:
            try:
                return descriptor.factory()
            except TypeError:
                # Factory might need dependencies
                return self._call_with_dependencies(descriptor.factory)

        # Create from implementation class
        if descriptor.implementation is not None:
            return self._call_with_dependencies(descriptor.implementation)

        raise ServiceNotFoundError(
            f"No implementation or factory for {descriptor.service_type.__name__}"
        )

    def _call_with_dependencies(self, callable_obj: Callable) -> Any:
        """Call a constructor/factory with resolved dependencies."""
        import inspect

        sig = inspect.signature(callable_obj)
        kwargs = {}

        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            if param.annotation != inspect.Parameter.empty:
                param_type = param.annotation

                # Check if it's a registered service
                if param_type in self._services:
                    kwargs[param_name] = self.resolve(param_type)
                elif param.default != inspect.Parameter.empty:
                    kwargs[param_name] = param.default
            elif param.default != inspect.Parameter.empty:
                kwargs[param_name] = param.default

        return callable_obj(**kwargs)

    def is_registered(self, service_type: Type) -> bool:
        """Check if a service type is registered."""
        return service_type in self._services

    def get_all_registered(self) -> List[Type]:
        """Get all registered service types."""
        return list(self._services.keys())

    def create_scope(self, scope_id: str) -> "ScopedContainer":
        """Create a scoped container."""
        return ScopedContainer(self, scope_id)

    def dispose_scope(self, scope_id: str) -> None:
        """Dispose a scope and its instances."""
        with self._lock:
            if scope_id in self._scopes:
                del self._scopes[scope_id]

    def clear(self) -> None:
        """Clear all registrations."""
        with self._lock:
            self._services.clear()
            self._scopes.clear()
            self._resolving.clear()


class ScopedContainer:
    """Scoped container for request-scoped dependencies."""

    def __init__(self, parent: Container, scope_id: str):
        self._parent = parent
        self._scope_id = scope_id

    def resolve(self, service_type: Type[T]) -> T:
        """Resolve within scope."""
        return self._parent.resolve(service_type, self._scope_id)

    def dispose(self) -> None:
        """Dispose this scope."""
        self._parent.dispose_scope(self._scope_id)

    def __enter__(self) -> "ScopedContainer":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.dispose()


class ServiceCollection:
    """
    Builder for configuring services before building container.

    Provides a fluent API for service registration.
    """

    def __init__(self):
        self._registrations: List[ServiceDescriptor] = []

    def add_singleton(
        self,
        service_type: Type[T],
        implementation: Type[T] = None,
    ) -> "ServiceCollection":
        """Add a singleton service."""
        self._registrations.append(ServiceDescriptor(
            service_type=service_type,
            implementation=implementation or service_type,
            lifecycle=Lifecycle.SINGLETON,
        ))
        return self

    def add_transient(
        self,
        service_type: Type[T],
        implementation: Type[T] = None,
    ) -> "ServiceCollection":
        """Add a transient service."""
        self._registrations.append(ServiceDescriptor(
            service_type=service_type,
            implementation=implementation or service_type,
            lifecycle=Lifecycle.TRANSIENT,
        ))
        return self

    def add_scoped(
        self,
        service_type: Type[T],
        implementation: Type[T] = None,
    ) -> "ServiceCollection":
        """Add a scoped service."""
        self._registrations.append(ServiceDescriptor(
            service_type=service_type,
            implementation=implementation or service_type,
            lifecycle=Lifecycle.SCOPED,
        ))
        return self

    def add_factory(
        self,
        service_type: Type[T],
        factory: Callable[..., T],
        lifecycle: Lifecycle = Lifecycle.SINGLETON,
    ) -> "ServiceCollection":
        """Add a service with factory."""
        self._registrations.append(ServiceDescriptor(
            service_type=service_type,
            factory=factory,
            lifecycle=lifecycle,
        ))
        return self

    def add_instance(
        self,
        service_type: Type[T],
        instance: T,
    ) -> "ServiceCollection":
        """Add an existing instance."""
        self._registrations.append(ServiceDescriptor(
            service_type=service_type,
            instance=instance,
            lifecycle=Lifecycle.SINGLETON,
        ))
        return self

    def build(self) -> Container:
        """Build the container from registrations."""
        container = Container()

        for descriptor in self._registrations:
            if descriptor.instance is not None:
                container.register_instance(descriptor.service_type, descriptor.instance)
            elif descriptor.factory is not None:
                container.register_factory(
                    descriptor.service_type,
                    descriptor.factory,
                    descriptor.lifecycle,
                )
            else:
                container.register(
                    descriptor.service_type,
                    descriptor.implementation,
                    descriptor.lifecycle,
                )

        return container
