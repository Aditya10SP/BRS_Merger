"""
Prompt templates for LLM-based generation and validation.
These templates enforce strict constraints to prevent hallucination.
"""

# ============================================================================
# SECTION GENERATION PROMPT
# ============================================================================

SECTION_GENERATION_PROMPT = """You are a Business Requirements Specification (BRS) Writer.

Your task is to generate EXACTLY ONE section of a BRS document based on the provided evidence.

**CRITICAL RULES:**
1. You MUST ONLY use information from the Evidence Pack provided below
2. You MUST NOT add new requirements or information not present in the evidence
3. You MUST NOT infer or assume anything beyond what is explicitly stated
4. If information is missing or unclear, write "Not Specified" or "To Be Determined"
5. Maintain professional, clear, and concise technical writing style
6. Use present tense and active voice where possible
7. Number requirements clearly if applicable

**EVIDENCE PACK:**

Section ID: {section_id}
Section Title: {section_title}
Section Path: {section_path}

**BASE CONTENT (from latest BRS version):**
{base_content}

**APPROVED CHANGES:**
{approved_changes}

**CONFLICT NOTES:**
{conflict_notes}

**YOUR TASK:**
Generate the final version of this section by:
1. Starting with the base content
2. Applying each approved change in order
3. Ensuring no contradictions remain
4. Maintaining requirement traceability

**OUTPUT FORMAT:**
Provide ONLY the section content. Do not include the section number or title (they will be added automatically).
Do not add any preamble or explanation.

Begin your response with the section content:
"""

# ============================================================================
# CONFLICT RESOLUTION PROMPT
# ============================================================================

CONFLICT_RESOLUTION_PROMPT = """You are a BRS Conflict Resolution Specialist.

Multiple Change Requests (CRs) are attempting to modify the same section with potentially conflicting changes.

**RESOLUTION RULES (in priority order):**
1. CRITICAL priority overrides all others
2. If same priority, APPROVED status takes precedence
3. If same priority and status, use the most recent timestamp
4. If still tied, flag for human review

**CONFLICTING CHANGES:**
{conflicting_changes}

**YOUR TASK:**
Analyze the conflicts and determine which change should be applied.

**OUTPUT FORMAT:**
Provide a JSON response with:
{{
  "selected_cr_id": "CR-XXX",
  "rationale": "Brief explanation of why this CR was selected",
  "requires_human_review": false
}}

Response:
"""

# ============================================================================
# VALIDATION PROMPT
# ============================================================================

VALIDATION_PROMPT = """You are a BRS Quality Assurance Auditor.

Your task is to validate a generated BRS section for quality, completeness, and compliance.

**VALIDATION CRITERIA:**
1. **Traceability**: All content must be traceable to source documents
2. **Completeness**: No critical information should be marked "Not Specified" without justification
3. **Consistency**: No internal contradictions
4. **Clarity**: Requirements are clear and unambiguous
5. **No Hallucination**: No information added beyond the evidence pack

**GENERATED SECTION:**
{generated_content}

**EVIDENCE PACK (for reference):**
Base Source: {base_source}
Applied Changes: {applied_changes}
Source Documents: {source_documents}

**YOUR TASK:**
Validate the generated section against the criteria above.

**OUTPUT FORMAT:**
Provide a JSON response with:
{{
  "validation_passed": true/false,
  "issues": [
    {{
      "severity": "critical/warning/info",
      "category": "traceability/completeness/consistency/clarity/hallucination",
      "description": "Detailed description of the issue",
      "location": "Where in the section the issue occurs"
    }}
  ],
  "recommendations": ["List of recommendations for improvement"],
  "overall_score": 0-100
}}

Response:
"""

# ============================================================================
# DEDUPLICATION PROMPT
# ============================================================================

DEDUPLICATION_PROMPT = """You are a BRS Deduplication Specialist.

Your task is to identify semantically duplicate or highly similar requirements.

**REQUIREMENTS TO ANALYZE:**
{requirements}

**YOUR TASK:**
Identify any duplicate or redundant requirements.

**RULES:**
1. Two requirements are duplicates if they express the same functionality
2. Consider semantic similarity, not just exact text matches
3. Preserve the most recent and complete version
4. Note the source of each requirement

**OUTPUT FORMAT:**
Provide a JSON response with:
{{
  "duplicates": [
    {{
      "group_id": 1,
      "requirement_ids": ["REQ-001", "REQ-005"],
      "similarity_score": 0.95,
      "recommended_keep": "REQ-005",
      "rationale": "REQ-005 is more recent and detailed"
    }}
  ],
  "unique_requirements": ["REQ-002", "REQ-003", "REQ-004"]
}}

Response:
"""

# ============================================================================
# SECTION OUTLINE GENERATION PROMPT
# ============================================================================

SECTION_OUTLINE_PROMPT = """You are a BRS Structure Analyzer.

Given multiple BRS documents, generate a unified section outline that covers all sections from all documents.

**BRS DOCUMENTS:**
{brs_documents}

**YOUR TASK:**
Create a comprehensive section outline that includes all unique sections from all BRS documents.

**RULES:**
1. Merge sections with the same or very similar titles
2. Maintain hierarchical structure (1, 1.1, 1.1.1, etc.)
3. Use standard BRS section names where applicable
4. Preserve all unique sections

**OUTPUT FORMAT:**
Provide a JSON response with:
{{
  "outline": [
    {{
      "section_path": "1",
      "section_title": "Introduction",
      "subsections": [
        {{
          "section_path": "1.1",
          "section_title": "Purpose",
          "subsections": []
        }}
      ]
    }}
  ]
}}

Response:
"""


def format_section_generation_prompt(
    section_id: str,
    section_title: str,
    section_path: str,
    base_content: str,
    approved_changes: list,
    conflict_notes: list
) -> str:
    """
    Format the section generation prompt with evidence pack data.
    
    Args:
        section_id: Section identifier
        section_title: Section title
        section_path: Hierarchical path
        base_content: Base BRS content
        approved_changes: List of approved change deltas
        conflict_notes: List of conflict information
    
    Returns:
        Formatted prompt string
    """
    # Format approved changes
    changes_text = ""
    if approved_changes:
        for idx, change in enumerate(approved_changes, 1):
            changes_text += f"\n--- Change {idx} (from {change.delta_id}) ---\n"
            changes_text += f"Type: {change.change_type.value.upper()}\n"
            if change.old_content:
                changes_text += f"Old: {change.old_content}\n"
            if change.new_content:
                changes_text += f"New: {change.new_content}\n"
            changes_text += f"Rationale: {change.rationale}\n"
    else:
        changes_text = "No approved changes for this section."
    
    # Format conflict notes
    conflicts_text = ""
    if conflict_notes:
        for idx, conflict in enumerate(conflict_notes, 1):
            conflicts_text += f"\n--- Conflict {idx} ---\n"
            conflicts_text += f"Conflicting CRs: {', '.join(conflict.conflicting_cr_ids)}\n"
            conflicts_text += f"Description: {conflict.conflict_description}\n"
            conflicts_text += f"Resolution: {conflict.resolution_strategy}\n"
    else:
        conflicts_text = "No conflicts detected."
    
    return SECTION_GENERATION_PROMPT.format(
        section_id=section_id,
        section_title=section_title,
        section_path=section_path,
        base_content=base_content or "No base content available. This is a new section.",
        approved_changes=changes_text,
        conflict_notes=conflicts_text
    )


def format_validation_prompt(
    generated_content: str,
    base_source: str,
    applied_changes: list,
    source_documents: list
) -> str:
    """
    Format the validation prompt.
    
    Args:
        generated_content: The generated section content
        base_source: Base BRS source
        applied_changes: List of applied CR IDs
        source_documents: List of all source document IDs
    
    Returns:
        Formatted prompt string
    """
    return VALIDATION_PROMPT.format(
        generated_content=generated_content,
        base_source=base_source or "None",
        applied_changes=", ".join(applied_changes) if applied_changes else "None",
        source_documents=", ".join(source_documents) if source_documents else "None"
    )
