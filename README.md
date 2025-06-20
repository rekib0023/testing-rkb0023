# Indian Legal AI Assistant

A legal AI assistant that helps users understand and search through Indian legal documents including the Constitution, bills, amendments, and sections.

## Features

- Vector database-based document storage and retrieval
- Real-time legal updates tracking
- Chat interface for natural language queries
- Integration with Ollama for LLM capabilities
- FastAPI backend for API interactions

---

## Setup

1. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the Ollama server (make sure it's running locally)

4. Run the application:

```bash
uvicorn app.main:app --reload
```

## Project Structure

- `app/`: Main application code
  - `main.py`: FastAPI application entry point
  - `models/`: Data models
  - `services/`: Business logic
  - `utils/`: Utility functions
  - `data/`: Data ingestion and processing
- `tests/`: Test files
- `docs/`: Documentation

## API Documentation

Once the server is running, visit `http://localhost:8000/docs` for interactive API documentation.
