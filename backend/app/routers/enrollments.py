from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from typing import List, Optional
from datetime import datetime, date

from database import get_db
from models import Enrollment, User, Program, UserRole
from auth import get_current_user
from schemas import (
    EnrollmentResponse, 
    EnrollmentCreate, 
    EnrollmentUpdate,
    EnrollmentStatsResponse,
    UserBasic,
    ProgramBasic,
    CoachBasic
)

router = APIRouter(prefix="/enrollments", tags=["enrollments"])

def require_admin_or_trainer(current_user: User = Depends(get_current_user)):
    """Ensure user has ADMIN or TRAINER role"""
    if current_user.role not in [UserRole.ADMIN, UserRole.TRAINER]:
        raise HTTPException(
            status_code=403, 
            detail="Access denied. Admin or Trainer role required."
        )
    return current_user

def require_admin_hr_or_coach(current_user: User = Depends(get_current_user)):
    """Ensure user has ADMIN, TRAINER role"""
    if current_user.role not in [UserRole.ADMIN, UserRole.TRAINER]:
        raise HTTPException(
            status_code=403, 
            detail="Access denied. Admin or Trainer role required."
        )
    return current_user

@router.get("/", response_model=List[EnrollmentResponse])
def get_enrollments(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Number of records to return"),
    search: Optional[str] = Query(None, description="Search by user or program name"),
    status: Optional[str] = Query(None, description="Filter by enrollment status"),
    program_id: Optional[int] = Query(None, description="Filter by program ID"),
    coach_id: Optional[int] = Query(None, description="Filter by coach ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_hr_or_coach)
):
    """
    Get paginated list of enrollments with advanced filtering and search.
    
    - **Admin/Trainer**: Can view all enrollments
    - **Trainer**: Can only view enrollments assigned to them
    """
    
    # Build base query with joins
    query = db.query(Enrollment).join(User, Enrollment.user_id == User.id).join(Program, Enrollment.program_id == Program.id)
    
    # Role-based filtering
    if current_user.role == UserRole.TRAINER:
        query = query.filter(Enrollment.coach_id == current_user.id)
    
    # Apply filters
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.email.ilike(search_term),
                Program.name.ilike(search_term)
            )
        )
    
    if status:
        query = query.filter(Enrollment.status == status.upper())
    
    if program_id:
        query = query.filter(Enrollment.program_id == program_id)
    
    if coach_id:
        query = query.filter(Enrollment.coach_id == coach_id)
        
    if user_id:
        query = query.filter(Enrollment.user_id == user_id)
    
    # Apply sorting
    if hasattr(Enrollment, sort_by):
        order_func = desc if sort_order == "desc" else asc
        query = query.order_by(order_func(getattr(Enrollment, sort_by)))
    else:
        query = query.order_by(desc(Enrollment.created_at))
    
    # Apply pagination
    enrollments = query.offset(skip).limit(limit).all()
    
    return enrollments

@router.get("/{enrollment_id}", response_model=EnrollmentResponse)
def get_enrollment(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_hr_or_coach)
):
    """
    Get specific enrollment by ID.
    
    - **Admin/Trainer**: Can view any enrollment
    - **Trainer**: Can only view enrollments assigned to them
    """
    
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    # Role-based access control
    if current_user.role == UserRole.TRAINER and enrollment.coach_id != current_user.id:
        raise HTTPException(
            status_code=403, 
            detail="Access denied. You can only view enrollments assigned to you."
        )
    
    return enrollment

@router.post("/", response_model=EnrollmentResponse, status_code=201)
def create_enrollment(
    enrollment_data: EnrollmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_trainer)
):
    """
    Create new enrollment.
    
    Validates:
    - User exists and has CLIENT role
    - Program exists and is active
    - Coach exists and has TRAINER role
    - User not already enrolled in the program
    - Program not expired
    """
    
    # Validate user exists and has CLIENT role
    user = db.query(User).filter(User.id == enrollment_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != UserRole.CLIENT:
        raise HTTPException(status_code=400, detail="Only users with CLIENT role can be enrolled")
    
    # Validate program exists and is active
    program = db.query(Program).filter(Program.id == enrollment_data.program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    if not program.is_active:
        raise HTTPException(status_code=400, detail="Cannot enroll in inactive program")
    if program.expiry_date and program.expiry_date < date.today():
        raise HTTPException(status_code=400, detail="Cannot enroll in expired program")
    
    # Validate coach exists and has TRAINER role
    coach = db.query(User).filter(User.id == enrollment_data.coach_id).first()
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    if coach.role != UserRole.TRAINER:
        raise HTTPException(status_code=400, detail="Assigned user must have TRAINER role")
    
    # Check for duplicate enrollment
    existing_enrollment = db.query(Enrollment).filter(
        and_(
            Enrollment.user_id == enrollment_data.user_id,
            Enrollment.program_id == enrollment_data.program_id,
            Enrollment.status.in_(["ENROLLED", "ACTIVE"])
        )
    ).first()
    
    if existing_enrollment:
        raise HTTPException(
            status_code=400, 
            detail="User is already enrolled in this program"
        )
    
    # Create enrollment
    enrollment = Enrollment(
        user_id=enrollment_data.user_id,
        program_id=enrollment_data.program_id,
        coach_id=enrollment_data.coach_id,
        status="ENROLLED",
        enrolled_at=datetime.utcnow(),
        notes=enrollment_data.notes
    )
    
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    
    return enrollment

@router.put("/{enrollment_id}", response_model=EnrollmentResponse)
def update_enrollment(
    enrollment_id: int,
    enrollment_data: EnrollmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_trainer)
):
    """
    Update enrollment details.
    
    Allows updating:
    - Coach assignment
    - Status
    - Start/End dates
    - Notes
    """
    
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    # Validate coach if being updated
    if enrollment_data.coach_id is not None:
        coach = db.query(User).filter(User.id == enrollment_data.coach_id).first()
        if not coach:
            raise HTTPException(status_code=404, detail="Coach not found")
        if coach.role != UserRole.TRAINER:
            raise HTTPException(status_code=400, detail="Assigned user must have TRAINER role")
    
    # Update fields
    update_data = enrollment_data.dict(exclude_unset=True)
    
    # Handle status-specific logic
    if enrollment_data.status:
        if enrollment_data.status == "ACTIVE" and enrollment.status == "ENROLLED":
            update_data["started_at"] = datetime.utcnow()
        elif enrollment_data.status in ["COMPLETED", "WITHDRAWN"] and not enrollment.ended_at:
            update_data["ended_at"] = datetime.utcnow()
    
    # Apply updates
    for field, value in update_data.items():
        setattr(enrollment, field, value)
    
    enrollment.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(enrollment)
    
    return enrollment

@router.delete("/{enrollment_id}")
def delete_enrollment(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_trainer)
):
    """
    Delete enrollment.
    
    Note: This permanently removes the enrollment record.
    Consider using status update to "WITHDRAWN" instead for audit trail.
    """
    
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    db.delete(enrollment)
    db.commit()
    
    return {"message": "Enrollment deleted successfully"}

@router.patch("/{enrollment_id}/status", response_model=EnrollmentResponse)
def update_enrollment_status(
    enrollment_id: int,
    status: str = Query(..., regex="^(ENROLLED|ACTIVE|COMPLETED|WITHDRAWN)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_hr_or_coach)
):
    """
    Update enrollment status.
    
    Status transitions:
    - ENROLLED → ACTIVE (sets started_at)
    - ACTIVE → COMPLETED/WITHDRAWN (sets ended_at)
    - Any status → WITHDRAWN (emergency withdrawal)
    
    - **Admin/Trainer**: Can change any enrollment status
    - **Trainer**: Can only change status of enrollments assigned to them
    """
    
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    # Role-based access control
    if current_user.role == UserRole.TRAINER and enrollment.coach_id != current_user.id:
        raise HTTPException(
            status_code=403, 
            detail="Access denied. You can only update enrollments assigned to you."
        )
    
    # Update status with automatic timestamp management
    enrollment.status = status.upper()
    
    if status.upper() == "ACTIVE" and enrollment.status == "ENROLLED":
        enrollment.started_at = datetime.utcnow()
    elif status.upper() in ["COMPLETED", "WITHDRAWN"] and not enrollment.ended_at:
        enrollment.ended_at = datetime.utcnow()
    
    enrollment.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(enrollment)
    
    return enrollment

@router.patch("/{enrollment_id}/coach", response_model=EnrollmentResponse)
def reassign_coach(
    enrollment_id: int,
    new_coach_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_trainer)
):
    """
    Reassign enrollment to different coach.
    
    Validates new coach exists and has TRAINER role.
    """
    
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    # Validate new coach
    new_coach = db.query(User).filter(User.id == new_coach_id).first()
    if not new_coach:
        raise HTTPException(status_code=404, detail="New coach not found")
    if new_coach.role != UserRole.TRAINER:
        raise HTTPException(status_code=400, detail="Assigned user must have TRAINER role")
    
    enrollment.coach_id = new_coach_id
    enrollment.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(enrollment)
    
    return enrollment

@router.get("/stats/summary", response_model=EnrollmentStatsResponse)
def get_enrollment_stats(
    program_id: Optional[int] = Query(None, description="Filter stats by program ID"),
    coach_id: Optional[int] = Query(None, description="Filter stats by coach ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_hr_or_coach)
):
    """
    Get enrollment statistics.
    
    - **Admin/Trainer**: Can view all enrollment stats
    - **Trainer**: Can only view stats for enrollments assigned to them
    """
    
    # Build base query
    query = db.query(Enrollment)
    
    # Role-based filtering
    if current_user.role == UserRole.TRAINER:
        query = query.filter(Enrollment.coach_id == current_user.id)
    
    # Apply additional filters
    if program_id:
        query = query.filter(Enrollment.program_id == program_id)
    
    if coach_id:
        if current_user.role == UserRole.TRAINER and coach_id != current_user.id:
            raise HTTPException(
                status_code=403, 
                detail="Trainers can only view their own stats"
            )
        query = query.filter(Enrollment.coach_id == coach_id)
    
    # Get all enrollments matching filters
    enrollments = query.all()
    
    # Calculate statistics
    total_enrollments = len(enrollments)
    status_counts = {}
    
    for status in ["ENROLLED", "ACTIVE", "COMPLETED", "WITHDRAWN"]:
        status_counts[status.lower()] = len([e for e in enrollments if e.status == status])
    
    # Active programs (enrolled + active)
    active_enrollments = status_counts["enrolled"] + status_counts["active"]
    
    # Calculate completion rate
    completed_or_withdrawn = status_counts["completed"] + status_counts["withdrawn"]
    completion_rate = (status_counts["completed"] / completed_or_withdrawn * 100) if completed_or_withdrawn > 0 else 0
    
    return EnrollmentStatsResponse(
        total_enrollments=total_enrollments,
        active_enrollments=active_enrollments,
        enrolled_count=status_counts["enrolled"],
        active_count=status_counts["active"],
        completed_count=status_counts["completed"],
        withdrawn_count=status_counts["withdrawn"],
        completion_rate=round(completion_rate, 2)
    )

@router.get("/user/{user_id}/enrollments", response_model=List[EnrollmentResponse])
def get_user_enrollments(
    user_id: int,
    status: Optional[str] = Query(None, description="Filter by enrollment status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_hr_or_coach)
):
    """
    Get all enrollments for a specific user.
    
    - **Admin/Trainer**: Can view enrollments for any user
    - **Trainer**: Can only view enrollments they're assigned to
    """
    
    # Validate user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Build query
    query = db.query(Enrollment).filter(Enrollment.user_id == user_id)
    
    # Role-based filtering
    if current_user.role == UserRole.TRAINER:
        query = query.filter(Enrollment.coach_id == current_user.id)
    
    # Status filter
    if status:
        query = query.filter(Enrollment.status == status.upper())
    
    enrollments = query.order_by(desc(Enrollment.created_at)).all()
    
    return enrollments

@router.get("/coach/{coach_id}/enrollments", response_model=List[EnrollmentResponse])
def get_coach_enrollments(
    coach_id: int,
    status: Optional[str] = Query(None, description="Filter by enrollment status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_hr_or_coach)
):
    """
    Get all enrollments assigned to a specific coach.
    
    - **Admin/Trainer**: Can view enrollments for any coach
    - **Trainer**: Can only view their own enrollments
    """
    
    # Access control for trainers
    if current_user.role == UserRole.TRAINER and coach_id != current_user.id:
        raise HTTPException(
            status_code=403, 
            detail="Trainers can only view their own enrollments"
        )
    
    # Validate coach exists
    coach = db.query(User).filter(
        User.id == coach_id, 
        User.role == UserRole.TRAINER
    ).first()
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    
    # Build query
    query = db.query(Enrollment).filter(Enrollment.coach_id == coach_id)
    
    # Status filter
    if status:
        query = query.filter(Enrollment.status == status.upper())
    
    enrollments = query.order_by(desc(Enrollment.created_at)).all()
    
    return enrollments