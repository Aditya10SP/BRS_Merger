# GenAI BRS Consolidator

Enterprise-grade system for consolidating multiple Business Requirement Specification (BRS) documents and Change Requests (CR) into a single Final BRS using controlled Retrieval-Augmented Generation (RAG).

## 🎯 Key Features

- **Accurate & Traceable**: Every requirement is traceable to source documents
- **Hallucination-Free**: Strict Evidence Pack constraints prevent LLM hallucinations
- **Conflict Resolution**: Automatic detection and resolution of conflicting changes
- **Multi-Format Support**: PDF and DOCX document ingestion
- **Semantic Chunking**: Section-aware document chunking for precise retrieval
- **Hybrid RAG**: Combines vector similarity with metadata filtering
- **Validation Layer**: LLM-based and rule-based quality validation
- **REST API**: FastAPI-based endpoints for easy integration

## 🏗️ Architecture

```
┌─────────────────┐
│  BRS/CR Upload  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Document Parser │ (PDF/DOCX → Structured JSON)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Semantic Chunker│ (Section-aware splitting)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Vector Store   │ (ChromaDB + Embeddings)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   RAG Engine    │ (Evidence Pack Builder)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LLM Generator  │ (Constrained Generation)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Validator     │ (Quality Assurance)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Final BRS     │ (JSON + Markdown)
└─────────────────┘
```

## 📋 Requirements

- Python 3.9+
- OpenAI API key (or Google Gemini API key, or local Ollama)

## 🚀 Quick Start

### 1. Setup Ollama

```bash
# Install Ollama from https://ollama.ai (if not already installed)

# Pull the qwen2.5 model
ollama pull qwen2.5

# Start Ollama server
ollama serve
```

### 2. Setup Backend

```bash
# Navigate to project directory
cd BRS_Merger2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file (already configured for Ollama)
cp .env.example .env

# Start the backend server
python -m uvicorn app.main:app --reload
```

Backend will be available at http://localhost:8000

### 3. Setup Frontend

```bash
# Open a new terminal
cd BRS_Merger2/frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

Frontend will be available at http://localhost:3000

### 4. Use the System

1. Open http://localhost:3000 in your browser
2. Upload BRS documents from `test_example/` folder
3. Upload Change Request documents
4. Click "Start Consolidation"
5. Download the final BRS when complete

**See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.**

## 📖 Usage

### API Endpoints

#### 1. Upload BRS Document

```bash
curl -X POST "http://localhost:8000/api/v1/upload/brs" \
  -F "file=@path/to/brs_v1.pdf" \
  -F "doc_id=BRS-2024-001" \
  -F "version=v1.0"
```

#### 2. Upload Change Request

```bash
curl -X POST "http://localhost:8000/api/v1/upload/cr" \
  -F "file=@path/to/cr_042.pdf" \
  -F "cr_id=CR-042" \
  -F "priority=high" \
  -F "approval_status=approved"
```

#### 3. Consolidate BRS

```bash
curl -X POST "http://localhost:8000/api/v1/consolidate" \
  -H "Content-Type: application/json" \
  -d '{
    "brs_id": "BRS-FINAL-2024",
    "title": "Authentication System BRS",
    "version": "v3.0"
  }'
```

Response:
```json
{
  "status": "success",
  "message": "Consolidation started",
  "job_id": "abc123..."
}
```

#### 4. Check Job Status

```bash
curl "http://localhost:8000/api/v1/job/abc123..."
```

#### 5. Get System Stats

```bash
curl "http://localhost:8000/api/v1/stats"
```

### Python SDK Usage

```python
from pathlib import Path
from app.services.orchestrator import BRSOrchestrator
from app.models.schemas import Priority, ApprovalStatus

# Initialize orchestrator
orchestrator = BRSOrchestrator()

# Process BRS documents
brs1 = orchestrator.process_brs_document(
    file_path=Path("data/brs_v1.pdf"),
    doc_id="BRS-2024-001",
    version="v1.0"
)

# Process Change Requests
cr = orchestrator.process_change_request(
    file_path=Path("data/cr_042.pdf"),
    cr_id="CR-042",
    priority=Priority.HIGH,
    approval_status=ApprovalStatus.APPROVED
)

# Consolidate
final_brs = orchestrator.consolidate_brs(
    brs_id="BRS-FINAL-2024",
    title="Authentication System BRS",
    version="v3.0"
)

# Export
orchestrator.export_to_json(final_brs, Path("output/final_brs.json"))
orchestrator.export_to_markdown(final_brs, Path("output/final_brs.md"))
```

## 🔧 Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | LLM provider (openai/gemini/ollama) | `ollama` |
| `LLM_MODEL` | Model name | `qwen2.5` |
| `LLM_TEMPERATURE` | Generation temperature | `0.1` |
| `EMBEDDING_MODEL` | Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| `TOP_K_RETRIEVAL` | Number of chunks to retrieve | `5` |
| `MAX_CHUNK_SIZE` | Maximum chunk size in characters | `1000` |

**Using Ollama (Default)**:
- No API key required
- Runs locally on your machine
- Model: qwen2.5
- Ollama must be running: `ollama serve`

**Using Cloud Providers**:
Edit `.env` and set:
- For OpenAI: `LLM_PROVIDER=openai` and `OPENAI_API_KEY=your_key`
- For Gemini: `LLM_PROVIDER=gemini` and `GEMINI_API_KEY=your_key`

## 📁 Project Structure

```
BRS_Merger2/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── core/
│   │   ├── config.py          # Configuration settings
│   │   └── logging_config.py  # Logging setup
│   ├── models/
│   │   └── schemas.py         # Pydantic models
│   ├── services/
│   │   ├── ingestion.py       # Document parser
│   │   ├── chunking.py        # Semantic chunker
│   │   ├── vector_store.py    # ChromaDB wrapper
│   │   ├── rag_engine.py      # Evidence Pack builder
│   │   ├── llm_client.py      # LLM client wrapper
│   │   ├── prompts.py         # Prompt templates
│   │   ├── generator.py       # BRS generator
│   │   ├── validator.py       # Validation service
│   │   └── orchestrator.py    # Pipeline orchestrator
│   └── api/
│       └── endpoints.py       # REST API endpoints
├── data/
│   ├── uploads/               # Uploaded files
│   ├── outputs/               # Generated BRS files
│   └── chroma_db/            # Vector database
├── tests/                     # Unit tests
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
└── README.md                 # This file
```

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=app tests/
```

## 🔒 Security Considerations

- **API Keys**: Never commit `.env` file to version control
- **File Upload**: Validate file types and sizes
- **Production**: Use proper authentication and authorization
- **Vector Store**: Secure ChromaDB persistence directory

## 🎓 How It Works

### 1. Evidence Pack Strategy

The system uses **Evidence Packs** to prevent hallucinations:

```python
EvidencePack = {
    "section_id": "SEC-001",
    "base_content": "Original BRS text...",
    "approved_changes": [ChangeDelta1, ChangeDelta2],
    "conflicts": [ConflictInfo],
    "source_documents": ["BRS-001", "CR-042"]
}
```

The LLM is **forbidden** from using information outside the Evidence Pack.

### 2. Conflict Resolution

Conflicts are resolved using:
1. **Priority**: CRITICAL > HIGH > MEDIUM > LOW
2. **Approval Status**: APPROVED > PENDING > REJECTED
3. **Timestamp**: Most recent wins
4. **Human Review**: Flagged if deterministic resolution fails

### 3. Traceability

Every generated section includes:
- Source BRS document IDs
- Applied CR IDs
- Generation timestamp

Example output:
```markdown
## 3.1 User Authentication

The system shall support multi-factor authentication...

*[Sources: BRS-2024-001 v2.0, CR-042]*
*[Applied Changes: CR-042, CR-043]*
```

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🐛 Troubleshooting

### ChromaDB Issues
```bash
# Reset vector store
curl -X DELETE "http://localhost:8000/api/v1/reset"
```

### LLM Connection Issues
- Verify API key in `.env`
- Check network connectivity
- For Ollama, ensure service is running: `ollama serve`

### Memory Issues
- Reduce `MAX_CHUNK_SIZE` in config
- Reduce `TOP_K_RETRIEVAL` value
- Process documents in smaller batches

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Check API documentation at `/docs`
- Review logs in `logs/brs_consolidator.log`

---

**Built with ❤️ using FastAPI, ChromaDB, and LangChain principles**
