# Installation Guide

Get Nexus installed and ready for development in 2 minutes.

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

# Install Nexus
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
poetry add nexus

# Activate environment
poetry shell

# Verify installation
nexus --version
```

### Method 3: pipx (Isolated)

```bash
# Install pipx if not available
pip install pipx

# Install Nexus
pipx install nexus

# Verify installation
nexus --version
```

## 🔧 Development Setup

### VS Code Extensions (Recommended)

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

### Git Configuration

```bash
# Configure git for contributions
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

## 🐳 Docker Installation

### Using Pre-built Image

```bash
# Pull official image
docker pull nexus/nexus:latest

# Run container
docker run -p 8000:8000 nexus/nexus:latest
```

### Building from Source

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000
CMD ["nexus", "run"]
```

## 🔍 Verify Installation

### Check Core Components

```bash
# Check CLI tools
nexus --help
nexus-admin --help

# Check Python import
python -c "import nexus; print(f'Nexus {nexus.__version__} installed')"
```

### Test Basic Functionality

```python
# test_install.py
from nexus import create_nexus_app

app = create_nexus_app(title="Test App")
print("✓ Nexus installation verified")
```

Run test:

```bash
python test_install.py
```

## 🚨 Troubleshooting

### Common Issues

#### Python Version Error

```bash
# Error: Python 3.11+ required
# Solution: Install correct Python version
pyenv install 3.11.0  # Using pyenv
pyenv global 3.11.0
```

#### Permission Denied

```bash
# Error: Permission denied during pip install
# Solution: Use virtual environment
python -m venv venv
source venv/bin/activate
pip install nexus-platform
```

#### Import Error

```bash
# Error: ModuleNotFoundError: No module named 'nexus'
# Solution: Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows
```

#### Port Already in Use

```bash
# Error: Port 8000 already in use
# Solution: Use different port
nexus run --port 8001
```

### Platform-Specific Issues

#### Windows

```powershell
# Enable long path support
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force

# Use WSL2 for better compatibility
wsl --install
```

#### macOS

```bash
# Install Xcode command line tools
xcode-select --install

# Install Homebrew Python (if needed)
brew install python@3.11
```

#### Linux

```bash
# Ubuntu/Debian - install Python dev headers
sudo apt update
sudo apt install python3.11-dev python3.11-venv

# CentOS/RHEL - install Python dev headers
sudo yum install python3.11-devel
```

## 🔒 Security Considerations

### Virtual Environment

Always use virtual environments for isolation:

```bash
python -m venv --prompt nexus-project venv
```

### Update pip

Keep pip updated for security patches:

```bash
pip install --upgrade pip
```

### Verify Package Integrity

```bash
pip install nexus-platform --verify
```

## 📦 Optional Dependencies

### Database Drivers

```bash
# PostgreSQL
pip install nexus-platform[postgresql]

# MySQL
pip install nexus-platform[mysql]

# All databases
pip install nexus-platform[all-db]
```

### Development Tools

```bash
# Development dependencies
pip install nexus-platform[dev]

# Testing tools
pip install nexus-platform[test]

# Documentation tools
pip install nexus-platform[docs]
```

## ⚡ Performance Optimization

### Production Dependencies

```bash
# Install with performance optimizations
pip install nexus-platform[production]
```

### Environment Variables

```bash
# Optimize Python for production
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1
```

## 🎯 Next Steps

After successful installation:

1. **[Quick Start](quickstart.md)** - Build your first app
2. **[First Plugin](first-plugin.md)** - Create a plugin
3. **[Configuration](configuration.md)** - Configure your app

## 📋 Installation Checklist

- [ ] Python 3.11+ installed
- [ ] Virtual environment created and activated
- [ ] Nexus installed via pip
- [ ] CLI tools working (`nexus --version`)
- [ ] Python import successful
- [ ] Ready for [Quick Start](quickstart.md)

---

**Installation complete!** Ready for [Quick Start](quickstart.md) →
