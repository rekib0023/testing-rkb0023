from typing import Dict, Any
from datetime import datetime
from app.core.base_service import BaseService
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class MonitoringService(BaseService):
    def __init__(self):
        super().__init__()
        self.metrics: Dict[str, Any] = {
            "requests": 0,
            "errors": 0,
            "response_times": [],
            "last_error": None,
            "start_time": datetime.now(),
        }

    async def initialize(self) -> None:
        """Initialize monitoring service"""
        logger.info("Initializing monitoring service")

    async def cleanup(self) -> None:
        """Clean up monitoring resources"""
        logger.info("Cleaning up monitoring service")

    def track_request(self, endpoint: str, duration: float) -> None:
        """Track API request metrics"""
        self.metrics["requests"] += 1
        self.metrics["response_times"].append(duration)
        logger.info(f"Request to {endpoint} completed in {duration:.2f}s")

    def track_error(self, error: Exception) -> None:
        """Track error metrics"""
        self.metrics["errors"] += 1
        self.metrics["last_error"] = {
            "message": str(error),
            "timestamp": datetime.now().isoformat(),
        }
        logger.error(f"Error occurred: {str(error)}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        avg_response_time = (
            sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
            if self.metrics["response_times"]
            else 0
        )

        return {
            "total_requests": self.metrics["requests"],
            "total_errors": self.metrics["errors"],
            "average_response_time": avg_response_time,
            "uptime": (datetime.now() - self.metrics["start_time"]).total_seconds(),
            "last_error": self.metrics["last_error"],
        }
