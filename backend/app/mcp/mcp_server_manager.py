"""
MCP Server Manager

This module initializes and manages the MCP server for VerseMind-RAG.
It provides functions to start and stop the server.
"""

import logging
from typing import Dict, Any

# Set up logging
logger = logging.getLogger(__name__)

# Global server instance
mcp_server_thread = None # This will be the thread for mcp_http_handler
mcp_server_instance = None # This will be the VerseMindMCPServer instance

# Global data for VerseMind-RAG
versemind_data = {
    "title": None,
    "reference": None,
    "knowledge_bases": {},
    "last_updated": None,
}


def start_mcp_server(port: int = 3006, host: str = "0.0.0.0") -> bool:
    """Start the MCP server in a separate thread.

    Args:
        port: Port to run the MCP server on.
        host: Host to bind the MCP server to.

    Returns:
        bool: True if server was started successfully, False otherwise.
    """
    # Import the new mcp_http_handler and the versemind_native_mcp server
    try:
        from app.mcp.versemind_native_mcp import get_global_server
        from app.mcp.mcp_http_handler import start_server_thread as start_http_server_thread
        logger.info("Successfully imported MCP components for http.server approach.")
    except ImportError as e:
        logger.error(f"Failed to import MCP components: {e}")
        return False

    global mcp_server_thread
    global mcp_server_instance

    if mcp_server_thread and mcp_server_thread.is_alive():
        logger.warning("MCP server (http_handler thread) is already running")
        return False

    try:
        # First, ensure the global VerseMindMCPServer instance is created or retrieved.
        # This is crucial because mcp_http_handler will use this shared instance.
        logger.info("Initializing/retrieving global VerseMindMCPServer instance...")
        server_instance = get_global_server()
        mcp_server_instance = server_instance # Store for global access if needed
        logger.info(f"VerseMindMCPServer instance {id(mcp_server_instance)} is ready.")
        logger.info("Tools should be registered by the VerseMindMCPServer upon its initialization.")

        # Now, start the mcp_http_handler, which will run its own HTTP server
        # and use the global_server_instance for handling MCP calls.
        logger.info(f"Starting MCP HTTP handler thread on http://{host}:{port}/mcp")
        # The mcp_http_handler.start_server_thread already creates and manages its own thread.
        # We just need to call it and store the thread if we want to manage it (e.g., for stopping).
        # The backup's start_server_thread in mcp_http_handler returns the thread.
        http_thread = start_http_server_thread(host, port)
        mcp_server_thread = http_thread # Store the thread from mcp_http_handler

        if mcp_server_thread and mcp_server_thread.is_alive():
            logger.info("MCP HTTP handler thread started successfully.")
            return True
        else:
            logger.error("MCP HTTP handler thread failed to start.")
            return False

    except Exception as e:
        logger.error(f"Failed to start MCP server: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def stop_mcp_server() -> bool:
    """Stop the MCP server if it's running."""
    global mcp_server_thread
    global mcp_server_instance
    # Import the mcp_http_handler's stop function
    try:
        from app.mcp.mcp_http_handler import stop_server as stop_http_server
    except ImportError:
        logger.error("Could not import stop_server from mcp_http_handler.")
        return False

    stopped_gracefully = False
    if mcp_server_thread and mcp_server_thread.is_alive():
        logger.info("Stopping MCP HTTP handler server...")
        try:
            stop_http_server() # Call the stop function from mcp_http_handler
            # The stop_server in http_handler should handle thread joining.
            logger.info("MCP HTTP handler server signaled to stop.")
            # Give it a moment to shut down
            if mcp_server_thread.is_alive():
                 mcp_server_thread.join(timeout=5) # Wait for thread from http_handler
            if not mcp_server_thread.is_alive():
                logger.info("MCP HTTP handler thread has terminated.")
                stopped_gracefully = True
            else:
                logger.warning("MCP HTTP handler thread did not terminate after stop signal.")
        except Exception as e:
            logger.error(f"Error stopping MCP HTTP handler: {e}")
    else:
        logger.warning("MCP server (http_handler thread) is not running or thread object unavailable.")
        # If thread is None but server might be running (e.g. after a restart),
        # we might not be able to stop it this way.

    # Reset global states
    mcp_server_thread = None
    # mcp_server_instance is managed by get_global_server, so we don't nullify it here
    # as it's a singleton that might be reused.
    if stopped_gracefully:
        logger.info("MCP server stopped successfully.")
        return True
    else:
        logger.warning("MCP server may not have stopped gracefully.")
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
        metadata: Optional metadata about the data (source, timestamp, etc)

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


        # Also update in the server instance if it exists - VerseMindMCPServer does not store this directly
        # global mcp_server_instance
        # if mcp_server_instance:
        #     mcp_server_instance.title = title
        #     mcp_server_instance.reference = reference
        #     # If we had added knowledge base management to the service
        #     # we would update that here too

        logger.info(
            f"Set VerseMind data: title='{title}' and reference data of length {len(reference if reference else [])}"
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

        # Try to get from server instance first - VerseMindMCPServer does not store this directly
        # global mcp_server_instance
        # if mcp_server_instance:
        #     data = {
        #         "title": mcp_server_instance.title,
        #         "reference": mcp_server_instance.reference,
        #         "last_updated": versemind_data.get("last_updated"),
        #         "knowledge_bases": versemind_data.get("knowledge_bases", {}),
        #     }

        #     # Add system information
        #     try:
        #         # Try to get list of available knowledge bases
        #         if hasattr(mcp_server_instance, "_get_knowledge_bases"):
        #             data["available_knowledge_bases"] = (
        #                 mcp_server_instance._get_knowledge_bases()
        #             )
        #     except Exception:
        #         # Ignore errors in enhancement data
        #         pass
        #
        #     return data

        # Fallback to global versemind data
        if versemind_data.get("title") is not None or versemind_data.get("reference") is not None:
            return versemind_data.copy() # Return a copy to prevent external modification

        # Last resort: try main module - Removing direct __main__ access as it's less reliable
        # import __main__
        #
        # return {
        #     "title": getattr(__main__, "title", None),
        #     "reference": getattr(__main__, "reference", None),
        #     "last_updated": None,
        #     "knowledge_bases": {},
        # }
        logger.warning("No VerseMind data available in mcp_server_manager.versemind_data")
        return {"title": None, "reference": None, "last_updated": None, "knowledge_bases": {}}
    except Exception as e:
        logger.error(f"Error getting VerseMind data: {str(e)}")
        return {"title": None, "reference": None, "error": str(e)}
