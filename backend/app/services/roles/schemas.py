from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from backend.app.services.llm.types import (
    EmploymentType,
    Level,
    Location,
    RoleMode,
)


class RoleListingRunStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING = "pending"


class RoleListing(BaseModel):
    """Role listing model for storing job listing data in Cosmos DB"""

    # Cosmos DB required fields
    id: str = Field(default_factory=lambda: str(uuid4()))
    partition_key: str = Field(default_factory=lambda: "role_listing")
    type: str = Field(default_factory=lambda: "role_listing")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    benefits: list[str] = Field(default_factory=list)
    creator_id: str
    description: Optional[str] = None
    embeddings: list[float] = Field(default_factory=list)
    employment_type: Optional[EmploymentType] = None
    industry: Optional[str] = None
    is_active: bool = Field(default=True)
    job_id: Optional[str] = None
    level: Optional[Level] = None
    location: Location = Field(default_factory=Location)
    organization_name: Optional[str] = None
    preferred_qualifications: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    role_mode: Optional[RoleMode] = None
    salary: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None


class RoleProfileRun(BaseModel):
    """
    RoleProfileRun model for storing job listing data in Cosmos DB.

    Similar to CVProfileRun, this is a temporary entity created when a recruiter
    submits a job listing. It stores the extracted and processed data until it
    is approved and merged into the RoleListing model.
    """

    # Cosmos DB required fields
    id: str = Field(default_factory=lambda: str(uuid4()))
    partition_key: str = Field(default_factory=lambda: "role_profile_run")
    type: str = Field(default_factory=lambda: "role_profile_run")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    benefits: list[str] = Field(default_factory=list)
    creator_id: str
    description: Optional[str] = None
    employment_type: Optional[EmploymentType] = None
    file_path: str
    industry: Optional[str] = None
    job_id: Optional[str] = None
    level: Optional[Level] = None
    location: Location = Field(default_factory=Location)
    organization_name: Optional[str] = None
    preferred_qualifications: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    role_mode: Optional[RoleMode] = None
    salary: Optional[str] = None
    status: RoleListingRunStatus = Field(default=RoleListingRunStatus.PENDING)
    status_comment: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
