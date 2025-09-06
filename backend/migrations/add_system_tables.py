from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'system_tables_001'
down_revision = 'previous_revision_id'  # Replace with your latest revision
branch_labels = None
depends_on = None

def upgrade():
    """Add system management tables"""
    
    # SystemConfig table
    op.create_table('system_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=200), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('config_type', sa.String(length=20), nullable=False),
        sa.Column('scope', sa.String(length=20), nullable=False),
        sa.Column('scope_id', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_encrypted', sa.Boolean(), nullable=True),
        sa.Column('is_sensitive', sa.Boolean(), nullable=True),
        sa.Column('validation_rules', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('updated_by', sa.String(length=100), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_configs_id'), 'system_configs', ['id'], unique=False)
    op.create_index(op.f('ix_system_configs_key'), 'system_configs', ['key'], unique=True)
    
    # SystemHealth table
    op.create_table('system_health',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('component_name', sa.String(length=100), nullable=False),
        sa.Column('component_type', sa.String(length=30), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('response_time_ms', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('cpu_usage', sa.Float(), nullable=True),
        sa.Column('memory_usage', sa.Float(), nullable=True),
        sa.Column('disk_usage', sa.Float(), nullable=True),
        sa.Column('network_latency', sa.Float(), nullable=True),
        sa.Column('custom_metrics', sa.JSON(), nullable=True),
        sa.Column('last_check', sa.DateTime(), nullable=True),
        sa.Column('check_duration_ms', sa.Float(), nullable=True),
        sa.Column('consecutive_failures', sa.Integer(), nullable=True),
        sa.Column('last_success', sa.DateTime(), nullable=True),
        sa.Column('alert_threshold_warning', sa.Float(), nullable=True),
        sa.Column('alert_threshold_critical', sa.Float(), nullable=True),
        sa.Column('alert_sent', sa.Boolean(), nullable=True),
        sa.Column('alert_sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_health_id'), 'system_health', ['id'], unique=False)
    op.create_index(op.f('ix_system_health_component_name'), 'system_health', ['component_name'], unique=False)
    
    # NetworkInfo table
    op.create_table('network_info',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('server_ip', sa.String(length=45), nullable=True),
        sa.Column('server_hostname', sa.String(length=255), nullable=True),
        sa.Column('server_port', sa.Integer(), nullable=True),
        sa.Column('bandwidth_mbps', sa.Float(), nullable=True),
        sa.Column('packet_loss_percentage', sa.Float(), nullable=True),
        sa.Column('average_latency_ms', sa.Float(), nullable=True),
        sa.Column('active_connections', sa.Integer(), nullable=True),
        sa.Column('max_connections', sa.Integer(), nullable=True),
        sa.Column('connection_pool_size', sa.Integer(), nullable=True),
        sa.Column('dns_servers', sa.JSON(), nullable=True),
        sa.Column('gateway_ip', sa.String(length=45), nullable=True),
        sa.Column('subnet_mask', sa.String(length=18), nullable=True),
        sa.Column('network_interfaces', sa.JSON(), nullable=True),
        sa.Column('is_connected', sa.Boolean(), nullable=True),
        sa.Column('last_connectivity_check', sa.DateTime(), nullable=True),
        sa.Column('uptime_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_network_info_id'), 'network_info', ['id'], unique=False)
    
    # SystemAlert table
    op.create_table('system_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('component', sa.String(length=100), nullable=True),
        sa.Column('source_id', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('acknowledged', sa.Boolean(), nullable=True),
        sa.Column('acknowledged_by', sa.String(length=100), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=True),
        sa.Column('resolved_by', sa.String(length=100), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('email_sent', sa.Boolean(), nullable=True),
        sa.Column('slack_sent', sa.Boolean(), nullable=True),
        sa.Column('webhook_sent', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_alerts_id'), 'system_alerts', ['id'], unique=False)

def downgrade():
    """Remove system management tables"""
    op.drop_index(op.f('ix_system_alerts_id'), table_name='system_alerts')
    op.drop_table('system_alerts')
    
    op.drop_index(op.f('ix_network_info_id'), table_name='network_info')
    op.drop_table('network_info')
    
    op.drop_index(op.f('ix_system_health_component_name'), table_name='system_health')
    op.drop_index(op.f('ix_system_health_id'), table_name='system_health')
    op.drop_table('system_health')
    
    op.drop_index(op.f('ix_system_configs_key'), table_name='system_configs')
    op.drop_index(op.f('ix_system_configs_id'), table_name='system_configs')
    op.drop_table('system_configs')
