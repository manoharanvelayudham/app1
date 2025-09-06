from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, EmailStr, validator


# ----------------------------- User Schemas -----------------------------
class UserRoleEnum(str, Enum):
    CLIENT = "client"
    TRAINER = "trainer"
    ADMIN = "admin"


class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    role: UserRoleEnum


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    role: Optional[UserRoleEnum] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserBasic(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    role: UserRoleEnum

    class Config:
        from_attributes = True


class CoachBasic(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr

    class Config:
        from_attributes = True


# ----------------------------- Program Schemas -----------------------------
class ProgramBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    duration_weeks: int = Field(..., ge=1, le=52)
    price: float = Field(..., ge=0)
    max_participants: Optional[int] = Field(None, ge=1)
    expiry_date: Optional[date] = None

    @validator("expiry_date")
    def expiry_must_be_future(cls, v):
        if v and v <= date.today():
            raise ValueError("Expiry date must be in the future")
        return v


class ProgramCreate(ProgramBase):
    pass


class ProgramUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    duration_weeks: Optional[int] = Field(None, ge=1, le=52)
    price: Optional[float] = Field(None, ge=0)
    max_participants: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None
    expiry_date: Optional[date] = None

    @validator("expiry_date")
    def expiry_must_be_future(cls, v):
        if v and v <= date.today():
            raise ValueError("Expiry date must be in the future")
        return v


class ProgramResponse(ProgramBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_expired: bool = Field(default=False)

    class Config:
        from_attributes = True


class ProgramBasic(BaseModel):
    id: int
    name: str
    duration_weeks: int
    price: float
    is_active: bool
    expiry_date: Optional[date] = None

    class Config:
        from_attributes = True


class ProgramStatsResponse(BaseModel):
    total_programs: int
    active_programs: int
    inactive_programs: int
    expired_programs: int
    programs_expiring_soon: int  # within 30 days


# ----------------------------- Enrollment Schemas -----------------------------
class EnrollmentStatusEnum(str, Enum):
    ENROLLED = "ENROLLED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    WITHDRAWN = "WITHDRAWN"


class EnrollmentBase(BaseModel):
    user_id: int
    program_id: int
    coach_id: int
    notes: Optional[str] = Field(None, max_length=1000)


class EnrollmentCreate(EnrollmentBase):
    pass


class EnrollmentUpdate(BaseModel):
    coach_id: Optional[int] = None
    status: Optional[EnrollmentStatusEnum] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=1000)


class EnrollmentResponse(BaseModel):
    id: int
    user_id: int
    program_id: int
    coach_id: int
    status: EnrollmentStatusEnum
    enrolled_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    # relationship data
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


# ----------------------------- Authentication Schemas -----------------------------
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# ----------------------------- Password Reset -----------------------------
class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


# ----------------------------- Dashboard -----------------------------
class DashboardStats(BaseModel):
    total_users: int
    total_coaches: int
    total_programs: int
    total_enrollments: int
    active_enrollments: int


# ----------------------------- Response / Audit -----------------------------
class ResponseStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    REVIEWED = "REVIEWED"
    ARCHIVED = "ARCHIVED"


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


class AutoSaveRequest(BaseModel):
    response_id: int
    draft_content: Dict[str, Any] = Field(..., description="Draft content to auto-save")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class AutoSaveResponse(BaseModel):
    success: bool
    response_id: int
    last_auto_save: datetime
    auto_save_count: int
    version: int
    message: Optional[str] = None


class StatusUpdateRequest(BaseModel):
    status: ResponseStatus
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class StatusUpdateResponse(BaseModel):
    success: bool
    response_id: int
    old_status: ResponseStatus
    new_status: ResponseStatus
    updated_at: datetime
    message: Optional[str] = None


class ResponseStatusInfo(BaseModel):
    response_id: int
    status: ResponseStatus
    last_updated: datetime
    last_auto_save: Optional[datetime]
    auto_save_count: int
    version: int
    is_draft_available: bool


class ParticipantResponseDetail(BaseModel):
    id: int
    participant_id: int
    program_id: int
    question_id: Optional[int]
    text_content: Optional[str]
    status: ResponseStatus
    submitted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    last_auto_save: Optional[datetime]
    auto_save_count: int
    is_auto_saved: bool
    version: int
    draft_content: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class AuditLogEntry(BaseModel):
    id: int
    user_id: Optional[int]
    action: AuditAction
    resource_type: str
    resource_id: Optional[int]
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]
    timestamp: datetime
    metadata: Dict[str, Any]


class AuditLogResponse(BaseModel):
    logs: List[AuditLogEntry]
    total: int
    page: int
    per_page: int
