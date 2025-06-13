"""
VerseMind MCP Service

This module implements a simplified MCP-compatible service that exposes VerseMind-RAG functionalities
without external dependencies.

The service provides tools to interact with VerseMind-RAG's knowledge bases, search capabilities,
and text generation features.
"""

import os
import sys
import json
import traceback
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

# Set up logging
logger = logging.getLogger(__name__)


class ToolManager:
    """Tool manager for the SimpleMCPServer."""

    def __init__(self, server):
        self.server = server

    def list_tools(self):
        """List all registered tools."""
        return [
            type("Tool", (), {"name": name, "description": f"Tool: {name}"})()
            for name in self.server.tools.keys()
        ]


class SimpleMCPServer:
    """A simple MCP-like server implementation without external dependencies."""

    def __init__(self):
        self.tools = {}
        self.settings = type("Settings", (), {"host": "0.0.0.0", "port": 3006})()
        self._tool_manager = ToolManager(self)

    def register_tool(self, name: str, func: callable, description: str = ""):
        """Register a tool with the server."""
        self.tools[name] = {"func": func, "description": description}

    def run(self, transport="streamable-http"):
        """Mock run method that doesn't actually start a server."""
        logger.info(
            f"Mock MCP server would run on {self.settings.host}:{self.settings.port} with transport {transport}"
        )
        logger.info(f"Registered tools: {list(self.tools.keys())}")


def mcp_tool_with_error_handling(func):
    """Decorator that wraps MCP tool methods to handle errors."""

    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_msg = f"Error in {func.__name__}: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return {"success": False, "error": error_msg}

    return wrapper


class VersemindMCPService:
    """Mock VerseMind MCP Service that provides the same interface without external dependencies."""

    def __init__(self):
        """Initialize the VerseMind MCP service."""
        self.mcp = SimpleMCPServer()  # This will be replaced by the actual MCP server instance
        self.title = None
        self.reference = None

        # Attempt to load current context from global environment if available
        self._load_from_globals()

        # Path to document storage
        # Ensure this path is correct for your project structure
        self.storage_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../storage")
        )
        self.documents_dir = os.path.join(self.storage_dir, "documents")
        self.indices_dir = os.path.join(self.storage_dir, "indices")

        # Available models (would typically be loaded from config)
        self.models = {
            "ollama": ["llama3:8b", "codellama:7b", "mistral:7b"],
            "openai": ["gpt-3.5-turbo", "gpt-4o"],
            "deepseek": ["deepseek-chat", "deepseek-reasoner"],
        }

        self._register_tools()
        logger.info("VersemindMCPService initialized (using definitions from backup)")

    def _load_from_globals(self):
        """Load title and reference from globals if available."""
        try:
            # This attempts to access variables from the main script's scope
            # It might be more robust to pass data explicitly or use a shared context object
            main_module = sys.modules.get("__main__")
            if main_module:
                if hasattr(main_module, "title"):
                    self.title = main_module.title
                if hasattr(main_module, "reference"):
                    self.reference = main_module.reference

            if self.title or self.reference:
                logger.info(
                    f"Loaded VerseMind data from globals: title='{self.title}', reference length={len(self.reference) if self.reference else 0}"
                )
            else:
                logger.debug("No VerseMind data found in globals for MCP service.")
        except Exception as e:
            logger.error(f"Error loading from globals for MCP service: {e}")

    def _register_tools(self):
        """Register all available tools with the MCP server."""
        # The actual registration will happen with the real MCP server instance
        # This method defines what tools *should* be registered.
        tools_to_register = {
            "get_versemind_data": {"func": self.get_versemind_data, "description": "Get current VerseMind data (title and reference)"},
            "list_knowledge_bases": {"func": self.list_knowledge_bases, "description": "List available knowledge bases in VerseMind-RAG"},
            "get_knowledge_base_info": {"func": self.get_knowledge_base_info, "description": "Get detailed information about a specific knowledge base"},
            "search_knowledge_base": {"func": self.search_knowledge_base, "description": "Search in a specific or all knowledge bases"},
            "list_available_models": {"func": self.list_available_models, "description": "List available AI models configured in VerseMind-RAG"},
        }

        # This part is more conceptual for this file, actual registration is in mcp_server_manager
        for name, tool_info in tools_to_register.items():
            if hasattr(self.mcp, 'register_tool'): # Check if mcp object can register (it can, via SimpleMCPServer)
                 self.mcp.register_tool(name, tool_info['func'], tool_info['description'])
            else:
                logger.warning(f"MCP server object does not have 'register_tool' method. Tool '{name}' not registered here.")

    def _get_knowledge_bases(self) -> List[Dict[str, Any]]:
        """Get list of available knowledge bases from the documents directory."""
        knowledge_bases = []

        if not os.path.exists(self.documents_dir):
            logger.warning(f"Documents directory not found: {self.documents_dir}")
            return []

        try:
            for filename in os.listdir(self.documents_dir):
                # Consider more robust file type checking if needed
                if filename.lower().endswith((".pdf", ".txt", ".md", ".docx")):
                    kb_path = os.path.join(self.documents_dir, filename)
                    try:
                        kb_info = {
                            "id": Path(filename).stem,  # Use Pathlib for robust name extraction
                            "name": filename,
                            "file_type": Path(filename).suffix.lower(),
                            "size_bytes": os.path.getsize(kb_path),
                            "last_modified": os.path.getmtime(kb_path),  # Consider converting to ISO format string
                        }
                        knowledge_bases.append(kb_info)
                    except Exception as e:
                        logger.error(f"Error processing file {kb_path}: {e}")
        except Exception as e:
            logger.error(f"Error listing knowledge bases from {self.documents_dir}: {e}")

        return knowledge_bases

    @mcp_tool_with_error_handling
    async def get_versemind_data(self) -> Dict[str, Any]:
        """Get the current VerseMind data (title and reference)."""
        # Ensure data is loaded if it wasn't at init
        if self.title is None and self.reference is None:
            self._load_from_globals()

        return {
            "success": True,
            "title": self.title,
            "reference": self.reference,
            "has_data": bool(self.title or self.reference),
        }

    @mcp_tool_with_error_handling
    async def list_knowledge_bases(self) -> Dict[str, Any]:
        """List all available knowledge bases."""
        knowledge_bases = self._get_knowledge_bases()
        return {
            "success": True,
            "knowledge_bases": knowledge_bases,
            "count": len(knowledge_bases),
        }

    @mcp_tool_with_error_handling
    async def get_knowledge_base_info(self, kb_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific knowledge base."""
        knowledge_bases = self._get_knowledge_bases()
        kb_info = next((kb for kb in knowledge_bases if kb["id"] == kb_id), None)

        if not kb_info:
            return {"success": False, "error": f"Knowledge base with ID '{kb_id}' not found."}

        return {"success": True, "knowledge_base": kb_info}

    @mcp_tool_with_error_handling
    async def search_knowledge_base(
        self, query: str, kb_id: Optional[str] = None, limit: int = 5
    ) -> Dict[str, Any]:
        """Search in a knowledge base or all knowledge bases. Mock implementation."""
        logger.info(f"Mock search in VersemindMCPService: query='{query}', kb_id={kb_id}, limit={limit}")

        # This would call the actual RAG search logic in a real implementation
        # For now, returns a mock response
        results = []
        for i in range(min(limit, 3)):  # Mock up to 3 results or limit
            results.append(
                {
                    "id": f"mock_result_{i+1}",
                    "content": f"This is mock search result {i+1} for query '{query}' from KB '{kb_id or 'all'}'.",
                    "score": round(0.9 - (i * 0.05), 2),
                    "source": kb_id or "all_knowledge_bases",
                }
            )

        return {"success": True, "query": query, "results": results, "total_results": len(results)}

    @mcp_tool_with_error_handling
    async def list_available_models(self) -> Dict[str, Any]:
        """List all available AI models."""
        # In a real scenario, this might dynamically check configured models
        return {"success": True, "models": self.models, "total_providers": len(self.models)}


# Example of how this service might be instantiated by mcp_server_manager
# This is for illustration and won't run directly here.
if __name__ == "__main__":
    # This block is for testing or direct execution, not part of the module's role in the app
    logging.basicConfig(level=logging.INFO)

    # Mock __main__ for testing _load_from_globals
    sys.modules["__main__"].title = "Test Document Title from __main__"
    sys.modules["__main__"].reference = "This is some reference text from __main__."

    service = VersemindMCPService()

    # Example of how tools might be accessed (though MCP server handles this)
    async def run_tool_test():
        print("--- Testing get_versemind_data ---")
        data_result = await service.get_versemind_data()
        print(json.dumps(data_result, indent=2))

        print("\n--- Testing list_knowledge_bases ---")
        # Create some dummy files for testing
        if not os.path.exists(service.documents_dir):
            os.makedirs(service.documents_dir)
        with open(os.path.join(service.documents_dir, "test_doc.pdf"), "w") as f:
            f.write("dummy pdf content")
        with open(os.path.join(service.documents_dir, "another_doc.txt"), "w") as f:
            f.write("dummy text content")

        kb_list_result = await service.list_knowledge_bases()
        print(json.dumps(kb_list_result, indent=2))

        if kb_list_result["count"] > 0:
            test_kb_id = kb_list_result["knowledge_bases"][0]["id"]
            print(f"\n--- Testing get_knowledge_base_info for {test_kb_id} ---")
            kb_info_result = await service.get_knowledge_base_info(kb_id=test_kb_id)
            print(json.dumps(kb_info_result, indent=2))

            print(f"\n--- Testing search_knowledge_base for {test_kb_id} ---")
            search_result = await service.search_knowledge_base(query="test query", kb_id=test_kb_id)
            print(json.dumps(search_result, indent=2))

        print("\n--- Testing list_available_models ---")
        models_result = await service.list_available_models()
        print(json.dumps(models_result, indent=2))

        # Clean up dummy files
        os.remove(os.path.join(service.documents_dir, "test_doc.pdf"))
        os.remove(os.path.join(service.documents_dir, "another_doc.txt"))

    import asyncio

    asyncio.run(run_tool_test())
