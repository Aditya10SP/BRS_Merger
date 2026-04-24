"""
Core Pydantic models for the BRS Consolidator system.
These models ensure type safety and structured data handling throughout the pipeline.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class DocumentType(str, Enum):
    """Type of document being processed."""
    BRS = "brs"
    CHANGE_REQUEST = "change_request"


class ChangeType(str, Enum):
    """Type of change in a Change Request."""
    ADD = "add"
    MODIFY = "modify"
    DELETE = "delete"


class ApprovalStatus(str, Enum):
    """Approval status for changes."""
    APPROVED = "approved"
    PENDING = "pending"
    REJECTED = "rejected"


class Priority(str, Enum):
    """Priority level for changes."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ============================================================================
# DOCUMENT MODELS
# ============================================================================

class DocumentMetadata(BaseModel):
    """Metadata for any document."""
    doc_id: str = Field(..., description="Unique document identifier")
    doc_type: DocumentType = Field(..., description="Type of document")
    version: str = Field(..., description="Document version (e.g., v1.0, v2.1)")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    source_file: str = Field(..., description="Original filename")
    
    class Config:
        json_schema_extra = {
            "example": {
                "doc_id": "BRS-2024-001",
                "doc_type": "brs",
                "version": "v1.0",
                "source_file": "BRS_Authentication_v1.0.pdf"
            }
        }


class SectionMetadata(BaseModel):
    """Metadata for a BRS section."""
    section_id: str = Field(..., description="Unique section identifier")
    section_title: str = Field(..., description="Section heading/title")
    section_path: str = Field(..., description="Hierarchical path (e.g., '1.2.3')")
    parent_section_id: Optional[str] = Field(None, description="Parent section ID if nested")
    
    class Config:
        json_schema_extra = {
            "example": {
                "section_id": "SEC-001",
                "section_title": "Authentication Requirements",
                "section_path": "3.1",
                "parent_section_id": "SEC-000"
            }
        }


class BRSSection(BaseModel):
    """A single section from a BRS document."""
    metadata: SectionMetadata
    content: str = Field(..., description="Raw text content of the section")
    subsections: List["BRSSection"] = Field(default_factory=list, description="Nested subsections")
    
    class Config:
        json_schema_extra = {
            "example": {
                "metadata": {
                    "section_id": "SEC-001",
                    "section_title": "User Authentication",
                    "section_path": "3.1"
                },
                "content": "The system shall support multi-factor authentication...",
                "subsections": []
            }
        }


class BRSDocument(BaseModel):
    """Complete BRS document structure."""
    metadata: DocumentMetadata
    sections: List[BRSSection] = Field(..., description="Top-level sections")
    
    class Config:
        json_schema_extra = {
            "example": {
                "metadata": {
                    "doc_id": "BRS-2024-001",
                    "doc_type": "brs",
                    "version": "v1.0",
                    "source_file": "BRS_v1.0.pdf"
                },
                "sections": []
            }
        }


# ============================================================================
# CHANGE REQUEST MODELS
# ============================================================================

class ChangeDelta(BaseModel):
    """Represents a single change in a Change Request."""
    delta_id: str = Field(..., description="Unique change delta identifier")
    impacted_section_id: str = Field(..., description="Section ID being modified")
    impacted_section_title: str = Field(..., description="Section title for reference")
    change_type: ChangeType = Field(..., description="Type of change")
    old_content: Optional[str] = Field(None, description="Original content (for MODIFY/DELETE)")
    new_content: Optional[str] = Field(None, description="New content (for ADD/MODIFY)")
    rationale: str = Field(..., description="Reason for the change")
    
    class Config:
        json_schema_extra = {
            "example": {
                "delta_id": "DELTA-001",
                "impacted_section_id": "SEC-001",
                "impacted_section_title": "User Authentication",
                "change_type": "modify",
                "old_content": "Session timeout: 5 minutes",
                "new_content": "Session timeout: 10 minutes",
                "rationale": "User feedback indicated 5 minutes was too short"
            }
        }


class ChangeRequest(BaseModel):
    """Complete Change Request document."""
    cr_id: str = Field(..., description="Unique CR identifier")
    title: str = Field(..., description="CR title/summary")
    priority: Priority = Field(..., description="Priority level")
    approval_status: ApprovalStatus = Field(..., description="Approval status")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    approved_at: Optional[datetime] = Field(None, description="Approval timestamp")
    source_file: str = Field(..., description="Original CR filename")
    deltas: List[ChangeDelta] = Field(..., description="List of changes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "cr_id": "CR-2024-042",
                "title": "Increase session timeout",
                "priority": "medium",
                "approval_status": "approved",
                "source_file": "CR-042.pdf",
                "deltas": []
            }
        }


# ============================================================================
# CHUNKING & EMBEDDING MODELS
# ============================================================================

class ChunkMetadata(BaseModel):
    """Metadata for a semantic chunk."""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    doc_id: str = Field(..., description="Source document ID")
    doc_type: DocumentType = Field(..., description="Source document type")
    version: str = Field(..., description="Document version")
    section_id: str = Field(..., description="Section this chunk belongs to")
    section_title: str = Field(..., description="Section title")
    section_path: str = Field(..., description="Hierarchical section path")
    approval_status: Optional[ApprovalStatus] = Field(None, description="Approval status (for CRs)")
    priority: Optional[Priority] = Field(None, description="Priority (for CRs)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "chunk_id": "CHUNK-001",
                "doc_id": "BRS-2024-001",
                "doc_type": "brs",
                "version": "v1.0",
                "section_id": "SEC-001",
                "section_title": "Authentication",
                "section_path": "3.1"
            }
        }


class SemanticChunk(BaseModel):
    """A semantic chunk with metadata and embeddings."""
    metadata: ChunkMetadata
    content: str = Field(..., description="Chunk text content")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    
    class Config:
        json_schema_extra = {
            "example": {
                "metadata": {
                    "chunk_id": "CHUNK-001",
                    "doc_id": "BRS-2024-001",
                    "doc_type": "brs",
                    "version": "v1.0",
                    "section_id": "SEC-001",
                    "section_title": "Authentication",
                    "section_path": "3.1"
                },
                "content": "The system shall support multi-factor authentication..."
            }
        }


# ============================================================================
# EVIDENCE PACK & GENERATION MODELS
# ============================================================================

class ConflictInfo(BaseModel):
    """Information about conflicting changes."""
    conflicting_cr_ids: List[str] = Field(..., description="IDs of conflicting CRs")
    conflict_description: str = Field(..., description="Description of the conflict")
    resolution_strategy: str = Field(..., description="How the conflict was resolved")
    
    class Config:
        json_schema_extra = {
            "example": {
                "conflicting_cr_ids": ["CR-042", "CR-043"],
                "conflict_description": "Both CRs modify session timeout with different values",
                "resolution_strategy": "Selected CR-043 due to higher priority"
            }
        }


class EvidencePack(BaseModel):
    """
    Evidence pack for a single BRS section.
    This is the ONLY context provided to the LLM for generation.
    """
    section_id: str = Field(..., description="Target section ID")
    section_title: str = Field(..., description="Section title")
    section_path: str = Field(..., description="Hierarchical path")
    
    # Base content from latest BRS version
    base_content: Optional[str] = Field(None, description="Original section content from latest BRS")
    base_source: Optional[str] = Field(None, description="Source BRS document ID and version")
    
    # Approved changes
    approved_changes: List[ChangeDelta] = Field(default_factory=list, description="Approved CR deltas")
    
    # Conflict information
    conflicts: List[ConflictInfo] = Field(default_factory=list, description="Resolved conflicts")
    
    # Traceability
    source_documents: List[str] = Field(default_factory=list, description="All source doc IDs")
    
    class Config:
        json_schema_extra = {
            "example": {
                "section_id": "SEC-001",
                "section_title": "User Authentication",
                "section_path": "3.1",
                "base_content": "The system shall support...",
                "base_source": "BRS-2024-001 v2.0",
                "approved_changes": [],
                "conflicts": [],
                "source_documents": ["BRS-2024-001", "CR-042"]
            }
        }


class GeneratedSection(BaseModel):
    """A generated section in the final BRS."""
    section_id: str = Field(..., description="Section identifier")
    section_title: str = Field(..., description="Section title")
    section_path: str = Field(..., description="Hierarchical path")
    content: str = Field(..., description="Generated content")
    
    # Traceability
    source_documents: List[str] = Field(..., description="Source document IDs")
    applied_changes: List[str] = Field(default_factory=list, description="Applied CR IDs")
    generation_timestamp: datetime = Field(default_factory=datetime.now)
    
    # Generation metadata (optional)
    confidence_score: Optional[float] = Field(None, description="Confidence score for generated content (0-1)")
    generation_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional generation metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "section_id": "SEC-001",
                "section_title": "User Authentication",
                "section_path": "3.1",
                "content": "The system shall support multi-factor authentication...",
                "source_documents": ["BRS-2024-001", "CR-042"],
                "applied_changes": ["CR-042"]
            }
        }


class FinalBRS(BaseModel):
    """The final consolidated BRS document."""
    brs_id: str = Field(..., description="Final BRS identifier")
    title: str = Field(..., description="BRS title")
    version: str = Field(..., description="Final version number")
    generated_at: datetime = Field(default_factory=datetime.now)
    
    sections: List[GeneratedSection] = Field(..., description="All generated sections")
    
    # Metadata
    source_brs_documents: List[str] = Field(..., description="All source BRS IDs")
    applied_change_requests: List[str] = Field(..., description="All applied CR IDs")
    
    # Validation
    validation_passed: bool = Field(False, description="Whether validation passed")
    validation_notes: List[str] = Field(default_factory=list, description="Validation findings")
    
    class Config:
        json_schema_extra = {
            "example": {
                "brs_id": "BRS-FINAL-2024-001",
                "title": "Authentication System BRS",
                "version": "v3.0",
                "sections": [],
                "source_brs_documents": ["BRS-2024-001"],
                "applied_change_requests": ["CR-042", "CR-043"],
                "validation_passed": True,
                "validation_notes": []
            }
        }
