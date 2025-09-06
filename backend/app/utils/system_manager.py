from sqlalchemy.orm import Session
from models import SystemConfig, ConfigScope, ConfigType
from database import SessionLocal
from typing import Any, Optional, Dict, List
import json
from datetime import datetime

class SystemConfigManager:
    """Centralized system configuration management"""
    
    def __init__(self):
        self._cache = {}
        self._cache_expiry = {}
        self.cache_duration_seconds = 300  # 5 minutes
    
    def get_config(
        self, 
        key: str, 
        default: Any = None, 
        scope: ConfigScope = ConfigScope.GLOBAL,
        scope_id: Optional[str] = None,
        force_refresh: bool = False
    ) -> Any:
        """Get configuration value with caching"""
        
        cache_key = f"{key}_{scope}_{scope_id}"
        
        # Check cache first
        if not force_refresh and cache_key in self._cache:
            if datetime.utcnow().timestamp() < self._cache_expiry.get(cache_key, 0):
                return self._cache[cache_key]
        
        # Fetch from database
        db = SessionLocal()
        try:
            config = db.query(SystemConfig).filter(
                SystemConfig.key == key,
                SystemConfig.scope == scope,
                SystemConfig.scope_id == scope_id,
                SystemConfig.is_active == True
            ).first()
            
            if config:
                value = config.get_typed_value()
                # Cache the value
                self._cache[cache_key] = value
                self._cache_expiry[cache_key] = datetime.utcnow().timestamp() + self.cache_duration_seconds
                return value
            
            return default
            
        finally:
            db.close()
    
    def set_config(
        self,
        key: str,
        value: Any,
        config_type: ConfigType = ConfigType.STRING,
        scope: ConfigScope = ConfigScope.GLOBAL,
        scope_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> bool:
        """Set configuration value"""
        
        db = SessionLocal()
        try:
            # Convert value to string for storage
            str_value = str(value)
            if config_type == ConfigType.JSON:
                str_value = json.dumps(value)
            
            existing = db.query(SystemConfig).filter(
                SystemConfig.key == key,
                SystemConfig.scope == scope,
                SystemConfig.scope_id == scope_id
            ).first()
            
            if existing:
                existing.value = str_value
                existing.config_type = config_type
                existing.description = description
                existing.updated_at = datetime.utcnow()
                existing.version += 1
            else:
                new_config = SystemConfig(
                    key=key,
                    value=str_value,
                    config_type=config_type,
                    scope=scope,
                    scope_id=scope_id,
                    description=description,
                    created_by="system_manager"
                )
                db.add(new_config)
            
            db.commit()
            
            # Update cache
            cache_key = f"{key}_{scope}_{scope_id}"
            self._cache[cache_key] = value
            self._cache_expiry[cache_key] = datetime.utcnow().timestamp() + self.cache_duration_seconds
            
            return True
            
        except Exception as e:
            db.rollback()
            print(f"Failed to set config {key}: {e}")
            return False
        finally:
            db.close()
    
    def get_all_configs(
        self, 
        scope: Optional[ConfigScope] = None,
        include_sensitive: bool = False
    ) -> Dict[str, Any]:
        """Get all configurations as dictionary"""
        
        db = SessionLocal()
        try:
            query = db.query(SystemConfig).filter(SystemConfig.is_active == True)
            
            if scope:
                query = query.filter(SystemConfig.scope == scope)
            if not include_sensitive:
                query = query.filter(SystemConfig.is_sensitive == False)
            
            configs = {}
            for config in query.all():
                configs[config.key] = config.get_typed_value()
            
            return configs
            
        finally:
            db.close()
    
    def clear_cache(self):
        """Clear configuration cache"""
        self._cache.clear()
        self._cache_expiry.clear()

# Global instance
config_manager = SystemConfigManager()
