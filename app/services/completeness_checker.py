"""
Completeness Checker for validating BRS completeness and coverage.
Ensures the final BRS contains all required sections and covers all source content.
"""
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict

from app.models.schemas import FinalBRS, GeneratedSection
from app.services.brs_template import BRSTemplate, SectionType
from app.services.vector_store import VectorStore
from app.services.llm_client import LLMClient
from app.core.logging_config import logger


class CompletenessReport:
    """Report on BRS completeness and coverage."""
    
    def __init__(self):
        self.structure_score: float = 0.0
        self.coverage_score: float = 0.0
        self.overall_score: float = 0.0
        
        self.missing_required_sections: List[str] = []
        self.empty_sections: List[str] = []
        self.uncovered_source_sections: List[Dict[str, str]] = []
        self.unused_crs: List[str] = []
        
        self.structure_issues: List[str] = []
        self.coverage_issues: List[str] = []
        self.recommendations: List[str] = []
        
        self.statistics: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "scores": {
                "structure_score": self.structure_score,
                "coverage_score": self.coverage_score,
                "overall_score": self.overall_score
            },
            "missing_required_sections": self.missing_required_sections,
            "empty_sections": self.empty_sections,
            "uncovered_source_sections": self.uncovered_source_sections,
            "unused_crs": self.unused_crs,
            "structure_issues": self.structure_issues,
            "coverage_issues": self.coverage_issues,
            "recommendations": self.recommendations,
            "statistics": self.statistics
        }
    
    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            "# BRS Completeness Report",
            "",
            "## Overall Scores",
            f"- **Structure Score:** {self.structure_score:.1f}% - {'✅ PASS' if self.structure_score >= 80 else '⚠️ NEEDS IMPROVEMENT' if self.structure_score >= 60 else '❌ FAIL'}",
            f"- **Coverage Score:** {self.coverage_score:.1f}% - {'✅ PASS' if self.coverage_score >= 80 else '⚠️ NEEDS IMPROVEMENT' if self.coverage_score >= 60 else '❌ FAIL'}",
            f"- **Overall Score:** {self.overall_score:.1f}% - {'✅ PASS' if self.overall_score >= 80 else '⚠️ NEEDS IMPROVEMENT' if self.overall_score >= 60 else '❌ FAIL'}",
            ""
        ]
        
        # Statistics
        if self.statistics:
            lines.extend([
                "## Statistics",
                f"- Total Sections: {self.statistics.get('total_sections', 0)}",
                f"- Required Sections Present: {self.statistics.get('required_sections_present', 0)}/{self.statistics.get('total_required_sections', 0)}",
                f"- Source Sections Covered: {self.statistics.get('source_sections_covered', 0)}/{self.statistics.get('total_source_sections', 0)}",
                f"- CRs Applied: {self.statistics.get('crs_applied', 0)}/{self.statistics.get('total_crs', 0)}",
                ""
            ])
        
        # Missing required sections
        if self.missing_required_sections:
            lines.extend([
                "## ❌ Missing Required Sections",
                ""
            ])
            for section in self.missing_required_sections:
                lines.append(f"- {section}")
            lines.append("")
        
        # Empty sections
        if self.empty_sections:
            lines.extend([
                "## ⚠️ Empty or Placeholder Sections",
                ""
            ])
            for section in self.empty_sections:
                lines.append(f"- {section}")
            lines.append("")
        
        # Uncovered source sections
        if self.uncovered_source_sections:
            lines.extend([
                "## ⚠️ Source Content Not Covered",
                "",
                "The following sections from source BRS documents are not adequately covered in the final BRS:",
                ""
            ])
            for section in self.uncovered_source_sections[:10]:  # Limit to 10
                lines.append(f"- **{section.get('section_title')}** (from {section.get('doc_id')})")
            if len(self.uncovered_source_sections) > 10:
                lines.append(f"- ... and {len(self.uncovered_source_sections) - 10} more")
            lines.append("")
        
        # Unused CRs
        if self.unused_crs:
            lines.extend([
                "## ⚠️ Unused Change Requests",
                "",
                "The following CRs were uploaded but not applied:",
                ""
            ])
            for cr in self.unused_crs:
                lines.append(f"- {cr}")
            lines.append("")
        
        # Structure issues
        if self.structure_issues:
            lines.extend([
                "## Structure Issues",
                ""
            ])
            for issue in self.structure_issues:
                lines.append(f"- {issue}")
            lines.append("")
        
        # Coverage issues
        if self.coverage_issues:
            lines.extend([
                "## Coverage Issues",
                ""
            ])
            for issue in self.coverage_issues:
                lines.append(f"- {issue}")
            lines.append("")
        
        # Recommendations
        if self.recommendations:
            lines.extend([
                "## 💡 Recommendations",
                ""
            ])
            for rec in self.recommendations:
                lines.append(f"- {rec}")
            lines.append("")
        
        return "\n".join(lines)


class CompletenessChecker:
    """Checks BRS completeness and coverage against source documents."""
    
    def __init__(self, vector_store: VectorStore, llm_client: LLMClient):
        """
        Initialize completeness checker.
        
        Args:
            vector_store: Vector store with source documents
            llm_client: LLM client for semantic analysis
        """
        self.vector_store = vector_store
        self.llm_client = llm_client
        self.brs_template = BRSTemplate()
        logger.info("Completeness Checker initialized")
    
    def check_completeness(self, final_brs: FinalBRS) -> CompletenessReport:
        """
        Perform comprehensive completeness check.
        
        Args:
            final_brs: Final BRS document to check
        
        Returns:
            Completeness report
        """
        logger.info(f"Checking completeness for BRS: {final_brs.brs_id}")
        
        report = CompletenessReport()
        
        # 1. Check BRS structure completeness
        structure_results = self._check_structure_completeness(final_brs)
        report.structure_score = structure_results["score"]
        report.missing_required_sections = structure_results["missing_sections"]
        report.empty_sections = structure_results["empty_sections"]
        report.structure_issues = structure_results["issues"]
        
        # 2. Check source content coverage
        coverage_results = self._check_source_coverage(final_brs)
        report.coverage_score = coverage_results["score"]
        report.uncovered_source_sections = coverage_results["uncovered_sections"]
        report.unused_crs = coverage_results["unused_crs"]
        report.coverage_issues = coverage_results["issues"]
        
        # 3. Calculate overall score (weighted average)
        report.overall_score = (report.structure_score * 0.6) + (report.coverage_score * 0.4)
        
        # 4. Generate statistics
        report.statistics = self._generate_statistics(final_brs, structure_results, coverage_results)
        
        # 5. Generate recommendations
        report.recommendations = self._generate_recommendations(report)
        
        logger.info(
            f"Completeness check complete: Overall={report.overall_score:.1f}%, "
            f"Structure={report.structure_score:.1f}%, Coverage={report.coverage_score:.1f}%"
        )
        
        return report
    
    def _check_structure_completeness(self, final_brs: FinalBRS) -> Dict[str, Any]:
        """
        Check if BRS has all required sections according to template.
        
        Args:
            final_brs: Final BRS document
        
        Returns:
            Structure completeness results
        """
        logger.debug("Checking BRS structure completeness")
        
        # Get all template sections
        template_sections = self.brs_template.get_all_sections_flat()
        required_sections = [s for s in template_sections if s.is_required]
        
        # Get section numbers from final BRS
        final_section_numbers = {s.section_path for s in final_brs.sections}
        
        # Check which required sections are missing
        missing_sections = []
        for req_section in required_sections:
            if req_section.section_number not in final_section_numbers:
                missing_sections.append(
                    f"{req_section.section_number} - {req_section.section_title}"
                )
        
        # Check for empty or placeholder sections
        empty_sections = []
        for section in final_brs.sections:
            content = section.content.strip()
            
            # Check if empty
            if len(content) < 50:
                empty_sections.append(f"{section.section_path} - {section.section_title} (too short)")
                continue
            
            # Check for placeholder text
            placeholder_indicators = [
                "to be completed",
                "to be determined",
                "tbd",
                "placeholder",
                "not specified",
                "requires manual completion",
                "[to be completed]"
            ]
            
            if any(indicator in content.lower() for indicator in placeholder_indicators):
                empty_sections.append(f"{section.section_path} - {section.section_title} (placeholder)")
        
        # Calculate structure score
        total_required = len(required_sections)
        present_required = total_required - len(missing_sections)
        total_sections = len(final_brs.sections)
        non_empty = total_sections - len(empty_sections)
        
        # Score: 70% for having required sections, 30% for non-empty content
        required_score = (present_required / total_required * 100) if total_required > 0 else 100
        content_score = (non_empty / total_sections * 100) if total_sections > 0 else 0
        structure_score = (required_score * 0.7) + (content_score * 0.3)
        
        issues = []
        if missing_sections:
            issues.append(f"{len(missing_sections)} required sections are missing")
        if empty_sections:
            issues.append(f"{len(empty_sections)} sections are empty or contain placeholders")
        
        return {
            "score": structure_score,
            "missing_sections": missing_sections,
            "empty_sections": empty_sections,
            "issues": issues,
            "total_required": total_required,
            "present_required": present_required
        }
    
    def _check_source_coverage(self, final_brs: FinalBRS) -> Dict[str, Any]:
        """
        Check if final BRS covers all content from source documents.
        
        Args:
            final_brs: Final BRS document
        
        Returns:
            Coverage results
        """
        logger.debug("Checking source content coverage")
        
        # Get all source BRS sections from vector store
        source_sections = self._get_all_source_sections()
        
        # Get all CRs from vector store
        all_crs = self._get_all_crs()
        
        # Track which source sections are covered
        covered_sections = set()
        for section in final_brs.sections:
            for source_doc in section.source_documents:
                covered_sections.add(source_doc)
        
        # Track which CRs are applied
        applied_crs = set(final_brs.applied_change_requests)
        
        # Find uncovered source sections
        uncovered_sections = []
        for source_section in source_sections:
            doc_id = source_section.get("doc_id", "")
            section_id = source_section.get("section_id", "")
            
            # Check if this section is referenced in final BRS
            is_covered = False
            for final_section in final_brs.sections:
                if doc_id in final_section.source_documents:
                    # Check if content is actually used (simple heuristic)
                    source_title = source_section.get("section_title", "").lower()
                    if source_title in final_section.content.lower() or \
                       source_title in final_section.section_title.lower():
                        is_covered = True
                        break
            
            if not is_covered:
                uncovered_sections.append({
                    "doc_id": doc_id,
                    "section_id": section_id,
                    "section_title": source_section.get("section_title", "Unknown"),
                    "section_path": source_section.get("section_path", "")
                })
        
        # Find unused CRs
        unused_crs = [cr for cr in all_crs if cr not in applied_crs]
        
        # Calculate coverage score
        total_source_sections = len(source_sections)
        covered_count = total_source_sections - len(uncovered_sections)
        
        total_crs = len(all_crs)
        applied_count = len(applied_crs)
        
        # Score: 70% for source section coverage, 30% for CR application
        section_coverage = (covered_count / total_source_sections * 100) if total_source_sections > 0 else 100
        cr_coverage = (applied_count / total_crs * 100) if total_crs > 0 else 100
        coverage_score = (section_coverage * 0.7) + (cr_coverage * 0.3)
        
        issues = []
        if uncovered_sections:
            issues.append(f"{len(uncovered_sections)} source sections not adequately covered")
        if unused_crs:
            issues.append(f"{len(unused_crs)} CRs were not applied")
        
        return {
            "score": coverage_score,
            "uncovered_sections": uncovered_sections,
            "unused_crs": unused_crs,
            "issues": issues,
            "total_source_sections": total_source_sections,
            "covered_sections": covered_count,
            "total_crs": total_crs,
            "applied_crs": applied_count
        }
    
    def _get_all_source_sections(self) -> List[Dict[str, str]]:
        """Get all sections from source BRS documents."""
        try:
            results = self.vector_store.brs_collection.get(limit=1000)
            
            sections = []
            seen = set()
            
            if results and 'metadatas' in results:
                for metadata in results['metadatas']:
                    section_id = metadata.get('section_id', '')
                    doc_id = metadata.get('doc_id', '')
                    key = f"{doc_id}:{section_id}"
                    
                    if key not in seen:
                        sections.append({
                            "doc_id": doc_id,
                            "section_id": section_id,
                            "section_title": metadata.get('section_title', ''),
                            "section_path": metadata.get('section_path', '')
                        })
                        seen.add(key)
            
            return sections
        except Exception as e:
            logger.error(f"Error getting source sections: {e}")
            return []
    
    def _get_all_crs(self) -> List[str]:
        """Get all CR IDs from vector store."""
        try:
            results = self.vector_store.cr_collection.get(limit=1000)
            
            cr_ids = set()
            if results and 'metadatas' in results:
                for metadata in results['metadatas']:
                    cr_id = metadata.get('cr_id', '')
                    if cr_id:
                        cr_ids.add(cr_id)
            
            return list(cr_ids)
        except Exception as e:
            logger.error(f"Error getting CRs: {e}")
            return []
    
    def _generate_statistics(
        self,
        final_brs: FinalBRS,
        structure_results: Dict[str, Any],
        coverage_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate statistics for the report."""
        return {
            "total_sections": len(final_brs.sections),
            "total_required_sections": structure_results.get("total_required", 0),
            "required_sections_present": structure_results.get("present_required", 0),
            "total_source_sections": coverage_results.get("total_source_sections", 0),
            "source_sections_covered": coverage_results.get("covered_sections", 0),
            "total_crs": coverage_results.get("total_crs", 0),
            "crs_applied": coverage_results.get("applied_crs", 0),
            "source_brs_documents": len(final_brs.source_brs_documents),
            "total_content_length": sum(len(s.content) for s in final_brs.sections)
        }
    
    def _generate_recommendations(self, report: CompletenessReport) -> List[str]:
        """Generate recommendations based on report findings."""
        recommendations = []
        
        # Structure recommendations
        if report.missing_required_sections:
            recommendations.append(
                f"Add the {len(report.missing_required_sections)} missing required sections to meet BRS standards"
            )
        
        if report.empty_sections:
            recommendations.append(
                f"Complete the {len(report.empty_sections)} empty or placeholder sections with actual content"
            )
        
        # Coverage recommendations
        if report.uncovered_source_sections:
            recommendations.append(
                f"Review and incorporate content from {len(report.uncovered_source_sections)} uncovered source sections"
            )
        
        if report.unused_crs:
            recommendations.append(
                f"Verify if the {len(report.unused_crs)} unused CRs should be applied or can be excluded"
            )
        
        # Score-based recommendations
        if report.structure_score < 80:
            recommendations.append(
                "Improve BRS structure by ensuring all required sections are present and complete"
            )
        
        if report.coverage_score < 80:
            recommendations.append(
                "Improve source coverage by ensuring all relevant content from source documents is included"
            )
        
        if not recommendations:
            recommendations.append("BRS appears complete and comprehensive. Perform final manual review.")
        
        return recommendations
