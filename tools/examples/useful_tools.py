from base import tool
import subprocess
from pathlib import Path


@tool(
    name="count_lines",
    description="Count lines of code in files by extension",
    schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path (default: .)"},
            "extensions": {
                "type": "string",
                "description": "Comma-separated extensions (e.g., 'py,js,txt')",
            },
        },
        "required": ["path"],
    },
)
def count_lines(path: str = ".", extensions: str = "") -> str:
    """Count lines of code in files, optionally filtered by extension."""
    import re

    full_path = Path("/workspace") / path
    if not full_path.exists():
        return f"Error: Path '{path}' not found"

    if extensions:
        exts = [f".{e.strip().lstrip('.')}" for e in extensions.split(",")]
    else:
        exts = None

    total_lines = 0
    total_files = 0
    details = []

    for f in full_path.rglob("*"):
        if f.is_file():
            if exts is None or f.suffix in exts:
                try:
                    lines = len(
                        f.read_text(encoding="utf-8", errors="ignore").splitlines()
                    )
                    total_lines += lines
                    total_files += 1
                    details.append(f"  {f.relative_to('/workspace')}: {lines}")
                except Exception:
                    pass

    if not details:
        return f"No files found matching criteria in '{path}'"
    return f"Total: {total_lines} lines in {total_files} files\n" + "\n".join(
        details[:20]
    )


@tool(
    name="download_file",
    description="Download a file from a URL to the workspace",
    schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to download from"},
            "filename": {
                "type": "string",
                "description": "Destination filename in workspace",
            },
        },
        "required": ["url", "filename"],
    },
)
def download_file(url: str, filename: str) -> str:
    """Download a file from URL to workspace."""
    import httpx

    full_path = Path("/workspace") / filename
    try:
        with httpx.get(url, timeout=30, follow_redirects=True) as response:
            response.raise_for_status()
            full_path.write_bytes(response.content)
        return f"Downloaded to '{filename}' ({len(response.content)} bytes)"
    except Exception as e:
        return f"Error downloading: {e}"


@tool(
    name="file_info",
    description="Get information about a file (size, modified date, permissions)",
    schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path in workspace"},
        },
        "required": ["path"],
    },
)
def file_info(path: str) -> str:
    """Get detailed file information."""
    import datetime

    full_path = Path("/workspace") / path
    if not full_path.exists():
        return f"Error: File '{path}' not found"
    if full_path.is_dir():
        return f"Error: '{path}' is a directory"
    stat = full_path.stat()
    info = {
        "path": str(full_path.relative_to("/workspace")),
        "size_bytes": stat.st_size,
        "size_readable": _format_size(stat.st_size),
        "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "created": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "permissions": _format_permissions(stat.st_mode),
    }
    return "\n".join(f"{k}: {v}" for k, v in info.items())


def _format_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _format_permissions(mode: int) -> str:
    import stat

    return oct(mode)[-3:]


@tool(
    name="create_directory",
    description="Create a directory in the workspace",
    schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path to create"},
        },
        "required": ["path"],
    },
)
def create_directory(path: "str") -> str:
    """Create a directory (and parent directories if needed)."""
    full_path = Path("/workspace") / path
    try:
        full_path.mkdir(parents=True, exist_ok=True)
        return f"Created directory: '{path}'"
    except Exception as e:
        return f"Error creating directory: {e}"


@tool(
    name="delete_file",
    description="Delete a file from the workspace (NOT directory deletion, use with caution)",
    schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to delete"},
        },
        "required": ["path"],
    },
)
def delete_file(path: str) -> str:
    """Delete a file. Does NOT delete directories."""
    full_path = Path("/workspace") / path
    if not full_path.exists():
        return f"Error: File '{path}' not found"
    if full_path.is_dir():
        return f"Error: '{path}' is a directory. Use list_directory to see contents."
    try:
        full_path.unlink()
        return f"Deleted file: '{path}'"
    except Exception as e:
        return f"Error deleting file: {e}"


@tool(
    name="run_python_script",
    description="Execute a Python script file in the workspace",
    schema={
        "type": "object",
        "properties": {
            "script_path": {
                "type": "string",
                "description": "Path to the Python script",
            },
            "args": {
                "type": "string",
                "description": "Command line arguments (optional)",
            },
        },
        "required": ["script_path"],
    },
)
def run_python_script(script_path: str, args: str = "") -> str:
    """Execute a Python script file with optional arguments."""
    import subprocess

    full_path = Path("/workspace") / script_path
    if not full_path.exists():
        return f"Error: Script '{script_path}' not found"
    if not full_path.suffix == ".py":
        return f"Error: '{script_path}' is not a Python file"

    cmd = ["python3", str(full_path)]
    if args:
        cmd.extend(args.split())

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd="/workspace",
        )
        output = []
        if result.stdout:
            output.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output.append(f"STDERR:\n{result.stderr}")
        output.append(f"Exit code: {result.returncode}")
        return "\n".join(output)
    except subprocess.TimeoutExpired:
        return f"Error: Script timed out after 30 seconds"
    except Exception as e:
        return f"Error running script: {e}"
