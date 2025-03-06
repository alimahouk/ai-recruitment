import json
from datetime import datetime, timezone
from threading import Lock
from typing import Optional

from backend.app.config import logger
from backend.app.exceptions import ContainerExists
from backend.app.services.llm.types import CVProfile
from backend.app.services.storage import ContainerName
from backend.app.services.storage.cosmos_db import CosmosDB
from backend.app.services.users.schemas import CVProfileRun, CVProfileRunStatus


class CVProfileManager:
    _instance = None
    _lock = Lock()

    def __init__(
        self,
        container_name: str = ContainerName.CV_PROFILES,
    ) -> None:
        self.db_service = CosmosDB()
        self.container = self.db_service.get_container(container_name)
        self.container_name = container_name

    def add_cv_profile(self, user_id: str, file_path: str) -> None:
        """Create an empty CV profile run for a user"""
        if not user_id:
            raise ValueError("Missing user ID")
        if not file_path:
            raise ValueError("Missing file path")

        logger.info(f"Creating CV profile run for user '{user_id}'...")

        # Create minimal CVProfileRun instance
        cv_profile_run = CVProfileRun(
            id=user_id,  # Use user_id as the profile id for uniqueness
            file_path=file_path,
            status=CVProfileRunStatus.PENDING,
        )

        try:
            cv_profile_run_json = cv_profile_run.model_dump_json()
            cv_profile_run_dict = json.loads(cv_profile_run_json)
            self.container.upsert_item(cv_profile_run_dict)
        except Exception as e:
            logger.error(e)
            raise

    def bootstrap(self) -> None:
        """Initialize the container with required indexes"""
        try:
            indexing_policy = {
                "indexingMode": "consistent",
                "automatic": True,
                "includedPaths": [
                    {"path": "/*"},
                ],
                "excludedPaths": [
                    {"path": '/"_etag"/?'},
                ],
            }

            container_definition = {
                "indexingPolicy": indexing_policy,
            }

            self.db_service.create_container(
                self.container_name,
                container_definition=container_definition,
            )
        except ContainerExists as e:
            logger.info(e)
        except Exception as e:
            logger.error(e)

    def delete_cv_profile(self, user_id: str) -> None:
        """Delete a user's CV profile"""
        try:
            self.container.delete_item(
                item=user_id,
                partition_key="cv_profile",
            )

            logger.info(f"Deleted CV profile for user {user_id}")
        except Exception as e:
            logger.error(f"Error deleting CV profile for user {user_id}: {e}")
            raise

    def get_cv_profile(self, user_id: str) -> Optional[CVProfileRun]:
        """Get a user's CV profile"""
        try:
            query = """
            SELECT * FROM c
            WHERE c.type = 'cv_profile'
            AND c.id = @user_id
            """
            parameters = [{"name": "@user_id", "value": user_id}]
            results = list(
                self.container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )
            if not results:
                return None
            return CVProfileRun.model_validate(results[0])
        except Exception as e:
            logger.error(f"Error fetching CV profile for user {user_id}: {e}")
            raise

    @classmethod
    def get_instance(cls) -> "CVProfileManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def get_pending_cv_profiles(self) -> list[CVProfileRun]:
        """Get all CV profiles with pending status"""
        try:
            query = """
            SELECT * FROM c
            WHERE c.type = 'cv_profile'
            AND c.status = 'pending'
            """
            results = list(
                self.container.query_items(
                    query=query,
                    enable_cross_partition_query=True,
                )
            )
            return [CVProfileRun.model_validate(result) for result in results]
        except Exception as e:
            logger.error(f"Error fetching pending CV profiles: {e}")
            raise

    def _create_cv_profile_run_from_cv_profile(
        self,
        user_id: str,
        cv_profile: CVProfile,
        file_path: Optional[str] = None,
        *,  # Force keyword arguments for clarity
        average_tenure: Optional[float] = None,
        creativity_score: Optional[int] = None,
        formatting_score: Optional[int] = None,
        grammar_score: Optional[int] = None,
        status: CVProfileRunStatus = CVProfileRunStatus.COMPLETED,
        status_comment: Optional[str] = None,
        years_experience: Optional[float] = None,
    ) -> CVProfileRun:
        """
        Create a CVProfileRun from a CVProfile

        Args:
            user_id: The ID of the user
            cv_profile: The CVProfile containing the main profile data
            file_path: Optional file path for the CV document
            creativity_score: Optional score for creativity assessment
            formatting_score: Optional score for formatting assessment
            grammar_score: Optional score for grammar assessment
            status: Status of the CV profile run (default: COMPLETED)

        Returns:
            A CVProfileRun instance populated with data from the CVProfile
        """
        now = datetime.now(timezone.utc)

        return CVProfileRun(
            average_tenure=average_tenure,
            awards=cv_profile.awards,
            contact_details=cv_profile.contact_details,
            created_at=now,
            creativity_score=creativity_score,
            education_history=cv_profile.education_history,
            employment_history=cv_profile.employment_history,
            file_path=file_path,
            formatting_score=formatting_score,
            grammar_score=grammar_score,
            highlights=cv_profile.highlights,
            hobbies=cv_profile.hobbies,
            id=user_id,
            industries=cv_profile.industries,
            job_title=cv_profile.job_title,
            level=cv_profile.level,
            location=cv_profile.location,
            name=cv_profile.name,
            nationality=cv_profile.nationality,
            skills=cv_profile.skills,
            spoken_languages=cv_profile.spoken_languages,
            status=status,
            status_comment=status_comment,
            summary=cv_profile.summary,
            urls=cv_profile.urls,
            updated_at=now,
            years_experience=years_experience,
        )

    def update_cv_profile(
        self,
        user_id: str,
        cv_profile: CVProfile,
        *,  # Force keyword arguments for clarity
        average_tenure: Optional[float] = None,
        creativity_score: Optional[int] = None,
        formatting_score: Optional[int] = None,
        grammar_score: Optional[int] = None,
        status: CVProfileRunStatus = CVProfileRunStatus.COMPLETED,
        status_comment: Optional[str] = None,
        years_experience: Optional[float] = None,
    ) -> None:
        """
        Update CV profile fields with data from CVProfile and optional scoring data

        Args:
            user_id: The ID of the user whose profile to update
            cv_profile: The CVProfile containing the main profile data
            creativity_score: Optional score for creativity assessment
            formatting_score: Optional score for formatting assessment
            grammar_score: Optional score for grammar assessment
        """
        try:
            # Get existing profile
            profile = self.get_cv_profile(user_id)
            if not profile:
                raise ValueError(f"No CV profile found for user {user_id}")

            # Create updated profile using the helper method
            updated_profile = self._create_cv_profile_run_from_cv_profile(
                user_id=user_id,
                cv_profile=cv_profile,
                file_path=profile.file_path,
                average_tenure=average_tenure,
                creativity_score=creativity_score,
                formatting_score=formatting_score,
                grammar_score=grammar_score,
                status=status,
                status_comment=status_comment,
                years_experience=years_experience,
            )

            # Preserve created_at from the original profile
            updated_profile.created_at = profile.created_at

            # Convert to dict and save
            updated_profile_json = updated_profile.model_dump_json()
            updated_profile_dict = json.loads(updated_profile_json)
            self.container.upsert_item(updated_profile_dict)
            logger.info(f"Updated CV profile for user {user_id}")
        except Exception as e:
            logger.error(f"Error updating CV profile for user {user_id}: {e}")
            raise
