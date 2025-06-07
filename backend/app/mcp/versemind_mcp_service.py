"""
VerseMind MCP Service

This module implements a simplified MCP-compatible service that exposes VerseMind-RAG functionalities
without external dependencies.

The service provides tools to interact with VerseMind-RAG's knowledge bases, search capabilities,
and text generation features.
"""

import os
import sys
import traceback
from typing import Dict, Any, List, Optional
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
            type('Tool', (), {'name': name, 'description': f'Tool: {name}'})()
            for name in self.server.tools.keys()
        ]

class SimpleMCPServer:
    """A simple MCP-like server implementation without external dependencies."""

    def __init__(self):
        self.tools = {}
        self.settings = type('Settings', (), {
            'host': '0.0.0.0',
            'port': 3005
        })()
        self._tool_manager = ToolManager(self)

    def register_tool(self, name: str, func: callable, description: str = ""):
        """Register a tool with the server."""
        self.tools[name] = {
            'func': func,
            'description': description
        }

    def run(self, transport='streamable-http'):
        """Mock run method that doesn't actually start a server."""
        logger.info(f"Mock MCP server would run on {self.settings.host}:{self.settings.port} with transport {transport}")
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
            return {
                "success": False,
                "error": error_msg
            }
    return wrapper

class VersemindMCPService:
    """Mock VerseMind MCP Service that provides the same interface without external dependencies."""

    def __init__(self):
        """Initialize the VerseMind MCP service."""
        self.mcp = SimpleMCPServer()
        self.title = None
        self.reference = None

        # Attempt to load current context from global environment if available
        self._load_from_globals()

        # Path to document storage
        self.storage_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../storage'))
        self.documents_dir = os.path.join(self.storage_dir, "documents")
        self.indices_dir = os.path.join(self.storage_dir, "indices")

        # Available models (would typically be loaded from config)
        self.models = {
            "ollama": ["llama3:8b", "codellama:7b", "mistral:7b"],
            "openai": ["gpt-3.5-turbo", "gpt-4o"],
            "deepseek": ["deepseek-chat", "deepseek-reasoner"]
        }

        self._register_tools()
        logger.info("VersemindMCPService initialized (mock implementation)")

    def _load_from_globals(self):
        """Load title and reference from globals if available."""
        try:
            main_module = sys.modules.get('__main__')
            if main_module:
                if hasattr(main_module, 'title'):
                    self.title = main_module.title
                if hasattr(main_module, 'reference'):
                    self.reference = main_module.reference

            # Check if we loaded anything
            if self.title or self.reference:
                logger.info(f"Loaded VerseMind data: title='{self.title}' and reference data of length {len(self.reference) if self.reference else 0}")
            else:
                logger.debug("No VerseMind data loaded from globals")
        except Exception as e:
            logger.error(f"Error loading from globals: {e}")

    def _register_tools(self):
        """Register all available tools with the MCP server."""
        tools = [
            ("get_versemind_data", self.get_versemind_data, "Get current VerseMind data"),
            ("list_knowledge_bases", self.list_knowledge_bases, "List available knowledge bases"),
            ("get_knowledge_base_info", self.get_knowledge_base_info, "Get knowledge base information"),
            ("search_knowledge_base", self.search_knowledge_base, "Search in knowledge base"),
            ("list_available_models", self.list_available_models, "List available models"),
        ]

        for name, func, description in tools:
            self.mcp.register_tool(name, func, description)

    def _get_knowledge_bases(self) -> List[Dict[str, Any]]:
        """Get list of available knowledge bases from the documents directory."""
        knowledge_bases = []

        try:
            # List knowledge bases from document directory
            if os.path.exists(self.documents_dir):
                for filename in os.listdir(self.documents_dir):
                    if filename.endswith(('.pdf', '.txt', '.md', '.docx')):
                        kb_path = os.path.join(self.documents_dir, filename)
                        kb_info = {
                            "id": filename.split('.')[0],
                            "name": filename,
                            "file_type": filename.split('.')[-1],
                            "size_bytes": os.path.getsize(kb_path),
                            "last_modified": os.path.getmtime(kb_path)
                        }
                        knowledge_bases.append(kb_info)
        except Exception as e:
            logger.error(f"Error getting knowledge bases: {e}")

        return knowledge_bases

    @mcp_tool_with_error_handling
    async def get_versemind_data(self) -> Dict[str, Any]:
        """Get the current VerseMind data (title and reference)."""
        return {
            "success": True,
            "title": self.title,
            "reference": self.reference,
            "has_data": bool(self.title or self.reference)
        }

    @mcp_tool_with_error_handling
    async def list_knowledge_bases(self) -> Dict[str, Any]:
        """List all available knowledge bases."""
        knowledge_bases = self._get_knowledge_bases()
        return {
            "success": True,
            "knowledge_bases": knowledge_bases,
            "count": len(knowledge_bases)
        }

    @mcp_tool_with_error_handling
    async def get_knowledge_base_info(self, kb_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific knowledge base."""
        knowledge_bases = self._get_knowledge_bases()
        kb_info = next((kb for kb in knowledge_bases if kb["id"] == kb_id), None)

        if not kb_info:
            return {
                "success": False,
                "error": f"Knowledge base '{kb_id}' not found"
            }

        return {
            "success": True,
            "knowledge_base": kb_info
        }

    @mcp_tool_with_error_handling
    async def search_knowledge_base(self, query: str, kb_id: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        """Search in a knowledge base or all knowledge bases."""
        # This is a mock implementation
        logger.info(f"Mock search: query='{query}', kb_id={kb_id}, limit={limit}")

        return {
            "success": True,
            "query": query,
            "results": [
                {
                    "id": "result_1",
                    "content": f"Mock search result for query: {query}",
                    "score": 0.95,
                    "source": kb_id or "all_knowledge_bases"
                }
            ],
            "total_results": 1
        }

    @mcp_tool_with_error_handling
    async def list_available_models(self) -> Dict[str, Any]:
        """List all available AI models."""
        return {
            "success": True,
            "models": self.models,
            "total_providers": len(self.models)
        }
