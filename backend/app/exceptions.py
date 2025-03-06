import inspect
import traceback
from typing import Optional

from backend.app.config import logger


class CosmosDBError(Exception):
    """Base class for all Cosmos DB exceptions."""

    pass


class ContainerExists(CosmosDBError):
    """The specified container already exists."""

    pass


class CVError(Exception):
    """Base class for all CV exceptions."""

    def __init__(
        self, error_message: str, cv_id: str, file_path: Optional[str] = None
    ):
        super().__init__(error_message)

        self.cv_id = cv_id
        self.file_path = file_path


class CVFormatError(CVError):
    """Exception raised for errors in the CV format."""

    pass


class CVLengthError(CVError):
    """Exception raised for errors in the CV length."""

    pass


class DatabaseExists(CosmosDBError):
    """The specified database already exists."""

    pass


class RoleListingError(Exception):
    """Base class for all JD exceptions."""

    def __init__(
        self, error_message: str, jd_id: str, file_path: Optional[str] = None
    ):
        super().__init__(error_message)

        self.jd_id = jd_id
        self.file_path = file_path


class JDFormatError(RoleListingError):
    """Exception raised for errors in the JD format."""

    pass


class JDLengthError(RoleListingError):
    """Exception raised for errors in the JD length."""

    pass


class LLMError(Exception):
    """Base class for LLM exceptions."""

    pass


class LLMConfigError(LLMError):
    """Exception raised for errors in the LLM configuration."""

    pass


class LLMInferenceError(LLMError):
    """Exception raised for errors in the LLM's response."""

    pass


class UserError(Exception):
    """Base class for user exceptions."""

    pass


class UserExistsError(UserError):
    """Exception raised when attempting to create a user that already exists."""

    pass


class UserNotFoundError(UserError):
    """Exception raised when a user is not found."""

    pass


class WebSearchError(Exception):
    """Exception raised for errors in the WebSearchService configuration."""

    pass


def log_exception(e: Exception):
    """
    Use for logging. Particularly helpful when debugging from a Docker container.
    """

    frame = inspect.currentframe().f_back  # Get caller's frame.
    try:
        logger.error(
            f"Exception: {str(e)}\n"
            f"Function: {frame.f_code.co_name}\n"
            f"Line: {frame.f_lineno}\n"
            f"Locals: {frame.f_locals}\n"  # Be careful with sensitive data.
            f"Traceback:\n{traceback.format_exc()}"
        )
    finally:
        del frame  # Clean up reference.
