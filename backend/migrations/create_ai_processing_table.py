"""
AI Processing Pipeline Database Migration
Creates ai_processing table for tracking AI processing status and results
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'ai_processing_pipeline'
down_revision = 'audit_logs_table'  # Previous migration
branch_labels = None
depends_on = None

def upgrade():
    # Create ai_processing table
    op.create_table('ai_processing',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('response_id', sa.Integer(), nullable=False),
        sa.Column('processing_status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'RETRYING', name='aiprocessingstatus'), nullable=False, default='PENDING'),
        sa.Column('input_type', sa.Enum('TEXT', 'IMAGE', 'AUDIO', 'DOCUMENT', name='aiinputtype'), nullable=False),
        sa.Column('original_content', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('processed_content', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('standardized_text', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('processing_steps', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('max_retries', sa.Integer(), nullable=False, default=3),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['response_id'], ['participant_responses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for efficient querying
    op.create_index('ix_ai_processing_response_id', 'ai_processing', ['response_id'])
    op.create_index('ix_ai_processing_status', 'ai_processing', ['processing_status'])
    op.create_index('ix_ai_processing_input_type', 'ai_processing', ['input_type'])
    op.create_index('ix_ai_processing_created_at', 'ai_processing', ['created_at'])
    op.create_index('ix_ai_processing_status_created', 'ai_processing', ['processing_status', 'created_at'])

def downgrade():
    # Drop indexes
    op.drop_index('ix_ai_processing_status_created', table_name='ai_processing')
    op.drop_index('ix_ai_processing_created_at', table_name='ai_processing')
    op.drop_index('ix_ai_processing_input_type', table_name='ai_processing')
    op.drop_index('ix_ai_processing_status', table_name='ai_processing')
    op.drop_index('ix_ai_processing_response_id', table_name='ai_processing')
    
    # Drop table
    op.drop_table('ai_processing')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS aiprocessingstatus")
    op.execute("DROP TYPE IF EXISTS aiinputtype")