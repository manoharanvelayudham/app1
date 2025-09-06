from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime
import pytz

from database import get_db
from models import CoachReview, ParticipantResponse, User, Enrollment, Program, ReviewStatus
from auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/reviews", tags=["reviews"])

# Pydantic models for request/response
class ReviewSubmission(BaseModel):
    score: Optional[float] = None
    max_score: Optional[float] = 100.0
    comments: Optional[str] = None

class ReviewUpdate(BaseModel):
    score: Optional[float] = None
    max_score: Optional[float] = None
    comments: Optional[str] = None
    status: Optional[ReviewStatus] = None

class ReviewSummary(BaseModel):
    id: int
    response_id: int
    participant_name: str
    program_name: str
    response_type: str
    submitted_at: datetime
    score: Optional[float] = None
    max_score: float
    comments: Optional[str] = None
    status: ReviewStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class ReviewDetail(BaseModel):
    id: int
    response_id: int
    coach_id: int
    coach_name: str
    participant_name: str
    program_name: str
    response_type: str
    response_content: Optional[str] = None
    response_filename: Optional[str] = None
    response_file_size: Optional[int] = None
    submitted_at: datetime
    score: Optional[float] = None
    max_score: float
    comments: Optional[str] = None
    status: ReviewStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

def require_coach_role(current_user: User = Depends(get_current_user)):
    """Verify that the current user is a coach"""
    if current_user.role != "coach":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Coach role required."
        )
    return current_user

@router.get("/queue/{coach_id}", response_model=List[ReviewSummary])
async def get_coach_review_queue(
    coach_id: int,
    status_filter: Optional[ReviewStatus] = None,
    program_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_role)
):
    """Get the review queue for a specific coach"""
    
    # Verify coach can access this queue (coaches can only see their own queue)
    if current_user.id != coach_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view your own review queue."
        )
    
    # Base query: get responses from enrollments assigned to this coach
    query = db.query(
        ParticipantResponse,
        CoachReview,
        User.full_name.label("participant_name"),
        Program.name.label("program_name")
    ).outerjoin(
        CoachReview,
        and_(
            CoachReview.response_id == ParticipantResponse.id,
            CoachReview.coach_id == coach_id
        )
    ).join(
        Enrollment, Enrollment.id == ParticipantResponse.enrollment_id
    ).join(
        User, User.id == Enrollment.participant_id
    ).join(
        Program, Program.id == Enrollment.program_id
    ).filter(
        Enrollment.assigned_coach_id == coach_id
    )
    
    # Apply filters
    if program_id:
        query = query.filter(Program.id == program_id)
    
    if status_filter:
        if status_filter == ReviewStatus.PENDING:
            # Pending means no review exists yet or review is pending
            query = query.filter(
                or_(
                    CoachReview.id.is_(None),
                    CoachReview.status == ReviewStatus.PENDING
                )
            )
        else:
            query = query.filter(CoachReview.status == status_filter)
    
    results = query.order_by(ParticipantResponse.submitted_at.desc()).all()
    
    review_summaries = []
    for response, review, participant_name, program_name in results:
        # Create or get review status
        review_status = review.status if review else ReviewStatus.PENDING
        score = review.score if review else None
        max_score = review.max_score if review else 100.0
        comments = review.comments if review else None
        started_at = review.started_at if review else None
        completed_at = review.completed_at if review else None
        review_id = review.id if review else None
        
        # If no review exists, create a placeholder ID (we'll handle this in the endpoint)
        if not review_id:
            # Create a pending review record
            new_review = CoachReview(
                response_id=response.id,
                coach_id=coach_id,
                status=ReviewStatus.PENDING
            )
            db.add(new_review)
            db.commit()
            db.refresh(new_review)
            review_id = new_review.id
        
        review_summaries.append(ReviewSummary(
            id=review_id,
            response_id=response.id,
            participant_name=participant_name,
            program_name=program_name,
            response_type=response.response_type.value,
            submitted_at=response.submitted_at,
            score=score,
            max_score=max_score,
            comments=comments,
            status=review_status,
            started_at=started_at,
            completed_at=completed_at
        ))
    
    return review_summaries

@router.post("/", response_model=ReviewDetail)
async def start_review(
    response_id: int,
    review_data: ReviewSubmission,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_role)
):
    """Start or update a review for a participant response"""
    
    # Verify the response exists and coach has access
    response = db.query(ParticipantResponse).join(
        Enrollment, Enrollment.id == ParticipantResponse.enrollment_id
    ).filter(
        ParticipantResponse.id == response_id,
        Enrollment.assigned_coach_id == current_user.id
    ).first()
    
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Response not found or access denied"
        )
    
    # Check if review already exists
    existing_review = db.query(CoachReview).filter(
        CoachReview.response_id == response_id,
        CoachReview.coach_id == current_user.id
    ).first()
    
    if existing_review:
        # Update existing review
        if review_data.score is not None:
            existing_review.score = review_data.score
        if review_data.max_score is not None:
            existing_review.max_score = review_data.max_score
        if review_data.comments is not None:
            existing_review.comments = review_data.comments
        
        # Update status and timestamps
        if existing_review.status == ReviewStatus.PENDING:
            existing_review.status = ReviewStatus.IN_PROGRESS
            existing_review.started_at = datetime.now(pytz.UTC)
        
        existing_review.updated_at = datetime.now(pytz.UTC)
        review = existing_review
    else:
        # Create new review
        review = CoachReview(
            response_id=response_id,
            coach_id=current_user.id,
            score=review_data.score,
            max_score=review_data.max_score or 100.0,
            comments=review_data.comments,
            status=ReviewStatus.IN_PROGRESS,
            started_at=datetime.now(pytz.UTC)
        )
        db.add(review)
    
    db.commit()
    db.refresh(review)
    
    # Get additional details for response
    enrollment = db.query(Enrollment).filter(Enrollment.id == response.enrollment_id).first()
    participant = db.query(User).filter(User.id == enrollment.participant_id).first()
    program = db.query(Program).filter(Program.id == enrollment.program_id).first()
    
    return ReviewDetail(
        id=review.id,
        response_id=review.response_id,
        coach_id=review.coach_id,
        coach_name=current_user.full_name,
        participant_name=participant.full_name,
        program_name=program.name,
        response_type=response.response_type.value,
        response_content=response.content if response.response_type.value == "TEXT" else None,
        response_filename=response.filename,
        response_file_size=response.file_size,
        submitted_at=response.submitted_at,
        score=review.score,
        max_score=review.max_score,
        comments=review.comments,
        status=review.status,
        started_at=review.started_at,
        completed_at=review.completed_at,
        created_at=review.created_at,
        updated_at=review.updated_at
    )

@router.get("/{review_id}", response_model=ReviewDetail)
async def get_review_detail(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_role)
):
    """Get detailed information about a specific review"""
    
    # Get review with all related data
    review = db.query(CoachReview).filter(
        CoachReview.id == review_id,
        CoachReview.coach_id == current_user.id
    ).first()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    # Get related data
    response = db.query(ParticipantResponse).filter(
        ParticipantResponse.id == review.response_id
    ).first()
    enrollment = db.query(Enrollment).filter(Enrollment.id == response.enrollment_id).first()
    participant = db.query(User).filter(User.id == enrollment.participant_id).first()
    program = db.query(Program).filter(Program.id == enrollment.program_id).first()
    
    return ReviewDetail(
        id=review.id,
        response_id=review.response_id,
        coach_id=review.coach_id,
        coach_name=current_user.full_name,
        participant_name=participant.full_name,
        program_name=program.name,
        response_type=response.response_type.value,
        response_content=response.content if response.response_type.value == "TEXT" else None,
        response_filename=response.filename,
        response_file_size=response.file_size,
        submitted_at=response.submitted_at,
        score=review.score,
        max_score=review.max_score,
        comments=review.comments,
        status=review.status,
        started_at=review.started_at,
        completed_at=review.completed_at,
        created_at=review.created_at,
        updated_at=review.updated_at
    )

@router.put("/{review_id}", response_model=ReviewDetail)
async def update_review(
    review_id: int,
    review_update: ReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_role)
):
    """Update an existing review"""
    
    review = db.query(CoachReview).filter(
        CoachReview.id == review_id,
        CoachReview.coach_id == current_user.id
    ).first()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    # Update fields if provided
    if review_update.score is not None:
        review.score = review_update.score
    if review_update.max_score is not None:
        review.max_score = review_update.max_score
    if review_update.comments is not None:
        review.comments = review_update.comments
    if review_update.status is not None:
        review.status = review_update.status
        
        # Update timestamps based on status
        if review_update.status == ReviewStatus.IN_PROGRESS and not review.started_at:
            review.started_at = datetime.now(pytz.UTC)
        elif review_update.status == ReviewStatus.COMPLETED:
            review.completed_at = datetime.now(pytz.UTC)
    
    review.updated_at = datetime.now(pytz.UTC)
    db.commit()
    db.refresh(review)
    
    # Get related data for response
    response = db.query(ParticipantResponse).filter(
        ParticipantResponse.id == review.response_id
    ).first()
    enrollment = db.query(Enrollment).filter(Enrollment.id == response.enrollment_id).first()
    participant = db.query(User).filter(User.id == enrollment.participant_id).first()
    program = db.query(Program).filter(Program.id == enrollment.program_id).first()
    
    return ReviewDetail(
        id=review.id,
        response_id=review.response_id,
        coach_id=review.coach_id,
        coach_name=current_user.full_name,
        participant_name=participant.full_name,
        program_name=program.name,
        response_type=response.response_type.value,
        response_content=response.content if response.response_type.value == "TEXT" else None,
        response_filename=response.filename,
        response_file_size=response.file_size,
        submitted_at=response.submitted_at,
        score=review.score,
        max_score=review.max_score,
        comments=review.comments,
        status=review.status,
        started_at=review.started_at,
        completed_at=review.completed_at,
        created_at=review.created_at,
        updated_at=review.updated_at
    )

@router.post("/{review_id}/finalize", response_model=ReviewDetail)
async def finalize_review(
    review_id: int,
    final_review: ReviewSubmission,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_role)
):
    """Finalize a review with final score and comments"""
    
    review = db.query(CoachReview).filter(
        CoachReview.id == review_id,
        CoachReview.coach_id == current_user.id
    ).first()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    # Finalize the review
    if final_review.score is not None:
        review.score = final_review.score
    if final_review.max_score is not None:
        review.max_score = final_review.max_score
    if final_review.comments is not None:
        review.comments = final_review.comments
    
    review.status = ReviewStatus.COMPLETED
    review.completed_at = datetime.now(pytz.UTC)
    review.updated_at = datetime.now(pytz.UTC)
    
    # If this is the first time starting the review, set started_at
    if not review.started_at:
        review.started_at = datetime.now(pytz.UTC)
    
    db.commit()
    db.refresh(review)
    
    # Get related data for response
    response = db.query(ParticipantResponse).filter(
        ParticipantResponse.id == review.response_id
    ).first()
    enrollment = db.query(Enrollment).filter(Enrollment.id == response.enrollment_id).first()
    participant = db.query(User).filter(User.id == enrollment.participant_id).first()
    program = db.query(Program).filter(Program.id == enrollment.program_id).first()
    
    return ReviewDetail(
        id=review.id,
        response_id=review.response_id,
        coach_id=review.coach_id,
        coach_name=current_user.full_name,
        participant_name=participant.full_name,
        program_name=program.name,
        response_type=response.response_type.value,
        response_content=response.content if response.response_type.value == "TEXT" else None,
        response_filename=response.filename,
        response_file_size=response.file_size,
        submitted_at=response.submitted_at,
        score=review.score,
        max_score=review.max_score,
        comments=review.comments,
        status=review.status,
        started_at=review.started_at,
        completed_at=review.completed_at,
        created_at=review.created_at,
        updated_at=review.updated_at
    )

@router.delete("/{review_id}")
async def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_role)
):
    """Delete a review (only if not completed)"""
    
    review = db.query(CoachReview).filter(
        CoachReview.id == review_id,
        CoachReview.coach_id == current_user.id
    ).first()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    if review.status == ReviewStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a completed review"
        )
    
    db.delete(review)
    db.commit()
    
    return {"message": "Review deleted successfully"}