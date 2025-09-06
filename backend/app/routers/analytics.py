from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json

from database import get_db
from models import User, Program, Response, Review, ProgramEnrollment
from auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/progress/{user_id}")
async def get_user_progress(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = Query(30, description="Number of days to analyze")
):
    """Get user progress analytics for Chart.js visualization"""
    
    # Verify access permissions
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get user's enrolled programs
    enrollments = db.query(ProgramEnrollment).filter(
        ProgramEnrollment.user_id == user_id
    ).all()
    
    program_ids = [e.program_id for e in enrollments]
    
    # Daily response counts for Chart.js line chart
    daily_responses = db.query(
        func.date(Response.created_at).label('date'),
        func.count(Response.id).label('count')
    ).filter(
        and_(
            Response.user_id == user_id,
            Response.created_at >= start_date,
            Response.created_at <= end_date
        )
    ).group_by(func.date(Response.created_at)).all()
    
    # Program completion rates for Chart.js pie chart
    program_stats = []
    for program_id in program_ids:
        program = db.query(Program).filter(Program.id == program_id).first()
        if program:
            total_responses = db.query(Response).filter(
                and_(
                    Response.user_id == user_id,
                    Response.program_id == program_id
                )
            ).count()
            
            program_stats.append({
                'program_name': program.title,
                'response_count': total_responses,
                'program_id': program_id
            })
    
    # Review scores over time for Chart.js line chart
    review_scores = db.query(
        func.date(Review.created_at).label('date'),
        func.avg(Review.rating).label('avg_rating')
    ).filter(
        and_(
            Review.user_id == user_id,
            Review.created_at >= start_date,
            Review.created_at <= end_date
        )
    ).group_by(func.date(Review.created_at)).all()
    
    # Format data for Chart.js
    return {
        "user_info": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        },
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": days
        },
        "daily_activity": {
            "labels": [str(item.date) for item in daily_responses],
            "datasets": [{
                "label": "Daily Responses",
                "data": [item.count for item in daily_responses],
                "borderColor": "rgb(75, 192, 192)",
                "backgroundColor": "rgba(75, 192, 192, 0.2)",
                "tension": 0.1
            }]
        },
        "program_engagement": {
            "labels": [item['program_name'] for item in program_stats],
            "datasets": [{
                "label": "Responses per Program",
                "data": [item['response_count'] for item in program_stats],
                "backgroundColor": [
                    "rgba(255, 99, 132, 0.8)",
                    "rgba(54, 162, 235, 0.8)",
                    "rgba(255, 205, 86, 0.8)",
                    "rgba(75, 192, 192, 0.8)",
                    "rgba(153, 102, 255, 0.8)"
                ]
            }]
        },
        "review_trends": {
            "labels": [str(item.date) for item in review_scores],
            "datasets": [{
                "label": "Average Rating",
                "data": [float(item.avg_rating) if item.avg_rating else 0 for item in review_scores],
                "borderColor": "rgb(255, 159, 64)",
                "backgroundColor": "rgba(255, 159, 64, 0.2)",
                "tension": 0.1
            }]
        },
        "summary_stats": {
            "total_responses": db.query(Response).filter(Response.user_id == user_id).count(),
            "programs_enrolled": len(program_ids),
            "average_rating": float(
                db.query(func.avg(Review.rating)).filter(Review.user_id == user_id).scalar() or 0
            ),
            "days_active": len(daily_responses)
        }
    }

@router.get("/program/{program_id}")
async def get_program_analytics(
    program_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = Query(30, description="Number of days to analyze")
):
    """Get program analytics for Chart.js visualization"""
    
    # Verify access permissions (admin or program owner)
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    if current_user.role != "admin" and current_user.id != program.creator_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get program enrollments
    enrollments = db.query(ProgramEnrollment).filter(
        ProgramEnrollment.program_id == program_id
    ).all()
    
    enrolled_user_ids = [e.user_id for e in enrollments]
    
    # Daily engagement for Chart.js line chart
    daily_engagement = db.query(
        func.date(Response.created_at).label('date'),
        func.count(func.distinct(Response.user_id)).label('active_users'),
        func.count(Response.id).label('total_responses')
    ).filter(
        and_(
            Response.program_id == program_id,
            Response.created_at >= start_date,
            Response.created_at <= end_date
        )
    ).group_by(func.date(Response.created_at)).all()
    
    # User engagement levels for Chart.js bar chart
    user_engagement = db.query(
        User.name.label('user_name'),
        func.count(Response.id).label('response_count')
    ).join(Response).filter(
        and_(
            Response.program_id == program_id,
            Response.user_id.in_(enrolled_user_ids)
        )
    ).group_by(User.id, User.name).order_by(desc(func.count(Response.id))).limit(10).all()
    
    # Rating distribution for Chart.js doughnut chart
    rating_distribution = db.query(
        Review.rating.label('rating'),
        func.count(Review.id).label('count')
    ).filter(
        Review.program_id == program_id
    ).group_by(Review.rating).all()
    
    # Completion timeline for Chart.js line chart
    completion_timeline = db.query(
        func.date(ProgramEnrollment.completed_at).label('date'),
        func.count(ProgramEnrollment.id).label('completions')
    ).filter(
        and_(
            ProgramEnrollment.program_id == program_id,
            ProgramEnrollment.completed_at.isnot(None),
            ProgramEnrollment.completed_at >= start_date,
            ProgramEnrollment.completed_at <= end_date
        )
    ).group_by(func.date(ProgramEnrollment.completed_at)).all()
    
    return {
        "program_info": {
            "id": program.id,
            "title": program.title,
            "description": program.description,
            "creator": program.creator.name if program.creator else "Unknown"
        },
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": days
        },
        "daily_engagement": {
            "labels": [str(item.date) for item in daily_engagement],
            "datasets": [
                {
                    "label": "Active Users",
                    "data": [item.active_users for item in daily_engagement],
                    "borderColor": "rgb(75, 192, 192)",
                    "backgroundColor": "rgba(75, 192, 192, 0.2)",
                    "tension": 0.1
                },
                {
                    "label": "Total Responses",
                    "data": [item.total_responses for item in daily_engagement],
                    "borderColor": "rgb(255, 99, 132)",
                    "backgroundColor": "rgba(255, 99, 132, 0.2)",
                    "tension": 0.1
                }
            ]
        },
        "user_engagement": {
            "labels": [item.user_name for item in user_engagement],
            "datasets": [{
                "label": "Response Count",
                "data": [item.response_count for item in user_engagement],
                "backgroundColor": "rgba(54, 162, 235, 0.8)",
                "borderColor": "rgba(54, 162, 235, 1)",
                "borderWidth": 1
            }]
        },
        "rating_distribution": {
            "labels": [f"{item.rating} Stars" for item in rating_distribution],
            "datasets": [{
                "label": "Rating Distribution",
                "data": [item.count for item in rating_distribution],
                "backgroundColor": [
                    "rgba(255, 99, 132, 0.8)",
                    "rgba(255, 159, 64, 0.8)",
                    "rgba(255, 205, 86, 0.8)",
                    "rgba(75, 192, 192, 0.8)",
                    "rgba(54, 162, 235, 0.8)"
                ]
            }]
        },
        "completion_timeline": {
            "labels": [str(item.date) for item in completion_timeline],
            "datasets": [{
                "label": "Program Completions",
                "data": [item.completions for item in completion_timeline],
                "borderColor": "rgb(153, 102, 255)",
                "backgroundColor": "rgba(153, 102, 255, 0.2)",
                "tension": 0.1
            }]
        },
        "summary_stats": {
            "total_enrolled": len(enrolled_user_ids),
            "total_responses": db.query(Response).filter(Response.program_id == program_id).count(),
            "total_completions": db.query(ProgramEnrollment).filter(
                and_(
                    ProgramEnrollment.program_id == program_id,
                    ProgramEnrollment.completed_at.isnot(None)
                )
            ).count(),
            "average_rating": float(
                db.query(func.avg(Review.rating)).filter(Review.program_id == program_id).scalar() or 0
            ),
            "completion_rate": round(
                (db.query(ProgramEnrollment).filter(
                    and_(
                        ProgramEnrollment.program_id == program_id,
                        ProgramEnrollment.completed_at.isnot(None)
                    )
                ).count() / max(len(enrolled_user_ids), 1)) * 100, 2
            )
        }
    }