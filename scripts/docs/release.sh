#!/bin/bash
# Documentation Release Script for Nexus Platform
# Automates the process of creating documentation for a new release

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
NEW_VERSION=""
SOURCE_VERSION=""
SET_AS_LATEST=false
BUILD_DOCS=false
DRY_RUN=false
VERBOSE=false

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Function to display usage
usage() {
    echo -e "${BLUE}Nexus Platform Documentation Release Script${NC}"
    echo ""
    echo "Usage: $0 [OPTIONS] <NEW_VERSION>"
    echo ""
    echo "OPTIONS:"
    echo "  -s, --source VERSION     Source version to copy from (default: current latest)"
    echo "  -l, --set-latest         Set this version as the latest stable version"
    echo "  -b, --build              Build documentation after creating version"
    echo "  -d, --dry-run           Show what would be done without making changes"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "ARGUMENTS:"
    echo "  NEW_VERSION             Version to create (e.g., v2.1.0, 2.1.0)"
    echo ""
    echo "Examples:"
    echo "  $0 v2.1.0                           # Create v2.1.0 from latest"
    echo "  $0 v2.1.0 --set-latest --build      # Create, set as latest, and build"
    echo "  $0 v2.1.0 --source v2.0.0           # Create v2.1.0 from v2.0.0"
    echo "  $0 v2.1.0 --dry-run                 # Show what would be done"
    echo ""
    echo "This script will:"
    echo "  1. Create new documentation version directory"
    echo "  2. Copy content from source version"
    echo "  3. Create MkDocs configuration file"
    echo "  4. Update versions.json metadata"
    echo "  5. Optionally set as latest version"
    echo "  6. Optionally build documentation"
    echo ""
}

# Function to log messages
log() {
    local level="$1"
    shift
    local message="$*"

    case "$level" in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        "DEBUG")
            if [ "$VERBOSE" = true ]; then
                echo -e "${CYAN}[DEBUG]${NC} $message"
            fi
            ;;
        *)
            echo "$message"
            ;;
    esac
}

# Function to run command with dry-run support
run_command() {
    local description="$1"
    shift
    local command="$*"

    if [ "$DRY_RUN" = true ]; then
        log "INFO" "[DRY-RUN] Would execute: $description"
        log "DEBUG" "Command: $command"
    else
        log "INFO" "Executing: $description"
        log "DEBUG" "Command: $command"
        eval "$command"
    fi
}

# Function to validate version format
validate_version() {
    local version="$1"

    # Remove 'v' prefix if present for validation
    local clean_version="${version#v}"

    # Check if it matches semantic versioning pattern
    if [[ ! "$clean_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        log "ERROR" "Invalid version format: $version"
        log "ERROR" "Version must follow semantic versioning (e.g., v2.1.0 or 2.1.0)"
        return 1
    fi

    return 0
}

# Function to normalize version (ensure v prefix)
normalize_version() {
    local version="$1"

    if [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "v$version"
    else
        echo "$version"
    fi
}

# Function to check if version exists
version_exists() {
    local version="$1"
    local docs_dir="$PROJECT_ROOT/docs/$version"
    local config_file="$PROJECT_ROOT/mkdocs-$version.yml"

    if [ -d "$docs_dir" ] || [ -f "$config_file" ]; then
        return 0
    else
        return 1
    fi
}

# Function to get current latest version
get_latest_version() {
    local versions_file="$PROJECT_ROOT/docs/versions.json"

    if [ -f "$versions_file" ]; then
        python3 -c "
import json
import sys
try:
    with open('$versions_file', 'r') as f:
        data = json.load(f)
    print(data.get('latest', ''))
except Exception as e:
    sys.exit(1)
" 2>/dev/null || echo ""
    else
        echo ""
    fi
}

# Function to check prerequisites
check_prerequisites() {
    log "DEBUG" "Checking prerequisites..."

    # Check if we're in the right directory
    if [ ! -f "$PROJECT_ROOT/pyproject.toml" ]; then
        log "ERROR" "Not in Nexus Platform project root (pyproject.toml not found)"
        return 1
    fi

    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        log "ERROR" "Python 3 is required but not found"
        return 1
    fi

    # Check if manage_versions.py exists
    if [ ! -f "$SCRIPT_DIR/manage_versions.py" ]; then
        log "ERROR" "manage_versions.py script not found"
        return 1
    fi

    # Check if docs directory exists
    if [ ! -d "$PROJECT_ROOT/docs" ]; then
        log "ERROR" "docs directory not found"
        return 1
    fi

    log "DEBUG" "Prerequisites check passed"
    return 0
}

# Function to get version from pyproject.toml
get_pyproject_version() {
    local pyproject_file="$PROJECT_ROOT/pyproject.toml"

    if [ -f "$pyproject_file" ]; then
        grep '^version = ' "$pyproject_file" | sed 's/version = "\(.*\)"/v\1/'
    else
        echo ""
    fi
}

# Function to suggest source version
suggest_source_version() {
    local latest_version
    latest_version=$(get_latest_version)

    if [ -n "$latest_version" ]; then
        echo "$latest_version"
    else
        # Fallback to pyproject version
        get_pyproject_version
    fi
}

# Function to create release
create_release() {
    local new_version="$1"
    local source_version="$2"

    log "INFO" "Creating documentation for version $new_version"

    # Determine source version if not specified
    if [ -z "$source_version" ]; then
        source_version=$(suggest_source_version)
        if [ -n "$source_version" ]; then
            log "INFO" "Using $source_version as source version"
        else
            log "WARN" "No source version specified and unable to determine latest"
            log "INFO" "Will create minimal documentation structure"
        fi
    fi

    # Check if source version exists (if specified)
    if [ -n "$source_version" ] && ! version_exists "$source_version"; then
        log "ERROR" "Source version $source_version does not exist"
        return 1
    fi

    # Create version using manage_versions.py
    local create_cmd="python3 '$SCRIPT_DIR/manage_versions.py' create '$new_version'"
    if [ -n "$source_version" ]; then
        create_cmd="$create_cmd --from '$source_version'"
    fi

    run_command "Create documentation version $new_version" "$create_cmd"

    return $?
}

# Function to set as latest version
set_latest_version() {
    local version="$1"

    log "INFO" "Setting $version as latest stable version"

    local set_latest_cmd="python3 '$SCRIPT_DIR/manage_versions.py' set-latest '$version'"
    run_command "Set $version as latest" "$set_latest_cmd"

    return $?
}

# Function to build documentation
build_documentation() {
    local version="$1"

    log "INFO" "Building documentation for $version"

    cd "$PROJECT_ROOT"

    # Check if Poetry is available
    if command -v poetry &> /dev/null; then
        local build_cmd="poetry run mkdocs build -f 'mkdocs-$version.yml' --strict"
    else
        local build_cmd="mkdocs build -f 'mkdocs-$version.yml' --strict"
    fi

    run_command "Build documentation for $version" "$build_cmd"

    return $?
}

# Function to display summary
display_summary() {
    local new_version="$1"
    local source_version="$2"

    echo ""
    log "INFO" "Documentation release summary:"
    echo -e "  ${CYAN}New Version:${NC} $new_version"
    if [ -n "$source_version" ]; then
        echo -e "  ${CYAN}Source Version:${NC} $source_version"
    fi
    echo -e "  ${CYAN}Set as Latest:${NC} $SET_AS_LATEST"
    echo -e "  ${CYAN}Build Docs:${NC} $BUILD_DOCS"
    echo -e "  ${CYAN}Dry Run:${NC} $DRY_RUN"
    echo ""

    if [ "$DRY_RUN" = false ]; then
        log "INFO" "Next steps:"
        echo "  1. Review the generated documentation"
        echo "  2. Test locally: ./scripts/docs/serve.sh $new_version"
        echo "  3. Commit and push changes to trigger deployment"
        echo ""
        echo "Files created/modified:"
        echo "  - docs/$new_version/ (documentation content)"
        echo "  - mkdocs-$new_version.yml (MkDocs configuration)"
        echo "  - docs/versions.json (version metadata)"
    fi
}

# Main function
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -s|--source)
                SOURCE_VERSION="$2"
                shift 2
                ;;
            -l|--set-latest)
                SET_AS_LATEST=true
                shift
                ;;
            -b|--build)
                BUILD_DOCS=true
                shift
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            -*)
                log "ERROR" "Unknown option: $1"
                usage
                exit 1
                ;;
            *)
                if [ -z "$NEW_VERSION" ]; then
                    NEW_VERSION="$1"
                else
                    log "ERROR" "Multiple versions specified: $NEW_VERSION and $1"
                    usage
                    exit 1
                fi
                shift
                ;;
        esac
    done

    # Validate required arguments
    if [ -z "$NEW_VERSION" ]; then
        log "ERROR" "New version is required"
        usage
        exit 1
    fi

    # Normalize and validate version
    NEW_VERSION=$(normalize_version "$NEW_VERSION")
    if ! validate_version "$NEW_VERSION"; then
        exit 1
    fi

    # Normalize source version if specified
    if [ -n "$SOURCE_VERSION" ]; then
        SOURCE_VERSION=$(normalize_version "$SOURCE_VERSION")
        if ! validate_version "$SOURCE_VERSION"; then
            exit 1
        fi
    fi

    log "INFO" "Starting documentation release process..."
    log "DEBUG" "Project root: $PROJECT_ROOT"

    # Check prerequisites
    if ! check_prerequisites; then
        exit 1
    fi

    # Check if version already exists
    if version_exists "$NEW_VERSION"; then
        log "ERROR" "Version $NEW_VERSION already exists"
        log "INFO" "Use 'python3 scripts/docs/manage_versions.py remove $NEW_VERSION' to remove it first"
        exit 1
    fi

    # Display summary before execution
    display_summary "$NEW_VERSION" "$SOURCE_VERSION"

    if [ "$DRY_RUN" = true ]; then
        log "INFO" "Dry run completed - no changes made"
        exit 0
    fi

    # Prompt for confirmation in interactive mode
    if [ -t 0 ] && [ -t 1 ]; then  # Check if running interactively
        echo -n "Proceed with creating documentation for $NEW_VERSION? [y/N]: "
        read -r confirmation
        case "$confirmation" in
            [yY]|[yY][eE][sS])
                log "INFO" "Proceeding with release..."
                ;;
            *)
                log "INFO" "Release cancelled"
                exit 0
                ;;
        esac
    fi

    # Create the release
    if ! create_release "$NEW_VERSION" "$SOURCE_VERSION"; then
        log "ERROR" "Failed to create documentation version"
        exit 1
    fi

    # Set as latest if requested
    if [ "$SET_AS_LATEST" = true ]; then
        if ! set_latest_version "$NEW_VERSION"; then
            log "ERROR" "Failed to set $NEW_VERSION as latest"
            exit 1
        fi
    fi

    # Build documentation if requested
    if [ "$BUILD_DOCS" = true ]; then
        if ! build_documentation "$NEW_VERSION"; then
            log "ERROR" "Failed to build documentation"
            exit 1
        fi
    fi

    log "INFO" "Documentation release completed successfully!"

    # Final summary
    echo ""
    log "INFO" "Release completed for version $NEW_VERSION"
    if [ "$SET_AS_LATEST" = true ]; then
        log "INFO" "Version $NEW_VERSION is now set as latest"
    fi
    if [ "$BUILD_DOCS" = true ]; then
        log "INFO" "Documentation has been built"
    fi

    echo ""
    log "INFO" "To test locally, run:"
    echo "  ./scripts/docs/serve.sh $NEW_VERSION"
    echo ""
    log "INFO" "To deploy, commit and push your changes:"
    echo "  git add ."
    echo "  git commit -m \"docs: add documentation for $NEW_VERSION\""
    echo "  git push origin main"
}

# Run main function
main "$@"
