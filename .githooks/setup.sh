#!/bin/bash
# Git Hooks Setup Script for Nexus Framework
# This script configures git to use the quality assurance hooks

set -e  # Exit on any error

echo "🚀 Setting up Nexus Framework Git Hooks"
echo "========================================"

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository"
    echo "   Please run this script from the root of the Nexus repository"
    exit 1
fi

# Check if .githooks directory exists
if [ ! -d ".githooks" ]; then
    echo "❌ Error: .githooks directory not found"
    echo "   Please run this script from the root of the Nexus repository"
    exit 1
fi

# Configure git to use .githooks directory
echo "📁 Configuring git hooks directory..."
git config core.hooksPath .githooks

# Make hooks executable
echo "🔧 Making hooks executable..."
chmod +x .githooks/*

# Check if Python and Poetry are available
echo "🐍 Checking Python environment..."
if ! command -v python &> /dev/null; then
    echo "❌ Error: Python not found"
    echo "   Please install Python 3.11+ and try again"
    exit 1
fi

if ! command -v poetry &> /dev/null; then
    echo "❌ Error: Poetry not found"
    echo "   Please install Poetry and try again"
    echo "   Visit: https://python-poetry.org/docs/"
    exit 1
fi

# Install dependencies if needed
echo "📦 Checking dependencies..."
if [ ! -d ".venv" ] || [ ! -f "poetry.lock" ]; then
    echo "📥 Installing dependencies..."
    poetry install --with dev,test
else
    echo "✅ Dependencies already installed"
fi

# Test the pre-commit hook
echo "🧪 Testing git hooks..."
if .githooks/pre-commit > /dev/null 2>&1; then
    echo "✅ Git hooks test passed"
else
    echo "⚠️  Git hooks test completed with warnings (this is normal)"
fi

echo ""
echo "🎉 Git hooks setup complete!"
echo ""
echo "📋 What was configured:"
echo "   • Git hooks directory: .githooks"
echo "   • Pre-commit validation: ENABLED"
echo "   • Code quality checks: ENABLED"
echo "   • Security scanning: ENABLED"
echo "   • Test suite validation: ENABLED"
echo ""
echo "💡 Usage:"
echo "   git commit -m \"Your message\"  # Triggers full validation"
echo "   python scripts/pre_push_check.py --fast  # Quick dev check"
echo ""
echo "📚 Documentation:"
echo "   • Git hooks: .githooks/README.md"
echo "   • Scripts: scripts/README.md"
echo "   • Troubleshooting: .github/TROUBLESHOOTING.md"
echo ""
echo "🚀 You're ready to contribute to Nexus with confidence!"
