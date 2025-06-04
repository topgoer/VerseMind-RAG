"""
MCP API router for VerseMind-RAG.

This module provides API endpoints to interact with the MCP server
and VerseMind data.
"""

import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional

from app.mcp import start_mcp_server, stop_mcp_server, set_versemind_data, get_versemind_data

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Models for API requests and responses
class VerseMindDataRequest(BaseModel):
    title: Optional[str] = None
    reference: Optional[str] = None

class VerseMindDataResponse(BaseModel):
    success: bool
    title: Optional[str] = None
    reference: Optional[str] = None
    error: Optional[str] = None

class MCPServerStatusResponse(BaseModel):
    success: bool
    running: bool
    error: Optional[str] = None

class MCPServerStartRequest(BaseModel):
    port: int = 3005
    host: str = "0.0.0.0"


@router.get("/mcp/status", response_model=MCPServerStatusResponse)
def get_mcp_status():
    """Get the status of the MCP server."""
    try:
        from app.mcp.mcp_server_manager import mcp_server_thread
        running = mcp_server_thread is not None and mcp_server_thread.is_alive()
        return {
            "success": True,
            "running": running
        }
    except Exception as e:
        logger.error(f"Error getting MCP server status: {e}")
        return {
            "success": False,
            "running": False,
            "error": str(e)
        }


@router.post("/mcp/start", response_model=MCPServerStatusResponse)
def start_mcp(request: MCPServerStartRequest, background_tasks: BackgroundTasks):
    """Start the MCP server."""
    try:
        # Check if MCP server is already running
        from app.mcp.mcp_server_manager import mcp_server_thread
        already_running = mcp_server_thread is not None and mcp_server_thread.is_alive()
        
        if already_running:
            return {
                "success": True,
                "running": True
            }
        
        # Start the MCP server in a background task
        def start_server():
            success = start_mcp_server(port=request.port, host=request.host)
            if not success:
                logger.error("Failed to start MCP server in background task")
        
        background_tasks.add_task(start_server)
        
        return {
            "success": True,
            "running": True
        }
    except Exception as e:
        logger.error(f"Error starting MCP server: {e}")
        return {
            "success": False,
            "running": False,
            "error": str(e)
        }


@router.post("/mcp/stop", response_model=MCPServerStatusResponse)
def stop_mcp():
    """Stop the MCP server."""
    try:
        success = stop_mcp_server()
        return {
            "success": success,
            "running": False if success else True
        }
    except Exception as e:
        logger.error(f"Error stopping MCP server: {e}")
        return {
            "success": False,
            "running": True,
            "error": str(e)
        }


@router.get("/mcp/data", response_model=VerseMindDataResponse)
def get_data():
    """Get the current VerseMind data."""
    try:
        data = get_versemind_data()
        return {
            "success": True,
            "title": data.get("title"),
            "reference": data.get("reference")
        }
    except Exception as e:
        logger.error(f"Error getting VerseMind data: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/mcp/data", response_model=VerseMindDataResponse)
def set_data(request: VerseMindDataRequest):
    """Set VerseMind data (title and reference)."""
    try:
        if request.title is None and request.reference is None:
            raise HTTPException(status_code=400, detail="Either title or reference must be provided")
        
        # Get current data to preserve fields not being updated
        current_data = get_versemind_data()
        title = request.title if request.title is not None else current_data.get("title")
        reference = request.reference if request.reference is not None else current_data.get("reference")
        
        success = set_versemind_data(title=title, reference=reference)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to set VerseMind data")
        
        return {
            "success": True,
            "title": title,
            "reference": reference
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error setting VerseMind data: {e}")
        return {
            "success": False,
            "error": str(e)
        }
