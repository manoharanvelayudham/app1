#!/usr/bin/env python3
"""
Database migration script to create the coach_reviews table
Run this script to add the review system to your database
"""

import sys
from sqlalchemy import create_engine, text
from database import DATABASE_URL

def create_reviews_table():
    """Create the coach_reviews table and update existing tables"""
    
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as connection:
        # Start a transaction
        trans = connection.begin()
        
        try:
            print("Creating ReviewStatus enum...")
            # Create the enum type for review status
            connection.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE reviewstatus AS ENUM ('pending', 'in_progress', 'completed');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            
            print("Creating coach_reviews table...")
            # Create the coach_reviews table
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS coach_reviews (
                    id SERIAL PRIMARY KEY,
                    response_id INTEGER NOT NULL,
                    coach_id INTEGER NOT NULL,
                    score FLOAT,
                    max_score FLOAT DEFAULT 100.0,
                    comments TEXT,
                    status reviewstatus DEFAULT 'pending',
                    started_at TIMESTAMP WITH TIME ZONE,
                    completed_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    
                    CONSTRAINT fk_review_response 
                        FOREIGN KEY (response_id) 
                        REFERENCES participant_responses(id) 
                        ON DELETE CASCADE,
                    
                    CONSTRAINT fk_review_coach 
                        FOREIGN KEY (coach_id) 
                        REFERENCES users(id) 
                        ON DELETE CASCADE,
                    
                    CONSTRAINT unique_coach_response_review 
                        UNIQUE (response_id, coach_id)
                );
            """))
            
            print("Creating indexes...")
            # Create indexes for better performance
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_coach_reviews_response_id ON coach_reviews(response_id);
                CREATE INDEX IF NOT EXISTS idx_coach_reviews_coach_id ON coach_reviews(coach_id);
                CREATE INDEX IF NOT EXISTS idx_coach_reviews_status ON coach_reviews(status);
                CREATE INDEX IF NOT EXISTS idx_coach_reviews_created_at ON coach_reviews(created_at);
            """))
            
            print("Creating trigger for updated_at timestamp...")
            # Create trigger to automatically update the updated_at timestamp
            connection.execute(text("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
                
                DROP TRIGGER IF EXISTS update_coach_reviews_updated_at ON coach_reviews;
                
                CREATE TRIGGER update_coach_reviews_updated_at
                    BEFORE UPDATE ON coach_reviews
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
            """))
            
            # Commit the transaction
            trans.commit()
            print("✅ Coach reviews table created successfully!")
            print("✅ Indexes and triggers created!")
            print("✅ Database migration completed!")
            
        except Exception as e:
            # Rollback on error
            trans.rollback()
            print(f"❌ Error creating reviews table: {e}")
            raise
        
        finally:
            connection.close()

def verify_table_creation():
    """Verify that the table was created correctly"""
    
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as connection:
        try:
            # Check if table exists
            result = connection.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'coach_reviews'
                );
            """))
            
            table_exists = result.fetchone()[0]
            
            if table_exists:
                print("✅ Table verification: coach_reviews table exists")
                
                # Check table structure
                result = connection.execute(text("""
                    SELECT column_name, data_type, is_nullable, column_default 
                    FROM information_schema.columns 
                    WHERE table_name = 'coach_reviews'
                    ORDER BY ordinal_position;
                """))
                
                columns = result.fetchall()
                print(f"✅ Table has {len(columns)} columns:")
                for col in columns:
                    print(f"   - {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
                
                # Check constraints
                result = connection.execute(text("""
                    SELECT constraint_name, constraint_type 
                    FROM information_schema.table_constraints 
                    WHERE table_name = 'coach_reviews';
                """))
                
                constraints = result.fetchall()
                print(f"✅ Table has {len(constraints)} constraints:")
                for constraint in constraints:
                    print(f"   - {constraint[0]}: {constraint[1]}")
                    
            else:
                print("❌ Table verification failed: coach_reviews table does not exist")
                return False
                
        except Exception as e:
            print(f"❌ Error verifying table: {e}")
            return False
        
        finally:
            connection.close()
    
    return True

if __name__ == "__main__":
    try:
        print("🚀 Starting coach reviews database migration...")
        print(f"Database URL: {DATABASE_URL}")
        
        # Create the table
        create_reviews_table()
        
        # Verify creation
        if verify_table_creation():
            print("\n🎉 Migration completed successfully!")
            print("\nNext steps:")
            print("1. Add the CoachReview model to your models.py")
            print("2. Add the reviews relationship to ParticipantResponse model")
            print("3. Include the reviews router in your main.py")
            print("4. Test the review endpoints")
        else:
            print("\n❌ Migration verification failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Migration failed: {e}")
        sys.exit(1)