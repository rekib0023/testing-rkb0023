from abc import ABC, abstractmethod

from app.config.config import settings


class BaseService(ABC):
    def __init__(self):
        self.settings = settings

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the service with necessary resources"""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources when service is no longer needed"""
        pass
