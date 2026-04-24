"""
BRS Mapper service for mapping source content to standard BRS template.
"""
from typing import List, Dict, Any, Optional
import re

from app.services.brs_template import BRSTemplate, BRSSection, SectionType
from app.models.schemas import GeneratedSection
from app.core.logging_config import logger


class BRSMapper:
    """Maps source content to standard BRS structure."""
    
    def __init__(self):
        """Initialize BRS mapper with template."""
        self.template = BRSTemplate()
        self.mapping_hints = self.template.get_section_mapping_hints()
        logger.info("BRS Mapper initialized with standard template")
    
    def map_sections_to_template(
        self,
        generated_sections: List[GeneratedSection]
    ) -> Dict[str, List[GeneratedSection]]:
        """
        Map generated sections to BRS template sections.
        
        Args:
            generated_sections: List of generated sections from consolidation
        
        Returns:
            Dictionary mapping template section numbers to generated sections
        """
        logger.info(f"Mapping {len(generated_sections)} sections to BRS template")
        
        section_mapping = {}
        unmapped_sections = []
        
        for gen_section in generated_sections:
            # Try to map based on section title and content
            mapped_section = self._find_best_match(gen_section)
            
            if mapped_section:
                section_num = mapped_section.section_number
                if section_num not in section_mapping:
                    section_mapping[section_num] = []
                section_mapping[section_num].append(gen_section)
                logger.debug(f"Mapped {gen_section.section_title} -> {mapped_section.section_title}")
            else:
                unmapped_sections.append(gen_section)
                logger.warning(f"Could not map section: {gen_section.section_title}")
        
        # Try to map unmapped sections to "Functional Requirements" as default
        if unmapped_sections:
            func_req_section = self.template.find_section_by_number("6")
            if func_req_section:
                if "6" not in section_mapping:
                    section_mapping["6"] = []
                section_mapping["6"].extend(unmapped_sections)
                logger.info(f"Mapped {len(unmapped_sections)} unmapped sections to Functional Requirements")
        
        return section_mapping
    
    def _find_best_match(self, gen_section: GeneratedSection) -> Optional[BRSSection]:
        """
        Find the best matching template section for a generated section.
        
        Args:
            gen_section: Generated section to map
        
        Returns:
            Best matching BRSSection or None
        """
        title_lower = gen_section.section_title.lower()
        content_lower = gen_section.content.lower()[:500]  # Check first 500 chars
        
        best_match = None
        best_score = 0
        
        for template_section in self.template.get_all_sections_flat():
            score = 0
            
            # Check title similarity
            template_title_lower = template_section.section_title.lower()
            if template_title_lower in title_lower or title_lower in template_title_lower:
                score += 10
            
            # Check keywords from mapping hints
            section_type_key = template_section.section_type.value
            if section_type_key in self.mapping_hints:
                keywords = self.mapping_hints[section_type_key]
                for keyword in keywords:
                    if keyword in title_lower:
                        score += 5
                    if keyword in content_lower:
                        score += 2
            
            # Special handling for scope sections
            if "scope" in title_lower:
                if "in scope" in title_lower or "included" in title_lower:
                    if template_section.section_number == "5.1":
                        score += 15
                elif "out of scope" in title_lower or "excluded" in title_lower:
                    if template_section.section_number == "5.2":
                        score += 15
            
            if score > best_score:
                best_score = score
                best_match = template_section
        
        return best_match if best_score > 0 else None
    
    def identify_missing_sections(
        self,
        section_mapping: Dict[str, List[GeneratedSection]]
    ) -> List[BRSSection]:
        """
        Identify which required template sections are missing.
        
        Args:
            section_mapping: Current mapping of sections
        
        Returns:
            List of missing required sections
        """
        missing = []
        
        for template_section in self.template.get_all_sections_flat():
            if template_section.is_required:
                if template_section.section_number not in section_mapping:
                    missing.append(template_section)
        
        logger.info(f"Found {len(missing)} missing required sections")
        return missing
