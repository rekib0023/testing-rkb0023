from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from langchain.agents import Tool
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.tools import BaseTool
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from pydantic import Field

from app.config.config import settings
from app.core.logging_config import get_logger
from app.services.document_service import DocumentService

logger = get_logger(__name__)


class LegalUpdatesTool(BaseTool):
    """Tool to use when the query cannot be answered from context or other tools."""

    name: str = "legal_updates_search"
    description: str = "Search for legal updates including bills, amendments, and government notifications. If no legal updates are found, attempt to answer from existing documents."

    base_urls: Dict[str, str] = Field(
        default={
            "india_code": "https://www.indiacode.nic.in/",
            "prsindia": "https://prsindia.org/billtrack/",
            "legislative_gov": "https://legislative.gov.in/",
            # "egazette": "https://egazette.nic.in/",
        }
    )

    headers: Dict[str, str] = Field(
        default={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    )

    embeddings: OllamaEmbeddings = Field(
        default_factory=lambda: OllamaEmbeddings(
            model=settings.EMBEDDING_MODEL, base_url=settings.OLLAMA_BASE_URL
        )
    )

    text_splitter: RecursiveCharacterTextSplitter = Field(
        default_factory=lambda: RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
    )

    vector_store: Optional[FAISS] = Field(default=None)

    async def _run(self, query: str) -> str:
        """Search for legal updates based on the query."""
        try:
            results = []

            # Search PRS India for bills
            bills = self._get_recent_bills()
            if bills:
                results.extend(
                    [f"- Bill: {bill['title']} ({bill['url']})" for bill in bills]
                )

            # Search for constitution amendments
            amendments = self._get_constitution_amendments()
            if amendments:
                results.extend(
                    [
                        f"- Amendment: {amendment['number']} ({amendment['url']})"
                        for amendment in amendments
                    ]
                )

            # Search eGazette for notifications
            # notifications = self._get_gazette_notifications()
            # if notifications:
            #     results.extend(
            #         [
            #             f"- Notification: {notif['title']} ({notif['url']})"
            #             for notif in notifications
            #         ]
            #     )

        except Exception as e:
            logger.error(f"Error searching legal updates: {str(e)}")
            results.append(f"Error searching legal updates: {str(e)}")

        # If no legal updates are found, attempt to answer from existing documents
        if not results:
            try:
                document_service = DocumentService()
                doc_results = await document_service.search_documents(query)
                if doc_results:
                    formatted_docs = []
                    for i, doc in enumerate(doc_results):
                        source_name = doc["metadata"].get("source", f"Document {i + 1}")
                        formatted_docs.append(
                            f"Source: {source_name}\nContent: {doc['content']}"
                        )
                    doc_context_str = "\n\n".join(formatted_docs)
                    results.append(f"Based on existing documents:\n{doc_context_str}")
                else:
                    results.append("No relevant documents found.")
            except Exception as e:
                logger.error(f"Error searching documents: {str(e)}")
                results.append(f"Error searching documents: {str(e)}")

        return (
            "\n".join(results)
            if results
            else "I cannot answer this question based on the available information and tools."
        )

    def _get_recent_bills(self) -> List[Dict[str, Any]]:
        """Fetch recent bills from PRS India."""
        try:
            response = requests.get(self.base_urls["prsindia"], headers=self.headers)
            soup = BeautifulSoup(response.text, "html.parser")

            bills = []
            bill_elements = soup.select(".bill-item")

            for element in bill_elements:
                bill = {
                    "title": element.select_one(".bill-title").text.strip(),
                    "status": element.select_one(".bill-status").text.strip(),
                    "date": element.select_one(".bill-date").text.strip(),
                    "url": element.select_one("a")["href"],
                }
                bills.append(bill)

            return bills
        except Exception as e:
            logger.error(f"Error fetching bills: {str(e)}")
            return []

    def _get_constitution_amendments(self) -> List[Dict[str, Any]]:
        """Fetch recent constitution amendments."""
        try:
            response = requests.get(
                f"{self.base_urls['legislative_gov']}/constitution-amendments",
                headers=self.headers,
            )
            soup = BeautifulSoup(response.text, "html.parser")

            amendments = []
            amendment_elements = soup.select(".amendment-item")

            for element in amendment_elements:
                amendment = {
                    "number": element.select_one(".amendment-number").text.strip(),
                    "description": element.select_one(".amendment-desc").text.strip(),
                    "date": element.select_one(".amendment-date").text.strip(),
                    "url": element.select_one("a")["href"],
                }
                amendments.append(amendment)

            return amendments
        except Exception as e:
            logger.error(f"Error fetching amendments: {str(e)}")
            return []

    def _get_gazette_notifications(self) -> List[Dict[str, Any]]:
        """Fetch government gazette notifications."""
        try:
            response = requests.get(self.base_urls["egazette"], headers=self.headers)
            soup = BeautifulSoup(response.text, "html.parser")

            notifications = []
            notification_elements = soup.select(".notification-item")

            for element in notification_elements:
                notification = {
                    "title": element.select_one("h3").text.strip(),
                    "date": element.select_one(".notification-date").text.strip(),
                    "url": element.select_one("a")["href"],
                }
                notifications.append(notification)

            return notifications
        except Exception as e:
            logger.error(f"Error fetching notifications: {str(e)}")
            return []

    def create_embeddings(self, legal_docs: List[Dict[str, Any]]) -> None:
        """Create embeddings for legal documents."""
        try:
            texts = []
            metadatas = []

            for doc in legal_docs:
                text = f"Title: {doc.get('title', '')}\n"
                text += f"Description: {doc.get('description', '')}\n"
                text += f"Status: {doc.get('status', '')}\n"
                text += f"Date: {doc.get('date', '')}\n"

                chunks = self.text_splitter.split_text(text)
                texts.extend(chunks)
                metadatas.extend([doc] * len(chunks))

            if texts:
                self.vector_store = FAISS.from_texts(
                    texts=texts, embedding=self.embeddings, metadatas=metadatas
                )
        except Exception as e:
            logger.error(f"Error creating embeddings: {str(e)}")
            raise

    def search_similar(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Search for similar legal documents."""
        if not self.vector_store:
            return []

        try:
            docs = self.vector_store.similarity_search(query, k=k)
            return [doc.metadata for doc in docs]
        except Exception as e:
            logger.error(f"Error searching similar documents: {str(e)}")


class CannotAnswerTool(BaseTool):
    """Tool to use when the query cannot be answered from context or other tools."""

    name: str = "cannot_answer"
    description: str = (
        "Use this tool ONLY when the user's query cannot be answered using the "
        "provided context (documents and chat history) and the 'legal_updates' tool is not relevant."
    )

    def _run(self, query: str) -> str:
        """Returns a fixed message indicating inability to answer."""
        # The 'query' argument is required by the interface but not used here.
        return "I cannot answer this question based on the available information and tools."

    async def _arun(self, query: str) -> str:
        """Asynchronous version."""
        return self._run(query)


def get_legal_tools() -> List[BaseTool]:  # Changed return type hint
    """Get all legal-related tools."""
    tools: List[BaseTool] = [LegalUpdatesTool(), CannotAnswerTool()]
    # Convert BaseTool instances to Langchain Tool objects for the agent
    # Note: Using tool._run directly might bypass some Langchain features like callbacks.
    # Consider wrapping them properly if needed, but this matches the previous structure.
    return [
        Tool(
            name=tool.name,
            func=tool._arun,  # Using async _arun
            description=tool.description,
            coroutine=tool._arun,
        )
        for tool in tools
    ]
