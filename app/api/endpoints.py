"""
FastAPI endpoints for the BRS Consolidator system.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import List, Optional
from pathlib import Path
import shutil
import uuid
from datetime import datetime

from app.models.schemas import (
    BRSDocument, ChangeRequest, FinalBRS,
    Priority, ApprovalStatus
)
from app.services.orchestrator import BRSOrchestrator
from app.core.logging_config import logger
from app.core.config import settings
from pydantic import BaseModel


router = APIRouter()

# Global orchestrator instance
orchestrator = BRSOrchestrator()

# In-memory job tracking (in production, use Redis or database)
jobs = {}


class JobStatus(BaseModel):
    """Job status response."""
    job_id: str
    status: str  # pending, processing, completed, failed
    message: str
    progress: float = 0.0
    result: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class ConsolidationRequest(BaseModel):
    """Request to consolidate BRS."""
    brs_id: str
    title: str
    version: str
    section_outline: Optional[List[dict]] = None


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "GenAI BRS Consolidator",
        "version": "1.0.0",
        "status": "operational"
    }


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    stats = orchestrator.get_stats()
    return {
        "status": "healthy",
        "stats": stats
    }


@router.post("/upload/brs")
async def upload_brs(
    file: UploadFile = File(...),
    doc_id: Optional[str] = None,
    version: Optional[str] = None
):
    """
    Upload and process a BRS document.
    
    Args:
        file: BRS file (PDF or DOCX)
        doc_id: Optional document ID
        version: Optional version string
    
    Returns:
        Parsed BRS document metadata
    """
    logger.info(f"Received BRS upload: {file.filename}")
    
    # Validate file type
    if not file.filename.endswith(('.pdf', '.docx', '.doc')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF and DOCX files are supported."
        )
    
    try:
        # Save uploaded file
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / f"{uuid.uuid4().hex}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process document
        brs_doc = orchestrator.process_brs_document(
            file_path=file_path,
            doc_id=doc_id,
            version=version
        )
        
        return {
            "status": "success",
            "message": "BRS document processed successfully",
            "document": {
                "doc_id": brs_doc.metadata.doc_id,
                "version": brs_doc.metadata.version,
                "sections": len(brs_doc.sections),
                "source_file": brs_doc.metadata.source_file
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing BRS upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/cr")
async def upload_change_request(
    file: UploadFile = File(...),
    cr_id: Optional[str] = None,
    priority: Priority = Priority.MEDIUM,
    approval_status: ApprovalStatus = ApprovalStatus.APPROVED
):
    """
    Upload and process a Change Request.
    
    Args:
        file: CR file (PDF or DOCX)
        cr_id: Optional CR ID
        priority: Priority level
        approval_status: Approval status
    
    Returns:
        Parsed CR metadata
    """
    logger.info(f"Received CR upload: {file.filename}")
    
    # Validate file type
    if not file.filename.endswith(('.pdf', '.docx', '.doc')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF and DOCX files are supported."
        )
    
    try:
        # Save uploaded file
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / f"{uuid.uuid4().hex}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process CR
        cr = orchestrator.process_change_request(
            file_path=file_path,
            cr_id=cr_id,
            priority=priority,
            approval_status=approval_status
        )
        
        return {
            "status": "success",
            "message": "Change Request processed successfully",
            "change_request": {
                "cr_id": cr.cr_id,
                "title": cr.title,
                "priority": cr.priority.value,
                "approval_status": cr.approval_status.value,
                "deltas": len(cr.deltas)
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing CR upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/consolidate")
async def consolidate_brs(
    request: ConsolidationRequest,
    background_tasks: BackgroundTasks
):
    """
    Start BRS consolidation process.
    
    Args:
        request: Consolidation request parameters
        background_tasks: FastAPI background tasks
    
    Returns:
        Job ID for tracking
    """
    logger.info(f"Starting consolidation: {request.brs_id}")
    
    # Create job
    job_id = str(uuid.uuid4())
    
    jobs[job_id] = JobStatus(
        job_id=job_id,
        status="pending",
        message="Consolidation job queued",
        progress=0.0,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Start background task
    background_tasks.add_task(
        _consolidate_brs_task,
        job_id=job_id,
        request=request
    )
    
    return {
        "status": "success",
        "message": "Consolidation started",
        "job_id": job_id
    }


async def _consolidate_brs_task(job_id: str, request: ConsolidationRequest):
    """Background task for BRS consolidation."""
    try:
        # Update job status
        jobs[job_id].status = "processing"
        jobs[job_id].message = "Generating consolidated BRS..."
        jobs[job_id].updated_at = datetime.now()
        
        # Define progress callback
        def update_progress(current: int, total: int, message: str = None):
            if job_id in jobs:
                if total > 0:
                    jobs[job_id].progress = min(100.0, (current / total) * 100)
                if message:
                    jobs[job_id].message = message
                jobs[job_id].updated_at = datetime.now()

        # Run consolidation
        final_brs = orchestrator.consolidate_brs(
            brs_id=request.brs_id,
            title=request.title,
            version=request.version,
            section_outline=request.section_outline,
            progress_callback=update_progress
        )
        
        # Export to files
        output_dir = Path(settings.OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        json_path = output_dir / f"{request.brs_id}.json"
        md_path = output_dir / f"{request.brs_id}.md"
        pdf_path = output_dir / f"{request.brs_id}.pdf"
        
        orchestrator.export_to_json(final_brs, json_path)
        orchestrator.export_to_markdown(final_brs, md_path)
        orchestrator.export_to_pdf(final_brs, pdf_path)
        
        # Update job status
        jobs[job_id].status = "completed"
        jobs[job_id].message = "Consolidation completed successfully"
        jobs[job_id].progress = 100.0
        jobs[job_id].result = {
            "brs_id": final_brs.brs_id,
            "version": final_brs.version,
            "sections": len(final_brs.sections),
            "validation_passed": final_brs.validation_passed,
            "json_output": f"/api/v1/download/{request.brs_id}.json",
            "markdown_output": f"/api/v1/download/{request.brs_id}.md",
            "pdf_output": f"/api/v1/download/{request.brs_id}.pdf"
        }
        jobs[job_id].updated_at = datetime.now()
        
        logger.info(f"Consolidation job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Consolidation job {job_id} failed: {e}")
        jobs[job_id].status = "failed"
        jobs[job_id].message = f"Consolidation failed: {str(e)}"
        jobs[job_id].updated_at = datetime.now()


@router.get("/job/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """
    Get status of a consolidation job.
    
    Args:
        job_id: Job identifier
    
    Returns:
        Job status
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]


@router.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download a generated file.
    
    Args:
        filename: Name of the file to download
    
    Returns:
        File response
    """
    from fastapi.responses import FileResponse
    
    file_path = Path(settings.OUTPUT_DIR) / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type
    media_type = "application/octet-stream"
    if filename.endswith(".pdf"):
        media_type = "application/pdf"
    elif filename.endswith(".json"):
        media_type = "application/json"
    elif filename.endswith(".md"):
        media_type = "text/markdown"
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type
    )


@router.get("/stats")
async def get_stats():
    """Get system statistics."""
    return orchestrator.get_stats()


@router.delete("/reset")
async def reset_vector_store():
    """
    Reset the vector store (use with caution!).
    
    Returns:
        Confirmation message
    """
    logger.warning("Resetting vector store")
    orchestrator.vector_store.reset()
    
    return {
        "status": "success",
        "message": "Vector store reset successfully"
    }
