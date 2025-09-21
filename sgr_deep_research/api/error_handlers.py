"""Error handling middleware for SGR Deep Research API.

This module provides centralized error handling, logging, and response formatting
for API errors.
"""

import logging
import traceback
from typing import Dict, Any
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base class for API-specific errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "API_ERROR",
        status_code: int = 500,
        details: Dict[str, Any] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class JobNotFoundError(APIError):
    """Raised when a requested job is not found."""

    def __init__(self, job_id: str):
        super().__init__(
            message=f"Job with ID {job_id} not found",
            error_code="JOB_NOT_FOUND",
            status_code=404,
            details={"job_id": job_id}
        )


class QueueFullError(APIError):
    """Raised when the job queue is full."""

    def __init__(self, queue_size: int, max_size: int):
        super().__init__(
            message="Too many jobs in queue, please try again later",
            error_code="QUEUE_FULL",
            status_code=429,
            details={"queue_size": queue_size, "max_queue_size": max_size}
        )


class InvalidJobRequestError(APIError):
    """Raised when job request validation fails."""

    def __init__(self, field: str, constraint: str, value: Any = None):
        super().__init__(
            message=f"Invalid value for field '{field}': {constraint}",
            error_code="INVALID_REQUEST",
            status_code=400,
            details={"field": field, "constraint": constraint, "value": value}
        )


class JobExecutionError(APIError):
    """Raised when job execution fails."""

    def __init__(self, job_id: str, reason: str):
        super().__init__(
            message=f"Job execution failed: {reason}",
            error_code="JOB_EXECUTION_ERROR",
            status_code=500,
            details={"job_id": job_id, "reason": reason}
        )


def setup_error_handlers(app: FastAPI) -> None:
    """Setup error handlers for the FastAPI application."""

    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        """Handle custom API errors."""
        logger.error(
            f"API Error: {exc.error_code} - {exc.message}",
            extra={
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "details": exc.details,
                "path": request.url.path,
                "method": request.method
            }
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle FastAPI HTTP exceptions."""
        logger.warning(
            f"HTTP Exception: {exc.status_code} - {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method
            }
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP_ERROR",
                "message": exc.detail,
                "details": {},
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle Starlette HTTP exceptions."""
        logger.warning(
            f"Starlette Exception: {exc.status_code} - {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method
            }
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP_ERROR",
                "message": exc.detail,
                "details": {},
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        logger.warning(
            f"Validation Error: {exc.errors()}",
            extra={
                "errors": exc.errors(),
                "path": request.url.path,
                "method": request.method
            }
        )

        # Format validation errors
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"][1:])  # Skip 'body'
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"]
            })

        return JSONResponse(
            status_code=422,
            content={
                "error": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"validation_errors": errors},
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        # Log the full traceback
        logger.error(
            f"Unexpected error: {str(exc)}",
            extra={
                "exception_type": type(exc).__name__,
                "path": request.url.path,
                "method": request.method,
                "traceback": traceback.format_exc()
            }
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": {
                    "exception_type": type(exc).__name__,
                    "timestamp": datetime.utcnow().isoformat()
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        )


async def log_request_response(request: Request, call_next):
    """Middleware to log requests and responses."""
    start_time = datetime.utcnow()

    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "user_agent": request.headers.get("user-agent", ""),
            "request_id": id(request)
        }
    )

    try:
        response = await call_next(request)

        # Calculate processing time
        process_time = (datetime.utcnow() - start_time).total_seconds()

        # Log response
        logger.info(
            f"Response: {response.status_code} for {request.method} {request.url.path}",
            extra={
                "status_code": response.status_code,
                "process_time_seconds": process_time,
                "request_id": id(request)
            }
        )

        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)

        return response

    except Exception as e:
        process_time = (datetime.utcnow() - start_time).total_seconds()

        logger.error(
            f"Request failed: {request.method} {request.url.path} - {str(e)}",
            extra={
                "exception_type": type(e).__name__,
                "process_time_seconds": process_time,
                "request_id": id(request),
                "traceback": traceback.format_exc()
            }
        )
        raise


def add_cors_headers():
    """Add CORS headers to responses."""
    from fastapi.middleware.cors import CORSMiddleware

    def setup_cors(app: FastAPI):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure based on environment
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    return setup_cors


def setup_security_headers():
    """Add security headers to responses."""
    from fastapi.middleware.trustedhost import TrustedHostMiddleware

    def setup_security(app: FastAPI):
        # Add trusted host middleware
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"]  # Configure based on environment
        )

        @app.middleware("http")
        async def add_security_headers(request: Request, call_next):
            response = await call_next(request)

            # Add security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

            return response

    return setup_security