"""
This file aggregates all schemas for easier imports.
"""
from .bulk_ops_schemas import (
    BulkImportResult, BulkImportStatus, BackupRequest, RestoreRequest,
    ImportValidationError, BulkOperationResponse
)

from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum

# Enum from models for use in schemas
class UserRole(str, Enum):
    CLIENT = "client"
    TRAINER = "trainer"
    ADMIN = "admin"

class AuditAction(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    VIEW = "VIEW"
    SUBMIT = "SUBMIT"
    REVIEW = "REVIEW"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    AUTO_SAVE = "AUTO_SAVE"
    STATUS_CHANGE = "STATUS_CHANGE"

# Schemas for Audit Logs
class AuditLogEntry(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    resource_type: str
    resource_id: Optional[int]
    timestamp: datetime
    details: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    logs: List[AuditLogEntry]
    total: int
    page: int
    per_page: int

# Schemas for Users
class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: UserRole

class UserCreate(UserBase):
    password: str
    is_active: Optional[bool] = True

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Schemas for Programs
class ProgramBase(BaseModel):
    name: str
    description: Optional[str] = None
    trainer_id: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class ProgramCreate(ProgramBase):
    pass

class ProgramUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trainer_id: Optional[int] = None
    is_active: Optional[bool] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class ProgramResponse(ProgramBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Schemas for Enrollments
class UserBasic(BaseModel):
    id: int
    full_name: str

class ProgramBasic(BaseModel):
    id: int
    name: str

class CoachBasic(BaseModel):
    id: int
    full_name: str

class EnrollmentBase(BaseModel):
    user_id: int
    program_id: int
    coach_id: int
    notes: Optional[str] = None

class EnrollmentCreate(EnrollmentBase):
    pass

class EnrollmentUpdate(BaseModel):
    coach_id: Optional[int] = None
    status: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    notes: Optional[str] = None

class EnrollmentResponse(EnrollmentBase):
    id: int
    status: str
    enrolled_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    user: UserBasic
    program: ProgramBasic
    coach: CoachBasic

    class Config:
        from_attributes = True

class EnrollmentStatsResponse(BaseModel):
    total_enrollments: int
    active_enrollments: int
    enrolled_count: int
    active_count: int
    completed_count: int
    withdrawn_count: int
    completion_rate: float
