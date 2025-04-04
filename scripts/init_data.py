import os
import json
from pathlib import Path
from app.data.ingestion import DataIngestion


def create_data_structure():
    """Create the necessary directory structure for legal documents."""
    base_dir = Path("data/legal_documents")
    acts_dir = base_dir / "acts"

    # Create directories
    base_dir.mkdir(parents=True, exist_ok=True)
    acts_dir.mkdir(parents=True, exist_ok=True)

    # Create sample constitution file
    constitution_data = {
        "articles": [
            {
                "number": "1",
                "title": "Name and territory of the Union",
                "content": "India, that is Bharat, shall be a Union of States...",
            },
            {
                "number": "2",
                "title": "Admission or establishment of new States",
                "content": "Parliament may by law admit into the Union, or establish, new States...",
            },
        ]
    }

    with open(base_dir / "constitution.json", "w") as f:
        json.dump(constitution_data, f, indent=2)

    # Create sample act file
    sample_act = {
        "name": "Indian Penal Code",
        "sections": [
            {
                "number": "1",
                "content": "This Act shall be called the Indian Penal Code...",
            },
            {
                "number": "2",
                "content": "Every person shall be liable to punishment under this Code...",
            },
        ],
    }

    with open(acts_dir / "ipc.json", "w") as f:
        json.dump(sample_act, f, indent=2)


def main():
    print("Initializing data structure...")
    create_data_structure()

    print("Starting data ingestion...")
    ingestion = DataIngestion()
    ingestion.run_ingestion()

    print("Initialization completed!")


if __name__ == "__main__":
    main()
