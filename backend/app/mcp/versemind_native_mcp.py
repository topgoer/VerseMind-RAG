#!/usr/bin/env python3

"""
VerseMind-RAG Native Python MCP Server
Integrated with the backend services using official MCP SDK
Refactored to reduce cognitive complexity
"""

import sys
import json
import asyncio
import logging
import os
import requests
from typing import Any, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    from mcp.server.stdio import stdio_server
    from mcp.server import Server
    from mcp.types import TextContent, CallToolResult

    logger.info("Successfully imported MCP SDK components")
except ImportError as e:
    logger.error(f"Failed to import MCP SDK: {e}")
    logger.error("Please install the MCP SDK: pip install mcp>=1.9.0")
    sys.exit(1)


class VerseMindMCPServer:
    """Native Python MCP Server for VerseMind-RAG integrated with backend"""

    def __init__(self):
        self.api_base = os.getenv("VERSEMIND_API_BASE", "http://localhost:8000/api")
        self.server = Server("versemind-rag-python")
        self.setup_tools()
        logger.info(f"VerseMind MCP Server initialized with API base: {self.api_base}")

    def setup_tools(self):
        """Set up all available tools - reduced cognitive complexity by delegation"""
        self._setup_search_tools()
        self._setup_document_tools()
        self._setup_system_tools()

    def _setup_search_tools(self):
        """Set up search-related tools"""

        @self.server.call_tool()
        async def get_versemind_data(arguments: Dict[str, Any]) -> CallToolResult:
            """Get data from VerseMind-RAG system"""
            try:
                query = arguments.get("query", "VerseMind")
                index_id_or_collection = arguments.get(
                    "index_id_or_collection", "default"
                )

                response = requests.post(
                    f"{self.api_base}/search/",
                    json={
                        "index_id_or_collection": index_id_or_collection,
                        "query": query,
                        "top_k": 3,
                        "similarity_threshold": 0.3,
                    },
                    timeout=30,
                )
                data = response.json()

                result = {
                    "status": "success",
                    "query": query,
                    "index_id_or_collection": index_id_or_collection,
                    "results": data.get("results", []),
                    "count": len(data.get("results", [])),
                }

                return CallToolResult(
                    content=[
                        TextContent(type="text", text=json.dumps(result, indent=2))
                    ]
                )

            except Exception as e:
                error_result = {
                    "status": "error",
                    "message": f"Search failed: {str(e)}",
                }
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text", text=json.dumps(error_result, indent=2)
                        )
                    ]
                )

        @self.server.call_tool()
        async def search_documents(arguments: Dict[str, Any]) -> CallToolResult:
            """Search through documents using vector similarity"""
            try:
                index_id_or_collection = arguments.get("index_id_or_collection")
                query = arguments.get("query")
                top_k = arguments.get("top_k", 3)
                similarity_threshold = arguments.get("similarity_threshold", 0.5)

                if not index_id_or_collection or not query:
                    raise ValueError("index_id_or_collection and query are required")

                response = requests.post(
                    f"{self.api_base}/search/",
                    json={
                        "index_id_or_collection": index_id_or_collection,
                        "query": query,
                        "top_k": top_k,
                        "similarity_threshold": similarity_threshold,
                    },
                    timeout=30,
                )
                data = response.json()

                result = {
                    "status": "success",
                    "index_id_or_collection": index_id_or_collection,
                    "query": query,
                    "results": data.get("results", []),
                    "count": len(data.get("results", [])),
                }

                return CallToolResult(
                    content=[
                        TextContent(type="text", text=json.dumps(result, indent=2))
                    ]
                )

            except Exception as e:
                error_result = {
                    "status": "error",
                    "message": f"Document search failed: {str(e)}",
                }
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text", text=json.dumps(error_result, indent=2)
                        )
                    ]
                )

    def _setup_document_tools(self):
        """Set up document management tools"""

        @self.server.call_tool()
        async def list_documents(arguments: Dict[str, Any]) -> CallToolResult:
            """List all uploaded documents"""
            try:
                response = requests.get(f"{self.api_base}/documents/list", timeout=30)
                data = response.json()

                result = {
                    "status": "success",
                    "documents": data,
                    "count": len(data) if isinstance(data, list) else 0,
                }

                return CallToolResult(
                    content=[
                        TextContent(type="text", text=json.dumps(result, indent=2))
                    ]
                )

            except Exception as e:
                error_result = {
                    "status": "error",
                    "message": f"Failed to list documents: {str(e)}",
                }
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text", text=json.dumps(error_result, indent=2)
                        )
                    ]
                )

        @self.server.call_tool()
        async def get_document_info(arguments: Dict[str, Any]) -> CallToolResult:
            """Get information about a specific document"""
            try:
                document_id = arguments.get("document_id")
                if not document_id:
                    raise ValueError("document_id is required")

                response = requests.get(
                    f"{self.api_base}/documents/{document_id}", timeout=30
                )
                data = response.json()

                result = {"status": "success", "document": data}

                return CallToolResult(
                    content=[
                        TextContent(type="text", text=json.dumps(result, indent=2))
                    ]
                )

            except Exception as e:
                error_result = {
                    "status": "error",
                    "message": f"Failed to get document info: {str(e)}",
                }
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text", text=json.dumps(error_result, indent=2)
                        )
                    ]
                )

    def _setup_system_tools(self):
        """Set up system management tools"""
        self._setup_index_tools()
        self._setup_model_tools()
        self._setup_connection_tools()

    def _setup_index_tools(self):
        """Set up index management tools"""

        @self.server.call_tool()
        async def list_indices(arguments: Dict[str, Any]) -> CallToolResult:
            """List all available vector indices"""
            try:
                document_id = arguments.get("document_id")
                url = f"{self.api_base}/indices/list"
                if document_id:
                    url += f"?document_id={document_id}"

                response = requests.get(url, timeout=30)
                data = response.json()

                result = {
                    "status": "success",
                    "indices": data,
                    "count": len(data) if isinstance(data, list) else 0,
                }

                return CallToolResult(
                    content=[
                        TextContent(type="text", text=json.dumps(result, indent=2))
                    ]
                )

            except Exception as e:
                error_result = {
                    "status": "error",
                    "message": f"Failed to list indices: {str(e)}",
                }
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text", text=json.dumps(error_result, indent=2)
                        )
                    ]
                )

    def _setup_model_tools(self):
        """Set up model management tools"""

        @self.server.call_tool()
        async def list_embedding_models(arguments: Dict[str, Any]) -> CallToolResult:
            """List all available embedding models"""
            try:
                response = requests.get(
                    f"{self.api_base}/embeddings/models", timeout=30
                )
                data = response.json()

                result = {
                    "status": "success",
                    "embedding_models": data,
                    "providers": list(data.keys()) if isinstance(data, dict) else [],
                }

                return CallToolResult(
                    content=[
                        TextContent(type="text", text=json.dumps(result, indent=2))
                    ]
                )

            except Exception as e:
                error_result = {
                    "status": "error",
                    "message": f"Failed to list embedding models: {str(e)}",
                }
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text", text=json.dumps(error_result, indent=2)
                        )
                    ]
                )

        @self.server.call_tool()
        async def list_generation_models(arguments: Dict[str, Any]) -> CallToolResult:
            """List all available text generation models"""
            try:
                response = requests.get(f"{self.api_base}/generate/models", timeout=30)
                data = response.json()

                result = {
                    "status": "success",
                    "generation_models": data,
                    "providers": list(data.keys()) if isinstance(data, dict) else [],
                }

                return CallToolResult(
                    content=[
                        TextContent(type="text", text=json.dumps(result, indent=2))
                    ]
                )

            except Exception as e:
                error_result = {
                    "status": "error",
                    "message": f"Failed to list generation models: {str(e)}",
                }
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text", text=json.dumps(error_result, indent=2)
                        )
                    ]
                )

    def _setup_connection_tools(self):
        """Set up connection testing tools"""

        @self.server.call_tool()
        async def test_connection(arguments: Dict[str, Any]) -> CallToolResult:
            """Test if the MCP bridge is working"""
            result = {
                "status": "success",
                "message": "VerseMind MCP bridge is working!",
                "server": "versemind-rag-python",
                "version": "1.0.0",
            }
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, indent=2))]
            )

        @self.server.call_tool()
        async def ping_backend(arguments: Dict[str, Any]) -> CallToolResult:
            """Ping the VerseMind-RAG backend"""
            try:
                response = requests.get(f"{self.api_base}/health/", timeout=30)
                data = response.json()

                result = {
                    "status": "success",
                    "backend_status": data.get("status"),
                    "backend_message": data.get("message"),
                    "api_version": data.get("api_version", "unknown"),
                }

                return CallToolResult(
                    content=[
                        TextContent(type="text", text=json.dumps(result, indent=2))
                    ]
                )

            except Exception as e:
                error_result = {
                    "status": "error",
                    "message": f"Backend unreachable: {str(e)}",
                }
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text", text=json.dumps(error_result, indent=2)
                        )
                    ]
                )

    async def run_stdio(self):
        """Run the MCP server with stdio transport for Cherry Studio compatibility"""
        try:
            logger.info("Starting VerseMind-RAG Python MCP Server on stdio")
            # Use the official MCP stdio server pattern
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options(),
                )
        except Exception as e:
            logger.error(f"Error running MCP server: {e}")
            raise


async def main():
    """Main entry point for standalone stdio server"""
    server = VerseMindMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    # This allows the script to be run directly for Cherry Studio
    asyncio.run(main())
