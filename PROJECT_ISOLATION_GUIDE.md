# Project Isolation Guide

## Problem Solved
Previously, when you uploaded BRS and CR files from different projects (test_example, test_example2, test_example3), the system would mix all the data together in the vector store. This caused the final BRS to contain information from ALL projects instead of just the current one.

## Solution Implemented
Added a **"New Project"** button that clears the vector store before starting work on a different project.

## How to Use

### For Each New Project:

1. **Click "New Project" Button**
   - Located in the stats card at the top
   - Red button with trash icon
   - Confirms before clearing: "⚠️ This will clear all uploaded BRS and CR data. Are you sure you want to start a new project?"
   - Clears all BRS chunks and CR chunks from the vector store

2. **Upload Your Project Files**
   - Upload BRS documents (v1.pdf, v2.pdf, etc.)
   - Upload CR documents (cr1.pdf, cr2.pdf, etc.)
   - All files will be processed and stored in the vector store

3. **Start Consolidation**
   - Click "Start Consolidation"
   - The system will ONLY use data from the files you just uploaded
   - No mixing with previous projects!

4. **Download Results**
   - Click "Download Final BRS" dropdown
   - Choose your preferred format:
     - **PDF** - Formatted document (best for reading/printing)
     - **DOCX** - Editable Word document (best for further editing)
     - **Markdown** - Plain text format (best for version control)
     - **JSON** - Structured data (best for programmatic access)

## Workflow Example

### Project 1 (test_example - Scramble 2.0):
```
1. Click "New Project" (if there's existing data)
2. Upload: v1.pdf, v2.pdf, v3_1.pdf, v3_2.pdf, v4.pdf
3. Upload: cr1.pdf, cr2.pdf, cr3.pdf, cr4.pdf
4. Click "Start Consolidation"
5. Download final BRS
```

### Project 2 (test_example2 - BRS Assistant):
```
1. Click "New Project" ⚠️ IMPORTANT!
2. Upload: BRS_assistant_V1.pdf, BRS_assistant_V2.pdf, BRS_assistant_V3.pdf
3. Upload: BRS_assistant_CR1.pdf, BRS_assistant_CR2.pdf, BRS_assistant_CR3.pdf
4. Click "Start Consolidation"
5. Download final BRS
```

### Project 3 (test_example3 - API BRS):
```
1. Click "New Project" ⚠️ IMPORTANT!
2. Upload: API_BRS_V1.pdf, API_BRS_V2.pdf, API_BRS_V3.pdf
3. Upload: API_CR_1.pdf, API_CR_2.pdf, API_CR_3.pdf
4. Click "Start Consolidation"
5. Download final BRS
```

## Important Notes

⚠️ **ALWAYS click "New Project" before uploading files for a different project!**

✅ The stats card shows:
- **BRS Chunks**: Number of BRS document chunks in vector store
- **CR Chunks**: Number of CR chunks in vector store
- **LLM Model**: Currently configured model (llama3.1:latest)

✅ After clicking "New Project", all counts should reset to 0

✅ The system now exports in 4 formats:
- PDF (formatted)
- DOCX (editable)
- Markdown (plain text)
- JSON (structured data)

## Technical Details

### Backend Changes:
- Added `/api/v1/clear-vector-store` endpoint
- Added `clear_all()` method to VectorStore
- Added `clear_vector_store()` method to Orchestrator
- Added DOCX exporter service
- Fixed config.py to properly read from .env file

### Frontend Changes:
- Added "New Project" button with confirmation dialog
- Added `clearVectorStore()` API function
- Added dropdown menu for download formats
- Added DOCX format support
- Improved UI with better visual feedback

## Configuration

Your current configuration (`.env`):
```properties
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=https://ollama.icicilabs.com/v1
LLM_MODEL=llama3.1:latest
LLM_TIMEOUT=300.0
TOKENIZERS_PARALLELISM=false
```

## Troubleshooting

**Q: I'm still getting mixed results**
A: Make sure you clicked "New Project" before uploading files for a different project

**Q: The "New Project" button is disabled**
A: Wait for any ongoing uploads or consolidation to complete

**Q: I want to switch models**
A: Edit `.env` file and change `LLM_MODEL` to one of:
- `llama3.1:latest` (4.9 GB) - Current, general purpose
- `deepseek-coder-v2:latest` (8.9 GB) - Better for technical docs

**Q: Where are my output files?**
A: All outputs are saved in `data/outputs/` directory

## Next Steps

The project is now working correctly with proper isolation between different projects. Each time you want to work on a different project, simply:

1. Click "New Project"
2. Upload your files
3. Consolidate
4. Download

Enjoy your properly isolated BRS consolidation system! 🎉
