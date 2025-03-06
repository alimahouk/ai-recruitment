from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

from backend.app.config import logger
from backend.app.exceptions import UserExistsError
from backend.app.services.users.schemas import User, UserRole
from backend.app.services.users.user_manager import UserManager

router = APIRouter()

user_manager = UserManager.get_instance()
user_manager.bootstrap()


@router.post("/")
async def create_user(user: User):
    try:
        user_manager.add_user(user)
        return {"message": "User created successfully"}
    except UserExistsError as e:
        return JSONResponse(status_code=409, content={"error": str(e)})
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return JSONResponse(
            status_code=500, content={"error": "Internal server error"}
        )


@router.get("/{user_identifier}")
async def get_user(
    user_identifier: str,
    lookup_type: str = Query(
        default="id", description="Type of lookup to perform"
    ),
):
    try:
        if lookup_type == "email":
            logger.info(f"Looking up user by email '{user_identifier}'")
            user = user_manager.get_user_by_email(user_identifier)
        elif lookup_type == "phone_number":
            logger.info(f"Looking up user by phone number '{user_identifier}'")
            user = user_manager.get_user_by_phone(user_identifier)
        else:  # default to ID lookup
            logger.info(f"Looking up user by ID '{user_identifier}'")
            user = user_manager.get_user_by_id(user_identifier)

        if not user:
            logger.info(f"User not found for '{user_identifier}'")
            return JSONResponse(
                status_code=404, content={"error": "User not found"}
            )
        return user
    except Exception as e:
        logger.error(f"Error retrieving user: {e}")
        return JSONResponse(
            status_code=500, content={"error": "Internal server error"}
        )


@router.patch("/{user_id}/role")
async def update_user_role(user_id: str, role_data: dict = Body(...)):
    try:
        role = UserRole(role_data["role"])
        user = user_manager.get_user_by_id(user_id)
        if not user:
            return JSONResponse(
                status_code=404, content={"error": "User not found"}
            )

        user.role = role
        user_manager.update_user(user_id, user)
        return {"message": "User role updated successfully"}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        return JSONResponse(
            status_code=500, content={"error": "Internal server error"}
        )
