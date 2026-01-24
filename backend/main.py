from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time

from config import Config
from routes import chat_router, snaptrade_router, resources_router, chat_files_router, api_keys_router, strategies_router, credits_router
from routes.analytics import router as analytics_router
from utils.logger import configure_logging, get_logger
from utils.tracing import setup_tracing

# Configure logging for the entire application
configure_logging()
logger = get_logger(__name__)

# Import tool definitions to register all tools
from modules.tools import definitions  # noqa: F401 - imported for side effects (tool registration)

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
    from database import get_pool_status
    from fastapi.responses import JSONResponse
    import traceback
    
    start_time = time.time()
    
    try:
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
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        
        # Check if it's a connection pool timeout error
        error_str = str(e)
        if "QueuePool limit" in error_str or "connection timed out" in error_str:
            pool_status = get_pool_status()
            logger.error(
                f"⚠️  DATABASE POOL EXHAUSTED - {request.method} {request.url.path} ({duration:.0f}ms) - "
                f"Pool: {pool_status['checked_out']}/{pool_status['total']} in use, "
                f"{pool_status['overflow']} overflow active"
            )
            logger.error(f"Full error: {error_str}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Database connection pool exhausted. Please try again in a moment.",
                    "error_type": "connection_pool_timeout"
                }
            )
        
        # Re-raise other exceptions to be handled by FastAPI
        raise

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
app.include_router(analytics_router)
app.include_router(chat_files_router)
app.include_router(api_keys_router)
app.include_router(strategies_router)
app.include_router(credits_router)


import asyncio

# Background task for monitoring connection pool
_pool_monitor_task = None

async def monitor_connection_pool():
    """Background task to monitor connection pool usage"""
    from database import get_pool_status
    
    while True:
        try:
            await asyncio.sleep(60)  # Check every minute
            pool_status = get_pool_status()
            usage_percent = (pool_status['checked_out'] / pool_status['total']) * 100 if pool_status['total'] > 0 else 0
            
            # Log warning if pool usage is high
            if usage_percent > 80:
                logger.warning(
                    f"⚠️  High DB pool usage: {pool_status['checked_out']}/{pool_status['total']} "
                    f"({usage_percent:.1f}% - {pool_status['overflow']} overflow active)"
                )
            elif usage_percent > 60:
                logger.info(
                    f"📊 DB pool usage: {pool_status['checked_out']}/{pool_status['total']} "
                    f"({usage_percent:.1f}%)"
                )
        except Exception as e:
            logger.error(f"Error in pool monitor: {e}")


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global _pool_monitor_task
    from services.storage import storage_service
    from modules.strategies.scheduler import start_scheduler
    from database import get_pool_status
    
    # Log database connection pool configuration
    pool_status = get_pool_status()
    logger.info(f"🔗 Database connection pool: size={pool_status['size']}, overflow={pool_status['overflow']}, total_max={pool_status['total']}, timeout={pool_status['timeout']}s")
    
    # Start background pool monitoring
    _pool_monitor_task = asyncio.create_task(monitor_connection_pool())
    logger.info("📊 Started connection pool monitoring")
    
    # Initialize Supabase Storage bucket (if configured)
    if storage_service.is_available():
        logger.info("Initializing Supabase Storage...")
        if storage_service.ensure_bucket_exists():
            logger.info(f"✅ Supabase Storage bucket '{storage_service.bucket_name}' ready")
        else:
            logger.warning("⚠️  Failed to initialize Supabase Storage bucket")
    else:
        logger.info("ℹ️  Supabase Storage not configured - images will be stored in database")
    
    # Start strategy scheduler
    logger.info("Starting strategy scheduler...")
    await start_scheduler()
    logger.info("✅ Strategy scheduler started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global _pool_monitor_task
    from modules.strategies.scheduler import stop_scheduler
    
    # Stop pool monitor
    if _pool_monitor_task:
        _pool_monitor_task.cancel()
        try:
            await _pool_monitor_task
        except asyncio.CancelledError:
            pass
        logger.info("📊 Stopped connection pool monitoring")
    
    logger.info("Stopping strategy scheduler...")
    await stop_scheduler()
    logger.info("✅ Strategy scheduler stopped")


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Finch Portfolio Chatbot API", "status": "running"}


@app.get("/health")
async def health():
    """Health check endpoint with database pool status"""
    from database import get_pool_status
    
    pool_status = get_pool_status()
    
    # Check if pool is exhausted (warning threshold at 80% usage)
    usage_percent = (pool_status['checked_out'] / pool_status['total']) * 100 if pool_status['total'] > 0 else 0
    
    return {
        "status": "healthy",
        "database_pool": {
            "checked_out": pool_status['checked_out'],
            "available": pool_status['checkedin'],
            "total": pool_status['total'],
            "usage_percent": round(usage_percent, 1),
            "overflow_active": pool_status['overflow']
        }
    }


if __name__ == "__main__":
    import uvicorn
    logger.info(f"🐦 Finch API starting on {Config.API_HOST}:{Config.API_PORT}")
    logger.info(f"📝 API Documentation: http://localhost:{Config.API_PORT}/docs")
    uvicorn.run(
        app, 
        host=Config.API_HOST, 
        port=Config.API_PORT,
        timeout_keep_alive=120,  # 2 minutes - long enough for SSE streams
        log_level="info"
    )

