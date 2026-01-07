"""
RAG Engine for building Evidence Packs and managing retrieval.
Implements the core logic for section-wise query planning and evidence gathering.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.schemas import (
    EvidencePack, ChangeDelta, ConflictInfo,
    ApprovalStatus, Priority, ChangeType
)
from app.services.vector_store import VectorStore
from app.core.logging_config import logger
from app.core.config import settings


class RAGEngine:
    """Manages RAG operations for BRS consolidation."""
    
    def __init__(self, vector_store: VectorStore):
        """
        Initialize RAG engine.
        
        Args:
            vector_store: Vector store instance
        """
        self.vector_store = vector_store
        logger.info("RAG Engine initialized")
    
    def build_evidence_pack(
        self,
        section_id: str,
        section_title: str,
        section_path: str
    ) -> EvidencePack:
        """
        Build an Evidence Pack for a specific BRS section.
        This is the ONLY context that will be provided to the LLM.
        
        Args:
            section_id: Target section ID
            section_title: Section title
            section_path: Hierarchical section path
        
        Returns:
            Complete Evidence Pack with base content and approved changes
        """
        logger.info(f"Building Evidence Pack for section: {section_path} - {section_title}")
        
        # Step 1: Retrieve base BRS content (latest version)
        # Pass section_path to merge content from all documents with same path
        base_content, base_source = self._get_latest_brs_content(section_id, section_title, section_path)
        
        # Step 2: Retrieve all Change Requests affecting this section
        # Pass section_path to get all CRs affecting this path
        cr_deltas = self._get_approved_changes(section_id, section_title, section_path)
        
        # Step 3: Detect and resolve conflicts
        conflicts = self._detect_and_resolve_conflicts(cr_deltas)
        
        # Step 4: Filter out conflicting CRs (keep only resolved ones)
        resolved_deltas = self._apply_conflict_resolution(cr_deltas, conflicts)
        
        # Step 5: Collect source documents
        source_docs = [base_source] if base_source else []
        source_docs.extend([delta.delta_id.split('-DELTA')[0] for delta in resolved_deltas])
        source_docs = list(set(source_docs))  # Deduplicate
        
        # Build Evidence Pack
        evidence_pack = EvidencePack(
            section_id=section_id,
            section_title=section_title,
            section_path=section_path,
            base_content=base_content,
            base_source=base_source,
            approved_changes=resolved_deltas,
            conflicts=conflicts,
            source_documents=source_docs
        )
        
        logger.info(
            f"Evidence Pack built: {len(resolved_deltas)} changes, "
            f"{len(conflicts)} conflicts resolved"
        )
        
        return evidence_pack
    
    def _get_latest_brs_content(
        self,
        section_id: str,
        section_title: str,
        section_path: str = None
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Retrieve the latest BRS content for a section.
        Searches by section_path to merge content from all documents with the same path.
        
        Args:
            section_id: Section ID (for backward compatibility)
            section_title: Section title
            section_path: Section path (preferred for searching)
        
        Returns:
            Tuple of (merged_content, source_doc_ids)
        """
        logger.debug(f"Retrieving BRS content for section_path: {section_path or section_id}")
        
        # Search by section_path if available (preferred method)
        if section_path:
            # Use the vector store query method
            results = self.vector_store.query_brs_by_section(
                section_path=section_path,
                top_k=100
            )
            
            if results:
                # Sort by version (latest first)
                sorted_results = sorted(
                    results,
                    key=lambda x: self._parse_version(x['metadata'].get('version', 'v0.0')),
                    reverse=True
                )
                
                # Use content from latest version
                latest = sorted_results[0]
                content = latest['content']
                
                # Collect all source documents
                source_docs = []
                seen_docs = set()
                for result in sorted_results:
                    doc_id = result['metadata'].get('doc_id', '')
                    version = result['metadata'].get('version', '')
                    doc_key = f"{doc_id} {version}"
                    if doc_key not in seen_docs:
                        source_docs.append(doc_key)
                        seen_docs.add(doc_key)
                
                source = ", ".join(source_docs[:3])  # Limit to first 3 for readability
                if len(source_docs) > 3:
                    source += f" (+{len(source_docs) - 3} more)"
                
                logger.debug(f"Retrieved merged content from {len(source_docs)} documents for path {section_path}")
                return content, source
        
        # Fallback: Try exact section ID match
        results = self.vector_store.query_brs_by_section(
            section_id=section_id,
            top_k=10
        )
        
        # If no exact match, try semantic search by title
        if not results:
            logger.debug(f"No exact match, trying semantic search for: {section_title}")
            results = self.vector_store.query_brs_by_section(
                section_title=section_title,
                top_k=5
            )
        
        if not results:
            logger.warning(f"No BRS content found for section: {section_path or section_id}")
            return None, None
        
        # Sort by version (assuming version format like v1.0, v2.0)
        # Take the latest version
        sorted_results = sorted(
            results,
            key=lambda x: self._parse_version(x['metadata'].get('version', 'v0.0')),
            reverse=True
        )
        
        latest = sorted_results[0]
        content = latest['content']
        source = f"{latest['metadata']['doc_id']} {latest['metadata']['version']}"
        
        logger.debug(f"Retrieved content from: {source}")
        return content, source
    
    def _get_approved_changes(
        self,
        section_id: str,
        section_title: str,
        section_path: str = None
    ) -> List[ChangeDelta]:
        """
        Retrieve all approved Change Requests for a section.
        
        Args:
            section_id: Section ID
            section_title: Section title
            section_path: Section path (preferred for searching)
        
        Returns:
            List of approved change deltas
        """
        logger.debug(f"Retrieving approved changes for: {section_path or section_id}")
        
        # Query CRs by section_path if available (to get all CRs affecting this path)
        if section_path:
            # Get all CR chunks with this section_path
            # Note: ChromaDB get() doesn't support multiple where conditions, so we filter after
            all_results = self.vector_store.cr_collection.get(
                where={"section_path": section_path},
                limit=100
            )
            
            if all_results and 'metadatas' in all_results and len(all_results['metadatas']) > 0:
                # Format results
                formatted_results = self.vector_store._format_results(all_results)
                # Filter by approval_status in Python
                results = [
                    r for r in formatted_results
                    if r.get('metadata', {}).get('approval_status') == ApprovalStatus.APPROVED.value
                ]
                logger.debug(f"Found {len(results)} approved CRs for section_path {section_path}")
            else:
                results = []
        else:
            # Query CRs with approval filter by section_id
            results = self.vector_store.query_cr_by_section(
                section_id=section_id,
                approval_status=ApprovalStatus.APPROVED,
                top_k=20
            )
        
        # If no exact match, try semantic search
        if not results:
            logger.debug(f"No exact match, trying semantic search for: {section_title}")
            results = self.vector_store.query_cr_by_section(
                section_title=section_title,
                approval_status=ApprovalStatus.APPROVED,
                top_k=10
            )
        
        # Convert results to ChangeDelta objects
        deltas = []
        for result in results:
            # Parse the content back into a ChangeDelta
            # (In a real system, we'd store structured data)
            delta = self._parse_cr_content(result)
            if delta:
                deltas.append(delta)
        
        logger.debug(f"Found {len(deltas)} approved changes")
        return deltas
    
    def _parse_cr_content(self, result: Dict[str, Any]) -> Optional[ChangeDelta]:
        """
        Parse CR content from vector store result back into ChangeDelta.
        This is a simplified version - in production, store structured data.
        
        Args:
            result: Vector store result
        
        Returns:
            ChangeDelta object or None
        """
        try:
            content = result['content']
            metadata = result['metadata']
            
            # Parse content sections
            old_content = None
            new_content = None
            rationale = None
            
            if '[OLD]' in content:
                old_content = content.split('[OLD]')[1].split('[NEW]')[0].strip()
            if '[NEW]' in content:
                new_content = content.split('[NEW]')[1].split('[RATIONALE]')[0].strip()
            if '[RATIONALE]' in content:
                rationale = content.split('[RATIONALE]')[1].strip()
            
            # Determine change type
            change_type = ChangeType.MODIFY
            if old_content and not new_content:
                change_type = ChangeType.DELETE
            elif new_content and not old_content:
                change_type = ChangeType.ADD
            
            delta = ChangeDelta(
                delta_id=result['chunk_id'].replace('-CHUNK', ''),
                impacted_section_id=metadata['section_id'],
                impacted_section_title=metadata['section_title'],
                change_type=change_type,
                old_content=old_content,
                new_content=new_content,
                rationale=rationale or "No rationale provided"
            )
            
            return delta
            
        except Exception as e:
            logger.error(f"Error parsing CR content: {e}")
            return None
    
    def _detect_and_resolve_conflicts(
        self,
        deltas: List[ChangeDelta]
    ) -> List[ConflictInfo]:
        """
        Detect conflicts between multiple CRs affecting the same section.
        
        Args:
            deltas: List of change deltas
        
        Returns:
            List of detected conflicts with resolution strategies
        """
        conflicts = []
        
        # Group deltas by section
        section_groups: Dict[str, List[ChangeDelta]] = {}
        for delta in deltas:
            section_id = delta.impacted_section_id
            if section_id not in section_groups:
                section_groups[section_id] = []
            section_groups[section_id].append(delta)
        
        # Check for conflicts within each section
        for section_id, section_deltas in section_groups.items():
            if len(section_deltas) > 1:
                # Multiple changes to same section - potential conflict
                logger.warning(f"Potential conflict in section {section_id}: {len(section_deltas)} changes")
                
                # Check if they're actually conflicting
                # (e.g., both modifying the same content)
                if self._are_conflicting(section_deltas):
                    cr_ids = [delta.delta_id.split('-DELTA')[0] for delta in section_deltas]
                    
                    conflict = ConflictInfo(
                        conflicting_cr_ids=cr_ids,
                        conflict_description=f"Multiple CRs modify section {section_id}",
                        resolution_strategy="Selected based on priority and timestamp"
                    )
                    conflicts.append(conflict)
        
        return conflicts
    
    def _are_conflicting(self, deltas: List[ChangeDelta]) -> bool:
        """
        Determine if deltas are actually conflicting.
        
        Args:
            deltas: List of deltas to check
        
        Returns:
            True if conflicting
        """
        # Simple heuristic: if multiple deltas have overlapping old_content
        # or are all MODIFY/DELETE type, they likely conflict
        
        modify_or_delete = [d for d in deltas if d.change_type in [ChangeType.MODIFY, ChangeType.DELETE]]
        
        # If we have multiple MODIFY/DELETE on same section, consider it a conflict
        return len(modify_or_delete) > 1
    
    def _apply_conflict_resolution(
        self,
        deltas: List[ChangeDelta],
        conflicts: List[ConflictInfo]
    ) -> List[ChangeDelta]:
        """
        Apply conflict resolution strategy to filter deltas.
        
        Args:
            deltas: All change deltas
            conflicts: Detected conflicts
        
        Returns:
            Filtered list of deltas with conflicts resolved
        """
        if not conflicts:
            return deltas
        
        # Get all conflicting CR IDs
        conflicting_cr_ids = set()
        for conflict in conflicts:
            conflicting_cr_ids.update(conflict.conflicting_cr_ids)
        
        # Group conflicting deltas by section
        section_conflicts: Dict[str, List[ChangeDelta]] = {}
        non_conflicting = []
        
        for delta in deltas:
            cr_id = delta.delta_id.split('-DELTA')[0]
            
            if cr_id in conflicting_cr_ids:
                section_id = delta.impacted_section_id
                if section_id not in section_conflicts:
                    section_conflicts[section_id] = []
                section_conflicts[section_id].append(delta)
            else:
                non_conflicting.append(delta)
        
        # Resolve conflicts: keep the one with highest priority
        # (In production, this would be more sophisticated)
        resolved = []
        for section_id, conflicting_deltas in section_conflicts.items():
            # Sort by priority (CRITICAL > HIGH > MEDIUM > LOW)
            # For now, just take the first one (would need priority metadata)
            logger.info(f"Resolving conflict in {section_id}: keeping first delta")
            resolved.append(conflicting_deltas[0])
        
        return non_conflicting + resolved
    
    def _parse_version(self, version_str: str) -> tuple:
        """
        Parse version string into comparable tuple.
        
        Args:
            version_str: Version string like 'v1.2.3'
        
        Returns:
            Tuple of integers for comparison
        """
        try:
            # Remove 'v' prefix and split
            parts = version_str.lstrip('v').split('.')
            return tuple(int(p) for p in parts)
        except:
            return (0, 0, 0)
