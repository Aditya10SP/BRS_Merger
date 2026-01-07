"""
Semantic chunking service for creating section-aware chunks.
Converts parsed documents into semantic chunks with embeddings.
"""
from typing import List
import uuid

from app.models.schemas import (
    BRSDocument, BRSSection, ChangeRequest, ChangeDelta,
    SemanticChunk, ChunkMetadata, DocumentType
)
from app.core.logging_config import logger
from app.core.config import settings


class SemanticChunker:
    """Creates semantic chunks from structured documents."""
    
    def __init__(self, max_chunk_size: int = None):
        """
        Initialize the chunker.
        
        Args:
            max_chunk_size: Maximum characters per chunk (uses config default if not provided)
        """
        self.max_chunk_size = max_chunk_size or settings.MAX_CHUNK_SIZE
        logger.info(f"Initialized SemanticChunker with max_chunk_size={self.max_chunk_size}")
    
    def chunk_brs_document(self, brs_doc: BRSDocument) -> List[SemanticChunk]:
        """
        Create semantic chunks from a BRS document.
        Each section becomes one or more chunks.
        
        Args:
            brs_doc: Parsed BRS document
        
        Returns:
            List of semantic chunks
        """
        logger.info(f"Chunking BRS document: {brs_doc.metadata.doc_id}")
        chunks = []
        
        for section in brs_doc.sections:
            section_chunks = self._chunk_section(
                section=section,
                doc_id=brs_doc.metadata.doc_id,
                version=brs_doc.metadata.version,
                doc_type=DocumentType.BRS
            )
            chunks.extend(section_chunks)
        
        logger.info(f"Created {len(chunks)} chunks from BRS document")
        return chunks
    
    def chunk_change_request(self, cr: ChangeRequest) -> List[SemanticChunk]:
        """
        Create semantic chunks from a Change Request.
        Each delta becomes a separate chunk.
        
        Args:
            cr: Parsed Change Request
        
        Returns:
            List of semantic chunks
        """
        logger.info(f"Chunking Change Request: {cr.cr_id}")
        chunks = []
        
        for delta in cr.deltas:
            chunk = self._chunk_delta(
                delta=delta,
                cr_id=cr.cr_id,
                priority=cr.priority,
                approval_status=cr.approval_status
            )
            chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} chunks from Change Request")
        return chunks
    
    def _chunk_section(
        self,
        section: BRSSection,
        doc_id: str,
        version: str,
        doc_type: DocumentType,
        parent_path: str = ""
    ) -> List[SemanticChunk]:
        """
        Chunk a BRS section and its subsections.
        
        Args:
            section: BRS section to chunk
            doc_id: Document ID
            version: Document version
            doc_type: Document type
            parent_path: Parent section path for hierarchy
        
        Returns:
            List of chunks for this section and subsections
        """
        chunks = []
        
        # Create chunk for this section
        content = section.content
        
        # If content is too large, split it (while trying to preserve meaning)
        if len(content) > self.max_chunk_size:
            sub_chunks = self._split_large_content(content)
            
            for idx, sub_content in enumerate(sub_chunks):
                # Include doc_id in chunk_id to ensure uniqueness across documents
                chunk_id = f"{doc_id}-{section.metadata.section_id}-CHUNK-{idx+1:03d}"
                chunk = self._create_chunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    version=version,
                    doc_type=doc_type,
                    section_id=section.metadata.section_id,
                    section_title=section.metadata.section_title,
                    section_path=section.metadata.section_path,
                    content=sub_content
                )
                chunks.append(chunk)
        else:
            # Single chunk for this section
            # Include doc_id in chunk_id to ensure uniqueness across documents
            chunk_id = f"{doc_id}-{section.metadata.section_id}-CHUNK-001"
            chunk = self._create_chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                version=version,
                doc_type=doc_type,
                section_id=section.metadata.section_id,
                section_title=section.metadata.section_title,
                section_path=section.metadata.section_path,
                content=content
            )
            chunks.append(chunk)
        
        # Process subsections recursively
        for subsection in section.subsections:
            subsection_chunks = self._chunk_section(
                section=subsection,
                doc_id=doc_id,
                version=version,
                doc_type=doc_type,
                parent_path=section.metadata.section_path
            )
            chunks.extend(subsection_chunks)
        
        return chunks
    
    def _chunk_delta(
        self,
        delta: ChangeDelta,
        cr_id: str,
        priority,
        approval_status
    ) -> SemanticChunk:
        """
        Create a chunk from a change delta.
        
        Args:
            delta: Change delta
            cr_id: Change Request ID
            priority: CR priority
            approval_status: CR approval status
        
        Returns:
            Semantic chunk
        """
        # Combine old and new content for the chunk
        content_parts = []
        
        if delta.old_content:
            content_parts.append(f"[OLD] {delta.old_content}")
        
        if delta.new_content:
            content_parts.append(f"[NEW] {delta.new_content}")
        
        content_parts.append(f"[RATIONALE] {delta.rationale}")
        
        content = "\n".join(content_parts)
        
        chunk_id = f"{delta.delta_id}-CHUNK"
        
        # Extract section_path from section_id (e.g., "SEC-2-1" -> "2.1")
        # Or use section_id if it doesn't match the pattern
        section_path = delta.impacted_section_id
        if section_path.startswith("SEC-"):
            # Convert "SEC-2-1" to "2.1"
            section_path = section_path.replace("SEC-", "").replace("-", ".")
        elif section_path.startswith("BRS-") and "-SEC-" in section_path:
            # Handle format like "BRS-xxx-SEC-2-1" -> "2.1"
            parts = section_path.split("-SEC-")
            if len(parts) > 1:
                section_path = parts[1].replace("-", ".")
        
        chunk = self._create_chunk(
            chunk_id=chunk_id,
            doc_id=cr_id,
            version="N/A",
            doc_type=DocumentType.CHANGE_REQUEST,
            section_id=delta.impacted_section_id,
            section_title=delta.impacted_section_title,
            section_path=section_path,
            content=content,
            approval_status=approval_status,
            priority=priority
        )
        
        return chunk
    
    def _create_chunk(
        self,
        chunk_id: str,
        doc_id: str,
        version: str,
        doc_type: DocumentType,
        section_id: str,
        section_title: str,
        section_path: str,
        content: str,
        approval_status=None,
        priority=None
    ) -> SemanticChunk:
        """Create a semantic chunk with metadata."""
        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            doc_id=doc_id,
            doc_type=doc_type,
            version=version,
            section_id=section_id,
            section_title=section_title,
            section_path=section_path,
            approval_status=approval_status,
            priority=priority
        )
        
        chunk = SemanticChunk(
            metadata=metadata,
            content=content,
            embedding=None  # Will be populated by vector store
        )
        
        return chunk
    
    def _split_large_content(self, content: str) -> List[str]:
        """
        Split large content into smaller chunks while preserving meaning.
        Uses paragraph boundaries when possible.
        
        Args:
            content: Content to split
        
        Returns:
            List of content chunks
        """
        # Split by paragraphs first
        paragraphs = content.split('\n\n')
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            # If single paragraph is too large, split by sentences
            if para_size > self.max_chunk_size:
                # Flush current chunk
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # Split large paragraph
                sentences = para.split('. ')
                for sentence in sentences:
                    if current_size + len(sentence) > self.max_chunk_size:
                        if current_chunk:
                            chunks.append('. '.join(current_chunk) + '.')
                        current_chunk = [sentence]
                        current_size = len(sentence)
                    else:
                        current_chunk.append(sentence)
                        current_size += len(sentence)
                
                # Flush sentence chunk
                if current_chunk:
                    chunks.append('. '.join(current_chunk) + '.')
                    current_chunk = []
                    current_size = 0
            
            # Normal paragraph handling
            elif current_size + para_size > self.max_chunk_size:
                # Flush current chunk
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size
        
        # Flush remaining
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        logger.debug(f"Split content into {len(chunks)} chunks")
        return chunks
