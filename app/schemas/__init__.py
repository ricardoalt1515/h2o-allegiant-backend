"""Pydantic schemas for request/response validation."""

from app.schemas.common import PaginatedResponse, APIError, SuccessResponse
from app.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectSummary,
    ProjectDetail,
)
from app.schemas.proposal import (
    ProposalGenerationRequest,
    ProposalJobStatus,
    ProposalResponse,
)

__all__ = [
    # Common
    "PaginatedResponse",
    "APIError",
    "SuccessResponse",
    # User
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    # Project
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectSummary",
    "ProjectDetail",
    # Proposal
    "ProposalGenerationRequest",
    "ProposalJobStatus",
    "ProposalResponse",
]
