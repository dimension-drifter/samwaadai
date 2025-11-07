from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.api import websocket, calls, tasks, auth

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    debug=settings.DEBUG
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database and services"""
    print("🚀 Starting Call Tracker AI Backend...")
    init_db()
    print("✅ Database initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("👋 Shutting down Call Tracker AI Backend...")

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "Call Tracker AI Backend",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Include routers
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
app.include_router(calls.router, prefix="/api/calls", tags=["Calls"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )