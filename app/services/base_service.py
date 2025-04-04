from abc import ABC, abstractmethod
from typing import Any
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class BaseService(ABC):
    """Base class for all services in the application."""

    def __init__(self):
        """Initialize the base service."""
        self.logger = logger

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the service.

        This method should be implemented by all services to perform any necessary
        setup, such as establishing database connections or loading models.
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources used by the service.

        This method should be implemented by all services to properly clean up
        any resources they use, such as closing database connections or unloading models.
        """
        pass

    def __enter__(self) -> "BaseService":
        """Context manager entry."""
        return self

    async def __aenter__(self) -> "BaseService":
        """Async context manager entry."""
        await self.initialize()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        pass

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.cleanup()
