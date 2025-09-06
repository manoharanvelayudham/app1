"""
Bulk Operations API Router
Handles bulk imports, data exports, and database backup/restore operations
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import pandas as pd
import json
import io
import zipfile
from datetime import datetime
import asyncio
import tempfile
import os
from pathlib import Path

from database import get_db
from models import Participant, Program, User, SystemAlert
from auth import get_current_user
from services.bulk_import_service import BulkImportService
from services.backup_service import BackupService
from schemas.bulk_ops_schemas import (
    BulkImportResult, BulkImportStatus, BackupRequest, RestoreRequest,
    ImportValidationError, BulkOperationResponse
)

router = APIRouter(prefix="/bulk-ops", tags=["bulk-operations"])

# Initialize services
bulk_import_service = BulkImportService()
backup_service = BackupService()


@router.post("/import/participants", response_model=BulkImportResult)
async def bulk_import_participants(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    validate_only: bool = Query(False, description="Only validate, don't import"),
    update_existing: bool = Query(False, description="Update existing participants"),
    batch_size: int = Query(100, ge=10, le=1000, description="Import batch size"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Bulk import participants from Excel/CSV file
    
    Features:
    - Excel/CSV file support
    - Data validation with detailed error reporting
    - Duplicate detection and handling
    - Batch processing for large files
    - Background processing for async imports
    - Rollback on validation errors
    """
    
    # Validate file format
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(
            status_code=400,
            detail="Only Excel (.xlsx, .xls) and CSV files are supported"
        )
    
    try:
        # Read file content
        content = await file.read()
        
        # Parse file based on format
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(content))
        
        # Validate file structure
        validation_result = await bulk_import_service.validate_participants_file(df)
        
        if not validation_result.is_valid:
            return BulkImportResult(
                status=BulkImportStatus.VALIDATION_FAILED,
                total_records=len(df),
                processed_records=0,
                successful_imports=0,
                failed_imports=len(df),
                errors=validation_result.errors,
                warnings=validation_result.warnings,
                processing_time=0.0
            )
        
        # If validation only, return results
        if validate_only:
            return BulkImportResult(
                status=BulkImportStatus.VALIDATED,
                total_records=len(df),
                processed_records=len(df),
                successful_imports=0,
                failed_imports=0,
                errors=[],
                warnings=validation_result.warnings,
                processing_time=0.0
            )
        
        # Process import
        if len(df) > batch_size:
            # Large file - process in background
            task_id = f"import_participants_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            background_tasks.add_task(
                bulk_import_service.process_participants_import,
                df, db, current_user.id, task_id, update_existing, batch_size
            )
            
            return BulkImportResult(
                status=BulkImportStatus.PROCESSING,
                total_records=len(df),
                processed_records=0,
                successful_imports=0,
                failed_imports=0,
                errors=[],
                warnings=validation_result.warnings,
                processing_time=0.0,
                task_id=task_id
            )
        else:
            # Small file - process immediately
            result = await bulk_import_service.import_participants(
                df, db, current_user.id, update_existing
            )
            return result
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing import file: {str(e)}"
        )


@router.post("/import/programs", response_model=BulkImportResult)
async def bulk_import_programs(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    validate_only: bool = Query(False, description="Only validate, don't import"),
    update_existing: bool = Query(False, description="Update existing programs"),
    batch_size: int = Query(50, ge=10, le=500, description="Import batch size"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Bulk import programs from Excel/CSV file
    
    Features:
    - Program template validation
    - Category and status validation
    - Date range validation
    - Capacity and requirement checks
    - Batch processing with progress tracking
    """
    
    # Validate file format
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(
            status_code=400,
            detail="Only Excel (.xlsx, .xls) and CSV files are supported"
        )
    
    try:
        content = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(content))
        
        # Validate program file structure
        validation_result = await bulk_import_service.validate_programs_file(df)
        
        if not validation_result.is_valid:
            return BulkImportResult(
                status=BulkImportStatus.VALIDATION_FAILED,
                total_records=len(df),
                processed_records=0,
                successful_imports=0,
                failed_imports=len(df),
                errors=validation_result.errors,
                warnings=validation_result.warnings,
                processing_time=0.0
            )
        
        if validate_only:
            return BulkImportResult(
                status=BulkImportStatus.VALIDATED,
                total_records=len(df),
                processed_records=len(df),
                successful_imports=0,
                failed_imports=0,
                errors=[],
                warnings=validation_result.warnings,
                processing_time=0.0
            )
        
        # Process import
        if len(df) > batch_size:
            task_id = f"import_programs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            background_tasks.add_task(
                bulk_import_service.process_programs_import,
                df, db, current_user.id, task_id, update_existing, batch_size
            )
            
            return BulkImportResult(
                status=BulkImportStatus.PROCESSING,
                total_records=len(df),
                processed_records=0,
                successful_imports=0,
                failed_imports=0,
                errors=[],
                warnings=validation_result.warnings,
                processing_time=0.0,
                task_id=task_id
            )
        else:
            result = await bulk_import_service.import_programs(
                df, db, current_user.id, update_existing
            )
            return result
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing import file: {str(e)}"
        )


@router.get("/import/status/{task_id}", response_model=BulkImportResult)
async def get_import_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the status of a background import task
    """
    try:
        status = await bulk_import_service.get_import_status(task_id, db)
        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Import task {task_id} not found"
            )
        return status
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving import status: {str(e)}"
        )


@router.get("/import/template/{entity_type}")
async def download_import_template(
    entity_type: str,
    format: str = Query("xlsx", regex="^(xlsx|csv)$", description="Template format")
):
    """
    Download import template for participants or programs
    
    Entity types:
    - participants: Template for participant bulk import
    - programs: Template for program bulk import
    """
    
    if entity_type not in ["participants", "programs"]:
        raise HTTPException(
            status_code=400,
            detail="Entity type must be 'participants' or 'programs'"
        )
    
    try:
        template_data = bulk_import_service.get_import_template(entity_type)
        
        if format == "csv":
            # Return CSV template
            df = pd.DataFrame(template_data)
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            
            return StreamingResponse(
                io.BytesIO(csv_buffer.getvalue().encode()),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={entity_type}_import_template.csv"}
            )
        else:
            # Return Excel template
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df = pd.DataFrame(template_data)
                df.to_excel(writer, sheet_name=entity_type.title(), index=False)
                
                # Add formatting and validation
                bulk_import_service.format_excel_template(writer, entity_type)
            
            excel_buffer.seek(0)
            return StreamingResponse(
                excel_buffer,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={entity_type}_import_template.xlsx"}
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating template: {str(e)}"
        )


@router.post("/backup/create", response_model=BulkOperationResponse)
async def create_backup(
    background_tasks: BackgroundTasks,
    request: BackupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create database backup
    
    Features:
    - Full or selective table backup
    - Compressed backup files
    - Metadata inclusion
    - Background processing for large backups
    - Backup validation
    """
    
    try:
        # Validate backup request
        validation_result = backup_service.validate_backup_request(request)
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid backup request: {', '.join(validation_result.errors)}"
            )
        
        # Generate backup task ID
        task_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Start backup process
        background_tasks.add_task(
            backup_service.create_backup,
            request, db, current_user.id, task_id
        )
        
        return BulkOperationResponse(
            success=True,
            message="Backup process started",
            task_id=task_id,
            estimated_completion=backup_service.estimate_backup_time(request, db)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error starting backup: {str(e)}"
        )


@router.post("/backup/restore", response_model=BulkOperationResponse)
async def restore_backup(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    restore_options: str = Query(..., description="JSON string with restore options"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Restore database from backup file
    
    Features:
    - Backup file validation
    - Selective table restoration
    - Pre-restore validation
    - Rollback capability
    - Data integrity checks
    """
    
    # Validate backup file
    if not file.filename.endswith('.zip'):
        raise HTTPException(
            status_code=400,
            detail="Backup file must be a ZIP archive"
        )
    
    try:
        # Parse restore options
        try:
            options = json.loads(restore_options)
            restore_request = RestoreRequest(**options)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid restore options JSON: {str(e)}"
            )
        
        # Read and validate backup file
        backup_content = await file.read()
        validation_result = await backup_service.validate_backup_file(backup_content)
        
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid backup file: {', '.join(validation_result.errors)}"
            )
        
        # Generate restore task ID
        task_id = f"restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Start restore process
        background_tasks.add_task(
            backup_service.restore_backup,
            backup_content, restore_request, db, current_user.id, task_id
        )
        
        return BulkOperationResponse(
            success=True,
            message="Restore process started",
            task_id=task_id,
            estimated_completion=backup_service.estimate_restore_time(validation_result.metadata)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error starting restore: {str(e)}"
        )


@router.get("/backup/status/{task_id}")
async def get_backup_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get backup/restore operation status
    """
    try:
        status = await backup_service.get_operation_status(task_id, db)
        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Operation {task_id} not found"
            )
        return status
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving operation status: {str(e)}"
        )


@router.get("/backup/download/{backup_id}")
async def download_backup(
    backup_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Download completed backup file
    """
    try:
        backup_path = await backup_service.get_backup_file_path(backup_id, db)
        if not backup_path or not os.path.exists(backup_path):
            raise HTTPException(
                status_code=404,
                detail="Backup file not found"
            )
        
        return FileResponse(
            backup_path,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=backup_{backup_id}.zip"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading backup: {str(e)}"
        )


@router.get("/export/data")
async def export_data(
    entity_type: str = Query(..., regex="^(participants|programs|users|all)$"),
    format: str = Query("xlsx", regex="^(xlsx|csv|json)$"),
    filters: Optional[str] = Query(None, description="JSON string with filter criteria"),
    include_deleted: bool = Query(False, description="Include soft-deleted records"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export data in various formats
    
    Features:
    - Multiple export formats (Excel, CSV, JSON)
    - Filtered exports
    - Include/exclude deleted records
    - Formatted output with proper headers
    """
    
    try:
        # Parse filters if provided
        filter_criteria = {}
        if filters:
            try:
                filter_criteria = json.loads(filters)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid filter JSON format"
                )
        
        # Export data
        export_result = await bulk_import_service.export_data(
            entity_type, format, filter_criteria, include_deleted, db
        )
        
        if format == "json":
            return StreamingResponse(
                io.BytesIO(json.dumps(export_result.data, indent=2).encode()),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={entity_type}_export.json"}
            )
        elif format == "csv":
            return StreamingResponse(
                io.BytesIO(export_result.content),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={entity_type}_export.csv"}
            )
        else:  # xlsx
            return StreamingResponse(
                io.BytesIO(export_result.content),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={entity_type}_export.xlsx"}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error exporting data: {str(e)}"
        )


@router.delete("/cleanup/temp-files")
async def cleanup_temp_files(
    older_than_hours: int = Query(24, ge=1, description="Delete files older than X hours"),
    current_user: User = Depends(get_current_user)
):
    """
    Clean up temporary files from import/export operations
    """
    try:
        deleted_count = await bulk_import_service.cleanup_temp_files(older_than_hours)
        return {
            "success": True,
            "message": f"Cleaned up {deleted_count} temporary files",
            "deleted_count": deleted_count
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error cleaning up temp files: {str(e)}"
        )