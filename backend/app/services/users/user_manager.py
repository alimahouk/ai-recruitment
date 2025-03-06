import json
from threading import Lock
from typing import Optional

from azure.cosmos import exceptions

from backend.app.config import logger
from backend.app.exceptions import (
    ContainerExists,
    UserExistsError,
    UserNotFoundError,
)
from backend.app.services.llm.types import Location
from backend.app.services.storage import ContainerName
from backend.app.services.storage.cosmos_db import CosmosDB
from backend.app.services.storage.embeddings import EmbeddingsClient
from backend.app.services.users.schemas import (
    CVProfileRun,
    CVProfileRunStatus,
    User,
)


class UserManager:
    _instance = None
    _lock = Lock()

    def __init__(
        self,
        container_name: str = ContainerName.USERS,
    ) -> None:
        self.db_service = CosmosDB()
        self.container = self.db_service.get_container(container_name)

    def add_user(self, user: User) -> None:
        if not user:
            raise ValueError("Missing user")

        logger.info(f"Adding user '{user.name}'...")
        user_json = user.model_dump_json()
        user_dict = json.loads(user_json)
        try:
            self.container.upsert_item(user_dict)
        except exceptions.CosmosResourceExistsError as e:
            raise UserExistsError(
                "User with this email or phone number already exists"
            ) from e
        except Exception as e:
            logger.error(e)
            raise

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

            # Add unique key policy for both email and phone number
            unique_key_policy = {
                "uniqueKeys": [
                    {"paths": ["/contact_details/email"]},
                    {"paths": ["/contact_details/phone_number"]},
                ]
            }

            indexing_policy = {
                "indexingMode": "consistent",
                "automatic": True,
                "includedPaths": [
                    {"path": "/*"},
                    {
                        "path": "/name/?",
                        "indexes": [
                            {
                                "kind": "Range",
                                "dataType": "String",
                                "precision": -1,
                            }
                        ],
                    },
                    {
                        "path": "/job_title/?",
                        "indexes": [
                            {
                                "kind": "Range",
                                "dataType": "String",
                                "precision": -1,
                            }
                        ],
                    },
                    {
                        "path": "/industries/*",
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
                    {
                        "path": "/contact_details/email/?",
                        "indexes": [
                            {
                                "kind": "Hash",
                                "dataType": "String",
                                "precision": -1,
                            }
                        ],
                    },
                    {
                        "path": "/contact_details/phone_number/?",
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
                "uniqueKeyPolicy": unique_key_policy,
            }

            self.db_service.create_container(
                ContainerName.USERS, container_definition=container_definition
            )

        except ContainerExists as e:
            logger.info(e)
        except Exception as e:
            logger.error(e)

    @classmethod
    def get_instance(cls) -> "UserManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def get_user_by_email(self, email: str) -> Optional[User]:
        try:
            query = """
            SELECT * FROM c
            WHERE c.type = 'user'
            AND c.contact_details.email = @email
            """
            parameters = [{"name": "@email", "value": email}]
            results = list(
                self.container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )
            return User.model_validate(results[0]) if results else None
        except Exception as e:
            logger.error(f"Error fetching user by email {email}: {e}")
            raise

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        try:
            query = """
            SELECT * FROM c
            WHERE c.type = 'user'
            AND c.id = @id
            """
            parameters = [{"name": "@id", "value": user_id}]
            results = list(
                self.container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )
            if not results:
                return None

            return User.model_validate(results[0])
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            raise

    def get_user_by_phone(self, phone_number: str) -> Optional[User]:
        try:
            query = """
            SELECT * FROM c
            WHERE c.type = 'user'
            AND c.contact_details.phone_number = @phone_number
            """
            parameters = [{"name": "@phone_number", "value": phone_number}]
            results = list(
                self.container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )
            return User.model_validate(results[0]) if results else None
        except Exception as e:
            logger.error(
                f"Error fetching user by phone number {phone_number}: {e}"
            )
            raise

    def get_users_by_location(self, location: Location) -> list[User]:
        query = """
        SELECT * FROM c
        WHERE c.type = 'user'
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
        return [User.model_validate(result) for result in results]

    def get_users_by_industry(self, industry: str) -> list[User]:
        query = """
        SELECT * FROM c
        WHERE c.type = 'user'
        AND ARRAY_CONTAINS(c.industries, @industry)
        """
        parameters = [{"name": "@industry", "value": industry}]
        results = list(
            self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )
        return [User.model_validate(result) for result in results]

    def get_users_by_job_title(self, job_title: str) -> list[User]:
        query = """
        SELECT * FROM c
        WHERE c.type = 'user'
        AND CONTAINS(LOWER(c.job_title), LOWER(@job_title))
        """
        parameters = [{"name": "@job_title", "value": job_title}]
        results = list(
            self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )
        return [User.model_validate(result) for result in results]

    def search_candidates(
        self, job_description: str, top_k: int = 10
    ) -> list[tuple[str, float]]:
        """Search for candidates based on similarity to job description"""
        if not job_description.strip():
            raise ValueError("Expected a job description!")

        embeddings_client = EmbeddingsClient.from_env()
        query_embedding = embeddings_client.generate_embeddings(job_description)

        query = """
        SELECT TOP @top_k
            c.id,
            c.name,
            VectorDistance(c.embeddings, @embedding) AS score
        FROM c
        WHERE c.type = 'user'
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

    def search_users_by_name(self, name: str) -> list[User]:
        query = """
        SELECT * FROM c
        WHERE c.type = 'user'
        AND CONTAINS(LOWER(c.name), LOWER(@name))
        """
        parameters = [{"name": "@name", "value": name}]
        results = list(
            self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )
        return [User.model_validate(result) for result in results]

    def update_user(self, user_id: str, user: User) -> None:
        """Update an existing user's information.

        Args:
            user_id: The ID of the user to update
            user: The updated User object

        Raises:
            ValueError: If user_id or user is missing
            UserExistsError: If the update would create a duplicate email/phone
            Exception: For other database errors
        """
        if not user_id or not user:
            raise ValueError("Missing user_id or user data")

        logger.info(f"Updating user '{user_id}'...")

        # Ensure the user exists
        existing_user = self.get_user_by_id(user_id)
        if not existing_user:
            raise UserNotFoundError(f"User with ID {user_id} not found")

        # Update the user data
        user_dict = json.loads(user.model_dump_json())
        user_dict["id"] = user_id  # Preserve the original ID
        user_dict["partition_key"] = "user"

        try:
            self.container.replace_item(item=user_id, body=user_dict)
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            raise

    def update_user_from_cv_profile(
        self, user_id: str, cv_profile_run: CVProfileRun
    ) -> User:
        """Update a user's information based on their CV profile analysis results.

        Args:
            user_id: The ID of the user to update
            cv_profile_run: The completed CV profile run containing the analyzed data

        Returns:
            User: The updated user object

        Raises:
            UserNotFoundError: If the user doesn't exist
            ValueError: If the CV profile run is not completed
            Exception: For other database errors
        """
        if cv_profile_run.status != CVProfileRunStatus.COMPLETED:
            raise ValueError("Cannot update user from incomplete CV profile")

        # Get existing user
        existing_user = self.get_user_by_id(user_id)
        if not existing_user:
            raise UserNotFoundError(f"User with ID {user_id} not found")

        # Get all fields from cv_profile_run, excluding 'status' and other metadata
        cv_profile_data = cv_profile_run.model_dump(
            exclude={
                "status",
                "id",
                "type",
                "user_id",
                "created_at",
                "updated_at",
            }
        )

        # Create updated user object, preserving the user's ID and any fields not in CV profile
        updated_user = User.model_validate(
            {**existing_user.model_dump(), **cv_profile_data}
        )

        # Generate embeddings for the user profile
        try:
            embeddings_client = EmbeddingsClient.from_env()
            profile_text = ""

            # Combine relevant fields for embedding generation
            if updated_user.name:
                profile_text += f"{updated_user.name}. "

            if updated_user.job_title:
                profile_text += f"{updated_user.job_title}. "

            if updated_user.summary:
                profile_text += f"{updated_user.summary}. "

            if updated_user.skills:
                skills_text = ". ".join(updated_user.skills)
                profile_text += f"Skills: {skills_text}. "

            if updated_user.experience:
                experience_text = ". ".join(
                    [
                        f"{exp.title} at {exp.company}"
                        for exp in updated_user.experience
                    ]
                )
                profile_text += f"Experience: {experience_text}. "

            if updated_user.education:
                education_text = ". ".join(
                    [
                        f"{edu.degree} from {edu.institution}"
                        for edu in updated_user.education
                    ]
                )
                profile_text += f"Education: {education_text}."

            if profile_text:
                embeddings = embeddings_client.generate_embeddings(profile_text)
                updated_user.embeddings = embeddings
                logger.info(f"Generated embeddings for user {user_id}")
        except Exception as e:
            logger.warning(
                f"Failed to generate embeddings for user {user_id}: {e}"
            )

        # Save the updates
        self.update_user(user_id, updated_user)
        logger.info(f"Updated user {user_id} with CV profile data")
        return updated_user
