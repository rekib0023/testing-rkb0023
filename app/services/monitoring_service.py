import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.config.config import settings
from app.core.logging_config import (  # We'll assume a helper for setup
    get_logger,
    setup_file_logger,
)
from app.services.base_service import BaseService

# Get the main application logger
logger = get_logger(__name__)


# ## --- IMPROVEMENT ---: Use Pydantic models for structured, validated logs.
class InteractionLog(BaseModel):
    """Data model for a system interaction log."""

    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    query: str
    response: str
    source: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ErrorLog(BaseModel):
    """Data model for an error log."""

    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    error_type: str
    error_message: str
    context: Dict[str, Any] = Field(default_factory=dict)


class MonitoringService(BaseService):
    """
    Service for persistent, structured monitoring of system interactions and errors.
    """

    def __init__(self):
        """Initialize the monitoring service."""
        super().__init__()
        self.logger = logger
        # ## --- IMPROVEMENT ---: Dedicated loggers for structured, file-based logging.
        self.interaction_logger = None
        self.error_logger = None

    async def initialize(self) -> None:
        """Initialize the monitoring service and set up file loggers."""
        try:
            # Assumes a helper function `setup_file_logger` exists to configure logging.
            # This would set up a logger that writes to the specified file.
            self.interaction_logger = setup_file_logger(
                "interactions", settings.INTERACTIONS_LOG_PATH
            )
            self.error_logger = setup_file_logger("errors", settings.ERRORS_LOG_PATH)
            self.logger.info(
                f"Monitoring service initialized. Logging interactions to '{settings.INTERACTIONS_LOG_PATH}' and errors to '{settings.ERRORS_LOG_PATH}'."
            )
        except Exception as e:
            self.logger.error(
                f"Error initializing monitoring service: {e}", exc_info=True
            )
            raise

    async def cleanup(self) -> None:
        """Clean up monitoring service resources by shutting down log handlers."""
        self.logger.info("Cleaning up monitoring service.")
        # The logging configuration should handle the shutdown of handlers gracefully.
        # No explicit clear() is needed as data is in files.

    # ## --- IMPROVEMENT ---: Methods are now synchronous as logging is non-blocking.
    def log_interaction(
        self,
        query: str,
        response: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an interaction with the system to a persistent file.

        Args:
            query: The user's query.
            response: The system's response.
            source: The source of the interaction (e.g., 'chat', 'api').
            metadata: Additional metadata about the interaction.
        """
        try:
            if not self.interaction_logger:
                self.logger.warning("Interaction logger not initialized. Skipping log.")
                return

            log_entry = InteractionLog(
                query=query, response=response, source=source, metadata=metadata or {}
            )
            # Log the JSON representation of the Pydantic model.
            self.interaction_logger.info(log_entry.model_dump_json())
        except Exception as e:
            self.logger.error(f"Error logging interaction: {e}", exc_info=True)

    def log_error(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an error that occurred in the system to a persistent file.

        Args:
            error: The exception that occurred.
            context: Additional context about the error.
        """
        try:
            if not self.error_logger:
                self.logger.warning("Error logger not initialized. Skipping log.")
                return

            log_entry = ErrorLog(
                error_type=type(error).__name__,
                error_message=str(error),
                context=context or {},
            )
            self.error_logger.error(log_entry.model_dump_json())
        except Exception as e:
            self.logger.error(f"Failed to log an error: {e}", exc_info=True)

    # ## --- IMPROVEMENT ---: Methods to retrieve data now read from the persistent logs.
    def _read_logs(self, file_path: str) -> List[Dict[str, Any]]:
        """Helper function to read a .jsonl log file."""
        records = []
        try:
            with open(file_path, "r") as f:
                for line in f:
                    records.append(json.loads(line))
        except FileNotFoundError:
            self.logger.warning(f"Log file not found: {file_path}")
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding JSON from {file_path}: {e}")
        return records

    def get_interactions(self) -> List[Dict[str, Any]]:
        """Get all logged interactions from the log file."""
        return self._read_logs(settings.INTERACTIONS_LOG_PATH)

    def get_errors(self) -> List[Dict[str, Any]]:
        """Get all logged errors from the log file."""
        return self._read_logs(settings.ERRORS_LOG_PATH)

    def get_basic_stats(self) -> Dict[str, int]:
        """Provides a basic count of total interactions and errors."""
        return {
            "total_interactions": len(self.get_interactions()),
            "total_errors": len(self.get_errors()),
        }
