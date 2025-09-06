# Run this script to create the new database table
# Save as create_responses_table.py and run with: python create_responses_table.py

# create_responses_table.py
import sys
import os

from sqlalchemy import create_engine, text
from backend.models import Base, ParticipantResponse
from backend.database import DATABASE_URL


# Add the current directory to Python path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from models import Base, ParticipantResponse
from database import DATABASE_URL, get_db

def create_tables():
    """Create the participant_responses table"""
    try:
        engine = create_engine(DATABASE_URL)
        
        # Create only new tables (won't affect existing ones)
        Base.metadata.create_all(bind=engine)
        
        # Verify the table was created
        with engine.connect() as connection:
            result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='participant_responses';"))
            if result.fetchone():
                print("✅ participant_responses table created successfully")
            else:
                print("❌ Failed to create participant_responses table")
                
    except Exception as e:
        print(f"❌ Error creating table: {str(e)}")
        print("Make sure you have:")
        print("1. Updated models.py with the new ParticipantResponse model")
        print("2. The database file exists or can be created")
        print("3. All dependencies are installed")

def check_table_structure():
    """Check the structure of the new table"""
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            result = connection.execute(text("PRAGMA table_info(participant_responses);"))
            columns = result.fetchall()
            if columns:
                print("\n📋 participant_responses table structure:")
                for col in columns:
                    print(f"  - {col[1]} ({col[2]})")
            else:
                print("❌ participant_responses table not found")
    except Exception as e:
        print(f"❌ Error checking table structure: {str(e)}")

if __name__ == "__main__":
    print("🔄 Creating participant_responses table...")
    create_tables()
    print("\n🔍 Checking table structure...")
    check_table_structure()
    print("\n✨ Database migration complete!")