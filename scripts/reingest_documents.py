import json
from pathlib import Path
from app.services.document_service import DocumentService


def main():
    # Initialize document service (this will create a fresh ChromaDB)
    doc_service = DocumentService()

    # Load and ingest constitution
    constitution_path = Path("data/legal_documents/constitution.json")
    if constitution_path.exists():
        with open(constitution_path, "r") as f:
            constitution_data = json.load(f)

        # Ingest each article as a separate document
        for article in constitution_data:
            metadata = {
                "type": "constitution",
                "article_number": article.get("article_number", ""),
                "format": "json",
                "source": "Constitution of India",
            }
            doc_service.ingest_document(article.get("text", ""), metadata)

        print("Constitution re-ingested successfully")

        # Print collection stats
        stats = doc_service.get_collection_stats()
        print(f"Total documents: {stats['total_documents']}")
        print(f"Total original documents: {stats['total_chunks']}")
    else:
        print("Constitution file not found")


if __name__ == "__main__":
    main()
