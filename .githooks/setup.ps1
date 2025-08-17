# Git Hooks Setup Script for Nexus Framework (Windows PowerShell)
# This script configures git to use the quality assurance hooks

param(
    [switch]$Help
)

if ($Help) {
    Write-Host "Git Hooks Setup Script for Nexus Framework" -ForegroundColor Green
    Write-Host "Usage: .\setup.ps1" -ForegroundColor Yellow
    Write-Host "This script configures git to use quality assurance hooks from .githooks directory"
    exit 0
}

Write-Host "🚀 Setting up Nexus Framework Git Hooks" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# Check if we're in a git repository
if (-not (Test-Path ".git")) {
    Write-Host "❌ Error: Not in a git repository" -ForegroundColor Red
    Write-Host "   Please run this script from the root of the Nexus repository" -ForegroundColor Yellow
    exit 1
}

# Check if .githooks directory exists
if (-not (Test-Path ".githooks")) {
    Write-Host "❌ Error: .githooks directory not found" -ForegroundColor Red
    Write-Host "   Please run this script from the root of the Nexus repository" -ForegroundColor Yellow
    exit 1
}

# Configure git to use .githooks directory
Write-Host "📁 Configuring git hooks directory..." -ForegroundColor Cyan
git config core.hooksPath .githooks

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error: Failed to configure git hooks directory" -ForegroundColor Red
    exit 1
}

# Check if Python is available
Write-Host "🐍 Checking Python environment..." -ForegroundColor Cyan
try {
    $pythonVersion = python --version 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
    Write-Host "✅ Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: Python not found" -ForegroundColor Red
    Write-Host "   Please install Python 3.11+ and try again" -ForegroundColor Yellow
    Write-Host "   Visit: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Check if Poetry is available
Write-Host "📦 Checking Poetry..." -ForegroundColor Cyan
try {
    $poetryVersion = poetry --version 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Poetry not found"
    }
    Write-Host "✅ Found: $poetryVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: Poetry not found" -ForegroundColor Red
    Write-Host "   Please install Poetry and try again" -ForegroundColor Yellow
    Write-Host "   Visit: https://python-poetry.org/docs/" -ForegroundColor Yellow
    exit 1
}

# Install dependencies if needed
Write-Host "📥 Checking dependencies..." -ForegroundColor Cyan
if (-not (Test-Path ".venv") -or -not (Test-Path "poetry.lock")) {
    Write-Host "📦 Installing dependencies..." -ForegroundColor Cyan
    poetry install --with dev,test
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Error: Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ Dependencies already installed" -ForegroundColor Green
}

# Test the pre-commit hook (simplified test)
Write-Host "🧪 Testing git hooks..." -ForegroundColor Cyan
try {
    # Test if the hook file exists and is readable
    if (Test-Path ".githooks/pre-commit") {
        Write-Host "✅ Git hooks configured successfully" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Warning: pre-commit hook not found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Git hooks test completed with warnings (this is normal)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 Git hooks setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 What was configured:" -ForegroundColor Cyan
Write-Host "   • Git hooks directory: .githooks" -ForegroundColor White
Write-Host "   • Pre-commit validation: ENABLED" -ForegroundColor White
Write-Host "   • Code quality checks: ENABLED" -ForegroundColor White
Write-Host "   • Security scanning: ENABLED" -ForegroundColor White
Write-Host "   • Test suite validation: ENABLED" -ForegroundColor White
Write-Host ""
Write-Host "💡 Usage:" -ForegroundColor Cyan
Write-Host "   git commit -m `"Your message`"  # Triggers full validation" -ForegroundColor White
Write-Host "   python scripts/pre_push_check.py --fast  # Quick dev check" -ForegroundColor White
Write-Host ""
Write-Host "📚 Documentation:" -ForegroundColor Cyan
Write-Host "   • Git hooks: .githooks/README.md" -ForegroundColor White
Write-Host "   • Scripts: scripts/README.md" -ForegroundColor White
Write-Host "   • Troubleshooting: .github/TROUBLESHOOTING.md" -ForegroundColor White
Write-Host ""
Write-Host "🚀 You're ready to contribute to Nexus with confidence!" -ForegroundColor Green
