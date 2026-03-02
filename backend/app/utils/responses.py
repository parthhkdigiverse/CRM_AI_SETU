from typing import Any, Optional
from fastapi.responses import JSONResponse
from pydantic import BaseModel

class StandardResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None

def success_response(data: Any = None, status_code: int = 200) -> JSONResponse:
    """Returns a standardized success response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "data": data,
            "error": None
        }
    )

def error_response(message: str, status_code: int = 400, error_details: Any = None) -> JSONResponse:
    """Returns a standardized error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "data": error_details,
            "error": message
        }
    )
