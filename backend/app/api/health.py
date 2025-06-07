from fastapi import APIRouter
import os

router = APIRouter()

@router.get("/")
async def health_check():
    """
    Basic health check endpoint to verify API connectivity
    """
    indices_path = os.path.join("storage", "indices")
    indices_exists = os.path.exists(indices_path)

    # Report more details about the indices directory
    indices_details = {}
    if indices_exists:
        try:
            indices_files = os.listdir(indices_path)
            indices_details["file_count"] = len(indices_files)
            indices_details["files"] = indices_files[:5]  # Show first 5 files
        except Exception as e:
            indices_details["error"] = str(e)

    return {
        "status": "ok",
        "message": "API is running",
        "indices_dir": indices_path,
        "indices_dir_exists": indices_exists,
        "indices_details": indices_details,
        "api_version": "0.2.0"
    }
