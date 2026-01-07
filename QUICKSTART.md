# Quick Start Guide - GenAI BRS Consolidator

## Prerequisites

1. **Ollama** installed and running
2. **Python 3.9+**
3. **Node.js 18+** (for frontend)

## Step 1: Setup Ollama

```bash
# Verify Ollama is installed
ollama --version

# Pull the qwen2.5 model
ollama pull qwen2.5

# Start Ollama server (if not already running)
ollama serve
```

## Step 2: Setup Backend

```bash
# Navigate to project root
cd /Users/adityasp_18/Desktop/Python/BRS_Merger2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# The .env is already configured for Ollama qwen2.5
# No changes needed unless you want to use a different model

# Start the backend server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: http://localhost:8000
API docs at: http://localhost:8000/docs

## Step 3: Setup Frontend

```bash
# Open a new terminal
cd /Users/adityasp_18/Desktop/Python/BRS_Merger2/frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

Frontend will be available at: http://localhost:3000

## Step 4: Test the System

1. **Open browser**: Navigate to http://localhost:3000

2. **Upload test documents**:
   - Upload BRS files from `test_example/` folder (v1.pdf, v2.pdf, etc.)
   - Upload CR files (cr1.pdf, cr2.pdf, etc.)

3. **Start consolidation**:
   - Click "Start Consolidation" button
   - Monitor the job status
   - Download the final BRS when complete

## Troubleshooting

### Ollama Connection Issues
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve
```

### Backend Issues
```bash
# Check backend health
curl http://localhost:8000/api/v1/health

# View logs
tail -f logs/brs_consolidator.log
```

### Frontend Issues
```bash
# Clear Next.js cache
cd frontend
rm -rf .next
npm run dev
```

## Using the System

### Via Web Interface (Recommended)
1. Go to http://localhost:3000
2. Upload BRS and CR documents
3. Click "Start Consolidation"
4. Download results

### Via API
```bash
# Upload BRS
curl -X POST "http://localhost:8000/api/v1/upload/brs" \
  -F "file=@test_example/v1.pdf" \
  -F "version=v1.0"

# Upload CR
curl -X POST "http://localhost:8000/api/v1/upload/cr" \
  -F "file=@test_example/cr1.pdf" \
  -F "approval_status=approved"

# Start consolidation
curl -X POST "http://localhost:8000/api/v1/consolidate" \
  -H "Content-Type: application/json" \
  -d '{
    "brs_id": "BRS-TEST-001",
    "title": "Test BRS",
    "version": "v1.0"
  }'

# Check job status (replace JOB_ID)
curl "http://localhost:8000/api/v1/job/JOB_ID"
```

### Via Python Script
```bash
python example_usage.py
```

## System Architecture

```
┌─────────────────┐
│   Frontend      │  Next.js (Port 3000)
│  (Next.js)      │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│   Backend       │  FastAPI (Port 8000)
│  (FastAPI)      │
└────────┬────────┘
         │
         ├──▶ Ollama (Port 11434) - qwen2.5 model
         │
         └──▶ ChromaDB (Local) - Vector storage
```

## Key Features

✅ **Ollama qwen2.5** - Local LLM, no API keys needed
✅ **Evidence Packs** - Zero-hallucination architecture
✅ **Traceability** - Every requirement traceable to source
✅ **Web Interface** - Easy file upload and monitoring
✅ **REST API** - Programmatic access available

## Next Steps

- Review generated BRS in `data/outputs/`
- Check validation notes for any issues
- Customize parsing rules in `app/services/ingestion.py`
- Add more test documents

## Support

- Backend API docs: http://localhost:8000/docs
- Logs: `logs/brs_consolidator.log`
- Issues: Check console output for errors
