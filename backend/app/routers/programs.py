from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional
from datetime import datetime
import math

from ..database import get_db
from ..models import (
    Program, User, UserRole,
    ProgramAnalytics, ParticipantProgress,
    PredictiveAnalysis, CompetencyMapping,
    CustomReportConfig
)
from ..auth import require_role
from ..schemas.program import ProgramCreate, ProgramUpdate, ProgramResponse

router = APIRouter(prefix="/programs", tags=["programs"])


@router.get("/", response_model=dict)
async def get_programs(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by program name or description"),
    active_only: bool = Query(True, description="Show only active programs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.TRAINER]))
):
    """
    Get paginated list of programs with filters.
    Accessible by ADMIN and TRAINER users.
    """
    try:
        query = db.query(Program)

        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                or_(
                    Program.name.ilike(search_filter),
                    Program.description.ilike(search_filter)
                )
            )

        if active_only:
            query = query.filter(Program.is_active == True)

        total_count = query.count()
        offset = (page - 1) * limit
        programs = query.offset(offset).limit(limit).all()

        total_pages = math.ceil(total_count / limit) if total_count > 0 else 1
        has_next = page < total_pages
        has_prev = page > 1

        program_list = []
        for program in programs:
            program_list.append({
                "id": program.id,
                "name": program.name,
                "description": program.description,
                "trainer_id": program.trainer_id,
                "is_active": program.is_active,
                "start_date": program.start_date,
                "end_date": program.end_date,
                "created_at": program.created_at,
                "updated_at": program.updated_at,
            })

        return {
            "programs": program_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            },
            "filters": {
                "search": search,
                "active_only": active_only
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving programs: {str(e)}")


@router.get("/{program_id}", response_model=dict)
async def get_program(
    program_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.TRAINER]))
):
    """
    Get specific program by ID with related analytics.
    """
    program = db.query(Program).filter(Program.id == program_id).first()

    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    return {
        "id": program.id,
        "name": program.name,
        "description": program.description,
        "trainer_id": program.trainer_id,
        "is_active": program.is_active,
        "start_date": program.start_date,
        "end_date": program.end_date,
        "created_at": program.created_at,
        "updated_at": program.updated_at,
        "participant_progress": [p.id for p in program.participant_progress],
        "analytics_records": [a.id for a in program.analytics_records],
        "predictive_analyses": [pa.id for pa in program.predictive_analyses],
        "competency_mappings": [c.id for c in program.competency_mappings],
        "custom_reports": [r.id for r in program.custom_reports],
    }


@router.get("/{program_id}/analytics")
async def get_program_analytics(
    program_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.TRAINER]))
):
    """
    Get detailed analytics and predictive insights for a program.
    """
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    return {
        "participant_progress": [p.__dict__ for p in program.participant_progress],
        "analytics_records": [a.__dict__ for a in program.analytics_records],
        "predictive_analyses": [pa.__dict__ for pa in program.predictive_analyses],
        "competency_mappings": [c.__dict__ for c in program.competency_mappings],
        "custom_reports": [r.__dict__ for r in program.custom_reports],
    }


@router.post("/", response_model=ProgramResponse, status_code=201)
async def create_program(
    program_data: ProgramCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Create a new program.
    Only accessible by ADMIN users.
    """
    try:
        new_program = Program(
            name=program_data.name,
            description=program_data.description,
            trainer_id=program_data.trainer_id,
            is_active=True,
            start_date=program_data.start_date,
            end_date=program_data.end_date,
            created_at=datetime.utcnow()
        )

        db.add(new_program)
        db.commit()
        db.refresh(new_program)

        return ProgramResponse(
            id=new_program.id,
            name=new_program.name,
            description=new_program.description,
            trainer_id=new_program.trainer_id,
            is_active=new_program.is_active,
            start_date=new_program.start_date,
            end_date=new_program.end_date,
            created_at=new_program.created_at,
            updated_at=new_program.updated_at
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating program: {str(e)}")


@router.put("/{program_id}", response_model=ProgramResponse)
async def update_program(
    program_id: int,
    program_data: ProgramUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.TRAINER]))
):
    """
    Update an existing program.
    ADMIN and TRAINER users can update.
    """
    try:
        program = db.query(Program).filter(Program.id == program_id).first()
        if not program:
            raise HTTPException(status_code=404, detail="Program not found")

        update_data = program_data.dict(exclude_unset=True)

        for field, value in update_data.items():
            setattr(program, field, value)

        program.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(program)

        return ProgramResponse(
            id=program.id,
            name=program.name,
            description=program.description,
            trainer_id=program.trainer_id,
            is_active=program.is_active,
            start_date=program.start_date,
            end_date=program.end_date,
            created_at=program.created_at,
            updated_at=program.updated_at
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating program: {str(e)}")


@router.delete("/{program_id}", status_code=204)
async def delete_program(
    program_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Delete a program.
    Only accessible by ADMIN users.
    """
    try:
        program = db.query(Program).filter(Program.id == program_id).first()
        if not program:
            raise HTTPException(status_code=404, detail="Program not found")

        db.delete(program)
        db.commit()
        return None

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting program: {str(e)}")


@router.patch("/{program_id}/toggle-status", response_model=ProgramResponse)
async def toggle_program_status(
    program_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Toggle program active status (activate/deactivate).
    Only accessible by ADMIN users.
    """
    try:
        program = db.query(Program).filter(Program.id == program_id).first()
        if not program:
            raise HTTPException(status_code=404, detail="Program not found")

        program.is_active = not program.is_active
        program.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(program)

        return ProgramResponse(
            id=program.id,
            name=program.name,
            description=program.description,
            trainer_id=program.trainer_id,
            is_active=program.is_active,
            start_date=program.start_date,
            end_date=program.end_date,
            created_at=program.created_at,
            updated_at=program.updated_at
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error toggling program status: {str(e)}")
