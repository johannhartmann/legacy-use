"""
FastAPI server implementation for the API Gateway.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from server.computer_use import APIProvider
from server.database import db
from server.routes import api_router, job_router, target_router
from server.routes.diagnostics import diagnostics_router
from server.routes.sessions import session_router, websocket_router
from server.routes.settings import settings_router
from server.routes.vnc import vnc_router
from server.utils.auth import get_api_key
from server.utils.job_execution import job_queue_initializer
from server.utils.session_monitor import start_session_monitor

from .settings import settings

# Set up logging
debug_mode = os.getenv('LEGACY_USE_DEBUG', '0') == '1'
logging.basicConfig(
    level=logging.DEBUG if debug_mode else logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



# Handle provider-specific environment variables
if settings.API_PROVIDER == APIProvider.BEDROCK:
    if not all(
        [
            settings.AWS_ACCESS_KEY_ID,
            settings.AWS_SECRET_ACCESS_KEY,
            settings.AWS_REGION,
        ]
    ):
        logger.warning('Using Bedrock provider but AWS credentials are missing.')
    else:
        # Export AWS credentials to environment if using Bedrock
        # Ensure these are set in environment for the AnthropicBedrock client
        os.environ['AWS_ACCESS_KEY_ID'] = settings.AWS_ACCESS_KEY_ID
        os.environ['AWS_SECRET_ACCESS_KEY'] = settings.AWS_SECRET_ACCESS_KEY
        os.environ['AWS_REGION'] = settings.AWS_REGION
        logger.info(
            f'AWS credentials loaded for Bedrock provider (region: {settings.AWS_REGION})'
        )
elif settings.API_PROVIDER == APIProvider.VERTEX:
    # Get Vertex-specific environment variables

    if not all([settings.VERTEX_REGION, settings.VERTEX_PROJECT_ID]):
        logger.warning(
            'Using Vertex provider but required environment variables are missing.'
        )
    else:
        # Ensure these are set in environment for the AnthropicVertex client
        os.environ['CLOUD_ML_REGION'] = settings.VERTEX_REGION
        os.environ['ANTHROPIC_VERTEX_PROJECT_ID'] = settings.VERTEX_PROJECT_ID
        logger.info(
            f'Vertex credentials loaded (region: {settings.VERTEX_REGION}, project: {settings.VERTEX_PROJECT_ID})'
        )


app = FastAPI(
    title='AI API Gateway',
    description='API Gateway for AI-powered endpoints',
    version='1.0.0',
    redoc_url='/redoc' if settings.SHOW_DOCS else None,
    # Disable automatic redirect from /path to /path/
    redirect_slashes=False,
)


@app.get('/health')
async def health_check():
    """Health check endpoint for container readiness/liveness probes."""
    try:
        # Check database connection
        db.list_targets()
        return {'status': 'healthy', 'database': 'connected'}
    except Exception as e:
        logger.error(f'Health check failed: {e}')
        raise HTTPException(status_code=500, detail=f'Database check failed: {str(e)}')


@app.get('/api/init-status')
async def get_init_status():
    """Get initialization status to determine if setup is needed.
    
    This endpoint is public and helps the frontend determine:
    1. If API key authentication is required
    2. If the system is already configured with AI provider credentials
    3. If a default API key should be used
    """
    # Check if API key is configured
    api_key_configured = bool(settings.API_KEY) if hasattr(settings, 'API_KEY') else False
    using_default_api_key = not api_key_configured
    
    # Check if any AI provider is configured
    has_anthropic = bool(settings.ANTHROPIC_API_KEY)
    has_bedrock = all([
        settings.AWS_ACCESS_KEY_ID,
        settings.AWS_SECRET_ACCESS_KEY,
        settings.AWS_REGION,
    ]) if settings.API_PROVIDER == 'bedrock' else False
    has_vertex = all([
        settings.VERTEX_REGION,
        settings.VERTEX_PROJECT_ID,
    ]) if settings.API_PROVIDER == 'vertex' else False
    
    # System is configured if current provider has valid credentials
    is_configured = False
    if settings.API_PROVIDER == 'anthropic':
        is_configured = has_anthropic
    elif settings.API_PROVIDER == 'bedrock':
        is_configured = has_bedrock
    elif settings.API_PROVIDER == 'vertex':
        is_configured = has_vertex
    
    response = {
        'requires_api_key': not using_default_api_key,
        'is_configured': is_configured,
        'current_provider': settings.API_PROVIDER,
    }
    
    # If using secure API key from environment, provide it to frontend
    if not using_default_api_key and settings.API_KEY:
        response['default_api_key'] = settings.API_KEY
    
    return response




@app.middleware('http')
async def auth_middleware(request: Request, call_next):
    import re

    # Allow CORS preflight requests (OPTIONS) to pass through without authentication
    if request.method == 'OPTIONS':
        return await call_next(request)

    # auth whitelist (regex patterns)
    whitelist_patterns = [
        r'^/health$',  # Health check endpoint
        r'^/api/init-status$',  # Initialization status endpoint
        r'^/favicon\.ico$',  # Favicon requests
        r'^/robots\.txt$',  # Robots.txt requests
        r'^/sitemap\.xml$',  # Sitemap requests
        r'^/vnc/.+/websockify$',  # VNC WebSocket connections (auth handled in endpoint)
    ]

    if settings.SHOW_DOCS:
        whitelist_patterns.append(r'^/docs(/.*)?$')  # Swagger UI
        whitelist_patterns.append(r'^/redoc(/.*)?$')  # ReDoc
        whitelist_patterns.append(r'^/openapi.json$')  # OpenAPI spec needed for docs

    # Check if request path matches any whitelist pattern
    # Normalize path by removing double slashes
    normalized_path = re.sub(r'/+', '/', request.url.path)
    for pattern in whitelist_patterns:
        if re.match(pattern, normalized_path):
            return await call_next(request)

    try:
        api_key = await get_api_key(request)
        if api_key == settings.API_KEY:
            return await call_next(request)
        else:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={'detail': 'Invalid API Key'},
            )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={'detail': e.detail},
        )


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        '*'
    ],  # Allows all origins; TODO: restrict to specific origins -> need to think of a way to handle "external" requests
    allow_credentials=True,
    allow_methods=[
        'GET',
        'POST',
        'PUT',
        'DELETE',
        'PATCH',
        'OPTIONS',
    ],  # Restrict to common HTTP methods
    allow_headers=[
        'Content-Type',
        'Authorization',
        'X-API-Key',
        'X-Distinct-Id',  # For telemetry/analytics
        'Accept',
        'Accept-Language',
        'Content-Language',
        'Cache-Control',
        'Origin',
        'X-Requested-With',
    ],  # Restrict to necessary headers
    expose_headers=[
        'Content-Type',
        'X-Total-Count',
    ],  # Only expose necessary response headers
)

# Add API key security scheme to OpenAPI
app.openapi_tags = [
    {'name': 'API Definitions', 'description': 'API definition endpoints'},
]

app.openapi_components = {
    'securitySchemes': {
        'ApiKeyAuth': {
            'type': 'apiKey',
            'in': 'header',
            'name': settings.API_KEY_NAME,
            'description': "API key authentication. Enter your API key in the format: 'your_api_key'",
        }
    }
}

app.openapi_security = [{'ApiKeyAuth': []}]

# Include API router (already has /api prefix)
app.include_router(api_router)

# Include core routers under /api prefix
app.include_router(target_router, prefix='/api')
app.include_router(
    session_router,
    prefix='/api',
    include_in_schema=not settings.HIDE_INTERNAL_API_ENDPOINTS_IN_DOC,
)
app.include_router(job_router, prefix='/api')

# Include WebSocket router under /api prefix
app.include_router(websocket_router, prefix='/api')

# Include diagnostics router under /api prefix
app.include_router(
    diagnostics_router,
    prefix='/api',
    include_in_schema=not settings.HIDE_INTERNAL_API_ENDPOINTS_IN_DOC,
)

# Include settings router under /api prefix
app.include_router(settings_router, prefix='/api')

# Include VNC router (already has /vnc prefix, not under /api)
app.include_router(vnc_router)



# Scheduled task to prune old logs
async def prune_old_logs():
    """Prune logs older than 7 days."""
    while True:
        try:
            # Sleep until next pruning time (once a day at midnight)
            now = datetime.now()
            next_run = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            sleep_seconds = (next_run - now).total_seconds()
            logger.info(
                f'Next log pruning scheduled in {sleep_seconds / 3600:.1f} hours'
            )
            await asyncio.sleep(sleep_seconds)

            # Prune logs
            days_to_keep = settings.LOG_RETENTION_DAYS
            deleted_count = db.prune_old_logs(days=days_to_keep)
            logger.info(f'Pruned {deleted_count} logs older than {days_to_keep} days')
        except Exception as e:
            logger.error(f'Error pruning logs: {str(e)}')
            await asyncio.sleep(3600)  # Sleep for an hour and try again


@app.on_event('startup')
async def startup_event():
    """Start background tasks on server startup."""
    # Start background tasks
    asyncio.create_task(prune_old_logs())
    logger.info('Started background task for pruning old logs')

    # Start session monitor
    start_session_monitor()
    logger.info('Started session state monitor')

    # No need to load API definitions on startup anymore
    # They will be loaded on demand when needed

    # Initialize job queue from database
    await job_queue_initializer()
    logger.info('Initialized job queue from database')


if __name__ == '__main__':
    import uvicorn

    host = settings.FASTAPI_SERVER_HOST
    port = settings.FASTAPI_SERVER_PORT
    uvicorn.run('server.server:app', host=host, port=port, reload=True)
