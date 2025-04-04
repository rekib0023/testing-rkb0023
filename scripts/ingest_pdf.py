import argparse
import json
import re
import asyncio
from pathlib import Path
from typing import List, Dict, Any
import fitz  # PyMuPDF
from app.services.document_service import DocumentService
from app.core.logging_config import get_logger

logger = get_logger(__name__)

async def ingest_document(doc_service: DocumentService, article: Dict[str, Any], metadata: Dict[str, Any]) -> None:
    """Ingest a single document into the vector store"""
    try:
        await doc_service.ingest_document(article["content"], metadata)
        logger.info(f"Ingested Article {metadata['article_number']}")
    except Exception as e:
        logger.error(f"Error ingesting article {metadata['article_number']}: {str(e)}")

async def ingest_pdf(pdf_path: str, is_constitution: bool = True) -> None:
    """Process and ingest a PDF file"""
    doc_service = DocumentService()
    await doc_service.initialize()

    # Open the PDF
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()

    # Split into articles
    articles = []
    current_article = {"content": "", "number": None}

    # Process text into articles
    lines = text.split('\n')
    for line in lines:
        if "ARTICLE" in line.upper() or "SECTION" in line.upper():
            if current_article["content"]:
                articles.append(current_article)
                current_article = {"content": "", "number": None}

            # Try to extract article number
            number_match = re.search(r'Article\s+(\d+)', line, re.IGNORECASE)
            if number_match:
                current_article["number"] = number_match.group(1)
                print(f"Extracted article number: {current_article['number']}")
            else:
                section_match = re.search(r'Section\s+(\d+)', line, re.IGNORECASE)
                if section_match:
                    current_article["number"] = f"section_{section_match.group(1)}"
                else:
                    current_article["number"] = f"section_{len(articles) + 1}"
                print(f"No number found, using: {current_article['number']}")

            print(f"Found article heading: {line}")

        current_article["content"] += line + "\n"

    # Add the last article
    if current_article["content"]:
        articles.append(current_article)

    print(f"Structured {len(articles)} articles")

    # Save to JSON for backup
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "constitution.json" if is_constitution else output_dir / "legal_document.json"
    print(f"Saving {len(articles)} articles to JSON...")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

    # Ingest articles
    tasks = []
    for article in articles:
        if not article["content"].strip():
            continue

        metadata = {
            "article_number": article["number"],
            "document_type": "constitution" if is_constitution else "legal_document",
            "title": f"Article {article['number']}",
            "length": len(article["content"])
        }

        print(f"Saving article {article['number']} with length {len(article['content'])}")
        tasks.append(ingest_document(doc_service, article, metadata))

    # Wait for all ingestion tasks to complete
    await asyncio.gather(*tasks)
    await doc_service.cleanup()

def main():
    parser = argparse.ArgumentParser(description='Ingest a PDF document into the vector store')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('--constitution', action='store_true', help='Process as Constitution')
    args = parser.parse_args()

    asyncio.run(ingest_pdf(args.pdf_path, args.constitution))

if __name__ == "__main__":
    main()
