from enum import Enum as PyEnum
import enum
from datetime import datetime
import pytz
import uuid
import statistics
from typing import Dict, Any, List

from sqlalchemy import (
    Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Text,
    Enum as SQLEnum, LargeBinary, Index, UniqueConstraint, and_, desc, text, JSON
)
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func

from app.database import Base


# --- Enums ---
class UserRole(enum.Enum):
    CLIENT = "client"
    TRAINER = "trainer"
    ADMIN = "admin"


class ProgramDifficulty(enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class AssessmentType(enum.Enum):
    INITIAL = "initial"
    PROGRESS = "progress"
    FINAL = "final"


class ResponseType(enum.Enum):
    TEXT = "text"
    FILE = "file"
    IMAGE = "image"
    AUDIO = "audio"


class ReviewStatus(str, PyEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ResponseStatus(enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    REVIEWED = "REVIEWED"
    ARCHIVED = "ARCHIVED"


class EnrollmentStatus(enum.Enum):
    ENROLLED = "ENROLLED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    WITHDRAWN = "WITHDRAWN"


class AuditAction(enum.Enum):
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


class AIProcessingStatus(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class AIInputType(enum.Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    DOCUMENT = "DOCUMENT"


# --- New Enums for AI Insights ---
class InsightType(str, PyEnum):
    PERSONALITY = "personality"
    COMPETENCY_GAP = "competency_gap"
    BEHAVIORAL_PATTERN = "behavioral_pattern"
    LEARNING_STYLE = "learning_style"
    ENGAGEMENT_PATTERN = "engagement_pattern"


class RecommendationPriority(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class RecommendationStatus(str, PyEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISMISSED = "dismissed"


# --- Additional Enums for Predictive Analytics ---
class PredictionType(str, PyEnum):
    COMPLETION_LIKELIHOOD = "completion_likelihood"
    PERFORMANCE_TREND = "performance_trend"
    ENGAGEMENT_FORECAST = "engagement_forecast"
    SKILL_PROGRESSION = "skill_progression"
    DROPOUT_RISK = "dropout_risk"
    OPTIMAL_TIMING = "optimal_timing"


class ProgressStatus(str, PyEnum):
    ON_TRACK = "on_track"
    AHEAD = "ahead"
    BEHIND = "behind"
    AT_RISK = "at_risk"
    STALLED = "stalled"
    ACCELERATING = "accelerating"


class CompetencyLevel(str, PyEnum):
    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class ReportType(str, PyEnum):
    INDIVIDUAL_PROGRESS = "individual_progress"
    COHORT_ANALYSIS = "cohort_analysis"
    COMPETENCY_MATRIX = "competency_matrix"
    PREDICTIVE_INSIGHTS = "predictive_insights"
    PROGRAM_EFFECTIVENESS = "program_effectiveness"
    CUSTOM_DASHBOARD = "custom_dashboard"


# --- System Monitoring Enums ---
class ConfigScope(str, PyEnum):
    GLOBAL = "global"
    TENANT = "tenant"
    USER = "user"
    PROGRAM = "program"


class ConfigType(str, PyEnum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    ENCRYPTED = "encrypted"


class HealthStatus(str, PyEnum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ComponentType(str, PyEnum):
    DATABASE = "database"
    API = "api"
    ML_SERVICE = "ml_service"
    STORAGE = "storage"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    ANALYTICS = "analytics"


# --- Models ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.CLIENT)
    is_active = Column(Boolean, default=True, nullable=False)
    phone = Column(String(20), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    enrollments = relationship("Enrollment", back_populates="user")
    assessments = relationship("Assessment", back_populates="user")
    created_programs = relationship("Program", back_populates="trainer", foreign_keys="Program.trainer_id")
    audit_logs = relationship("AuditLog", back_populates="user")
    ai_insights = relationship("AIInsight", back_populates="user")
    coaching_recommendations = relationship("CoachingRecommendation", back_populates="user")

    # New relationships
    progress_records = relationship("ParticipantProgress", back_populates="user")
    predictive_analyses = relationship("PredictiveAnalysis", back_populates="user")
    competency_mappings = relationship("CompetencyMapping", back_populates="user")
    created_reports = relationship("CustomReportConfig", back_populates="creator")


class Program(Base):
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    difficulty = Column(SQLEnum(ProgramDifficulty), nullable=False)
    duration_weeks = Column(Integer, nullable=False)
    trainer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    max_participants = Column(Integer, default=20)
    price = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    trainer = relationship("User", back_populates="created_programs", foreign_keys=[trainer_id])
    enrollments = relationship("Enrollment", back_populates="program")
    ai_insights = relationship("AIInsight", back_populates="program")
    coaching_recommendations = relationship("CoachingRecommendation", back_populates="program")

    # New relationships
    participant_progress = relationship("ParticipantProgress", back_populates="program")
    analytics_records = relationship("ProgramAnalytics", back_populates="program")
    predictive_analyses = relationship("PredictiveAnalysis", back_populates="program")
    competency_mappings = relationship("CompetencyMapping", back_populates="program")
    custom_reports = relationship("CustomReportConfig", back_populates="program")


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=False)
    enrollment_date = Column(DateTime(timezone=True), server_default=func.now())
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    progress_percentage = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    status = Column(SQLEnum(EnrollmentStatus), default=EnrollmentStatus.ENROLLED)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="enrollments")
    program = relationship("Program", back_populates="enrollments")
    responses = relationship("ParticipantResponse", back_populates="enrollment")


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assessment_type = Column(SQLEnum(AssessmentType), nullable=False)
    assessment_date = Column(DateTime(timezone=True), server_default=func.now())

    # Physical measurements
    weight = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    body_fat_percentage = Column(Float, nullable=True)
    muscle_mass = Column(Float, nullable=True)

    # Fitness metrics
    cardio_endurance_score = Column(Integer, nullable=True)
    strength_score = Column(Integer, nullable=True)
    flexibility_score = Column(Integer, nullable=True)

    fitness_goals = Column(Text, nullable=True)
    trainer_notes = Column(Text, nullable=True)
    client_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="assessments")


class ParticipantResponse(Base):
    __tablename__ = "participant_responses"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False)
    response_type = Column(SQLEnum(ResponseType), nullable=False)

    # Content
    text_content = Column(Text, nullable=True)
    file_name = Column(String(255), nullable=True)
    file_content = Column(LargeBinary, nullable=True)
    file_mime_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)

    # Metadata
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    submission_notes = Column(Text, nullable=True)

    # Auto-save and status
    status = Column(SQLEnum(ResponseStatus), default=ResponseStatus.DRAFT, index=True)
    last_auto_save = Column(DateTime(timezone=True), nullable=True)
    auto_save_count = Column(Integer, default=0)
    is_auto_saved = Column(Boolean, default=False)
    draft_content = Column(JSONB, nullable=True)
    version = Column(Integer, default=1)

    enrollment = relationship("Enrollment", back_populates="responses")
    reviews = relationship("CoachReview", back_populates="response")
    ai_processing = relationship("AIProcessing", back_populates="response", cascade="all, delete-orphan")


class AIProcessing(Base):
    """AI Processing Pipeline tracking table"""

    __tablename__ = "ai_processing"

    id = Column(Integer, primary_key=True, index=True)
    response_id = Column(Integer, ForeignKey("participant_responses.id", ondelete="CASCADE"), nullable=False, index=True)
    processing_status = Column(SQLEnum(AIProcessingStatus), nullable=False, default=AIProcessingStatus.PENDING, index=True)
    input_type = Column(SQLEnum(AIInputType), nullable=False, index=True)

    # Content storage
    original_content = Column(JSONB, nullable=True)
    processed_content = Column(JSONB, nullable=True)
    standardized_text = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)

    # Processing tracking
    processing_steps = Column(JSONB, nullable=True, default=list)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    response = relationship("ParticipantResponse", back_populates="ai_processing")


class CoachReview(Base):
    __tablename__ = "coach_reviews"

    id = Column(Integer, primary_key=True, index=True)
    response_id = Column(Integer, ForeignKey("participant_responses.id"), nullable=False)
    coach_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    score = Column(Float, nullable=True)
    max_score = Column(Float, default=100.0)
    comments = Column(Text, nullable=True)

    status = Column(SQLEnum(ReviewStatus), default=ReviewStatus.PENDING)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    response = relationship("ParticipantResponse", back_populates="reviews")
    coach = relationship("User", foreign_keys=[coach_id])

    __table_args__ = (
        UniqueConstraint("response_id", "coach_id", name="unique_coach_response_review"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(SQLEnum(AuditAction), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(Integer, nullable=True, index=True)
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    session_id = Column(String(255), nullable=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC), index=True)
    details = Column(JSONB, default=dict)

    user = relationship("User", back_populates="audit_logs")


# --- New Models ---
class AIInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(Integer, primary_key=True, index=True)
    insight_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=True, index=True)

    insight_type = Column(SQLEnum(InsightType), nullable=False, index=True)
    category = Column(String(100), nullable=False)
    subcategory = Column(String(100), nullable=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    key_findings = Column(JSONB, nullable=True)
    supporting_data = Column(JSONB, nullable=True)

    confidence_score = Column(Float, nullable=False, default=0.0)
    impact_score = Column(Float, nullable=False, default=0.0)
    reliability_score = Column(Float, nullable=False, default=0.0)

    analysis_start_date = Column(DateTime, nullable=False)
    analysis_end_date = Column(DateTime, nullable=False)
    data_points_analyzed = Column(Integer, nullable=False, default=0)

    is_active = Column(Boolean, default=True)
    is_actionable = Column(Boolean, default=True)
    tags = Column(JSONB, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="ai_insights")
    program = relationship("Program", back_populates="ai_insights")
    coaching_recommendations = relationship("CoachingRecommendation", back_populates="ai_insight")


class CoachingRecommendation(Base):
    __tablename__ = "coaching_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=True, index=True)
    ai_insight_id = Column(Integer, ForeignKey("ai_insights.id"), nullable=True, index=True)

    category = Column(String(100), nullable=False, index=True)
    priority = Column(SQLEnum(RecommendationPriority), nullable=False, index=True, default=RecommendationPriority.MEDIUM)
    status = Column(SQLEnum(RecommendationStatus), nullable=False, index=True, default=RecommendationStatus.PENDING)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    rationale = Column(Text, nullable=False)
    expected_outcome = Column(Text, nullable=True)

    action_items = Column(JSONB, nullable=True)
    resources = Column(JSONB, nullable=True)
    timeline = Column(String(100), nullable=True)

    potential_impact = Column(Float, nullable=False, default=0.0)
    difficulty_level = Column(Float, nullable=False, default=0.5)
    confidence_score = Column(Float, nullable=False, default=0.0)

    progress_percentage = Column(Float, default=0.0)
    last_progress_update = Column(DateTime, nullable=True)
    completion_date = Column(DateTime, nullable=True)

    user_rating = Column(Float, nullable=True)
    user_feedback = Column(Text, nullable=True)
    is_bookmarked = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="coaching_recommendations")
    program = relationship("Program", back_populates="coaching_recommendations")
    ai_insight = relationship("AIInsight", back_populates="coaching_recommendations")


# --- Predictive Analytics Models ---
class ParticipantProgress(Base):
    __tablename__ = "participant_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=False)

    current_phase = Column(String(100), nullable=False)
    completion_percentage = Column(Float, default=0.0)
    total_sessions_completed = Column(Integer, default=0)
    total_time_spent_minutes = Column(Integer, default=0)

    average_rating = Column(Float, nullable=True)
    consistency_score = Column(Float, default=0.0)
    engagement_score = Column(Float, default=0.0)
    improvement_rate = Column(Float, default=0.0)

    status = Column(SQLEnum(ProgressStatus), default=ProgressStatus.ON_TRACK)
    days_since_last_activity = Column(Integer, default=0)
    streak_count = Column(Integer, default=0)
    milestone_count = Column(Integer, default=0)

    predicted_completion_date = Column(DateTime, nullable=True)
    dropout_risk_score = Column(Float, default=0.0)
    success_probability = Column(Float, default=0.5)
    optimal_session_frequency = Column(Float, nullable=True)

    preferred_learning_times = Column(JSONB, nullable=True)
    response_patterns = Column(JSONB, nullable=True)
    difficulty_areas = Column(JSONB, nullable=True)
    strength_areas = Column(JSONB, nullable=True)

    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, default=func.now())
    data_freshness = Column(DateTime, default=func.now())
    calculation_confidence = Column(Float, default=0.5)

    user = relationship("User", back_populates="progress_records")
    program = relationship("Program", back_populates="participant_progress")
    predictions = relationship("PredictiveAnalysis", back_populates="participant_progress")


class ProgramAnalytics(Base):
    __tablename__ = "program_analytics"

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=False)

    total_participants = Column(Integer, default=0)
    active_participants = Column(Integer, default=0)
    completed_participants = Column(Integer, default=0)
    dropout_count = Column(Integer, default=0)

    average_completion_rate = Column(Float, default=0.0)
    average_satisfaction_rating = Column(Float, nullable=True)
    average_time_to_completion_days = Column(Integer, nullable=True)
    median_session_duration_minutes = Column(Integer, nullable=True)

    total_sessions_conducted = Column(Integer, default=0)
    average_sessions_per_participant = Column(Float, default=0.0)
    peak_activity_hours = Column(JSONB, nullable=True)
    engagement_trend = Column(String(20), nullable=True)

    top_performing_areas = Column(JSONB, nullable=True)
    improvement_needed_areas = Column(JSONB, nullable=True)
    skill_development_rates = Column(JSONB, nullable=True)
    competency_distribution = Column(JSONB, nullable=True)

    projected_completion_rate = Column(Float, nullable=True)
    estimated_optimal_duration_weeks = Column(Integer, nullable=True)
    success_factors = Column(JSONB, nullable=True)
    risk_factors = Column(JSONB, nullable=True)

    industry_benchmark_comparison = Column(JSONB, nullable=True)
    historical_performance_trend = Column(JSONB, nullable=True)
    cohort_comparisons = Column(JSONB, nullable=True)

    content_effectiveness_scores = Column(JSONB, nullable=True)
    participant_feedback_summary = Column(JSONB, nullable=True)
    improvement_recommendations = Column(JSONB, nullable=True)

    analysis_period_start = Column(DateTime, nullable=False)
    analysis_period_end = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    data_points_analyzed = Column(Integer, default=0)
    confidence_score = Column(Float, default=0.5)

    program = relationship("Program", back_populates="analytics_records")


class PredictiveAnalysis(Base):
    __tablename__ = "predictive_analysis"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=False)
    progress_id = Column(Integer, ForeignKey("participant_progress.id"), nullable=True)

    prediction_type = Column(SQLEnum(PredictionType), nullable=False)
    prediction_value = Column(Float, nullable=False)
    confidence_level = Column(Float, nullable=False)
    probability_distribution = Column(JSONB, nullable=True)

    model_version = Column(String(50), nullable=False)
    features_used = Column(JSONB, nullable=False)
    feature_importance = Column(JSONB, nullable=True)
    supporting_evidence = Column(JSONB, nullable=True)

    prediction_date = Column(DateTime, default=func.now())
    prediction_horizon_days = Column(Integer, nullable=False)
    expiry_date = Column(DateTime, nullable=True)

    scenario_conditions = Column(JSONB, nullable=True)
    alternative_outcomes = Column(JSONB, nullable=True)
    intervention_suggestions = Column(JSONB, nullable=True)

    actual_outcome = Column(Float, nullable=True)
    prediction_accuracy = Column(Float, nullable=True)
    is_validated = Column(Boolean, default=False)
    validation_date = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=func.now())
    created_by_model = Column(String(100), nullable=False)
    computation_time_ms = Column(Integer, nullable=True)

    user = relationship("User", back_populates="predictive_analyses")
    program = relationship("Program", back_populates="predictive_analyses")
    participant_progress = relationship("ParticipantProgress", back_populates="predictions")


class CustomReportConfig(Base):
    __tablename__ = "custom_report_configs"

    id = Column(Integer, primary_key=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=True)

    report_name = Column(String(200), nullable=False)
    report_type = Column(SQLEnum(ReportType), nullable=False)
    description = Column(Text, nullable=True)

    date_range_start = Column(DateTime, nullable=True)
    date_range_end = Column(DateTime, nullable=True)
    participant_filters = Column(JSONB, nullable=True)
    metric_selections = Column(JSONB, nullable=False)

    chart_types = Column(JSONB, nullable=True)
    grouping_options = Column(JSONB, nullable=True)
    comparison_settings = Column(JSONB, nullable=True)

    is_automated = Column(Boolean, default=False)
    schedule_frequency = Column(String(50), nullable=True)
    next_generation_date = Column(DateTime, nullable=True)
    recipients = Column(JSONB, nullable=True)

    is_template = Column(Boolean, default=False)
    is_public = Column(Boolean, default=False)
    usage_count = Column(Integer, default=0)
    last_generated = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    creator = relationship("User", back_populates="created_reports")
    program = relationship("Program", back_populates="custom_reports")


class CompetencyMapping(Base):
    __tablename__ = "competency_mappings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=False)

    competency_name = Column(String(200), nullable=False)
    competency_category = Column(String(100), nullable=True)
    competency_description = Column(Text, nullable=True)

    current_level = Column(SQLEnum(CompetencyLevel), default=CompetencyLevel.NOVICE)
    current_score = Column(Float, nullable=False)
    assessment_date = Column(DateTime, default=func.now())
    assessment_confidence = Column(Float, default=0.5)

    initial_score = Column(Float, nullable=True)
    previous_score = Column(Float, nullable=True)
    score_change = Column(Float, default=0.0)
    improvement_rate = Column(Float, default=0.0)

    target_level = Column(SQLEnum(CompetencyLevel), nullable=True)
    target_score = Column(Float, nullable=True)
    target_date = Column(DateTime, nullable=True)
    progression_plan = Column(JSONB, nullable=True)

    supporting_activities = Column(JSONB, nullable=True)
    evidence_sources = Column(JSONB, nullable=True)
    peer_assessments = Column(JSONB, nullable=True)
    self_assessment = Column(Float, nullable=True)

    predicted_next_level = Column(SQLEnum(CompetencyLevel), nullable=True)
    predicted_achievement_date = Column(DateTime, nullable=True)
    development_recommendations = Column(JSONB, nullable=True)
    skill_dependencies = Column(JSONB, nullable=True)

    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    requires_validation = Column(Boolean, default=False)

    user = relationship("User", back_populates="competency_mappings")
    program = relationship("Program", back_populates="competency_mappings")


# --- Indexes ---
Index("idx_enrollment_user_program", Enrollment.user_id, Enrollment.program_id)
Index("idx_assessment_user_type", Assessment.user_id, Assessment.assessment_type)
Index("idx_program_trainer_active", Program.trainer_id, Program.is_active)
Index("idx_user_role_active", User.role, User.is_active)
Index("idx_response_enrollment_type", ParticipantResponse.enrollment_id, ParticipantResponse.response_type)
Index("idx_response_submitted_at", ParticipantResponse.submitted_at)


# --- Utility ---
def create_audit_log(
    db_session,
    user_id: int = None,
    action: AuditAction = None,
    resource_type: str = None,
    resource_id: int = None,
    old_values: dict = None,
    new_values: dict = None,
    ip_address: str = None,
    user_agent: str = None,
    session_id: str = None,
    details: dict = None,
):
    """Utility function to create audit log entries"""
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        old_values=old_values or {},
        new_values=new_values or {},
        ip_address=ip_address,
        user_agent=user_agent,
        session_id=session_id,
        details=details or {},
    )
    db_session.add(audit_log)
    return audit_log


# --- Predictive Analytics Utility Functions ---

def get_user_progress_summary(user_id: str, db: Session) -> Dict[str, Any]:
    """Get comprehensive progress summary for a user"""
    
    progress_records = db.query(ParticipantProgress).filter(
        ParticipantProgress.user_id == user_id
    ).all()
    
    if not progress_records:
        return {"message": "No progress data found"}
    
    total_programs = len(progress_records)
    completed_programs = len([p for p in progress_records if p.completion_percentage >= 100])
    average_completion = statistics.mean([p.completion_percentage for p in progress_records])
    
    return {
        "user_id": user_id,
        "total_programs": total_programs,
        "completed_programs": completed_programs,
        "completion_rate": (completed_programs / total_programs) * 100 if total_programs > 0 else 0,
        "average_progress": average_completion,
        "total_time_invested_hours": sum([p.total_time_spent_minutes for p in progress_records]) / 60,
        "total_sessions": sum([p.total_sessions_completed for p in progress_records]),
        "overall_engagement": statistics.mean([p.engagement_score for p in progress_records]) if progress_records else 0
    }


def get_program_health_metrics(program_id: str, db: Session) -> Dict[str, Any]:
    """Get program health and performance metrics"""
    
    analytics = db.query(ProgramAnalytics).filter(
        ProgramAnalytics.program_id == program_id
    ).order_by(desc(ProgramAnalytics.created_at)).first()
    
    if not analytics:
        return {"message": "No analytics data found"}
    
    # Calculate health score based on multiple factors
    completion_factor = min(1.0, analytics.average_completion_rate / 80)  # Target 80% completion
    satisfaction_factor = (analytics.average_satisfaction_rating or 3.0) / 5.0
    retention_factor = 1 - (analytics.dropout_count / max(1, analytics.total_participants))
    engagement_trend_factor = 1.0 if analytics.engagement_trend == "increasing" else 0.8 if analytics.engagement_trend == "stable" else 0.6
    
    health_score = (completion_factor * 0.3 + satisfaction_factor * 0.3 + retention_factor * 0.25 + engagement_trend_factor * 0.15) * 100
    
    # Determine health status
    if health_score >= 85:
        health_status = "excellent"
    elif health_score >= 70:
        health_status = "good"
    elif health_score >= 55:
        health_status = "fair"
    else:
        health_status = "poor"
    
    return {
        "program_id": program_id,
        "health_score": round(health_score, 1),
        "health_status": health_status,
        "key_metrics": {
            "total_participants": analytics.total_participants,
            "completion_rate": analytics.average_completion_rate,
            "satisfaction_rating": analytics.average_satisfaction_rating,
            "dropout_rate": (analytics.dropout_count / max(1, analytics.total_participants)) * 100,
            "engagement_trend": analytics.engagement_trend
        },
        "recommendations": _get_program_improvement_recommendations(analytics)
    }


def _get_program_improvement_recommendations(analytics: ProgramAnalytics) -> List[str]:
    """Generate improvement recommendations based on program analytics"""
    
    recommendations = []
    
    # Low completion rate
    if analytics.average_completion_rate < 60:
        recommendations.append("Consider breaking content into smaller, more manageable modules")
        recommendations.append("Add more interactive elements to maintain engagement")
    
    # High dropout rate
    dropout_rate = (analytics.dropout_count / max(1, analytics.total_participants)) * 100
    if dropout_rate > 20:
        recommendations.append("Implement early intervention system for at-risk participants")
        recommendations.append("Review program difficulty and pacing")
    
    # Low satisfaction
    if analytics.average_satisfaction_rating and analytics.average_satisfaction_rating < 3.5:
        recommendations.append("Collect detailed feedback to identify specific pain points")
        recommendations.append("Consider updating content based on participant preferences")
    
    # Declining engagement
    if analytics.engagement_trend == "decreasing":
        recommendations.append("Add gamification elements to boost motivation")
        recommendations.append("Facilitate more peer interaction and collaboration")
    
    return recommendations


def calculate_competency_progression_rate(user_id: str, competency_name: str, db: Session) -> float:
    """Calculate the rate of improvement for a specific competency"""
    
    competency_records = db.query(CompetencyMapping).filter(
        and_(
            CompetencyMapping.user_id == user_id,
            CompetencyMapping.competency_name == competency_name
        )
    ).order_by(CompetencyMapping.assessment_date).all()
    
    if len(competency_records) < 2:
        return 0.0
    
    # Calculate improvement rate (points per day)
    first_record = competency_records[0]
    latest_record = competency_records[-1]
    
    score_change = latest_record.current_score - first_record.current_score
    days_elapsed = (latest_record.assessment_date - first_record.assessment_date).days
    
    if days_elapsed == 0:
        return 0.0
    
    return score_change / days_elapsed


def get_predictive_accuracy_metrics(db: Session) -> Dict[str, Any]:
    """Calculate accuracy metrics for predictive models"""
    
    # Get predictions that have actual outcomes
    validated_predictions = db.query(PredictiveAnalysis).filter(
        and_(
            PredictiveAnalysis.is_validated == True,
            PredictiveAnalysis.actual_outcome.isnot(None)
        )
    ).all()
    
    if not validated_predictions:
        return {"message": "No validated predictions available"}
    
    # Calculate accuracy by prediction type
    accuracy_by_type = {}
    
    for pred_type in PredictionType:
        type_predictions = [p for p in validated_predictions if p.prediction_type == pred_type]
        
        if type_predictions:
            accuracies = []
            for pred in type_predictions:
                # Calculate absolute percentage error
                error = abs(pred.prediction_value - pred.actual_outcome)
                accuracy = max(0, 1 - error)  # 1 = perfect, 0 = completely wrong
                accuracies.append(accuracy)
            
            accuracy_by_type[pred_type.value] = {
                "average_accuracy": statistics.mean(accuracies),
                "sample_size": len(accuracies),
                "confidence_range": {
                    "min": min(accuracies),
                    "max": max(accuracies)
                }
            }
    
    overall_accuracy = statistics.mean([
        metrics["average_accuracy"] for metrics in accuracy_by_type.values()
    ]) if accuracy_by_type else 0
    
    return {
        "overall_accuracy": overall_accuracy,
        "accuracy_by_prediction_type": accuracy_by_type,
        "total_validated_predictions": len(validated_predictions),
        "model_performance_status": "excellent" if overall_accuracy > 0.8 else 
                                   "good" if overall_accuracy > 0.7 else 
                                   "fair" if overall_accuracy > 0.6 else "poor"
    }


# Database indexing optimization for analytics queries
def create_analytics_indexes(engine):
    """Create database indexes to optimize analytics queries"""
    
    with engine.connect() as conn:
        # Participant Progress indexes
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_progress_user_status 
            ON participant_progress(user_id, status);
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_progress_completion_date 
            ON participant_progress(completion_percentage, last_updated);
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_progress_engagement 
            ON participant_progress(engagement_score, consistency_score);
        """))
        
        # Predictive Analysis indexes
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_prediction_confidence 
            ON predictive_analysis(prediction_type, confidence_level);
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_prediction_validation 
            ON predictive_analysis(is_validated, prediction_accuracy);
        """))
        
        # Competency Mapping indexes  
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_competency_score_date 
            ON competency_mappings(current_score, assessment_date);
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_competency_improvement 
            ON competency_mappings(improvement_rate, current_level);
        """))
        
        conn.commit()
        print("Analytics database indexes created successfully")


# Add this to your database initialization
def init_analytics_database(engine):
    """Initialize analytics database with indexes and constraints"""
    
    # Create tables
    from models import Base
    Base.metadata.create_all(bind=engine)
    
    # Create optimized indexes
    create_analytics_indexes(engine)
    
    # Add any additional constraints
    with engine.connect() as conn:
        # Ensure positive scores
        conn.execute(text("""
            ALTER TABLE participant_progress 
            ADD CONSTRAINT check_positive_completion 
            CHECK (completion_percentage >= 0 AND completion_percentage <= 100);
        """))
        
        conn.execute(text("""
            ALTER TABLE competency_mappings 
            ADD CONSTRAINT check_positive_score 
            CHECK (current_score >= 0 AND current_score <= 100);
        """))
        
        conn.commit()


# Helper functions for data validation
def validate_progress_data(progress_data: Dict[str, Any]) -> List[str]:
    """Validate progress data before saving"""
    
    errors = []
    
    if progress_data.get("completion_percentage", 0) < 0 or progress_data.get("completion_percentage", 0) > 100:
        errors.append("Completion percentage must be between 0 and 100")
    
    if progress_data.get("engagement_score", 0) < 0 or progress_data.get("engagement_score", 0) > 1:
        errors.append("Engagement score must be between 0 and 1")
    
    if progress_data.get("consistency_score", 0) < 0 or progress_data.get("consistency_score", 0) > 1:
        errors.append("Consistency score must be between 0 and 1")
    
    if progress_data.get("total_sessions_completed", 0) < 0:
        errors.append("Total sessions completed cannot be negative")
    
    if progress_data.get("total_time_spent_minutes", 0) < 0:
        errors.append("Total time spent cannot be negative")
    
    return errors


def validate_competency_data(competency_data: Dict[str, Any]) -> List[str]:
    """Validate competency data before saving"""
    
    errors = []
    
    if competency_data.get("current_score", 0) < 0 or competency_data.get("current_score", 0) > 100:
        errors.append("Current score must be between 0 and 100")
    
    if competency_data.get("target_score") and (
        competency_data["target_score"] < 0 or competency_data["target_score"] > 100
    ):
        errors.append("Target score must be between 0 and 100")
    
    if not competency_data.get("competency_name", "").strip():
        errors.append("Competency name is required")
    
    return errors


# Analytics data export utilities
def export_analytics_to_csv(data: List[Dict[str, Any]], filename: str) -> str:
    """Export analytics data to CSV format"""
    
    import csv
    import io
    
    if not data:
        return ""
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    
    for row in data:
        # Flatten nested dictionaries and lists for CSV
        flat_row = {}
        for key, value in row.items():
            if isinstance(value, (dict, list)):
                flat_row[key] = str(value)
            else:
                flat_row[key] = value
        writer.writerow(flat_row)
    
    return output.getvalue()


def format_analytics_for_dashboard(analytics_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format analytics data for frontend dashboard consumption"""
    
    formatted_data = {
        "summary": {
            "total_users": analytics_data.get("total_participants", 0),
            "completion_rate": f"{analytics_data.get('average_completion_rate', 0):.1f}%",
            "satisfaction": f"{analytics_data.get('average_satisfaction_rating', 0):.1f}/5.0",
            "engagement_trend": analytics_data.get("engagement_trend", "stable").title()
        },
        "charts": {
            "completion_distribution": analytics_data.get("completion_distribution", {}),
            "engagement_over_time": analytics_data.get("engagement_history", []),
            "competency_heatmap": analytics_data.get("competency_data", [])
        },
        "alerts": [],
        "recommendations": analytics_data.get("recommendations", [])
    }
    
    # Add alerts based on metrics
    if analytics_data.get("average_completion_rate", 0) < 50:
        formatted_data["alerts"].append({
            "type": "warning",
            "message": "Low completion rate detected",
            "priority": "high"
        })
    
    dropout_rate = analytics_data.get("dropout_count", 0) / max(1, analytics_data.get("total_participants", 1)) * 100
    if dropout_rate > 25:
        formatted_data["alerts"].append({
            "type": "danger",
            "message": f"High dropout rate: {dropout_rate:.1f}%",
            "priority": "urgent"
        })
    
    return formatted_data
