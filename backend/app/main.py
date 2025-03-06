from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import logger
from backend.app.routers import cvs, roles, users
from backend.app.services.storage.cosmos_db import CosmosDB

# Initialize the DB
db_service = CosmosDB()
db_service.bootstrap()

app = FastAPI()

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # The Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


# Include routers
app.include_router(cvs.router, prefix="/api/cvs")
app.include_router(roles.router, prefix="/api/roles")
app.include_router(users.router, prefix="/api/users")
