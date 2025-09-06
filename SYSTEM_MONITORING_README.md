# System Monitoring Integration Guide

## Overview

The Corporate Wellness Platform now includes comprehensive system monitoring capabilities that provide real-time health checks, configuration management, network monitoring, and alerting systems.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Run System Setup

```bash
python startup_system_monitoring.py
```

### 3. Start the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Access System Monitoring

- **Health Dashboard**: `http://localhost:8000/system/health`
- **Configuration Management**: `http://localhost:8000/system/config`
- **Network Status**: `http://localhost:8000/system/lan-status`
- **API Documentation**: `http://localhost:8000/docs`

## 📁 New Files Structure

```
backend/
├── app/
│   ├── utils/
│   │   ├── __init__.py
│   │   └── system_manager.py          # Configuration management
│   ├── services/
│   │   └── health_monitor.py          # Background health monitoring
│   └── main.py                        # Updated with system integration
├── migrations/
│   ├── __init__.py
│   └── add_system_tables.py           # Database migration script
├── config/
│   └── system_defaults.json           # Default configuration template
├── startup_system_monitoring.py       # System setup script
└── requirements.txt                    # Updated dependencies
```

## 🏥 Health Monitoring

### Components Monitored

1. **Database** - Connection, response time, query performance
2. **API Service** - CPU, memory, disk usage, system metrics
3. **Storage System** - Disk usage, available space
4. **Network** - Connectivity, latency, interface status
5. **Authentication** - Service availability
6. **ML Service** - Processing capabilities (placeholder)
7. **Analytics Engine** - Data processing status (placeholder)

### Health Status Levels

- **🟢 HEALTHY** - Component operating normally
- **🟡 WARNING** - Component has minor issues but functional
- **🔴 CRITICAL** - Component has serious issues or is down
- **⚪ UNKNOWN** - Component status not yet determined

### API Endpoints

```http
GET /system/health                    # Get overall system health
POST /system/health/check            # Trigger health check
GET /system/health?component_type=DATABASE  # Filter by component
```

## ⚙️ Configuration Management

### Configuration Scopes

- **GLOBAL** - System-wide settings
- **TENANT** - Organization-specific settings
- **USER** - User-specific settings
- **PROGRAM** - Program-specific settings

### Configuration Types

- **STRING** - Text values
- **INTEGER** - Numeric values
- **FLOAT** - Decimal values
- **BOOLEAN** - True/false values
- **JSON** - Complex structured data
- **ENCRYPTED** - Sensitive encrypted data

### API Endpoints

```http
GET /system/config                    # Get all configurations
GET /system/config/{key}             # Get specific configuration
POST /system/config                   # Create/update configuration
```

### Example Configuration Update

```json
{
  "key": "system.health_check_interval_minutes",
  "value": "10",
  "config_type": "INTEGER",
  "scope": "GLOBAL",
  "description": "Health check interval in minutes",
  "is_sensitive": false
}
```

## 🌐 Network Monitoring

### Network Information Tracked

- Server IP and hostname
- Active connections
- Network interfaces
- Bandwidth usage
- Connectivity status
- DNS configuration
- System uptime

### API Endpoints

```http
GET /system/lan-status               # Get current network status
POST /system/lan-status/refresh      # Force refresh network info
```

## 🚨 Alert System

### Alert Types

- **health** - Component health issues
- **performance** - Performance degradation
- **security** - Security-related alerts
- **reliability** - System reliability issues

### Alert Severity Levels

- **low** - Informational alerts
- **medium** - Moderate issues requiring attention
- **high** - Serious issues requiring immediate attention
- **critical** - Critical issues requiring urgent action

## 🔧 System Configuration

### Default Configurations

#### System Settings
```json
{
  "system.health_check_interval_minutes": 5,
  "system.max_log_retention_days": 30,
  "system.alert_email_enabled": false,
  "system.maintenance_window_start": "02:00",
  "system.max_concurrent_users": 1000,
  "system.session_timeout_minutes": 60
}
```

#### Analytics Settings
```json
{
  "analytics.batch_size": 1000,
  "analytics.prediction_cache_hours": 24,
  "analytics.ml_model_retrain_days": 7,
  "analytics.report_generation_max_records": 50000
}
```

#### Security Settings
```json
{
  "security.password_min_length": 8,
  "security.max_login_attempts": 5,
  "security.lockout_duration_minutes": 15,
  "security.jwt_expiration_hours": 24
}
```

#### Performance Settings
```json
{
  "performance.database_pool_size": 20,
  "performance.cache_expiration_minutes": 15,
  "performance.max_file_upload_mb": 100,
  "performance.request_timeout_seconds": 30
}
```

## 🗄️ Database Schema

### New Tables

1. **system_configs** - System configuration storage
2. **system_health** - Health monitoring records
3. **network_info** - Network status information
4. **system_alerts** - System alerts and notifications

### Migration

Run the migration to create system tables:

```bash
# Using Alembic (if configured)
alembic upgrade head

# Or run the startup script which creates tables automatically
python startup_system_monitoring.py
```

## 🔄 Background Services

### Health Monitor Service

The `HealthMonitorService` runs continuously in the background:

- Performs health checks at configurable intervals
- Monitors system metrics (CPU, memory, disk, network)
- Creates alerts for critical conditions
- Tracks failure patterns and recovery

### Configuration Manager

The `SystemConfigManager` provides:

- Cached configuration access
- Type-safe configuration retrieval
- Configuration validation
- Audit trail for configuration changes

## 📊 Usage Examples

### Get System Health Status

```python
import httpx

response = httpx.get("http://localhost:8000/system/health")
health_data = response.json()

print(f"Overall Status: {health_data['overall_status']}")
print(f"Healthy Components: {health_data['healthy_components']}")
print(f"Critical Components: {health_data['critical_components']}")
```

### Update Configuration

```python
import httpx

config_update = {
    "key": "system.health_check_interval_minutes",
    "value": "3",
    "config_type": "INTEGER",
    "description": "Updated health check interval"
}

response = httpx.post("http://localhost:8000/system/config", json=config_update)
```

### Trigger Health Check

```python
import httpx

response = httpx.post("http://localhost:8000/system/health/check")
print(response.json()["message"])  # "Health check initiated"
```

## 🛠️ Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check database configuration in `.env`
   - Ensure database server is running
   - Verify connection credentials

2. **Missing Dependencies**
   - Run `pip install -r requirements.txt`
   - Check for system-specific requirements (e.g., `psutil`)

3. **Permission Issues**
   - Ensure proper file permissions for log directories
   - Check database write permissions

4. **High Resource Usage**
   - Monitor system metrics via `/system/health`
   - Adjust health check intervals if needed
   - Review application logs for issues

### Log Locations

- Application logs: Check FastAPI/uvicorn output
- Health monitor logs: Integrated with application logging
- System metrics: Available via `/system/health` endpoint

## 🔐 Security Considerations

1. **Sensitive Configurations**
   - Mark sensitive configs with `is_sensitive: true`
   - Use encrypted configuration types for secrets
   - Restrict access to configuration endpoints

2. **Network Security**
   - Monitor network interfaces and connections
   - Set up alerts for unusual network activity
   - Regularly review network configuration

3. **Access Control**
   - Implement proper authentication for system endpoints
   - Use role-based access control for configuration changes
   - Audit configuration modifications

## 📈 Performance Optimization

1. **Configuration Caching**
   - Configurations are cached for 5 minutes by default
   - Use `force_refresh=True` to bypass cache
   - Monitor cache hit rates

2. **Health Check Optimization**
   - Adjust check intervals based on system load
   - Use component-specific health checks when possible
   - Monitor health check performance

3. **Database Performance**
   - Indexes are created for frequently queried fields
   - Regular cleanup of old health records
   - Monitor database connection pool usage

## 🚀 Next Steps

1. **Custom Metrics**
   - Add application-specific health checks
   - Implement custom performance metrics
   - Create domain-specific alerts

2. **Integration**
   - Connect with external monitoring tools
   - Set up email/Slack notifications
   - Implement webhook integrations

3. **Dashboards**
   - Create real-time monitoring dashboards
   - Implement historical trend analysis
   - Add predictive health analytics

## 📞 Support

For issues or questions regarding system monitoring:

1. Check the application logs for error details
2. Review the health status via `/system/health`
3. Verify configuration via `/system/config`
4. Run the startup script to validate setup

---

**System Monitoring Integration** - Corporate Wellness Platform v3.1.0
