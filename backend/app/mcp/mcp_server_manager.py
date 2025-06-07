"""
MCP Server Manager

This module initializes and manages the MCP server for VerseMind-RAG.
It provides functions to start and stop the server.
"""

import threading
import logging
from typing import Dict, Any

# Set up logging
logger = logging.getLogger(__name__)

# Global server instance
mcp_server_thread = None
mcp_server_instance = None

# Global data for VerseMind-RAG
versemind_data = {
    "title": None,
    "reference": None,
    "knowledge_bases": {},
    "last_updated": None,
}


def start_mcp_server(port: int = 3005, host: str = "0.0.0.0") -> bool:
    """Start the MCP server in a separate thread.

    Args:
        port: Port to run the MCP server on.
        host: Host to bind the MCP server to.

    Returns:
        bool: True if server was started successfully, False otherwise.
    """
    from app.mcp.versemind_mcp_service import VersemindMCPService

    global mcp_server_thread
    global mcp_server_instance

    if mcp_server_thread and mcp_server_thread.is_alive():
        logger.warning("MCP server is already running")
        return False

    def run_server():
        """Run the MCP server in a thread."""
        # Create the service instance
        service = VersemindMCPService()
        global mcp_server_instance
        mcp_server_instance = service

        # Configure the server settings
        service.mcp.settings.host = host
        service.mcp.settings.port = port

        # Log available tools
        tools = service.mcp._tool_manager.list_tools()
        logger.info(f"MCP Server configured with {len(tools)} tools:")
        for tool in tools:
            logger.info(f"  - {tool.name}: {tool.description}")

        logger.info(f"Starting MCP server on http://{host}:{port}/mcp")
        # Start the server
        try:
            # Patch for uvicorn logging issue with sys.stdout not having isatty
            import uvicorn.logging

            # Create a patched formatter class that doesn't check isatty
            original_init = uvicorn.logging.ColourizedFormatter.__init__

            def patched_init(self, *args, **kwargs):
                kwargs["use_colors"] = False  # Force disable colors
                if "fmt" not in kwargs and not args:
                    kwargs["fmt"] = "%(levelprefix)s %(message)s"
                original_init(self, *args, **kwargs)

            # Apply the patch
            uvicorn.logging.ColourizedFormatter.__init__ = patched_init

            # Run the MCP server
            service.mcp.run(transport="streamable-http")
        except Exception as e:
            logger.error(f"Error in MCP server: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())

    try:
        # Start the server in a separate thread
        logger.info(f"Starting MCP server thread on port {port}...")
        mcp_server_thread = threading.Thread(target=run_server)
        mcp_server_thread.daemon = (
            True  # Allow the thread to be terminated when the main process exits
        )
        mcp_server_thread.start()
        logger.info("MCP server thread started")
        return True
    except Exception as e:
        logger.error(f"Failed to start MCP server: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return False


def stop_mcp_server() -> bool:
    """Stop the MCP server if it's running.

    Returns:
        bool: True if server was stopped successfully, False otherwise.
    """
    global mcp_server_thread
    global mcp_server_instance

    if not mcp_server_thread or not mcp_server_thread.is_alive():
        logger.warning("MCP server is not running")
        return False

    try:
        logger.info("Stopping MCP server...")
        # In a more complete implementation, we would have a way to signal
        # the server to shut down gracefully. For now, we'll rely on the
        # daemon flag to terminate the thread when the main process exits.

        # Signal could be implemented with a stop flag in the server instance
        if mcp_server_instance and hasattr(mcp_server_instance.mcp, "stop"):
            mcp_server_instance.mcp.stop()

        # Mark as stopped
        mcp_server_thread = None
        mcp_server_instance = None
        logger.info("MCP server stopped")
        return True
    except Exception as e:
        logger.error(f"Error stopping MCP server: {str(e)}")
        return False


def set_versemind_data(
    title: str, reference: str, kb_id: str = None, metadata: Dict[str, Any] = None
) -> bool:
    """Set VerseMind data (title and reference) for the MCP service.

    This function updates the global VerseMind data state and
    propagates updates to the MCP service instance.

    Args:
        title: The title of the current document.
        reference: The reference content of the current document.
        kb_id: Optional knowledge base ID associated with this data.
        metadata: Optional metadata about the data (source, timestamp, etc).

    Returns:
        bool: True if data was set successfully, False otherwise.
    """
    try:
        import datetime

        # Update global versemind data object
        global versemind_data
        versemind_data["title"] = title
        versemind_data["reference"] = reference
        versemind_data["last_updated"] = datetime.datetime.now().isoformat()

        # Store in knowledge base if ID provided
        if kb_id:
            versemind_data["knowledge_bases"][kb_id] = {
                "title": title,
                "content": reference,
                "metadata": metadata or {},
            }

        # Set global variables in the main module for backward compatibility
        import __main__

        __main__.title = title
        __main__.reference = reference

        # Also update in the server instance if it exists
        global mcp_server_instance
        if mcp_server_instance:
            mcp_server_instance.title = title
            mcp_server_instance.reference = reference
            # If we had added knowledge base management to the service
            # we would update that here too

        logger.info(
            f"Set VerseMind data: title='{title}' and reference data of length {len(reference)}"
        )
        return True
    except Exception as e:
        logger.error(f"Error setting VerseMind data: {str(e)}")
        return False


def get_versemind_data() -> Dict[str, Any]:
    """Get the current VerseMind data from the MCP service.

    Returns:
        Dict containing title, reference data, and other RAG information.
    """
    try:
        global versemind_data

        # Try to get from server instance first
        global mcp_server_instance
        if mcp_server_instance:
            data = {
                "title": mcp_server_instance.title,
                "reference": mcp_server_instance.reference,
                "last_updated": versemind_data.get("last_updated"),
                "knowledge_bases": versemind_data.get("knowledge_bases", {}),
            }

            # Add system information
            try:
                # Try to get list of available knowledge bases
                if hasattr(mcp_server_instance, "_get_knowledge_bases"):
                    data["available_knowledge_bases"] = (
                        mcp_server_instance._get_knowledge_bases()
                    )
            except Exception:
                # Ignore errors in enhancement data
                pass

            return data

        # Fallback to global versemind data
        if versemind_data.get("title") is not None:
            return versemind_data

        # Last resort: try main module
        import __main__

        return {
            "title": getattr(__main__, "title", None),
            "reference": getattr(__main__, "reference", None),
            "last_updated": None,
        }
    except Exception as e:
        logger.error(f"Error getting VerseMind data: {str(e)}")
        return {"title": None, "reference": None, "error": str(e)}
