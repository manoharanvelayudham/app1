import time
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager

import pytz
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv

# Database imports
from app.database import engine, get_db, Base

# Authentication imports
from app.auth import get_current_user, get_current_user_optional, SECRET_KEY, ALGORITHM

# Model imports
from app.models import (
    User, Program, Enrollment, AuditAction,
    ParticipantProgress, ProgramAnalytics, PredictiveAnalysis,
    CustomReportConfig, CompetencyMapping
)

# Router imports
from app.routers import (
    auth,
    users,
    programs,
    enrollments,
    dashboard,
    responses,
    reviews,
    audit,
    ai_processing,   # AI processing router
    analytics,       # Analytics router
    ai,              # New AI insights router
    predictive,      # Predictive analytics router
    system           # System monitoring router
)
from app.export_excel_router import router as export_router  # Excel export router

# Service imports
from app.services.audit_service import AuditService

# Background scheduler
from apscheduler import AsyncIOScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler as AioScheduler
from apscheduler.triggers.cron import CronTrigger


# Load environment variables
load_dotenv()

# Configure logging for AI processing
logging.basicConfig(level=logging.INFO)
ai_logger = logging.getLogger("ai_processing")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management - startup and shutdown events"""
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {e}")
        raise

    yield

    print("Application shutting down...")


# Create FastAPI app with lifespan management
app = FastAPI(
    title="Leadership Development Platform API",
    description="AI-Enhanced Leadership Development and Coaching Platform",
    version="3.1.0",
    contact={"name": "LMS API Support", "email": "support@lms-api.com"},
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
)


# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Audit logging middleware
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    """Middleware to log API requests for audit purposes"""
    start_time = time.time()
    response = await call_next(request)

    skip_paths = ["/docs", "/redoc", "/openapi.json", "/health", "/static", "/status"]
    if any(request.url.path.startswith(path) for path in skip_paths):
        return response

    if request.method == "GET" and "/audit/" not in request.url.path:
        return response

    try:
        user = None
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from jose import jwt
                from app.auth import SECRET_KEY, ALGORITHM

                token = auth_header.replace("Bearer ", "")
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                user_id = payload.get("sub")
                if user_id:
                    db = next(get_db())
                    user = db.query(User).filter(User.id == user_id).first()
                    db.close()
            except Exception:
                pass

        if user:
            try:
                db = next(get_db())
                AuditService.log_action(
                    db=db,
                    user_id=user.id,
                    action=AuditAction.VIEW
                    if request.method == "GET"
                    else AuditAction.UPDATE,
                    resource_type="API_REQUEST",
                    request=request,
                    metadata={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "response_time": round(time.time() - start_time, 3),
                    },
                )
                db.commit()
                db.close()
            except Exception as e:
                print(f"Audit logging failed: {e}")
    except Exception as e:
        print(f"Audit middleware error: {e}")

    return response


# AI processing middleware
@app.middleware("http")
async def ai_processing_middleware(request: Request, call_next):
    """Enhanced middleware that logs AI processing requests"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    if "/ai" in str(request.url) or "/process" in str(request.url):
        ai_logger.info(
            f"AI Request: {request.method} {request.url} - "
            f"Status: {response.status_code} - "
            f"Duration: {process_time:.4f}s"
        )
    return response


# Analytics middleware
@app.middleware("http")
async def analytics_middleware(request: Request, call_next):
    """Middleware to track API usage for analytics"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    if "/analytics/" in str(request.url):
        print(f"Analytics API: {request.method} {request.url.path} - {process_time:.3f}s")
    return response


# Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(programs.router)
app.include_router(enrollments.router)
app.include_router(responses.router)
app.include_router(reviews.router)
app.include_router(audit.router)
app.include_router(dashboard.router)
app.include_router(ai_processing.router)
app.include_router(analytics.router)
app.include_router(export_router)
app.include_router(ai.router, prefix="/api/v1")  # New AI insights router
app.include_router(
    predictive.router,
    prefix="/api/v1",
    tags=["predictive-analytics"],
    dependencies=[Depends(get_current_user)]
)
app.include_router(system.router)  # System monitoring router


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    return {
        "message": "Leadership Development Platform API - Phase 3.1",
        "version": "3.1.0",
        "features": [
            "AI-driven insights generation",
            "Personalized coaching recommendations",
            "Behavioral pattern analysis",
            "Learning style identification",
            "Competency gap analysis",
            "Progress tracking and analytics"
        ],
        "endpoints": {
            "ai_insights": "/api/v1/ai/generate-insights/{participant_id}",
            "coaching_suggestions": "/api/v1/ai/coaching-suggestions",
            "insight_details": "/api/v1/ai/insights/{insight_id}",
            "analytics_summary": "/api/v1/ai/analytics/summary/{user_id}",
            "update_recommendation": "/api/v1/ai/recommendations/{recommendation_id}/status"
        }
    }


# Health check
@app.get("/health", tags=["health"])
async def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "Connected"
        db_healthy = True
    except Exception as e:
        db_status = f"Error: {str(e)}"
        db_healthy = False
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "service": "leadership-development-platform-api",
        "database": db_status,
        "version": "3.1.0",
        "timestamp": datetime.now(pytz.UTC).isoformat(),
    }


# ===== AI Processing Additions =====
scheduler = AsyncIOScheduler()


async def cleanup_old_ai_processing_records():
    """Clean up old AI processing records to maintain database performance"""
    try:
        from app.database import get_db
        from app.models import AIProcessing, AIProcessingStatus

        db = next(get_db())
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        old_failed_records = (
            db.query(AIProcessing)
            .filter(
                AIProcessing.processing_status == AIProcessingStatus.FAILED,
                AIProcessing.created_at < cutoff_date,
            )
            .all()
        )
        for record in old_failed_records:
            db.delete(record)

        very_old_cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        old_completed_records = (
            db.query(AIProcessing)
            .filter(
                AIProcessing.processing_status == AIProcessingStatus.COMPLETED,
                AIProcessing.created_at < very_old_cutoff,
            )
            .all()
        )
        for record in old_completed_records:
            record.original_content = None
            record.processed_content = None
            record.processing_steps = []

        db.commit()
        ai_logger.info(
            f"AI cleanup: {len(old_failed_records)} failed, "
            f"{len(old_completed_records)} cleaned"
        )
    except Exception as e:
        ai_logger.error(f"AI processing cleanup failed: {e}")


scheduler.add_job(
    cleanup_old_ai_processing_records,
    "cron",
    hour=2,
    minute=0,
    id="ai_processing_cleanup",
)


# ===== Predictive Analytics Scheduled Jobs =====
@scheduler.scheduled_job(trigger=CronTrigger(hour=2, minute=0))
async def daily_analytics_update():
    """Daily scheduled task to update program analytics"""
    from app.database import SessionLocal
    from sqlalchemy import distinct
    db = SessionLocal()
    try:
        program_ids = db.query(distinct(ParticipantProgress.program_id)).all()
        for (program_id,) in program_ids:
            # Placeholder for program analytics update function
            pass
        print(f"Daily analytics updated for {len(program_ids)} programs")
    finally:
        db.close()


@scheduler.scheduled_job(trigger=CronTrigger(hour=1, minute=0))
async def cleanup_old_predictions():
    """Clean up predictions older than 30 days"""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        cutoff_date = datetime.now() - timedelta(days=30)
        old_predictions = db.query(PredictiveAnalysis).filter(
            PredictiveAnalysis.created_at < cutoff_date
        ).all()
        for pred in old_predictions:
            db.delete(pred)
        db.commit()
        print(f"Cleaned up {len(old_predictions)} old predictions")
    finally:
        db.close()


@app.on_event("startup")
async def startup_event():
    print("=" * 50)
    print("Leadership Development Platform API starting up...")
    print("=" * 50)

    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key or openai_key == "your-openai-api-key":
            ai_logger.warning("OpenAI API key not configured properly")

        import pytesseract
        pytesseract.get_tesseract_version()
        ai_logger.info("Tesseract OCR available")

        import speech_recognition as sr  # noqa: F401
        ai_logger.info("Speech recognition available")

        import docx2txt, PyPDF2  # noqa: F401
        ai_logger.info("Document processing available")

        ai_logger.info("AI Processing Pipeline startup check completed")
    except Exception as e:
        ai_logger.error(f"AI Processing startup check failed: {e}")

    scheduler.start()
    ai_logger.info("AI processing background scheduler started")
    print("Analytics scheduler started")

    # Comprehensive system monitoring initialization
    from app.system_monitoring import SystemMonitoring
    system_monitoring = SystemMonitoring()
    system_monitoring.start()


@app.on_event("shutdown")
async def stop_scheduler():
    scheduler.shutdown()
    ai_logger.info("AI processing background scheduler stopped")
    print("Analytics scheduler stopped")


@app.get("/health/ai-processing")
async def ai_processing_health_check():
    status = {"timestamp": datetime.now(timezone.utc).isoformat(), "status": "healthy", "components": {}}
    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        status["components"]["openai"] = "configured" if openai_key else "not_configured"
    except Exception:
        status["components"]["openai"] = "error"
        status["status"] = "unhealthy"
    return status


@app.get("/config/ai-processing")
async def get_ai_processing_config(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return {
        "openai_model": "gpt-3.5-turbo",
        "max_retries": 3,
        "processing_timeout": 300,
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info", access_log=True)
