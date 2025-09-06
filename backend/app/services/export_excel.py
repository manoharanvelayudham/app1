import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from io import BytesIO
import json

from models import User, Program, Response, Review, ProgramEnrollment

class ExcelExportService:
    def __init__(self, db: Session):
        self.db = db
    
    def export_program_data(
        self,
        program_id: Optional[int] = None,
        user_ids: Optional[List[int]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_participants: bool = True,
        include_responses: bool = True,
        include_reviews: bool = True
    ) -> BytesIO:
        """
        Export program data to Excel with multiple sheets
        """
        
        # Create Excel writer
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='openpyxl')
        
        # Build filters
        filters = []
        if program_id:
            filters.append(Program.id == program_id)
        if start_date:
            filters.append(Program.created_at >= start_date)
        if end_date:
            filters.append(Program.created_at <= end_date)
        
        # Export participants data
        if include_participants:
            participants_data = self._get_participants_data(
                program_id=program_id,
                user_ids=user_ids,
                start_date=start_date,
                end_date=end_date
            )
            if participants_data:
                participants_df = pd.DataFrame(participants_data)
                participants_df.to_excel(writer, sheet_name='Participants', index=False)
        
        # Export responses data
        if include_responses:
            responses_data = self._get_responses_data(
                program_id=program_id,
                user_ids=user_ids,
                start_date=start_date,
                end_date=end_date
            )
            if responses_data:
                responses_df = pd.DataFrame(responses_data)
                responses_df.to_excel(writer, sheet_name='Responses', index=False)
        
        # Export reviews data
        if include_reviews:
            reviews_data = self._get_reviews_data(
                program_id=program_id,
                user_ids=user_ids,
                start_date=start_date,
                end_date=end_date
            )
            if reviews_data:
                reviews_df = pd.DataFrame(reviews_data)
                reviews_df.to_excel(writer, sheet_name='Reviews', index=False)
        
        # Export program summary
        summary_data = self._get_program_summary(
            program_id=program_id,
            start_date=start_date,
            end_date=end_date
        )
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Program Summary', index=False)
        
        # Save and close
        writer.close()
        output.seek(0)
        
        return output
    
    def _get_participants_data(
        self,
        program_id: Optional[int] = None,
        user_ids: Optional[List[int]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get participants data for Excel export"""
        
        query = self.db.query(
            User.id.label('user_id'),
            User.name.label('user_name'),
            User.email.label('user_email'),
            User.role.label('user_role'),
            Program.id.label('program_id'),
            Program.title.label('program_title'),
            ProgramEnrollment.enrolled_at.label('enrollment_date'),
            ProgramEnrollment.completed_at.label('completion_date'),
            ProgramEnrollment.progress.label('progress_percentage')
        ).join(
            ProgramEnrollment, User.id == ProgramEnrollment.user_id
        ).join(
            Program, ProgramEnrollment.program_id == Program.id
        )
        
        # Apply filters
        if program_id:
            query = query.filter(Program.id == program_id)
        if user_ids:
            query = query.filter(User.id.in_(user_ids))
        if start_date:
            query = query.filter(ProgramEnrollment.enrolled_at >= start_date)
        if end_date:
            query = query.filter(ProgramEnrollment.enrolled_at <= end_date)
        
        results = query.all()
        
        participants_data = []
        for result in results:
            # Calculate additional metrics
            total_responses = self.db.query(Response).filter(
                and_(
                    Response.user_id == result.user_id,
                    Response.program_id == result.program_id
                )
            ).count()
            
            avg_rating = self.db.query(
                func.avg(Review.rating)
            ).filter(
                and_(
                    Review.user_id == result.user_id,
                    Review.program_id == result.program_id
                )
            ).scalar()
            
            participants_data.append({
                'User ID': result.user_id,
                'User Name': result.user_name,
                'Email': result.user_email,
                'Role': result.user_role,
                'Program ID': result.program_id,
                'Program Title': result.program_title,
                'Enrollment Date': result.enrollment_date.isoformat() if result.enrollment_date else None,
                'Completion Date': result.completion_date.isoformat() if result.completion_date else None,
                'Progress %': result.progress_percentage,
                'Status': 'Completed' if result.completion_date else 'In Progress',
                'Total Responses': total_responses,
                'Average Rating': round(float(avg_rating), 2) if avg_rating else None,
                'Days Enrolled': (
                    (result.completion_date or datetime.now()) - result.enrollment_date
                ).days if result.enrollment_date else None
            })
        
        return participants_data
    
    def _get_responses_data(
        self,
        program_id: Optional[int] = None,
        user_ids: Optional[List[int]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get responses data for Excel export"""
        
        query = self.db.query(
            Response.id.label('response_id'),
            Response.user_id,
            User.name.label('user_name'),
            Response.program_id,
            Program.title.label('program_title'),
            Response.content,
            Response.created_at,
            Response.updated_at
        ).join(
            User, Response.user_id == User.id
        ).join(
            Program, Response.program_id == Program.id
        )
        
        # Apply filters
        if program_id:
            query = query.filter(Response.program_id == program_id)
        if user_ids:
            query = query.filter(Response.user_id.in_(user_ids))
        if start_date:
            query = query.filter(Response.created_at >= start_date)
        if end_date:
            query = query.filter(Response.created_at <= end_date)
        
        results = query.order_by(Response.created_at.desc()).all()
        
        responses_data = []
        for result in results:
            # Parse content if it's JSON
            content_text = result.content
            if isinstance(result.content, str):
                try:
                    content_json = json.loads(result.content)
                    if isinstance(content_json, dict):
                        content_text = '; '.join([f"{k}: {v}" for k, v in content_json.items()])
                except:
                    pass
            
            responses_data.append({
                'Response ID': result.response_id,
                'User ID': result.user_id,
                'User Name': result.user_name,
                'Program ID': result.program_id,
                'Program Title': result.program_title,
                'Content': content_text,
                'Content Length': len(str(result.content)),
                'Created Date': result.created_at.isoformat() if result.created_at else None,
                'Updated Date': result.updated_at.isoformat() if result.updated_at else None,
                'Word Count': len(str(result.content).split()) if result.content else 0
            })
        
        return responses_data
    
    def _get_reviews_data(
        self,
        program_id: Optional[int] = None,
        user_ids: Optional[List[int]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get reviews data for Excel export"""
        
        query = self.db.query(
            Review.id.label('review_id'),
            Review.user_id,
            User.name.label('user_name'),
            Review.program_id,
            Program.title.label('program_title'),
            Review.rating,
            Review.comment,
            Review.created_at,
            Review.updated_at
        ).join(
            User, Review.user_id == User.id
        ).join(
            Program, Review.program_id == Program.id
        )
        
        # Apply filters
        if program_id:
            query = query.filter(Review.program_id == program_id)
        if user_ids:
            query = query.filter(Review.user_id.in_(user_ids))
        if start_date:
            query = query.filter(Review.created_at >= start_date)
        if end_date:
            query = query.filter(Review.created_at <= end_date)
        
        results = query.order_by(Review.created_at.desc()).all()
        
        reviews_data = []
        for result in results:
            reviews_data.append({
                'Review ID': result.review_id,
                'User ID': result.user_id,
                'User Name': result.user_name,
                'Program ID': result.program_id,
                'Program Title': result.program_title,
                'Rating': result.rating,
                'Rating Category': self._get_rating_category(result.rating),
                'Comment': result.comment,
                'Comment Length': len(result.comment) if result.comment else 0,
                'Created Date': result.created_at.isoformat() if result.created_at else None,
                'Updated Date': result.updated_at.isoformat() if result.updated_at else None,
                'Has Comment': 'Yes' if result.comment and result.comment.strip() else 'No'
            })
        
        return reviews_data
    
    def _get_program_summary(
        self,
        program_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get program summary data for Excel export"""
        
        query = self.db.query(Program)
        
        # Apply filters
        if program_id:
            query = query.filter(Program.id == program_id)
        if start_date:
            query = query.filter(Program.created_at >= start_date)
        if end_date:
            query = query.filter(Program.created_at <= end_date)
        
        programs = query.all()
        
        summary_data = []
        for program in programs:
            # Calculate metrics
            total_enrolled = self.db.query(ProgramEnrollment).filter(
                ProgramEnrollment.program_id == program.id
            ).count()
            
            total_completed = self.db.query(ProgramEnrollment).filter(
                and_(
                    ProgramEnrollment.program_id == program.id,
                    ProgramEnrollment.completed_at.isnot(None)
                )
            ).count()
            
            total_responses = self.db.query(Response).filter(
                Response.program_id == program.id
            ).count()
            
            total_reviews = self.db.query(Review).filter(
                Review.program_id == program.id
            ).count()
            
            avg_rating = self.db.query(
                func.avg(Review.rating)
            ).filter(
                Review.program_id == program.id
            ).scalar()
            
            avg_progress = self.db.query(
                func.avg(ProgramEnrollment.progress)
            ).filter(
                ProgramEnrollment.program_id == program.id
            ).scalar()
            
            summary_data.append({
                'Program ID': program.id,
                'Program Title': program.title,
                'Description': program.description,
                'Creator': program.creator.name if program.creator else 'Unknown',
                'Created Date': program.created_at.isoformat() if program.created_at else None,
                'Total Enrolled': total_enrolled,
                'Total Completed': total_completed,
                'Completion Rate %': round((total_completed / max(total_enrolled, 1)) * 100, 2),
                'Total Responses': total_responses,
                'Avg Responses per User': round(total_responses / max(total_enrolled, 1), 2),
                'Total Reviews': total_reviews,
                'Average Rating': round(float(avg_rating), 2) if avg_rating else None,
                'Average Progress %': round(float(avg_progress), 2) if avg_progress else None,
                'Status': 'Active' if program.is_active else 'Inactive'
            })
        
        return summary_data
    
    def _get_rating_category(self, rating: int) -> str:
        """Convert numeric rating to category"""
        if rating >= 5:
            return 'Excellent'
        elif rating >= 4:
            return 'Good'
        elif rating >= 3:
            return 'Average'
        elif rating >= 2:
            return 'Poor'
        else:
            return 'Very Poor'