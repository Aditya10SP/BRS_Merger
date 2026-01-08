# Fixes Applied - January 8, 2026

## Issue 1: Memory Error with Remote Ollama Model

### Problem
```
Error code: 500 - {'error': {'message': 'model requires more system memory (15.7 GiB) than is available (14.1 GiB)'}}
```

The `maryasov/qwen2.5-coder-cline:32b` model (18.5 GB) was too large for the available memory on the remote Ollama server.

### Solution
Switched to `deepseek-coder-v2:latest` (8.3 GB) which:
- Fits within available memory (14.1 GiB)
- Is optimized for code and technical documentation
- Provides excellent performance for BRS consolidation tasks

### Changes Made
- Updated `.env`: `LLM_MODEL=deepseek-coder-v2:latest`
- Updated `app/core/config.py`: Default model changed to `deepseek-coder-v2:latest`

## Issue 2: PDF Export Font Error

### Problem
```
paragraph text '<para>Consolidated Business Requirements Specification</para>' caused exception error with style name=BRSTitle Can't map determine family/bold/italic for tahoma-bold
```

The PDF exporter was trying to use Tahoma font which wasn't properly registered with ReportLab.

### Solution
Switched to standard PDF fonts (Helvetica family) which are always available in PDF readers:
- `Helvetica-Bold` for titles and headings
- `Helvetica` for body text
- `Helvetica-Oblique` for italic text

### Changes Made
- Updated `app/services/pdf_exporter.py`: 
  - Removed Tahoma font references and use only standard PDF fonts
  - Fixed `_filename` attribute error by storing `output_path` in the exporter instance

## Available Models on Remote Ollama Server

| Model | Size | Status |
|-------|------|--------|
| nomic-embed-text:latest | 0.3 GB | ✅ Available |
| llama3.1:latest | 4.6 GB | ✅ Available |
| deepseek-coder-v2:latest | 8.3 GB | ✅ **Currently Used** |
| ryanshillington/Qwen3-Embedding-8B:latest | 14.1 GB | ⚠️ Too large |
| maryasov/qwen2.5-coder-cline:32b | 18.5 GB | ❌ Too large |

## Current Configuration

```properties
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=https://ollama.icicilabs.com/v1
LLM_MODEL=deepseek-coder-v2:latest
LLM_TIMEOUT=300.0
```

## Testing Recommendations

1. **Test BRS Consolidation**: Run a full consolidation to verify the new model works correctly
2. **Test PDF Export**: Verify PDF generation completes without font errors
3. **Monitor Memory Usage**: Check that the remote server has sufficient memory during processing
4. **Validate Output Quality**: Compare generated BRS quality with previous runs

## Rollback Instructions

If needed, you can switch to `llama3.1:latest` (4.6 GB) which is smaller and more stable:

```bash
# Update .env
LLM_MODEL=llama3.1:latest

# Restart backend
kill $(ps aux | grep uvicorn | grep -v grep | awk '{print $2}')
source venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
```

## Git Commit

Changes committed and pushed to GitHub:
- Commit: `c530127`
- Message: "Fix memory issue and PDF export: Switch to deepseek-coder-v2 model and use standard PDF fonts"
- Repository: `https://github.icicilabs.com/ICICI-Labs/BRS_Merger.git`
