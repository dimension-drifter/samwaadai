import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"🚀 Starting {settings.APP_NAME}")
    print(f"📍 Server: http://{settings.HOST}:{settings.PORT}")
    print(f"📚 Docs: http://{settings.HOST}:{settings.PORT}/docs")
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )