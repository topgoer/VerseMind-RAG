"""
MCP (Model Context Protocol) module for VerseMind-RAG.

This module provides MCP server functionality and data management
for the VerseMind-RAG system.
"""

from .mcp_server_manager import (
    start_mcp_server,
    stop_mcp_server,
    set_versemind_data,
    get_versemind_data
)

__all__ = [
    'start_mcp_server',
    'stop_mcp_server',
    'set_versemind_data',
    'get_versemind_data'
]
