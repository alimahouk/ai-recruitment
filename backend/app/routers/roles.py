import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Form, Query, UploadFile
from fastapi.responses import JSONResponse

from backend.app.config import Configuration, logger
from backend.app.services.roles.role_listing_manager import RoleListingManager
from backend.app.services.roles.role_profile_manager import RoleProfileManager
from backend.app.services.users.schemas import UserRole
from backend.app.services.users.user_manager import UserManager
from backend.app.workers.jd_processor import JDProcessorWorker

router = APIRouter()

role_profile_manager = RoleProfileManager.get_instance()
role_profile_manager.bootstrap()

role_listing_manager = RoleListingManager.get_instance()
role_listing_manager.bootstrap()

user_manager = UserManager.get_instance()

# Start workers only after bootsrapping the DB because they rely on it
jd_processor = JDProcessorWorker()


@router.delete("/role/{role_id}")
async def delete_role(role_id: str, user_id: str = Query(...)):
    """Delete a role by ID (checks both role listings and role profiles)

    Args:
        role_id: The ID of the role to delete
        user_id: The ID of the user making the request (must be the creator)
    """
    try:
        # First check if it's a role listing
        role = role_listing_manager.get_role_by_id(role_id)
        if role:
            # Check if the user is the creator of the role
            if role.creator_id != user_id:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "You are not authorized to delete this role"
                    },
                )

            # Delete the role
            role_listing_manager.delete_role(role_id)
            return {"message": f"Role {role_id} deleted successfully"}

        # If not found in role listings, check if it's a role profile
        role_profile = role_profile_manager.get_role_profile(role_id)
        if role_profile:
            # Check if the user is the creator of the role profile
            if role_profile.creator_id != user_id:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "You are not authorized to delete this role"
                    },
                )

            # Delete the role profile
            role_profile_manager.delete_role_profile(role_id)
            return {"message": f"Role profile {role_id} deleted successfully"}

        # If not found in either, return 404
        return JSONResponse(
            status_code=404, content={"error": "Role not found"}
        )
    except Exception as e:
        logger.error(f"Error deleting role {role_id}: {e}")
        return JSONResponse(
            status_code=500, content={"error": "Failed to delete role"}
        )


@router.get("/role/{role_id}")
async def get_role(role_id: str):
    """Get a role by ID (checks both role listings and role profiles)"""
    try:
        # First check if it's a role listing
        role = role_listing_manager.get_role_by_id(role_id)
        if role:
            return role

        # If not found, check if it's a role profile
        role_profile = role_profile_manager.get_role_profile(role_id)
        if role_profile:
            return role_profile

        # If not found in either, return 404
        return JSONResponse(
            status_code=404, content={"error": "Role not found"}
        )
    except Exception as e:
        logger.error(f"Error fetching role {role_id}: {e}")
        return JSONResponse(
            status_code=500, content={"error": "Failed to fetch role"}
        )


@router.get("/role-profile-run/{role_id}")
async def get_role_profile_run(role_id: str):
    """Get a complete role profile"""
    try:
        role_profile = role_profile_manager.get_role_profile(role_id)
        if not role_profile:
            return JSONResponse(
                status_code=404, content={"error": "Role profile not found"}
            )

        return role_profile
    except Exception as e:
        logger.error(f"Error fetching role profile for role {role_id}: {e}")
        return JSONResponse(
            status_code=500, content={"error": "Failed to fetch role profile"}
        )


@router.get("/role-profile-run-status/{role_id}")
async def get_role_profile_run_status(role_id: str):
    """Get the current status of a role's processing"""
    try:
        role_profile = role_profile_manager.get_role_profile(role_id)
        if not role_profile:
            return JSONResponse(
                status_code=404, content={"error": "Role profile not found"}
            )

        return {
            "status": role_profile.status,
            "updated_at": role_profile.updated_at,
        }
    except Exception as e:
        logger.error(f"Error fetching role status for role {role_id}: {e}")
        return JSONResponse(
            status_code=500, content={"error": "Failed to fetch role status"}
        )


@router.get("/user-roles/{user_id}")
async def get_user_roles(user_id: str):
    """Get all role profiles created by a specific user"""
    try:
        user = user_manager.get_user_by_id(user_id)
        if not user:
            return JSONResponse(
                status_code=404, content={"error": "User not found"}
            )

        # Get all roles created by this user
        user_roles = role_listing_manager.get_roles_by_creator_id(user_id)

        return {"user_id": user_id, "roles": user_roles}
    except Exception as e:
        logger.error(f"Error fetching roles for user {user_id}: {e}")
        return JSONResponse(
            status_code=500, content={"error": "Failed to fetch user roles"}
        )


@router.get("/user-role-profiles/{user_id}")
async def get_user_role_profiles(user_id: str):
    """Get all role profiles created by a specific user"""
    try:
        user = user_manager.get_user_by_id(user_id)
        if not user:
            return JSONResponse(
                status_code=404, content={"error": "User not found"}
            )

        # Get all role profiles created by this user
        user_role_profiles = (
            role_profile_manager.get_role_profiles_by_creator_id(user_id)
        )

        return {"user_id": user_id, "role_profiles": user_role_profiles}
    except Exception as e:
        logger.error(f"Error fetching role profiles for user {user_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to fetch user role profiles"},
        )


@router.get("/user-listings/{user_id}")
async def get_user_listings(user_id: str):
    """Get combined list of roles and role profiles created by a specific user

    Logic:
    - All roles are included
    - Role profiles are included only if there's no role with the same ID
    """
    try:
        user = user_manager.get_user_by_id(user_id)
        if not user:
            return JSONResponse(
                status_code=404, content={"error": "User not found"}
            )

        # Get all roles created by this user
        user_roles = role_listing_manager.get_roles_by_creator_id(user_id)

        # Get all role profiles created by this user
        user_role_profiles = (
            role_profile_manager.get_role_profiles_by_creator_id(user_id)
        )

        # Create a set of role IDs for quick lookup
        role_ids = {role.id for role in user_roles}

        # Filter role profiles to only include those without a matching role
        filtered_profiles = [
            profile
            for profile in user_role_profiles
            if profile.id not in role_ids
        ]

        # Combine the lists
        combined_listings = user_roles + filtered_profiles

        return {
            "user_id": user_id,
            "listings": combined_listings,
            "total_count": len(combined_listings),
        }
    except Exception as e:
        logger.error(
            f"Error fetching combined listings for user {user_id}: {e}"
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to fetch user listings"},
        )


@router.post("/upload-jd")
async def upload_jd(
    file: UploadFile,
    user_id: str = Form(...),
):
    user = user_manager.get_user_by_id(user_id)
    if not user:
        return JSONResponse(
            status_code=404, content={"error": "User not found"}
        )

    if user.role != UserRole.RECRUITER:
        return JSONResponse(
            status_code=403, content={"error": "User is not a recruiter"}
        )

    uploads_dir = Configuration.UPLOADS_DIRECTORY

    # Create a unique directory for this upload
    role_id = str(uuid.uuid4())
    role_upload_folder = os.path.join(uploads_dir, role_id)
    os.makedirs(role_upload_folder, exist_ok=True)
    # Clear any existing files in the upload folder
    for existing_file in os.listdir(role_upload_folder):
        file_path = os.path.join(role_upload_folder, existing_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            logger.error(f"Error clearing role {role_id} upload folder: {e}")
            raise

    # Generate filename as "jd" with original extension
    original_extension = Path(file.filename).suffix
    safe_filename = f"jd{original_extension}"

    # Save the file in the unique folder
    file_path = os.path.join(role_upload_folder, safe_filename)
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Add to processing queue
    role_profile_manager.add_role_profile(role_id, file_path, user_id)
    jd_processor.add_jd_to_queue(role_id, file_path)

    return {
        "id": role_id,
        "original_filename": file.filename,
        "saved_filename": safe_filename,
        "status": "processing",
    }
