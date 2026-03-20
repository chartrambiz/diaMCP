# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-03-19

### Added
- Initial release
- 14 built-in tools:
  - File operations: `read_file`, `write_file`, `list_directory`, `search_files`, `grep`
  - Web tools: `web_search`, `web_fetch`
  - Git tools: `git_clone`, `git_pull`
  - System tools: `run_command`, `python_eval`, `get_system_info`, `get_time`, `calculate`
- Dynamic tool discovery from `./workspace/tools/`
- HTTP transport with streamable-http
- JSON response mode for broad compatibility
- Persistent workspace volume
- Docker and Docker Compose setup

### Custom Tools Included
- `greeting` - Generate personalized greetings (formal, casual, funny)
- `add_numbers` - Add two numbers
- `word_reverser` - Reverse words in a sentence

## [Unreleased]

### Added
- **Dangerous command blocking** - `run_command` now blocks dangerous patterns:
  - All `rm -rf` and `rm -r` commands (any path)
  - `dd` to disk devices or root
  - System commands: `shutdown`, `reboot`, `halt`, `poweroff`, `mkfs`, `init 0`
  - `chmod 777` and `chmod -R 777`
  - `curl | sh` and `wget | sh` (drive-by installs)
  - Fork bombs (`:(){...}`)
  - Path traversal detection (`..` outside workspace)
  - Redirects to `/etc/passwd`, `/etc/shadow`
- **Command blacklist management** - `manage_blacklist` tool to add/remove commands
- **Session approval tracking** - `manage_approved` tool to list/clear approved commands
- **Dangerous patterns info** - `get_dangerous_patterns` tool shows all blocked patterns
- **Elicitation support** - Confirmation prompts for dangerous commands (works with MCP clients that support it)
- **MCP Resources** - Expose context to LLM:
  - `diamcp://context/time` - current datetime
  - `diamcp://context/system` - system information
  - `diamcp://workspace/summary` - workspace contents overview
  - `diamcp://tools/list` - list of all available tools
- **MCP Prompts** - Reusable prompt templates:
  - `startup_context` - call get_time and get_system_info first
  - `file_search_first` - use search_files before reading files
  - `web_research` - web_search then web_fetch workflow
  - `code_review` - steps for reviewing code
- **Additional built-in tools**: `count_lines`, `download_file`, `file_info`, `create_directory`, `delete_file`, `run_python_script`

### Known Issues
- Custom tools may require LLM to refresh tool list on first load
- Elicitation prompts do not work with llama.cpp webui (webui lacks MCP elicitation support)

### Planned
- Additional web research tools
- MCP registry integration for easy tool discovery
