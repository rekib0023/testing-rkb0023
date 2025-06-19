import asyncio

import chromadb
from chromadb.config import Settings

from app.config.config import settings
from app.core.logging_config import get_logger
from app.utils.legal_tools import LegalUpdatesTool

logger = get_logger(__name__)


class LegalUpdatesIngester:
    def __init__(self):
        self.legal_tool = LegalUpdatesTool()
        self.chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_DB_PATH, settings=Settings(allow_reset=True)
        )
        self.legal_collection = self.chroma_client.get_or_create_collection(
            name="legal_updates", metadata={"hnsw:space": "cosine"}
        )

    async def ingest_updates(self) -> None:
        """Ingest legal updates from various sources."""
        try:
            logger.info("Starting legal updates ingestion")

            # Get updates from various sources
            updates = []

            # Get recent bills
            bills = self.legal_tool._get_recent_bills()
            updates.extend(bills)

            # Get constitution amendments
            amendments = self.legal_tool._get_constitution_amendments()
            updates.extend(amendments)

            # Get government gazette notifications
            # notifications = self.legal_tool._get_gazette_notifications()
            # updates.extend(notifications)

            if updates:
                # Create embeddings
                self.legal_tool.create_embeddings(updates)

                # Store in ChromaDB
                self.legal_collection.add(
                    documents=[str(update) for update in updates],
                    metadatas=updates,
                    ids=[f"update_{i}" for i in range(len(updates))],
                )

                logger.info(f"Successfully ingested {len(updates)} legal updates")
            else:
                logger.warning("No legal updates found to ingest")

        except Exception as e:
            logger.error(f"Error ingesting legal updates: {str(e)}")
            raise


async def main():
    """Main function to run the ingestion process."""
    ingester = LegalUpdatesIngester()
    await ingester.ingest_updates()


if __name__ == "__main__":
    asyncio.run(main())
