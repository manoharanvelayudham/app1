"""
Database migration script to create audit_logs table
Run this script to add audit logging functionality to the database
"""

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import os
from datetime import datetime

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")

def create_audit_logs_table():
    """Create the audit_logs table with indexes and constraints"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        action VARCHAR(100) NOT NULL,
        resource_type VARCHAR(50) NOT NULL,
        resource_id INTEGER,
        old_values JSONB,
        new_values JSONB,
        ip_address INET,
        user_agent TEXT,
        session_id VARCHAR(255),
        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        metadata JSONB DEFAULT '{}'::jsonb
    );
    """
    
    # Create indexes for performance
    create_indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);",
        "CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);",
        "CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);",
        "CREATE INDEX IF NOT EXISTS idx_audit_logs_session ON audit_logs(session_id);",
        "CREATE INDEX IF NOT EXISTS idx_audit_logs_compound ON audit_logs(user_id, resource_type, timestamp DESC);"
    ]
    
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Create the table
            conn.execute(text(create_table_sql))
            print("✅ Created audit_logs table")
            
            # Create indexes
            for index_sql in create_indexes_sql:
                conn.execute(text(index_sql))
            
            print("✅ Created audit_logs indexes")
            
            # Commit the transaction
            conn.commit()
            
        print("🎯 Audit logs table migration completed successfully!")
        
    except SQLAlchemyError as e:
        print(f"❌ Database migration failed: {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error during migration: {e}")
        raise

if __name__ == "__main__":
    print("🚀 Starting audit logs table migration...")
    create_audit_logs_table()