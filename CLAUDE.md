# CLAUDE.md - Backend

This file provides guidance to Claude Code (claude.ai/code) when working with the FastAPI backend.

## Backend Architecture

**Tech Stack**: FastAPI 0.115+ (Python 3.11+), PostgreSQL 14, SQLAlchemy (async), Redis, Pydantic-AI

**Key Design**: Clean architecture with separation of concerns - API layer → Services layer → Models

## Directory Structure

```
backend/app/
├── api/v1/                 # API endpoints (FastAPI routers)
│   ├── auth.py            # FastAPI Users authentication
│   ├── projects.py        # Project CRUD with pagination
│   ├── proposals.py       # AI proposal generation
│   ├── project_data.py    # Dynamic technical data management
│   ├── files.py           # Document upload/download
│   └── health.py          # Health check endpoint
├── core/
│   ├── config.py          # Pydantic Settings (env vars)
│   ├── database.py        # SQLAlchemy async session
│   ├── auth_*.py          # JWT + FastAPI Users setup
│   └── startup_checks.py  # Configuration validation
├── models/                 # SQLAlchemy ORM models
│   ├── base.py            # BaseModel with UUID + timestamps
│   ├── user.py            # User authentication
│   ├── project.py         # Project with JSONB project_data
│   ├── proposal.py        # Proposal versions
│   ├── project_input.py   # FlexibleWaterProjectData (AI input schema)
│   ├── proposal_output.py # ProposalOutput (AI result schema)
│   ├── file.py            # Document metadata
│   └── timeline.py        # Activity history
├── schemas/               # Pydantic request/response models
│   ├── project.py         # ProjectCreate/Update/Detail/Summary
│   ├── proposal.py        # ProposalGenerationRequest/Response
│   ├── project_data.py    # Technical section schemas
│   └── common.py          # PaginatedResponse, ErrorResponse
├── services/              # Business logic layer
│   ├── proposal_service.py    # Proposal workflow management
│   ├── project_data_service.py # Technical data operations
│   ├── cache_service.py       # Redis wrapper (async)
│   ├── storage_service.py     # Storage abstraction (local/S3)
│   └── s3_service.py          # AWS S3 integration
├── agents/                # AI agents and tools
│   ├── proposal_agent.py      # Pydantic-AI agent
│   └── tools/
│       ├── intelligent_case_filter.py    # Query similar projects
│       └── engineering_calculations.py   # Sizing formulas
├── visualization/         # PDF and chart generation
│   ├── pdf_generator.py   # WeasyPrint HTML→PDF
│   └── modern_charts.py   # Cost breakdowns
└── middleware/            # Custom middleware (rate limiting)
```

## Development Commands

### Local Development (Docker - Recommended)

```bash
# Start all services (FastAPI + PostgreSQL + Redis)
docker-compose up

# Rebuild after dependency changes
docker-compose up --build

# Run migrations
docker-compose exec app alembic upgrade head

# Access container shell
docker-compose exec app bash

# View logs
docker-compose logs app -f

# Stop services
docker-compose down
```

### Database Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "description of changes"

# Review generated migration in alembic/versions/

# Apply migration
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# View migration history
alembic history

# Check current version
alembic current
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_projects.py

# Run specific test function
pytest tests/test_projects.py::test_create_project

# Run with verbose output
pytest -v

```

### Code Quality

```bash
# Format code (Black)
black app/

# Lint (Ruff)
ruff check app/

# Type checking (MyPy)
mypy app/

# Run all checks
black app/ && ruff check app/ && mypy app/ && pytest
```

## Core Architecture Patterns

### 1. Dependency Injection with FastAPI

```python
# app/api/dependencies.py
from typing import Annotated
from fastapi import Depends, Query

# Type aliases for DRY code
PageNumber = Annotated[int, Query(ge=1, description="Page number")]
PageSize = Annotated[int, Query(ge=1, le=100, description="Items per page")]

# Use in endpoints
@router.get("/projects")
async def list_projects(
    page: PageNumber = 1,
    page_size: PageSize = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Implementation
```

### 2. Async Database Operations

```python
# Always use async/await for database operations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def get_project(db: AsyncSession, project_id: UUID) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    return result.scalar_one_or_none()
```

### 3. Service Layer Pattern

```python
# API layer (thin - just routing)
@router.post("/projects")
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db)
):
    return await ProjectService.create_project(db, data)

# Service layer (thick - business logic)
class ProjectService:
    @staticmethod
    async def create_project(db: AsyncSession, data: ProjectCreate):
        # Validation
        # Business logic
        # Database operations
        # Return result
```

### 4. Structured Logging

```python
import structlog

logger = structlog.get_logger()

# In development: colored output
# In production: JSON format for log aggregation

logger.info(
    "project_created",
    project_id=str(project.id),
    user_id=str(user.id),
    sector=project.sector
)
```

### 5. Error Handling

```python
from fastapi import HTTPException, status

# Use specific HTTP status codes
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Project not found"
)

# Validation errors are automatically handled by Pydantic
# General exceptions are caught by middleware
```

## Working with the AI System

### Proposal Generation Flow

```
POST /api/v1/ai/proposals/generate
    ↓
proposal_service.py: Start background job
    ↓
proposal_agent.py: Pydantic-AI agent runs
    1. Load project.project_data → FlexibleWaterProjectData
    2. Call tools (deterministic calculations)
    3. Generate ProposalOutput (validated by Pydantic)
    ↓
Save to database + generate PDF
    ↓
Return job completion
```

### Adding a New AI Tool

```python
# backend/app/agents/tools/your_new_tool.py
def calculate_something(param: float) -> float:
    """
    Deterministic calculation using engineering standards.
    Must be reproducible and cite sources.
    """
    # Use published formulas (Metcalf & Eddy, WEF, etc.)
    return param * ENGINEERING_CONSTANT

# backend/app/agents/proposal_agent.py
from app.agents.tools.your_new_tool import calculate_something

@agent.tool
def your_tool(ctx: RunContext, param: float) -> float:
    """Tool description for the AI agent"""
    return calculate_something(param)
```

### Modifying AI Input/Output Schemas

```python
# Input schema: app/models/project_input.py
class FlexibleWaterProjectData(BaseModel):
    """Schema for AI agent input"""
    # Add new field with validation
    new_field: Optional[str] = Field(None, description="...")

# Output schema: app/models/proposal_output.py
class ProposalOutput(BaseModel):
    """Schema for AI agent output"""
    # Add new field
    new_result: Optional[float] = Field(None, description="...")
```

## Working with Dynamic Data (JSONB)

### Understanding project_data

The `project.project_data` column is a JSONB field that stores flexible technical data:

```python
# Database schema
project_data = Column(JSONB, default={}, nullable=False)

# Structure
{
    "technical_sections": [
        {
            "id": "section-uuid",
            "name": "Water Quality",
            "fields": [
                {
                    "id": "field-uuid",
                    "name": "BOD",
                    "value": 250,
                    "unit": "mg/L",
                    "field_type": "number"
                }
            ]
        }
    ]
}
```

### Querying JSONB

```python
from sqlalchemy import func

# Query by JSONB field
projects = await db.execute(
    select(Project).where(
        func.jsonb_extract_path_text(
            Project.project_data,
            'technical_sections',
            '0',
            'name'
        ) == 'Water Quality'
    )
)

# Update JSONB field
stmt = update(Project).where(Project.id == project_id).values(
    project_data=func.jsonb_set(
        Project.project_data,
        '{technical_sections,0,name}',
        '"Updated Name"'
    )
)
```

## API Endpoint Patterns

### Standard CRUD Endpoints

```python
# List (with pagination, filtering, sorting)
@router.get("/projects", response_model=PaginatedResponse[ProjectSummary])
async def list_projects(
    page: PageNumber = 1,
    page_size: PageSize = 10,
    status: Optional[str] = None,
    sector: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc"
)

# Get single
@router.get("/projects/{project_id}", response_model=ProjectDetail)
async def get_project(project_id: UUID)

# Create
@router.post("/projects", response_model=ProjectDetail, status_code=201)
async def create_project(data: ProjectCreate)

# Update (partial)
@router.patch("/projects/{project_id}", response_model=ProjectDetail)
async def update_project(project_id: UUID, data: ProjectUpdate)

# Delete
@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: UUID)
```

### Adding a New Endpoint

1. **Create router** in `app/api/v1/your_feature.py`
2. **Add schemas** in `app/schemas/your_feature.py`
3. **Create service** in `app/services/your_feature_service.py`
4. **Update models** if needed in `app/models/`
5. **Register router** in `app/api/v1/__init__.py`
6. **Write tests** in `tests/test_your_feature.py`

Example:

```python
# app/api/v1/your_feature.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.schemas.your_feature import YourFeatureCreate, YourFeatureResponse
from app.services.your_feature_service import YourFeatureService

router = APIRouter(prefix="/your-feature", tags=["your-feature"])

@router.post("", response_model=YourFeatureResponse)
async def create_feature(
    data: YourFeatureCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await YourFeatureService.create(db, data, current_user)
```

## Database Optimization

### Avoiding N+1 Queries

```python
from sqlalchemy.orm import selectinload

# Bad: N+1 query
projects = await db.execute(select(Project))
for project in projects:
    print(project.user.email)  # Triggers a query per project

# Good: Eager loading
projects = await db.execute(
    select(Project).options(selectinload(Project.user))
)
for project in projects:
    print(project.user.email)  # No additional queries
```

### Using raiseload()

```python
from sqlalchemy.orm import raiseload

# Prevent accidental lazy loading
result = await db.execute(
    select(Project).options(raiseload("*"))
)
# Accessing unloaded relationships will raise an error
```

### Indexing

```python
# Add indexes to frequently queried columns
class Project(BaseModel):
    __tablename__ = "projects"

    user_id = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, index=True)
```

## Caching with Redis

```python
from app.services.cache_service import CacheService

# Set cache
await CacheService.set(
    key="project:stats:user:123",
    value={"total": 10, "active": 5},
    ttl=300  # 5 minutes
)

# Get cache
stats = await CacheService.get("project:stats:user:123")

# Delete cache
await CacheService.delete("project:stats:user:123")

# Pattern-based deletion
await CacheService.delete_pattern("project:stats:user:*")
```

## File Storage

### Using Storage Service

```python
from app.services.storage_service import StorageService

# Upload file
file_url = await StorageService.upload_file(
    file=file_content,
    filename="proposal.pdf",
    project_id=project_id,
    content_type="application/pdf"
)

# Download file
file_content = await StorageService.download_file(file_url)

# Delete file
await StorageService.delete_file(file_url)
```

### Storage Configuration

```bash
# Local storage (development)
USE_LOCAL_STORAGE=true
LOCAL_STORAGE_PATH=./storage

# S3 storage (production)
USE_LOCAL_STORAGE=false
AWS_S3_BUCKET=h2o-allegiant-production
AWS_REGION=us-west-2
```
