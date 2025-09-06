from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional
from datetime import datetime
import math

from backend.database import get_db
from backend.models import (
    User, UserRole,
    ParticipantProgress, PredictiveAnalysis,
    CompetencyMapping, CustomReportConfig
)
from backend.auth import get_current_user, require_role
from backend.schemas import UserResponse, UserCreate, UserUpdate
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/users", tags=["users"])


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(password)


@router.get("/", response_model=dict)
async def get_users(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by username or email"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    active_only: bool = Query(True, description="Show only active users"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Get paginated list of users with filters.
    Only accessible by ADMIN users.
    """
    try:
        query = db.query(User)

        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                or_(
                    User.username.ilike(search_filter),
                    User.email.ilike(search_filter)
                )
            )

        if role:
            query = query.filter(User.role == role)

        if active_only:
            query = query.filter(User.is_active == True)

        total_count = query.count()
        offset = (page - 1) * limit
        users = query.offset(offset).limit(limit).all()

        total_pages = math.ceil(total_count / limit) if total_count > 0 else 1
        has_next = page < total_pages
        has_prev = page > 1

        user_list = []
        for user in users:
            user_list.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat() if user.updated_at else None
            })

        return {
            "users": user_list,
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
                "role": role.value if role else None,
                "active_only": active_only
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving users: {str(e)}")


@router.get("/{user_id}", response_model=dict)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Get specific user by ID with related analytics.
    Only accessible by ADMIN users.
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role.value,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "progress_records": [p.id for p in user.progress_records],
        "predictive_analyses": [pa.id for pa in user.predictive_analyses],
        "competency_mappings": [c.id for c in user.competency_mappings],
        "created_reports": [r.id for r in user.created_reports],
    }


@router.get("/{user_id}/analytics")
async def get_user_analytics(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Get predictive analytics and competency mappings for a specific user.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "progress_records": [p.__dict__ for p in user.progress_records],
        "predictive_analyses": [pa.__dict__ for pa in user.predictive_analyses],
        "competency_mappings": [c.__dict__ for c in user.competency_mappings],
        "created_reports": [r.__dict__ for r in user.created_reports],
    }


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Create a new user.
    Only accessible by ADMIN users.
    """
    try:
        existing_user = db.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")

        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")

        new_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            role=UserRole(user_data.role),
            is_active=user_data.is_active if hasattr(user_data, 'is_active') else True,
            created_at=datetime.utcnow()
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return UserResponse(
            id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            role=new_user.role.value,
            is_active=new_user.is_active,
            created_at=new_user.created_at,
            updated_at=new_user.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Update an existing user.
    Only accessible by ADMIN users.
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.id == current_user.id and hasattr(user_data, 'is_active') and not user_data.is_active:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

        if user_data.username and user_data.username != user.username:
            existing_user = db.query(User).filter(
                and_(User.username == user_data.username, User.id != user_id)
            ).first()
            if existing_user:
                raise HTTPException(status_code=400, detail="Username already exists")

        if user_data.email and user_data.email != user.email:
            existing_email = db.query(User).filter(
                and_(User.email == user_data.email, User.id != user_id)
            ).first()
            if existing_email:
                raise HTTPException(status_code=400, detail="Email already exists")

        update_data = user_data.dict(exclude_unset=True)

        for field, value in update_data.items():
            if field == "password" and value:
                setattr(user, "password_hash", hash_password(value))
            elif field == "role":
                setattr(user, field, UserRole(value))
            elif field != "password":
                setattr(user, field, value)

        user.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(user)

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating user: {str(e)}")


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Delete a user.
    Only accessible by ADMIN users.
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")

        db.delete(user)
        db.commit()

        return None

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")


@router.patch("/{user_id}/toggle-status", response_model=UserResponse)
async def toggle_user_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Toggle user active status (activate/deactivate).
    Only accessible by ADMIN users.
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.id == current_user.id and user.is_active:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

        user.is_active = not user.is_active
        user.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(user)

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error toggling user status: {str(e)}")


@router.get("/stats/summary")
async def get_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Get user statistics summary.
    Only accessible by ADMIN users.
    """
    try:
        admin_count = db.query(User).filter(User.role == UserRole.ADMIN).count()
        trainer_count = db.query(User).filter(User.role == UserRole.TRAINER).count()
        client_count = db.query(User).filter(User.role == UserRole.CLIENT).count()

        active_count = db.query(User).filter(User.is_active == True).count()
        inactive_count = db.query(User).filter(User.is_active == False).count()

        total_count = db.query(User).count()

        return {
            "total_users": total_count,
            "by_role": {
                "admin": admin_count,
                "trainer": trainer_count,
                "client": client_count
            },
            "by_status": {
                "active": active_count,
                "inactive": inactive_count
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving user stats: {str(e)}")
