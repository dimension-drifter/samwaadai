from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import calls, tasks, websocket, auth
from app.database import init_db
from app.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(calls.router, prefix="/api/calls", tags=["Calls"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    print("🚀 Starting Call Tracker AI Backend...")
    init_db()
    print("✅ Database initialized")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "app_name": settings.APP_NAME
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )