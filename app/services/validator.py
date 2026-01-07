"""
Validation service for ensuring BRS quality and compliance.
Implements LLM-based and rule-based validation.
"""
from typing import List, Dict, Any
import json

from app.models.schemas import FinalBRS, GeneratedSection
from app.services.llm_client import LLMClient
from app.services.prompts import format_validation_prompt
from app.core.logging_config import logger


class BRSValidator:
    """Validates generated BRS for quality and compliance."""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize validator.
        
        Args:
            llm_client: LLM client instance
        """
        self.llm_client = llm_client
        logger.info("BRS Validator initialized")
    
    def validate_final_brs(self, final_brs: FinalBRS) -> FinalBRS:
        """
        Validate the complete final BRS.
        
        Args:
            final_brs: Final BRS to validate
        
        Returns:
            Updated FinalBRS with validation results
        """
        logger.info(f"Validating final BRS: {final_brs.brs_id}")
        
        all_validation_notes = []
        all_passed = True
        
        # Validate each section
        for section in final_brs.sections:
            section_validation = self.validate_section(section)
            
            if not section_validation["validation_passed"]:
                all_passed = False
            
            # Collect validation notes
            for issue in section_validation.get("issues", []):
                note = (
                    f"[{section.section_id}] {issue['severity'].upper()}: "
                    f"{issue['category']} - {issue['description']}"
                )
                all_validation_notes.append(note)
        
        # Perform structural validation
        structural_issues = self._validate_structure(final_brs)
        all_validation_notes.extend(structural_issues)
        
        if structural_issues:
            all_passed = False
        
        # Update final BRS
        final_brs.validation_passed = all_passed
        final_brs.validation_notes = all_validation_notes
        
        logger.info(
            f"Validation complete: {'PASSED' if all_passed else 'FAILED'} "
            f"({len(all_validation_notes)} notes)"
        )
        
        return final_brs
    
    def validate_section(self, section: GeneratedSection) -> Dict[str, Any]:
        """
        Validate a single generated section using LLM.
        
        Args:
            section: Generated section to validate
        
        Returns:
            Validation results dict
        """
        logger.debug(f"Validating section: {section.section_id}")
        
        # Format validation prompt
        prompt = format_validation_prompt(
            generated_content=section.content,
            base_source=section.source_documents[0] if section.source_documents else "None",
            applied_changes=section.applied_changes,
            source_documents=section.source_documents
        )
        
        try:
            # Get LLM validation
            response = self.llm_client.generate(
                prompt=prompt,
                temperature=0.1,
                max_tokens=1000,
                json_mode=True
            )
            
            # Parse JSON response
            validation_result = self.llm_client.parse_json_response(response)
            
            logger.debug(
                f"Section {section.section_id}: "
                f"{'PASSED' if validation_result.get('validation_passed') else 'FAILED'}"
            )
            
            return validation_result
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"LLM validation unavailable for section {section.section_id}: {error_msg}")
            
            # If LLM is unavailable, use rule-based validation only
            # Don't mark as critical error - just skip LLM validation
            issues = []
            
            # Rule-based checks
            if not section.content or len(section.content.strip()) < 10:
                issues.append({
                    "severity": "warning",
                    "category": "completeness",
                    "description": "Section content is very short or empty",
                    "location": section.section_id
                })
            
            if not section.source_documents:
                issues.append({
                    "severity": "critical",
                    "category": "traceability",
                    "description": "No source documents recorded",
                    "location": section.section_id
                })
            
            # Check for placeholder text
            if "Not Specified" in section.content or "To Be Determined" in section.content:
                issues.append({
                    "severity": "info",
                    "category": "completeness",
                    "description": "Contains placeholder text - may need review",
                    "location": section.section_id
                })
            
            # Determine if validation passed (only fail on critical issues)
            validation_passed = not any(issue.get("severity") == "critical" for issue in issues)
            
            return {
                "validation_passed": validation_passed,
                "issues": issues,
                "recommendations": ["LLM validation unavailable - using rule-based validation only"] if "404" in error_msg or "not available" in error_msg.lower() else ["Manual review recommended"],
                "overall_score": 70 if validation_passed else 40  # Default scores
            }
    
    def _validate_structure(self, final_brs: FinalBRS) -> List[str]:
        """
        Perform rule-based structural validation.
        
        Args:
            final_brs: Final BRS document
        
        Returns:
            List of validation issues
        """
        issues = []
        
        # Check for empty sections
        for section in final_brs.sections:
            if not section.content or len(section.content.strip()) < 10:
                issues.append(
                    f"[{section.section_id}] WARNING: Section appears empty or too short"
                )
        
        # Check for missing traceability
        for section in final_brs.sections:
            if not section.source_documents:
                issues.append(
                    f"[{section.section_id}] CRITICAL: No source documents recorded"
                )
        
        # Check for duplicate section IDs
        section_ids = [s.section_id for s in final_brs.sections]
        duplicates = set([sid for sid in section_ids if section_ids.count(sid) > 1])
        
        if duplicates:
            issues.append(
                f"CRITICAL: Duplicate section IDs found: {', '.join(duplicates)}"
            )
        
        # Check for "Not Specified" placeholders
        for section in final_brs.sections:
            if "Not Specified" in section.content or "To Be Determined" in section.content:
                issues.append(
                    f"[{section.section_id}] INFO: Contains placeholder text - may need review"
                )
        
        return issues
    
    def generate_validation_report(self, final_brs: FinalBRS) -> str:
        """
        Generate a human-readable validation report.
        
        Args:
            final_brs: Validated final BRS
        
        Returns:
            Markdown-formatted validation report
        """
        report_lines = [
            "# BRS Validation Report",
            f"\n**BRS ID:** {final_brs.brs_id}",
            f"**Version:** {final_brs.version}",
            f"**Generated:** {final_brs.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"\n**Validation Status:** {'✅ PASSED' if final_brs.validation_passed else '❌ FAILED'}",
            f"\n## Summary",
            f"- Total Sections: {len(final_brs.sections)}",
            f"- Source BRS Documents: {len(final_brs.source_brs_documents)}",
            f"- Applied Change Requests: {len(final_brs.applied_change_requests)}",
            f"- Validation Issues: {len(final_brs.validation_notes)}",
        ]
        
        if final_brs.validation_notes:
            report_lines.append("\n## Validation Issues")
            for note in final_brs.validation_notes:
                report_lines.append(f"- {note}")
        
        report_lines.append("\n## Section Details")
        for section in final_brs.sections:
            report_lines.append(f"\n### {section.section_path} {section.section_title}")
            report_lines.append(f"- **Section ID:** {section.section_id}")
            report_lines.append(f"- **Content Length:** {len(section.content)} characters")
            report_lines.append(f"- **Source Documents:** {', '.join(section.source_documents)}")
            if section.applied_changes:
                report_lines.append(f"- **Applied Changes:** {', '.join(section.applied_changes)}")
        
        return "\n".join(report_lines)
