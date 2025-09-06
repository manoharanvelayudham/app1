# routers/predictive.py - Predictive Analytics & Progress Tracking API

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Path, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import statistics
import json
from enum import Enum

# Import your database dependencies
from database import get_db
from models import (
    User, Program, ParticipantProgress, ProgramAnalytics, 
    PredictiveAnalysis, CustomReportConfig, CompetencyMapping,
    PredictionType, ProgressStatus, CompetencyLevel, ReportType
)
from auth import get_current_user, check_permissions

router = APIRouter(prefix="/predictive", tags=["Predictive Analytics"])

# ================================
# PYDANTIC MODELS FOR REQUESTS/RESPONSES
# ================================

class PredictiveInsightResponse(BaseModel):
    prediction_id: str
    prediction_type: PredictionType
    prediction_value: float
    confidence_level: float
    prediction_horizon_days: int
    supporting_evidence: Dict[str, Any]
    intervention_suggestions: List[Dict[str, Any]]
    
    class Config:
        from_attributes = True

class ProgressTrackingResponse(BaseModel):
    progress_id: str
    user_id: str
    program_id: str
    current_phase: str
    completion_percentage: float
    status: ProgressStatus
    key_metrics: Dict[str, float]
    predictions: List[PredictiveInsightResponse]
    trends: Dict[str, Any]
    
    class Config:
        from_attributes = True

class CompetencyHeatmapCell(BaseModel):
    competency_name: str
    current_level: CompetencyLevel
    current_score: float
    improvement_rate: float
    target_score: Optional[float]
    status: str  # "progressing", "stalled", "at_target"
    color_intensity: float  # 0-1 for heatmap visualization

class CompetencyHeatmapResponse(BaseModel):
    user_id: str
    program_id: str
    competencies: List[CompetencyHeatmapCell]
    overall_progress: float
    areas_of_strength: List[str]
    areas_for_development: List[str]
    recommendations: List[Dict[str, Any]]

class CustomReportRequest(BaseModel):
    report_name: str
    report_type: ReportType
    program_id: Optional[str] = None
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    participant_filters: Optional[Dict[str, Any]] = None
    metric_selections: List[str]
    chart_types: Optional[List[str]] = None
    grouping_options: Optional[Dict[str, Any]] = None
    is_automated: bool = False
    schedule_frequency: Optional[str] = None

class TrendAnalysisResponse(BaseModel):
    metric_name: str
    trend_direction: str  # "increasing", "decreasing", "stable"
    trend_strength: float  # 0-1
    data_points: List[Dict[str, Any]]
    forecast: List[Dict[str, Any]]
    statistical_significance: float
    confidence_interval: Dict[str, float]
