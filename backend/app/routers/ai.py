# routers/ai.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import statistics
from enum import Enum

from database import get_db
from models import (
    User, Program, Response, Review, AIInsight, CoachingRecommendation,
    ProgramEnrollment, InsightType, RecommendationPriority, RecommendationStatus
)
from auth import get_current_user, require_admin_or_program_creator, require_auth
from pydantic import BaseModel, Field

router = APIRouter(prefix="/ai", tags=["AI Insights & Recommendations"])

# Pydantic Models
class InsightResponse(BaseModel):
    id: int
    insight_id: str
    insight_type: str
    category: str
    subcategory: Optional[str]
    title: str
    description: str
    key_findings: Optional[List[str]]
    confidence_score: float
    impact_score: float
    analysis_period_days: int
    data_points_analyzed: int
    is_actionable: bool
    tags: Optional[List[str]]
    created_at: datetime
    
    class Config:
        from_attributes = True

class RecommendationResponse(BaseModel):
    id: int
    recommendation_id: str
    category: str
    priority: str
    status: str
    title: str
    description: str
    rationale: str
    expected_outcome: Optional[str]
    action_items: Optional[List[str]]
    resources: Optional[List[Dict[str, str]]]
    timeline: Optional[str]
    potential_impact: float
    difficulty_level: float
    confidence_score: float
    progress_percentage: float
    user_rating: Optional[float]
    is_bookmarked: bool
    created_at: datetime
    expires_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class GenerateInsightsRequest(BaseModel):
    analysis_days: int = Field(default=30, ge=7, le=365)
    include_personality: bool = True
    include_competency_gaps: bool = True
    include_behavioral_patterns: bool = True
    include_learning_style: bool = True
    minimum_confidence: float = Field(default=0.6, ge=0.0, le=1.0)

class CoachingSuggestionsRequest(BaseModel):
    user_id: Optional[int] = None
    program_id: Optional[int] = None
    priority_filter: Optional[str] = None
    category_filter: Optional[str] = None
    max_recommendations: int = Field(default=10, ge=1, le=50)
    include_completed: bool = False

# AI Insights Generation Endpoint
@router.post("/generate-insights/{participant_id}")
async def generate_insights(
    participant_id: int = Path(..., description="Participant ID to generate insights for"),
    request: GenerateInsightsRequest = GenerateInsightsRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate AI-driven insights for a participant based on their activity and responses.
    
    This endpoint analyzes user behavior, responses, and engagement patterns to generate
    actionable insights about personality traits, competency gaps, and learning patterns.
    """
    
    # Permission check: users can only access their own insights, admins/creators can access all
    if current_user.id != participant_id and current_user.role not in ['admin', 'program_creator']:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Verify participant exists
    participant = db.query(User).filter(User.id == participant_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Calculate analysis period
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=request.analysis_days)
    
    # Gather data for analysis
    responses = db.query(Response).filter(
        and_(
            Response.user_id == participant_id,
            Response.created_at >= start_date,
            Response.created_at <= end_date
        )
    ).all()
    
    reviews = db.query(Review).filter(
        and_(
            Review.user_id == participant_id,
            Review.created_at >= start_date,
            Review.created_at <= end_date
        )
    ).all()
    
    enrollments = db.query(ProgramEnrollment).filter(
        ProgramEnrollment.user_id == participant_id
    ).all()
    
    if not responses and not reviews:
        raise HTTPException(
            status_code=400, 
            detail="Insufficient data for analysis. Participant needs more activity."
        )
    
    # Generate insights using background task
    background_tasks.add_task(
        _generate_insights_background,
        db, participant_id, responses, reviews, enrollments,
        start_date, end_date, request
    )
    
    # Return existing insights immediately
    existing_insights = db.query(AIInsight).filter(
        and_(
            AIInsight.user_id == participant_id,
            AIInsight.is_active == True,
            AIInsight.confidence_score >= request.minimum_confidence
        )
    ).order_by(desc(AIInsight.created_at)).limit(20).all()
    
    return {
        "message": "Insights generation started",
        "participant_id": participant_id,
        "analysis_period": f"{request.analysis_days} days",
        "data_points": len(responses) + len(reviews),
        "existing_insights": [InsightResponse.from_orm(insight) for insight in existing_insights],
        "generating_new": True
    }

async def _generate_insights_background(
    db: Session,
    participant_id: int,
    responses: List[Response],
    reviews: List[Review],
    enrollments: List[ProgramEnrollment],
    start_date: datetime,
    end_date: datetime,
    request: GenerateInsightsRequest
):
    """Background task to generate AI insights"""
    
    insights_to_create = []
    
    # 1. Personality Analysis
    if request.include_personality:
        personality_insight = _analyze_personality(
            participant_id, responses, reviews, start_date, end_date
        )
        if personality_insight and personality_insight['confidence_score'] >= request.minimum_confidence:
            insights_to_create.append(personality_insight)
    
    # 2. Competency Gap Analysis
    if request.include_competency_gaps:
        competency_insights = _analyze_competency_gaps(
            participant_id, responses, reviews, enrollments, start_date, end_date
        )
        insights_to_create.extend([
            insight for insight in competency_insights 
            if insight['confidence_score'] >= request.minimum_confidence
        ])
    
    # 3. Behavioral Pattern Analysis
    if request.include_behavioral_patterns:
        behavioral_insights = _analyze_behavioral_patterns(
            participant_id, responses, reviews, start_date, end_date
        )
        insights_to_create.extend([
            insight for insight in behavioral_insights 
            if insight['confidence_score'] >= request.minimum_confidence
        ])
    
    # 4. Learning Style Analysis
    if request.include_learning_style:
        learning_insight = _analyze_learning_style(
            participant_id, responses, reviews, start_date, end_date
        )
        if learning_insight and learning_insight['confidence_score'] >= request.minimum_confidence:
            insights_to_create.append(learning_insight)
    
    # Save insights to database
    for insight_data in insights_to_create:
        db_insight = AIInsight(**insight_data)
        db.add(db_insight)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving insights: {e}")

# Coaching Suggestions Endpoint
@router.post("/coaching-suggestions")
async def get_coaching_suggestions(
    request: CoachingSuggestionsRequest = CoachingSuggestionsRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get AI-generated coaching recommendations based on user insights and behavior.
    
    Returns personalized coaching suggestions with priority levels and action items.
    """
    
    # Build base query
    query = db.query(CoachingRecommendation)
    
    # Apply filters based on user role and request
    if current_user.role == 'admin':
        # Admins can see all recommendations
        if request.user_id:
            query = query.filter(CoachingRecommendation.user_id == request.user_id)
        if request.program_id:
            query = query.filter(CoachingRecommendation.program_id == request.program_id)
    elif current_user.role == 'program_creator':
        # Program creators can see recommendations for their programs
        if request.program_id:
            # Verify program ownership
            program = db.query(Program).filter(
                and_(Program.id == request.program_id, Program.created_by == current_user.id)
            ).first()
            if not program:
                raise HTTPException(status_code=403, detail="Access denied to this program")
            query = query.filter(CoachingRecommendation.program_id == request.program_id)
        else:
            # Show recommendations for all their programs
            user_programs = db.query(Program.id).filter(Program.created_by == current_user.id).all()
            program_ids = [p.id for p in user_programs]
            query = query.filter(CoachingRecommendation.program_id.in_(program_ids))
    else:
        # Regular users can only see their own recommendations
        query = query.filter(CoachingRecommendation.user_id == current_user.id)
    
    # Apply additional filters
    if request.priority_filter:
        query = query.filter(CoachingRecommendation.priority == request.priority_filter)
    
    if request.category_filter:
        query = query.filter(CoachingRecommendation.category == request.category_filter)
    
    if not request.include_completed:
        query = query.filter(CoachingRecommendation.status != "completed")
    
    # Order by priority and impact
    priority_order = {
        'urgent': 4,
        'high': 3,
        'medium': 2,
        'low': 1
    }
    
    recommendations = query.order_by(
        desc(CoachingRecommendation.potential_impact),
        desc(CoachingRecommendation.created_at)
    ).limit(request.max_recommendations).all()
    
    # If no recommendations exist, generate some
    if not recommendations and current_user.role != 'admin':
        await _generate_recommendations_for_user(db, current_user.id)
        # Re-query after generation
        recommendations = query.limit(request.max_recommendations).all()
    
    return {
        "recommendations": [RecommendationResponse.from_orm(rec) for rec in recommendations],
        "total_count": len(recommendations),
        "filters_applied": {
            "user_id": request.user_id,
            "program_id": request.program_id,
            "priority": request.priority_filter,
            "category": request.category_filter,
            "include_completed": request.include_completed
        }
    }

# Get specific insight details
@router.get("/insights/{insight_id}")
async def get_insight_details(
    insight_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a specific AI insight"""
    
    insight = db.query(AIInsight).filter(AIInsight.insight_id == insight_id).first()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    # Permission check
    if (current_user.id != insight.user_id and 
        current_user.role not in ['admin', 'program_creator']):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # If program creator, verify they own the program
    if current_user.role == 'program_creator' and insight.program_id:
        program = db.query(Program).filter(
            and_(Program.id == insight.program_id, Program.created_by == current_user.id)
        ).first()
        if not program:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return InsightResponse.from_orm(insight)

# Update recommendation status
@router.patch("/recommendations/{recommendation_id}/status")
async def update_recommendation_status(
    recommendation_id: str,
    status: RecommendationStatus,
    progress_percentage: Optional[float] = None,
    user_feedback: Optional[str] = None,
    user_rating: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update the status and progress of a coaching recommendation"""
    
    recommendation = db.query(CoachingRecommendation).filter(
        CoachingRecommendation.recommendation_id == recommendation_id
    ).first()
    
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    # Permission check - users can only update their own recommendations
    if (current_user.id != recommendation.user_id and 
        current_user.role not in ['admin']):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update fields
    recommendation.status = status.value
    recommendation.last_progress_update = datetime.utcnow()
    
    if progress_percentage is not None:
        recommendation.progress_percentage = min(100.0, max(0.0, progress_percentage))
    
    if user_feedback:
        recommendation.user_feedback = user_feedback
    
    if user_rating is not None:
        recommendation.user_rating = min(5.0, max(1.0, user_rating))
    
    if status == RecommendationStatus.COMPLETED:
        recommendation.completion_date = datetime.utcnow()
        recommendation.progress_percentage = 100.0
    
    try:
        db.commit()
        return {"message": "Recommendation updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update recommendation")

# Helper functions for AI analysis (simplified versions)
def _analyze_personality(participant_id: int, responses: List[Response], 
                        reviews: List[Review], start_date: datetime, end_date: datetime):
    """Analyze personality traits from user data"""
    
    if len(responses) < 5:
        return None
    
    # Simple personality analysis based on response patterns
    response_lengths = [len(r.content or '') for r in responses]
    avg_length = statistics.mean(response_lengths) if response_lengths else 0
    
    # Analyze communication style
    if avg_length > 200:
        communication_style = "Detailed and thorough"
        confidence = 0.75
    elif avg_length > 100:
        communication_style = "Balanced and clear"
        confidence = 0.70
    else:
        communication_style = "Concise and direct"
        confidence = 0.65
    
    return {
        'user_id': participant_id,
        'insight_type': InsightType.PERSONALITY.value,
        'category': 'Communication Style',
        'title': f'Communication Style: {communication_style}',
        'description': f'Based on {len(responses)} responses, your communication style is {communication_style.lower()}. This suggests you prefer to {"provide comprehensive details" if avg_length > 200 else "get straight to the point"}.',
        'key_findings': [
            f'Average response length: {avg_length:.0f} characters',
            f'Response consistency: {"High" if len(set(response_lengths)) < len(response_lengths)/2 else "Variable"}',
            f'Communication preference: {communication_style}'
        ],
        'supporting_data': {
            'response_count': len(responses),
            'average_length': avg_length,
            'response_lengths': response_lengths[:10]  # Sample
        },
        'confidence_score': confidence,
        'impact_score': 0.8,
        'reliability_score': 0.7,
        'analysis_start_date': start_date,
        'analysis_end_date': end_date,
        'data_points_analyzed': len(responses),
        'tags': ['learning-style', 'processing', 'adaptation']
    }

async def _generate_recommendations_for_user(db: Session, user_id: int):
    """Generate coaching recommendations for a user based on their insights"""
    
    # Get recent insights for the user
    recent_insights = db.query(AIInsight).filter(
        and_(
            AIInsight.user_id == user_id,
            AIInsight.is_active == True,
            AIInsight.created_at >= datetime.utcnow() - timedelta(days=30)
        )
    ).all()
    
    recommendations_to_create = []
    
    # Generate recommendations based on insights
    for insight in recent_insights:
        if insight.insight_type == InsightType.COMPETENCY_GAP.value:
            if insight.impact_score > 0.7:  # High impact gaps
                recommendations_to_create.append({
                    'user_id': user_id,
                    'program_id': insight.program_id,
                    'ai_insight_id': insight.id,
                    'category': 'Skill Development',
                    'priority': RecommendationPriority.HIGH.value,
                    'title': f'Address {insight.category} Gap',
                    'description': f'Focus on improving your {insight.category.lower()} skills based on recent performance analysis.',
                    'rationale': f'Analysis shows this area has high impact potential ({insight.impact_score:.0%}) for your development.',
                    'expected_outcome': f'Improved performance in {insight.category.lower()} with measurable progress within 2-4 weeks.',
                    'action_items': [
                        f'Review feedback related to {insight.category.lower()}',
                        'Practice specific skills daily for 15-20 minutes',
                        'Seek mentorship or additional resources',
                        'Track progress weekly'
                    ],
                    'resources': [
                        {'title': 'Skill Development Guide', 'url': '#', 'type': 'guide'},
                        {'title': 'Practice Exercises', 'url': '#', 'type': 'exercises'},
                        {'title': 'Video Tutorials', 'url': '#', 'type': 'video'}
                    ],
                    'timeline': '2-4 weeks',
                    'potential_impact': insight.impact_score,
                    'difficulty_level': 0.6,
                    'confidence_score': insight.confidence_score,
                    'expires_at': datetime.utcnow() + timedelta(days=30)
                })
        
        elif insight.insight_type == InsightType.BEHAVIORAL_PATTERN.value:
            if 'timing' in insight.tags:
                recommendations_to_create.append({
                    'user_id': user_id,
                    'ai_insight_id': insight.id,
                    'category': 'Productivity Optimization',
                    'priority': RecommendationPriority.MEDIUM.value,
                    'title': 'Optimize Your Peak Hours',
                    'description': 'Leverge your natural activity patterns for maximum productivity and engagement.',
                    'rationale': f'Your activity analysis shows clear patterns that can be optimized for better results.',
                    'expected_outcome': 'Increased engagement and better quality responses by aligning activities with peak hours.',
                    'action_items': [
                        'Schedule important tasks during your peak activity time',
                        'Use less productive hours for routine activities',
                        'Track energy levels throughout the day',
                        'Adjust your learning schedule accordingly'
                    ],
                    'resources': [
                        {'title': 'Time Management Guide', 'url': '#', 'type': 'guide'},
                        {'title': 'Energy Tracking Template', 'url': '#', 'type': 'template'}
                    ],
                    'timeline': '1-2 weeks',
                    'potential_impact': 0.7,
                    'difficulty_level': 0.3,
                    'confidence_score': insight.confidence_score,
                    'expires_at': datetime.utcnow() + timedelta(days=21)
                })
        
        elif insight.insight_type == InsightType.LEARNING_STYLE.value:
            recommendations_to_create.append({
                'user_id': user_id,
                'ai_insight_id': insight.id,
                'category': 'Learning Enhancement',
                'priority': RecommendationPriority.MEDIUM.value,
                'title': 'Personalize Your Learning Approach',
                'description': 'Adapt learning materials and methods to match your identified learning style.',
                'rationale': f'Understanding your learning style can improve retention and engagement significantly.',
                'expected_outcome': 'Better learning outcomes and increased satisfaction with the learning process.',
                'action_items': [
                    'Choose learning materials that match your style',
                    'Adjust note-taking and review methods',
                    'Experiment with different content formats',
                    'Provide feedback on material effectiveness'
                ],
                'resources': [
                    {'title': 'Learning Style Guide', 'url': '#', 'type': 'guide'},
                    {'title': 'Study Techniques', 'url': '#', 'type': 'techniques'}
                ],
                'timeline': '2-3 weeks',
                'potential_impact': 0.6,
                'difficulty_level': 0.4,
                'confidence_score': insight.confidence_score,
                'expires_at': datetime.utcnow() + timedelta(days=30)
            })
    
    # If no insights available, create general recommendations
    if not recommendations_to_create:
        # Get user's recent activity
        recent_responses = db.query(Response).filter(
            and_(
                Response.user_id == user_id,
                Response.created_at >= datetime.utcnow() - timedelta(days=14)
            )
        ).count()
        
        if recent_responses < 3:
            recommendations_to_create.append({
                'user_id': user_id,
                'category': 'Engagement',
                'priority': RecommendationPriority.HIGH.value,
                'title': 'Increase Your Engagement',
                'description': 'Your recent activity level is lower than optimal for meaningful progress.',
                'rationale': 'Regular engagement is crucial for skill development and getting value from the program.',
                'expected_outcome': 'Improved learning outcomes and better skill development through consistent participation.',
                'action_items': [
                    'Set daily reminders for program activities',
                    'Dedicate 10-15 minutes daily to responses',
                    'Engage with program content regularly',
                    'Track your daily participation'
                ],
                'resources': [
                    {'title': 'Habit Formation Guide', 'url': '#', 'type': 'guide'},
                    {'title': 'Daily Tracker Template', 'url': '#', 'type': 'template'}
                ],
                'timeline': '1-2 weeks',
                'potential_impact': 0.8,
                'difficulty_level': 0.5,
                'confidence_score': 0.9,
                'expires_at': datetime.utcnow() + timedelta(days=14)
            })
        else:
            recommendations_to_create.append({
                'user_id': user_id,
                'category': 'Growth',
                'priority': RecommendationPriority.MEDIUM.value,
                'title': 'Expand Your Learning Goals',
                'description': 'Consider setting more ambitious learning objectives to accelerate your growth.',
                'rationale': 'Your consistent engagement shows readiness for more challenging goals.',
                'expected_outcome': 'Accelerated skill development and increased confidence in new areas.',
                'action_items': [
                    'Identify 2-3 new skill areas to explore',
                    'Set specific, measurable goals',
                    'Create a timeline for achievement',
                    'Seek feedback on progress regularly'
                ],
                'resources': [
                    {'title': 'Goal Setting Framework', 'url': '#', 'type': 'framework'},
                    {'title': 'Progress Tracking Tools', 'url': '#', 'type': 'tools'}
                ],
                'timeline': '3-4 weeks',
                'potential_impact': 0.7,
                'difficulty_level': 0.6,
                'confidence_score': 0.8,
                'expires_at': datetime.utcnow() + timedelta(days=28)
            })
    
    # Save recommendations to database
    for rec_data in recommendations_to_create[:5]:  # Limit to 5 recommendations
        db_recommendation = CoachingRecommendation(**rec_data)
        db.add(db_recommendation)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving recommendations: {e}")

# Get analytics summary for insights
@router.get("/analytics/summary/{user_id}")
async def get_ai_analytics_summary(
    user_id: int,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a summary of AI insights and recommendations for analytics dashboard"""
    
    # Permission check
    if (current_user.id != user_id and 
        current_user.role not in ['admin', 'program_creator']):
        raise HTTPException(status_code=403, detail="Access denied")
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get insights summary
    insights = db.query(AIInsight).filter(
        and_(
            AIInsight.user_id == user_id,
            AIInsight.created_at >= start_date,
            AIInsight.is_active == True
        )
    ).all()
    
    # Get recommendations summary
    recommendations = db.query(CoachingRecommendation).filter(
        and_(
            CoachingRecommendation.user_id == user_id,
            CoachingRecommendation.created_at >= start_date
        )
    ).all()
    
    # Calculate statistics
    insight_types = {}
    for insight in insights:
        insight_types[insight.insight_type] = insight_types.get(insight.insight_type, 0) + 1
    
    rec_statuses = {}
    for rec in recommendations:
        rec_statuses[rec.status] = rec_statuses.get(rec.status, 0) + 1
    
    high_impact_insights = len([i for i in insights if i.impact_score > 0.7])
    completed_recommendations = len([r for r in recommendations if r.status == 'completed'])
    
    return {
        "summary": {
            "total_insights": len(insights),
            "total_recommendations": len(recommendations),
            "high_impact_insights": high_impact_insights,
            "completed_recommendations": completed_recommendations,
            "average_confidence": statistics.mean([i.confidence_score for i in insights]) if insights else 0,
            "average_recommendation_rating": statistics.mean([r.user_rating for r in recommendations if r.user_rating]) if any(r.user_rating for r in recommendations) else None
        },
        "insight_breakdown": {
            "by_type": insight_types,
            "high_confidence": len([i for i in insights if i.confidence_score > 0.8]),
            "actionable": len([i for i in insights if i.is_actionable])
        },
        "recommendation_breakdown": {
            "by_status": rec_statuses,
            "by_priority": {
                "urgent": len([r for r in recommendations if r.priority == 'urgent']),
                "high": len([r for r in recommendations if r.priority == 'high']),
                "medium": len([r for r in recommendations if r.priority == 'medium']),
                "low": len([r for r in recommendations if r.priority == 'low'])
            }
        },
        "recent_insights": [
            {
                "title": insight.title,
                "type": insight.insight_type,
                "confidence": insight.confidence_score,
                "impact": insight.impact_score,
                "created_at": insight.created_at
            }
            for insight in sorted(insights, key=lambda x: x.created_at, reverse=True)[:5]
        ],
        "active_recommendations": [
            {
                "title": rec.title,
                "priority": rec.priority,
                "status": rec.status,
                "progress": rec.progress_percentage,
                "created_at": rec.created_at
            }
            for rec in sorted([r for r in recommendations if r.status != 'completed'], 
                            key=lambda x: x.created_at, reverse=True)[:5]
        ],
        'analysis_start_date': start_date,
        'analysis_end_date': end_date,
        'data_points_analyzed': len(insights) + len(recommendations),
        'tags': ['communication', 'personality', 'writing-style']
    }

def _analyze_competency_gaps(participant_id: int, responses: List[Response], 
                           reviews: List[Review], enrollments: List[ProgramEnrollment],
                           start_date: datetime, end_date: datetime):
    """Analyze competency gaps based on performance data"""
    
    insights = []
    
    if reviews:
        ratings = [r.rating for r in reviews if r.rating]
        if ratings:
            avg_rating = statistics.mean(ratings)
            
            if avg_rating < 3.0:
                insights.append({
                    'user_id': participant_id,
                    'insight_type': InsightType.COMPETENCY_GAP.value,
                    'category': 'Overall Performance',
                    'subcategory': 'Rating Trends',
                    'title': 'Performance Improvement Opportunity',
                    'description': f'Your average rating of {avg_rating:.1f}/5.0 suggests there are opportunities for improvement. Focus on areas where you received lower ratings.',
                    'key_findings': [
                        f'Average rating: {avg_rating:.1f}/5.0',
                        f'Total reviews analyzed: {len(reviews)}',
                        f'Improvement potential: {((5.0 - avg_rating) / 5.0 * 100):.0f}%'
                    ],
                    'supporting_data': {
                        'ratings': ratings,
                        'review_count': len(reviews)
                    },
                    'confidence_score': 0.8,
                    'impact_score': 0.9,
                    'reliability_score': 0.75,
                    'analysis_start_date': start_date,
                    'analysis_end_date': end_date,
                    'data_points_analyzed': len(reviews),
                    'tags': ['performance', 'improvement', 'competency']
                })
    
    return insights

def _analyze_behavioral_patterns(participant_id: int, responses: List[Response], 
                               reviews: List[Review], start_date: datetime, end_date: datetime):
    """Analyze behavioral patterns from engagement data"""
    
    insights = []
    
    if responses:
        # Analyze response timing patterns
        response_hours = [r.created_at.hour for r in responses]
        morning_responses = len([h for h in response_hours if 6 <= h < 12])
        afternoon_responses = len([h for h in response_hours if 12 <= h < 18])
        evening_responses = len([h for h in response_hours if 18 <= h < 24])
        
        total_responses = len(responses)
        
        # Determine peak activity time
        if morning_responses > afternoon_responses and morning_responses > evening_responses:
            peak_time = "morning"
            peak_percentage = (morning_responses / total_responses) * 100
        elif afternoon_responses > evening_responses:
            peak_time = "afternoon"
            peak_percentage = (afternoon_responses / total_responses) * 100
        else:
            peak_time = "evening"
            peak_percentage = (evening_responses / total_responses) * 100
        
        if peak_percentage > 50:  # If more than 50% of responses in one time period
            insights.append({
                'user_id': participant_id,
                'insight_type': InsightType.BEHAVIORAL_PATTERN.value,
                'category': 'Engagement Patterns',
                'subcategory': 'Activity Timing',
                'title': f'Peak Activity: {peak_time.title()} Person',
                'description': f'You are most active during the {peak_time}, with {peak_percentage:.0f}% of your responses occurring during this time. This suggests you may be most productive and engaged during {peak_time} hours.',
                'key_findings': [
                    f'Peak activity time: {peak_time}',
                    f'{peak_percentage:.0f}% of responses during peak time',
                    f'Total responses analyzed: {total_responses}'
                ],
                'supporting_data': {
                    'morning_responses': morning_responses,
                    'afternoon_responses': afternoon_responses,
                    'evening_responses': evening_responses,
                    'response_hours': response_hours
                },
                'confidence_score': 0.7,
                'impact_score': 0.6,
                'reliability_score': 0.8,
                'analysis_start_date': start_date,
                'analysis_end_date': end_date,
                'data_points_analyzed': total_responses,
                'tags': ['timing', 'productivity', 'engagement', 'behavioral']
            })
    
    return insights

def _analyze_learning_style(participant_id: int, responses: List[Response], 
                          reviews: List[Review], start_date: datetime, end_date: datetime):
    """Analyze learning style preferences"""
    
    if len(responses) < 3:
        return None
    
    # Simple learning style analysis based on response patterns
    response_lengths = [len(r.content or '') for r in responses]
    avg_length = statistics.mean(response_lengths)
    
    # Determine learning style based on response characteristics
    if avg_length > 300:
        learning_style = "Deep Processor"
        description = "You tend to provide detailed, thoughtful responses, suggesting you prefer to process information thoroughly before responding."
    elif avg_length > 150:
        learning_style = "Balanced Learner"
        description = "Your responses show a balance between detail and conciseness, suggesting you adapt your learning approach to the situation."
    else:
        learning_style = "Quick Processor"
        description = "You tend to provide concise, focused responses, suggesting you prefer to extract key points and move quickly through material."
    
    return {
        'user_id': participant_id,
        'insight_type': InsightType.LEARNING_STYLE.value,
        'category': 'Learning Preferences',
        'title': f'Learning Style: {learning_style}',
        'description': description,
        'key_findings': [
            f'Response depth: {learning_style}',
            f'Average response length: {avg_length:.0f} characters',
            f'Learning preference: {"Thorough analysis" if avg_length > 300 else "Quick synthesis" if avg_length < 150 else "Adaptive approach"}'
        ],
        'supporting_data': {
            'response_count': len(responses),
            'average_length': avg_length,
            'style_classification': learning_style
        },
        'confidence_score': 0.65,
        'impact_score': 0.75,
        'reliability_score': 0.7,
        'analysis_start_date': start_date,
        'analysis_end_date': end_date,
        'data_points_analyzed': len(responses),
        'tags': ['communication', 'personality', 'writing-style']
    }