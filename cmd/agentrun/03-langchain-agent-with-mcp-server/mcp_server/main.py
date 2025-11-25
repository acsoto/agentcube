"""
MCP Server with Utility Tools

This MCP server provides a collection of useful tools:
- Calculator: Perform mathematical calculations
- File operations: Read, write, and list files in a workspace
- DateTime utilities: Get current time, format dates, timezone conversions

The server uses FastMCP with stateless HTTP transport for compatibility
with AgentRun CLI deployment.
"""

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP(
    name="utility-tools-server",
    host="0.0.0.0",
    port=8000,
    stateless_http=True
)

# Create a workspace directory for file operations
WORKSPACE_DIR = Path("/tmp/mcp_workspace")
WORKSPACE_DIR.mkdir(exist_ok=True)


# ============================================================================
# Calculator Tools
# ============================================================================

@mcp.tool()
def calculate(expression: str) -> str:
    """
    Evaluate a mathematical expression and return the result.

    Args:
        expression: A mathematical expression string (e.g., "2 + 2", "10 * 5 + 3")

    Returns:
        The result of the calculation as a string

    Examples:
        - calculate("5 + 3") -> "8"
        - calculate("10 * (5 + 2)") -> "70"
    """
    try:
        # Use eval with restricted globals for safety
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Result: {result}"
    except Exception as e:
        return f"Error calculating expression: {str(e)}"


@mcp.tool()
def power(base: float, exponent: float) -> str:
    """
    Calculate base raised to the power of exponent.

    Args:
        base: The base number
        exponent: The exponent to raise the base to

    Returns:
        The result of base^exponent

    Examples:
        - power(2, 3) -> "8.0"
        - power(5, 2) -> "25.0"
    """
    try:
        result = base ** exponent
        return f"Result: {result}"
    except Exception as e:
        return f"Error calculating power: {str(e)}"


# ============================================================================
# File Operation Tools
# ============================================================================

@mcp.tool()
def write_file(filename: str, content: str) -> str:
    """
    Write content to a file in the workspace.

    Args:
        filename: Name of the file to write
        content: Content to write to the file

    Returns:
        Success message or error message

    Examples:
        - write_file("notes.txt", "Hello World") -> "Successfully wrote to notes.txt"
    """
    try:
        file_path = WORKSPACE_DIR / filename
        with open(file_path, 'w') as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to {filename}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@mcp.tool()
def read_file(filename: str) -> str:
    """
    Read content from a file in the workspace.

    Args:
        filename: Name of the file to read

    Returns:
        Content of the file or error message

    Examples:
        - read_file("notes.txt") -> "Hello World"
    """
    try:
        file_path = WORKSPACE_DIR / filename
        if not file_path.exists():
            return f"Error: File '{filename}' not found in workspace"

        with open(file_path, 'r') as f:
            content = f.read()
        return f"Content of {filename}:\n{content}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@mcp.tool()
def list_files() -> str:
    """
    List all files in the workspace directory.

    Returns:
        A list of files in the workspace

    Examples:
        - list_files() -> "Files in workspace: notes.txt, data.json"
    """
    try:
        files = [f.name for f in WORKSPACE_DIR.iterdir() if f.is_file()]
        if not files:
            return "Workspace is empty (no files)"
        return f"Files in workspace:\n" + "\n".join(f"- {f}" for f in files)
    except Exception as e:
        return f"Error listing files: {str(e)}"


# ============================================================================
# DateTime Tools
# ============================================================================

@mcp.tool()
def get_current_time(timezone_name: Optional[str] = None) -> str:
    """
    Get the current date and time.

    Args:
        timezone_name: Optional timezone name (e.g., "UTC", "US/Eastern")
                      If not provided, returns UTC time

    Returns:
        Current date and time as a formatted string

    Examples:
        - get_current_time() -> "2024-01-15 10:30:45 UTC"
        - get_current_time("US/Eastern") -> "2024-01-15 05:30:45 US/Eastern"
    """
    try:
        if timezone_name:
            try:
                import pytz
                tz = pytz.timezone(timezone_name)
                now = datetime.now(tz)
                return f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"
            except:
                return f"Warning: Timezone '{timezone_name}' not available. Using UTC.\nCurrent time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        else:
            now = datetime.now(timezone.utc)
            return f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    except Exception as e:
        return f"Error getting current time: {str(e)}"


@mcp.tool()
def format_timestamp(timestamp: int, format_string: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Convert a Unix timestamp to a formatted date string.

    Args:
        timestamp: Unix timestamp (seconds since epoch)
        format_string: Optional format string (default: "%Y-%m-%d %H:%M:%S")

    Returns:
        Formatted date string

    Examples:
        - format_timestamp(1705315200) -> "2024-01-15 08:00:00"
        - format_timestamp(1705315200, "%B %d, %Y") -> "January 15, 2024"
    """
    try:
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return f"Formatted time: {dt.strftime(format_string)}"
    except Exception as e:
        return f"Error formatting timestamp: {str(e)}"


# ============================================================================
# Server Health and Info
# ============================================================================

@mcp.tool()
def server_info() -> str:
    """
    Get information about the MCP server and available tools.

    Returns:
        Server information and tool count
    """
    tool_count = len([name for name in dir(mcp) if callable(getattr(mcp, name)) and not name.startswith('_')])
    return f"""MCP Server Information:
- Server Name: utility-tools-server
- Server Version: 1.0.0
- Available Tools: Calculator (2), File Operations (3), DateTime (2), Info (1)
- Total Tools: 8
- Workspace: {WORKSPACE_DIR}
- Status: Running
"""


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MCP Utility Tools Server Starting...")
    print("=" * 60)
    print(f"Server Name: utility-tools-server")
    print(f"Host: 0.0.0.0:8000")
    print(f"Transport: Streamable HTTP")
    print(f"Workspace: {WORKSPACE_DIR}")
    print("=" * 60)
    print("\nAvailable Tools:")
    print("  Calculator Tools:")
    print("    - calculate: Evaluate mathematical expressions")
    print("    - power: Calculate base^exponent")
    print("  File Operation Tools:")
    print("    - write_file: Write content to a file")
    print("    - read_file: Read content from a file")
    print("    - list_files: List all files in workspace")
    print("  DateTime Tools:")
    print("    - get_current_time: Get current date and time")
    print("    - format_timestamp: Format Unix timestamp to date string")
    print("  Info Tools:")
    print("    - server_info: Get server information")
    print("=" * 60)
    print("\nStarting MCP server on port 8000...")
    print("Ready to accept connections!\n")

    # Run the MCP server
    mcp.run(transport="streamable-http")
