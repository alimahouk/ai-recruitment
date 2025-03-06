import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field

from backend.app.services.llm.types import (
    Award,
    ContactDetails,
    Education,
    Employment,
    Level,
    Location,
)


class CVProfileRunStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING = "pending"


class UserRole(StrEnum):
    RECRUITER = "recruiter"
    JOB_SEEKER = "job_seeker"


class User(BaseModel):
    """User model for storing CV profile data in Cosmos DB"""

    # Cosmos DB required fields
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    partition_key: str = Field(default_factory=lambda: "user")
    type: str = Field(default_factory=lambda: "user")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    average_tenure: Optional[float] = None
    awards: list[Award] = Field(default_factory=list)
    contact_details: ContactDetails = Field(default_factory=ContactDetails)
    creativity_score: Optional[int] = None
    education_history: list[Education] = Field(default_factory=list)
    embeddings: list[float] = Field(default_factory=list)
    employment_history: list[Employment] = Field(default_factory=list)
    formatting_score: Optional[int] = None
    grammar_score: Optional[int] = None
    highlights: list[str] = Field(default_factory=list)
    hobbies: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    is_onboarded: bool = Field(default_factory=lambda: False)
    job_title: Optional[str] = None
    level: Optional[Level] = None
    location: Location = Field(default_factory=Location)
    location_preferences: list[Location] = Field(default_factory=list)
    name: Optional[str] = None
    nationality: Optional[str] = None
    profile_picture_url: Optional[str] = None
    role: Optional[UserRole] = None
    skills: list[str] = Field(default_factory=list)
    spoken_languages: list[str] = Field(default_factory=list)
    summary: Optional[str] = None
    urls: list[str] = Field(default_factory=list)
    years_experience: Optional[float] = None


class CVProfileRun(BaseModel):
    """
    CVProfile model for storing CV data in Cosmos DB.

    You might be wondering why this is a separate model from the User model.
    Well, a CVProfileRun is a temporary entity that is created when a user uploads their CV.
    It is used to extract the data from the CV and store it in the User model.
    Once the data is extracted, it is stored until the user approves it, then the CVProfileRun's
    fields are merged into the User model. We may then keep or delete the CVProfileRun.

    This ensures that CV profile updates are atomic and allows the user to reject any aspects
    of the CV profile if it is not accurate.
    """

    # Cosmos DB required fields
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )  # This will get set to the ID of the user it is associated with at insertion time.
    partition_key: str = Field(default_factory=lambda: "cv_profile")
    type: str = Field(default_factory=lambda: "cv_profile")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    average_tenure: Optional[float] = None
    awards: list[Award] = Field(default_factory=list)
    contact_details: ContactDetails = Field(default_factory=ContactDetails)
    creativity_score: Optional[int] = None
    education_history: list[Education] = Field(default_factory=list)
    employment_history: list[Employment] = Field(default_factory=list)
    file_path: str
    formatting_score: Optional[int] = None
    grammar_score: Optional[int] = None
    highlights: list[str] = Field(default_factory=list)
    hobbies: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    job_title: Optional[str] = None
    level: Optional[Level] = None
    location: Location = Field(default_factory=Location)
    name: Optional[str] = None
    nationality: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    spoken_languages: list[str] = Field(default_factory=list)
    status: CVProfileRunStatus = Field(default=CVProfileRunStatus.PENDING)
    status_comment: Optional[str] = None
    summary: Optional[str] = None
    urls: list[str] = Field(default_factory=list)
    years_experience: Optional[float] = None
