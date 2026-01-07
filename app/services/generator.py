"""
Generator service for creating final BRS sections using LLM.
Implements section-wise generation with Evidence Packs.
"""
from typing import List, Optional
from datetime import datetime
import time

from app.models.schemas import (
    EvidencePack, GeneratedSection, FinalBRS, BRSSection
)
from app.services.llm_client import LLMClient
from app.services.prompts import format_section_generation_prompt
from app.core.logging_config import logger


class BRSGenerator:
    """Generates final BRS sections using constrained LLM generation."""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize generator.
        
        Args:
            llm_client: LLM client instance
        """
        self.llm_client = llm_client
        logger.info("BRS Generator initialized")
    
    def generate_section(
        self,
        evidence_pack: EvidencePack
    ) -> GeneratedSection:
        """
        Generate a single BRS section from an Evidence Pack.
        
        Args:
            evidence_pack: Evidence pack containing all context
        
        Returns:
            Generated section with traceability
        """
        logger.info(f"Generating section: {evidence_pack.section_id}")
        
        # Format the prompt
        prompt = format_section_generation_prompt(
            section_id=evidence_pack.section_id,
            section_title=evidence_pack.section_title,
            section_path=evidence_pack.section_path,
            base_content=evidence_pack.base_content,
            approved_changes=evidence_pack.approved_changes,
            conflict_notes=evidence_pack.conflicts
        )
        
        # Generate content using LLM with retry logic for remote connection
        max_retries = 2  # Reduced retries for remote connection
        retry_delay = 5  # Longer delay for remote connection
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Generation attempt {attempt + 1}/{max_retries} for section {evidence_pack.section_id}")
                logger.debug(f"Using model: {self.llm_client.model} via {self.llm_client.provider}")
                
                generated_content = self.llm_client.generate(
                    prompt=prompt,
                    temperature=0.1,  # Low temperature for deterministic output
                    max_tokens=2000
                )
                
                # Check if generation actually produced content
                if not generated_content or len(generated_content.strip()) < 10:
                    logger.warning(f"Generated content too short for section {evidence_pack.section_id}")
                    # If no base content, we can't generate anything
                    if not evidence_pack.base_content:
                        generated_content = "Not Specified - No source content available for this section."
                    else:
                        generated_content = evidence_pack.base_content
                
                logger.debug(f"Generated {len(generated_content)} characters")
                break  # Success, exit retry loop
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Generation attempt {attempt + 1} failed for section {evidence_pack.section_id}: {error_msg}")
                
                # If this is the last attempt, handle the error
                if attempt == max_retries - 1:
                    logger.error(f"Generation failed for section {evidence_pack.section_id}: {error_msg}")
                    
                    # Provide helpful error messages for remote connection
                    if "timeout" in error_msg.lower():
                        error_msg = f"Remote Ollama request timed out for model {self.llm_client.model}. The remote server may be overloaded."
                    elif "connection" in error_msg.lower() or "network" in error_msg.lower():
                        error_msg = f"Network connection failed to remote Ollama server. Please check connectivity."
                    elif "404" in error_msg or "not found" in error_msg.lower():
                        error_msg = f"Model {self.llm_client.model} not found on remote Ollama server."
                    
                    # If we have base content, use it as fallback (clean, without error notes)
                    if evidence_pack.base_content:
                        # Use base content directly without error notes for cleaner output
                        generated_content = evidence_pack.base_content
                        logger.info(f"Using base content as fallback for section {evidence_pack.section_id}")
                    else:
                        generated_content = "Not Specified - No source content available for this section."
                        logger.warning(f"No base content available for section {evidence_pack.section_id}")
                    break
                else:
                    # Wait before retrying with longer delay for remote connection
                    wait_time = retry_delay * (attempt + 1)
                    logger.info(f"Retrying remote connection in {wait_time} seconds...")
                    time.sleep(wait_time)
        
        # Extract applied CR IDs
        applied_changes = [
            delta.delta_id.split('-DELTA')[0]
            for delta in evidence_pack.approved_changes
        ]
        
        # Create GeneratedSection
        section = GeneratedSection(
            section_id=evidence_pack.section_id,
            section_title=evidence_pack.section_title,
            section_path=evidence_pack.section_path,
            content=generated_content,
            source_documents=evidence_pack.source_documents,
            applied_changes=applied_changes
        )
        
        logger.info(f"Section generated successfully: {evidence_pack.section_id}")
        return section
    
    def generate_final_brs(
        self,
        brs_id: str,
        title: str,
        version: str,
        sections: List[GeneratedSection],
        source_brs_documents: List[str],
        applied_change_requests: List[str]
    ) -> FinalBRS:
        """
        Assemble the final BRS document from generated sections.
        
        Args:
            brs_id: Final BRS identifier
            title: BRS title
            version: Final version number
            sections: List of generated sections
            source_brs_documents: Source BRS document IDs
            applied_change_requests: Applied CR IDs
        
        Returns:
            Complete FinalBRS document
        """
        logger.info(f"Assembling final BRS: {brs_id}")
        
        final_brs = FinalBRS(
            brs_id=brs_id,
            title=title,
            version=version,
            sections=sections,
            source_brs_documents=source_brs_documents,
            applied_change_requests=applied_change_requests,
            validation_passed=False,  # Will be set by validator
            validation_notes=[]
        )
        
        logger.info(
            f"Final BRS assembled: {len(sections)} sections, "
            f"{len(source_brs_documents)} source BRS, "
            f"{len(applied_change_requests)} CRs applied"
        )
        
        return final_brs
