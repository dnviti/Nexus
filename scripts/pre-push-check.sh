#!/bin/bash

# ============================================================================
# Nexus Framework - Pre-Push Validation Script
# ============================================================================
# This script runs all CI/CD pipeline checks locally before pushing to git.
# It ensures code quality, tests, and build integrity.
#
# Usage:
#   ./scripts/pre-push-check.sh [--fix] [--fast] [--help]
#
# Options:
#   --fix     Automatically fix formatting and import issues
#   --fast    Skip slower checks (coverage, security scan)
#   --help    Show this help message
# ============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Default options
FIX_MODE=false
FAST_MODE=false
SHOW_HELP=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX_MODE=true
            shift
            ;;
        --fast)
            FAST_MODE=true
            shift
            ;;
        --help|-h)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Help message
if [ "$SHOW_HELP" = true ]; then
    echo -e "${BOLD}Nexus Framework - Pre-Push Validation Script${NC}"
    echo ""
    echo "This script runs all CI/CD pipeline checks locally before pushing to git."
    echo ""
    echo -e "${BOLD}Usage:${NC}"
    echo "  ./scripts/pre-push-check.sh [OPTIONS]"
    echo ""
    echo -e "${BOLD}Options:${NC}"
    echo "  --fix     Automatically fix formatting and import issues"
    echo "  --fast    Skip slower checks (coverage, security scan)"
    echo "  --help    Show this help message"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  ./scripts/pre-push-check.sh                    # Run all checks"
    echo "  ./scripts/pre-push-check.sh --fix              # Run and auto-fix issues"
    echo "  ./scripts/pre-push-check.sh --fast             # Quick check only"
    echo "  ./scripts/pre-push-check.sh --fix --fast       # Quick fix and check"
    echo ""
    exit 0
fi

# Utility functions
print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}=====================================${NC}"
    echo -e "${BOLD}${BLUE} $1${NC}"
    echo -e "${BOLD}${BLUE}=====================================${NC}"
}

print_step() {
    echo -e "${YELLOW}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if we're in the project root
check_project_root() {
    if [ ! -f "$PROJECT_ROOT/pyproject.toml" ]; then
        print_error "Not in Nexus project root! Please run from project directory."
        exit 1
    fi
}

# Check if poetry is available
check_poetry() {
    if ! command -v poetry &> /dev/null; then
        print_error "Poetry is not installed or not in PATH!"
        print_info "Install poetry: https://python-poetry.org/docs/#installation"
        exit 1
    fi
}

# Check if dependencies are installed
check_dependencies() {
    print_step "Checking dependencies..."
    cd "$PROJECT_ROOT"

    if ! poetry check &> /dev/null; then
        print_warning "Poetry configuration issues detected"
        poetry check
    fi

    print_step "Installing/updating dependencies..."
    poetry install --no-interaction --with dev,test
    print_success "Dependencies ready"
}

# Git status check
check_git_status() {
    print_step "Checking git status..."

    if [ -n "$(git status --porcelain)" ]; then
        print_info "Uncommitted changes detected:"
        git status --short
        echo ""
    else
        print_success "Working directory clean"
    fi
}

# Code Quality Checks
run_formatting_check() {
    print_step "Checking code formatting (Black)..."

    if [ "$FIX_MODE" = true ]; then
        poetry run black nexus/ tests/ scripts/
        print_success "Code formatted automatically"
    else
        if poetry run black --check --diff nexus/ tests/ scripts/; then
            print_success "Code formatting is correct"
        else
            print_error "Code formatting issues found!"
            print_info "Run with --fix to auto-format, or run: poetry run black nexus/ tests/ scripts/"
            return 1
        fi
    fi
}

run_import_sorting() {
    print_step "Checking import sorting (isort)..."

    if [ "$FIX_MODE" = true ]; then
        poetry run isort nexus/ tests/ scripts/
        print_success "Imports sorted automatically"
    else
        if poetry run isort --check-only --diff nexus/ tests/ scripts/; then
            print_success "Import sorting is correct"
        else
            print_error "Import sorting issues found!"
            print_info "Run with --fix to auto-sort, or run: poetry run isort nexus/ tests/ scripts/"
            return 1
        fi
    fi
}

run_linting() {
    print_step "Running linter (Flake8)..."

    # Run critical errors only (as per CI pipeline)
    if poetry run flake8 nexus/ tests/ scripts/ --count --select=E9,F63,F7,F82 --show-source --statistics; then
        print_success "No critical lint issues found"
    else
        print_error "Critical lint issues found!"
        return 1
    fi
}

run_type_checking() {
    print_step "Running type checker (MyPy)..."

    if poetry run mypy nexus/; then
        print_success "Type checking passed"
    else
        print_error "Type checking failed!"
        return 1
    fi
}

run_security_scan() {
    if [ "$FAST_MODE" = true ]; then
        print_warning "Skipping security scan (fast mode)"
        return 0
    fi

    print_step "Running security scan (Bandit)..."

    # Run bandit and capture results
    if poetry run bandit -r nexus/ -f json -o bandit-report.json --quiet; then
        # Check if any issues were found
        local issues=$(jq '.results | length' bandit-report.json 2>/dev/null || echo "0")
        if [ "$issues" -eq 0 ]; then
            print_success "No security issues found"
        else
            print_error "Security issues found! Check bandit-report.json"
            return 1
        fi
    else
        print_error "Security scan failed!"
        return 1
    fi
}

# Test Suite
run_unit_tests() {
    print_step "Running unit tests..."

    local test_args=(
        "tests/unit/"
        "--tb=short"
        "--asyncio-mode=auto"
        "--log-cli-level=WARNING"
        "--disable-warnings"
        "--maxfail=5"
    )

    if [ "$FAST_MODE" = false ]; then
        test_args+=(
            "--cov=nexus"
            "--cov-branch"
            "--cov-report=xml"
            "--cov-report=html"
            "--cov-report=term-missing"
            "--cov-fail-under=20"
        )
    fi

    if poetry run pytest "${test_args[@]}"; then
        print_success "Unit tests passed"
    else
        print_error "Unit tests failed!"
        return 1
    fi
}

run_integration_tests() {
    print_step "Running integration tests..."

    if poetry run pytest tests/integration/ --tb=short --asyncio-mode=auto --disable-warnings --maxfail=3; then
        print_success "Integration tests passed"
    else
        print_error "Integration tests failed!"
        return 1
    fi
}

# Build and Package
run_build_check() {
    print_step "Testing package build..."

    # Clean previous builds
    rm -rf dist/ build/ *.egg-info/

    if poetry build --no-interaction; then
        print_success "Package built successfully"
    else
        print_error "Package build failed!"
        return 1
    fi

    # Check package integrity
    print_step "Checking package integrity..."
    if poetry run twine check dist/*; then
        print_success "Package integrity verified"
    else
        print_error "Package integrity check failed!"
        return 1
    fi
}

# Documentation build and linting check
run_documentation_check() {
    if [ "$FAST_MODE" = true ]; then
        print_warning "Skipping documentation checks (fast mode)"
        return 0
    fi

    print_step "Running documentation checks..."

    # Check if mkdocs config exists
    if [ ! -f "mkdocs.yml" ]; then
        print_error "mkdocs.yml not found!"
        return 1
    fi

    # Run documentation linting first
    if ! run_documentation_linting; then
        return 1
    fi

    # Test documentation build
    print_step "Testing documentation build with mkdocs.yml..."
    if poetry run mkdocs build --config-file mkdocs.yml --site-dir test-site; then
        print_success "Build successful for mkdocs.yml"

        # Verify Mermaid integration
        print_step "Verifying Mermaid integration..."
        if find test-site -name "*.html" -exec grep -l "mermaid" {} \; | head -1 > /dev/null; then
            print_success "Mermaid integration verified"
        else
            print_warning "Mermaid integration not found in built docs"
        fi

        # Clean up test site
        rm -rf test-site
        return 0
    else
        print_error "Build failed for mkdocs.yml"
        return 1
    fi
}

# Documentation linting
run_documentation_linting() {
    print_step "Linting documentation..."

    local lint_success=true

    # Check markdown links
    if ! check_markdown_links; then
        lint_success=false
    fi

    # Verify documentation structure
    if ! verify_documentation_structure; then
        lint_success=false
    fi

    if [ "$lint_success" = true ]; then
        print_success "Documentation linting passed"
        return 0
    else
        print_error "Documentation linting failed"
        return 1
    fi
}

# Check markdown links
check_markdown_links() {
    print_step "Checking markdown links..."

    if [ ! -d "docs" ]; then
        print_warning "No docs directory found, skipping link check"
        return 0
    fi

    # Check if markdown-link-check is available
    if ! command -v markdown-link-check >/dev/null 2>&1; then
        print_warning "markdown-link-check not found. Install with: npm install -g markdown-link-check"
        return 0  # Don't fail if tool is not available
    fi

    # Find all markdown files
    local md_files=$(find docs -name "*.md" -type f)
    if [ -z "$md_files" ]; then
        print_warning "No markdown files found in docs/"
        return 0
    fi

    local config_file=".github/markdown-link-check.json"
    local failed_files=""
    local total_files=0

    # Check links in each markdown file
    for md_file in $md_files; do
        total_files=$((total_files + 1))
        local cmd="markdown-link-check"

        if [ -f "$config_file" ]; then
            cmd="$cmd -c $config_file"
        fi

        if ! $cmd "$md_file" >/dev/null 2>&1; then
            failed_files="$failed_files$md_file\n"
        fi
    done

    if [ -n "$failed_files" ]; then
        print_error "Link check failed for files:"
        printf "$failed_files" | while read -r file; do
            if [ -n "$file" ]; then
                echo "  ✗ $file"
            fi
        done
        return 1
    else
        print_success "Link check passed for $total_files files"
        return 0
    fi
}

# Verify documentation structure
verify_documentation_structure() {
    print_step "Verifying documentation structure..."

    if [ ! -d "docs" ]; then
        print_error "docs/ directory not found!"
        return 1
    fi

    # Check for required files
    local required_files="index.md"
    local missing_files=""

    for file in $required_files; do
        if [ ! -f "docs/$file" ]; then
            missing_files="$missing_files $file"
        fi
    done

    if [ -n "$missing_files" ]; then
        print_error "Missing required documentation files:$missing_files"
        return 1
    fi

    # Count markdown files
    local md_count=$(find docs -name "*.md" -type f | wc -l)
    print_success "Documentation structure verified - $md_count markdown files found"

    return 0
}

# Diagnostic checks
run_diagnostic_check() {
    print_step "Running diagnostic checks..."

    # Check for common issues
    local issues=0

    # Check for TODO/FIXME comments in critical files
    if grep -r "TODO\|FIXME" nexus/ --include="*.py" &> /dev/null; then
        print_warning "TODO/FIXME comments found in source code:"
        grep -r "TODO\|FIXME" nexus/ --include="*.py" -n | head -5
        if [ $(grep -r "TODO\|FIXME" nexus/ --include="*.py" | wc -l) -gt 5 ]; then
            echo "  ... and $(( $(grep -r "TODO\|FIXME" nexus/ --include="*.py" | wc -l) - 5 )) more"
        fi
        echo ""
    fi

    # Check for debug statements
    if grep -r "print(\|pdb\|breakpoint()" nexus/ --include="*.py" &> /dev/null; then
        print_warning "Debug statements found in source code:"
        grep -r "print(\|pdb\|breakpoint()" nexus/ --include="*.py" -n | head -3
        issues=$((issues + 1))
    fi

    # Check for large files (exclude build artifacts)
    local large_files=$(find nexus/ tests/ -type f -size +100k \
        -not -path "*/__pycache__/*" \
        -not -path "*/.*" \
        -not -path "*/htmlcov/*" \
        -not -path "*/logs/*" \
        -not -path "*/dist/*" \
        -not -path "*/build/*" \
        -not -path "*/site/*" \
        -not -name "*.pyc" \
        -not -name "*.pyo" \
        -not -name "*.so" \
        -not -name "*.egg-info" \
        -not -name "coverage.xml" \
        -not -name "poetry.lock" \
        -not -name ".coverage" \
        2>/dev/null || true)
    if [ -n "$large_files" ]; then
        print_warning "Large files detected:"
        echo "$large_files"
        issues=$((issues + 1))
    fi

    if [ $issues -eq 0 ]; then
        print_success "Diagnostic checks passed"
    else
        print_warning "Some diagnostic issues found (non-blocking)"
    fi
}

# Git hooks setup
setup_git_hooks() {
    print_step "Setting up git hooks..."

    local hooks_dir="$PROJECT_ROOT/.git/hooks"
    local pre_commit_hook="$hooks_dir/pre-commit"

    # Create pre-commit hook that runs this script
    cat > "$pre_commit_hook" << 'EOF'
#!/bin/bash
# Auto-generated pre-commit hook for Nexus Framework

echo "Running pre-commit checks..."
if ! ./scripts/pre-push-check.sh --fast; then
    echo ""
    echo "❌ Pre-commit checks failed!"
    echo "💡 Fix issues or run: ./scripts/pre-push-check.sh --fix"
    exit 1
fi
EOF

    chmod +x "$pre_commit_hook"
    print_success "Git hooks configured"
}

# Performance metrics
calculate_metrics() {
    print_step "Calculating project metrics..."

    local total_lines=$(find nexus/ -name "*.py" -exec wc -l {} + | tail -1 | awk '{print $1}')
    local test_lines=$(find tests/ -name "*.py" -exec wc -l {} + | tail -1 | awk '{print $1}')
    local total_files=$(find nexus/ -name "*.py" | wc -l)
    local test_files=$(find tests/ -name "*.py" | wc -l)

    echo ""
    print_info "Project Metrics:"
    echo "  📁 Source files: $total_files"
    echo "  📝 Source lines: $total_lines"
    echo "  🧪 Test files: $test_files"
    echo "  📋 Test lines: $test_lines"
    echo "  📊 Test ratio: $(echo "scale=1; $test_lines * 100 / $total_lines" | bc -l)%"
}

# Main execution
main() {
    # Header
    echo -e "${BOLD}${GREEN}🚀 Nexus Framework - Pre-Push Validation${NC}"
    echo -e "${BLUE}Started at: $TIMESTAMP${NC}"
    echo -e "${BLUE}Mode: $([ "$FIX_MODE" = true ] && echo "Auto-fix" || echo "Check-only")$([ "$FAST_MODE" = true ] && echo " (Fast)" || "")${NC}"
    echo ""

    # Track timing
    local start_time=$(date +%s)
    local failed_checks=()

    # Preliminary checks
    check_project_root
    check_poetry
    check_dependencies
    check_git_status

    # Code Quality Pipeline
    print_header "CODE QUALITY CHECKS"

    if ! run_formatting_check; then
        failed_checks+=("Formatting")
    fi

    if ! run_import_sorting; then
        failed_checks+=("Import Sorting")
    fi

    if ! run_linting; then
        failed_checks+=("Linting")
    fi

    if ! run_type_checking; then
        failed_checks+=("Type Checking")
    fi

    if ! run_security_scan; then
        failed_checks+=("Security Scan")
    fi

    # Test Pipeline
    print_header "TEST SUITE"

    if ! run_unit_tests; then
        failed_checks+=("Unit Tests")
    fi

    if ! run_integration_tests; then
        failed_checks+=("Integration Tests")
    fi

    # Build Pipeline
    print_header "BUILD & PACKAGE"

    if ! run_build_check; then
        failed_checks+=("Build Check")
    fi

    # Documentation Pipeline
    print_header "DOCUMENTATION"

    if ! run_documentation_check; then
        failed_checks+=("Documentation Build")
    fi

    # Additional Checks
    print_header "ADDITIONAL CHECKS"

    run_diagnostic_check
    setup_git_hooks

    if [ "$FAST_MODE" = false ]; then
        calculate_metrics
    fi

    # Summary
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    print_header "SUMMARY"

    if [ ${#failed_checks[@]} -eq 0 ]; then
        print_success "All checks passed! ✨"
        print_success "Ready to push to git! 🚀"
        echo ""
        print_info "Total time: ${duration}s"

        # Suggest next steps
        echo ""
        echo -e "${BOLD}Next steps:${NC}"
        echo "  git add ."
        echo "  git commit -m \"Your commit message\""
        echo "  git push"

        exit 0
    else
        print_error "Failed checks: ${failed_checks[*]}"
        echo ""
        print_info "Total time: ${duration}s"

        # Suggest fixes
        echo ""
        echo -e "${BOLD}Quick fixes:${NC}"
        echo "  # Fix formatting and imports:"
        echo "  ./scripts/pre-push-check.sh --fix"
        echo ""
        echo "  # Run specific tools:"
        echo "  poetry run black nexus/ tests/ scripts/"
        echo "  poetry run isort nexus/ tests/ scripts/"
        echo "  poetry run mypy nexus/"
        echo "  poetry run pytest tests/unit/"
        echo "  poetry run mkdocs build -f mkdocs.yml"

        exit 1
    fi
}

# Trap ctrl+c and cleanup
trap 'echo -e "\n${YELLOW}Script interrupted by user${NC}"; exit 130' INT

# Run main function
main "$@"
