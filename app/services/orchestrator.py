"""
Orchestrator service that coordinates the entire BRS consolidation pipeline.
"""
from typing import List, Dict, Any, Callable
from pathlib import Path
import json
from datetime import datetime

from app.models.schemas import (
    BRSDocument, ChangeRequest, FinalBRS, GeneratedSection,
    ApprovalStatus, Priority
)
from app.services.ingestion import DocumentParser
from app.services.chunking import SemanticChunker
from app.services.vector_store import VectorStore
from app.services.rag_engine import RAGEngine
from app.services.llm_client import LLMClient
from app.services.generator import BRSGenerator
from app.services.validator import BRSValidator
from app.services.pdf_exporter import PDFExporter
from app.core.logging_config import logger
from app.core.config import settings


class BRSOrchestrator:
    """Orchestrates the complete BRS consolidation pipeline."""
    
    def __init__(self):
        """Initialize all services."""
        logger.info("Initializing BRS Orchestrator")
        
        self.parser = DocumentParser()
        self.chunker = SemanticChunker()
        self.vector_store = VectorStore()
        self.rag_engine = RAGEngine(self.vector_store)
        self.llm_client = LLMClient()
        self.generator = BRSGenerator(self.llm_client)
        self.validator = BRSValidator(self.llm_client)
        self.pdf_exporter = PDFExporter()
        
        logger.info("BRS Orchestrator initialized successfully")
    
    def process_brs_document(
        self,
        file_path: Path,
        doc_id: str = None,
        version: str = None
    ) -> BRSDocument:
        """
        Process a BRS document through the pipeline.
        
        Args:
            file_path: Path to BRS file
            doc_id: Optional document ID
            version: Optional version string
        
        Returns:
            Parsed BRS document
        """
        logger.info(f"Processing BRS document: {file_path}")
        
        # Parse document
        brs_doc = self.parser.parse_brs_document(file_path, doc_id, version)
        
        # Chunk document
        chunks = self.chunker.chunk_brs_document(brs_doc)
        
        # Add to vector store
        self.vector_store.add_brs_chunks(chunks)
        
        logger.info(f"BRS document processed: {brs_doc.metadata.doc_id}")
        return brs_doc
    
    def process_change_request(
        self,
        file_path: Path,
        cr_id: str = None,
        priority: Priority = Priority.MEDIUM,
        approval_status: ApprovalStatus = ApprovalStatus.APPROVED
    ) -> ChangeRequest:
        """
        Process a Change Request through the pipeline.
        
        Args:
            file_path: Path to CR file
            cr_id: Optional CR ID
            priority: Priority level
            approval_status: Approval status
        
        Returns:
            Parsed Change Request
        """
        logger.info(f"Processing Change Request: {file_path}")
        
        # Parse CR
        cr = self.parser.parse_change_request(
            file_path, cr_id, priority, approval_status
        )
        
        # Chunk CR
        chunks = self.chunker.chunk_change_request(cr)
        
        # Add to vector store
        self.vector_store.add_cr_chunks(chunks)
        
        logger.info(f"Change Request processed: {cr.cr_id}")
        return cr
    
    def consolidate_brs(
        self,
        brs_id: str,
        title: str,
        version: str,
        section_outline: List[Dict[str, str]] = None,
        progress_callback: Callable[[int, int, str], None] = None
    ) -> FinalBRS:
        """
        Generate the final consolidated BRS.
        
        Args:
            brs_id: Final BRS identifier
            title: BRS title
            version: Final version number
            section_outline: Optional list of sections to generate
                            Format: [{"section_id": "...", "section_title": "...", "section_path": "..."}]
        
        Returns:
            Final consolidated BRS
        """
        logger.info(f"Starting BRS consolidation: {brs_id}")
        
        # If no outline provided, extract from vector store
        if not section_outline:
            section_outline = self._extract_section_outline()
        
        # Generate each section
        generated_sections = []
        all_source_docs = set()
        all_applied_crs = set()
        
        total_sections = len(section_outline)
        
        for i, section_spec in enumerate(section_outline):
            if progress_callback:
                progress_callback(i, total_sections, f"Generating section {i+1} of {total_sections}")
            section_id = section_spec.get("section_id")
            section_title = section_spec.get("section_title")
            section_path = section_spec.get("section_path")
            
            logger.info(f"Processing section: {section_path} - {section_title}")
            
            # Build Evidence Pack
            evidence_pack = self.rag_engine.build_evidence_pack(
                section_id=section_id,
                section_title=section_title,
                section_path=section_path
            )
            
            # Generate section
            generated_section = self.generator.generate_section(evidence_pack)
            generated_sections.append(generated_section)
            
            # Collect metadata
            all_source_docs.update(evidence_pack.source_documents)
            all_applied_crs.update(generated_section.applied_changes)
        
        # Assemble final BRS
        final_brs = self.generator.generate_final_brs(
            brs_id=brs_id,
            title=title,
            version=version,
            sections=generated_sections,
            source_brs_documents=list(all_source_docs),
            applied_change_requests=list(all_applied_crs)
        )
        
        # Validate
        final_brs = self.validator.validate_final_brs(final_brs)
        
        logger.info(
            f"BRS consolidation complete: {brs_id} "
            f"({'PASSED' if final_brs.validation_passed else 'FAILED'})"
        )
        
        return final_brs
    
    def _extract_section_outline(self) -> List[Dict[str, str]]:
        """
        Extract section outline from ingested BRS documents.
        Merges sections with the same section_path from different documents.
        
        Returns:
            List of section specifications (unique by section_path)
        """
        logger.info("Extracting section outline from vector store")
        
        # Get all BRS chunks
        stats = self.vector_store.get_stats()
        logger.debug(f"Vector store stats: {stats}")
        
        # Query for all BRS sections
        results = self.vector_store.brs_collection.get(limit=1000)
        
        # Group by section_path (not section_id) to merge duplicates
        sections_by_path = {}
        section_titles = {}  # Track title frequency for each path
        
        if results and 'metadatas' in results:
            for metadata in results['metadatas']:
                section_path = metadata.get('section_path')
                section_title = metadata.get('section_title', 'Untitled Section')
                section_id = metadata.get('section_id', '')
                
                if not section_path:
                    continue
                
                # If we haven't seen this path, add it
                if section_path not in sections_by_path:
                    sections_by_path[section_path] = {
                        "section_path": section_path,
                        "section_title": section_title,
                        "section_id": f"SEC-{section_path.replace('.', '-')}"  # Generate unified ID
                    }
                    section_titles[section_path] = {section_title: 1}
                else:
                    # Track title frequency to pick most common one
                    if section_title not in section_titles[section_path]:
                        section_titles[section_path][section_title] = 0
                    section_titles[section_path][section_title] += 1
                    
                    # Update title if this one is more common
                    most_common_title = max(
                        section_titles[section_path].items(),
                        key=lambda x: x[1]
                    )[0]
                    sections_by_path[section_path]["section_title"] = most_common_title
        
        # Convert to list and sort by section path
        sections = list(sections_by_path.values())
        sections.sort(key=lambda x: self._parse_section_path(x['section_path']))
        
        logger.info(f"Extracted {len(sections)} unique sections (merged by section_path)")
        return sections
    
    def _parse_section_path(self, path: str) -> tuple:
        """Parse section path for sorting."""
        try:
            parts = path.split('.')
            return tuple(int(p) for p in parts)
        except:
            return (999,)  # Put unparseable paths at the end
    
    def export_to_json(self, final_brs: FinalBRS, output_path: Path) -> None:
        """
        Export final BRS to JSON file.
        
        Args:
            final_brs: Final BRS document
            output_path: Output file path
        """
        logger.info(f"Exporting BRS to JSON: {output_path}")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_brs.model_dump(), f, indent=2, default=str)
        
        logger.info(f"BRS exported successfully to {output_path}")
    
    def export_to_markdown(self, final_brs: FinalBRS, output_path: Path) -> None:
        """
        Export final BRS to Markdown file.
        
        Args:
            final_brs: Final BRS document
            output_path: Output file path
        """
        logger.info(f"Exporting BRS to Markdown: {output_path}")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        lines = [
            f"# {final_brs.title}",
            f"\n**Version:** {final_brs.version}",
            f"**BRS ID:** {final_brs.brs_id}",
            f"**Generated:** {final_brs.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"\n---\n",
            f"## Document Metadata",
            f"\n**Source BRS Documents:**",
        ]
        
        for doc_id in final_brs.source_brs_documents:
            lines.append(f"- {doc_id}")
        
        lines.append(f"\n**Applied Change Requests:**")
        for cr_id in final_brs.applied_change_requests:
            lines.append(f"- {cr_id}")
        
        lines.append(f"\n**Validation Status:** {'✅ PASSED' if final_brs.validation_passed else '❌ FAILED'}")
        
        if final_brs.validation_notes:
            lines.append(f"\n**Validation Notes:**")
            for note in final_brs.validation_notes:
                lines.append(f"- {note}")
        
        lines.append(f"\n---\n")
        
        # Add sections
        for section in final_brs.sections:
            lines.append(f"\n## {section.section_path} {section.section_title}")
            lines.append(f"\n{section.content}")
            
            # Add traceability footer
            lines.append(f"\n*[Sources: {', '.join(section.source_documents)}]*")
            if section.applied_changes:
                lines.append(f"*[Applied Changes: {', '.join(section.applied_changes)}]*")
            lines.append("")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        logger.info(f"BRS exported successfully to {output_path}")
    
    def export_to_pdf(self, final_brs: FinalBRS, output_path: Path) -> None:
        """
        Export final BRS to PDF file.
        
        Args:
            final_brs: Final BRS document
            output_path: Output file path
        """
        logger.info(f"Exporting BRS to PDF: {output_path}")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.pdf_exporter.export_to_pdf(final_brs, output_path)
        
        logger.info(f"BRS exported successfully to {output_path}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        return {
            "vector_store": self.vector_store.get_stats(),
            "llm_provider": self.llm_client.provider,
            "llm_model": self.llm_client.model
        }
