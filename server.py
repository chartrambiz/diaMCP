"""MCP Server with dynamic tool discovery - HTTP/streamable-http for llama.cpp webui."""

import sys
import os
import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("diamcp")

WORKSPACE_DIR = Path("/workspace")
WORKSPACE_TOOLS_DIR = WORKSPACE_DIR / "tools"
APP_DIR = Path("/app")
APP_TOOLS_EXAMPLES_DIR = APP_DIR / "examples"

sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(WORKSPACE_DIR))
sys.path.insert(0, str(WORKSPACE_TOOLS_DIR))

from base import ToolRegistry
from builtin import register_builtin_tools

mcp = FastMCP(
    "do-it-all-mcp",
    host="0.0.0.0",
    port=8000,
    stateless_http=True,
    json_response=True,
)


def discover_tools_from_dir(tools_dir: Path, source_name: str):
    """Discover and load Python tools from a directory."""
    if not tools_dir.exists():
        return

    for filepath in tools_dir.glob("*.py"):
        if filepath.name.startswith("_"):
            continue

        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(filepath.stem, filepath)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[filepath.stem] = module
                spec.loader.exec_module(module)
                logger.info(f"Loaded tools from {source_name}/{filepath.name}")
        except Exception as e:
            logger.error(f"Failed to load {source_name}/{filepath.name}: {e}")


def discover_user_tools():
    """Discover and load Python tools from workspace and examples directories."""
    discover_tools_from_dir(WORKSPACE_TOOLS_DIR, "workspace/tools")
    discover_tools_from_dir(APP_TOOLS_EXAMPLES_DIR, "tools/examples")


def register_tools():
    """Register all tools from registry with FastMCP."""
    for name, tool_def in ToolRegistry.get_all().items():
        try:
            mcp.add_tool(
                tool_def.func, name=tool_def.name, description=tool_def.description
            )
        except Exception as e:
            logger.error(f"Failed to register tool {tool_def.name}: {e}")


def main():
    """Start the MCP server."""
    register_builtin_tools()
    discover_user_tools()
    register_tools()

    logger.info(f"diaMCP Server starting on 0.0.0.0:8000")
    logger.info(f"Workspace: {WORKSPACE_DIR}")
    logger.info(f"Tools directory: {WORKSPACE_TOOLS_DIR}")
    logger.info(f"Tools loaded: {len(ToolRegistry.get_all())}")

    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
