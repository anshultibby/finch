from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import Config
from routes import chat_router, snaptrade_router, resources_router

app = FastAPI(
    title="Finch Portfolio Chatbot API",
    description="AI-powered portfolio assistant with SnapTrade brokerage integration",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router)
app.include_router(snaptrade_router)
app.include_router(resources_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Finch Portfolio Chatbot API", "status": "running"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    print(f"🐦 Finch API starting on {Config.API_HOST}:{Config.API_PORT}")
    print(f"📝 API Documentation: http://localhost:{Config.API_PORT}/docs")
    uvicorn.run(
        app, 
        host=Config.API_HOST, 
        port=Config.API_PORT,
        timeout_keep_alive=5,
        log_level="info"
    )

