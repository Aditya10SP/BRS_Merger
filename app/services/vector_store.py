"""
Vector store service for managing embeddings and retrieval.
Provides a unified interface for ChromaDB operations.
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from app.models.schemas import SemanticChunk, ChunkMetadata, DocumentType, ApprovalStatus
from app.core.config import settings
from app.core.logging_config import logger


class VectorStore:
    """Manages vector storage and retrieval using ChromaDB."""
    
    def __init__(self):
        """Initialize the vector store with ChromaDB."""
        logger.info("Initializing VectorStore with ChromaDB")
        
        # Create persist directory if it doesn't exist
        persist_dir = Path(settings.CHROMA_PERSIST_DIR)
        persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        
        # Get or create collections
        self.brs_collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_BRS,
            metadata={"description": "BRS document chunks"}
        )
        
        self.cr_collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_CR,
            metadata={"description": "Change Request deltas"}
        )
        
        logger.info("VectorStore initialized successfully")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector
        """
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def add_brs_chunks(self, chunks: List[SemanticChunk]) -> None:
        """
        Add BRS chunks to the vector store.
        Handles duplicate IDs by checking existing chunks first.
        
        Args:
            chunks: List of semantic chunks from BRS documents
        """
        if not chunks:
            logger.warning("No chunks to add")
            return
        
        logger.info(f"Adding {len(chunks)} BRS chunks to vector store")
        
        ids = []
        documents = []
        embeddings = []
        metadatas = []
        
        # Check for existing chunks to avoid duplicates
        chunk_ids = [chunk.metadata.chunk_id for chunk in chunks]
        existing_chunks = set()
        
        try:
            existing = self.brs_collection.get(ids=chunk_ids)
            if existing and 'ids' in existing:
                existing_chunks = set(existing['ids'])
                logger.info(f"Found {len(existing_chunks)} existing chunks, will update them")
        except Exception as e:
            logger.debug(f"No existing chunks found (or error checking): {e}")
        
        for chunk in chunks:
            # Generate embedding if not present
            if chunk.embedding is None:
                chunk.embedding = self.generate_embedding(chunk.content)
            
            chunk_id = chunk.metadata.chunk_id
            
            # Convert metadata to dict
            metadata_dict = {
                "doc_id": chunk.metadata.doc_id,
                "doc_type": chunk.metadata.doc_type.value,
                "version": chunk.metadata.version,
                "section_id": chunk.metadata.section_id,
                "section_title": chunk.metadata.section_title,
                "section_path": chunk.metadata.section_path
            }
            
            # If chunk exists, update it; otherwise add to new list
            if chunk_id in existing_chunks:
                # Update existing chunk
                try:
                    self.brs_collection.update(
                        ids=[chunk_id],
                        documents=[chunk.content],
                        embeddings=[chunk.embedding],
                        metadatas=[metadata_dict]
                    )
                    logger.debug(f"Updated existing chunk: {chunk_id}")
                except Exception as e:
                    logger.warning(f"Failed to update chunk {chunk_id}: {e}, will try to add")
                    # Fall through to add
                    ids.append(chunk_id)
                    documents.append(chunk.content)
                    embeddings.append(chunk.embedding)
                    metadatas.append(metadata_dict)
            else:
                # New chunk
                ids.append(chunk_id)
                documents.append(chunk.content)
                embeddings.append(chunk.embedding)
                metadatas.append(metadata_dict)
        
        # Add new chunks (if any)
        if ids:
            try:
                self.brs_collection.add(
                    ids=ids,
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas
                )
                logger.info(f"Successfully added {len(ids)} new BRS chunks")
            except Exception as e:
                # If still getting duplicate error, make IDs unique
                if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                    logger.warning(f"Duplicate IDs detected, making them unique: {e}")
                    import uuid
                    unique_ids = [f"{chunk_id}-{uuid.uuid4().hex[:8]}" for chunk_id in ids]
                    self.brs_collection.add(
                        ids=unique_ids,
                        documents=documents,
                        embeddings=embeddings,
                        metadatas=metadatas
                    )
                    logger.info(f"Added {len(ids)} chunks with unique IDs")
                else:
                    raise
        
        logger.info(f"Successfully processed {len(chunks)} BRS chunks ({len(ids)} new, {len(existing_chunks)} updated)")
    
    def add_cr_chunks(self, chunks: List[SemanticChunk]) -> None:
        """
        Add Change Request chunks to the vector store.
        Handles duplicate IDs by checking existing chunks first.
        
        Args:
            chunks: List of semantic chunks from Change Requests
        """
        if not chunks:
            logger.warning("No chunks to add")
            return
        
        logger.info(f"Adding {len(chunks)} CR chunks to vector store")
        
        ids = []
        documents = []
        embeddings = []
        metadatas = []
        
        # Check for existing chunks to avoid duplicates
        chunk_ids = [chunk.metadata.chunk_id for chunk in chunks]
        existing_chunks = set()
        
        try:
            existing = self.cr_collection.get(ids=chunk_ids)
            if existing and 'ids' in existing:
                existing_chunks = set(existing['ids'])
                logger.info(f"Found {len(existing_chunks)} existing CR chunks, will update them")
        except Exception as e:
            logger.debug(f"No existing CR chunks found (or error checking): {e}")
        
        for chunk in chunks:
            # Generate embedding if not present
            if chunk.embedding is None:
                chunk.embedding = self.generate_embedding(chunk.content)
            
            chunk_id = chunk.metadata.chunk_id
            
            # Convert metadata to dict
            metadata_dict = {
                "doc_id": chunk.metadata.doc_id,
                "doc_type": chunk.metadata.doc_type.value,
                "section_id": chunk.metadata.section_id,
                "section_title": chunk.metadata.section_title,
                "section_path": chunk.metadata.section_path,
                "approval_status": chunk.metadata.approval_status.value if chunk.metadata.approval_status else None,
                "priority": chunk.metadata.priority.value if chunk.metadata.priority else None
            }
            
            # If chunk exists, update it; otherwise add to new list
            if chunk_id in existing_chunks:
                # Update existing chunk
                try:
                    self.cr_collection.update(
                        ids=[chunk_id],
                        documents=[chunk.content],
                        embeddings=[chunk.embedding],
                        metadatas=[metadata_dict]
                    )
                    logger.debug(f"Updated existing CR chunk: {chunk_id}")
                except Exception as e:
                    logger.warning(f"Failed to update CR chunk {chunk_id}: {e}, will try to add")
                    # Fall through to add
                    ids.append(chunk_id)
                    documents.append(chunk.content)
                    embeddings.append(chunk.embedding)
                    metadatas.append(metadata_dict)
            else:
                # New chunk
                ids.append(chunk_id)
                documents.append(chunk.content)
                embeddings.append(chunk.embedding)
                metadatas.append(metadata_dict)
        
        # Add new chunks (if any)
        if ids:
            try:
                self.cr_collection.add(
                    ids=ids,
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas
                )
                logger.info(f"Successfully added {len(ids)} new CR chunks")
            except Exception as e:
                # If still getting duplicate error, make IDs unique
                if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                    logger.warning(f"Duplicate IDs detected, making them unique: {e}")
                    import uuid
                    unique_ids = [f"{chunk_id}-{uuid.uuid4().hex[:8]}" for chunk_id in ids]
                    self.cr_collection.add(
                        ids=unique_ids,
                        documents=documents,
                        embeddings=embeddings,
                        metadatas=metadatas
                    )
                    logger.info(f"Added {len(ids)} CR chunks with unique IDs")
                else:
                    raise
        
        logger.info(f"Successfully processed {len(chunks)} CR chunks ({len(ids)} new, {len(existing_chunks)} updated)")
    
    def query_brs_by_section(
        self,
        section_id: str = None,
        section_title: str = None,
        section_path: str = None,
        version: str = None,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Query BRS chunks by section metadata.
        
        Args:
            section_id: Section ID to filter by
            section_title: Section title to search for
            section_path: Section path to filter by (preferred for merging)
            version: Document version to filter by
            top_k: Number of results to return
        
        Returns:
            List of matching chunks with metadata
        """
        top_k = top_k or settings.TOP_K_RETRIEVAL
        
        # Build where clause (ChromaDB get() supports only single condition)
        # Prioritize section_path > section_id, then filter version in Python if needed
        where_clause = None
        filter_by_version = False
        
        if section_path:
            where_clause = {"section_path": section_path}
            if version:
                filter_by_version = True
        elif section_id:
            where_clause = {"section_id": section_id}
            if version:
                filter_by_version = True
        elif version:
            where_clause = {"version": version}
        
        # If we have a where clause, use get() for exact match
        if where_clause:
            logger.info(f"Querying BRS chunks with filters: {where_clause}")
            results = self.brs_collection.get(
                where=where_clause,
                limit=top_k * 10 if section_path else top_k  # Get more results when merging by path
            )
            
            # Filter by version in Python if needed (ChromaDB limitation)
            if filter_by_version and results and 'metadatas' in results:
                filtered_metadatas = []
                filtered_ids = []
                filtered_documents = []
                filtered_embeddings = []
                
                for idx, metadata in enumerate(results.get('metadatas', [])):
                    if metadata.get('version') == version:
                        filtered_metadatas.append(metadata)
                        if 'ids' in results:
                            filtered_ids.append(results['ids'][idx])
                        if 'documents' in results:
                            filtered_documents.append(results['documents'][idx])
                        if 'embeddings' in results:
                            filtered_embeddings.append(results['embeddings'][idx])
                
                # Reconstruct results dict
                results = {
                    'ids': filtered_ids,
                    'metadatas': filtered_metadatas,
                    'documents': filtered_documents
                }
                if filtered_embeddings:
                    results['embeddings'] = filtered_embeddings
        # Otherwise use semantic search with section title
        elif section_title:
            logger.info(f"Semantic search for section: {section_title}")
            query_embedding = self.generate_embedding(section_title)
            results = self.brs_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
        else:
            logger.warning("No search criteria provided")
            return []
        
        return self._format_results(results)
    
    def query_cr_by_section(
        self,
        section_id: str = None,
        section_title: str = None,
        section_path: str = None,
        approval_status: ApprovalStatus = None,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Query Change Request chunks by section.
        
        Args:
            section_id: Section ID to filter by
            section_title: Section title to search for
            section_path: Section path to filter by (preferred for merging)
            approval_status: Filter by approval status
            top_k: Number of results to return
        
        Returns:
            List of matching CR chunks
        """
        top_k = top_k or settings.TOP_K_RETRIEVAL
        
        # Query by section_path first (preferred for merging sections)
        if section_path:
            logger.info(f"Querying CR chunks for section_path: {section_path}")
            # ChromaDB get() doesn't support multiple where conditions, so filter after
            results = self.cr_collection.get(
                where={"section_path": section_path},
                limit=top_k * 10  # Get more results when merging
            )
            formatted = self._format_results(results)
            
            # Post-filter by approval_status if specified
            if approval_status:
                formatted = [
                    r for r in formatted 
                    if r.get('metadata', {}).get('approval_status') == approval_status.value
                ]
            
            return formatted[:top_k] if top_k else formatted
        
        # Query by section_id (fallback)
        elif section_id:
            logger.info(f"Querying CR chunks for section: {section_id}")
            # Use semantic search with section filter
            query_text = section_title if section_title else section_id
            query_embedding = self.generate_embedding(query_text)
            results = self.cr_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k * 3,  # Get more results for post-filtering
                where={"section_id": section_id}
            )
            formatted = self._format_results(results)
            
            # Post-filter by approval_status if specified
            if approval_status:
                formatted = [
                    r for r in formatted 
                    if r.get('metadata', {}).get('approval_status') == approval_status.value
                ]
            
            return formatted[:top_k]
            
        elif section_title:
            logger.info(f"Semantic search for CRs affecting: {section_title}")
            query_embedding = self.generate_embedding(section_title)
            
            # Apply approval filter if specified
            where = {"approval_status": approval_status.value} if approval_status else None
            
            results = self.cr_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where
            )
            return self._format_results(results)
            
        elif approval_status:
            logger.info(f"Querying CRs by approval status: {approval_status.value}")
            query_embedding = self.generate_embedding("change request")
            results = self.cr_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where={"approval_status": approval_status.value}
            )
            return self._format_results(results)
        else:
            logger.warning("No search criteria provided")
            return []
    
    def hybrid_search(
        self,
        query_text: str,
        doc_type: DocumentType = None,
        section_id: str = None,
        approval_status: ApprovalStatus = None,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic similarity and metadata filtering.
        
        Args:
            query_text: Text query for semantic search
            doc_type: Filter by document type
            section_id: Filter by section ID
            approval_status: Filter by approval status (for CRs)
            top_k: Number of results
        
        Returns:
            List of matching chunks
        """
        top_k = top_k or settings.TOP_K_RETRIEVAL
        
        logger.info(f"Hybrid search: '{query_text}' with filters")
        
        # Generate query embedding
        query_embedding = self.generate_embedding(query_text)
        
        # Build where clause
        where_clause = {}
        if section_id:
            where_clause["section_id"] = section_id
        if approval_status:
            where_clause["approval_status"] = approval_status.value
        
        # Choose collection based on doc_type
        if doc_type == DocumentType.BRS:
            collection = self.brs_collection
        elif doc_type == DocumentType.CHANGE_REQUEST:
            collection = self.cr_collection
        else:
            # Search both collections and merge results
            brs_results = self.brs_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k // 2,
                where=where_clause if where_clause else None
            )
            cr_results = self.cr_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k // 2,
                where=where_clause if where_clause else None
            )
            
            # Merge and return
            all_results = self._format_results(brs_results) + self._format_results(cr_results)
            return sorted(all_results, key=lambda x: x.get('distance', 0))[:top_k]
        
        # Single collection search
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause if where_clause else None
        )
        
        return self._format_results(results)
    
    def _format_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Format ChromaDB results into a consistent structure.
        
        Args:
            results: Raw results from ChromaDB
        
        Returns:
            Formatted results list
        """
        formatted = []
        
        # Handle both query() and get() result formats
        if 'ids' in results:
            ids = results['ids'][0] if isinstance(results['ids'][0], list) else results['ids']
            documents = results['documents'][0] if isinstance(results['documents'][0], list) else results['documents']
            metadatas = results['metadatas'][0] if isinstance(results['metadatas'][0], list) else results['metadatas']
            distances = results.get('distances', [[]] * len(ids))[0] if 'distances' in results else [None] * len(ids)
            
            for idx, chunk_id in enumerate(ids):
                formatted.append({
                    'chunk_id': chunk_id,
                    'content': documents[idx],
                    'metadata': metadatas[idx],
                    'distance': distances[idx] if distances else None
                })
        
        return formatted
    
    def reset(self) -> None:
        """Reset all collections (use with caution!)."""
        logger.warning("Resetting all vector store collections")
        self.client.reset()
        
        # Recreate collections
        self.brs_collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_BRS
        )
        self.cr_collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_CR
        )
        
        logger.info("Vector store reset complete")
    
    def clear_all(self) -> None:
        """Clear all data from vector store collections."""
        logger.info("Clearing all vector store data...")
        
        # Delete all items from BRS collection
        brs_count = self.brs_collection.count()
        if brs_count > 0:
            all_brs = self.brs_collection.get()
            if all_brs and 'ids' in all_brs and all_brs['ids']:
                self.brs_collection.delete(ids=all_brs['ids'])
                logger.info(f"Deleted {brs_count} BRS chunks")
        
        # Delete all items from CR collection
        cr_count = self.cr_collection.count()
        if cr_count > 0:
            all_cr = self.cr_collection.get()
            if all_cr and 'ids' in all_cr and all_cr['ids']:
                self.cr_collection.delete(ids=all_cr['ids'])
                logger.info(f"Deleted {cr_count} CR chunks")
        
        logger.info("Vector store cleared successfully")
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about the vector store."""
        return {
            "brs_chunks": self.brs_collection.count(),
            "cr_chunks": self.cr_collection.count(),
            "total_chunks": self.brs_collection.count() + self.cr_collection.count()
        }
