from typing import Dict, Any, Optional
from datetime import datetime
from app.services.base_service import BaseService
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class MonitoringService(BaseService):
    """Service for monitoring and tracking system interactions."""

    def __init__(self):
        """Initialize the monitoring service."""
        super().__init__()
        self.interactions = []
        self.errors = []

    async def initialize(self) -> None:
        """Initialize the monitoring service."""
        try:
            self.logger.info("Monitoring service initialized")
        except Exception as e:
            self.logger.error(f"Error initializing monitoring service: {str(e)}")
            raise

    async def cleanup(self) -> None:
        """Clean up monitoring service resources."""
        try:
            self.interactions.clear()
            self.errors.clear()
            self.logger.info("Monitoring service cleaned up")
        except Exception as e:
            self.logger.error(f"Error cleaning up monitoring service: {str(e)}")
            raise

    async def log_interaction(
        self,
        query: str,
        response: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an interaction with the system.

        Args:
            query: The user's query
            response: The system's response
            source: The source of the interaction (e.g., 'chat', 'api')
            metadata: Additional metadata about the interaction
        """
        try:
            interaction = {
                "timestamp": datetime.utcnow().isoformat(),
                "query": query,
                "response": response,
                "source": source,
                "metadata": metadata or {},
            }
            self.interactions.append(interaction)
            self.logger.info(f"Logged interaction from {source}")
        except Exception as e:
            self.logger.error(f"Error logging interaction: {str(e)}")
            raise

    async def log_error(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an error that occurred in the system.

        Args:
            error: The exception that occurred
            context: Additional context about the error
        """
        try:
            error_log = {
                "timestamp": datetime.utcnow().isoformat(),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context or {},
            }
            self.errors.append(error_log)
            self.logger.error(f"Logged error: {str(error)}")
        except Exception as e:
            self.logger.error(f"Error logging error: {str(e)}")
            raise

    def get_interactions(self) -> list:
        """Get all logged interactions.

        Returns:
            list: List of interaction logs
        """
        return self.interactions

    def get_errors(self) -> list:
        """Get all logged errors.

        Returns:
            list: List of error logs
        """
        return self.errors
