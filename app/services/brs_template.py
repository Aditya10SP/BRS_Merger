"""
BRS Template service for generating properly structured BRS documents.
Defines the standard structure and sections of a Business Requirements Specification.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from app.core.logging_config import logger


class SectionType(Enum):
    """Types of BRS sections."""
    EXECUTIVE_SUMMARY = "executive_summary"
    INTRODUCTION = "introduction"
    BUSINESS_OBJECTIVES = "business_objectives"
    STAKEHOLDER_REQUIREMENTS = "stakeholder_requirements"
    SCOPE = "scope"
    FUNCTIONAL_REQUIREMENTS = "functional_requirements"
    NON_FUNCTIONAL_REQUIREMENTS = "non_functional_requirements"
    CONSTRAINTS = "constraints"
    ASSUMPTIONS = "assumptions"
    DEPENDENCIES = "dependencies"
    ACCEPTANCE_CRITERIA = "acceptance_criteria"
    GLOSSARY = "glossary"
    APPENDICES = "appendices"


@dataclass
class BRSSection:
    """Defines a BRS section structure."""
    section_number: str
    section_title: str
    section_type: SectionType
    description: str
    is_required: bool = True
    subsections: List['BRSSection'] = None
    
    def __post_init__(self):
        if self.subsections is None:
            self.subsections = []


class BRSTemplate:
    """Standard BRS document template."""
    
    def __init__(self):
        """Initialize BRS template with standard structure."""
        self.sections = self._create_standard_template()
    
    def _create_standard_template(self) -> List[BRSSection]:
        """
        Create the standard BRS document structure.
        
        Returns:
            List of BRS sections in proper order
        """
        return [
            # 1. Executive Summary
            BRSSection(
                section_number="1",
                section_title="Executive Summary",
                section_type=SectionType.EXECUTIVE_SUMMARY,
                description="High-level overview of the business requirements, objectives, and expected outcomes",
                is_required=True
            ),
            
            # 2. Introduction
            BRSSection(
                section_number="2",
                section_title="Introduction",
                section_type=SectionType.INTRODUCTION,
                description="Background, purpose, and context of the requirements",
                is_required=True,
                subsections=[
                    BRSSection(
                        section_number="2.1",
                        section_title="Purpose",
                        section_type=SectionType.INTRODUCTION,
                        description="Purpose of this BRS document"
                    ),
                    BRSSection(
                        section_number="2.2",
                        section_title="Document Scope",
                        section_type=SectionType.INTRODUCTION,
                        description="What this document covers"
                    ),
                    BRSSection(
                        section_number="2.3",
                        section_title="Definitions and Acronyms",
                        section_type=SectionType.INTRODUCTION,
                        description="Key terms and abbreviations used"
                    ),
                    BRSSection(
                        section_number="2.4",
                        section_title="References",
                        section_type=SectionType.INTRODUCTION,
                        description="Related documents and sources"
                    ),
                ]
            ),
            
            # 3. Business Objectives
            BRSSection(
                section_number="3",
                section_title="Business Objectives",
                section_type=SectionType.BUSINESS_OBJECTIVES,
                description="Strategic goals and business drivers",
                is_required=True,
                subsections=[
                    BRSSection(
                        section_number="3.1",
                        section_title="Business Goals",
                        section_type=SectionType.BUSINESS_OBJECTIVES,
                        description="High-level business goals"
                    ),
                    BRSSection(
                        section_number="3.2",
                        section_title="Success Criteria",
                        section_type=SectionType.BUSINESS_OBJECTIVES,
                        description="Measurable success indicators"
                    ),
                ]
            ),
            
            # 4. Stakeholder Requirements
            BRSSection(
                section_number="4",
                section_title="Stakeholder Requirements",
                section_type=SectionType.STAKEHOLDER_REQUIREMENTS,
                description="Requirements from different stakeholder groups",
                is_required=True,
                subsections=[
                    BRSSection(
                        section_number="4.1",
                        section_title="Business Stakeholders",
                        section_type=SectionType.STAKEHOLDER_REQUIREMENTS,
                        description="Requirements from business users"
                    ),
                    BRSSection(
                        section_number="4.2",
                        section_title="Technical Stakeholders",
                        section_type=SectionType.STAKEHOLDER_REQUIREMENTS,
                        description="Requirements from technical teams"
                    ),
                    BRSSection(
                        section_number="4.3",
                        section_title="End Users",
                        section_type=SectionType.STAKEHOLDER_REQUIREMENTS,
                        description="Requirements from end users"
                    ),
                ]
            ),
            
            # 5. Scope
            BRSSection(
                section_number="5",
                section_title="Scope",
                section_type=SectionType.SCOPE,
                description="What is included and excluded from the project",
                is_required=True,
                subsections=[
                    BRSSection(
                        section_number="5.1",
                        section_title="In Scope",
                        section_type=SectionType.SCOPE,
                        description="Features and capabilities included"
                    ),
                    BRSSection(
                        section_number="5.2",
                        section_title="Out of Scope",
                        section_type=SectionType.SCOPE,
                        description="Features and capabilities explicitly excluded"
                    ),
                ]
            ),
            
            # 6. Functional Requirements
            BRSSection(
                section_number="6",
                section_title="Functional Requirements",
                section_type=SectionType.FUNCTIONAL_REQUIREMENTS,
                description="Detailed functional capabilities the system must provide",
                is_required=True
            ),
            
            # 7. Non-Functional Requirements
            BRSSection(
                section_number="7",
                section_title="Non-Functional Requirements",
                section_type=SectionType.NON_FUNCTIONAL_REQUIREMENTS,
                description="Quality attributes and system characteristics",
                is_required=True,
                subsections=[
                    BRSSection(
                        section_number="7.1",
                        section_title="Performance Requirements",
                        section_type=SectionType.NON_FUNCTIONAL_REQUIREMENTS,
                        description="Speed, throughput, response time"
                    ),
                    BRSSection(
                        section_number="7.2",
                        section_title="Security Requirements",
                        section_type=SectionType.NON_FUNCTIONAL_REQUIREMENTS,
                        description="Authentication, authorization, data protection"
                    ),
                    BRSSection(
                        section_number="7.3",
                        section_title="Scalability Requirements",
                        section_type=SectionType.NON_FUNCTIONAL_REQUIREMENTS,
                        description="Growth and load handling"
                    ),
                    BRSSection(
                        section_number="7.4",
                        section_title="Reliability and Availability",
                        section_type=SectionType.NON_FUNCTIONAL_REQUIREMENTS,
                        description="Uptime, fault tolerance, disaster recovery"
                    ),
                    BRSSection(
                        section_number="7.5",
                        section_title="Usability Requirements",
                        section_type=SectionType.NON_FUNCTIONAL_REQUIREMENTS,
                        description="User experience and accessibility"
                    ),
                    BRSSection(
                        section_number="7.6",
                        section_title="Maintainability",
                        section_type=SectionType.NON_FUNCTIONAL_REQUIREMENTS,
                        description="Ease of maintenance and updates"
                    ),
                ]
            ),
            
            # 8. Constraints
            BRSSection(
                section_number="8",
                section_title="Constraints",
                section_type=SectionType.CONSTRAINTS,
                description="Limitations and restrictions",
                is_required=True,
                subsections=[
                    BRSSection(
                        section_number="8.1",
                        section_title="Technical Constraints",
                        section_type=SectionType.CONSTRAINTS,
                        description="Technology and platform limitations"
                    ),
                    BRSSection(
                        section_number="8.2",
                        section_title="Business Constraints",
                        section_type=SectionType.CONSTRAINTS,
                        description="Budget, timeline, resource limitations"
                    ),
                    BRSSection(
                        section_number="8.3",
                        section_title="Regulatory Constraints",
                        section_type=SectionType.CONSTRAINTS,
                        description="Compliance and legal requirements"
                    ),
                ]
            ),
            
            # 9. Assumptions
            BRSSection(
                section_number="9",
                section_title="Assumptions",
                section_type=SectionType.ASSUMPTIONS,
                description="Assumptions made during requirements gathering",
                is_required=True
            ),
            
            # 10. Dependencies
            BRSSection(
                section_number="10",
                section_title="Dependencies",
                section_type=SectionType.DEPENDENCIES,
                description="External dependencies and prerequisites",
                is_required=True,
                subsections=[
                    BRSSection(
                        section_number="10.1",
                        section_title="System Dependencies",
                        section_type=SectionType.DEPENDENCIES,
                        description="Dependent systems and services"
                    ),
                    BRSSection(
                        section_number="10.2",
                        section_title="Data Dependencies",
                        section_type=SectionType.DEPENDENCIES,
                        description="Required data sources and formats"
                    ),
                ]
            ),
            
            # 11. Acceptance Criteria
            BRSSection(
                section_number="11",
                section_title="Acceptance Criteria",
                section_type=SectionType.ACCEPTANCE_CRITERIA,
                description="Criteria for accepting the delivered solution",
                is_required=True
            ),
            
            # 12. Glossary
            BRSSection(
                section_number="12",
                section_title="Glossary",
                section_type=SectionType.GLOSSARY,
                description="Definitions of terms used in this document",
                is_required=False
            ),
            
            # 13. Appendices
            BRSSection(
                section_number="13",
                section_title="Appendices",
                section_type=SectionType.APPENDICES,
                description="Supporting documentation and additional information",
                is_required=False
            ),
        ]
    
    def get_all_sections_flat(self) -> List[BRSSection]:
        """
        Get all sections including subsections in a flat list.
        
        Returns:
            Flat list of all sections
        """
        flat_sections = []
        for section in self.sections:
            flat_sections.append(section)
            if section.subsections:
                flat_sections.extend(section.subsections)
        return flat_sections
    
    def find_section_by_number(self, section_number: str) -> Optional[BRSSection]:
        """
        Find a section by its number.
        
        Args:
            section_number: Section number (e.g., "3.1")
        
        Returns:
            BRSSection if found, None otherwise
        """
        for section in self.get_all_sections_flat():
            if section.section_number == section_number:
                return section
        return None
    
    def get_section_mapping_hints(self) -> Dict[str, List[str]]:
        """
        Get hints for mapping source content to BRS sections.
        
        Returns:
            Dictionary mapping section types to keywords
        """
        return {
            "executive_summary": ["summary", "overview", "abstract", "executive"],
            "introduction": ["introduction", "background", "purpose", "context"],
            "business_objectives": ["objectives", "goals", "business goals", "strategic"],
            "stakeholder_requirements": ["stakeholder", "user requirements", "business requirements"],
            "scope": ["scope", "in scope", "out of scope", "boundaries"],
            "functional_requirements": ["functional", "features", "capabilities", "shall", "must"],
            "non_functional_requirements": ["performance", "security", "scalability", "reliability", "usability"],
            "constraints": ["constraints", "limitations", "restrictions"],
            "assumptions": ["assumptions", "assumptions made"],
            "dependencies": ["dependencies", "prerequisites", "dependent"],
            "acceptance_criteria": ["acceptance", "criteria", "success criteria"],
        }
