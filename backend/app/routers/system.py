# routers/system.py - Enterprise System Management Router

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import json
import asyncio
import psutil
import platform
import socket
import subprocess
import time
from pathlib import Path

from ..database import get_db
from ..models import (
    SystemConfig, SystemHealth, NetworkInfo, SystemAlert,
    ConfigScope, ConfigType, HealthStatus, ComponentType
)

router = APIRouter(prefix="/system", tags=["Enterprise System"])

# Pydantic Models
class ConfigUpdate(BaseModel):
    key: str = Field(..., max_length=200, description="Configuration key")
    value: str = Field(..., description="Configuration value")
    config_type: ConfigType = ConfigType.STRING
    scope: ConfigScope = ConfigScope.GLOBAL
    scope_id: Optional[str] = None
    description: Optional[str] = None
    is_sensitive: bool = False
    validation_rules: Optional[Dict[str, Any]] = None

class ConfigResponse(BaseModel):
    key: str
    value: Any
    config_type: ConfigType
    scope: ConfigScope
    scope_id: Optional[str]
    description: Optional[str]
    is_sensitive: bool
    created_at: datetime
    updated_at: datetime
    version: int

class HealthCheckResponse(BaseModel):
    component_name: str
    component_type: ComponentType
    status: HealthStatus
    response_time_ms: Optional[float]
    error_message: Optional[str]
    cpu_usage: Optional[float]
    memory_usage: Optional[float]
    disk_usage: Optional[float]
    custom_metrics: Optional[Dict[str, Any]]
    last_check: datetime
    consecutive_failures: int

class SystemHealthSummary(BaseModel):
    overall_status: HealthStatus
    total_components: int
    healthy_components: int
    warning_components: int
    critical_components: int
    last_check: datetime
    uptime_hours: float
    components: List[HealthCheckResponse]

class NetworkInfoResponse(BaseModel):
    server_ip: Optional[str]
    server_hostname: Optional[str]
    bandwidth_mbps: Optional[float]
    active_connections: Optional[int]
    is_connected: bool
    uptime_seconds: Optional[int]
    network_interfaces: Optional[Dict[str, Any]]
    dns_servers: Optional[List[str]]
    last_connectivity_check: datetime

# Configuration Management Endpoints

@router.post("/config", response_model=ConfigResponse)
async def update_system_config(
    config: ConfigUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Update or create system configuration"""
    try:
        # Validate configuration value
        if config.validation_rules:
            validate_config_value(config.value, config.validation_rules, config.config_type)
        
        # Check if config exists
        existing_config = db.query(SystemConfig).filter(
            SystemConfig.key == config.key,
            SystemConfig.scope == config.scope,
            SystemConfig.scope_id == config.scope_id
        ).first()
        
        if existing_config:
            # Update existing
            existing_config.value = config.value
            existing_config.config_type = config.config_type
            existing_config.description = config.description
            existing_config.is_sensitive = config.is_sensitive
            existing_config.validation_rules = config.validation_rules
            existing_config.updated_at = datetime.utcnow()
            existing_config.version += 1
            db_config = existing_config
        else:
            # Create new
            db_config = SystemConfig(
                key=config.key,
                value=config.value,
                config_type=config.config_type,
                scope=config.scope,
                scope_id=config.scope_id,
                description=config.description,
                is_sensitive=config.is_sensitive,
                validation_rules=config.validation_rules,
                created_by="system",
                updated_by="system"
            )
            db.add(db_config)
        
        db.commit()
        db.refresh(db_config)
        
        # Schedule background validation
        background_tasks.add_task(validate_config_impact, config.key, config.value)
        
        return ConfigResponse(
            key=db_config.key,
            value=db_config.get_typed_value(),
            config_type=db_config.config_type,
            scope=db_config.scope,
            scope_id=db_config.scope_id,
            description=db_config.description,
            is_sensitive=db_config.is_sensitive,
            created_at=db_config.created_at,
            updated_at=db_config.updated_at,
            version=db_config.version
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Configuration update failed: {str(e)}")

@router.get("/config", response_model=List[ConfigResponse])
async def get_system_configs(
    scope: Optional[ConfigScope] = None,
    scope_id: Optional[str] = None,
    include_sensitive: bool = Query(False, description="Include sensitive configurations"),
    db: Session = Depends(get_db)
):
    """Retrieve system configurations"""
    query = db.query(SystemConfig).filter(SystemConfig.is_active == True)
    
    if scope:
        query = query.filter(SystemConfig.scope == scope)
    if scope_id:
        query = query.filter(SystemConfig.scope_id == scope_id)
    if not include_sensitive:
        query = query.filter(SystemConfig.is_sensitive == False)
    
    configs = query.all()
    
    return [
        ConfigResponse(
            key=config.key,
            value=config.get_typed_value() if not config.is_sensitive else "***HIDDEN***",
            config_type=config.config_type,
            scope=config.scope,
            scope_id=config.scope_id,
            description=config.description,
            is_sensitive=config.is_sensitive,
            created_at=config.created_at,
            updated_at=config.updated_at,
            version=config.version
        )
        for config in configs
    ]

@router.get("/config/{key}")
async def get_config_by_key(
    key: str,
    scope: ConfigScope = ConfigScope.GLOBAL,
    scope_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get specific configuration by key"""
    config = db.query(SystemConfig).filter(
        SystemConfig.key == key,
        SystemConfig.scope == scope,
        SystemConfig.scope_id == scope_id,
        SystemConfig.is_active == True
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    return {
        "key": config.key,
        "value": config.get_typed_value(),
        "type": config.config_type,
        "description": config.description
    }

# Health Monitoring Endpoints

@router.get("/health", response_model=SystemHealthSummary)
async def get_system_health(
    component_type: Optional[ComponentType] = None,
    include_metrics: bool = Query(True, description="Include system metrics"),
    db: Session = Depends(get_db)
):
    """Get comprehensive system health status"""
    
    # Get latest health records
    query = db.query(SystemHealth)
    if component_type:
        query = query.filter(SystemHealth.component_type == component_type)
    
    # Get most recent health check for each component
    health_records = {}
    for record in query.all():
        key = f"{record.component_name}_{record.component_type}"
        if key not in health_records or record.last_check > health_records[key].last_check:
            health_records[key] = record
    
    components = []
    status_counts = {"healthy": 0, "warning": 0, "critical": 0, "unknown": 0}
    
    for record in health_records.values():
        components.append(HealthCheckResponse(
            component_name=record.component_name,
            component_type=record.component_type,
            status=record.status,
            response_time_ms=record.response_time_ms,
            error_message=record.error_message,
            cpu_usage=record.cpu_usage,
            memory_usage=record.memory_usage,
            disk_usage=record.disk_usage,
            custom_metrics=record.custom_metrics,
            last_check=record.last_check,
            consecutive_failures=record.consecutive_failures
        ))
        
        status_counts[record.status] += 1
    
    # Determine overall status
    overall_status = HealthStatus.HEALTHY
    if status_counts["critical"] > 0:
        overall_status = HealthStatus.CRITICAL
    elif status_counts["warning"] > 0:
        overall_status = HealthStatus.WARNING
    elif status_counts["unknown"] > 0:
        overall_status = HealthStatus.UNKNOWN
    
    # Calculate uptime
    uptime_hours = get_system_uptime_hours()
    
    return SystemHealthSummary(
        overall_status=overall_status,
        total_components=len(components),
        healthy_components=status_counts["healthy"],
        warning_components=status_counts["warning"],
        critical_components=status_counts["critical"],
        last_check=datetime.utcnow(),
        uptime_hours=uptime_hours,
        components=components
    )

@router.post("/health/check")
async def perform_health_check(
    background_tasks: BackgroundTasks,
    component_types: Optional[List[ComponentType]] = Query(None, description="Specific components to check"),
    db: Session = Depends(get_db)
):
    """Trigger comprehensive health check"""
    
    # Schedule background health checks
    if component_types:
        for component_type in component_types:
            background_tasks.add_task(run_component_health_check, component_type, db)
    else:
        background_tasks.add_task(run_full_health_check, db)
    
    return {
        "message": "Health check initiated",
        "timestamp": datetime.utcnow(),
        "components": component_types or "all"
    }

# Network Status Endpoints

@router.get("/lan-status", response_model=NetworkInfoResponse)
async def get_lan_status(db: Session = Depends(get_db)):
    """Get current LAN and network status information"""
    
    try:
        # Get or create network info record
        network_info = db.query(NetworkInfo).order_by(NetworkInfo.created_at.desc()).first()
        
        if not network_info or (datetime.utcnow() - network_info.updated_at).seconds > 300:  # 5 min cache
            # Update network information
            network_info = await update_network_info(db)
        
        return NetworkInfoResponse(
            server_ip=network_info.server_ip,
            server_hostname=network_info.server_hostname,
            bandwidth_mbps=network_info.bandwidth_mbps,
            active_connections=network_info.active_connections,
            is_connected=network_info.is_connected,
            uptime_seconds=network_info.uptime_seconds,
            network_interfaces=network_info.network_interfaces,
            dns_servers=network_info.dns_servers,
            last_connectivity_check=network_info.last_connectivity_check
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Network status check failed: {str(e)}")

@router.post("/lan-status/refresh")
async def refresh_lan_status(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Force refresh of network status information"""
    
    background_tasks.add_task(update_network_info, db, force_refresh=True)
    
    return {
        "message": "Network status refresh initiated",
        "timestamp": datetime.utcnow()
    }

# Utility Functions

def validate_config_value(value: str, validation_rules: Dict[str, Any], config_type: ConfigType):
    """Validate configuration value against rules"""
    
    if config_type == ConfigType.INTEGER:
        try:
            int_val = int(value)
            if "min" in validation_rules and int_val < validation_rules["min"]:
                raise ValueError(f"Value must be >= {validation_rules['min']}")
            if "max" in validation_rules and int_val > validation_rules["max"]:
                raise ValueError(f"Value must be <= {validation_rules['max']}")
        except ValueError as e:
            if "Value must be" in str(e):
                raise
            raise ValueError("Invalid integer value")
    
    elif config_type == ConfigType.FLOAT:
        try:
            float_val = float(value)
            if "min" in validation_rules and float_val < validation_rules["min"]:
                raise ValueError(f"Value must be >= {validation_rules['min']}")
            if "max" in validation_rules and float_val > validation_rules["max"]:
                raise ValueError(f"Value must be <= {validation_rules['max']}")
        except ValueError as e:
            if "Value must be" in str(e):
                raise
            raise ValueError("Invalid float value")
    
    elif config_type == ConfigType.JSON:
        try:
            json.loads(value)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format")

async def validate_config_impact(key: str, value: str):
    """Background task to validate configuration impact"""
    # Add custom validation logic for critical configurations
    pass

def get_system_uptime_hours() -> float:
    """Get system uptime in hours"""
    try:
        return psutil.boot_time() / 3600
    except:
        return 0.0

async def run_component_health_check(component_type: ComponentType, db: Session):
    """Run health check for specific component type"""
    
    start_time = time.time()
    
    try:
        if component_type == ComponentType.DATABASE:
            await check_database_health(db)
        elif component_type == ComponentType.API:
            await check_api_health(db)
        elif component_type == ComponentType.STORAGE:
            await check_storage_health(db)
        elif component_type == ComponentType.NETWORK:
            await check_network_health(db)
            
    except Exception as e:
        # Log health check failure
        health_record = SystemHealth(
            component_name=f"{component_type.value}_service",
            component_type=component_type,
            status=HealthStatus.CRITICAL,
            error_message=str(e),
            last_check=datetime.utcnow(),
            check_duration_ms=(time.time() - start_time) * 1000
        )
        db.add(health_record)
        db.commit()

async def run_full_health_check(db: Session):
    """Run comprehensive health check for all components"""
    
    for component_type in ComponentType:
        await run_component_health_check(component_type, db)

async def check_database_health(db: Session):
    """Check database connectivity and performance"""
    
    start_time = time.time()
    status = HealthStatus.HEALTHY
    error_message = None
    
    try:
        # Simple connectivity test
        db.execute("SELECT 1")
        response_time = (time.time() - start_time) * 1000
        
        if response_time > 1000:  # > 1 second
            status = HealthStatus.WARNING
        elif response_time > 5000:  # > 5 seconds
            status = HealthStatus.CRITICAL
            
    except Exception as e:
        status = HealthStatus.CRITICAL
        error_message = str(e)
        response_time = (time.time() - start_time) * 1000
    
    health_record = SystemHealth(
        component_name="primary_database",
        component_type=ComponentType.DATABASE,
        status=status,
        response_time_ms=response_time,
        error_message=error_message,
        last_check=datetime.utcnow(),
        check_duration_ms=response_time
    )
    
    if status == HealthStatus.HEALTHY:
        health_record.last_success = datetime.utcnow()
        health_record.consecutive_failures = 0
    else:
        # Get previous record to increment failure count
        prev_record = db.query(SystemHealth).filter(
            SystemHealth.component_name == "primary_database"
        ).order_by(SystemHealth.last_check.desc()).first()
        
        if prev_record:
            health_record.consecutive_failures = prev_record.consecutive_failures + 1
    
    db.add(health_record)
    db.commit()

async def check_api_health(db: Session):
    """Check API service health"""
    
    try:
        # Get system metrics
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        status = HealthStatus.HEALTHY
        if cpu_usage > 80 or memory.percent > 85 or disk.percent > 90:
            status = HealthStatus.WARNING
        if cpu_usage > 95 or memory.percent > 95 or disk.percent > 98:
            status = HealthStatus.CRITICAL
        
        health_record = SystemHealth(
            component_name="api_service",
            component_type=ComponentType.API,
            status=status,
            cpu_usage=cpu_usage,
            memory_usage=memory.percent,
            disk_usage=disk.percent,
            last_check=datetime.utcnow(),
            custom_metrics={
                "memory_available_gb": memory.available / (1024**3),
                "disk_free_gb": disk.free / (1024**3),
                "process_count": len(psutil.pids())
            }
        )
        
        if status == HealthStatus.HEALTHY:
            health_record.last_success = datetime.utcnow()
            health_record.consecutive_failures = 0
        
        db.add(health_record)
        db.commit()
        
    except Exception as e:
        health_record = SystemHealth(
            component_name="api_service",
            component_type=ComponentType.API,
            status=HealthStatus.CRITICAL,
            error_message=str(e),
            last_check=datetime.utcnow()
        )
        db.add(health_record)
        db.commit()

async def check_storage_health(db: Session):
    """Check storage system health"""
    
    try:
        disk_usage = psutil.disk_usage('/')
        
        status = HealthStatus.HEALTHY
        if disk_usage.percent > 80:
            status = HealthStatus.WARNING
        if disk_usage.percent > 95:
            status = HealthStatus.CRITICAL
        
        health_record = SystemHealth(
            component_name="storage_system",
            component_type=ComponentType.STORAGE,
            status=status,
            disk_usage=disk_usage.percent,
            last_check=datetime.utcnow(),
            custom_metrics={
                "total_gb": disk_usage.total / (1024**3),
                "used_gb": disk_usage.used / (1024**3),
                "free_gb": disk_usage.free / (1024**3)
            }
        )
        
        db.add(health_record)
        db.commit()
        
    except Exception as e:
        health_record = SystemHealth(
            component_name="storage_system",
            component_type=ComponentType.STORAGE,
            status=HealthStatus.CRITICAL,
            error_message=str(e),
            last_check=datetime.utcnow()
        )
        db.add(health_record)
        db.commit()

async def check_network_health(db: Session):
    """Check network connectivity health"""
    
    try:
        # Simple connectivity test
        start_time = time.time()
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        latency = (time.time() - start_time) * 1000
        
        status = HealthStatus.HEALTHY
        if latency > 200:  # > 200ms
            status = HealthStatus.WARNING
        if latency > 1000:  # > 1 second
            status = HealthStatus.CRITICAL
        
        health_record = SystemHealth(
            component_name="network_connectivity",
            component_type=ComponentType.NETWORK,
            status=status,
            network_latency=latency,
            last_check=datetime.utcnow()
        )
        
        db.add(health_record)
        db.commit()
        
    except Exception as e:
        health_record = SystemHealth(
            component_name="network_connectivity",
            component_type=ComponentType.NETWORK,
            status=HealthStatus.CRITICAL,
            error_message=str(e),
            last_check=datetime.utcnow()
        )
        db.add(health_record)
        db.commit()

async def update_network_info(db: Session, force_refresh: bool = False) -> NetworkInfo:
    """Update network information in database"""
    
    try:
        # Get network interfaces
        interfaces = {}
        for interface, addrs in psutil.net_if_addrs().items():
            interfaces[interface] = []
            for addr in addrs:
                interfaces[interface].append({
                    "family": str(addr.family),
                    "address": addr.address,
                    "netmask": addr.netmask,
                    "broadcast": addr.broadcast
                })
        
        # Get hostname and IP
        hostname = socket.gethostname()
        try:
            server_ip = socket.gethostbyname(hostname)
        except:
            server_ip = "127.0.0.1"
        
        # Create new network info record
        network_info = NetworkInfo(
            server_ip=server_ip,
            server_hostname=hostname,
            active_connections=len(psutil.net_connections()),
            network_interfaces=interfaces,
            is_connected=True,
            last_connectivity_check=datetime.utcnow(),
            uptime_seconds=int(time.time() - psutil.boot_time())
        )
        
        db.add(network_info)
        db.commit()
        db.refresh(network_info)
        
        return network_info
        
    except Exception as e:
        # Create minimal record on failure
        network_info = NetworkInfo(
            server_hostname=socket.gethostname(),
            is_connected=False,
            last_connectivity_check=datetime.utcnow()
        )
        db.add(network_info)
        db.commit()
        db.refresh(network_info)
        
        return network_info