from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from database import get_db
from auth import get_current_user
from models import AuditLog, User, AuditAction, UserRole
from schemas import AuditLogResponse, AuditLogEntry
from services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])

@router.get("/logs", response_model=AuditLogResponse)
async def get_audit_logs(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    action: Optional[AuditAction] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[int] = Query(None, description="Filter by resource ID"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get audit logs with filtering options
    Admins can see all logs, users can only see their own
    """
    
    # Build query
    query = db.query(AuditLog)
    
    # Role-based access control
    if current_user.role != UserRole.ADMIN:
        # Non-admins can only see their own audit logs
        query = query.filter(AuditLog.user_id == current_user.id)
    elif user_id:
        # Admins can filter by specific user
        query = query.filter(AuditLog.user_id == user_id)
    
    # Apply filters
    if action:
        query = query.filter(AuditLog.action == action)
    
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    
    if resource_id:
        query = query.filter(AuditLog.resource_id == resource_id)
    
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(per_page).all()
    
    return AuditLogResponse(
        logs=[AuditLogEntry.from_orm(log) for log in logs],
        total=total,
        page=page,
        per_page=per_page
    )

@router.get("/my-activity", response_model=AuditLogResponse)
async def get_my_activity(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    action: Optional[AuditAction] = Query(None),
    resource_type: Optional[str] = Query(None),
    days_back: int = Query(30, ge=1, le=365, description="Days of history to include"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's activity history
    """
    
    start_date = datetime.utcnow() - timedelta(days=days_back)
    
    query = db.query(AuditLog).filter(
        AuditLog.user_id == current_user.id,
        AuditLog.timestamp >= start_date
    )
    
    if action:
        query = query.filter(AuditLog.action == action)
    
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    
    total = query.count()
    offset = (page - 1) * per_page
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(per_page).all()
    
    return AuditLogResponse(
        logs=[AuditLogEntry.from_orm(log) for log in logs],
        total=total,
        page=page,
        per_page=per_page
    )

@router.get("/stats/actions")
async def get_action_stats(
    days_back: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get action statistics for the current user
    """
    
    start_date = datetime.utcnow() - timedelta(days=days_back)
    
    # Get action counts
    action_counts = db.query(
        AuditLog.action,
        db.func.count(AuditLog.id).label('count')
    ).filter(
        AuditLog.user_id == current_user.id,
        AuditLog.timestamp >= start_date
    ).group_by(AuditLog.action).all()
    
    # Get auto-save specific stats
    auto_save_stats = AuditService.get_auto_save_stats(db, current_user.id)
    
    # Get daily activity for the past week
    week_ago = datetime.utcnow() - timedelta(days=7)
    daily_activity = db.query(
        db.func.date(AuditLog.timestamp).label('date'),
        db.func.count(AuditLog.id).label('count')
    ).filter(
        AuditLog.user_id == current_user.id,
        AuditLog.timestamp >= week_ago
    ).group_by(db.func.date(AuditLog.timestamp)).order_by('date').all()
    
    return {
        "action_counts": {str(action): count for action, count in action_counts},
        "auto_save_stats": auto_save_stats,
        "daily_activity": [
            {"date": str(date), "count": count}
            for date, count in daily_activity
        ],
        "period_days": days_back
    }

@router.get("/stats/system")
async def get_system_stats(
    days_back: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get system-wide audit statistics (admin only)
    """
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    start_date = datetime.utcnow() - timedelta(days=days_back)
    
    # Overall activity stats
    total_logs = db.query(AuditLog).filter(AuditLog.timestamp >= start_date).count()
    
    # Active users
    active_users = db.query(AuditLog.user_id).filter(
        AuditLog.timestamp >= start_date,
        AuditLog.user_id.isnot(None)
    ).distinct().count()
    
    # Action breakdown
    action_breakdown = db.query(
        AuditLog.action,
        db.func.count(AuditLog.id).label('count')
    ).filter(
        AuditLog.timestamp >= start_date
    ).group_by(AuditLog.action).all()
    
    # Resource type breakdown
    resource_breakdown = db.query(
        AuditLog.resource_type,
        db.func.count(AuditLog.id).label('count')
    ).filter(
        AuditLog.timestamp >= start_date
    ).group_by(AuditLog.resource_type).all()
    
    # Top active users
    top_users = db.query(
        AuditLog.user_id,
        User.email,
        db.func.count(AuditLog.id).label('activity_count')
    ).join(User, AuditLog.user_id == User.id).filter(
        AuditLog.timestamp >= start_date
    ).group_by(AuditLog.user_id, User.email).order_by(
        db.func.count(AuditLog.id).desc()
    ).limit(10).all()
    
    return {
        "period_days": days_back,
        "total_logs": total_logs,
        "active_users": active_users,
        "action_breakdown": {str(action): count for action, count in action_breakdown},
        "resource_breakdown": {resource_type: count for resource_type, count in resource_breakdown},
        "top_users": [
            {"user_id": user_id, "email": email, "activity_count": count}
            for user_id, email, count in top_users
        ]
    }

@router.get("/resource/{resource_type}/{resource_id}/history")
async def get_resource_audit_history(
    resource_type: str,
    resource_id: int,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get complete audit history for a specific resource
    Access control based on resource type and user role
    """
    
    # Basic access control - admins can see all, others need specific permissions
    if current_user.role != UserRole.ADMIN:
        # For non-admins, verify they have access to this resource
        if resource_type == "ParticipantResponse":
            from models import ParticipantResponse, Enrollment
            
            # Check if it's their own response or they're the assigned coach
            response = db.query(ParticipantResponse).filter(
                ParticipantResponse.id == resource_id
            ).first()
            
            if not response:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Resource not found"
                )
            
            has_access = False
            if current_user.role == UserRole.participant and response.participant_id == current_user.id:
                has_access = True
            elif current_user.role == UserRole.coach:
                enrollment = db.query(Enrollment).filter(
                    Enrollment.participant_id == response.participant_id,
                    Enrollment.assigned_coach_id == current_user.id
                ).first()
                has_access = bool(enrollment)
            
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to resource history"
                )
        else:
            # For other resource types, restrict to admin only
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to resource history"
            )
    
    # Get the audit history
    logs = AuditService.get_resource_history(db, resource_type, resource_id, limit)
    
    return {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "history": [AuditLogEntry.from_orm(log) for log in logs],
        "total_entries": len(logs)
    }