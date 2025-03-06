import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Form, UploadFile
from fastapi.responses import JSONResponse

from backend.app.config import Configuration, logger
from backend.app.services.users.cv_profile_manager import CVProfileManager
from backend.app.services.users.user_manager import UserManager
from backend.app.workers.cv_processor import CVProcessorWorker

router = APIRouter()

cv_profile_manager = CVProfileManager.get_instance()
cv_profile_manager.bootstrap()

user_manager = UserManager.get_instance()

# Start workers only after bootsrapping the DB because they rely on it
cv_processor = CVProcessorWorker()


@router.get("/cv-profile-run/{user_id}")
async def get_cv_profile_run(user_id: str):
    """Get a user's complete CV profile"""
    try:
        cv_profile = cv_profile_manager.get_cv_profile(user_id)
        if not cv_profile:
            return JSONResponse(
                status_code=404, content={"error": "CV profile not found"}
            )

        return cv_profile
    except Exception as e:
        logger.error(f"Error fetching CV profile for user {user_id}: {e}")
        return JSONResponse(
            status_code=500, content={"error": "Failed to fetch CV profile"}
        )


@router.get("/cv-profile-run-status/{user_id}")
async def get_cv_profile_run_status(user_id: str):
    """Get the current status of a user's CV processing"""
    try:
        cv_profile = cv_profile_manager.get_cv_profile(user_id)
        if not cv_profile:
            return JSONResponse(
                status_code=404, content={"error": "CV profile not found"}
            )

        return {
            "status": cv_profile.status,
            "updated_at": cv_profile.updated_at,
        }
    except Exception as e:
        logger.error(f"Error fetching CV status for user {user_id}: {e}")
        return JSONResponse(
            status_code=500, content={"error": "Failed to fetch CV status"}
        )


@router.post("/upload-cv")
async def upload_cv(
    file: UploadFile,
    user_id: str = Form(...),
):
    uploads_dir = Configuration.UPLOADS_DIRECTORY

    user = user_manager.get_user_by_id(user_id)
    if not user:
        return JSONResponse(
            status_code=400, content={"error": "User not found"}
        )

    # Create a unique directory for this upload
    user_upload_folder = os.path.join(uploads_dir, user_id)
    os.makedirs(user_upload_folder, exist_ok=True)
    # Clear any existing files in the upload folder
    for existing_file in os.listdir(user_upload_folder):
        file_path = os.path.join(user_upload_folder, existing_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            logger.error(f"Error clearing user {user_id} upload folder: {e}")
            raise

    # Generate filename as "cv" with original extension
    original_extension = Path(file.filename).suffix
    safe_filename = f"cv{original_extension}"

    # Save the file in the unique folder
    file_path = os.path.join(user_upload_folder, safe_filename)
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Add to processing queue
    cv_profile_manager.add_cv_profile(user_id, file_path)
    cv_processor.add_cv_to_queue(user_id, file_path)

    return {
        "id": user_id,
        "original_filename": file.filename,
        "saved_filename": safe_filename,
        "status": "processing",
    }
