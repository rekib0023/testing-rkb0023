from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings
from app.core.base_service import BaseService
from app.core.data_processor import DataProcessor
from app.core.monitoring import MonitoringService
from app.core.logging_config import get_logger
from app.config.config import settings
from app.models.document import Document
import json
import time

logger = get_logger(__name__)


class DocumentService(BaseService):
    def __init__(self):
        super().__init__()
        self.client = None
        self.collection = None
        self.data_processor = DataProcessor()
        self.monitoring = MonitoringService()

    async def initialize(self) -> None:
        """Initialize ChromaDB client and collection"""
        logger.info("Initializing DocumentService")
        await self.data_processor.initialize()
        await self.monitoring.initialize()

        try:
            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_DB_PATH, settings=Settings(allow_reset=True)
            )

            self.collection = self.client.get_or_create_collection(
                name="legal_documents", metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {str(e)}")
            raise

    async def cleanup(self) -> None:
        """Clean up resources"""
        logger.info("Cleaning up DocumentService")
        await self.data_processor.cleanup()
        await self.monitoring.cleanup()

    async def ingest_document(self, content: str, metadata: Dict[str, Any]) -> str:
        """Process and ingest a document into the vector database"""
        start_time = time.time()
        try:
            logger.info(
                f"Starting document ingestion: {metadata.get('title', 'Unknown')}"
            )

            # Process the document
            filename = f"{metadata.get('title', 'document')}.json"
            processed_path = self.data_processor.save_processed_file(
                content, filename, metadata
            )
            logger.debug(f"Document processed and saved to: {processed_path}")

            # Create document chunks
            chunks = self._create_chunks(content)
            logger.debug(f"Created {len(chunks)} chunks from document")

            # Prepare data for ChromaDB
            ids = [f"{filename}_{i}" for i in range(len(chunks))]
            documents = chunks
            metadatas = [{"source": filename, **metadata} for _ in chunks]

            # Add to ChromaDB
            self.collection.add(documents=documents, metadatas=metadatas, ids=ids)

            duration = time.time() - start_time
            self.monitoring.track_request("ingest_document", duration)
            logger.info(f"Document {filename} ingested successfully in {duration:.2f}s")

            return f"Document {filename} processed and ingested successfully"
        except Exception as e:
            self.monitoring.track_error(e)
            logger.error(f"Error ingesting document: {str(e)}")
            raise

    async def search_documents(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant documents"""
        start_time = time.time()
        try:
            logger.debug(f"Searching documents for query: {query}")
            results = self.collection.query(query_texts=[query], n_results=k)

            duration = time.time() - start_time
            self.monitoring.track_request("search_documents", duration)
            logger.info(
                f"Search completed in {duration:.2f}s, found {len(results['documents'][0])} results"
            )

            return [
                {"content": doc, "metadata": meta, "distance": dist}
                for doc, meta, dist in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                )
            ]
        except Exception as e:
            self.monitoring.track_error(e)
            logger.error(f"Error searching documents: {str(e)}")
            raise

    def _create_chunks(self, content: str, chunk_size: int = 1000) -> List[str]:
        """Split content into chunks for better embedding"""
        try:
            words = content.split()
            chunks = []
            current_chunk = []
            current_size = 0

            for word in words:
                if current_size + len(word) > chunk_size:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = [word]
                    current_size = len(word)
                else:
                    current_chunk.append(word)
                    current_size += len(word) + 1

            if current_chunk:
                chunks.append(" ".join(current_chunk))

            return chunks
        except Exception as e:
            logger.error(f"Error creating chunks: {str(e)}")
            raise

    def get_document_by_id(self, doc_id: str) -> Dict[str, Any]:
        """Retrieve a specific document by its ID."""
        try:
            result = self.collection.get(ids=[doc_id])
            if not result["documents"]:
                raise Exception("Document not found")
            return {
                "content": result["documents"][0],
                "metadata": result["metadatas"][0],
            }
        except Exception as e:
            raise Exception(f"Error retrieving document: {str(e)}")

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        try:
            result = self.collection.get()
            return {
                "total_documents": len(result["ids"]),
                "total_chunks": sum(
                    1
                    for m in result["metadatas"]
                    if "chunk_index" in m and m["chunk_index"] == 0
                ),
            }
        except Exception as e:
            raise Exception(f"Error getting collection stats: {str(e)}")
