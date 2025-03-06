from enum import StrEnum
from typing import Optional

from pydantic import BaseModel


class Award(BaseModel):
    """Structured output from LLM analysis of an award"""

    date: Optional["Date"] = None
    description: Optional[str] = None
    name: Optional[str] = None


class Certification(BaseModel):
    """Structured output from LLM analysis of a certification"""

    field: Optional[str] = None
    level: Optional[str] = None
    name: Optional[str] = None


class ContactDetails(BaseModel):
    """Structured output from LLM analysis of contact details"""

    email: Optional[str] = None
    phone_number: Optional[str] = None


class CVProfile(BaseModel):
    """Structured output from LLM analysis of a CV profile"""

    awards: list["Award"]
    contact_details: "ContactDetails"
    education_history: list["Education"]
    employment_history: list["Employment"]
    highlights: list[str]
    hobbies: list[str]
    industries: list[str]
    job_title: Optional[str] = None
    level: Optional["Level"] = None
    location: "Location"
    name: Optional[str] = None
    nationality: Optional[str] = None
    skills: list[str]
    spoken_languages: list[str]
    summary: Optional[str] = None
    urls: list[
        str
    ]  # Any links included in the CV, e.g. LinkedIn, blog, GitHub, etc.


class Date(BaseModel):
    """Structured output from LLM analysis of a date"""

    month: int
    year: int


class Education(BaseModel):
    """Structured output from LLM analysis of an education record"""

    certification: "Certification"
    end_date: "Date"
    institution: Optional[str] = None
    location: "Location"
    start_date: Date


class Employment(BaseModel):
    """Structured output from LLM analysis of an employment record"""

    organization_name: Optional[str] = None
    end_date: Date
    location: "Location"
    role: Optional[str] = None
    start_date: Date
    summary: Optional[str] = None
    type: Optional["EmploymentType"] = None


class EmploymentType(StrEnum):
    """Type of employment of the job role"""

    CONTRACT = "contract"
    FULL_TIME = "full-time"
    INTERNSHIP = "internship"
    PART_TIME = "part-time"
    VOLUNTEER = "volunteer"


class Level(StrEnum):
    """Seniority level of experience of the candidate"""

    ENTRY_LEVEL = "entry-level"  # Fresh graduates, 0-2 years experience
    JUNIOR = "junior"  # Early career, 2-4 years experience
    MID_LEVEL = "mid-level"  # Established professionals, 4-8 years experience
    SENIOR = "senior"  # Experienced professionals, 8+ years experience
    EXECUTIVE = "executive"  # C-level, VP, Director positions


class Location(BaseModel):
    """Structured output from LLM analysis of a location"""

    city: Optional[str] = None
    country: Optional[str] = None  # ISO 3166-1 alpha-2 code


class RoleMode(StrEnum):
    """Working format of the job role"""

    HYBRID = "hybrid"
    ON_SITE = "on-site"
    REMOTE = "remote"


class RoleProfile(BaseModel):
    """Structured output from LLM analysis of a job listing"""

    benefits: list[str]
    description: str
    employment_type: Optional["EmploymentType"] = None
    industry: Optional[str] = None
    job_id: Optional[str] = None
    level: Optional["Level"] = None
    location: "Location" = None
    organization_name: Optional[str] = None
    preferred_qualifications: list[str]
    requirements: list[str]
    role_mode: Optional["RoleMode"] = None
    salary: Optional[str] = None
    title: str
    url: Optional[str] = None
