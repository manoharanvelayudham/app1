from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd
from sqlalchemy import func

from database import get_db
from models import User, Program
from auth import get_current_user
from services.export_excel import ExcelExportService

router = APIRouter(prefix="/export", tags=["export"])

@router.get("/excel")
async def export_excel(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    program_id: Optional[int] = Query(None, description="Filter by specific program ID"),
    user_ids: Optional[str] = Query(None, description="Comma-separated user IDs to filter"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    include_participants: bool = Query(True, description="Include participants data"),
    include_responses: bool = Query(True, description="Include responses data"),
    include_reviews: bool = Query(True, description="Include reviews data"),
    days: Optional[int] = Query(None, description="Number of days back from today")
):
    """
    Export coaching program data to Excel format with filtering options
    """
    
    # Verify permissions - only admins can export all data
    if current_user.role != "admin":
        # Non-admins can only export their own program data
        if program_id:
            program = db.query(Program).filter(Program.id == program_id).first()
            if not program or program.creator_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied")
        else:
            # If no program specified, filter to user's programs only
            user_programs = db.query(Program.id).filter(Program.creator_id == current_user.id).all()
            if not user_programs:
                raise HTTPException(status_code=404, detail="No programs found")
    
    # Parse date filters
    start_date_obj = None
    end_date_obj = None
    
    if days:
        end_date_obj = datetime.now()
        start_date_obj = end_date_obj - timedelta(days=days)
    else:
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                # Add 23:59:59 to include the entire end date
                end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
    
    # Parse user IDs filter
    user_ids_list = None
    if user_ids:
        try:
            user_ids_list = [int(uid.strip()) for uid in user_ids.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_ids format. Use comma-separated integers")
    
    # Create export service an