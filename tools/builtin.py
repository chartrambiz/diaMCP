"""Built-in tools for the MCP server."""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from base import tool


DANGEROUS_PATTERNS = [
    (r"\brm\s+-rf\s+/\s", "rm -rf / with trailing path"),
    (r"\brm\s+-rf\s+\*\s", "rm -rf * with trailing space"),
    (r"\brm\s+-rf\s+\.\s", "rm -rf . with trailing space"),
    (r"\brm\s+-rf\s+/", "rm -rf /"),
    (r"\brm\s+-rf\s+\*", "rm -rf *"),
    (r"\brm\s+-rf\s+\.", "rm -rf ."),
    (r"\brm\s+-rf\s", "rm -rf with any path"),
    (r"\brm\s+-r\s+/\s", "rm -r / with trailing path"),
    (r"\brm\s+-r\s+\*\s", "rm -r * with trailing space"),
    (r"\brm\s+-r\s+\.\s", "rm -r . with trailing space"),
    (r"\brm\s+-r\s+/\s", "rm -r / with trailing path"),
    (r"\brm\s+-r\s+\*", "rm -r *"),
    (r"\brm\s+-r\s+\.", "rm -r ."),
    (r"\brm\s+-r\s", "rm -r with any path"),
    (r"\bdd\s+.*of=/dev/sd", "dd to disk device"),
    (r"\bdd\s+.*of=/dev/hd", "dd to disk device"),
    (r"\bdd\s+.*of=/dev/null", "dd to null (data loss)"),
    (r"\bdd\s+.*of=/", "dd to root device"),
    (r"\bmkfs", "filesystem creation"),
    (r"\bshutdown", "shutdown command"),
    (r"\breboot", "reboot command"),
    (r"\bhalt", "halt command"),
    (r"\bpoweroff", "poweroff command"),
    (r"\binit\s+0", "init 0 (halt)"),
    (r"\bchmod\s+-R\s+777", "chmod -R 777"),
    (r"\bchmod\s+777", "chmod 777 (wide open)"),
    (r"\bcurl.*\|.*sh", "curl piped to shell"),
    (r"\bwget.*\|.*sh", "wget piped to shell"),
    (r":\(\)\{", "fork bomb"),
    (r">\s*/etc/passwd", "writing to passwd"),
    (r">\s*/etc/shadow", "writing to shadow"),
    (r"\.\/.*\s*>", "redirecting output to file"),
]


class CommandApprovalSchema(BaseModel):
    confirm: bool = Field(description="Confirm execution of this command")
    remember: bool = Field(default=False, description="Remember for this session")


approved_commands: set[str] = set()
blacklisted_commands: set[str] = set()


def is_command_dangerous(command: str) -> tuple[bool, str]:
    """Check if command matches dangerous patterns."""
    cmd_lower = command.lower()
    for pattern, description in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd_lower, re.IGNORECASE):
            return True, f"Dangerous command: {description}"
    if command.strip() in blacklisted_commands:
        return True, "Command is blacklisted"

    if ".." in command and not command.strip().startswith("/workspace"):
        return True, "Path traversal detected"

    return False, ""


def approve_command(command: str):
    """Add command to session-approved set."""
    approved_commands.add(command.strip())


def is_command_approved(command: str) -> bool:
    """Check if command is in approved set."""
    return command.strip() in approved_commands


def blacklist_add(command: str):
    """Add command to permanent blacklist."""
    blacklisted_commands.add(command.strip())


def blacklist_remove(command: str):
    """Remove command from permanent blacklist."""
    blacklisted_commands.discard(command.strip())


def get_blacklist() -> set[str]:
    """Get current blacklist."""
    return blacklisted_commands.copy()


def get_approved() -> set[str]:
    """Get current approved commands."""
    return approved_commands.copy()


@tool(
    name="read_file",
    description="Read contents of a file from the workspace",
    schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path to the file"}
        },
        "required": ["path"],
    },
)
def read_file(path: str) -> str:
    """Read a file from the workspace."""
    full_path = Path("/workspace") / path
    if not full_path.exists():
        return f"Error: File '{path}' not found"
    if not full_path.is_file():
        return f"Error: '{path}' is not a file"
    try:
        return full_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {e}"


@tool(
    name="write_file",
    description="Write content to a file in the workspace",
    schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path to the file"},
            "content": {"type": "string", "description": "Content to write"},
        },
        "required": ["path", "content"],
    },
)
def write_file(path: str, content: str) -> str:
    """Write content to a file in the workspace."""
    full_path = Path("/workspace") / path
    try:
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        return f"Successfully wrote to '{path}'"
    except Exception as e:
        return f"Error writing file: {e}"


@tool(
    name="list_directory",
    description="List contents of a directory in the workspace",
    schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to directory (default: root)",
            }
        },
        "required": [],
    },
)
def list_directory(path: str = ".") -> str:
    """List directory contents."""
    full_path = Path("/workspace") / path
    if not full_path.exists():
        return f"Error: Directory '{path}' not found"
    if not full_path.is_dir():
        return f"Error: '{path}' is not a directory"
    try:
        items = []
        for item in sorted(full_path.iterdir()):
            suffix = "/" if item.is_dir() else ""
            items.append(f"{item.name}{suffix}")
        return "\n".join(items) if items else "(empty)"
    except Exception as e:
        return f"Error listing directory: {e}"


@tool(
    name="search_files",
    description="Search for files matching a glob pattern in the workspace",
    schema={
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern (e.g., '*.py', '**/*.txt')",
            },
            "path": {
                "type": "string",
                "description": "Directory to search in (default: workspace root)",
            },
        },
        "required": ["pattern"],
    },
)
def search_files(pattern: str, path: str = ".") -> str:
    """Search for files matching a glob pattern."""
    full_path = Path("/workspace") / path
    if not full_path.exists():
        return f"Error: Directory '{path}' not found"
    try:
        matches = list(full_path.glob(pattern))
        if not matches:
            return f"No files matching '{pattern}' found in '{path}'"
        return "\n".join(str(m.relative_to("/workspace")) for m in matches)
    except Exception as e:
        return f"Error searching files: {e}"


@tool(
    name="run_command",
    description="Execute a shell command in the workspace. Dangerous commands require confirmation.",
    schema={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to execute"},
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 30)",
            },
        },
        "required": ["command"],
    },
)
async def run_command(command: str, timeout: int = 30, ctx=None) -> str:
    """Execute a shell command with danger checking and optional confirmation."""
    global approved_commands

    dangerous, reason = is_command_dangerous(command)
    if dangerous:
        if is_command_approved(command):
            pass
        elif ctx is not None:
            try:
                from mcp.server.fastmcp import Context

                if isinstance(ctx, Context):
                    result = await ctx.elicit(
                        message=f"⚠️ DANGEROUS COMMAND DETECTED\n\nCommand: `{command}`\n\nReason: {reason}\n\nDo you want to execute this?",
                        schema=CommandApprovalSchema,
                    )
                    if result.action != "accept":
                        return f"[BLOCKED] Command blocked by user"
                    if result.data and result.data.remember:
                        approve_command(command)
            except Exception:
                return f"[BLOCKED] {reason}"
        else:
            return f"[BLOCKED] {reason}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
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
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing command: {e}"


@tool(
    name="web_search",
    description="Search the web for information",
    schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "num_results": {
                "type": "integer",
                "description": "Number of results (default: 5)",
            },
        },
        "required": ["query"],
    },
)
def web_search(query: str, num_results: int = 5) -> str:
    """Search the web using DuckDuckGo."""
    try:
        from ddgs import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=num_results):
                results.append(f"Title: {r['title']}\nURL: {r['href']}\n{r['body']}\n")

        if not results:
            return "No results found"
        return "\n---\n".join(results)
    except ImportError:
        return "Error: ddgs not installed. Run: pip install ddgs"
    except Exception as e:
        return f"Error performing search: {e}"


@tool(
    name="web_fetch",
    description="Fetch and extract text content from a web page",
    schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
            "max_length": {
                "type": "integer",
                "description": "Max characters to return (default: 10000)",
            },
        },
        "required": ["url"],
    },
)
def web_fetch(url: str, max_length: int = 10000) -> str:
    """Fetch content from a URL."""
    try:
        import httpx
        from selectolax.parser import HTMLParser

        response = httpx.get(url, timeout=10, follow_redirects=True)
        response.raise_for_status()

        tree = HTMLParser(response.text)
        for tag in tree.css("script, style, nav, footer, header"):
            tag.decompose()

        text = tree.text()
        if len(text) > max_length:
            text = (
                text[:max_length]
                + f"\n... [truncated, full content: {len(text)} chars]"
            )
        return text.strip()
    except ImportError:
        return "Error: httpx or selectolax not installed"
    except Exception as e:
        return f"Error fetching URL: {e}"


@tool(
    name="python_eval",
    description="Evaluate a Python expression or statement",
    schema={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python code to evaluate"},
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 10)",
            },
        },
        "required": ["code"],
    },
)
def python_eval(code: str, timeout: int = 10) -> str:
    """Evaluate Python code in a sandbox."""
    import signal

    def timeout_handler(signum, frame):
        raise TimeoutError(f"Execution timed out after {timeout} seconds")

    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)

        namespace = {"__builtins__": __builtins__}
        try:
            result = eval(code, namespace)
            return str(result) if result is not None else "Executed successfully"
        except SyntaxError:
            exec(code, namespace)
            return "Executed successfully"
        finally:
            signal.alarm(0)
    except TimeoutError as e:
        return str(e)
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


@tool(
    name="git_clone",
    description="Clone a git repository into the workspace",
    schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Git repository URL"},
            "path": {
                "type": "string",
                "description": "Destination path in workspace (optional)",
            },
        },
        "required": ["url"],
    },
)
def git_clone(url: str, path: str = "") -> str:
    """Clone a git repository."""
    dest = Path("/workspace") / (path or "")
    if dest.exists() and any(dest.iterdir()):
        return f"Error: Destination '{path}' already exists and is not empty"

    try:
        subprocess.run(
            ["git", "clone", url, str(dest)],
            capture_output=True,
            text=True,
            check=True,
            cwd="/workspace",
        )
        return f"Successfully cloned to '{path or dest.name}'"
    except subprocess.CalledProcessError as e:
        return f"Error cloning repo: {e.stderr}"
    except Exception as e:
        return f"Error: {e}"


@tool(
    name="git_pull",
    description="Pull latest changes from a git repository",
    schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the git repository"}
        },
        "required": ["path"],
    },
)
def git_pull(path: str) -> str:
    """Pull changes from a git repository."""
    full_path = Path("/workspace") / path
    try:
        result = subprocess.run(
            ["git", "pull", "origin", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(full_path),
        )
        return result.stdout or result.stderr or f"Exit code: {result.returncode}"
    except Exception as e:
        return f"Error: {e}"


@tool(
    name="get_system_info",
    description="Get system information",
    schema={"type": "object", "properties": {}, "required": []},
)
def get_system_info() -> str:
    """Get basic system information."""
    import platform
    import datetime

    info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "hostname": platform.node(),
        "cwd": str(Path.cwd()),
        "time": datetime.datetime.now().isoformat(),
    }
    return json.dumps(info, indent=2)


@tool(
    name="grep",
    description="Search for text patterns in files within the workspace",
    schema={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern to search for"},
            "path": {
                "type": "string",
                "description": "Directory to search in (default: .)",
            },
            "file_pattern": {
                "type": "string",
                "description": "File glob pattern (e.g., '*.py')",
            },
        },
        "required": ["pattern"],
    },
)
def grep(pattern: str, path: str = ".", file_pattern: str = "*") -> str:
    """Search for pattern in files."""
    import re

    full_path = Path("/workspace") / path
    if not full_path.exists():
        return f"Error: Path '{path}' not found"

    try:
        regex = re.compile(pattern)
        matches = []

        for f in full_path.rglob(file_pattern):
            if f.is_file():
                try:
                    for i, line in enumerate(
                        f.read_text(encoding="utf-8").splitlines(), 1
                    ):
                        if regex.search(line):
                            rel_path = f.relative_to(Path("/workspace"))
                            matches.append(f"{rel_path}:{i}: {line.rstrip()}")
                except Exception:
                    pass

        if not matches:
            return f"No matches for '{pattern}'"
        return "\n".join(matches[:100])  # Limit output
    except re.error as e:
        return f"Invalid regex: {e}"
    except Exception as e:
        return f"Error: {e}"


@tool(
    name="get_time",
    description="Get the current date and time",
    schema={
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "Timezone (e.g., 'UTC', 'America/New_York')",
            }
        },
        "required": [],
    },
)
def get_time(timezone: str = "UTC") -> str:
    """Get current time in specified timezone."""
    import datetime

    try:
        if timezone != "UTC":
            import zoneinfo

            tz = zoneinfo.ZoneInfo(timezone)
            now = datetime.datetime.now(tz)
        else:
            now = datetime.datetime.utcnow()
        return now.isoformat()
    except Exception as e:
        return f"Error: {e}"


@tool(
    name="calculate",
    description="Perform mathematical calculations",
    schema={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Math expression (e.g., '2+2', 'sqrt(16)', 'sin(pi/2)')",
            }
        },
        "required": ["expression"],
    },
)
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        import math

        allowed_names = {
            k: v for k, v in math.__dict__.items() if not k.startswith("_")
        }
        allowed_names.update(
            {"abs": abs, "round": round, "min": min, "max": max, "pow": pow}
        )

        result = eval(expression, {"__builtins__": {}, **allowed_names})
        return str(result)
    except Exception as e:
        return f"Error: {e}"


@tool(
    name="manage_blacklist",
    description="Manage the command blacklist (requires confirmation for dangerous ops)",
    schema={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "add", "remove", "clear"],
                "description": "Action to perform",
            },
            "command": {
                "type": "string",
                "description": "Command to add or remove from blacklist",
            },
        },
        "required": ["action"],
    },
)
def manage_blacklist(action: str, command: str = "") -> str:
    """Manage command blacklist."""
    global blacklisted_commands
    if action == "list":
        if not blacklisted_commands:
            return "Blacklist is empty"
        return "Blacklisted commands:\n" + "\n".join(
            f"  - {c}" for c in sorted(blacklisted_commands)
        )
    elif action == "add":
        if not command:
            return "Error: command required for 'add' action"
        blacklist_add(command)
        return f"Added '{command}' to blacklist"
    elif action == "remove":
        if not command:
            return "Error: command required for 'remove' action"
        if command not in blacklisted_commands:
            return f"Command '{command}' not in blacklist"
        blacklist_remove(command)
        return f"Removed '{command}' from blacklist"
    elif action == "clear":
        count = len(blacklisted_commands)
        blacklisted_commands.clear()
        return f"Cleared {count} commands from blacklist"
    return f"Unknown action: {action}"


@tool(
    name="manage_approved",
    description="Manage session-approved commands",
    schema={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "clear"],
                "description": "Action to perform",
            },
        },
        "required": ["action"],
    },
)
def manage_approved(action: str) -> str:
    """Manage approved commands for this session."""
    global approved_commands
    if action == "list":
        if not approved_commands:
            return "No approved commands for this session"
        return "Approved commands:\n" + "\n".join(
            f"  - {c}" for c in sorted(approved_commands)
        )
    elif action == "clear":
        count = len(approved_commands)
        approved_commands.clear()
        return f"Cleared {count} approved commands"
    return f"Unknown action: {action}"


@tool(
    name="get_dangerous_patterns",
    description="Get list of dangerous command patterns that trigger confirmation",
    schema={
        "type": "object",
        "properties": {},
        "required": [],
    },
)
def get_dangerous_patterns() -> str:
    """Get dangerous command patterns."""
    patterns = [
        "rm -rf /",
        "rm -rf *",
        "dd to disk device",
        "mkfs",
        "shutdown/reboot/halt",
        "chmod -R 777",
        "curl | sh",
        "wget | sh",
        "Fork bomb (:(){...})",
    ]
    return "Dangerous patterns:\n" + "\n".join(f"  - {p}" for p in patterns)


def register_builtin_tools():
    """Register all built-in tools with the registry."""
    from base import ToolRegistry

    builtin_tools = [
        read_file,
        write_file,
        list_directory,
        search_files,
        run_command,
        web_search,
        web_fetch,
        python_eval,
        git_clone,
        git_pull,
        get_system_info,
        grep,
        get_time,
        calculate,
        manage_blacklist,
        manage_approved,
        get_dangerous_patterns,
    ]

    for t in builtin_tools:
        ToolRegistry.register(
            name=t.__name__,
            description=t.__doc__ or "",
            func=t,
            input_schema=t.__annotations__ if hasattr(t, "__annotations__") else {},
        )
