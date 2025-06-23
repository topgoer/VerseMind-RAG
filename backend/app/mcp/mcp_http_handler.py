#!/usr/bin/env python3

"""
Fixed HTTP Server for VerseMind-RAG MCP

This script implements a fixed HTTP server for the MCP protocol that uses
a singleton pattern to maintain a single server instance with registered tools.
"""

import os
import sys
import asyncio
import logging
import http.server
import socketserver
import json
from threading import Thread
from mcp.types import CallToolResult, TextContent

CONTENT_TYPE_JSON = "application/json"

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add the backend directory to the Python path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

try:
    # Import the fixed MCP server with the singleton pattern
    from app.mcp.versemind_native_mcp import (
        get_global_server,
    )  # MODIFIED_LINE to versemind_native_mcp

    logger.info("Successfully imported fixed MCP Server with singleton pattern")
except ImportError as e:
    logger.error(f"Failed to import fixed MCP Server: {e}")
    sys.exit(1)


def _serialize_tool_result(tool_result):
    """Convert CallToolResult or plain result into JSON-serializable dict."""
    if isinstance(tool_result, CallToolResult):
        serialized = []
        for item in tool_result.content:
            if isinstance(item, TextContent):
                serialized.append({"type": item.type, "text": item.text})
            else:
                serialized.append(item)
        return {"content": serialized}
    return tool_result


class MCPHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for MCP requests"""

    def _set_cors_headers(self):
        """Set CORS headers"""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        """Handle OPTIONS requests (CORS preflight)"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_POST(self):
        """Handle POST requests"""
        if self.path != "/mcp":
            self.send_response(404)
            self.send_header("Content-Type", CONTENT_TYPE_JSON)
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))
            return

        content_length = int(self.headers.get("Content-Length", 0))
        request_body = self.rfile.read(content_length).decode("utf-8")

        try:
            # Parse the JSON-RPC request
            request = json.loads(request_body)
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")

            # Process the method
            if method == "initialize":
                result = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "capabilities": {
                            "toolCallsSupported": True,
                            "streamingSupported": True,
                        },
                        "serverInfo": {"name": "versemind-rag", "version": "1.0.0"},
                    },
                }
            elif method == "listTools":  # Matches backup's handler
                server = get_global_server()
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                tool_attrs = loop.run_until_complete(server.get_tools())
                loop.close()
                result = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": tool_attrs},
                }
            elif method == "callTool":
                logger.debug(f"callTool: received raw params: {json.dumps(params)}")
                # Try to get tool_name from "toolName" first, then fall back to "name"
                tool_name = params.get("toolName")
                if not tool_name:
                    tool_name = params.get("name") # Fallback to "name"
                
                tool_args = params.get("arguments", {})

                if not tool_name:
                    logger.error("callTool: 'toolName' or 'name' is missing or empty in request params.") # Updated log message
                    result = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32602, "message": "Invalid params: 'toolName' or 'name' is missing or empty in request."}, # Updated error message
                    }
                else:
                    logger.debug(f"callTool: extracted tool_name: '{tool_name}', tool_args: {json.dumps(tool_args)}")
                    server = get_global_server()
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    # This is the direct result from VerseMindMCPServer.callTool
                    # It can be a CallToolResult object on success, or a dict like {"error": "message"} on failure.
                    raw_tool_result = loop.run_until_complete(
                        server.callTool(tool_name, tool_args)
                    )
                    loop.close()

                    if isinstance(raw_tool_result, dict) and "error" in raw_tool_result:
                        # Handle errors returned by server.callTool (e.g., tool not found, execution error)
                        error_message = raw_tool_result.get("error", "Unknown server error during tool execution.")
                        logger.error(f"callTool: Error from server.callTool for '{tool_name}': {error_message}")
                        result = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {"code": -32000, "message": error_message}, # Generic server error for tool issues
                        }
                    elif isinstance(raw_tool_result, CallToolResult):
                        # Successful tool execution
                        tool_body = _serialize_tool_result(raw_tool_result)
                        result = {"jsonrpc": "2.0", "id": request_id, "result": tool_body}
                    else:
                        # Unexpected result type from server.callTool
                        logger.error(f"callTool: Unexpected result type from server.callTool for '{tool_name}': {type(raw_tool_result)}")
                        result = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {"code": -32000, "message": "Internal server error: Unexpected tool result type."},
                        }
            else:
                result = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method {method} not found"},
                }

            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_JSON)
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))

        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            self.send_response(500)
            self.send_header("Content-Type", CONTENT_TYPE_JSON)
            self._set_cors_headers()
            self.end_headers()
            error_result = {
                "jsonrpc": "2.0",
                "id": request.get("id") if "request" in locals() else None,
                "error": {"code": -32000, "message": str(e)},
            }
            self.wfile.write(json.dumps(error_result).encode("utf-8"))


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Thread-per-connection HTTP server"""

    pass


def _mcp_http_handler_factory(*args, **kwargs):
    return MCPHTTPRequestHandler(*args, **kwargs)


def run_mcp_http_server(host="0.0.0.0", port=3006):
    """Run the MCP HTTP server"""
    handler = _mcp_http_handler_factory
    server = ThreadedHTTPServer((host, port), handler)
    logger.info(f"Starting Fixed MCP HTTP server on http://{host}:{port}/mcp")
    get_global_server()  # Initialize server instance
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping MCP HTTP server...")
    finally:
        server.server_close()
        logger.info("MCP HTTP server stopped")


def start_server_thread(host="0.0.0.0", port=3006):
    """Start the MCP HTTP server in a separate thread"""
    server_thread = Thread(target=run_mcp_http_server, args=(host, port), daemon=True)
    server_thread.start()
    logger.info(
        f"MCP HTTP server thread started, listening on {host}:{port}"
    )  # Added log
    return server_thread


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fixed VerseMind-RAG MCP HTTP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=3006, help="Port to listen on")
    args = parser.parse_args()
    run_mcp_http_server(args.host, args.port)
