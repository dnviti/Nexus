#!/bin/bash
# Documentation Development Server Script
# Provides easy way to serve different versions of documentation locally

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
VERSION=""
PORT=8000
RELOAD=false

# Function to display usage
usage() {
    echo -e "${BLUE}Nexus Platform Documentation Server${NC}"
    echo ""
    echo "Usage: $0 [OPTIONS] [VERSION]"
    echo ""
    echo "OPTIONS:"
    echo "  -p, --port PORT      Port to serve on (default: 8000)"
    echo "  -r, --reload         Enable live reload"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "VERSION:"
    echo "  v2.0.0              Serve v2.0.0 documentation"
    echo "  dev                 Serve development documentation"
    echo "  (none)              List available versions and prompt"
    echo ""
    echo "Examples:"
    echo "  $0 v2.0.0           # Serve v2.0.0 on port 8000"
    echo "  $0 dev -p 8080      # Serve dev version on port 8080"
    echo "  $0 -r dev           # Serve dev version with live reload"
    echo ""
}

# Function to list available versions
list_versions() {
    echo -e "${BLUE}Available documentation versions:${NC}"
    echo ""

    local docs_dir="$(dirname "$0")/../../docs"
    local count=1

    for dir in "$docs_dir"/*/; do
        if [ -d "$dir" ]; then
            local version=$(basename "$dir")
            if [ "$version" != "overrides" ]; then
                local config_file="$(dirname "$0")/../../mkdocs-${version}.yml"
                if [ -f "$config_file" ]; then
                    if [ "$version" = "dev" ]; then
                        echo -e "  ${count}. ${YELLOW}${version}${NC} (development)"
                    else
                        echo -e "  ${count}. ${GREEN}${version}${NC}"
                    fi
                    count=$((count + 1))
                fi
            fi
        fi
    done
    echo ""
}

# Function to check if version exists
version_exists() {
    local version="$1"
    local docs_dir="$(dirname "$0")/../../docs/${version}"
    local config_file="$(dirname "$0")/../../mkdocs-${version}.yml"

    if [ -d "$docs_dir" ] && [ -f "$config_file" ]; then
        return 0
    else
        return 1
    fi
}

# Function to serve documentation
serve_docs() {
    local version="$1"
    local port="$2"
    local reload_flag="$3"

    local project_root="$(dirname "$0")/../.."
    local config_file="mkdocs-${version}.yml"

    echo -e "${GREEN}Starting documentation server...${NC}"
    echo -e "Version: ${BLUE}${version}${NC}"
    echo -e "Port: ${BLUE}${port}${NC}"
    echo -e "URL: ${BLUE}http://localhost:${port}${NC}"

    if [ "$version" = "dev" ]; then
        echo -e "Type: ${YELLOW}Development Version${NC}"
    fi

    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
    echo ""

    cd "$project_root"

    # Check if Poetry is available
    if command -v poetry &> /dev/null; then
        if [ "$reload_flag" = "true" ]; then
            poetry run mkdocs serve -f "$config_file" -a "localhost:${port}" --livereload
        else
            poetry run mkdocs serve -f "$config_file" -a "localhost:${port}"
        fi
    else
        # Fallback to direct mkdocs command
        if [ "$reload_flag" = "true" ]; then
            mkdocs serve -f "$config_file" -a "localhost:${port}" --livereload
        else
            mkdocs serve -f "$config_file" -a "localhost:${port}"
        fi
    fi
}

# Function to prompt for version selection
prompt_version() {
    list_versions

    echo -n "Select version (1-9) or enter version name: "
    read -r selection

    case $selection in
        1)
            echo "v2.0.0"
            ;;
        2)
            echo "dev"
            ;;
        v*.*)
            echo "$selection"
            ;;
        dev)
            echo "dev"
            ;;
        *)
            echo -e "${RED}Invalid selection: $selection${NC}" >&2
            return 1
            ;;
    esac
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -r|--reload)
            RELOAD=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        v*.*|dev)
            VERSION="$1"
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}" >&2
            usage
            exit 1
            ;;
    esac
done

# Validate port number
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then
    echo -e "${RED}Error: Port must be a number between 1024 and 65535${NC}" >&2
    exit 1
fi

# If no version specified, prompt for one
if [ -z "$VERSION" ]; then
    VERSION=$(prompt_version)
    if [ $? -ne 0 ]; then
        exit 1
    fi
fi

# Check if version exists
if ! version_exists "$VERSION"; then
    echo -e "${RED}Error: Version '$VERSION' not found${NC}" >&2
    echo ""
    list_versions
    exit 1
fi

# Check if port is in use
if command -v lsof &> /dev/null; then
    if lsof -Pi ":$PORT" -sTCP:LISTEN -t >/dev/null; then
        echo -e "${RED}Error: Port $PORT is already in use${NC}" >&2
        echo "Please choose a different port with -p option"
        exit 1
    fi
fi

# Start the server
serve_docs "$VERSION" "$PORT" "$RELOAD"
