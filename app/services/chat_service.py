from typing import List, Dict, Any, Optional
from app.core.base_service import BaseService
from app.services.document_service import DocumentService
from app.core.monitoring import MonitoringService
from app.core.logging_config import get_logger
from app.config.config import settings
import json
from langchain_ollama import OllamaLLM
from app.utils.legal_tools import get_legal_tools
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
import chromadb
from chromadb.config import Settings

logger = get_logger(__name__)


class ChatService(BaseService):
    def __init__(self):
        super().__init__()
        self.document_service = DocumentService()
        self.chat_history = []
        self.monitoring = MonitoringService()

        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_DB_PATH, settings=Settings(allow_reset=True)
        )
        self.legal_collection = self.chroma_client.get_or_create_collection(
            name="legal_updates", metadata={"hnsw:space": "cosine"}
        )

        # Initialize Langchain Ollama with simpler configuration
        self.llm = OllamaLLM(
            model=settings.CHAT_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.7,
        )

        # Initialize legal tools
        self.legal_tools = get_legal_tools()

        # Create agent with legal tools
        self.agent = initialize_agent(
            tools=self.legal_tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
        )

    async def initialize(self) -> None:
        """Initialize services"""
        try:
            logger.info("Initializing ChatService")
            await self.monitoring.initialize()
            await self.document_service.initialize()
            logger.info("ChatService initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing ChatService: {str(e)}", exc_info=True)
            raise

    async def cleanup(self) -> None:
        """Clean up resources"""
        logger.info("Cleaning up ChatService")
        await self.document_service.cleanup()
        await self.monitoring.cleanup()
        self.chat_history = []

    async def get_response(
        self, query: str, context: Optional[List[str]] = None
    ) -> Dict:
        """Get a response for the given query"""
        try:
            # Search ChromaDB for relevant legal updates
            legal_results = self.legal_collection.query(
                query_texts=[query], n_results=3
            )

            # Search for relevant documents
            doc_results = await self.document_service.search_documents(query)

            # Combine results
            all_results = []
            if legal_results and legal_results["documents"]:
                all_results.extend(
                    [
                        {"content": doc, "metadata": meta, "distance": dist}
                        for doc, meta, dist in zip(
                            legal_results["documents"][0],
                            legal_results["metadatas"][0],
                            legal_results["distances"][0],
                        )
                    ]
                )

            if doc_results:
                all_results.extend(doc_results)

            # Handle case when no relevant documents are found
            if not all_results:
                logger.warning(f"No relevant documents found for query: {query}")
                context_text = "No relevant legal documents were found for this query."
                confidence = 0.0
            else:
                # Calculate confidence score
                total_score = sum(result["distance"] for result in all_results)
                confidence = 1.0 - min(1.0, total_score / len(all_results))

                # Prepare context from search results
                context_text = "\n\n".join(
                    [
                        f"Document {i+1}:\n{result['content']}"
                        for i, result in enumerate(all_results)
                    ]
                )

            # Add additional context if provided
            if context and isinstance(context, list):
                additional_context = "\n\n".join(context)
                context_text = (
                    f"{context_text}\n\nAdditional Context:\n{additional_context}"
                )

            system_prompt = """You are a legal AI assistant specializing in Indian law.
            Your responses should be clear, accurate, and based on the provided legal documents.
            Format your responses using Markdown for better readability.
            When citing legal articles, use proper formatting and reference the specific article numbers."""

            user_prompt = f"""Based on the following context and using available legal tools,
                please answer this question: {query}

                Context:
                {context_text}

                If no relevant information is found, use the legal tools to search for
                recent updates and provide a comprehensive response."""

            # Use agent to get response with legal tools
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            agent_response = self.agent.run(full_prompt)

            return {
                "response": agent_response,
                "confidence": confidence,
                "sources": [
                    {"content": result["content"], "metadata": result["metadata"]}
                    for result in (all_results or [])
                ],
            }

        except Exception as e:
            self.monitoring.track_error(e)
            logger.error(f"Error in get_response: {str(e)}")
            raise

    def get_chat_history(self) -> List[Dict[str, str]]:
        """Get the chat history"""
        logger.debug("Retrieving chat history")
        return self.chat_history

    def clear_history(self) -> None:
        """Clear the chat history"""
        logger.info("Clearing chat history")
        self.chat_history = []
