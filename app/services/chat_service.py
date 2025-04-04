from typing import List, Dict, Any, Optional
from langchain_community.chat_models import ChatOllama
from langchain.agents import AgentType, initialize_agent
from langchain.memory import ConversationBufferMemory
from app.services.base_service import BaseService
from app.services.document_service import DocumentService
from app.services.monitoring_service import MonitoringService
from app.utils.legal_tools import get_legal_tools
from app.core.logging_config import get_logger
from app.config.config import settings

logger = get_logger(__name__)


class ChatService(BaseService):
    """Service for handling chat interactions with legal AI."""

    def __init__(self):
        """Initialize the chat service."""
        super().__init__()
        self.document_service = DocumentService()
        self.monitoring_service = MonitoringService()
        self.memory = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True
        )
        self.llm = ChatOllama(
            model=settings.CHAT_MODEL, base_url=settings.OLLAMA_BASE_URL
        )
        self.agent = None
        self.legal_tools = get_legal_tools()

    async def initialize(self) -> None:
        """Initialize the chat service and its dependencies."""
        try:
            await self.document_service.initialize()
            await self.monitoring_service.initialize()

            # Initialize the agent with legal tools
            self.agent = initialize_agent(
                tools=self.legal_tools,
                llm=self.llm,
                agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
                verbose=True,
                memory=self.memory,
                handle_parsing_errors=True,
            )

            self.logger.info("Chat service initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing chat service: {str(e)}")
            raise

    async def cleanup(self) -> None:
        """Clean up resources used by the chat service."""
        try:
            await self.document_service.cleanup()
            await self.monitoring_service.cleanup()
            self.memory.clear()
            self.logger.info("Chat service cleaned up successfully")
        except Exception as e:
            self.logger.error(f"Error cleaning up chat service: {str(e)}")
            raise

    async def get_response(
        self, query: str, context: Optional[List[str]] = None
    ) -> str:
        """Get a response for the given query.

        Args:
            query: The user's query string.
            context: Optional list of context strings to include in the response.

        Returns:
            str: The generated response.
        """
        try:
            if not self.agent:
                raise ValueError("Chat service not initialized")

            # Get relevant documents
            docs = await self.document_service.search_documents(query)

            # Get legal updates
            legal_updates = self.legal_tools[0]._run(query)

            # Combine context
            context_parts = [
                f"Relevant Documents:\n{docs}",
                f"Legal Updates:\n{legal_updates}",
            ]

            # Add additional context if provided
            if context:
                context_parts.append(f"Additional Context:\n{chr(10).join(context)}")

            full_context = chr(10).join(context_parts)

            # Get response from agent
            response = await self.agent.arun(
                input=f"Context: {full_context}\n\nUser Query: {query}"
            )

            # Log the interaction
            await self.monitoring_service.log_interaction(
                query=query,
                response=response,
                source="chat",
                metadata={"context": context} if context else None,
            )

            return response
        except Exception as e:
            self.logger.error(f"Error getting response: {str(e)}")
            await self.monitoring_service.log_error(
                e, {"query": query, "context": context}
            )
            return f"Error: {str(e)}"

    def get_chat_history(self) -> List[Dict[str, str]]:
        """Get the chat history.

        Returns:
            List[Dict[str, str]]: The chat history messages.
        """
        return self.memory.chat_memory.messages

    def clear_history(self) -> None:
        """Clear the chat history."""
        self.memory.clear()
