import configparser
import logging
import logging.config
import os
from enum import StrEnum
from pathlib import Path

import colorlog
from dotenv import load_dotenv

# Get the path to the backend directory (two levels up from this file)
backend_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(
    dotenv_path=backend_dir / ".env"
)  # Load environment variables from the .env file

current_dir = Path(__file__).parent

config = configparser.ConfigParser()
config.read(current_dir / "config.ini")
ai_config = config["ai"]
db_config = config["databases"]
main_config = config["main"]
storage_config = config["file_storage"]

# Load environment variables from .env file
load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')

class AnthropicModel(StrEnum):
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20241022"


class AnthropicBedrockModel(StrEnum):
    CLAUDE_3_5_SONNET = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"


class AzureOpenAIDeployment(StrEnum):
    GPT_4O = "gpt-4o"
    TEXT_EMBEDDINGS_3_LARGE = "text-embedding-3-large"


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Configuration:
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_BEDROCK_REGION = ai_config.get("aws_bedrock_region")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AZURE_AI_SERVICES_EASTUS_API_KEY = os.getenv(
        "AZURE_AI_SERVICES_EASTUS_API_KEY"
    )
    AZURE_AI_SERVICES_EASTUS_ENDPOINT = ai_config.get(
        "azure_ai_services_eastus_endpoint"
    )
    AZURE_AI_SERVICES_EASTUS2_API_KEY = os.getenv(
        "AZURE_AI_SERVICES_EASTUS2_API_KEY"
    )
    AZURE_AI_SERVICES_EASTUS2_ENDPOINT = ai_config.get(
        "azure_ai_services_eastus2_endpoint"
    )
    AZURE_COSMOSDB_ACCOUNT_ENDPOINT = db_config.get(
        "azure_cosmosdb_account_endpoint"
    )
    AZURE_COSMOSDB_ACCOUNT_KEY = os.getenv("AZURE_COSMOSDB_NOSQL_ACCOUNT_KEY")
    AZURE_COSMOSDB_DB_NAME = db_config.get("azure_cosmosdb_db_name")
    AZURE_OPENAI_GPT_4O_API_VERSION = ai_config.get(
        "azure_openai_gpt_4o_api_version"
    )
    AZURE_OPENAI_TEXT_EMBEDDINGS_3_LARGE_API_VERSION = ai_config.get(
        "azure_openai_text_embeddings_3_large_api_version"
    )
    CV_MAX_PAGES = 2
    ENV = Environment(main_config.get("identity_environment"))
    JD_MAX_PAGES = 3
    LOG_DIRECTORY = main_config.get("log_directory")
    UPLOADS_DIRECTORY = Path("backend") / "uploads"


# Logging
# --
os.makedirs(Configuration.LOG_DIRECTORY, exist_ok=True)
if Configuration.ENV == Environment.PRODUCTION:
    # Log to a file when running in container.
    logging.config.fileConfig(
        "config/logging.ini"
    )  # Load the logging configuration.

# Stream Handler for logging to the console with color.
stream_handler = colorlog.StreamHandler()
stream_handler.setFormatter(
    colorlog.ColoredFormatter(
        "%(log_color)s[%(asctime)s][%(levelname)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)

# Disable Azure info logs.
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

# Configure logger.
logger = colorlog.getLogger()
logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)
