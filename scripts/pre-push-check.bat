@echo off
REM ============================================================================
REM Nexus Framework - Pre-Push Validation Script (Windows)
REM ============================================================================
REM This batch file runs all CI/CD pipeline checks locally before pushing to git.
REM It ensures code quality, tests, and build integrity on Windows systems.
REM
REM Usage:
REM   scripts\pre-push-check.bat [--fix] [--fast] [--help]
REM
REM Options:
REM   --fix     Automatically fix formatting and import issues
REM   --fast    Skip slower checks (coverage, security scan)
REM   --help    Show this help message
REM ============================================================================

setlocal enabledelayedexpansion

REM Colors for Windows (limited support)
set "BLUE=[34m"
set "GREEN=[32m"
set "YELLOW=[33m"
set "RED=[31m"
set "BOLD=[1m"
set "NC=[0m"

REM Configuration
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "TIMESTAMP=%DATE% %TIME%"

REM Default options
set "FIX_MODE=false"
set "FAST_MODE=false"
set "SHOW_HELP=false"

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :args_done
if "%~1"=="--fix" (
    set "FIX_MODE=true"
    shift
    goto :parse_args
)
if "%~1"=="--fast" (
    set "FAST_MODE=true"
    shift
    goto :parse_args
)
if "%~1"=="--help" (
    set "SHOW_HELP=true"
    shift
    goto :parse_args
)
if "%~1"=="-h" (
    set "SHOW_HELP=true"
    shift
    goto :parse_args
)
echo Unknown option: %~1
exit /b 1

:args_done

REM Show help if requested
if "%SHOW_HELP%"=="true" (
    echo.
    echo Nexus Framework - Pre-Push Validation Script ^(Windows^)
    echo.
    echo This script runs all CI/CD pipeline checks locally before pushing to git.
    echo.
    echo Usage:
    echo   scripts\pre-push-check.bat [OPTIONS]
    echo.
    echo Options:
    echo   --fix     Automatically fix formatting and import issues
    echo   --fast    Skip slower checks ^(coverage, security scan^)
    echo   --help    Show this help message
    echo.
    echo Examples:
    echo   scripts\pre-push-check.bat                    # Run all checks
    echo   scripts\pre-push-check.bat --fix              # Run and auto-fix issues
    echo   scripts\pre-push-check.bat --fast             # Quick check only
    echo   scripts\pre-push-check.bat --fix --fast       # Quick fix and check
    echo.
    exit /b 0
)

REM Change to project root
cd /d "%PROJECT_ROOT%"

REM Header
echo.
echo %BOLD%%GREEN%🚀 Nexus Framework - Pre-Push Validation%NC%
echo %BLUE%Started at: %TIMESTAMP%%NC%
set "MODE=Check-only"
if "%FIX_MODE%"=="true" set "MODE=Auto-fix"
if "%FAST_MODE%"=="true" set "MODE=%MODE% (Fast)"
echo %BLUE%Mode: %MODE%%NC%
echo.

REM Check if we're in the project root
if not exist "pyproject.toml" (
    echo %RED%❌ Not in Nexus project root! Please run from project directory.%NC%
    exit /b 1
)

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%❌ Python is not installed or not in PATH!%NC%
    echo %BLUE%ℹ️  Install Python 3.11+ from https://python.org%NC%
    exit /b 1
)

REM Check if Poetry is available
poetry --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%❌ Poetry is not installed or not in PATH!%NC%
    echo %BLUE%ℹ️  Install Poetry from https://python-poetry.org%NC%
    exit /b 1
)

REM Use Python script for main functionality
echo %YELLOW%▶ Delegating to Python script for cross-platform compatibility...%NC%
echo.

REM Build Python command
set "PYTHON_CMD=python scripts\pre_push_check.py"
if "%FIX_MODE%"=="true" set "PYTHON_CMD=%PYTHON_CMD% --fix"
if "%FAST_MODE%"=="true" set "PYTHON_CMD=%PYTHON_CMD% --fast"

REM Execute Python script
%PYTHON_CMD%
set "PYTHON_EXIT_CODE=%errorlevel%"

REM Handle result
echo.
if %PYTHON_EXIT_CODE% equ 0 (
    echo %GREEN%✅ Pre-push validation completed successfully!%NC%
    echo %GREEN%✅ Ready to push to git! 🚀%NC%
    echo.
    echo %BOLD%Next steps:%NC%
    echo   git add .
    echo   git commit -m "Your commit message"
    echo   git push
) else (
    echo %RED%❌ Pre-push validation failed!%NC%
    echo.
    echo %BOLD%Quick fixes:%NC%
    echo   # Fix formatting and imports:
    echo   scripts\pre-push-check.bat --fix
    echo.
    echo   # Run specific tools:
    echo   poetry run black nexus\ tests\ scripts\
    echo   poetry run isort nexus\ tests\ scripts\
    echo   poetry run mypy nexus\
    echo   poetry run pytest tests\unit\
)

echo.
echo %BLUE%ℹ️  For detailed output, use the Python script directly:%NC%
echo   python scripts\pre_push_check.py --help

exit /b %PYTHON_EXIT_CODE%
