#!/usr/bin/env python3
"""
Nexus Framework - Pre-Push Validation Script (Python Version)
============================================================================
This script runs all CI/CD pipeline checks locally before pushing to git.
It ensures code quality, tests, and build integrity.

Cross-platform Python version of the bash script.

Usage:
    python scripts/pre_push_check.py [--fix] [--fast] [--help]

Options:
    --fix     Automatically fix formatting and import issues
    --fast    Skip slower checks (coverage, security scan)
    --help    Show this help message
============================================================================
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


class Colors:
    """ANSI color codes for cross-platform terminal output."""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    BOLD = "\033[1m"
    NC = "\033[0m"  # No Color

    @classmethod
    def strip_colors(cls) -> None:
        """Remove colors for non-terminal output."""
        cls.RED = cls.GREEN = cls.YELLOW = cls.BLUE = cls.BOLD = cls.NC = ""


class PrePushChecker:
    """Main class for running pre-push validation checks."""

    def __init__(self, fix_mode: bool = False, fast_mode: bool = False):
        self.fix_mode = fix_mode
        self.fast_mode = fast_mode
        self.project_root = Path(__file__).parent.parent
        self.failed_checks: List[str] = []

        # Disable colors on Windows or non-TTY
        if os.name == "nt" or not sys.stdout.isatty():
            Colors.strip_colors()

    def print_header(self, text: str) -> None:
        """Print a section header."""
        print()
        print(f"{Colors.BOLD}{Colors.BLUE}====================================={Colors.NC}")
        print(f"{Colors.BOLD}{Colors.BLUE} {text}{Colors.NC}")
        print(f"{Colors.BOLD}{Colors.BLUE}====================================={Colors.NC}")

    def print_step(self, text: str) -> None:
        """Print a step message."""
        print(f"{Colors.YELLOW}> {text}{Colors.NC}")

    def print_success(self, text: str) -> None:
        """Print a success message."""
        print(f"{Colors.GREEN}[OK] {text}{Colors.NC}")

    def print_error(self, text: str) -> None:
        """Print an error message."""
        print(f"{Colors.RED}[ERROR] {text}{Colors.NC}")

    def print_warning(self, text: str) -> None:
        """Print a warning message."""
        print(f"{Colors.YELLOW}[WARNING] {text}{Colors.NC}")

    def print_info(self, text: str) -> None:
        """Print an info message."""
        print(f"{Colors.BLUE}[INFO] {text}{Colors.NC}")

    def run_command(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        capture_output: bool = False,
        check: bool = True,
    ) -> Tuple[int, str, str]:
        """Run a command and return the result."""
        if cwd is None:
            cwd = self.project_root

        try:
            result = subprocess.run(
                cmd, cwd=cwd, capture_output=capture_output, text=True, check=check
            )
            return (
                result.returncode,
                result.stdout if capture_output else "",
                result.stderr if capture_output else "",
            )
        except subprocess.CalledProcessError as e:
            return (
                e.returncode,
                e.stdout if capture_output else "",
                e.stderr if capture_output else "",
            )
        except FileNotFoundError:
            return 1, "", f"Command not found: {cmd[0]}"

    def check_project_root(self) -> bool:
        """Verify we're in the correct project directory."""
        if not (self.project_root / "pyproject.toml").exists():
            self.print_error("Not in Nexus project root! Please run from project directory.")
            return False
        return True

    def check_poetry(self) -> bool:
        """Check if Poetry is available."""
        if shutil.which("poetry") is None:
            self.print_error("Poetry is not installed or not in PATH!")
            self.print_info("Install poetry: https://python-poetry.org/docs/#installation")
            self.print_info("On Windows: python -m pip install poetry")
            self.print_info("On Unix: curl -sSL https://install.python-poetry.org | python3 -")
            return False

        # Verify poetry is working
        returncode, stdout, stderr = self.run_command(
            ["poetry", "--version"], capture_output=True, check=False
        )
        if returncode != 0:
            self.print_error("Poetry installation appears broken!")
            self.print_info(f"Error: {stderr}")
            return False

        return True

    def check_dependencies(self) -> bool:
        """Check and install dependencies."""
        self.print_step("Checking dependencies...")

        # Configure Poetry for better Windows compatibility
        self.print_step("Configuring Poetry...")
        self.run_command(["poetry", "config", "virtualenvs.create", "true"], check=False)
        self.run_command(["poetry", "config", "virtualenvs.in-project", "true"], check=False)

        # Check poetry configuration
        returncode, stdout, stderr = self.run_command(
            ["poetry", "check"], capture_output=True, check=False
        )
        if returncode != 0:
            self.print_warning("Poetry configuration issues detected")
            print(stderr)

        # Install dependencies
        self.print_step("Installing/updating dependencies...")

        # On Windows, use --no-cache to avoid permission issues
        if os.name == "nt":
            cmd = ["poetry", "install", "--no-interaction", "--with", "dev,test", "--no-cache"]
        else:
            cmd = ["poetry", "install", "--no-interaction", "--with", "dev,test"]

        returncode, stdout, stderr = self.run_command(cmd, capture_output=True, check=False)

        if returncode == 0:
            self.print_success("Dependencies ready")
            return True
        else:
            self.print_error("Failed to install dependencies")
            if stderr:
                print(f"Error output: {stderr}")
            return False

    def check_git_status(self) -> None:
        """Check git status and show uncommitted changes."""
        self.print_step("Checking git status...")

        returncode, stdout, _ = self.run_command(
            ["git", "status", "--porcelain"], capture_output=True, check=False
        )

        if returncode == 0 and stdout.strip():
            self.print_info("Uncommitted changes detected:")
            self.run_command(["git", "status", "--short"])
            print()
        else:
            self.print_success("Working directory clean")

    def run_formatting_check(self) -> bool:
        """Run Black formatting check/fix."""
        self.print_step("Checking code formatting (Black)...")

        paths = ["nexus/", "tests/", "scripts/"]

        if self.fix_mode:
            returncode, _, _ = self.run_command(["poetry", "run", "black"] + paths)
            if returncode == 0:
                self.print_success("Code formatted automatically")
                return True
            else:
                self.print_error("Failed to format code")
                return False
        else:
            returncode, _, _ = self.run_command(
                ["poetry", "run", "black", "--check", "--diff"] + paths, check=False
            )
            if returncode == 0:
                self.print_success("Code formatting is correct")
                return True
            else:
                self.print_error("Code formatting issues found!")
                self.print_info(
                    "Run with --fix to auto-format, or run: poetry run black nexus/ tests/ scripts/"
                )
                return False

    def run_import_sorting(self) -> bool:
        """Run isort import sorting check/fix."""
        self.print_step("Checking import sorting (isort)...")

        paths = ["nexus/", "tests/", "scripts/"]

        if self.fix_mode:
            returncode, _, _ = self.run_command(["poetry", "run", "isort"] + paths)
            if returncode == 0:
                self.print_success("Imports sorted automatically")
                return True
            else:
                self.print_error("Failed to sort imports")
                return False
        else:
            returncode, _, _ = self.run_command(
                ["poetry", "run", "isort", "--check-only", "--diff"] + paths, check=False
            )
            if returncode == 0:
                self.print_success("Import sorting is correct")
                return True
            else:
                self.print_error("Import sorting issues found!")
                self.print_info(
                    "Run with --fix to auto-sort, or run: poetry run isort nexus/ tests/ scripts/"
                )
                return False

    def run_linting(self) -> bool:
        """Run Flake8 linting."""
        self.print_step("Running linter (Flake8)...")

        returncode, _, _ = self.run_command(
            [
                "poetry",
                "run",
                "flake8",
                "nexus/",
                "tests/",
                "scripts/",
                "--count",
                "--select=E9,F63,F7,F82",
                "--show-source",
                "--statistics",
            ],
            check=False,
        )

        if returncode == 0:
            self.print_success("No critical lint issues found")
            return True
        else:
            self.print_error("Critical lint issues found!")
            return False

    def run_type_checking(self) -> bool:
        """Run MyPy type checking."""
        self.print_step("Running type checker (MyPy)...")

        returncode, _, _ = self.run_command(["poetry", "run", "mypy", "nexus/"], check=False)

        if returncode == 0:
            self.print_success("Type checking passed")
            return True
        else:
            self.print_error("Type checking failed!")
            return False

    def run_security_scan(self) -> bool:
        """Run Bandit security scan."""
        if self.fast_mode:
            self.print_warning("Skipping security scan (fast mode)")
            return True

        self.print_step("Running security scan (Bandit)...")

        report_file = self.project_root / "bandit-report.json"
        returncode, _, _ = self.run_command(
            [
                "poetry",
                "run",
                "bandit",
                "-r",
                "nexus/",
                "-f",
                "json",
                "-o",
                str(report_file),
                "--quiet",
            ],
            check=False,
        )

        if returncode == 0:
            # Check the report for issues
            try:
                with open(report_file, "r") as f:
                    report = json.load(f)
                    issues = len(report.get("results", []))

                if issues == 0:
                    self.print_success("No security issues found")
                    return True
                else:
                    self.print_error(f"Security issues found! Check {report_file}")
                    return False
            except (json.JSONDecodeError, FileNotFoundError):
                self.print_error("Failed to read security scan report")
                return False
        else:
            self.print_error("Security scan failed!")
            return False

    def run_unit_tests(self) -> bool:
        """Run unit tests."""
        self.print_step("Running unit tests...")

        cmd = [
            "poetry",
            "run",
            "pytest",
            "tests/unit/",
            "--tb=short",
            "--asyncio-mode=auto",
            "--log-cli-level=WARNING",
            "--disable-warnings",
            "--maxfail=5",
        ]

        if not self.fast_mode:
            cmd.extend(
                [
                    "--cov=nexus",
                    "--cov-branch",
                    "--cov-report=xml",
                    "--cov-report=html",
                    "--cov-report=term-missing",
                    "--cov-fail-under=20",
                ]
            )

        # Windows-specific environment setup
        env = os.environ.copy()
        if os.name == "nt":
            env["PYTHONHASHSEED"] = "0"
            env["PYTHONASYNCIODEBUG"] = "0"  # Disable on Windows to avoid issues

        returncode, _, _ = self.run_command(cmd, check=False)

        if returncode == 0:
            self.print_success("Unit tests passed")
            return True
        else:
            self.print_error("Unit tests failed!")
            return False

    def run_integration_tests(self) -> bool:
        """Run integration tests."""
        self.print_step("Running integration tests...")

        returncode, _, _ = self.run_command(
            [
                "poetry",
                "run",
                "pytest",
                "tests/integration/",
                "--tb=short",
                "--asyncio-mode=auto",
                "--disable-warnings",
                "--maxfail=3",
            ],
            check=False,
        )

        if returncode == 0:
            self.print_success("Integration tests passed")
            return True
        else:
            self.print_error("Integration tests failed!")
            return False

    def run_build_check(self) -> bool:
        """Test package build."""
        self.print_step("Testing package build...")

        # Clean previous builds
        for path in ["dist", "build"]:
            full_path = self.project_root / path
            if full_path.exists():
                shutil.rmtree(full_path)

        # Find and remove egg-info directories
        for egg_info in self.project_root.glob("*.egg-info"):
            shutil.rmtree(egg_info)

        # Build package
        returncode, _, _ = self.run_command(["poetry", "build", "--no-interaction"], check=False)

        if returncode != 0:
            self.print_error("Package build failed!")
            return False

        self.print_success("Package built successfully")

        # Check package integrity
        self.print_step("Checking package integrity...")
        returncode, _, _ = self.run_command(
            ["poetry", "run", "twine", "check", "dist/*"], check=False
        )

        if returncode == 0:
            self.print_success("Package integrity verified")
            return True
        else:
            self.print_error("Package integrity check failed!")
            return False

    def _check_todo_fixme_comments(self) -> None:
        """Check for TODO/FIXME comments."""
        try:
            result = subprocess.run(
                ["grep", "-r", "TODO\\|FIXME", "nexus/", "--include=*.py"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0 and result.stdout.strip():
                self.print_warning("TODO/FIXME comments found in source code:")
                lines = result.stdout.strip().split("\n")
                for line in lines[:5]:
                    print(f"  {line}")
                if len(lines) > 5:
                    print(f"  ... and {len(lines) - 5} more")
                print()
        except FileNotFoundError:
            pass  # grep not available (Windows)

    def _check_debug_statements(self) -> bool:
        """Check for debug statements. Returns True if issues found."""
        debug_patterns = ["print(", "pdb", "breakpoint()"]
        for pattern in debug_patterns:
            try:
                result = subprocess.run(
                    ["grep", "-r", pattern, "nexus/", "--include=*.py"],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode == 0 and result.stdout.strip():
                    self.print_warning(f"Debug statements found in source code ({pattern}):")
                    lines = result.stdout.strip().split("\n")
                    for line in lines[:3]:
                        print(f"  {line}")
                    return True
            except FileNotFoundError:
                pass
        return False

    def _check_large_files(self) -> bool:
        """Check for large files. Returns True if issues found."""
        large_files = []
        for path in self.project_root.rglob("*.py"):
            if path.is_file() and path.stat().st_size > 100 * 1024:  # 100KB
                large_files.append(str(path.relative_to(self.project_root)))

        if large_files:
            self.print_warning("Large files detected:")
            for file in large_files:
                print(f"  {file}")
            return True
        return False

    def run_diagnostic_check(self) -> None:
        """Run additional diagnostic checks."""
        self.print_step("Running diagnostic checks...")

        issues = 0

        self._check_todo_fixme_comments()

        if self._check_debug_statements():
            issues += 1

        if self._check_large_files():
            issues += 1

        if issues == 0:
            self.print_success("Diagnostic checks passed")
        else:
            self.print_warning("Some diagnostic issues found (non-blocking)")

    def setup_git_hooks(self) -> None:
        """Set up git hooks."""
        self.print_step("Setting up git hooks...")

        hooks_dir = self.project_root / ".git" / "hooks"
        if not hooks_dir.exists():
            self.print_warning("Git hooks directory not found (not a git repo?)")
            return

        pre_commit_hook = hooks_dir / "pre-commit"

        hook_content = """#!/bin/bash
# Auto-generated pre-commit hook for Nexus Framework

echo "Running pre-commit checks..."
if ! python scripts/pre_push_check.py; then
    echo ""
    echo "[ERROR] Pre-commit checks failed!"
    echo "TIP: Fix issues or run: python scripts/pre_push_check.py --fix"
    exit 1
fi
"""

        with open(pre_commit_hook, "w") as f:
            f.write(hook_content)

        # Make executable on Unix-like systems
        if os.name != "nt":
            pre_commit_hook.chmod(0o755)

        self.print_success("Git hooks configured")
        self.print_info("💡: Hooks are also available in .githooks/ directory for version control")
        self.print_info("   You can also run: git config core.hooksPath .githooks")

    def calculate_metrics(self) -> None:
        """Calculate and display project metrics."""
        self.print_step("Calculating project metrics...")

        source_files = list(self.project_root.glob("nexus/**/*.py"))
        test_files = list(self.project_root.glob("tests/**/*.py"))

        source_lines = sum(
            len(file.read_text(encoding="utf-8").splitlines())
            for file in source_files
            if file.is_file()
        )

        test_lines = sum(
            len(file.read_text(encoding="utf-8").splitlines())
            for file in test_files
            if file.is_file()
        )

        print()
        self.print_info("Project Metrics:")
        print(f"  Source files: {len(source_files)}")
        print(f"  Source lines: {source_lines}")
        print(f"  Test files: {len(test_files)}")
        print(f"  Test lines: {test_lines}")
        if source_lines > 0:
            test_ratio = (test_lines * 100) / source_lines
            print(f"  Test ratio: {test_ratio:.1f}%")

    def run_all_checks(self) -> bool:
        """Run all validation checks."""
        start_time = time.time()

        # Header
        print(f"{Colors.BOLD}{Colors.GREEN}Nexus Framework - Pre-Push Validation{Colors.NC}")
        print(f"{Colors.BLUE}Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.NC}")
        mode = "Auto-fix" if self.fix_mode else "Check-only"
        if self.fast_mode:
            mode += " (Fast)"
        print(f"{Colors.BLUE}Mode: {mode}{Colors.NC}")
        print()

        # Preliminary checks
        if not self.check_project_root():
            return False
        if not self.check_poetry():
            return False
        if not self.check_dependencies():
            return False

        self.check_git_status()

        # Code Quality Pipeline
        self.print_header("CODE QUALITY CHECKS")

        checks = [
            ("Formatting", self.run_formatting_check),
            ("Import Sorting", self.run_import_sorting),
            ("Linting", self.run_linting),
            ("Type Checking", self.run_type_checking),
            ("Security Scan", self.run_security_scan),
        ]

        for check_name, check_func in checks:
            if not check_func():
                self.failed_checks.append(check_name)

        # Test Pipeline
        self.print_header("TEST SUITE")

        test_checks = [
            ("Unit Tests", self.run_unit_tests),
            ("Integration Tests", self.run_integration_tests),
        ]

        for check_name, check_func in test_checks:
            if not check_func():
                self.failed_checks.append(check_name)

        # Build Pipeline
        self.print_header("BUILD & PACKAGE")

        if not self.run_build_check():
            self.failed_checks.append("Build Check")

        # Additional Checks
        self.print_header("ADDITIONAL CHECKS")

        self.run_diagnostic_check()
        self.setup_git_hooks()

        if not self.fast_mode:
            self.calculate_metrics()

        # Summary
        end_time = time.time()
        duration = int(end_time - start_time)

        self.print_header("SUMMARY")

        if not self.failed_checks:
            self.print_success("All checks passed!")
            self.print_success("Ready to push to git!")
            print()
            self.print_info(f"Total time: {duration}s")

            # Suggest next steps
            print()
            print(f"{Colors.BOLD}Next steps:{Colors.NC}")
            print("  git add .")
            print('  git commit -m "Your commit message"')
            print("  git push")

            return True
        else:
            self.print_error(f"Failed checks: {', '.join(self.failed_checks)}")
            print()
            self.print_info(f"Total time: {duration}s")

            # Suggest fixes
            print()
            print(f"{Colors.BOLD}Quick fixes:{Colors.NC}")
            print("  # Fix formatting and imports:")
            print("  python scripts/pre_push_check.py --fix")
            print()
            print("  # Run specific tools:")
            print("  poetry run black nexus/ tests/ scripts/")
            print("  poetry run isort nexus/ tests/ scripts/")
            print("  poetry run mypy nexus/")
            print("  poetry run pytest tests/unit/")

            return False


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Nexus Framework Pre-Push Validation Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/pre_push_check.py                    # Run all checks
  python scripts/pre_push_check.py --fix              # Run and auto-fix issues
  python scripts/pre_push_check.py --fast             # Quick check only
  python scripts/pre_push_check.py --fix --fast       # Quick fix and check
        """,
    )

    parser.add_argument(
        "--fix", action="store_true", help="Automatically fix formatting and import issues"
    )

    parser.add_argument(
        "--fast", action="store_true", help="Skip slower checks (coverage, security scan)"
    )

    args = parser.parse_args()

    # Handle Ctrl+C gracefully
    try:
        checker = PrePushChecker(fix_mode=args.fix, fast_mode=args.fast)
        success = checker.run_all_checks()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Script interrupted by user{Colors.NC}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}[ERROR] Unexpected error: {e}{Colors.NC}")
        if os.name == "nt":
            print(
                f"{Colors.BLUE}[INFO] On Windows, try running as Administrator or use: python -m pip install --upgrade poetry{Colors.NC}"
            )
        sys.exit(1)


if __name__ == "__main__":
    main()
