# services/audit_service.py

from sqlalchemy.orm import Session
from models import AuditLog, AuditAction
from datetime import datetime, timezone
import pytz
from typing import Optional, Dict, Any
import json
from fastapi import Request

class AuditService:
    """Service for managing audit logs and tracking user actions"""
    
    @staticmethod
    def log_action(
        db: Session,
        user_id: Optional[int],
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[int] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Create an audit log entry for a user action
        """
        ip_address = None
        user_agent = None
        session_id = None
        
        if request:
            ip_address = (
                request.headers.get("x-forwarded-for", "").split(",")[0].strip() or
                request.headers.get("x-real-ip") or
                request.client.host if request.client else None
            )
            user_agent = request.headers.get("user-agent")
            session_id = request.headers.get("x-session-id") or str(request.session) if hasattr(request, 'session') else None
        
        clean_old_values = AuditService._clean_values(old_values)
        clean_new_values = AuditService._clean_values(new_values)
        
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=clean_old_values,
            new_values=clean_new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            timestamp=datetime.now(pytz.UTC),
            metadata=metadata or {}
        )
        
        db.add(audit_log)
        db.flush()
        return audit_log
    
    @staticmethod
    def log_response_action(
        db: Session,
        user_id: int,
        action: AuditAction,
        response_id: int,
        old_response: Optional[Dict] = None,
        new_response: Optional[Dict] = None,
        request: Optional[Request] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        return AuditService.log_action(
            db=db,
            user_id=user_id,
            action=action,
            resource_type="ParticipantResponse",
            resource_id=response_id,
            old_values=old_response,
            new_values=new_response,
            request=request,
            metadata=metadata
        )
    
    @staticmethod
    def log_auto_save(
        db: Session,
        user_id: int,
        response_id: int,
        content: Dict[str, Any],
        request: Optional[Request] = None,
        auto_save_count: int = 0
    ) -> AuditLog:
        metadata = {
            "auto_save_count": auto_save_count,
            "content_length": len(json.dumps(content)) if content else 0,
            "auto_save_trigger": "periodic"
        }
        
        return AuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditAction.AUTO_SAVE,
            resource_type="ParticipantResponse",
            resource_id=response_id,
            new_values={"response_content": content},
            request=request,
            metadata=metadata
        )
    
    @staticmethod
    def log_status_change(
        db: Session,
        user_id: int,
        response_id: int,
        old_status: str,
        new_status: str,
        request: Optional[Request] = None,
        reason: Optional[str] = None
    ) -> AuditLog:
        metadata = {
            "status_change_reason": reason or "User initiated",
            "transition": f"{old_status} -> {new_status}"
        }
        
        return AuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditAction.STATUS_CHANGE,
            resource_type="ParticipantResponse",
            resource_id=response_id,
            old_values={"status": old_status},
            new_values={"status": new_status},
            request=request,
            metadata=metadata
        )
    
    @staticmethod
    def get_user_activity(
        db: Session,
        user_id: int,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[list[AuditLog], int]:
        query = db.query(AuditLog).filter(AuditLog.user_id == user_id)
        
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.filter(AuditLog.resource_id == resource_id)
        
        total = query.count()
        logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()
        return logs, total
    
    @staticmethod
    def get_resource_history(
        db: Session,
        resource_type: str,
        resource_id: int,
        limit: int = 100
    ) -> list[AuditLog]:
        return db.query(AuditLog).filter(
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == resource_id
        ).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    @staticmethod
    def _clean_values(values: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not values:
            return values
        
        clean_values = {}
        for key, value in values.items():
            try:
                json.dumps(value)
                clean_values[key] = value
            except (TypeError, ValueError):
                clean_values[key] = str(value)
        return clean_values
    
    @staticmethod
    def get_auto_save_stats(db: Session, user_id: int) -> Dict[str, Any]:
        auto_save_logs = db.query(AuditLog).filter(
            AuditLog.user_id == user_id,
            AuditLog.action == AuditAction.AUTO_SAVE
        ).all()
        
        if not auto_save_logs:
            return {
                "total_auto_saves": 0,
                "responses_with_auto_saves": 0,
                "last_auto_save": None,
                "average_auto_saves_per_response": 0.0
            }
        
        unique_responses = set(log.resource_id for log in auto_save_logs if log.resource_id)
        
        return {
            "total_auto_saves": len(auto_save_logs),
            "responses_with_auto_saves": len(unique_responses),
            "last_auto_save": max(log.timestamp for log in auto_save_logs),
            "average_auto_saves_per_response": len(auto_save_logs) / len(unique_responses) if unique_responses else 0.0
        }

    # ---------------- AI-specific logging ----------------

    async def log_ai_processing(
        self,
        user_id: Optional[int],
        response_id: int,
        processing_id: Optional[int],
        status: str,
        confidence_score: Optional[float] = None,
        error_message: Optional[str] = None,
        request=None
    ):
        """Log AI processing activities"""
        audit_data = {
            "response_id": response_id,
            "processing_id": processing_id,
            "status": status,
            "confidence_score": confidence_score,
            "error_message": error_message
        }
        await self.create_audit_log(
            user_id=user_id,
            action=f"ai_processing_{status}",
            resource_type="ai_processing",
            resource_id=processing_id,
            details=audit_data,
            request=request
        )

    async def log_ai_pipeline_step(
        self,
        user_id: Optional[int],
        processing_id: int,
        step_name: str,
        step_data: Dict[str, Any],
        request=None
    ):
        """Log individual AI pipeline processing steps"""
        audit_data = {
            "processing_id": processing_id,
            "step_name": step_name,
            "step_data": step_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.create_audit_log(
            user_id=user_id,
            action="ai_pipeline_step",
            resource_type="ai_processing_step",
            resource_id=processing_id,
            details=audit_data,
            request=request
        )

    async def log_ai_retry_attempt(
        self,
        user_id: Optional[int],
        processing_id: int,
        retry_count: int,
        reason: str,
        request=None
    ):
        """Log AI processing retry attempts"""
        audit_data = {
            "processing_id": processing_id,
            "retry_count": retry_count,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.create_audit_log(
            user_id=user_id,
            action="ai_processing_retry",
            resource_type="ai_processing",
            resource_id=processing_id,
            details=audit_data,
            request=request
        )
