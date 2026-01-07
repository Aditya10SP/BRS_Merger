# BRS Merger2 - Detailed Project Explanation

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Core Problem Statement](#core-problem-statement)
3. [System Architecture](#system-architecture)
4. [Component Breakdown](#component-breakdown)
5. [Data Flow & Pipeline](#data-flow--pipeline)
6. [Key Technologies](#key-technologies)
7. [Workflow Examples](#workflow-examples)
8. [Design Patterns & Principles](#design-patterns--principles)

---

## Project Overview

**BRS Merger2** (GenAI BRS Consolidator) is an enterprise-grade system that automatically consolidates multiple Business Requirement Specification (BRS) documents and Change Requests (CR) into a single, unified Final BRS document using **controlled Retrieval-Augmented Generation (RAG)**.

### What It Does

The system solves a critical problem in enterprise software development: when multiple versions of BRS documents exist, along with numerous approved Change Requests, manually consolidating them is:
- **Time-consuming**: Hours or days of manual work
- **Error-prone**: Easy to miss changes or create inconsistencies
- **Untraceable**: Hard to track which source document contributed what

This system automates the entire process while ensuring:
- ✅ **100% Traceability**: Every requirement links back to source documents
- ✅ **Zero Hallucination**: LLM is strictly constrained to evidence packs
- ✅ **Conflict Resolution**: Automatically detects and resolves conflicting changes
- ✅ **Quality Validation**: Multi-layer validation ensures output quality

---

## Core Problem Statement

### The Challenge

In enterprise environments, BRS documents evolve over time:
1. **Multiple Versions**: BRS v1.0, v2.0, v3.0 exist simultaneously
2. **Change Requests**: Dozens of approved CRs modify different sections
3. **Conflicts**: Multiple CRs may modify the same section differently
4. **Traceability Requirements**: Regulatory/compliance needs require tracking every change

### The Solution

The system uses a **controlled RAG approach**:
- **Evidence Packs**: Each section generation uses ONLY a curated set of evidence
- **No Open Retrieval**: LLM cannot access information outside the evidence pack
- **Structured Output**: Generated content maintains traceability metadata
- **Validation Layer**: Post-generation validation ensures quality

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI REST API                          │
│  (Upload, Consolidate, Status, Download Endpoints)           │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  BRS Orchestrator                            │
│  (Coordinates entire pipeline, manages workflow)             │
└───────┬───────────────┬───────────────┬─────────────────────┘
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Ingestion   │ │   Chunking   │ │ Vector Store │
│   Service    │ │   Service    │ │  (ChromaDB)  │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┴────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAG Engine                               │
│  (Builds Evidence Packs, Conflict Resolution)              │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              LLM Client (Ollama/OpenAI/Gemini)              │
│  (Constrained Generation, Validation)                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Generator + Validator                          │
│  (Section Generation, Quality Assurance)                    │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Final BRS (JSON/Markdown/PDF)                  │
└─────────────────────────────────────────────────────────────┘
```

### Component Layers

1. **API Layer** (`app/api/endpoints.py`)
   - RESTful endpoints for upload, consolidation, status tracking
   - File handling and background job management

2. **Orchestration Layer** (`app/services/orchestrator.py`)
   - Coordinates all services
   - Manages workflow state
   - Handles export operations

3. **Processing Layer**
   - **Ingestion** (`app/services/ingestion.py`): Parses PDF/DOCX → Structured JSON
   - **Chunking** (`app/services/chunking.py`): Creates semantic chunks
   - **Vector Store** (`app/services/vector_store.py`): Manages embeddings & retrieval

4. **RAG Layer** (`app/services/rag_engine.py`)
   - Builds Evidence Packs
   - Conflict detection & resolution
   - Section-wise retrieval

5. **Generation Layer**
   - **Generator** (`app/services/generator.py`): LLM-based section generation
   - **Validator** (`app/services/validator.py`): Quality validation

6. **Data Models** (`app/models/schemas.py`)
   - Pydantic models for type safety
   - Structured data validation

---

## Component Breakdown

### 1. Document Ingestion Service

**Purpose**: Parse uploaded PDF/DOCX files into structured JSON

**Key Functions**:
- `parse_brs_document()`: Extracts sections, metadata from BRS files
- `parse_change_request()`: Extracts deltas, approval status from CR files

**Output**: 
- `BRSDocument`: Contains metadata + list of `BRSSection` objects
- `ChangeRequest`: Contains CR metadata + list of `ChangeDelta` objects

**Example**:
```python
BRSDocument {
    metadata: {
        doc_id: "BRS-2024-001",
        version: "v1.0",
        source_file: "brs_v1.pdf"
    },
    sections: [
        {
            metadata: {section_id: "SEC-001", section_title: "Introduction"},
            content: "This document specifies...",
            subsections: []
        }
    ]
}
```

### 2. Semantic Chunking Service

**Purpose**: Convert structured documents into searchable chunks with embeddings

**Strategy**:
- **Section-Aware**: Each section becomes one or more chunks
- **Hierarchical**: Preserves parent-child relationships
- **Metadata-Rich**: Each chunk includes section_id, version, doc_type

**Chunking Rules**:
- If section content > `MAX_CHUNK_SIZE` (1000 chars), split intelligently
- Preserve paragraph boundaries when possible
- Each chunk gets unique `chunk_id` (e.g., "SEC-001-CHUNK-001")

**Output**: `SemanticChunk` objects with:
- Content text
- Metadata (section_id, doc_id, version, etc.)
- Embedding vector (generated later)

### 3. Vector Store Service

**Purpose**: Manage embeddings and enable semantic search

**Technology**: ChromaDB (persistent vector database)

**Collections**:
- `brs_chunks`: Stores BRS document chunks
- `cr_deltas`: Stores Change Request deltas

**Key Operations**:
- `add_brs_chunks()`: Add BRS chunks with embeddings
- `add_cr_chunks()`: Add CR chunks with embeddings
- `query_brs_by_section()`: Retrieve BRS content by section_id or semantic search
- `query_cr_by_section()`: Retrieve approved CRs affecting a section
- `hybrid_search()`: Combine semantic similarity + metadata filtering

**Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional vectors)

### 4. RAG Engine

**Purpose**: Build Evidence Packs for section generation

**Evidence Pack Structure**:
```python
EvidencePack {
    section_id: "SEC-001",
    section_title: "User Authentication",
    section_path: "3.1",
    base_content: "Original BRS text...",  # From latest BRS version
    base_source: "BRS-2024-001 v2.0",
    approved_changes: [ChangeDelta1, ChangeDelta2],  # Only APPROVED CRs
    conflicts: [ConflictInfo],  # Detected conflicts with resolution
    source_documents: ["BRS-2024-001", "CR-042", "CR-043"]
}
```

**Workflow**:
1. **Retrieve Base Content**: Get latest BRS version for the section
2. **Retrieve Approved Changes**: Get all APPROVED CRs affecting this section
3. **Detect Conflicts**: Identify if multiple CRs conflict
4. **Resolve Conflicts**: Apply priority-based resolution
5. **Build Evidence Pack**: Combine all evidence into single pack

**Conflict Resolution Strategy**:
- Priority: CRITICAL > HIGH > MEDIUM > LOW
- Approval Status: APPROVED > PENDING > REJECTED
- Timestamp: Most recent wins
- If still tied → Flag for human review

### 5. LLM Client

**Purpose**: Unified interface for multiple LLM providers

**Supported Providers**:
- **Ollama** (default): Local, no API key needed
- **OpenAI**: GPT-3.5/4 models
- **Google Gemini**: Gemini Pro models

**Key Features**:
- Temperature control (default: 0.1 for deterministic output)
- JSON mode support
- Error handling and retries

**Configuration** (from `config.py`):
```python
LLM_PROVIDER = "ollama"  # or "openai", "gemini"
LLM_MODEL = "qwen2.5:1.5b"
LLM_TEMPERATURE = 0.1
LLM_MAX_TOKENS = 2000
```

### 6. Generator Service

**Purpose**: Generate final BRS sections using LLM

**Process**:
1. Receive `EvidencePack` for a section
2. Format prompt using `format_section_generation_prompt()`
3. Call LLM with strict constraints
4. Parse generated content
5. Create `GeneratedSection` with traceability

**Prompt Strategy** (from `prompts.py`):
- **Strict Constraints**: "You MUST ONLY use information from the Evidence Pack"
- **No Hallucination**: "You MUST NOT add new requirements"
- **Missing Info**: "If information is missing, write 'Not Specified'"

**Output**: `GeneratedSection` with:
- Generated content
- Source document IDs
- Applied CR IDs
- Generation timestamp

### 7. Validator Service

**Purpose**: Quality assurance for generated sections

**Validation Types**:

1. **LLM-Based Validation**:
   - Checks traceability
   - Detects hallucinations
   - Validates completeness
   - Scores overall quality (0-100)

2. **Rule-Based Validation**:
   - Empty section detection
   - Missing traceability
   - Duplicate section IDs
   - Placeholder text detection

**Output**: Updated `FinalBRS` with:
- `validation_passed`: Boolean
- `validation_notes`: List of issues/recommendations

### 8. Orchestrator Service

**Purpose**: Coordinate entire pipeline

**Main Workflow** (`consolidate_brs()`):

```python
1. Extract section outline (or use provided)
2. For each section:
   a. Build Evidence Pack (RAG Engine)
   b. Generate section (Generator)
   c. Collect metadata
3. Assemble Final BRS
4. Validate Final BRS
5. Export to JSON/Markdown/PDF
```

**Export Formats**:
- **JSON**: Full structured data with all metadata
- **Markdown**: Human-readable format with traceability footers
- **PDF**: Professional document (via PDF exporter)

---

## Data Flow & Pipeline

### Complete Pipeline Flow

```
┌──────────────────────────────────────────────────────────────┐
│ STEP 1: Document Upload                                      │
│                                                              │
│ User uploads:                                                │
│ - BRS v1.0.pdf, BRS v2.0.pdf, BRS v3.0.pdf                 │
│ - CR-042.pdf, CR-043.pdf, CR-044.pdf                        │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│ STEP 2: Document Parsing                                     │
│                                                              │
│ PDF/DOCX → Structured JSON:                                  │
│ - BRSDocument objects with sections                         │
│ - ChangeRequest objects with deltas                          │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│ STEP 3: Semantic Chunking                                    │
│                                                              │
│ Documents → Semantic Chunks:                                 │
│ - Each section → 1+ chunks                                  │
│ - Metadata preserved (section_id, version, etc.)             │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│ STEP 4: Embedding & Storage                                  │
│                                                              │
│ Chunks → Vector Store (ChromaDB):                           │
│ - Generate embeddings (384-dim vectors)                      │
│ - Store in brs_chunks or cr_deltas collection                │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│ STEP 5: Consolidation Request                               │
│                                                              │
│ User requests: "Consolidate into BRS-FINAL-2024 v3.0"        │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│ STEP 6: Section-by-Section Generation                        │
│                                                              │
│ For each section:                                            │
│   6a. RAG Engine builds Evidence Pack:                       │
│       - Retrieves latest BRS content                         │
│       - Retrieves approved CRs                               │
│       - Detects/resolves conflicts                           │
│                                                              │
│   6b. Generator creates section:                             │
│       - Formats prompt with Evidence Pack                     │
│       - Calls LLM (constrained)                              │
│       - Parses generated content                             │
│                                                              │
│   6c. Collect traceability metadata                          │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│ STEP 7: Assembly & Validation                                │
│                                                              │
│ - Assemble all GeneratedSection objects                      │
│ - Create FinalBRS document                                   │
│ - Run validation (LLM + rules)                               │
│ - Generate validation report                                 │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│ STEP 8: Export                                               │
│                                                              │
│ FinalBRS → JSON + Markdown + PDF                            │
│ - JSON: Full structured data                                 │
│ - Markdown: Human-readable with traceability                 │
│ - PDF: Professional document                                 │
└──────────────────────────────────────────────────────────────┘
```

### Evidence Pack Example

For section "SEC-002: User Authentication":

```python
EvidencePack {
    section_id: "SEC-002",
    section_title: "User Authentication",
    section_path: "2",
    
    # Base content from latest BRS
    base_content: """
    The system shall support the following authentication methods:
    1. Username and password authentication
    2. Multi-factor authentication (MFA) using SMS or authenticator apps
    3. Single Sign-On (SSO) integration
    
    Session Management:
    - Session timeout shall be 30 minutes of inactivity
    - Maximum session duration shall be 8 hours
    """,
    base_source: "BRS-2024-001 v2.0",
    
    # Approved changes from CRs
    approved_changes: [
        ChangeDelta {
            delta_id: "CR-2024-042-DELTA-001",
            change_type: "modify",
            old_content: "Session timeout shall be 30 minutes",
            new_content: "Session timeout shall be 60 minutes",
            rationale: "User feedback indicated 30 minutes was too short"
        },
        ChangeDelta {
            delta_id: "CR-2024-042-DELTA-003",
            change_type: "add",
            old_content: null,
            new_content: "Biometric Authentication:\n- Fingerprint\n- Facial recognition",
            rationale: "Add biometric support for mobile devices"
        }
    ],
    
    conflicts: [],  # No conflicts in this example
    
    source_documents: ["BRS-2024-001", "CR-2024-042"]
}
```

**LLM Prompt** (simplified):
```
You are a BRS Writer. Generate section SEC-002: User Authentication.

CRITICAL: You MUST ONLY use information from the Evidence Pack below.

BASE CONTENT:
[base_content shown above]

APPROVED CHANGES:
1. Change session timeout from 30 to 60 minutes
2. Add biometric authentication support

Generate the final section content...
```

**Generated Output**:
```
The system shall support the following authentication methods:
1. Username and password authentication
2. Multi-factor authentication (MFA) using SMS or authenticator apps
3. Single Sign-On (SSO) integration
4. Biometric Authentication:
   - The system shall support fingerprint authentication on supported devices
   - The system shall support facial recognition on supported devices

Session Management:
- Session timeout shall be 60 minutes of inactivity
- Users shall be able to extend their session before timeout
- Maximum session duration shall be 8 hours
```

---

## Key Technologies

### Backend Stack

1. **FastAPI**: Modern Python web framework
   - Async support
   - Automatic API documentation
   - Type validation with Pydantic

2. **ChromaDB**: Vector database
   - Persistent storage
   - Metadata filtering
   - Semantic search

3. **Sentence Transformers**: Embedding generation
   - Model: `all-MiniLM-L6-v2`
   - 384-dimensional vectors
   - Fast inference

4. **Ollama/OpenAI/Gemini**: LLM providers
   - Ollama: Local, no API key
   - OpenAI: GPT models
   - Gemini: Google's models

5. **Pydantic**: Data validation
   - Type safety
   - Schema validation
   - JSON serialization

### Frontend Stack (Optional)

- Next.js (React framework)
- TypeScript
- Tailwind CSS

---

## Workflow Examples

### Example 1: Simple Consolidation

**Input**:
- BRS v1.0: 4 sections
- BRS v2.0: 5 sections (adds new section)
- CR-042: Modifies section SEC-002

**Process**:
1. Upload all documents
2. System chunks and stores in vector DB
3. User requests consolidation
4. For each section:
   - If section exists in v2.0 → use v2.0 as base
   - If section only in v1.0 → use v1.0 as base
   - Apply CR-042 changes to SEC-002
5. Generate final BRS with 5 sections

**Output**: Final BRS v3.0 with all sections, SEC-002 updated

### Example 2: Conflict Resolution

**Input**:
- BRS v1.0: Section SEC-003 (Password Requirements)
- CR-042: Changes password expiration from 90 to 180 days
- CR-043: Changes password expiration from 90 to 120 days
- Both CRs are APPROVED, HIGH priority

**Process**:
1. RAG Engine detects conflict in SEC-003
2. Conflict resolution:
   - Both HIGH priority → Check timestamp
   - CR-043 is more recent → Selected
3. Evidence Pack includes only CR-043
4. Generated section uses 120 days expiration
5. Validation notes: "Conflict resolved: CR-043 selected over CR-042"

**Output**: Final BRS with 120-day expiration, conflict noted

### Example 3: Multi-Version Merge

**Input**:
- BRS v1.0: Sections 1-4
- BRS v2.0: Sections 1-5 (adds section 5, modifies section 2)
- BRS v3.0: Sections 1-6 (adds section 6, modifies section 3)
- Multiple CRs affecting various sections

**Process**:
1. System extracts section outline: 6 unique sections
2. For each section:
   - Use latest version as base (v3.0 > v2.0 > v1.0)
   - Apply all approved CRs
3. Generate all 6 sections
4. Validate completeness

**Output**: Final BRS with all 6 sections, latest content, all CRs applied

---

## Design Patterns & Principles

### 1. Evidence Pack Pattern

**Principle**: LLM generation is constrained to a curated evidence set

**Benefits**:
- Prevents hallucination
- Ensures traceability
- Enables auditability

**Implementation**:
- RAG Engine builds Evidence Pack per section
- Generator uses ONLY Evidence Pack in prompt
- Validator verifies no information outside Evidence Pack

### 2. Section-Wise Processing

**Principle**: Process one section at a time, not entire document

**Benefits**:
- Better control over context size
- Easier conflict resolution
- Parallelizable (future enhancement)

**Implementation**:
- Orchestrator iterates through section outline
- Each section gets its own Evidence Pack
- Sections assembled into Final BRS

### 3. Hybrid Retrieval

**Principle**: Combine semantic search + metadata filtering

**Benefits**:
- Semantic: Finds similar content even if section_id differs
- Metadata: Ensures exact matches when section_id known
- Flexible: Works with or without exact section IDs

**Implementation**:
- Try exact section_id match first
- Fall back to semantic search by section_title
- Filter by version, approval_status, etc.

### 4. Conflict Resolution Strategy

**Principle**: Deterministic conflict resolution with human review fallback

**Priority Order**:
1. Priority (CRITICAL > HIGH > MEDIUM > LOW)
2. Approval Status (APPROVED > PENDING > REJECTED)
3. Timestamp (Most recent)
4. Human Review (If still tied)

**Implementation**:
- RAG Engine detects conflicts
- Applies resolution strategy
- Flags for review if needed
- Includes conflict notes in Evidence Pack

### 5. Traceability by Design

**Principle**: Every generated requirement must be traceable

**Implementation**:
- `GeneratedSection` includes:
  - `source_documents`: List of source BRS IDs
  - `applied_changes`: List of applied CR IDs
- Final BRS includes:
  - `source_brs_documents`: All source BRS IDs
  - `applied_change_requests`: All applied CR IDs
- Markdown export includes traceability footers

### 6. Validation Layer

**Principle**: Multi-layer validation ensures quality

**Layers**:
1. **LLM Validation**: Semantic quality, hallucination detection
2. **Rule-Based Validation**: Structural checks, completeness
3. **Traceability Validation**: Ensures all sources recorded

**Output**: Validation report with issues and recommendations

---

## Configuration & Customization

### Key Configuration Options

**LLM Settings** (`app/core/config.py`):
```python
LLM_PROVIDER = "ollama"  # or "openai", "gemini"
LLM_MODEL = "qwen2.5:1.5b"
LLM_TEMPERATURE = 0.1  # Low for deterministic output
LLM_MAX_TOKENS = 2000
```

**Retrieval Settings**:
```python
TOP_K_RETRIEVAL = 5  # Number of chunks to retrieve
SIMILARITY_THRESHOLD = 0.7  # Minimum similarity score
```

**Chunking Settings**:
```python
MAX_CHUNK_SIZE = 1000  # Characters per chunk
CHUNK_OVERLAP = 100  # Overlap between chunks
```

**Vector Store**:
```python
VECTOR_DB_TYPE = "chroma"
CHROMA_PERSIST_DIR = "./data/chroma_db"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
```

---

## API Endpoints

### 1. Upload BRS Document
```
POST /api/v1/upload/brs
- file: PDF/DOCX file
- doc_id: Optional document ID
- version: Optional version string
```

### 2. Upload Change Request
```
POST /api/v1/upload/cr
- file: PDF/DOCX file
- cr_id: Optional CR ID
- priority: HIGH/MEDIUM/LOW
- approval_status: APPROVED/PENDING/REJECTED
```

### 3. Consolidate BRS
```
POST /api/v1/consolidate
- brs_id: Final BRS identifier
- title: BRS title
- version: Final version
- section_outline: Optional custom outline
```

### 4. Check Job Status
```
GET /api/v1/job/{job_id}
- Returns: status, progress, result
```

### 5. Download Output
```
GET /api/v1/download/{filename}
- Returns: JSON/Markdown/PDF file
```

### 6. System Stats
```
GET /api/v1/stats
- Returns: Vector store stats, LLM info
```

---

## Data Models

### Core Models

1. **BRSDocument**: Parsed BRS with sections
2. **ChangeRequest**: CR with deltas
3. **SemanticChunk**: Chunked content with metadata
4. **EvidencePack**: Curated evidence for generation
5. **GeneratedSection**: Generated section with traceability
6. **FinalBRS**: Complete consolidated document

### Model Relationships

```
BRSDocument
  └─> BRSSection (multiple)
        └─> SemanticChunk (1+ per section)

ChangeRequest
  └─> ChangeDelta (multiple)
        └─> SemanticChunk (1 per delta)

EvidencePack
  ├─> Base Content (from BRSDocument)
  └─> Approved Changes (from ChangeDelta)

GeneratedSection
  ├─> Source Documents (from BRSDocument)
  └─> Applied Changes (from ChangeRequest)

FinalBRS
  └─> GeneratedSection (multiple)
```

---

## Security & Best Practices

### Security Considerations

1. **API Keys**: Stored in `.env`, never committed
2. **File Upload**: Validated file types and sizes
3. **Vector Store**: Local persistence, secure directory
4. **Production**: Should add authentication/authorization

### Best Practices

1. **Version Control**: All documents have version tracking
2. **Audit Trail**: Complete traceability in output
3. **Error Handling**: Graceful failures with logging
4. **Validation**: Multi-layer quality checks
5. **Logging**: Comprehensive logging for debugging

---

## Future Enhancements

Potential improvements:
1. **Parallel Processing**: Generate sections in parallel
2. **Advanced Conflict Resolution**: LLM-based conflict analysis
3. **Deduplication**: Detect and merge duplicate requirements
4. **Version Comparison**: Visual diff between versions
5. **Collaborative Review**: Multi-user review workflow
6. **Template Support**: Custom BRS templates
7. **Multi-Language**: Support for non-English documents

---

## Summary

**BRS Merger2** is a sophisticated RAG-based system that:

1. **Ingests** multiple BRS versions and Change Requests
2. **Chunks** documents semantically with rich metadata
3. **Stores** in vector database for semantic search
4. **Retrieves** relevant content per section
5. **Resolves** conflicts automatically
6. **Generates** sections using constrained LLM
7. **Validates** output for quality and traceability
8. **Exports** to multiple formats (JSON/Markdown/PDF)

The system ensures **zero hallucination** through strict Evidence Pack constraints, maintains **100% traceability** through metadata tracking, and provides **enterprise-grade quality** through multi-layer validation.

---

**Built with**: FastAPI, ChromaDB, Sentence Transformers, Ollama/OpenAI/Gemini, Pydantic

