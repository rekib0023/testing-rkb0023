from typing import List, Dict, Any, Optional
from langchain_ollama import ChatOllama
from langchain.agents import AgentType, initialize_agent
from langchain.memory import ConversationBufferMemory
from app.services.base_service import BaseService
from app.services.document_service import DocumentService
from app.services.monitoring_service import MonitoringService
from app.utils.legal_tools import get_legal_tools
from app.core.logging_config import get_logger
from app.config.config import settings
from app.schemas.chat import ChatResponse, Source # Added import

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
    ) -> ChatResponse: # Changed return type
        """Get a response for the given query.

        Args:
            query: The user's query string.
            context: Optional list of context strings to include in the response.

        Returns:
            ChatResponse: The generated response object including sources and confidence.
        """
        try:
            if not self.agent:
                # Return a valid ChatResponse even if not initialized
                error_msg = "Chat service not initialized"
                self.logger.error(error_msg)
                # Return ChatResponse without confidence
                return ChatResponse(response=error_msg, sources=[])

            # --- Prompt Engineering & Context Building ---
            # Refined System Prompt: Emphasize using context first, tool second.
            system_prompt = (
                "You are a helpful legal AI assistant specializing in Indian law.\n"
                "IMPORTANT: Your primary goal is to answer the user's query based *only* on the 'Relevant Documents' provided in the context.\n"
                "1. Analyze the 'Relevant Documents' section carefully.\n"
                "2. If the answer is found within the documents, provide the answer and cite the source document (e.g., 'According to [source filename]...').\n"
                "3. If the answer is NOT found in the documents, state that clearly (e.g., 'The provided documents do not contain information about X.').\n"
                "4. ONLY use the 'legal_updates' tool if the user explicitly asks for recent legal updates, bills, amendments, or government notifications.\n"
                "Do NOT use the 'legal_updates' tool for general questions if the answer might be in the documents."
            )

            # Get relevant documents and format them for context
            doc_results = await self.document_service.search_documents(query)
            sources = [Source(content=doc['content'], metadata=doc['metadata']) for doc in doc_results]

            formatted_docs = []
            for i, doc in enumerate(doc_results):
                source_name = doc['metadata'].get('source', f'Document {i+1}')
                formatted_docs.append(f"--- Document {i+1} (Source: {source_name}) ---\n{doc['content']}")
            doc_context_str = "\n\n".join(formatted_docs)

            # Combine context parts
            context_parts = [f"--- Relevant Documents ---\n{doc_context_str}"]
            if context:
                context_parts.append(f"\n--- Additional Context ---\n{chr(10).join(context)}")

            full_context = "\n".join(context_parts)

            # Construct the final prompt for the agent
            final_prompt = (
                f"{system_prompt}\n\n"
                f"--- Context ---\n{full_context}\n\n"
                f"--- User Query ---\n{query}"
            )

            # Get response from agent using ainvoke
            agent_input = {"input": final_prompt} # Use the engineered prompt
            agent_response = await self.agent.ainvoke(agent_input)
            response = agent_response.get("output", "Error: Could not parse agent response.")

            # Log the interaction
            await self.monitoring_service.log_interaction(
                query=query,
                response=response,
                source="chat",
                metadata={"context": context} if context else None,
            )

            # Return ChatResponse without confidence
            return ChatResponse(response=response, sources=sources)

        except Exception as e:
            error_msg = f"Error getting response: {str(e)}"
            self.logger.error(error_msg, exc_info=True) # Log with traceback
            await self.monitoring_service.log_error(
                e, {"query": query, "context": context}
            )
            # Return ChatResponse without confidence on error
            return ChatResponse(response=error_msg, sources=[])

    def get_chat_history(self) -> List[Dict[str, str]]:
        """Get the chat history.

        Returns:
            List[Dict[str, str]]: The chat history messages.
        """
        return self.memory.chat_memory.messages

    def clear_history(self) -> None:
        """Clear the chat history."""
        self.memory.clear()
