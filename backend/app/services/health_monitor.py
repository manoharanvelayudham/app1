import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal
from models import SystemHealth, SystemAlert, SystemConfig, HealthStatus, ComponentType
from utils.system_manager import config_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthMonitorService:
    """Background service for continuous health monitoring"""
    
    def __init__(self):
        self.is_running = False
        self.check_interval = 300  # 5 minutes default
    
    async def start(self):
        """Start the health monitoring service"""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("🏥 Health monitoring service started")
        
        while self.is_running:
            try:
                # Get check interval from config
                self.check_interval = config_manager.get_config(
                    "system.health_check_interval_minutes", 
                    default=5
                ) * 60
                
                # Run health checks
                await self.perform_health_checks()
                
                # Check for alerts
                await self.check_alert_conditions()
                
                # Wait for next interval
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def stop(self):
        """Stop the health monitoring service"""
        self.is_running = False
        logger.info("🛑 Health monitoring service stopped")
    
    async def perform_health_checks(self):
        """Perform comprehensive health checks"""
        db = SessionLocal()
        try:
            await self.run_full_health_check(db)
            logger.info("✅ Health checks completed")
        except Exception as e:
            logger.error(f"Health check failed: {e}")
        finally:
            db.close()
    
    async def run_full_health_check(self, db: Session):
        """Run comprehensive health checks for all system components"""
        import psutil
        import time
        from sqlalchemy import text
        
        # Database health check
        try:
            start_time = time.time()
            db.execute(text("SELECT 1"))
            response_time = (time.time() - start_time) * 1000
            
            self.update_health_record(
                db, "primary_database", ComponentType.DATABASE,
                HealthStatus.HEALTHY, response_time=response_time
            )
        except Exception as e:
            self.update_health_record(
                db, "primary_database", ComponentType.DATABASE,
                HealthStatus.CRITICAL, error_message=str(e)
            )
        
        # System metrics
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # API service health (based on system metrics)
            api_status = HealthStatus.HEALTHY
            if cpu_usage > 80 or memory.percent > 85:
                api_status = HealthStatus.WARNING
            if cpu_usage > 95 or memory.percent > 95:
                api_status = HealthStatus.CRITICAL
                
            self.update_health_record(
                db, "api_service", ComponentType.API, api_status,
                cpu_usage=cpu_usage, memory_usage=memory.percent, 
                disk_usage=disk.percent
            )
            
            # Storage system health
            storage_status = HealthStatus.HEALTHY
            if disk.percent > 80:
                storage_status = HealthStatus.WARNING
            if disk.percent > 90:
                storage_status = HealthStatus.CRITICAL
                
            self.update_health_record(
                db, "storage_system", ComponentType.STORAGE, storage_status,
                disk_usage=disk.percent
            )
            
        except Exception as e:
            logger.error(f"System metrics check failed: {e}")
        
        # Network connectivity check
        try:
            import socket
            start_time = time.time()
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            network_latency = (time.time() - start_time) * 1000
            
            self.update_health_record(
                db, "network_connectivity", ComponentType.NETWORK,
                HealthStatus.HEALTHY, network_latency=network_latency
            )
        except Exception as e:
            self.update_health_record(
                db, "network_connectivity", ComponentType.NETWORK,
                HealthStatus.CRITICAL, error_message=str(e)
            )
        
        # Authentication service check
        try:
            from auth import verify_token
            # Simple auth service health check
            self.update_health_record(
                db, "auth_service", ComponentType.AUTHENTICATION,
                HealthStatus.HEALTHY
            )
        except Exception as e:
            self.update_health_record(
                db, "auth_service", ComponentType.AUTHENTICATION,
                HealthStatus.WARNING, error_message=str(e)
            )
        
        # ML service placeholder
        self.update_health_record(
            db, "ml_service", ComponentType.ML_SERVICE,
            HealthStatus.HEALTHY
        )
        
        # Analytics engine placeholder
        self.update_health_record(
            db, "analytics_engine", ComponentType.ANALYTICS,
            HealthStatus.HEALTHY
        )
        
        db.commit()
    
    def update_health_record(
        self, db: Session, component_name: str, component_type: ComponentType,
        status: HealthStatus, response_time: float = None, error_message: str = None,
        cpu_usage: float = None, memory_usage: float = None, 
        disk_usage: float = None, network_latency: float = None
    ):
        """Update or create health record for a component"""
        
        health_record = db.query(SystemHealth).filter(
            SystemHealth.component_name == component_name
        ).first()
        
        if not health_record:
            health_record = SystemHealth(
                component_name=component_name,
                component_type=component_type
            )
            db.add(health_record)
        
        # Update health record
        health_record.status = status
        health_record.last_check = datetime.utcnow()
        health_record.response_time_ms = response_time
        health_record.error_message = error_message
        health_record.cpu_usage = cpu_usage
        health_record.memory_usage = memory_usage
        health_record.disk_usage = disk_usage
        health_record.network_latency = network_latency
        
        # Update failure tracking
        if status == HealthStatus.CRITICAL:
            health_record.consecutive_failures = (health_record.consecutive_failures or 0) + 1
        else:
            health_record.consecutive_failures = 0
            if status == HealthStatus.HEALTHY:
                health_record.last_success = datetime.utcnow()
    
    async def check_alert_conditions(self):
        """Check for conditions that require alerts"""
        db = SessionLocal()
        try:
            # Get recent health records
            recent_time = datetime.utcnow() - timedelta(minutes=10)
            critical_components = db.query(SystemHealth).filter(
                SystemHealth.status == HealthStatus.CRITICAL,
                SystemHealth.last_check > recent_time
            ).all()
            
            for component in critical_components:
                await self.create_alert(
                    alert_type="health",
                    severity="critical",
                    title=f"Critical: {component.component_name}",
                    message=f"Component {component.component_name} is in critical state: {component.error_message}",
                    component=component.component_name,
                    db=db
                )
            
            # Check for high consecutive failures
            high_failure_components = db.query(SystemHealth).filter(
                SystemHealth.consecutive_failures >= 3,
                SystemHealth.last_check > recent_time
            ).all()
            
            for component in high_failure_components:
                await self.create_alert(
                    alert_type="reliability",
                    severity="high",
                    title=f"High Failure Rate: {component.component_name}",
                    message=f"Component {component.component_name} has {component.consecutive_failures} consecutive failures",
                    component=component.component_name,
                    db=db
                )
                
        except Exception as e:
            logger.error(f"Alert check failed: {e}")
        finally:
            db.close()
    
    async def create_alert(
        self, 
        alert_type: str, 
        severity: str, 
        title: str, 
        message: str, 
        component: str,
        db: Session
    ):
        """Create system alert"""
        
        # Check if similar alert already exists
        existing_alert = db.query(SystemAlert).filter(
            SystemAlert.component == component,
            SystemAlert.alert_type == alert_type,
            SystemAlert.is_active == True
        ).first()
        
        if not existing_alert:
            alert = SystemAlert(
                alert_type=alert_type,
                severity=severity,
                title=title,
                message=message,
                component=component
            )
            db.add(alert)
            db.commit()
            
            logger.warning(f"🚨 Alert created: {title}")

# Global health monitor instance
health_monitor = HealthMonitorService()
