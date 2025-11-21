from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time

from config import Config
from routes import chat_router, snaptrade_router, resources_router
from utils.logger import configure_logging, get_logger
from utils.tracing import setup_tracing

# Configure logging for the entire application
configure_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="Finch Portfolio Chatbot API",
    description="AI-powered portfolio assistant with SnapTrade brokerage integration",
    version="2.0.0"
)

# Setup OpenTelemetry tracing (auto-instruments FastAPI, DB, HTTP)
setup_tracing(app)

# Add simple timing middleware for request duration logging
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = (time.time() - start_time) * 1000
    
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} ({duration:.0f}ms)",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round(duration, 2),
            "type": "http_request"
        }
    )
    return response

logger.info("Finch API initialized")

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
    logger.info(f"🐦 Finch API starting on {Config.API_HOST}:{Config.API_PORT}")
    logger.info(f"📝 API Documentation: http://localhost:{Config.API_PORT}/docs")
    uvicorn.run(
        app, 
        host=Config.API_HOST, 
        port=Config.API_PORT,
        timeout_keep_alive=5,
        log_level="info"
    )

