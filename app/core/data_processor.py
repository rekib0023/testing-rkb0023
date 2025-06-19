from pathlib import Path
from typing import Any, Dict, List

from app.config.config import settings
from app.core.base_service import BaseService


class DataProcessor(BaseService):
    def __init__(self):
        super().__init__()
        self.raw_dir = Path(settings.RAW_DATA_DIR)
        self.processed_dir = Path(settings.PROCESSED_DATA_DIR)

    async def initialize(self) -> None:
        """Create necessary directories if they don't exist"""
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    async def cleanup(self) -> None:
        """Clean up temporary files if any"""
        pass

    def get_raw_files(self) -> List[Path]:
        """Get all files from the raw directory"""
        return list(self.raw_dir.glob("*"))

    def get_processed_files(self) -> List[Path]:
        """Get all files from the processed directory"""
        return list(self.processed_dir.glob("*"))

    def save_processed_file(
        self, content: str, filename: str, metadata: Dict[str, Any]
    ) -> Path:
        """Save processed content to the processed directory"""
        file_path = self.processed_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path
