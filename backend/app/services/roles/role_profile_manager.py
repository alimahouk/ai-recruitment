import json
from datetime import datetime, timezone
from threading import Lock
from typing import Optional

from backend.app.config import logger
from backend.app.exceptions import ContainerExists
from backend.app.services.llm.types import RoleProfile
from backend.app.services.roles.schemas import (
    RoleListingRunStatus,
    RoleProfileRun,
)
from backend.app.services.storage import ContainerName
from backend.app.services.storage.cosmos_db import CosmosDB


class RoleProfileManager:
    _instance = None
    _lock = Lock()

    def __init__(
        self,
        container_name: str = ContainerName.ROLE_LISTING_PROFILES,
    ) -> None:
        self.db_service = CosmosDB()
        self.container = self.db_service.get_container(container_name)
        self.container_name = container_name

    def add_role_profile(
        self, role_id: str, file_path: str, creator_id: str
    ) -> None:
        """Create an empty role profile run"""
        if not file_path:
            raise ValueError("Missing file path")

        logger.info("Creating role profile run...")

        # Create minimal RoleProfileRun instance
        role_profile_run = RoleProfileRun(
            creator_id=creator_id,
            file_path=file_path,
            id=role_id,
            status=RoleListingRunStatus.PENDING,
        )

        try:
            role_profile_run_json = role_profile_run.model_dump_json()
            role_profile_run_dict = json.loads(role_profile_run_json)
            self.container.upsert_item(role_profile_run_dict)
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
                    {
                        "path": "/status/?",
                        "indexes": [
                            {
                                "kind": "Hash",
                                "dataType": "String",
                                "precision": -1,
                            }
                        ],
                    },
                    {
                        "path": "/creator_id/?",
                        "indexes": [
                            {
                                "kind": "Hash",
                                "dataType": "String",
                                "precision": -1,
                            }
                        ],
                    },
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

    def delete_role_profile(self, role_id: str) -> None:
        """Delete a role profile"""
        try:
            self.container.delete_item(
                item=role_id,
                partition_key="role_profile_run",
            )

            logger.info(f"Deleted role profile {role_id}")
        except Exception as e:
            logger.error(f"Error deleting role profile {role_id}: {e}")
            raise

    @classmethod
    def get_instance(cls) -> "RoleProfileManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def get_pending_role_profiles(self) -> list[RoleProfileRun]:
        """Get all role profiles with pending status"""
        try:
            query = """
            SELECT * FROM c
            WHERE c.type = 'role_profile_run'
            AND c.status = 'pending'
            """
            results = list(
                self.container.query_items(
                    query=query,
                    enable_cross_partition_query=True,
                )
            )
            return [RoleProfileRun.model_validate(result) for result in results]
        except Exception as e:
            logger.error(f"Error fetching pending role profiles: {e}")
            raise

    def get_role_profile(self, role_id: str) -> Optional[RoleProfileRun]:
        """Get a role profile by ID"""
        try:
            query = """
            SELECT * FROM c
            WHERE c.type = 'role_profile_run'
            AND c.id = @role_id
            """
            parameters = [{"name": "@role_id", "value": role_id}]
            results = list(
                self.container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )
            if not results:
                return None
            return RoleProfileRun.model_validate(results[0])
        except Exception as e:
            logger.error(f"Error fetching role profile {role_id}: {e}")
            raise

    def get_role_profiles_by_creator_id(
        self, creator_id: str
    ) -> list[RoleProfileRun]:
        """
        Get all role profiles created by a specific user

        Args:
            creator_id: The ID of the creator/recruiter

        Returns:
            A list of RoleProfileRun objects created by the specified user
        """
        try:
            query = """
            SELECT * FROM c
            WHERE c.type = 'role_profile_run'
            AND c.creator_id = @creator_id
            """
            parameters = [{"name": "@creator_id", "value": creator_id}]
            results = list(
                self.container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )
            return [RoleProfileRun.model_validate(result) for result in results]
        except Exception as e:
            logger.error(
                f"Error fetching role profiles for creator {creator_id}: {e}"
            )
            raise

    def _create_role_profile_run_from_profile(
        self,
        role_profile: RoleProfile,
        file_path: str,
        creator_id: str,
        existing_profile: Optional[RoleProfileRun] = None,
        status: RoleListingRunStatus = RoleListingRunStatus.COMPLETED,
        status_comment: Optional[str] = None,
    ) -> RoleProfileRun:
        """
        Create a RoleProfileRun from a RoleProfile

        Args:
            role_profile: The RoleProfile containing the profile data
            file_path: Path to the file from which the profile was extracted
            creator_id: Optional ID of the creator/recruiter
            existing_profile: Optional existing profile to update

        Returns:
            A new or updated RoleProfileRun instance
        """
        profile_data = {
            "benefits": role_profile.benefits,
            "creator_id": creator_id,
            "description": role_profile.description,
            "employment_type": role_profile.employment_type,
            "file_path": file_path,
            "industry": role_profile.industry,
            "level": role_profile.level,
            "location": role_profile.location,
            "organization_name": role_profile.organization_name,
            "preferred_qualifications": role_profile.preferred_qualifications,
            "requirements": role_profile.requirements,
            "role_mode": role_profile.role_mode,
            "salary": role_profile.salary,
            "title": role_profile.title,
            "url": role_profile.url,
            "status": status,
            "status_comment": status_comment,
            "updated_at": datetime.now(timezone.utc),
        }

        # If updating an existing profile, merge with existing data
        if existing_profile:
            return RoleProfileRun.model_validate(
                {**existing_profile.model_dump(), **profile_data}
            )

        # Otherwise create a new profile
        return RoleProfileRun(**profile_data)

    def update_role_profile(
        self,
        role_id: str,
        role_profile: RoleProfile,
        creator_id: str,
        status: RoleListingRunStatus = RoleListingRunStatus.COMPLETED,
        status_comment: Optional[str] = None,
    ) -> RoleProfileRun:
        """
        Update role profile fields with data from RoleProfile

        Args:
            role_id: The ID of the role profile to update
            role_profile: The RoleProfile containing the main profile data
            creator_id: ID of the creator/recruiter

        Returns:
            The updated RoleProfileRun object

        Raises:
            ValueError: If no profile is found with the given ID
            Exception: For database errors
        """
        try:
            # Get existing profile
            existing_profile = self.get_role_profile(role_id)
            if not existing_profile:
                raise ValueError(f"No role profile found with ID {role_id}")

            # Create updated profile using helper method
            updated_profile = self._create_role_profile_run_from_profile(
                role_profile=role_profile,
                file_path=existing_profile.file_path,
                creator_id=creator_id,
                existing_profile=existing_profile,
                status=status,
                status_comment=status_comment,
            )

            # Save the updated profile
            updated_profile_json = updated_profile.model_dump_json()
            updated_profile_dict = json.loads(updated_profile_json)
            self.container.upsert_item(updated_profile_dict)
            logger.info(f"Updated role profile {role_id}")

            # Return the updated profile
            return updated_profile
        except Exception as e:
            logger.error(f"Error updating role profile {role_id}: {e}")
            raise
