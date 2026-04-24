"""
Orchestrator service that coordinates the entire BRS consolidation pipeline.
"""
from typing import List, Dict, Any, Callable, Optional
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
from app.services.docx_exporter import DOCXExporter
from app.services.template_extractor import TemplateExtractor, DocumentTemplate
from app.services.brs_template import BRSTemplate
from app.services.brs_mapper import BRSMapper
from app.services.missing_section_generator import MissingSectionGenerator
from app.services.completeness_checker import CompletenessChecker
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
        self.docx_exporter = DOCXExporter()
        self.template_extractor = TemplateExtractor()
        self.brs_template = BRSTemplate()
        self.brs_mapper = BRSMapper()
        self.missing_section_generator = MissingSectionGenerator(self.llm_client, self.rag_engine)
        self.completeness_checker = CompletenessChecker(self.vector_store, self.llm_client)
        
        # Store the document template from first uploaded BRS
        self.document_template: Optional[DocumentTemplate] = None
        
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
        
        # Extract template from first BRS document
        if self.document_template is None:
            logger.info("Extracting document template from first BRS")
            if file_path.suffix.lower() == '.docx':
                self.document_template = self.template_extractor.extract_from_docx(file_path)
            elif file_path.suffix.lower() == '.pdf':
                self.document_template = self.template_extractor.extract_from_pdf(file_path)
            else:
                self.document_template = self.template_extractor._get_default_template()
            logger.info(f"Template extracted: numbering format = {self.document_template.section_numbering_format}")
        
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
        Generate the final consolidated BRS using template-based approach.
        
        Args:
            brs_id: Final BRS identifier
            title: BRS title
            version: Final version number
            section_outline: Optional list of sections to generate
        
        Returns:
            Final consolidated BRS
        """
        logger.info(f"Starting template-based BRS consolidation: {brs_id}")
        
        # Step 1: Generate sections from source documents
        if not section_outline:
            section_outline = self._extract_section_outline()
        
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
        
        # Step 2: Map generated sections to BRS template
        logger.info("Mapping sections to BRS template")
        section_mapping = self.brs_mapper.map_sections_to_template(generated_sections)
        
        # Step 3: Identify missing required sections
        missing_sections = self.brs_mapper.identify_missing_sections(section_mapping)
        
        # Step 4: Generate missing sections
        if missing_sections:
            logger.info(f"Generating {len(missing_sections)} missing sections")
            project_context = {
                "title": title,
                "source_documents": list(all_source_docs),
                "applied_changes": list(all_applied_crs)
            }
            
            for i, missing_section in enumerate(missing_sections):
                if progress_callback:
                    progress_callback(
                        total_sections + i,
                        total_sections + len(missing_sections),
                        f"Generating missing section: {missing_section.section_title}"
                    )
                
                generated = self.missing_section_generator.generate_missing_section(
                    missing_section,
                    project_context,
                    generated_sections
                )
                
                # Add to mapping
                if missing_section.section_number not in section_mapping:
                    section_mapping[missing_section.section_number] = []
                section_mapping[missing_section.section_number].append(generated)
                generated_sections.append(generated)
        
        # Step 5: Assemble complete BRS following template order
        logger.info("Assembling complete BRS document")
        ordered_sections = self._order_sections_by_template(section_mapping)
        
        # Assemble final BRS
        final_brs = self.generator.generate_final_brs(
            brs_id=brs_id,
            title=title,
            version=version,
            sections=ordered_sections,
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
    
    def _order_sections_by_template(
        self,
        section_mapping: Dict[str, List[GeneratedSection]]
    ) -> List[GeneratedSection]:
        """
        Order sections according to BRS template structure.
        
        Args:
            section_mapping: Mapping of template sections to generated sections
        
        Returns:
            Ordered list of sections
        """
        ordered_sections = []
        
        for template_section in self.brs_template.get_all_sections_flat():
            section_num = template_section.section_number
            if section_num in section_mapping:
                # If multiple sections mapped to same template section, merge or take first
                sections = section_mapping[section_num]
                if len(sections) == 1:
                    ordered_sections.append(sections[0])
                else:
                    # Merge multiple sections
                    merged = self._merge_sections(sections, template_section)
                    ordered_sections.append(merged)
        
        return ordered_sections
    
    def _merge_sections(
        self,
        sections: List[GeneratedSection],
        template_section
    ) -> GeneratedSection:
        """
        Merge multiple sections into one.
        
        Args:
            sections: List of sections to merge
            template_section: Template section they map to
        
        Returns:
            Merged section
        """
        # Combine content
        combined_content = []
        all_sources = set()
        all_changes = set()
        
        for section in sections:
            combined_content.append(f"### {section.section_title}\n\n{section.content}")
            all_sources.update(section.source_documents)
            all_changes.update(section.applied_changes)
        
        merged_content = "\n\n".join(combined_content)
        
        # Calculate average confidence score (handle None values)
        confidence_scores = [s.confidence_score for s in sections if s.confidence_score is not None]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else None
        
        return GeneratedSection(
            section_id=f"SEC-{template_section.section_number.replace('.', '-')}",
            section_title=template_section.section_title,
            section_path=template_section.section_number,
            content=merged_content,
            source_documents=list(all_sources),
            applied_changes=list(all_changes),
            confidence_score=avg_confidence,
            generation_metadata={"merged_from": len(sections)}
        )

    
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
        # Pass the document template to the exporter
        self.pdf_exporter.export_to_pdf(final_brs, output_path, self.document_template)
        
        logger.info(f"BRS exported successfully to {output_path}")
    
    def export_to_docx(self, final_brs: FinalBRS, output_path: Path) -> None:
        """
        Export final BRS to DOCX file.
        
        Args:
            final_brs: Final BRS document
            output_path: Output file path
        """
        logger.info(f"Exporting BRS to DOCX: {output_path}")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Pass the document template to the exporter
        self.docx_exporter.export_to_docx(final_brs, output_path, self.document_template)
        
        logger.info(f"BRS exported successfully to {output_path}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        return {
            "vector_store": self.vector_store.get_stats(),
            "llm_provider": self.llm_client.provider,
            "llm_model": self.llm_client.model
        }
    
    def clear_vector_store(self) -> None:
        """Clear all data from the vector store."""
        logger.info("Clearing vector store...")
        self.vector_store.clear_all()
        # Also clear the document template for new project
        self.document_template = None
        logger.info("Vector store cleared successfully")
    
    def check_completeness(self, final_brs: FinalBRS) -> Dict[str, Any]:
        """
        Check completeness and coverage of final BRS.
        
        Args:
            final_brs: Final BRS document to check
        
        Returns:
            Completeness report as dictionary
        """
        logger.info(f"Running completeness check for BRS: {final_brs.brs_id}")
        report = self.completeness_checker.check_completeness(final_brs)
        return report.to_dict()
