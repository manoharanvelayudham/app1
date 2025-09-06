from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from database import get_db
from models import User, Program, Enrollment, EnrollmentStatus, UserRole
from auth import get_current_user
from datetime import datetime, timedelta
from typing import Dict, List, Any
from pydantic import BaseModel

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Dashboard Response Schemas
class AdminDashboardResponse(BaseModel):
    total_users: int
    active_users: int
    total_programs: int
    active_programs: int
    total_enrollments: int
    active_enrollments: int
    completion_rate: float
    recent_enrollments: List[Dict[str, Any]]
    user_role_breakdown: Dict[str, int]
    program_popularity: List[Dict[str, Any]]
    enrollment_trends: Dict[str, int]

class CoachDashboardResponse(BaseModel):
    assigned_participants: int
    active_enrollments: int
    completed_enrollments: int
    completion_rate: float
    review_queue: List[Dict[str, Any]]
    recent_participants: List[Dict[str, Any]]
    program_breakdown: Dict[str, int]
    monthly_progress: Dict[str, int]

class ParticipantDashboardResponse(BaseModel):
    enrolled_programs: int
    active_programs: int
    completed_programs: int
    completion_rate: float
    current_enrollments: List[Dict[str, Any]]
    completed_enrollments: List[Dict[str, Any]]
    progress_summary: Dict[str, Any]
    upcoming_deadlines: List[Dict[str, Any]]

@router.get("/admin", response_model=AdminDashboardResponse)
async def get_admin_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive admin dashboard with system-wide statistics."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Basic counts
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    total_programs = db.query(Program).count()
    active_programs = db.query(Program).filter(Program.is_active == True).count()
    total_enrollments = db.query(Enrollment).count()
    active_enrollments = db.query(Enrollment).filter(
        Enrollment.status.in_([EnrollmentStatus.ENROLLED, EnrollmentStatus.ACTIVE])
    ).count()
    
    # Completion rate
    completed_enrollments = db.query(Enrollment).filter(
        Enrollment.status == EnrollmentStatus.COMPLETED
    ).count()
    completion_rate = (completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0.0
    
    # Recent enrollments (last 10)
    recent_enrollments_query = db.query(Enrollment).join(User).join(Program).filter(
        Enrollment.enrolled_at >= datetime.now() - timedelta(days=30)
    ).order_by(Enrollment.enrolled_at.desc()).limit(10)
    
    recent_enrollments = []
    for enrollment in recent_enrollments_query:
        recent_enrollments.append({
            "id": enrollment.id,
            "user_name": enrollment.user.full_name,
            "program_name": enrollment.program.name,
            "status": enrollment.status.value,
            "enrolled_at": enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None
        })
    
    # User role breakdown
    user_roles = db.query(User.role, func.count(User.id)).group_by(User.role).all()
    user_role_breakdown = {role.value: count for role, count in user_roles}
    
    # Program popularity (by enrollment count)
    program_popularity_query = db.query(
        Program.name,
        func.count(Enrollment.id).label('enrollment_count')
    ).join(Enrollment).group_by(Program.id, Program.name).order_by(
        func.count(Enrollment.id).desc()
    ).limit(10)
    
    program_popularity = []
    for program_name, count in program_popularity_query:
        program_popularity.append({
            "program_name": program_name,
            "enrollment_count": count
        })
    
    # Enrollment trends (last 12 months)
    enrollment_trends = {}
    for i in range(12):
        month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        month_name = month_start.strftime("%Y-%m")
        
        count = db.query(Enrollment).filter(
            and_(
                Enrollment.enrolled_at >= month_start,
                Enrollment.enrolled_at < month_end
            )
        ).count()
        enrollment_trends[month_name] = count
    
    return AdminDashboardResponse(
        total_users=total_users,
        active_users=active_users,
        total_programs=total_programs,
        active_programs=active_programs,
        total_enrollments=total_enrollments,
        active_enrollments=active_enrollments,
        completion_rate=round(completion_rate, 2),
        recent_enrollments=recent_enrollments,
        user_role_breakdown=user_role_breakdown,
        program_popularity=program_popularity,
        enrollment_trends=enrollment_trends
    )

@router.get("/coach", response_model=CoachDashboardResponse)
async def get_coach_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get coach dashboard with assigned participants and review queue."""
    if current_user.role != UserRole.TRAINER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trainer access required"
        )
    
    # Basic counts for this coach
    assigned_participants = db.query(Enrollment).filter(
        Enrollment.coach_id == current_user.id
    ).count()
    
    active_enrollments = db.query(Enrollment).filter(
        and_(
            Enrollment.coach_id == current_user.id,
            Enrollment.status.in_([EnrollmentStatus.ENROLLED, EnrollmentStatus.ACTIVE])
        )
    ).count()
    
    completed_enrollments = db.query(Enrollment).filter(
        and_(
            Enrollment.coach_id == current_user.id,
            Enrollment.status == EnrollmentStatus.COMPLETED
        )
    ).count()
    
    # Completion rate for this coach
    completion_rate = (completed_enrollments / assigned_participants * 100) if assigned_participants > 0 else 0.0
    
    # Review queue (active enrollments that might need attention)
    review_queue_query = db.query(Enrollment).join(User).join(Program).filter(
        and_(
            Enrollment.coach_id == current_user.id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
            or_(
                Enrollment.started_at <= datetime.now() - timedelta(days=7),  # Active for more than a week
                Enrollment.started_at.is_(None)  # No start date set
            )
        )
    ).order_by(Enrollment.started_at.asc())
    
    review_queue = []
    for enrollment in review_queue_query:
        days_active = (datetime.now() - enrollment.started_at).days if enrollment.started_at else None
        review_queue.append({
            "id": enrollment.id,
            "user_name": enrollment.user.full_name,
            "program_name": enrollment.program.name,
            "status": enrollment.status.value,
            "days_active": days_active,
            "started_at": enrollment.started_at.isoformat() if enrollment.started_at else None
        })
    
    # Recent participants (last 10 enrollments)
    recent_participants_query = db.query(Enrollment).join(User).join(Program).filter(
        Enrollment.coach_id == current_user.id
    ).order_by(Enrollment.enrolled_at.desc()).limit(10)
    
    recent_participants = []
    for enrollment in recent_participants_query:
        recent_participants.append({
            "id": enrollment.id,
            "user_name": enrollment.user.full_name,
            "program_name": enrollment.program.name,
            "status": enrollment.status.value,
            "enrolled_at": enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None
        })
    
    # Program breakdown for this coach
    program_breakdown_query = db.query(
        Program.name,
        func.count(Enrollment.id).label('count')
    ).join(Enrollment).filter(
        Enrollment.coach_id == current_user.id
    ).group_by(Program.id, Program.name)
    
    program_breakdown = {}
    for program_name, count in program_breakdown_query:
        program_breakdown[program_name] = count
    
    # Monthly progress (last 6 months completion)
    monthly_progress = {}
    for i in range(6):
        month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        month_name = month_start.strftime("%Y-%m")
        
        count = db.query(Enrollment).filter(
            and_(
                Enrollment.coach_id == current_user.id,
                Enrollment.status == EnrollmentStatus.COMPLETED,
                Enrollment.ended_at >= month_start,
                Enrollment.ended_at < month_end
            )
        ).count()
        monthly_progress[month_name] = count
    
    return CoachDashboardResponse(
        assigned_participants=assigned_participants,
        active_enrollments=active_enrollments,
        completed_enrollments=completed_enrollments,
        completion_rate=round(completion_rate, 2),
        review_queue=review_queue,
        recent_participants=recent_participants,
        program_breakdown=program_breakdown,
        monthly_progress=monthly_progress
    )

@router.get("/participant", response_model=ParticipantDashboardResponse)
async def get_participant_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get participant dashboard with enrolled programs and progress."""
    if current_user.role != UserRole.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Participant access required"
        )
    
    # Basic counts for this participant
    enrolled_programs = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id
    ).count()
    
    active_programs = db.query(Enrollment).filter(
        and_(
            Enrollment.user_id == current_user.id,
            Enrollment.status.in_([EnrollmentStatus.ENROLLED, EnrollmentStatus.ACTIVE])
        )
    ).count()
    
    completed_programs = db.query(Enrollment).filter(
        and_(
            Enrollment.user_id == current_user.id,
            Enrollment.status == EnrollmentStatus.COMPLETED
        )
    ).count()
    
    # Completion rate for this participant
    completion_rate = (completed_programs / enrolled_programs * 100) if enrolled_programs > 0 else 0.0
    
    # Current enrollments
    current_enrollments_query = db.query(Enrollment).join(Program).outerjoin(User, Enrollment.coach_id == User.id).filter(
        and_(
            Enrollment.user_id == current_user.id,
            Enrollment.status.in_([EnrollmentStatus.ENROLLED, EnrollmentStatus.ACTIVE])
        )
    ).order_by(Enrollment.enrolled_at.desc())
    
    current_enrollments = []
    for enrollment in current_enrollments_query:
        coach_name = enrollment.coach.full_name if enrollment.coach else None
        current_enrollments.append({
            "id": enrollment.id,
            "program_name": enrollment.program.name,
            "program_description": enrollment.program.description,
            "status": enrollment.status.value,
            "coach_name": coach_name,
            "enrolled_at": enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
            "started_at": enrollment.started_at.isoformat() if enrollment.started_at else None
        })
    
    # Completed enrollments
    completed_enrollments_query = db.query(Enrollment).join(Program).outerjoin(User, Enrollment.coach_id == User.id).filter(
        and_(
            Enrollment.user_id == current_user.id,
            Enrollment.status == EnrollmentStatus.COMPLETED
        )
    ).order_by(Enrollment.ended_at.desc()).limit(10)
    
    completed_enrollments = []
    for enrollment in completed_enrollments_query:
        coach_name = enrollment.coach.full_name if enrollment.coach else None
        completed_enrollments.append({
            "id": enrollment.id,
            "program_name": enrollment.program.name,
            "coach_name": coach_name,
            "completed_at": enrollment.ended_at.isoformat() if enrollment.ended_at else None
        })
    
    # Progress summary
    progress_summary = {
        "total_enrolled": enrolled_programs,
        "in_progress": active_programs,
        "completed": completed_programs,
        "completion_rate": round(completion_rate, 2)
    }
    
    # Upcoming deadlines (programs with end dates)
    upcoming_deadlines_query = db.query(Enrollment).join(Program).filter(
        and_(
            Enrollment.user_id == current_user.id,
            Enrollment.status.in_([EnrollmentStatus.ENROLLED, EnrollmentStatus.ACTIVE]),
            Program.end_date.is_not(None),
            Program.end_date >= datetime.now().date()
        )
    ).order_by(Program.end_date.asc())
    
    upcoming_deadlines = []
    for enrollment in upcoming_deadlines_query:
        days_until_end = (enrollment.program.end_date - datetime.now().date()).days
        upcoming_deadlines.append({
            "program_name": enrollment.program.name,
            "end_date": enrollment.program.end_date.isoformat(),
            "days_remaining": days_until_end
        })
    
    return ParticipantDashboardResponse(
        enrolled_programs=enrolled_programs,
        active_programs=active_programs,
        completed_programs=completed_programs,
        completion_rate=round(completion_rate, 2),
        current_enrollments=current_enrollments,
        completed_enrollments=completed_enrollments,
        progress_summary=progress_summary,
        upcoming_deadlines=upcoming_deadlines
    )