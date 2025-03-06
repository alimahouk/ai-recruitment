import json
from threading import Lock
from typing import Optional

from backend.app.config import logger
from backend.app.exceptions import ContainerExists
from backend.app.services.llm.types import Location
from backend.app.services.roles.schemas import (
    RoleListing,
    RoleListingRunStatus,
    RoleProfileRun,
)
from backend.app.services.storage import ContainerName
from backend.app.services.storage.cosmos_db import CosmosDB
from backend.app.services.storage.embeddings import EmbeddingsClient


class RoleListingManager:
    _instance = None
    _lock = Lock()

    def __init__(
        self,
        container_name: str = ContainerName.ROLE_LISTINGS,
    ) -> None:
        self.db_service = CosmosDB()
        self.container = self.db_service.get_container(container_name)

    def add_role(self, role: RoleListing) -> None:
        if not role:
            raise ValueError("Missing role listing")

        logger.info(f"Adding role listing '{role.title}'...")
        role_json = role.model_dump_json()
        role_dict = json.loads(role_json)
        try:
            self.container.upsert_item(role_dict)
        except Exception as e:
            logger.error(e)
            raise

    def add_role_from_profile(
        self, role_profile_run: RoleProfileRun
    ) -> RoleListing:
        """Create a new role listing from a completed role profile analysis.

        Args:
            role_profile_run: The completed role profile run containing the analyzed data

        Returns:
            RoleListing: The newly created role listing object

        Raises:
            ValueError: If the role profile run is not completed
            Exception: For database errors
        """
        if role_profile_run.status != RoleListingRunStatus.COMPLETED:
            raise ValueError("Cannot create role from incomplete profile")

        logger.info(
            f"Creating new role listing from profile {role_profile_run.id}..."
        )

        # Get all fields from role_profile_run, excluding 'status' and other metadata
        role_profile_data = role_profile_run.model_dump(
            exclude={
                "status",
                "id",
                "type",
                "partition_key",
                "created_at",
                "updated_at",
                "file_path",
            }
        )

        # Create new role listing object
        new_role = RoleListing.model_validate(role_profile_data)

        # Generate embeddings if needed
        if (
            hasattr(role_profile_run, "description")
            and role_profile_run.description
        ):
            try:
                embeddings_client = EmbeddingsClient.from_env()
                description = role_profile_run.description
                # Combine with other relevant fields
                if role_profile_run.title:
                    description = f"{role_profile_run.title}. {description}"
                if role_profile_run.requirements:
                    requirements_text = ". ".join(role_profile_run.requirements)
                    description = (
                        f"{description}. Requirements: {requirements_text}"
                    )

                embeddings = embeddings_client.generate_embeddings(description)
                new_role.embeddings = embeddings
            except Exception as e:
                logger.warning(
                    f"Failed to generate embeddings for new role: {e}"
                )

        # Save the new role
        self.add_role(new_role)
        logger.info(f"Created new role listing with ID {new_role.id}")
        return new_role

    def bootstrap(self) -> None:
        try:
            vector_embedding_policy = {
                "vectorEmbeddings": [
                    {
                        "path": "/embeddings",
                        "dataType": "float32",
                        "distanceFunction": "cosine",
                        "dimensions": 3072,
                    }
                ]
            }

            indexing_policy = {
                "indexingMode": "consistent",
                "automatic": True,
                "includedPaths": [
                    {"path": "/*"},
                    {
                        "path": "/title/?",
                        "indexes": [
                            {
                                "kind": "Range",
                                "dataType": "String",
                                "precision": -1,
                            }
                        ],
                    },
                    {
                        "path": "/organization_name/?",
                        "indexes": [
                            {
                                "kind": "Range",
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
                    {
                        "path": "/industry/?",
                        "indexes": [
                            {
                                "kind": "Hash",
                                "dataType": "String",
                                "precision": -1,
                            }
                        ],
                    },
                    {
                        "path": "/location/city/?",
                        "indexes": [
                            {
                                "kind": "Hash",
                                "dataType": "String",
                                "precision": -1,
                            }
                        ],
                    },
                    {
                        "path": "/location/country/?",
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
                    {"path": "/embeddings/*"},
                ],
                "vectorIndexes": [
                    {"path": "/embeddings", "type": "quantizedFlat"}
                ],
            }

            container_definition = {
                "indexingPolicy": indexing_policy,
                "vectorEmbeddingPolicy": vector_embedding_policy,
            }

            self.db_service.create_container(
                ContainerName.ROLE_LISTINGS,
                container_definition=container_definition,
            )

        except ContainerExists as e:
            logger.info(e)
        except Exception as e:
            logger.error(e)

    @classmethod
    def get_instance(cls) -> "RoleListingManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def get_role_by_id(self, role_id: str) -> Optional[RoleListing]:
        try:
            query = """
            SELECT * FROM c
            WHERE c.type = 'role_listing'
            AND c.id = @id
            """
            parameters = [{"name": "@id", "value": role_id}]
            results = list(
                self.container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )
            return RoleListing.model_validate(results[0]) if results else None
        except Exception as e:
            logger.error(f"Error fetching role {role_id}: {e}")
            raise

    def get_roles_by_creator_id(self, creator_id: str) -> list[RoleListing]:
        """
        Fetch all role listings created by a specific user.

        Args:
            creator_id: The ID of the creator/recruiter

        Returns:
            A list of RoleListing objects created by the specified user
        """
        query = """
        SELECT * FROM c
        WHERE c.type = 'role_listing'
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
        return [RoleListing.model_validate(result) for result in results]

    def get_roles_by_industry(self, industry: str) -> list[RoleListing]:
        query = """
        SELECT * FROM c
        WHERE c.type = 'role_listing'
        AND c.industry = @industry
        """
        parameters = [{"name": "@industry", "value": industry}]
        results = list(
            self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )
        return [RoleListing.model_validate(result) for result in results]

    def get_roles_by_location(self, location: Location) -> list[RoleListing]:
        query = """
        SELECT * FROM c
        WHERE c.type = 'role_listing'
        AND (
            (@city IS NULL OR c.location.city = @city)
            AND (@country IS NULL OR c.location.country = @country)
        )
        """
        parameters = [
            {"name": "@city", "value": location.city},
            {"name": "@country", "value": location.country},
        ]
        results = list(
            self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )
        return [RoleListing.model_validate(result) for result in results]

    def get_roles_by_title(self, title: str) -> list[RoleListing]:
        query = """
        SELECT * FROM c
        WHERE c.type = 'role_listing'
        AND CONTAINS(LOWER(c.title), LOWER(@title))
        """
        parameters = [{"name": "@title", "value": title}]
        results = list(
            self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )
        return [RoleListing.model_validate(result) for result in results]

    def search_roles(
        self, candidate_profile: str, top_k: int = 10
    ) -> list[tuple[str, float]]:
        """Search for roles based on similarity to candidate profile"""
        if not candidate_profile.strip():
            raise ValueError("Expected a candidate profile!")

        embeddings_client = EmbeddingsClient.from_env()
        query_embedding = embeddings_client.generate_embeddings(
            candidate_profile
        )

        query = """
        SELECT TOP @top_k
            c.id,
            c.title,
            VectorDistance(c.embeddings, @embedding) AS score
        FROM c
        WHERE c.type = 'role_listing'
        ORDER BY VectorDistance(c.embeddings, @embedding)
        """
        parameters = [
            {"name": "@embedding", "value": query_embedding},
            {"name": "@top_k", "value": top_k},
        ]
        results = list(
            self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )
        return [(result["id"], result["score"]) for result in results]

    def search_roles_by_organization(
        self, organization_name: str
    ) -> list[RoleListing]:
        query = """
        SELECT * FROM c
        WHERE c.type = 'role_listing'
        AND CONTAINS(LOWER(c.organization_name), LOWER(@organization_name))
        """
        parameters = [
            {"name": "@organization_name", "value": organization_name}
        ]
        results = list(
            self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )
        return [RoleListing.model_validate(result) for result in results]

    def update_role(self, role_id: str, role: RoleListing) -> None:
        """Update an existing role listing's information.

        Args:
            role_id: The ID of the role to update
            role: The updated RoleListing object

        Raises:
            ValueError: If role_id or role is missing
            Exception: For database errors
        """
        if not role_id or not role:
            raise ValueError("Missing role_id or role data")

        logger.info(f"Updating role '{role_id}'...")

        # Ensure the role exists
        existing_role = self.get_role_by_id(role_id)
        if not existing_role:
            raise ValueError(f"Role with ID {role_id} not found")

        # Update the role data
        role_dict = json.loads(role.model_dump_json())
        role_dict["id"] = role_id  # Preserve the original ID
        role_dict["partition_key"] = "role"

        try:
            self.container.replace_item(item=role_id, body=role_dict)
        except Exception as e:
            logger.error(f"Error updating role {role_id}: {e}")
            raise

    def update_role_from_profile(
        self, role_id: str, role_profile_run: RoleProfileRun
    ) -> RoleListing:
        """Update a role listing's information based on role profile analysis results.

        Args:
            role_id: The ID of the role to update
            role_profile_run: The completed role profile run containing the analyzed data

        Returns:
            RoleListing: The updated role listing object

        Raises:
            ValueError: If the role profile run is not completed or role not found
            Exception: For other database errors
        """
        if role_profile_run.status != RoleListingRunStatus.COMPLETED:
            raise ValueError("Cannot update role from incomplete profile")

        # Get existing role
        existing_role = self.get_role_by_id(role_id)
        if not existing_role:
            raise ValueError(f"Role with ID {role_id} not found")

        # Get all fields from role_profile_run, excluding 'status' and other metadata
        role_profile_data = role_profile_run.model_dump(
            exclude={
                "status",
                "id",
                "type",
                "created_at",
                "updated_at",
                "file_path",
            }
        )

        # Create updated role object, preserving the role's ID and any fields not in profile
        updated_role = RoleListing.model_validate(
            {**existing_role.model_dump(), **role_profile_data}
        )

        # Save the updates
        self.update_role(role_id, updated_role)
        logger.info(f"Updated role {role_id} with profile data")
        return updated_role

    def delete_role(self, role_id: str) -> None:
        """Delete a role listing by ID.

        Args:
            role_id: The ID of the role to delete

        Raises:
            Exception: For database errors
        """
        try:
            self.container.delete_item(
                item=role_id,
                partition_key="role_listing",
            )
            logger.info(f"Deleted role listing {role_id}")
        except Exception as e:
            logger.error(f"Error deleting role listing {role_id}: {e}")
            raise
