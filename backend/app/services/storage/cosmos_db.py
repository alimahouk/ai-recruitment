import json
from typing import Any

from azure.cosmos import (
    ContainerProxy,
    CosmosClient,
    DatabaseProxy,
    PartitionKey,
    exceptions,
)
from azure.cosmos.aio import CosmosClient as CosmosAsyncClient

from backend.app.config import Configuration, logger
from backend.app.exceptions import ContainerExists, DatabaseExists


class CosmosDB:
    def __init__(self, db_name: str = Configuration.AZURE_COSMOSDB_DB_NAME):
        if db_name:
            db_name = db_name.strip()

        self.client = CosmosClient(
            url=Configuration.AZURE_COSMOSDB_ACCOUNT_ENDPOINT,
            credential=Configuration.AZURE_COSMOSDB_ACCOUNT_KEY,
        )
        self.db_name = db_name.strip()

    def bootstrap(self) -> None:
        try:
            # If the DB already exists, an exception will be caught.
            self.create_db()
        except DatabaseExists as e:
            logger.info(e)
        except Exception as e:
            logger.error(e)

    def create_container(
        self,
        container_name: str,
        container_definition: dict[str, Any],
        partition_key: str = "partition_key",
    ) -> ContainerProxy:
        if container_name:
            container_name = container_name.strip()

        if not container_name:
            raise ValueError("No container name specified.")

        if not partition_key:
            raise ValueError("No partition key specified.")

        db = self.get_db()
        try:
            # Remove 'id' from container_definition if it exists
            container_definition.pop("id", None)

            # Create the partition key definition
            partition_key_def = PartitionKey(
                path=f"/{partition_key}", kind="Hash"
            )

            # Create the complete options dictionary with camelCase keys
            container_options = {}

            # Add the rest of the container definition
            if "indexingPolicy" in container_definition:
                container_options["indexing_policy"] = container_definition[
                    "indexingPolicy"
                ]
            if "uniqueKeyPolicy" in container_definition:
                container_options["unique_key_policy"] = container_definition[
                    "uniqueKeyPolicy"
                ]
            if "vectorEmbeddingPolicy" in container_definition:
                container_options["vector_embedding_policy"] = (
                    container_definition["vectorEmbeddingPolicy"]
                )

            # Create container with partition_key as a positional argument
            container = db.create_container(
                id=container_name,
                partition_key=partition_key_def,
                **container_options,
            )
            logger.info(f"Container '{container_name}' created successfully.")
            return container
        except exceptions.CosmosResourceExistsError:
            raise ContainerExists(
                f"A container with name '{container_name}' already exists."
            )

    def create_db(self) -> DatabaseProxy:
        if not self.db_name:
            raise ValueError("No database specified.")

        try:
            logger.info(f"Creating database '{self.db_name}'...")
            db = self.client.create_database(id=self.db_name)
            properties = db.read()
            logger.info(f"Database '{self.db_name}' created successfully.")
            logger.info(json.dumps(properties))
            return db
        except exceptions.CosmosResourceExistsError:
            raise DatabaseExists(
                f"A database with ID '{self.db_name}' already exists."
            )

    def get_container(self, container_name: str) -> ContainerProxy:
        db = self.get_db()
        if db:
            return db.get_container_client(container_name)

    def get_db(self) -> DatabaseProxy:
        if not self.db_name:
            raise ValueError("No database specified.")

        return self.client.get_database_client(self.db_name)
