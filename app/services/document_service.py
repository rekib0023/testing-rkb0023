import asyncio
import time
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

# ## --- IMPROVEMENT ---: Using a more sophisticated text splitter from LangChain.
# You will need to add `langchain` to your project's dependencies.
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.config.config import settings
from app.core.base_service import BaseService
from app.core.data_processor import DataProcessor
from app.core.logging_config import get_logger
from app.core.monitoring import MonitoringService

# ## --- IMPROVEMENT ---: Module-level logger for consistency.
logger = get_logger(__name__)


class DocumentService(BaseService):
    """
    Service for ingesting and searching documents using a vector database.
    """

    def __init__(self):
        super().__init__()
        self.client: Optional[chromadb.Client] = None
        self.collection: Optional[chromadb.Collection] = None
        self.data_processor = DataProcessor()
        self.monitoring = MonitoringService()
        self.logger = (
            logger  # ## --- IMPROVEMENT ---: Instance logger for consistent access.
        )

        # ## --- IMPROVEMENT ---: Use a more robust text splitter.
        # Parameters are now driven by the central configuration.
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
        )

    async def initialize(self) -> None:
        """Initialize ChromaDB client and collection."""
        self.logger.info("Initializing DocumentService")
        try:
            await self.data_processor.initialize()
            await self.monitoring.initialize()

            # ## --- IMPROVEMENT ---: Dangerous settings like `allow_reset` are now configurable.
            client_settings = Settings(
                allow_reset=settings.CHROMA_ALLOW_RESET,
                # Add other ChromaDB settings from your config as needed
            )
            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_DB_PATH, settings=client_settings
            )
            self.collection = self.client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},  # Cosine is good for text
            )
            self.logger.info(
                f"ChromaDB client initialized. Collection '{settings.CHROMA_COLLECTION_NAME}' loaded."
            )
        except Exception as e:
            self.logger.error(f"Error initializing ChromaDB: {e}", exc_info=True)
            raise

    async def cleanup(self) -> None:
        """Clean up resources."""
        self.logger.info("Cleaning up DocumentService")
        await self.data_processor.cleanup()
        await self.monitoring.cleanup()

    async def ingest_document(self, content: str, metadata: Dict[str, Any]) -> str:
        """Process and ingest a document into the vector database."""
        start_time = time.time()
        source_name = metadata.get(
            "source", "Unknown_Source"
        )  # Use source for filename
        try:
            self.logger.info(f"Starting document ingestion: {source_name}")
            if not self.collection:
                raise Exception("Collection is not initialized.")

            # Process the document with DataProcessor (e.g., for archival or cleaning)
            # The current implementation just saves it, which might be for backup.
            processed_path = self.data_processor.save_processed_file(
                content, source_name, metadata
            )
            self.logger.debug(f"Document processed and saved to: {processed_path}")

            # Create document chunks using the improved text splitter
            chunks = self.text_splitter.split_text(content)
            self.logger.debug(
                f"Created {len(chunks)} chunks from document '{source_name}'"
            )

            # Prepare data for ChromaDB with richer metadata
            ids = [f"{source_name}_{i}" for i in range(len(chunks))]
            metadatas = [
                {**metadata, "chunk_index": i, "chunk_total": len(chunks)}
                for i in range(len(chunks))
            ]

            # ## --- CRITICAL FIX ---: Run blocking I/O in a separate thread
            await asyncio.to_thread(
                self.collection.add, documents=chunks, metadatas=metadatas, ids=ids
            )

            duration = time.time() - start_time
            await self.monitoring.track_request("ingest_document", duration)
            self.logger.info(
                f"Document '{source_name}' ingested successfully in {duration:.2f}s"
            )

            return f"Document '{source_name}' processed and ingested successfully with {len(chunks)} chunks."
        except Exception as e:
            await self.monitoring.track_error(e)
            self.logger.error(
                f"Error ingesting document {source_name}: {e}", exc_info=True
            )
            raise

    async def search_documents(
        self, query: str, k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search for relevant documents in the collection."""
        start_time = time.time()
        # ## --- IMPROVEMENT ---: Use configured default for 'k' if not provided.
        num_results = k if k is not None else settings.SEARCH_RESULTS_K

        try:
            self.logger.debug(
                f"Searching documents for query: '{query[:50]}...' with k={num_results}"
            )
            if not self.collection:
                raise Exception("Collection is not initialized.")

            # ## --- CRITICAL FIX ---: Run blocking I/O in a separate thread
            results = await asyncio.to_thread(
                self.collection.query, query_texts=[query], n_results=num_results
            )

            duration = time.time() - start_time
            await self.monitoring.track_request("search_documents", duration)

            # Safely access results
            if not results or not results.get("documents"):
                self.logger.info("Search returned no results.")
                return []

            found_docs = results["documents"][0]
            self.logger.info(
                f"Search completed in {duration:.2f}s, found {len(found_docs)} results"
            )

            # Combine results into a list of dictionaries
            return [
                {"content": doc, "metadata": meta, "distance": dist}
                for doc, meta, dist in zip(
                    found_docs,
                    results["metadatas"][0],
                    results["distances"][0],
                )
            ]
        except Exception as e:
            await self.monitoring.track_error(e)
            self.logger.error(f"Error searching documents: {e}", exc_info=True)
            raise

    async def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific document chunk by its ID."""
        try:
            if not self.collection:
                raise Exception("Collection is not initialized.")

            result = await asyncio.to_thread(
                self.collection.get, ids=[doc_id], include=["metadatas", "documents"]
            )

            if not result or not result.get("documents"):
                self.logger.warning(f"Document with ID '{doc_id}' not found.")
                return None  # ## --- IMPROVEMENT ---: Return None instead of raising Exception for not found.

            return {
                "id": result["ids"][0],
                "content": result["documents"][0],
                "metadata": result["metadatas"][0],
            }
        except Exception as e:
            self.logger.error(
                f"Error retrieving document '{doc_id}': {e}", exc_info=True
            )
            raise

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        try:
            if not self.collection:
                raise Exception("Collection is not initialized.")

            # ## --- CRITICAL FIX ---: Correctly getting collection stats.
            total_chunks = await asyncio.to_thread(self.collection.count)

            # To get unique documents, we fetch all metadata and count unique sources.
            # This can be slow for very large collections.
            all_metadatas = await asyncio.to_thread(
                self.collection.get, include=["metadatas"]
            )
            unique_sources = set(
                meta["source"]
                for meta in all_metadatas["metadatas"]
                if "source" in meta
            )

            return {
                "total_chunks": total_chunks,
                "total_unique_documents": len(unique_sources),
            }
        except Exception as e:
            self.logger.error(f"Error getting collection stats: {e}", exc_info=True)
            raise
