"""
Missing Section Generator for creating BRS sections that don't exist in source documents.
Uses RAG to extract relevant information from uploaded documents.
"""
from typing import List, Dict, Any, Optional

from app.services.brs_template import BRSSection, SectionType
from app.services.llm_client import LLMClient
from app.services.rag_engine import RAGEngine
from app.models.schemas import GeneratedSection
from app.core.logging_config import logger


class MissingSectionGenerator:
    """Generates missing BRS sections using RAG and LLM."""
    
    def __init__(self, llm_client: LLMClient, rag_engine: RAGEngine):
        """
        Initialize generator.
        
        Args:
            llm_client: LLM client for generation
            rag_engine: RAG engine for retrieving relevant content
        """
        self.llm_client = llm_client
        self.rag_engine = rag_engine
        logger.info("Missing Section Generator initialized with RAG")
    
    def generate_missing_section(
        self,
        template_section: BRSSection,
        project_context: Dict[str, Any],
        existing_sections: List[GeneratedSection]
    ) -> GeneratedSection:
        """
        Generate a missing BRS section using RAG to extract from source documents.
        
        Args:
            template_section: Template section to generate
            project_context: Context about the project
            existing_sections: Already generated sections for context
        
        Returns:
            Generated section
        """
        logger.info(f"Generating missing section: {template_section.section_title}")
        
        # Step 1: Use RAG to retrieve relevant content from uploaded documents
        relevant_content = self._retrieve_relevant_content(template_section)
        
        # Step 2: Build context from existing sections
        context_summary = self._build_context_summary(existing_sections)
        
        # Step 3: Create generation prompt with retrieved content
        prompt = self._create_generation_prompt(
            template_section,
            project_context,
            context_summary,
            relevant_content
        )
        
        try:
            # Generate content
            response = self.llm_client.generate(
                prompt=prompt,
                temperature=0.2,  # Lower temperature for factual content
                max_tokens=2000
            )
            
            content = response.strip()
            
            # Create GeneratedSection
            section = GeneratedSection(
                section_id=f"SEC-{template_section.section_number.replace('.', '-')}",
                section_title=template_section.section_title,
                section_path=template_section.section_number,
                content=content,
                source_documents=relevant_content.get("source_documents", ["GENERATED"]),
                applied_changes=relevant_content.get("applied_changes", []),
                confidence_score=0.85 if relevant_content.get("chunks") else 0.6,
                generation_metadata={
                    "generated_by": "missing_section_generator",
                    "template_section": template_section.section_number,
                    "section_type": template_section.section_type.value,
                    "used_rag": bool(relevant_content.get("chunks")),
                    "num_source_chunks": len(relevant_content.get("chunks", []))
                }
            )
            
            logger.info(f"Successfully generated section: {template_section.section_title} (used {len(relevant_content.get('chunks', []))} source chunks)")
            return section
            
        except Exception as e:
            logger.error(f"Error generating section {template_section.section_title}: {e}")
            # Return placeholder section
            return self._create_placeholder_section(template_section)
    
    def _retrieve_relevant_content(self, template_section: BRSSection) -> Dict[str, Any]:
        """
        Retrieve relevant content from uploaded documents using RAG.
        
        Args:
            template_section: Template section to find content for
        
        Returns:
            Dictionary with retrieved chunks and metadata
        """
        # Build search queries based on section type
        search_queries = self._get_search_queries_for_section(template_section)
        
        all_chunks = []
        all_sources = set()
        all_changes = set()
        
        for query in search_queries:
            try:
                # Search BRS chunks
                brs_results = self.rag_engine.vector_store.query_brs_by_section(
                    section_title=query,
                    top_k=5
                )
                
                for result in brs_results:
                    all_chunks.append({
                        "content": result.get("content", ""),
                        "metadata": result.get("metadata", {})
                    })
                    if "doc_id" in result.get("metadata", {}):
                        all_sources.add(result["metadata"]["doc_id"])
                
                # Search CR chunks for relevant changes
                cr_results = self.rag_engine.vector_store.query_cr_by_section(
                    section_title=query,
                    top_k=3
                )
                
                for result in cr_results:
                    all_chunks.append({
                        "content": result.get("content", ""),
                        "metadata": result.get("metadata", {})
                    })
                    if "cr_id" in result.get("metadata", {}):
                        all_changes.add(result["metadata"]["cr_id"])
                
            except Exception as e:
                logger.warning(f"Error retrieving content for query '{query}': {e}")
                continue
        
        logger.info(f"Retrieved {len(all_chunks)} chunks from {len(all_sources)} sources for {template_section.section_title}")
        
        return {
            "chunks": all_chunks,
            "source_documents": list(all_sources),
            "applied_changes": list(all_changes)
        }
    
    def _format_retrieved_content(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Format retrieved chunks into readable content for the prompt.
        
        Args:
            chunks: List of retrieved chunks with content and metadata
        
        Returns:
            Formatted string of source content
        """
        if not chunks:
            return "No relevant content found in source documents. Please generate based on standard BRS practices."
        
        formatted_parts = []
        
        for i, chunk in enumerate(chunks[:10], 1):  # Limit to top 10 chunks
            content = chunk.get("content", "").strip()
            metadata = chunk.get("metadata", {})
            
            # Get source information
            doc_id = metadata.get("doc_id", metadata.get("cr_id", "Unknown"))
            section_title = metadata.get("section_title", "")
            
            # Format chunk
            formatted_parts.append(f"**Source {i}** (from {doc_id}):")
            if section_title:
                formatted_parts.append(f"Section: {section_title}")
            formatted_parts.append(f"{content}")
            formatted_parts.append("")  # Empty line between chunks
        
        return "\n".join(formatted_parts)
    
    def _get_search_queries_for_section(self, template_section: BRSSection) -> List[str]:
        """
        Generate search queries based on section type.
        
        Args:
            template_section: Template section
        
        Returns:
            List of search queries
        """
        section_type = template_section.section_type
        
        # Map section types to relevant search terms
        query_map = {
            SectionType.EXECUTIVE_SUMMARY: ["summary", "overview", "executive", "introduction", "purpose"],
            SectionType.INTRODUCTION: ["introduction", "background", "purpose", "scope", "context"],
            SectionType.BUSINESS_OBJECTIVES: ["objectives", "goals", "business goals", "strategic", "targets"],
            SectionType.STAKEHOLDER_REQUIREMENTS: ["stakeholder", "requirements", "user needs", "business needs"],
            SectionType.SCOPE: ["scope", "in scope", "out of scope", "boundaries", "limitations"],
            SectionType.FUNCTIONAL_REQUIREMENTS: ["functional", "features", "capabilities", "requirements", "shall"],
            SectionType.NON_FUNCTIONAL_REQUIREMENTS: ["performance", "security", "scalability", "reliability", "quality"],
            SectionType.CONSTRAINTS: ["constraints", "limitations", "restrictions", "dependencies"],
            SectionType.ASSUMPTIONS: ["assumptions", "prerequisites", "conditions"],
            SectionType.DEPENDENCIES: ["dependencies", "integrations", "external systems", "interfaces"],
            SectionType.ACCEPTANCE_CRITERIA: ["acceptance", "criteria", "testing", "validation", "success"],
        }
        
        queries = query_map.get(section_type, [template_section.section_title.lower()])
        
        # Add the section title itself
        queries.append(template_section.section_title.lower())
        
        return queries[:3]  # Limit to top 3 queries
    
    def _build_context_summary(self, existing_sections: List[GeneratedSection]) -> str:
        """
        Build a summary of existing sections for context.
        
        Args:
            existing_sections: List of existing sections
        
        Returns:
            Context summary string
        """
        if not existing_sections:
            return "No existing sections available."
        
        summary_parts = ["Available context from existing sections:"]
        
        for section in existing_sections[:10]:  # Limit to first 10 sections
            # Get first 200 chars of content
            content_preview = section.content[:200].strip()
            if len(section.content) > 200:
                content_preview += "..."
            
            summary_parts.append(
                f"\n- {section.section_title}: {content_preview}"
            )
        
        return "\n".join(summary_parts)
    
    def _create_generation_prompt(
        self,
        template_section: BRSSection,
        project_context: Dict[str, Any],
        context_summary: str,
        relevant_content: Dict[str, Any]
    ) -> str:
        """
        Create prompt for generating missing section with retrieved content.
        
        Args:
            template_section: Template section to generate
            project_context: Project context
            context_summary: Summary of existing sections
            relevant_content: Retrieved content from source documents
        
        Returns:
            Generation prompt
        """
        project_title = project_context.get("title", "Business Requirements Specification")
        
        # Format retrieved chunks
        source_content = self._format_retrieved_content(relevant_content.get("chunks", []))
        
        prompt = f"""You are a Business Analyst creating a Business Requirements Specification (BRS) document.

**Task**: Generate the "{template_section.section_title}" section for this BRS document.

**Section Purpose**: {template_section.description}

**Project Information**:
- Title: {project_title}

**IMPORTANT**: Use ONLY the information from the source documents provided below. Do NOT make up or invent information.

**Source Content from Uploaded Documents**:
{source_content}

**Context from Other Generated Sections**:
{context_summary}

**Instructions**:
1. Extract and synthesize information from the source content above
2. Focus on information relevant to "{template_section.section_title}"
3. Write professional, clear, and concise content
4. Maintain consistency with other sections
5. Use proper formatting (bullet points, numbered lists where appropriate)
6. If source content is insufficient, clearly state what information is missing
7. Do NOT invent or fabricate information not present in source documents

**Section Type Specific Guidelines**:
{self._get_section_specific_guidelines(template_section.section_type)}

Generate the content for the "{template_section.section_title}" section now, using ONLY information from the source documents:
"""
        
        return prompt
    
    def _get_section_specific_guidelines(self, section_type: SectionType) -> str:
        """
        Get specific guidelines for different section types.
        
        Args:
            section_type: Type of section
        
        Returns:
            Guidelines string
        """
        guidelines = {
            SectionType.EXECUTIVE_SUMMARY: """
- Provide a high-level overview (1-2 paragraphs)
- Summarize key objectives and expected outcomes
- Highlight critical requirements
- Keep it concise and business-focused
""",
            SectionType.INTRODUCTION: """
- Explain the purpose of this document
- Provide background and context
- Define the scope of the document
- List key stakeholders
""",
            SectionType.BUSINESS_OBJECTIVES: """
- List 3-5 clear business goals
- Make them SMART (Specific, Measurable, Achievable, Relevant, Time-bound)
- Align with business strategy
- Include success metrics
""",
            SectionType.STAKEHOLDER_REQUIREMENTS: """
- Identify different stakeholder groups
- List their specific needs and requirements
- Prioritize requirements
- Note any conflicting requirements
""",
            SectionType.SCOPE: """
- Clearly define what IS included
- Explicitly state what is NOT included
- Set clear boundaries
- Avoid ambiguity
""",
            SectionType.FUNCTIONAL_REQUIREMENTS: """
- Use "shall" or "must" for mandatory requirements
- Use "should" for recommended requirements
- Number each requirement (FR-001, FR-002, etc.)
- Make requirements testable and verifiable
""",
            SectionType.NON_FUNCTIONAL_REQUIREMENTS: """
- Include quantifiable metrics where possible
- Cover: performance, security, scalability, reliability, usability
- Make requirements measurable
- Use industry standards as reference
""",
            SectionType.CONSTRAINTS: """
- List technical, business, and regulatory constraints
- Explain impact of each constraint
- Be realistic and specific
""",
            SectionType.ASSUMPTIONS: """
- List key assumptions made
- Explain why each assumption is necessary
- Note risks if assumptions prove incorrect
""",
            SectionType.DEPENDENCIES: """
- Identify external systems and services
- List data dependencies
- Note critical path dependencies
- Include version requirements where applicable
""",
            SectionType.ACCEPTANCE_CRITERIA: """
- Define clear, measurable criteria
- Specify testing requirements
- Include sign-off procedures
- List deliverables
""",
        }
        
        return guidelines.get(section_type, "Follow standard BRS documentation practices.")
    
    def _create_placeholder_section(self, template_section: BRSSection) -> GeneratedSection:
        """
        Create a placeholder section when generation fails.
        
        Args:
            template_section: Template section
        
        Returns:
            Placeholder GeneratedSection
        """
        content = f"""**{template_section.section_title}**

{template_section.description}

*This section requires manual completion. Please provide the following information:*

{self._get_placeholder_content(template_section.section_type)}

---
*Note: This section was auto-generated as a placeholder. Please review and complete with project-specific details.*
"""
        
        return GeneratedSection(
            section_id=f"SEC-{template_section.section_number.replace('.', '-')}",
            section_title=template_section.section_title,
            section_path=template_section.section_number,
            content=content,
            source_documents=["PLACEHOLDER"],
            applied_changes=[],
            confidence_score=0.3,
            generation_metadata={
                "generated_by": "placeholder",
                "requires_manual_completion": True
            }
        )
    
    def _get_placeholder_content(self, section_type: SectionType) -> str:
        """Get placeholder content for different section types."""
        placeholders = {
            SectionType.EXECUTIVE_SUMMARY: "- Project overview\n- Key objectives\n- Expected outcomes\n- Critical success factors",
            SectionType.BUSINESS_OBJECTIVES: "- Business goal 1\n- Business goal 2\n- Success metrics\n- Timeline",
            SectionType.STAKEHOLDER_REQUIREMENTS: "- Business stakeholder needs\n- Technical stakeholder needs\n- End user requirements",
            SectionType.FUNCTIONAL_REQUIREMENTS: "- FR-001: [Requirement description]\n- FR-002: [Requirement description]",
            SectionType.NON_FUNCTIONAL_REQUIREMENTS: "- Performance requirements\n- Security requirements\n- Scalability requirements",
            SectionType.CONSTRAINTS: "- Technical constraints\n- Business constraints\n- Regulatory constraints",
            SectionType.ASSUMPTIONS: "- Assumption 1\n- Assumption 2\n- Assumption 3",
            SectionType.DEPENDENCIES: "- System dependencies\n- Data dependencies\n- External service dependencies",
            SectionType.ACCEPTANCE_CRITERIA: "- Acceptance criterion 1\n- Acceptance criterion 2\n- Testing requirements",
        }
        
        return placeholders.get(section_type, "- [To be completed]")
