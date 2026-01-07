# Troubleshooting Guide

## Issue: Empty Sections in Generated BRS

### Problem
Generated PDF/Markdown/JSON files have sections with content like:
```
"[GENERATION FAILED] 404 page not found\n\nPlease review manually."
```

### Root Cause
The LLM (Ollama) is not running or not accessible, causing all generation attempts to fail.

### Solution

#### 1. Check if Ollama is Running

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If you get a connection error, start Ollama:
ollama serve
```

#### 2. Verify Model is Installed

```bash
# List installed models
ollama list

# If qwen2.5:1.5b is not installed, pull it:
ollama pull qwen2.5:1.5b
```

#### 3. Test Ollama Connection

```bash
# Test the API endpoint
curl http://localhost:11434/v1/models
```

#### 4. Check Configuration

Verify in `app/core/config.py` or `.env`:
```python
LLM_PROVIDER = "ollama"
OLLAMA_BASE_URL = "http://localhost:11434/v1"
LLM_MODEL = "qwen2.5:1.5b"
```

### Alternative: Use Different LLM Provider

If Ollama is not available, you can use OpenAI or Gemini:

1. **OpenAI**:
   ```python
   LLM_PROVIDER = "openai"
   OPENAI_API_KEY = "your-api-key"
   LLM_MODEL = "gpt-3.5-turbo"  # or gpt-4
   ```

2. **Google Gemini**:
   ```python
   LLM_PROVIDER = "gemini"
   GEMINI_API_KEY = "your-api-key"
   LLM_MODEL = "gemini-pro"
   ```

## Issue: Too Many Documents Being Processed

### Problem
The system processes 79+ documents when you only uploaded 4 files.

### Root Cause
The vector store contains data from previous runs. The `_extract_section_outline()` method retrieves ALL sections from the vector store, not just from your recent uploads.

### Solution

#### Option 1: Reset Vector Store (Recommended for Testing)

```bash
# Via API
curl -X DELETE "http://localhost:8000/api/v1/reset"

# Or delete the database manually
rm -rf data/chroma_db/*
```

#### Option 2: Provide Custom Section Outline

When calling the consolidation API, provide a `section_outline` parameter:

```json
{
  "brs_id": "BRS-FINAL-2024",
  "title": "My BRS",
  "version": "v1.0",
  "section_outline": [
    {"section_id": "SEC-001", "section_title": "Introduction", "section_path": "1"},
    {"section_id": "SEC-002", "section_title": "Requirements", "section_path": "2"}
  ]
}
```

## Issue: Sections Have No Content

### Problem
Sections are generated but have empty or minimal content.

### Possible Causes

1. **No Base Content Found**: The RAG engine couldn't find matching sections in the uploaded BRS documents.
2. **Section IDs Don't Match**: The section IDs in your documents don't match what the system expects.
3. **Document Parsing Failed**: The PDF/DOCX parsing didn't extract sections correctly.

### Solution

1. **Check Document Parsing**:
   - Verify your PDF/DOCX files have clear section headings
   - Sections should be numbered (e.g., "1. Introduction", "2. Requirements")
   - Check logs for parsing errors

2. **Check Vector Store**:
   ```python
   # Check what's in the vector store
   stats = orchestrator.get_stats()
   print(stats)
   ```

3. **Review Logs**:
   Check `logs/brs_consolidator.log` for:
   - Section detection messages
   - Evidence pack building messages
   - Generation errors

## Quick Fix Checklist

Before running consolidation:

- [ ] Ollama is running: `ollama serve`
- [ ] Model is installed: `ollama pull qwen2.5:1.5b`
- [ ] Vector store is clean (or you're okay with old data)
- [ ] Documents are properly formatted with numbered sections
- [ ] Check logs for errors

## Testing with Sample Data

Use the provided sample files to test:

```bash
# Upload sample BRS
curl -X POST "http://localhost:8000/api/v1/upload/brs" \
  -F "file=@data/samples/sample_brs.json" \
  -F "doc_id=BRS-TEST-001" \
  -F "version=v1.0"

# Upload sample CR
curl -X POST "http://localhost:8000/api/v1/upload/cr" \
  -F "file=@data/samples/sample_cr.json" \
  -F "cr_id=CR-TEST-001" \
  -F "priority=high" \
  -F "approval_status=approved"

# Consolidate
curl -X POST "http://localhost:8000/api/v1/consolidate" \
  -H "Content-Type: application/json" \
  -d '{
    "brs_id": "BRS-TEST-FINAL",
    "title": "Test BRS",
    "version": "v1.0"
  }'
```

## Getting Help

1. Check logs: `logs/brs_consolidator.log`
2. Check API docs: `http://localhost:8000/docs`
3. Verify Ollama: `curl http://localhost:11434/api/tags`
4. Check vector store stats: `GET /api/v1/stats`

