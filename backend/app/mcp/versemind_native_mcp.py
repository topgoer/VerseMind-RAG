#!/usr/bin/env python3

"""
Fixed MCP Server for VerseMind-RAG

This module fixes the "No tools registered" error in the MCP server
by implementing a singleton pattern to reuse the same server instance.
"""

import os
import sys
import json
import asyncio
import time
import requests
from typing import Dict, Any

# Import the centralized logger
from app.core.logger import get_logger_with_env_level

# Initialize logger using the centralized function
logger = get_logger_with_env_level(__name__)

try:
    from mcp.server.stdio import stdio_server
    from mcp.server import Server
    from mcp.types import TextContent, CallToolResult

    logger.info("Successfully imported MCP SDK components")
except ImportError as e:
    logger.error(f"Failed to import MCP SDK: {e}")
    logger.error("Please install the MCP SDK: pip install mcp>=1.9.0")
    sys.exit(1)

# Global server instance (singleton)
_global_server_instance = None


def get_global_server():
    """Get or create the global server instance"""
    global _global_server_instance
    if _global_server_instance is None:
        logger.info("Creating new global MCP server instance")
        _global_server_instance = VerseMindMCPServer()
    else:
        logger.info("Reusing existing global MCP server instance")
    return _global_server_instance


class VerseMindMCPServer:
    """Fixed native Python MCP Server for VerseMind-RAG with proper tool registration"""

    def __init__(self):
        self.api_base = os.getenv("VERSEMIND_API_BASE", "http://localhost:8200/api")
        logger.info(f"VerseMind MCP Server initializing with API base: {self.api_base}")
        self.server = Server("versemind-rag-python")
        # map of tool names to their async functions
        self._tool_funcs: Dict[str, Any] = {}

        # Debug info about server instance
        logger.debug(f"DEBUG: Server instance created with ID: {id(self.server)}")
        logger.debug(f"DEBUG: Server type: {type(self.server)}")
        logger.debug(f"DEBUG: Server dir: {dir(self.server)}")
        logger.debug(
            f"DEBUG: Server has _tools attribute: {hasattr(self.server, '_tools')}"
        )
        logger.debug(
            f"DEBUG: Server has call_tool method: {hasattr(self.server, 'call_tool')}"
        )

        # Setup tools
        self.setup_tools()

        # Debug info after setup - newer MCP SDK doesn't expose _tools directly
        # but tools are still registered via decorators
        logger.info("Tools registered via @server.call_tool() decorators")
        logger.info("MCP SDK handles tool registration internally")

        logger.info("VerseMind MCP Server initialization complete")

    def setup_tools(self):
        """Set up all available tools"""
        logger.info("Registering tools...")

        # Setup all tools
        self._setup_search_tools()
        self._setup_document_tools()
        self._setup_model_tools()
        self._setup_index_tools()
        self._setup_connection_tools()
        self._setup_query_with_llm_tool()  # Add this line

    def _setup_model_tools(self):
        """Set up model-related tools"""
        logger.debug("Setting up model tools...")
        logger.debug(
            f"DEBUG: About to register list_generation_models, server type: {type(self.server)}"
        )
        logger.debug(
            f"DEBUG: Server has call_tool method: {hasattr(self.server, 'call_tool')}"
        )

        try:

            @self.server.call_tool()
            async def list_generation_models(
                arguments: Dict[str, Any],
            ) -> CallToolResult:
                """List all available text generation models"""
                logger.debug(
                    f"list_generation_models called with arguments: {arguments}"
                )
                try:
                    response = requests.get(
                        f"{self.api_base}/generate/models", timeout=30
                    )
                    data = response.json()

                    result = {
                        "status": "success",
                        "generation_models": data,
                        "providers": list(data.keys())
                        if isinstance(data, dict)
                        else [],
                    }

                    logger.debug(f"list_generation_models result: {result}")
                    return CallToolResult(
                        content=[
                            TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))
                        ]
                    )
                except Exception as e:
                    logger.error(f"Error in list_generation_models: {e}")
                    error_result = {
                        "status": "error",
                        "message": f"Failed to list generation models: {str(e)}",
                    }
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text", text=json.dumps(error_result, indent=2, ensure_ascii=False)
                            )
                        ]
                    )

            logger.debug("DEBUG: list_generation_models registration completed")
            # track tool for direct invocation
            self._tool_funcs["list_generation_models"] = list_generation_models
            logger.debug(
                f"DEBUG: Server _tools after registration: {hasattr(self.server, '_tools')}"
            )
            if hasattr(self.server, "_tools"):
                logger.debug(f"DEBUG: Tools now: {list(self.server._tools.keys())}")

        except Exception as e:
            logger.error(f"ERROR: Failed to register list_generation_models: {e}")
            logger.error(f"ERROR: Exception type: {type(e)}")

        try:

            @self.server.call_tool()
            async def list_embedding_models(
                arguments: Dict[str, Any],
            ) -> CallToolResult:
                """List all available embedding models"""
                try:
                    response = requests.get(
                        f"{self.api_base}/embeddings/models", timeout=30
                    )
                    data = response.json()

                    result = {
                        "status": "success",
                        "embedding_models": data,
                        "providers": list(data.keys())
                        if isinstance(data, dict)
                        else [],
                    }

                    return CallToolResult(
                        content=[
                            TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))
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
                                type="text", text=json.dumps(error_result, indent=2, ensure_ascii=False)
                            )
                        ]
                    )

            logger.debug("DEBUG: list_embedding_models registration completed")
            # track tool for direct invocation
            self._tool_funcs["list_embedding_models"] = list_embedding_models

        except Exception as e:
            logger.error(f"ERROR: Failed to register list_embedding_models: {e}")

    def _setup_index_tools(self):
        """Set up index-related tools"""
        logger.debug("Setting up index tools...")

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
                        TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))
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
                            type="text", text=json.dumps(error_result, indent=2, ensure_ascii=False)
                        )
                    ]
                )

        self._tool_funcs["list_indices"] = list_indices # Add this line
        logger.info("list_indices tool registered for custom dispatch.") # Optional: add a log

    def _setup_search_tools(self):
        """Set up search-related tools"""
        logger.debug("Setting up search tools...")

        @self.server.call_tool()
        async def search_documents(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Search through documents using vector similarity.

            Args:
                arguments (Dict[str, Any]): A dictionary of arguments. Expected keys:
                    query (str): The search query.
                    index_id_or_collection (str, optional): Specifies the search scope.
                        - To search within a specific document: "doc:<document_id>"
                        - To search within a specific collection/index: "col:<collection_name>"
                        - For global search or to use the default index: "default" or omit.
                        Defaults to "default".
                    top_k (int, optional): Number of results to retrieve. Defaults to 3.
                    similarity_threshold (float, optional): Minimum similarity for results. Defaults to 0.5.
            """
            try:
                query = arguments.get("query", "")
                index_id_or_collection = arguments.get(
                    "index_id_or_collection", "default"
                )
                top_k = arguments.get("top_k", 3)
                similarity_threshold = arguments.get("similarity_threshold", 0.5)

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
                    "query": query,
                    "results": data.get("results", []),
                    "count": len(data.get("results", [])),
                }

                return CallToolResult(
                    content=[
                        TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))
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
                            type="text", text=json.dumps(error_result, indent=2, ensure_ascii=False)
                        )
                    ]
                )

        # track tool for direct invocation
        self._tool_funcs["search_documents"] = search_documents

    def _setup_document_tools(self):
        """Set up document-related tools"""
        logger.debug("Setting up document tools...")

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
                        TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))
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
                            type="text", text=json.dumps(error_result, indent=2, ensure_ascii=False)
                        )
                    ]
                )

        # track tool for direct invocation
        self._tool_funcs["list_documents"] = list_documents

        @self.server.call_tool()
        async def get_document_info(arguments: Dict[str, Any]) -> CallToolResult:
            """Get detailed information about a specific document"""
            try:
                document_id = arguments.get("document_id")
                if not document_id:
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text=json.dumps(
                                    {"status": "error", "message": "document_id is required."},
                                    indent=2,
                                    ensure_ascii=False,
                                ),
                            )
                        ]
                    )

                response = requests.get(
                    f"{self.api_base}/documents/info/{document_id}", timeout=30
                )
                data = response.json()

                if response.status_code != 200:
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text=json.dumps(
                                    {"status": "error", "message": data.get("message", "Unknown error")},
                                    indent=2,
                                    ensure_ascii=False,
                                ),
                            )
                        ]
                    )

                result = {
                    "status": "success",
                    "document": data,
                }

                return CallToolResult(
                    content=[
                        TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))
                    ]
                )
            except Exception as e:
                error_result = {
                    "status": "error",
                    "message": f"Failed to get document info: {str(e)}",
                }
                return CallToolResult(
                    content=[
                        TextContent(type="text", text=json.dumps(error_result, indent=2, ensure_ascii=False))
                    ]
                )

        # track tool for direct invocation
        self._tool_funcs["get_document_info"] = get_document_info

    def _setup_query_with_llm_tool(self):
        """Set up the tool to query knowledge base and generate answer with LLM."""
        logger.debug("Setting up query_knowledge_base_with_llm tool...")

        @self.server.call_tool()
        async def query_knowledge_base_with_llm(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Queries the knowledge base with a user's question, then uses the default LLM
            to generate an answer based on the search results.

            Args:
                arguments (Dict[str, Any]): A dictionary of arguments. Expected keys:
                    query (str): The user's question.
                    index_id_or_collection (str, optional): Specifies the search scope.
                        - To search within a specific document: "doc:<document_id>"
                        - To search within a specific collection/index: "col:<collection_name>"
                        - For global search or to use the default index: "default" or omit.
                        Defaults to "default".
                    top_k (int, optional): Number of results to retrieve. Defaults to 3.
                    similarity_threshold (float, optional): Minimum similarity for results. Defaults to 0.5.
            """
            try:
                user_query = arguments.get("query", "")
                index_id_or_collection = arguments.get("index_id_or_collection", "default")
                top_k = arguments.get("top_k", 3)
                similarity_threshold = arguments.get("similarity_threshold", 0.5)

                if not user_query:
                    return CallToolResult(
                        content=[
                            TextContent(type="text", text=json.dumps({"status": "error", "message": "Query cannot be empty."}, indent=2, ensure_ascii=False))
                        ]
                    )

                # Step 1: Search documents (reuse existing logic or call the search endpoint)
                logger.info(f"Searching documents for query: {user_query}")
                search_response = requests.post(
                    f"{self.api_base}/search/",
                    json={
                        "index_id_or_collection": index_id_or_collection,
                        "query": user_query,
                        "top_k": top_k,
                        "similarity_threshold": similarity_threshold,
                    },
                    timeout=30,
                )
                search_data = search_response.json()

                if search_response.status_code != 200 or search_data.get("status") == "error":
                    logger.error(f"Search failed: {search_data.get('message')}")
                    return CallToolResult(
                        content=[
                            TextContent(type="text", text=json.dumps({"status": "error", "message": f"Search failed: {search_data.get('message', 'Unknown error')}"}, indent=2, ensure_ascii=False))
                        ]
                    )

                search_results = search_data.get("results", [])
                context = "\n\n".join([result.get("text", "") for result in search_results])

                if not context:
                    logger.info("No relevant context found from search.")
                    # Optionally, you could still send the query to the LLM without context
                    # or return a message indicating no context was found.
                    # For now, let's proceed to LLM with the original query only if no context.

                # Step 2: Generate answer using LLM with context
                logger.info("Generating answer with LLM...")

                # Construct prompt for LLM
                # You might want to refine this prompt engineering
                prompt = f"Based on the following context, please answer the question.\n\nContext:\n{context}\n\nQuestion: {user_query}\n\nAnswer:"
                if not search_results: # If no context, just ask the question
                    prompt = f"Please answer the following question: {user_query}\n\nAnswer:"

                # Assuming a /api/generate/text endpoint similar to your other services
                # You might need to adjust the payload and endpoint based on your actual backend implementation
                generation_payload = {
                    "prompt": prompt,
                    "model_id": "default", # Or allow specifying model via arguments
                    "stream": False
                    # Add other parameters like max_tokens, temperature if needed
                }

                logger.debug(f"Sending to generation endpoint: {self.api_base}/generate/text with payload: {generation_payload}")
                generation_response = requests.post(
                    f"{self.api_base}/generate/text", # Adjust if your generation endpoint is different
                    json=generation_payload,
                    timeout=60, # Generation can take longer
                )
                generation_data = generation_response.json()

                if generation_response.status_code != 200:
                    logger.error(f"LLM generation failed: {generation_data.get('detail', 'Unknown error')}")
                    return CallToolResult(
                        content=[
                            TextContent(type="text", text=json.dumps({"status": "error", "message": f"LLM generation failed: {generation_data.get('detail', 'Unknown error')}"}, indent=2, ensure_ascii=False))
                        ]
                    )

                llm_answer = generation_data.get("text", "No answer generated.")

                final_result = {
                    "status": "success",
                    "user_query": user_query,
                    "retrieved_context_count": len(search_results),
                    "llm_answer": llm_answer,
                }

                return CallToolResult(
                    content=[
                        TextContent(type="text", text=json.dumps(final_result, indent=2, ensure_ascii=False))
                    ]
                )

            except Exception as e:
                logger.error(f"Error in query_knowledge_base_with_llm: {e}", exc_info=True)
                error_result = {
                    "status": "error",
                    "message": f"An unexpected error occurred: {str(e)}",
                }
                return CallToolResult(
                    content=[
                        TextContent(type="text", text=json.dumps(error_result, indent=2, ensure_ascii=False))
                    ]
                )

        self._tool_funcs["query_knowledge_base_with_llm"] = query_knowledge_base_with_llm
        logger.info("query_knowledge_base_with_llm tool registered.")

    def _setup_connection_tools(self):
        """Set up connection-related tools"""
        logger.debug("Setting up connection tools...")

        @self.server.call_tool()
        async def test_connection(arguments: Dict[str, Any]) -> CallToolResult:
            """Test connectivity to the VerseMind-RAG system"""
            try:
                result = {
                    "status": "success",
                    "message": "MCP server connection successful",
                    "api_base": self.api_base,
                    "timestamp": str(time.time()),
                }

                return CallToolResult(
                    content=[
                        TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))
                    ]
                )
            except Exception as e:
                error_result = {
                    "status": "error",
                    "message": f"Connection test failed: {str(e)}",
                }
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text", text=json.dumps(error_result, indent=2, ensure_ascii=False)
                        )
                    ]
                )

        # track tool for direct invocation
        self._tool_funcs["test_connection"] = test_connection

    async def get_tools(self):
        """Get all registered tools"""
        # With newer MCP SDK, we can't access _tools directly
        # but tools are registered via @server.call_tool() decorators
        tools = [
            {
                "name": "list_generation_models",
                "description": "List all available text generation models",
            },
            {
                "name": "list_embedding_models",
                "description": "List all available embedding models",
            },
            {
                "name": "list_indices",
                "description": "List all available vector indices",
            },
            {
                "name": "search_documents",
                "description": "Search documents by vector similarity (scope: doc:<id>/col:<name>/default).",
            },
            {"name": "list_documents", "description": "List all uploaded documents"},
            {
                "name": "get_document_info",
                "description": "Get detailed information about a specific document",
            },
            {
                "name": "test_connection",
                "description": "Test connectivity to the VerseMind-RAG system",
            },
            {
                "name": "query_knowledge_base_with_llm",
                "description": "Queries knowledge base (scope: doc:<id>/col:<name>/default) and uses LLM for answers.",
            },
        ]
        logger.info(f"Retrieved {len(tools)} tools (hardcoded list for newer MCP SDK)")
        return tools

    async def callTool(self, toolName: str, arguments: Dict[str, Any]): # type: ignore[override] # noqa: N802 # NOSONAR
        """Call a tool by name with arguments. Method name uses camelCase to match JSON-RPC spec from clients like n8n.
           Parameter 'toolName' uses camelCase for the same reason.
        """ # noqa: N803
        logger.info(f"Invoking tool {toolName} with arguments: {arguments}")
        func = self._tool_funcs.get(toolName)
        if not func:
            error = {"error": f"Tool '{toolName}' not found"}
            logger.error(error["error"])
            return error
        try:
            # The actual tool functions expect a dictionary named 'arguments'
            return await func(arguments)
        except Exception as e:
            logger.error(f"Error executing tool '{toolName}': {e}")
            return {"error": str(e)}

    async def run_stdio(self):
        """Run the MCP server with stdio transport"""
        try:
            logger.info("Starting VerseMind-RAG MCP Server on stdio")
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options(),
                )
        except Exception as e:
            logger.error(f"Error running MCP server: {e}")
            raise

    async def run_http(self, host="0.0.0.0", port=3006):
        """Run the MCP server with HTTP transport"""
        try:
            from mcp.server.streamable_http import streamable_http_server

            logger.info(f"Starting VerseMind-RAG MCP Server on HTTP: {host}:{port}/mcp")
            await streamable_http_server(
                self.server,
                host=host,
                port=port,
                path="/mcp",
                cors_origins=["*"],  # Allow all origins for testing
            )
        except ImportError:
            logger.error("Streamable HTTP server transport not available in MCP SDK")
            logger.error("You can install it with: pip install mcp>=1.9.0")
            raise
        except Exception as e:
            logger.error(f"Error running HTTP MCP server: {e}")
            raise


async def main():
    """Main entry point"""
    # Get the global server instance
    server = get_global_server()

    # Run the server
    await server.run_stdio()


if __name__ == "__main__":
    # This allows the script to be run directly
    asyncio.run(main())
