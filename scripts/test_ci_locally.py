#!/usr/bin/env python3
"""
Local CI Test Script

This script runs the same checks that the CI pipeline runs,
allowing you to verify your changes locally before pushing.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple


class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class TestRunner:
    """Runs CI tests locally."""

    def __init__(self, fast_mode: bool = False, verbose: bool = False):
        self.fast_mode = fast_mode
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent
        self.results: Dict[str, bool] = {}

    def print_header(self, text: str) -> None:
        """Print a formatted header."""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")

    def print_status(self, test_name: str, success: bool, details: str = "") -> None:
        """Print test status with color coding."""
        status = (
            f"{Colors.OKGREEN}✅ PASS{Colors.ENDC}"
            if success
            else f"{Colors.FAIL}❌ FAIL{Colors.ENDC}"
        )
        print(f"{status} {test_name}")
        if details and (not success or self.verbose):
            print(f"   {details}")

    def run_command(self, cmd: List[str], description: str) -> Tuple[bool, str]:
        """Run a command and return success status and output."""
        if self.verbose:
            print(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=300 if not self.fast_mode else 60,
            )

            success = result.returncode == 0
            output = result.stdout + result.stderr

            if not success and self.verbose:
                print(f"Command failed with exit code {result.returncode}")
                print(f"Output: {output}")

            return success, output

        except subprocess.TimeoutExpired:
            return False, f"Command timed out: {' '.join(cmd)}"
        except Exception as e:
            return False, f"Error running command: {e}"

    def check_prerequisites(self) -> bool:
        """Check if required tools are available."""
        self.print_header("Checking Prerequisites")

        tools = [
            ("python", ["python", "--version"]),
            ("poetry", ["poetry", "--version"]),
        ]

        all_good = True
        for tool_name, cmd in tools:
            success, output = self.run_command(cmd, f"Check {tool_name}")
            self.print_status(
                f"{tool_name} available",
                success,
                output.strip() if success else f"Command not found: {tool_name}",
            )
            if not success:
                all_good = False

        # Check if we're in a Poetry project
        if (self.project_root / "pyproject.toml").exists():
            self.print_status("Poetry project detected", True, "pyproject.toml found")
        else:
            self.print_status("Poetry project detected", False, "pyproject.toml not found")
            all_good = False

        return all_good

    def install_dependencies(self) -> bool:
        """Install project dependencies."""
        self.print_header("Installing Dependencies")

        # Install dependencies
        success, output = self.run_command(
            ["poetry", "install", "--no-interaction", "--with", "dev,test"], "Install dependencies"
        )

        self.print_status(
            "Dependency installation", success, "Dependencies installed" if success else output
        )

        if success and self.verbose:
            # Show dependency tree
            success2, tree_output = self.run_command(
                ["poetry", "show", "--tree"], "Show dependency tree"
            )
            if success2:
                print("Dependency tree:")
                print(tree_output[:1000] + "..." if len(tree_output) > 1000 else tree_output)

        return success

    def run_code_quality_checks(self) -> bool:
        """Run code quality checks."""
        self.print_header("Code Quality Checks")

        checks = [
            (
                "Code formatting (black)",
                ["poetry", "run", "black", "--check", "--diff", "nexus/", "tests/"],
            ),
            (
                "Import sorting (isort)",
                ["poetry", "run", "isort", "--check-only", "--diff", "nexus/", "tests/"],
            ),
            (
                "Linting (flake8)",
                [
                    "poetry",
                    "run",
                    "flake8",
                    "nexus/",
                    "tests/",
                    "--count",
                    "--select=E9,F63,F7,F82",
                    "--show-source",
                    "--statistics",
                ],
            ),
            ("Type checking (mypy)", ["poetry", "run", "mypy", "nexus/"]),
        ]

        all_passed = True
        for check_name, cmd in checks:
            success, output = self.run_command(cmd, check_name)
            self.print_status(
                check_name, success, "Passed" if success else f"Issues found:\n{output}"
            )
            self.results[check_name] = success
            if not success:
                all_passed = False

        return all_passed

    def run_security_scan(self) -> bool:
        """Run security scan."""
        self.print_header("Security Scan")

        success, output = self.run_command(
            ["poetry", "run", "bandit", "-r", "nexus/", "-f", "json"], "Security scan (bandit)"
        )

        # Bandit returns non-zero if issues found, but that's not necessarily a failure
        # Parse the JSON output to determine severity
        scan_result = True
        details = "No high-severity issues found"

        if not success and "No issues identified" not in output:
            try:
                import json

                result_data = json.loads(output)
                if result_data.get("results"):
                    high_severity = [
                        r for r in result_data["results"] if r.get("issue_severity") == "HIGH"
                    ]
                    if high_severity:
                        scan_result = False
                        details = f"Found {len(high_severity)} high-severity security issues"
                    else:
                        details = f"Found {len(result_data['results'])} low/medium severity issues"
            except:
                details = "Security scan completed with warnings"

        self.print_status("Security scan", scan_result, details)
        self.results["Security scan"] = scan_result

        return scan_result

    def run_tests(self) -> bool:
        """Run tests."""
        self.print_header("Running Tests")

        if self.fast_mode:
            # Run only unit tests in fast mode
            test_commands = [
                (
                    "Unit tests",
                    [
                        "poetry",
                        "run",
                        "pytest",
                        "tests/unit/",
                        "-v",
                        "--tb=short",
                        "--maxfail=5",
                        "--asyncio-mode=auto",
                    ],
                )
            ]
        else:
            # Run all tests with coverage
            test_commands = [
                (
                    "Unit tests with coverage",
                    [
                        "poetry",
                        "run",
                        "pytest",
                        "tests/",
                        "--cov=nexus",
                        "--cov-branch",
                        "--cov-report=term-missing",
                        "--tb=short",
                        "--asyncio-mode=auto",
                        "--maxfail=10",
                    ],
                )
            ]

        all_passed = True
        for test_name, cmd in test_commands:
            success, output = self.run_command(cmd, test_name)

            # Extract useful info from pytest output
            details = "Tests passed"
            if not success:
                lines = output.split("\n")
                # Look for the summary line
                for line in lines:
                    if "failed" in line.lower() and "passed" in line.lower():
                        details = line.strip()
                        break
                else:
                    details = "Tests failed - check output above"
            elif "passed" in output:
                # Extract passed count
                lines = output.split("\n")
                for line in lines:
                    if " passed" in line and "==" in line:
                        details = line.strip().replace("=", "").strip()
                        break

            self.print_status(test_name, success, details)
            self.results[test_name] = success

            if not success:
                all_passed = False

        return all_passed

    def run_build_test(self) -> bool:
        """Test package building."""
        self.print_header("Build Test")

        success, output = self.run_command(["poetry", "build"], "Build package")

        details = "Package built successfully" if success else "Build failed"

        if success:
            # Check if dist files were created
            dist_dir = self.project_root / "dist"
            if dist_dir.exists():
                files = list(dist_dir.glob("*"))
                details = f"Built {len(files)} files: {', '.join(f.name for f in files)}"

        self.print_status("Package build", success, details)
        self.results["Package build"] = success

        return success

    def print_summary(self) -> bool:
        """Print test summary."""
        self.print_header("Test Summary")

        passed = sum(1 for result in self.results.values() if result)
        total = len(self.results)

        print(f"Results: {passed}/{total} checks passed\n")

        for test_name, success in self.results.items():
            status = (
                f"{Colors.OKGREEN}PASS{Colors.ENDC}"
                if success
                else f"{Colors.FAIL}FAIL{Colors.ENDC}"
            )
            print(f"  {status} {test_name}")

        if passed == total:
            print(
                f"\n{Colors.OKGREEN}{Colors.BOLD}🎉 All checks passed! Ready to push.{Colors.ENDC}"
            )
        else:
            print(
                f"\n{Colors.FAIL}{Colors.BOLD}❌ {total - passed} checks failed. Please fix before pushing.{Colors.ENDC}"
            )

        return passed == total

    def run_all(self) -> bool:
        """Run all tests."""
        start_time = time.time()

        print(f"{Colors.BOLD}🚀 Running Local CI Tests{Colors.ENDC}")
        print(f"Mode: {'Fast' if self.fast_mode else 'Complete'}")
        print(f"Verbose: {'Yes' if self.verbose else 'No'}")

        # Run checks in order
        steps = [
            ("Prerequisites", self.check_prerequisites),
            ("Dependencies", self.install_dependencies),
            ("Code Quality", self.run_code_quality_checks),
            ("Security", self.run_security_scan),
            ("Tests", self.run_tests),
            ("Build", self.run_build_test),
        ]

        for step_name, step_func in steps:
            try:
                success = step_func()
                if success is False and step_name in ["Prerequisites", "Dependencies"]:
                    print(
                        f"\n{Colors.FAIL}❌ Critical step '{step_name}' failed. Stopping.{Colors.ENDC}"
                    )
                    return False
            except KeyboardInterrupt:
                print(f"\n{Colors.WARNING}⚠️  Interrupted by user{Colors.ENDC}")
                return False
            except Exception as e:
                print(f"\n{Colors.FAIL}❌ Error in {step_name}: {e}{Colors.ENDC}")
                return False

        # Print summary
        overall_success = self.print_summary()

        elapsed = time.time() - start_time
        print(f"\n⏱️  Total time: {elapsed:.1f} seconds")

        return overall_success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run CI tests locally before pushing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test_ci_locally.py                    # Run all tests
  python scripts/test_ci_locally.py --fast             # Run quick tests only
  python scripts/test_ci_locally.py --verbose          # Show detailed output
  python scripts/test_ci_locally.py --fast --verbose   # Quick tests with details
        """,
    )

    parser.add_argument(
        "--fast",
        action="store_true",
        help="Run only quick tests (skip full test suite and coverage)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show verbose output including command details"
    )

    args = parser.parse_args()

    # Change to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)

    runner = TestRunner(fast_mode=args.fast, verbose=args.verbose)
    success = runner.run_all()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
