"""
Main FastAPI application entry point.

Initializes the FastAPI app, creates database tables,
and includes API routers.
"""

from fastapi import FastAPI
from .database import engine, Base
from .routers import auth, images, tags

# Create all database tables (if they don't exist)
# This will create tbl_user based on app/models.py
try:
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")
except Exception as e:
    print(f"Error creating database tables: {e}")
    # In a real app, we might retry or use Alembic migrations.
    # For this project, this is ok.

# Initialize the FastAPI app
app = FastAPI(
    title="Photo Management Website",
    description="B/S Design Course Project"
)

# Include the routers
app.include_router(auth.router)
app.include_router(images.router)
app.include_router(tags.router)

# Root endpoint for health check
@app.get("/")
def read_root():
    """
    Root endpoint for health checks.
    
    Returns:
        A welcome message indicating the API is running.
    """
    return {"message": "Welcome to the Photo Management API"}
