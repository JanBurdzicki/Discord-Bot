"""
Service container for dependency injection.
Provides simple dependency injection without over-engineering.
"""

from typing import Type, TypeVar, Dict, Any, Callable, Optional, Union
import inspect

T = TypeVar('T')

class ServiceContainer:
    """
    Simple dependency injection container that supports:
    - Singleton registration
    - Factory registration
    - Auto-wiring of dependencies
    - Lazy initialization
    """

    def __init__(self):
        self._services: Dict[Union[Type, str], Any] = {}
        self._factories: Dict[Union[Type, str], Callable] = {}
        self._singletons: Dict[Union[Type, str], Any] = {}
        self._initializing: set = set()  # Prevent circular dependencies

    def register_singleton(self, interface: Union[Type[T], str], instance: T) -> None:
        """Register a singleton instance"""
        self._singletons[interface] = instance

    def register_factory(self, interface: Union[Type[T], str], factory: Callable[[], T]) -> None:
        """Register a factory function"""
        self._factories[interface] = factory

    def register_type(self, interface: Union[Type[T], str], implementation: Type[T]) -> None:
        """Register a type to be auto-instantiated"""
        self._services[interface] = implementation

    def get(self, interface: Union[Type[T], str]) -> T:
        """Get an instance of the requested type or by string name"""
        # Check if it's a singleton
        if interface in self._singletons:
            return self._singletons[interface]

        # Check if it's a factory
        if interface in self._factories:
            instance = self._factories[interface]()
            # Cache factory results as singletons
            self._singletons[interface] = instance
            return instance

        # Check if it's a registered type
        if interface in self._services:
            return self._create_instance(self._services[interface])

        # Try to create the type directly (if it's a type, not a string)
        if not isinstance(interface, str):
            try:
                return self._create_instance(interface)
            except Exception as e:
                interface_name = getattr(interface, '__name__', str(interface))
                raise ServiceNotFoundError(f"Cannot resolve service {interface_name}: {str(e)}")

        # If we get here, the service was not found
        interface_name = getattr(interface, '__name__', str(interface))
        raise ServiceNotFoundError(f"Service '{interface_name}' not found")

    def _create_instance(self, cls: Type[T]) -> T:
        """Create an instance with dependency injection"""
        if cls in self._initializing:
            raise CircularDependencyError(f"Circular dependency detected for {cls.__name__}")

        self._initializing.add(cls)

        try:
            # Get constructor signature
            signature = inspect.signature(cls.__init__)
            args = {}

            for param_name, param in signature.parameters.items():
                if param_name == 'self':
                    continue

                # Skip parameters with default values
                if param.default is not inspect.Parameter.empty:
                    continue

                # Get the parameter type
                param_type = param.annotation
                if param_type is inspect.Parameter.empty:
                    continue

                # Resolve the dependency
                args[param_name] = self.get(param_type)

            # Create the instance
            instance = cls(**args)

            # Cache as singleton
            self._singletons[cls] = instance

            return instance

        finally:
            self._initializing.remove(cls)

    def has(self, interface: Union[Type[T], str]) -> bool:
        """Check if a service is registered"""
        return (interface in self._singletons or
                interface in self._factories or
                interface in self._services)

    def clear(self) -> None:
        """Clear all registered services"""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
        self._initializing.clear()

class ServiceNotFoundError(Exception):
    """Raised when a requested service cannot be found or created"""
    pass

class CircularDependencyError(Exception):
    """Raised when a circular dependency is detected"""
    pass

# Decorator for easy service registration
def service(interface: Type[T] = None):
    """
    Decorator to mark a class as a service.
    Usage:
        @service(ISomeInterface)
        class SomeService:
            pass
    """
    def decorator(cls):
        cls._service_interface = interface or cls
        return cls
    return decorator

# Global service container instance
container = ServiceContainer()