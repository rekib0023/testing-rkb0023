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

            # Define the system prompt for the agent
            system_prompt = (
                "You are a helpful legal AI assistant specializing in Indian law.\n"
                "IMPORTANT: Your primary goal is to answer the user's query based *only* on the 'Relevant Documents' provided in the context AND the ongoing 'Chat History'.\n"
                "1. Analyze the 'Relevant Documents' section and the 'Chat History' carefully.\n"
                "2. **Identify the key points from each document and combine them into a concise and coherent answer.**\n" # Added instruction to synthesize
                "3. If the answer is found within the documents or history, provide the answer and cite the source document if applicable (e.g., 'According to [source filename]...' or 'As mentioned earlier...').\n"
                "4. If the user asks for recent legal updates, bills, amendments, or government notifications, or if you cannot find an answer in the documents or history, use the 'legal_updates_search' tool.\n"
                "5. If the 'legal_updates_search' tool also cannot find an answer, use the 'cannot_answer' tool.\n" # Added instruction for cannot_answer tool
                "Do NOT use the 'legal_updates' tool for general questions if the answer might be in the documents or history."
            )

            # Initialize the agent with legal tools and system prompt
            self.agent = initialize_agent(
                tools=self.legal_tools,
                llm=self.llm,
                agent_kwargs={"system_message": system_prompt}, # Pass system prompt here
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
                error_msg = "Chat service not initialized"
                self.logger.error(error_msg)
                # Return ChatResponse without confidence
                return ChatResponse(response=error_msg, sources=[])

            # --- Context Building ---
            # Get relevant documents and format them for context
            doc_results = await self.document_service.search_documents(query)
            sources = [Source(content=doc['content'], metadata=doc['metadata']) for doc in doc_results] # Keep sources for the final response

            # Format documents for the input to the agent - use only the first two sentences
            formatted_docs = []
            if doc_results:
                 formatted_docs.append("--- Relevant Documents ---")
                 for i, doc in enumerate(doc_results):
                     source_name = doc['metadata'].get('source', f'Document {i+1}')
                     # Extract the first two sentences
                     sentences = doc['content'].split('.')
                     first_two_sentences = '.'.join(sentences[:2]) + '.' if len(sentences) >= 2 else doc['content']
                     formatted_docs.append(f"Source: {source_name}\nContent: {first_two_sentences}")
                 doc_context_str = "\n\n".join(formatted_docs)
            else:
                 doc_context_str = "No relevant documents found."


            # Combine retrieved documents context with any additional provided context
            input_context = doc_context_str
            if context:
                input_context += f"\n\n--- Additional Context ---\n{chr(10).join(context)}"

            # Prepare the input for the agent. The agent framework will handle combining
            # this with chat_history and the system_prompt provided during initialization.
            agent_input = {
                "input": f"Context:\n{input_context}\n\nUser Query: {query}"
            }

            # Get response from agent using ainvoke
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
