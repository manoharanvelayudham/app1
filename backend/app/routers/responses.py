import logging
import pytz
import os
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import (
    ParticipantResponse,
    Enrollment,
    ResponseStatus,
    AuditAction,
    create_audit_log,
    User,
    AIProcessing,
    AIProcessingStatus,
)
from auth import get_current_user
from schemas.responses import (
    AutoSaveRequest,
    AutoSaveResponse,
    StatusUpdateRequest,
    StatusUpdateResponse,
    ResponseStatusInfo,
    AuditLogResponse,
    AutoSaveStats,
    ParticipantResponseDetail,
)
from services.audit_service import AuditService
from services.ai_pipeline import AIProcessingPipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/responses", tags=["responses"])

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key")

# ------------------------- Utility Functions --------------------------------
def _require_response_access(db: Session, response_id: int, user: User) -> ParticipantResponse:
    resp = db.query(ParticipantResponse).filter(ParticipantResponse.id == response_id).first()
    if not resp:
        raise HTTPException(status_code=404, detail="Response not found")

    enrollment = db.query(Enrollment).filter(Enrollment.id == resp.enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    if user.role == "participant" and enrollment.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if user.role == "coach" and enrollment.assigned_coach_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if user.role not in ["participant", "coach", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    return resp


def _validate_status_transition(old_status: ResponseStatus, new_status: ResponseStatus) -> bool:
    valid_transitions = {
        ResponseStatus.DRAFT: {ResponseStatus.SUBMITTED, ResponseStatus.ARCHIVED},
        ResponseStatus.SUBMITTED: {ResponseStatus.REVIEWED, ResponseStatus.ARCHIVED},
        ResponseStatus.REVIEWED: {ResponseStatus.ARCHIVED},
        ResponseStatus.ARCHIVED: set(),
    }
    return new_status in valid_transitions.get(old_status, set())


# ------------------------- Auto-save -----------------------------------------
@router.post("/autosave", response_model=AutoSaveResponse)
async def autosave_response(
    payload: AutoSaveRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resp = _require_response_access(db, payload.response_id, current_user)
    enrollment = db.query(Enrollment).filter(Enrollment.id == resp.enrollment_id).first()

    if current_user.role == "participant" and enrollment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only participants can auto-save")
    if resp.status in [ResponseStatus.SUBMITTED, ResponseStatus.REVIEWED]:
        raise HTTPException(status_code=400, detail="Cannot auto-save submitted or reviewed responses")

    try:
        old_values = {"draft_content": resp.draft_content}
        resp.draft_content = payload.draft_content
        resp.last_auto_save = datetime.now(pytz.UTC)
        resp.auto_save_count = (resp.auto_save_count or 0) + 1
        resp.is_auto_saved = True
        resp.version = (resp.version or 0) + 1

        if resp.status != ResponseStatus.DRAFT:
            resp.status = ResponseStatus.DRAFT

        db.commit()
        db.refresh(resp)

        background_tasks.add_task(
            _log_auto_save_action,
            db,
            current_user.id,
            resp.id,
            old_values,
            {"draft_content": resp.draft_content},
            request,
        )

        return AutoSaveResponse(
            success=True,
            response_id=resp.id,
            last_auto_save=resp.last_auto_save,
            auto_save_count=resp.auto_save_count,
            version=resp.version,
            message="Auto-save successful",
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Auto-save failed: {str(e)}")


def _log_auto_save_action(db: Session, user_id: int, response_id: int, old_values: dict, new_values: dict, request: Request):
    try:
        create_audit_log(
            db_session=db,
            user_id=user_id,
            action=AuditAction.AUTO_SAVE,
            resource_type="ParticipantResponse",
            resource_id=response_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            session_id=request.cookies.get("session_id"),
        )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to log auto-save action: {e}")


# ------------------------- Status Management ---------------------------------
@router.post("/{response_id}/status", response_model=StatusUpdateResponse)
async def update_response_status(
    response_id: int,
    request: StatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resp = _require_response_access(db, response_id, current_user)

    if not _validate_status_transition(resp.status, request.new_status):
        raise HTTPException(status_code=400, detail="Invalid status transition")

    old_status = resp.status
    resp.status = request.new_status
    db.commit()
    db.refresh(resp)

    create_audit_log(
        db_session=db,
        user_id=current_user.id,
        action=AuditAction.STATUS_UPDATE,
        resource_type="ParticipantResponse",
        resource_id=response_id,
        old_values={"status": old_status},
        new_values={"status": resp.status},
    )
    db.commit()

    return StatusUpdateResponse(
        success=True,
        response_id=response_id,
        old_status=old_status,
        new_status=resp.status,
        message="Status updated",
    )


# ------------------------- AI Processing Models -------------------------------
class ProcessAIRequest(BaseModel):
    force_reprocess: bool = False
    processing_options: Dict[str, Any] = {}


class ProcessAIResponse(BaseModel):
    processing_id: int
    status: str
    message: str
    estimated_completion_time: Optional[str] = None


class AIProcessingStatusResponse(BaseModel):
    processing_id: int
    response_id: int
    status: str
    standardized_text: Optional[str] = None
    confidence_score: Optional[float] = None
    retry_count: int
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    processing_steps: List[Dict[str, Any]] = []


class AIProcessingStatsResponse(BaseModel):
    total_processed: int
    successful_processing: int
    failed_processing: int
    average_confidence_score: float
    processing_by_type: Dict[str, int]
    recent_activity: List[Dict[str, Any]]


# ------------------------- AI Processing Endpoints ----------------------------
@router.post("/{response_id}/process-ai", response_model=ProcessAIResponse)
async def trigger_ai_processing(
    response_id: int,
    background_tasks: BackgroundTasks,
    request: ProcessAIRequest = ProcessAIRequest(),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resp = _require_response_access(db, response_id, current_user)

    existing = db.query(AIProcessing).filter(
        AIProcessing.response_id == response_id,
        AIProcessing.processing_status.in_([
            AIProcessingStatus.PENDING,
            AIProcessingStatus.PROCESSING,
            AIProcessingStatus.COMPLETED,
        ]),
    ).first()

    if existing and not request.force_reprocess:
        return ProcessAIResponse(
            processing_id=existing.id,
            status=existing.processing_status.value.lower(),
            message="Processing already exists",
        )

    if file:
        content_data = await file.read()
        content_type = file.content_type
        filename = file.filename
    elif resp.text_content:
        content_data = resp.text_content.encode("utf-8")
        content_type = "text/plain"
        filename = None
    else:
        raise HTTPException(status_code=400, detail="No content to process")

    ai_pipeline = AIProcessingPipeline(OPENAI_API_KEY, db)
    audit_service = AuditService(db)

    background_tasks.add_task(
        process_content_background,
        ai_pipeline,
        audit_service,
        response_id,
        content_data,
        content_type,
        filename,
        current_user.id,
        request.processing_options,
    )

    await audit_service.log_ai_processing(
        user_id=current_user.id,
        response_id=response_id,
        processing_id=None,
        status="initiated",
    )

    return ProcessAIResponse(
        processing_id=0,
        status="initiated",
        message="AI processing started",
        estimated_completion_time="2-5 minutes",
    )


async def process_content_background(
    ai_pipeline: AIProcessingPipeline,
    audit_service: AuditService,
    response_id: int,
    content_data: bytes,
    content_type: str,
    filename: Optional[str],
    user_id: int,
    processing_options: Dict[str, Any],
):
    try:
        result = await ai_pipeline.process_response_content(
            response_id=response_id,
            content_data=content_data,
            content_type=content_type,
            filename=filename,
        )
        logger.info(f"AI processing completed for response {response_id}: {result}")
    except Exception as e:
        logger.error(f"Background AI processing failed for response {response_id}: {str(e)}")


# ------------------------- Enhanced Submit Endpoint --------------------------
@router.post("/{response_id}/submit")
async def submit_response(
    response_id: int,
    background_tasks: BackgroundTasks,
    trigger_ai_processing: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = db.query(ParticipantResponse).filter(ParticipantResponse.id == response_id).first()
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")

    if current_user.role == "participant" and response.participant_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    response.status = ResponseStatus.SUBMITTED
    response.submitted_at = datetime.now(timezone.utc)

    if response.draft_content and response.is_auto_saved:
        response.content = response.draft_content.get("content", response.content)
        response.draft_content = None
        response.is_auto_saved = False

    db.commit()

    audit_service = AuditService(db)
    await audit_service.log_response_status_change(
        user_id=current_user.id,
        response_id=response_id,
        old_status="DRAFT",
        new_status="SUBMITTED",
    )

    if trigger_ai_processing and response.content:
        existing_ai_processing = db.query(AIProcessing).filter(
            AIProcessing.response_id == response_id,
            AIProcessing.processing_status.in_([
                AIProcessingStatus.PENDING,
                AIProcessingStatus.PROCESSING,
                AIProcessingStatus.COMPLETED,
            ]),
        ).first()
        if not existing_ai_processing:
            ai_pipeline = AIProcessingPipeline(OPENAI_API_KEY, db)
            background_tasks.add_task(
                start_ai_processing_on_submit,
                ai_pipeline,
                audit_service,
                response_id,
                response.content,
                current_user.id,
            )

    return {
        "message": "Response submitted successfully",
        "response_id": response_id,
        "status": "SUBMITTED",
        "ai_processing_triggered": trigger_ai_processing,
        "submitted_at": response.submitted_at.isoformat(),
    }


async def start_ai_processing_on_submit(
    ai_pipeline: AIProcessingPipeline,
    audit_service: AuditService,
    response_id: int,
    content: str,
    user_id: int,
):
    try:
        content_data = content.encode("utf-8")
        result = await ai_pipeline.process_response_content(
            response_id=response_id,
            content_data=content_data,
            content_type="text/plain",
            filename=None,
        )
        await audit_service.log_ai_processing(
            user_id=user_id,
            response_id=response_id,
            processing_id=result.get("processing_id"),
            status="auto_started_on_submit",
        )
        logger.info(f"AI processing auto-started for response {response_id}")
    except Exception as e:
        logger.error(f"Failed to auto-start AI processing for response {response_id}: {str(e)}")
        await audit_service.log_ai_processing(
            user_id=user_id,
            response_id=response_id,
            processing_id=None,
            status="auto_start_failed",
            error_message=str(e),
        )


# ------------------------- AI Insights Endpoint ------------------------------
@router.get("/{response_id}/ai-insights")
async def get_response_ai_insights(
    response_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = db.query(ParticipantResponse).filter(ParticipantResponse.id == response_id).first()
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")

    if current_user.role == "participant" and response.participant_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    ai_processing_records = db.query(AIProcessing).filter(
        AIProcessing.response_id == response_id,
        AIProcessing.processing_status == AIProcessingStatus.COMPLETED,
    ).order_by(AIProcessing.completed_at.desc()).all()

    if not ai_processing_records:
        return {
            "response_id": response_id,
            "ai_insights_available": False,
            "message": "No completed AI processing found for this response",
        }

    latest_processing = ai_processing_records[0]

    return {
        "response_id": response_id,
        "ai_insights_available": True,
        "original_content": response.content,
        "standardized_text": latest_processing.standardized_text,
        "confidence_score": latest_processing.confidence_score,
        "processing_details": {
            "input_type": latest_processing.input_type.value,
            "processing_id": latest_processing.id,
            "completed_at": latest_processing.completed_at.isoformat(),
            "processing_steps": latest_processing.processing_steps,
        },
        "content_analysis": {
            "original_length": len(response.content) if response.content else 0,
            "standardized_length": len(latest_processing.standardized_text)
            if latest_processing.standardized_text
            else 0,
            "improvement_ratio": latest_processing.confidence_score,
        },
    }


# ------------------------- Batch Processing Endpoint -------------------------
@router.post("/batch-ai-processing")
async def batch_ai_processing(
    response_ids: List[int],
    background_tasks: BackgroundTasks,
    force_reprocess: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["admin", "coach"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    responses = db.query(ParticipantResponse).filter(ParticipantResponse.id.in_(response_ids)).all()
    found_ids = [r.id for r in responses]
    missing_ids = [rid for rid in response_ids if rid not in found_ids]

    if missing_ids:
        raise HTTPException(status_code=404, detail=f"Responses not found: {missing_ids}")

    ai_pipeline = AIProcessingPipeline(OPENAI_API_KEY, db)
    audit_service = AuditService(db)
    background_tasks.add_task(
        process_responses_batch,
        ai_pipeline,
        audit_service,
        response_ids,
        current_user.id,
        force_reprocess,
    )

    await audit_service.create_audit_log(
        user_id=current_user.id,
        action="batch_ai_processing_started",
        resource_type="bulk_operation",
        resource_id=None,
        details={
            "response_ids": response_ids,
            "response_count": len(response_ids),
            "force_reprocess": force_reprocess,
        },
    )

    return {
        "message": f"Batch AI processing started for {len(response_ids)} responses",
        "response_ids": response_ids,
        "estimated_completion_time": f"{len(response_ids) * 10} seconds"
    }
