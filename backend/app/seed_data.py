import hashlib
import sys
import os

# Add the current directory to Python path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, User, Program, Enrollment, Assessment, UserRole, ProgramDifficulty, AssessmentType
from datetime import datetime, timedelta

def hash_password(password: str) -> str:
    """Simple password hashing using hashlib (for development only)"""
    # In production, use proper bcrypt hashing
    return hashlib.sha256(password.encode()).hexdigest()

def create_seed_data():
    """Create seed data for the database"""
    
    # Create all tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully")
    
    db = SessionLocal()
    
    try:
        # Check if data already exists
        existing_users = db.query(User).count()
        if existing_users > 0:
            print(f"⚠️  Seed data already exists ({existing_users} users found), skipping...")
            return
        
        print("Creating seed data...")
        
        # Create Users (5 per role)
        users_data = [
            # Clients
            {"username": "client1", "email": "client1@fitness.com", "first_name": "John", "last_name": "Doe", "role": UserRole.CLIENT, "phone": "+1234567890", "date_of_birth": datetime(1990, 5, 15)},
            {"username": "client2", "email": "client2@fitness.com", "first_name": "Jane", "last_name": "Smith", "role": UserRole.CLIENT, "phone": "+1234567891", "date_of_birth": datetime(1988, 8, 22)},
            {"username": "client3", "email": "client3@fitness.com", "first_name": "Mike", "last_name": "Johnson", "role": UserRole.CLIENT, "phone": "+1234567892", "date_of_birth": datetime(1992, 3, 10)},
            {"username": "client4", "email": "client4@fitness.com", "first_name": "Sarah", "last_name": "Wilson", "role": UserRole.CLIENT, "phone": "+1234567893", "date_of_birth": datetime(1985, 12, 5)},
            {"username": "client5", "email": "client5@fitness.com", "first_name": "David", "last_name": "Brown", "role": UserRole.CLIENT, "phone": "+1234567894", "date_of_birth": datetime(1993, 7, 18)},
            
            # Trainers
            {"username": "trainer1", "email": "trainer1@fitness.com", "first_name": "Alex", "last_name": "Martinez", "role": UserRole.TRAINER, "phone": "+1234567895"},
            {"username": "trainer2", "email": "trainer2@fitness.com", "first_name": "Emily", "last_name": "Davis", "role": UserRole.TRAINER, "phone": "+1234567896"},
            {"username": "trainer3", "email": "trainer3@fitness.com", "first_name": "Chris", "last_name": "Anderson", "role": UserRole.TRAINER, "phone": "+1234567897"},
            {"username": "trainer4", "email": "trainer4@fitness.com", "first_name": "Lisa", "last_name": "Taylor", "role": UserRole.TRAINER, "phone": "+1234567898"},
            {"username": "trainer5", "email": "trainer5@fitness.com", "first_name": "Ryan", "last_name": "Thomas", "role": UserRole.TRAINER, "phone": "+1234567899"},
            
            # Admins
            {"username": "admin1", "email": "admin1@fitness.com", "first_name": "Admin", "last_name": "User", "role": UserRole.ADMIN, "phone": "+1234567900"},
            {"username": "admin2", "email": "admin2@fitness.com", "first_name": "Super", "last_name": "Admin", "role": UserRole.ADMIN, "phone": "+1234567901"},
            {"username": "admin3", "email": "admin3@fitness.com", "first_name": "System", "last_name": "Administrator", "role": UserRole.ADMIN, "phone": "+1234567902"},
            {"username": "admin4", "email": "admin4@fitness.com", "first_name": "Manager", "last_name": "Admin", "role": UserRole.ADMIN, "phone": "+1234567903"},
            {"username": "admin5", "email": "admin5@fitness.com", "first_name": "Chief", "last_name": "Admin", "role": UserRole.ADMIN, "phone": "+1234567904"},
        ]
        
        users = []
        for user_data in users_data:
            user = User(
                **user_data,
                password_hash=hash_password("password123")  # Default password for all users
            )
            users.append(user)
            db.add(user)
        
        db.commit()
        print(f"✅ Created {len(users)} users")
        
        # Get trainer IDs for programs
        trainers = [user for user in users if user.role == UserRole.TRAINER]
        
        # Create Programs (3 programs)
        programs_data = [
            {
                "name": "Beginner Fitness Fundamentals",
                "description": "A comprehensive 8-week program designed for fitness beginners. Learn proper form, build basic strength, and establish healthy exercise habits.",
                "difficulty": ProgramDifficulty.BEGINNER,
                "duration_weeks": 8,
                "trainer_id": trainers[0].id,
                "max_participants": 15,
                "price": 199.99
            },
            {
                "name": "Intermediate Strength Training",
                "description": "12-week intermediate program focusing on compound movements, progressive overload, and strength building for experienced exercisers.",
                "difficulty": ProgramDifficulty.INTERMEDIATE,
                "duration_weeks": 12,
                "trainer_id": trainers[1].id,
                "max_participants": 12,
                "price": 299.99
            },
            {
                "name": "Advanced Athletic Performance",
                "description": "Elite 16-week program for advanced athletes focusing on power, agility, and sport-specific conditioning.",
                "difficulty": ProgramDifficulty.ADVANCED,
                "duration_weeks": 16,
                "trainer_id": trainers[2].id,
                "max_participants": 8,
                "price": 499.99
            }
        ]
        
        programs = []
        for program_data in programs_data:
            program = Program(**program_data)
            programs.append(program)
            db.add(program)
        
        db.commit()
        print(f"✅ Created {len(programs)} programs")
        
        # Create Enrollments (clients enrolled in programs)
        clients = [user for user in users if user.role == UserRole.CLIENT]
        
        enrollments_data = [
            # Client 1 enrolled in Beginner program
            {
                "user_id": clients[0].id,
                "program_id": programs[0].id,
                "start_date": datetime.now() - timedelta(days=30),
                "progress_percentage": 60.0,
                "notes": "Great progress, very motivated student"
            },
            # Client 2 enrolled in Intermediate program
            {
                "user_id": clients[1].id,
                "program_id": programs[1].id,
                "start_date": datetime.now() - timedelta(days=45),
                "progress_percentage": 75.0,
                "notes": "Excellent form, pushing hard in workouts"
            },
            # Client 3 enrolled in Beginner program
            {
                "user_id": clients[2].id,
                "program_id": programs[0].id,
                "start_date": datetime.now() - timedelta(days=15),
                "progress_percentage": 25.0,
                "notes": "Just started, learning proper techniques"
            },
            # Client 4 enrolled in Advanced program
            {
                "user_id": clients[3].id,
                "program_id": programs[2].id,
                "start_date": datetime.now() - timedelta(days=60),
                "progress_percentage": 85.0,
                "notes": "Elite athlete, exceptional performance"
            }
        ]
        
        enrollments = []
        for enrollment_data in enrollments_data:
            enrollment = Enrollment(**enrollment_data)
            enrollments.append(enrollment)
            db.add(enrollment)
        
        db.commit()
        print(f"✅ Created {len(enrollments)} enrollments")
        
        # Create Assessments (initial assessments for enrolled clients)
        assessments_data = [
            {
                "user_id": clients[0].id,
                "assessment_type": AssessmentType.INITIAL,
                "weight": 75.5,
                "height": 175.0,
                "body_fat_percentage": 18.5,
                "muscle_mass": 32.0,
                "cardio_endurance_score": 5,
                "strength_score": 4,
                "flexibility_score": 6,
                "fitness_goals": "Lose weight, build muscle, improve overall fitness",
                "trainer_notes": "Good baseline fitness, needs work on strength"
            },
            {
                "user_id": clients[1].id,
                "assessment_type": AssessmentType.INITIAL,
                "weight": 65.0,
                "height": 168.0,
                "body_fat_percentage": 22.0,
                "muscle_mass": 28.5,
                "cardio_endurance_score": 7,
                "strength_score": 6,
                "flexibility_score": 8,
                "fitness_goals": "Increase strength, improve body composition",
                "trainer_notes": "Good cardio base, focus on strength training"
            },
            {
                "user_id": clients[2].id,
                "assessment_type": AssessmentType.INITIAL,
                "weight": 82.0,
                "height": 180.0,
                "body_fat_percentage": 25.0,
                "muscle_mass": 35.0,
                "cardio_endurance_score": 3,
                "strength_score": 5,
                "flexibility_score": 4,
                "fitness_goals": "Improve cardiovascular health, lose body fat",
                "trainer_notes": "Needs significant cardio improvement"
            },
            {
                "user_id": clients[3].id,
                "assessment_type": AssessmentType.INITIAL,
                "weight": 70.0,
                "height": 172.0,
                "body_fat_percentage": 12.0,
                "muscle_mass": 38.0,
                "cardio_endurance_score": 9,
                "strength_score": 9,
                "flexibility_score": 7,
                "fitness_goals": "Peak athletic performance, competition preparation",
                "trainer_notes": "Elite fitness level, focus on sport-specific training"
            }
        ]
        
        assessments = []
        for assessment_data in assessments_data:
            assessment = Assessment(**assessment_data)
            assessments.append(assessment)
            db.add(assessment)
        
        db.commit()
        print(f"✅ Created {len(assessments)} assessments")
        
        print("\n🎉 Seed data created successfully!")
        print("="*50)
        print(f"📊 Database Statistics:")
        print(f"   • Users: {len(users)} (5 clients, 5 trainers, 5 admins)")
        print(f"   • Programs: {len(programs)}")
        print(f"   • Enrollments: {len(enrollments)}")
        print(f"   • Assessments: {len(assessments)}")
        print("="*50)
        print("🔑 Default login credentials:")
        print("   • Username: client1, trainer1, admin1, etc.")
        print("   • Password: password123")
        print("="*50)
        print("🚀 Next steps:")
        print("   1. Start server: uvicorn main:app --reload")
        print("   2. Test health: http://localhost:8000/health")
        print("   3. View stats: http://localhost:8000/stats")
        print("   4. API docs: http://localhost:8000/docs")
        
    except Exception as e:
        print(f"❌ Error creating seed data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_seed_data()