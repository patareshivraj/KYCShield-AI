from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from backend.app.api.routes import upload, status
from backend.app.db.session import engine, Base
from backend.app.core.config import settings
from backend.app.core.exceptions import KYCShieldException
from backend.app.models.schemas import ErrorResponse
from backend.app.core.schema_validator import SchemaValidator

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

@app.exception_handler(KYCShieldException)
async def kycshield_exception_handler(request: Request, exc: KYCShieldException):
    error_data = {
        "schema_version": "1.0.0",
        "error_code": exc.error_code,
        "message": exc.message,
        "details": exc.details,
        "request_id": "req-id" # Dummy for Phase 2
    }
    validated = SchemaValidator.validate_response("error", error_data)
    
    status_code = 400
    if exc.error_code == "UNSUPPORTED_FORMAT":
        status_code = 422
    elif exc.error_code == "JOB_NOT_FOUND":
        status_code = 404
        
    return JSONResponse(status_code=status_code, content=validated)

app.include_router(upload.router, prefix=settings.API_V1_STR + "/applicants", tags=["applicants"])
app.include_router(status.router, prefix=settings.API_V1_STR + "/jobs", tags=["jobs"])
