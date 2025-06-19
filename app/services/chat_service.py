from typing import List, Optional

from langchain.agents import AgentType, initialize_agent
from langchain.memory import ConversationBufferMemory
from langchain.schema.messages import BaseMessage
from langchain_ollama import ChatOllama

from app.config.config import settings
from app.core.logging_config import get_logger
from app.schemas.chat import ChatResponse, Source
from app.services.base_service import BaseService
from app.services.document_service import DocumentService
from app.services.monitoring_service import MonitoringService
from app.utils.legal_tools import get_legal_tools

logger = get_logger(__name__)

AGENT_SYSTEM_PROMPT = """You are an expert legal AI assistant for Indian Law. Your goal
is to provide accurate, context-aware answers.

Follow these steps to answer the user's query:

1.  **Analyze Context**: First, carefully review the 'Chat History' for conversational
    context. Then, analyze the 'Relevant Documents' provided below.

2.  **Synthesize Answer**:
    * If the 'Relevant Documents' or 'Chat History' contain the information needed to
    answer the user's query, synthesize a comprehensive answer directly from this
    material.
    * Combine key points from multiple sources into a single, coherent response.
    * When you use information from a document, you MUST cite the source filename
    (e.g., "According to [source filename]...").

3.  **Use Tools if Necessary**:
    * If the user explicitly asks for recent legal updates, new bills, amendments, or
    government notifications, OR if the provided documents and chat history are
    insufficient to answer the query, use the `legal_updates_search` tool.
    * Only after trying `legal_updates_search` and still not finding an answer, use the
    `cannot_answer` tool to state that you cannot provide an answer.

4.  **General Knowledge**: For general legal questions where no documents are provided
    and no specific updates are requested, you may use your internal knowledge.
    However, prioritize provided context above all else.
"""


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
        self.logger = logger

    async def initialize(self) -> None:
        """Initialize the chat service and its dependencies."""
        try:
            await self.document_service.initialize()
            await self.monitoring_service.initialize()

            self.agent = initialize_agent(
                tools=self.legal_tools,
                llm=self.llm,
                agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
                verbose=settings.AGENT_VERBOSE,
                memory=self.memory,
                handle_parsing_errors="""Could not parse LLM output. Please follow the
                required format. If you have the final answer, please provide it using
                the 'Final Answer:' format.""",
                agent_kwargs={"system_message": AGENT_SYSTEM_PROMPT},
            )

            self.logger.info("Chat service initialized successfully")
        except Exception as e:
            self.logger.error(
                f"Error initializing chat service: {str(e)}", exc_info=True
            )
            raise

    async def cleanup(self) -> None:
        """Clean up resources used by the chat service."""
        try:
            await self.document_service.cleanup()
            await self.monitoring_service.cleanup()
            self.memory.clear()
            self.logger.info("Chat service cleaned up successfully")
        except Exception as e:
            self.logger.error(
                f"Error cleaning up chat service: {str(e)}", exc_info=True
            )
            raise

    async def get_response(
        self, query: str, context: Optional[List[str]] = None
    ) -> ChatResponse:
        """Get a response for the given query.

        Args:
            query: The user's query string.
            context: Optional list of context strings to include in the response.

        Returns:
            ChatResponse: The generated response object including sources.
        """
        if not self.agent:
            error_msg = """Chat service is not initialized. Please ensure initialize()
            is called before getting a response."""
            self.logger.error(error_msg)
            return ChatResponse(response=error_msg, sources=[])

        try:
            # --- Context Building ---
            doc_results = await self.document_service.search_documents(query)
            sources = [
                Source(content=doc["content"], metadata=doc["metadata"])
                for doc in doc_results
            ]

            formatted_docs = []
            if doc_results:
                formatted_docs.append("--- Relevant Documents ---")
                for doc in doc_results:
                    source_name = doc["metadata"].get("source", "Unknown Document")
                    content = doc["content"]
                    formatted_docs.append(f"Source: {source_name}\nContent: {content}")
                doc_context_str = "\n\n".join(formatted_docs)
            else:
                doc_context_str = "No relevant documents were found for this query."

            input_context = doc_context_str
            if context:
                input_context += (
                    f"\n\n--- Additional Context ---\n{chr(10).join(context)}"
                )

            agent_input = {"input": f"Context:\n{input_context}\n\nUser Query: {query}"}

            agent_response = await self.agent.ainvoke(agent_input)
            response = agent_response.get(
                "output", "Error: Could not parse agent response."
            )

            await self.monitoring_service.log_interaction(
                query=query,
                response=response,
                source="chat",
                metadata={"context_sources": [s.metadata for s in sources]},
            )

            return ChatResponse(response=response, sources=sources)

        except Exception as e:
            error_msg = (
                f"An unexpected error occurred while getting the response: {str(e)}"
            )
            self.logger.error(error_msg, exc_info=True)
            await self.monitoring_service.log_error(
                e, {"query": query, "context": context}
            )
            return ChatResponse(response=error_msg, sources=[])

    def get_chat_history(self) -> List[BaseMessage]:
        """Get the chat history as a list of LangChain message objects.

        Returns:
            List[BaseMessage]: The chat history messages.
        """
        return self.memory.chat_memory.messages

    def clear_history(self) -> None:
        """Clear the chat history."""
        self.memory.clear()
        self.logger.info("Chat history cleared.")
