import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.mongo import init_mongo_indexes, get_mongo_db

from app.api import (
    auth, users, subjects, cos, syllabus, rules_config,
    papers, questions, previous_papers, scrutiny, reports,
    history, moderator, dashboard, examinations
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "question_papers"), exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "previous_papers"), exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "syllabus_docs"), exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "reports"), exist_ok=True)

    try:
        get_mongo_db()
        init_mongo_indexes()
        logger.info(f"Connected to MongoDB database '{settings.MONGODB_DB_NAME}' successfully.")
    except Exception:
        logger.error("MongoDB startup check failed; verify service connectivity and configuration.")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-Based Intelligent Question Paper Scrutiny Decision Support System for Autonomous Engineering Colleges",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(subjects.router, prefix=settings.API_V1_STR)
app.include_router(examinations.router, prefix=settings.API_V1_STR)
app.include_router(cos.router, prefix=settings.API_V1_STR)
app.include_router(syllabus.router, prefix=settings.API_V1_STR)
app.include_router(rules_config.router, prefix=settings.API_V1_STR)
app.include_router(papers.router, prefix=settings.API_V1_STR)
app.include_router(questions.router, prefix=settings.API_V1_STR)
app.include_router(previous_papers.router, prefix=settings.API_V1_STR)
app.include_router(scrutiny.router, prefix=settings.API_V1_STR)
app.include_router(reports.router, prefix=settings.API_V1_STR)
app.include_router(history.router, prefix=settings.API_V1_STR)
app.include_router(moderator.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    try:
        get_mongo_db().command("ping")
        database_status = "connected"
        status = "online"
    except Exception:
        database_status = "unavailable"
        status = "degraded"
    return {
        "status": status,
        "app": settings.PROJECT_NAME,
        "database": database_status,
        "ai_provider": settings.AI_PROVIDER,
        "docs": "/docs"
    }
