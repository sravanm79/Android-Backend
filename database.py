import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ✅ LOAD ENVIRONMENT VARIABLES
load_dotenv()

# SQLite database URL (from environment variable or default)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./teacher_database.db")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False},  # Required for SQLite
    echo=False  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base for models
Base = declarative_base()


def get_db():
    """Dependency injection for FastAPI endpoints to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)




