# Installation Guide

Get Nexus Platform installed and ready for development in 2 minutes.

## 🎯 Quick Install

```bash
pip install nexus-platform
```

Verify installation:

```bash
nexus --version
```

## 📋 System Requirements

### Python Version

- **Required**: Python 3.11 or higher
- **Recommended**: Python 3.12 for best performance

Check your Python version:

```bash
python --version
```

### Operating Systems

- **Linux**: All major distributions
- **macOS**: 10.15+ (Catalina or newer)
- **Windows**: 10/11 with WSL2 recommended

### Hardware Requirements

- **RAM**: 512MB minimum, 2GB recommended
- **Disk**: 100MB for framework, 500MB for development
- **CPU**: Any modern processor

## 🛠️ Installation Methods

### Method 1: pip (Recommended)

```bash
# Create virtual environment (recommended)
python -m venv nexus-env
source nexus-env/bin/activate  # On Windows: nexus-env\Scripts\activate

# Install Nexus Platform
pip install nexus-platform

# Verify installation
nexus --version
```

### Method 2: Poetry

```bash
# Create new project
poetry new my-nexus-app
cd my-nexus-app

# Add Nexus dependency
poetry add nexus-platform

# Activate environment
poetry shell

# Verify installation
nexus --version
```

### Method 3: pipx (Isolated)

```bash
# Install pipx if not available
pip install pipx

# Install Nexus Platform
pipx install nexus-platform

# Verify installation
nexus --version
```

## 🔧 Development Setup

### Clone for Development

If you want to contribute or run from source:

```bash
# Clone the repository
git clone https://github.com/dnviti/nexus-platform.git
cd nexus-platform

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e .[dev,test]
```

### VS Code Extensions (Recommended)

Create `.vscode/extensions.json`:

```json
{
    "recommendations": [
        "ms-python.python",
        "ms-python.black-formatter",
        "ms-python.isort",
        "ms-python.mypy-type-checker",
        "bierner.markdown-mermaid"
    ]
}
```

## 🐳 Docker Installation

### Using Pre-built Image

```bash
# Pull official image (when available)
docker pull nexus/nexus-platform:latest

# Run container
docker run -p 8000:8000 nexus/nexus-platform:latest
```

### Building from Source

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "main.py"]
```

Build and run:

```bash
docker build -t my-nexus-app .
docker run -p 8000:8000 my-nexus-app
```

## 🔍 Verify Installation

### Check Core Components

```bash
# Check CLI tools
nexus --help
nexus-admin --help

# List available commands
nexus plugin --help
nexus status
```

### Test Python Import

```python
# test_install.py
from nexus import create_nexus_app, BasePlugin

# Test app creation
app = create_nexus_app(title="Test App")
print(f"✓ Nexus Platform installed successfully")
print(f"✓ App created: {app.title}")

# Test plugin import
class TestPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "test"

plugin = TestPlugin()
print(f"✓ Plugin system working: {plugin.name}")
```

Run test:

```bash
python test_install.py
```

### Test Project Initialization

Test the project initialization:

```bash
# Create a test directory
mkdir nexus-test
cd nexus-test

# Initialize a new Nexus project
nexus init

# This should create:
# - nexus_config.yaml
# - main.py
# - plugins/
# - config/, logs/, static/, templates/
```

Verify the created files:

```bash
ls -la
# Should show: main.py, nexus_config.yaml, plugins/, config/, logs/, etc.
```

### Test Application Startup

Run the initialized application:

```bash
# Run the application created by nexus init
python main.py
```

## 🚨 Troubleshooting

### Common Issues

#### Python Version Error

```bash
# Error: Python 3.11+ required
# Solution: Install correct Python version

# Using pyenv
pyenv install 3.11.0
pyenv global 3.11.0

# Using conda
conda create -n nexus python=3.11
conda activate nexus
```

#### Permission Denied

```bash
# Error: Permission denied during pip install
# Solution: Use virtual environment or --user flag

# Option 1: Virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows
pip install nexus-platform

# Option 2: User installation
pip install --user nexus-platform
```

#### Import Error

```bash
# Error: ModuleNotFoundError: No module named 'nexus'
# Solution: Make sure virtual environment is activated

source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# Check if package is installed
pip list | grep nexus-platform
```

#### CLI Command Not Found

```bash
# Error: nexus: command not found
# Solution: Make sure package is installed correctly

pip install nexus-platform
# Check PATH includes pip install directory
echo $PATH

# Or run directly with Python
python -m nexus --help
```

#### Port Already in Use

```bash
# Error: Port 8000 already in use
# Solution: Use different port or kill existing process

# Use different port
nexus run --port 8001

# Or find and kill existing process
lsof -ti:8000 | xargs kill -9  # Linux/Mac
netstat -ano | findstr :8000   # Windows
```

### Platform-Specific Issues

#### Windows

```powershell
# Enable long path support (run as Administrator)
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force

# Install Visual Studio Build Tools if needed
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Use WSL2 for better compatibility
wsl --install
```

#### macOS

```bash
# Install Xcode command line tools
xcode-select --install

# Install Homebrew Python (if needed)
brew install python@3.11

# Add to PATH
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

#### Linux

```bash
# Ubuntu/Debian - install Python dev headers
sudo apt update
sudo apt install python3.11-dev python3.11-venv python3-pip

# CentOS/RHEL/Rocky - install Python dev headers
sudo yum install python3.11-devel python3-pip

# Arch Linux
sudo pacman -S python python-pip
```

## 📦 Optional Dependencies

### Database Drivers

```bash
# PostgreSQL support
pip install nexus-platform[postgresql]

# MySQL support
pip install nexus-platform[mysql]

# MongoDB support
pip install nexus-platform[mongodb]

# SQLite (included by default)
pip install nexus-platform[sqlite]

# All databases
pip install nexus-platform[all-databases]
```

### Development Tools

```bash
# Development dependencies
pip install nexus-platform[dev]

# Testing tools
pip install nexus-platform[test]

# Documentation tools
pip install nexus-platform[docs]

# Everything
pip install nexus-platform[full]
```

### Plugin Development Extras

```bash
# Task scheduler support
pip install nexus-platform[task-scheduler]

# Messaging support
pip install nexus-platform[messaging]

# Email support
pip install nexus-platform[email]
```

## 🔒 Security Considerations

### Virtual Environment

Always use virtual environments for isolation:

```bash
python -m venv --prompt nexus-project venv
source venv/bin/activate
```

### Keep Dependencies Updated

```bash
# Update pip
pip install --upgrade pip

# Update nexus-platform
pip install --upgrade nexus-platform

# Check for security vulnerabilities
pip audit
```

### Verify Package Integrity

```bash
# Verify package signatures (if available)
pip install nexus-platform --require-hashes
```

## ⚡ Performance Optimization

### Production Installation

```bash
# Install with production optimizations
pip install nexus-platform[production]
```

### Environment Variables

```bash
# Optimize Python for production
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
```

### System Configuration

```bash
# Increase file descriptor limits
ulimit -n 65536

# Configure kernel parameters (Linux)
echo 'net.core.somaxconn = 65535' >> /etc/sysctl.conf
echo 'net.ipv4.tcp_max_syn_backlog = 65535' >> /etc/sysctl.conf
```

## 🎯 Next Steps

After successful installation:

1. **[Quick Start](quickstart.md)** - Initialize and build your first app in 5 minutes
2. **[First Plugin](first-plugin.md)** - Create your first plugin
3. **[Configuration](configuration.md)** - Configure your application

## 📋 Installation Checklist

- [ ] Python 3.11+ installed and verified
- [ ] Virtual environment created and activated
- [ ] `nexus-platform` installed via pip
- [ ] CLI tools working (`nexus --version`)
- [ ] Python import successful (`from nexus import create_nexus_app`)
- [ ] Project initialization works (`nexus init`)
- [ ] Test application runs successfully
- [ ] Ready for [Quick Start](quickstart.md)

---

**Installation complete!** Ready to build your first application → [Quick Start](quickstart.md)
