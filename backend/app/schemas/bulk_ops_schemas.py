"""
Pydantic schemas for bulk operations
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class BulkImportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    VALIDATED = "validated"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATION_FAILED = "validation_failed"
    CANCELLED = "cancelled"


class ImportValidationError(BaseModel):
    row: int = Field(..., description="Row number where error occurred")
    column: str = Field(..., description="Column name with error")
    value: Any = Field(..., description="Invalid value")
    error_type: str = Field(..., description="Type of validation error")
    message: str = Field(..., description="Error message")


class BulkImportResult(BaseModel):
    status: BulkImportStatus
    total_records: int = Field(..., description="Total number of records in file")
    processed_records: int = Field(..., description="Number of records processed")
    successful_imports: int = Field(..., description="Number of successful imports")
    failed_imports: int = Field(..., description="Number of failed imports")
    errors: List[ImportValidationError] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list, description="Non-critical warnings")
    processing_time: float = Field(..., description="Processing time in seconds")
    task_id: Optional[str] = Field(None, description="Background task ID if applicable")
    started_at: Optional[datetime] = Field(None, description="Processing start time")
    completed_at: Optional[datetime] = Field(None, description="Processing completion time")
    created_ids: List[int] = Field(default_factory=list, description="IDs of created records")
    updated_ids: List[int] = Field(default_factory=list, description="IDs of updated records")


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[ImportValidationError] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class BackupScope(str, Enum):
    FULL = "full"
    PARTICIPANTS_ONLY = "participants_only"
    PROGRAMS_ONLY = "programs_only"
    USER_DATA = "user_data"
    SYSTEM_CONFIG = "system_config"
    CUSTOM = "custom"


class BackupRequest(BaseModel):
    scope: BackupScope = Field(..., description="Scope of backup")
    include_tables: Optional[List[str]] = Field(None, description="Specific tables to backup")
    exclude_tables: Optional[List[str]] = Field(None, description="Tables to exclude from backup")
    include_data: bool = Field(True, description="Include table data or structure only")
    compress: bool = Field(True, description="Compress backup file")
    include_metadata: bool = Field(True, description="Include system metadata")
    encrypt: bool = Field(False, description="Encrypt backup file")
    encryption_key: Optional[str] = Field(None, description="Encryption key if encrypt=True")
    description: Optional[str] = Field(None, description="Backup description")
    
    @validator('encryption_key')
    def validate_encryption_key(cls, v, values):
        if values.get('encrypt') and not v:
            raise ValueError('Encryption key required when encrypt=True')
        return v


class RestoreRequest(BaseModel):
    restore_scope: BackupScope = Field(..., description="Scope of restoration")
    include_tables: Optional[List[str]] = Field(None, description="Specific tables to restore")
    exclude_tables: Optional[List[str]] = Field(None, description="Tables to exclude from restore")
    truncate_before_restore: bool = Field(False, description="Truncate tables before restore")
    update_existing: bool = Field(False, description="Update existing records")
    skip_validation: bool = Field(False, description="Skip data validation during restore")
    create_backup_before_restore: bool = Field(True, description="Create backup before restore")
    decryption_key: Optional[str] = Field(None, description="Decryption key for encrypted backups")


class BackupMetadata(BaseModel):
    backup_id: str
    created_at: datetime
    created_by: str
    scope: BackupScope
    total_tables: int
    total_records: int
    file_size: int
    is_encrypted: bool
    description: Optional[str]
    system_info: Dict[str, Any]
    schema_version: str


class BulkOperationResponse(BaseModel):
    success: bool
    message: str
    task_id: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    data: Optional[Dict[str, Any]] = None


class OperationStatus(BaseModel):
    task_id: str
    operation_type: str = Field(..., description="import, export, backup, or restore")
    status: str
    progress: float = Field(0.0, ge=0.0, le=100.0, description="Progress percentage")
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_items: Optional[int] = None
    processed_items: Optional[int] = None
    current_step: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    result_data: Optional[Dict[str, Any]] = None


class ExportRequest(BaseModel):
    entity_type: str = Field(..., regex="^(participants|programs|users|all)$")
    format: str = Field("xlsx", regex="^(xlsx|csv|json)$")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filter criteria")
    include_deleted: bool = Field(False, description="Include soft-deleted records")
    columns: Optional[List[str]] = Field(None, description="Specific columns to export")
    sort_by: Optional[str] = Field(None, description="Column to sort by")
    sort_order: str = Field("asc", regex="^(asc|desc)$")
    limit: Optional[int] = Field(None, ge=1, description="Maximum number of records")


class ExportResult(BaseModel):
    success: bool
    entity_type: str
    format: str
    total_records: int
    exported_records: int
    file_size: int
    content: Optional[bytes] = None
    data: Optional[List[Dict[str, Any]]] = None
    warnings: List[str] = Field(default_factory=list)


class ImportTemplate(BaseModel):
    entity_type: str
    columns: List[Dict[str, Any]]
    sample_data: List[Dict[str, Any]]
    validation_rules: Dict[str, Any]
    instructions: List[str]


class FileValidationResult(BaseModel):
    is_valid: bool
    file_type: str
    total_rows: int
    column_count: int
    missing_required_columns: List[str] = Field(default_factory=list)
    extra_columns: List[str] = Field(default_factory=list)
    data_type_errors: List[ImportValidationError] = Field(default_factory=list)
    duplicate_rows: List[int] = Field(default_factory=list)
    empty_rows: List[int] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class BatchProcessingConfig(BaseModel):
    batch_size: int = Field(100, ge=10, le=1000)
    max_errors_per_batch: int = Field(50, ge=1)
    continue_on_error: bool = Field(True)
    validate_before_import: bool = Field(True)
    create_rollback_point: bool = Field(True)


class DataIntegrityCheck(BaseModel):
    table_name: str
    check_type: str  # "count", "references", "constraints", "duplicates"
    expected_result: Any
    actual_result: Any
    is_valid: bool
    error_message: Optional[str] = None


class BackupValidationResult(BaseModel):
    is_valid: bool
    metadata: Optional[BackupMetadata] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    integrity_checks: List[DataIntegrityCheck] = Field(default_factory=list)
    file_size: int
    estimated_records: int


# Template data structures for different entity types
PARTICIPANT_TEMPLATE_COLUMNS = [
    {"name": "first_name", "type": "string", "required": True, "max_length": 50},
    {"name": "last_name", "type": "string", "required": True, "max_length": 50},
    {"name": "email", "type": "email", "required": True, "unique": True},
    {"name": "phone", "type": "string", "required": False, "max_length": 20},
    {"name": "date_of_birth", "type": "date", "required": True, "format": "YYYY-MM-DD"},
    {"name": "address", "type": "string", "required": False, "max_length": 200},
    {"name": "emergency_contact_name", "type": "string", "required": False, "max_length": 100},
    {"name": "emergency_contact_phone", "type": "string", "required": False, "max_length": 20},
    {"name": "medical_conditions", "type": "text", "required": False},
    {"name": "dietary_restrictions", "type": "text", "required": False},
    {"name": "status", "type": "enum", "required": False, "default": "active", 
     "values": ["active", "inactive", "pending"]},
    {"name": "notes", "type": "text", "required": False}
]

PROGRAM_TEMPLATE_COLUMNS = [
    {"name": "name", "type": "string", "required": True, "max_length": 100},
    {"name": "description", "type": "text", "required": True},
    {"name": "category", "type": "enum", "required": True,
     "values": ["fitness", "education", "recreation", "therapy", "social"]},
    {"name": "start_date", "type": "date", "required": True, "format": "YYYY-MM-DD"},
    {"name": "end_date", "type": "date", "required": True, "format": "YYYY-MM-DD"},
    {"name": "start_time", "type": "time", "required": False, "format": "HH:MM"},
    {"name": "end_time", "type": "time", "required": False, "format": "HH:MM"},
    {"name": "max_capacity", "type": "integer", "required": True, "min_value": 1},
    {"name": "location", "type": "string", "required": False, "max_length": 100},
    {"name": "instructor", "type": "string", "required": False, "max_length": 100},
    {"name": "requirements", "type": "text", "required": False},
    {"name": "cost", "type": "decimal", "required": False, "min_value": 0},
    {"name": "status", "type": "enum", "required": False, "default": "active",
     "values": ["active", "inactive", "cancelled", "completed"]},
    {"name": "tags", "type": "string", "required": False, "description": "Comma-separated tags"}
]