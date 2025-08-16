# Nexus Framework Installation Guide

Complete installation instructions for the Nexus Framework pip package.

## 📋 System Requirements

### Minimum Requirements
- **Python**: 3.11 or higher
- **Operating System**: Linux, macOS, Windows
- **Memory**: 512MB RAM
- **Disk Space**: 100MB for framework + additional for plugins
- **Network**: Internet connection for package installation

### Recommended Requirements
- **Python**: 3.12 or higher
- **Memory**: 2GB RAM or more
- **Disk Space**: 1GB or more
- **CPU**: Multi-core processor for production workloads

### Supported Platforms
- ✅ **Linux** (Ubuntu 20.04+, CentOS 8+, Debian 11+, Alpine 3.15+)
- ✅ **macOS** (10.15+ / macOS Catalina or newer)
- ✅ **Windows** (Windows 10, Windows 11, Windows Server 2019+)
- ✅ **Docker** (Official Docker images available)

## 🚀 Quick Installation

### Standard Installation

```bash
# Install from PyPI
pip install nexus-framework

# Verify installation
nexus --version
```

That's it! You can now start building with Nexus Framework.

## 📦 Installation Methods

### Method 1: PyPI Installation (Recommended)

#### Latest Stable Version
```bash
pip install nexus-framework
```

#### Specific Version
```bash
# Install specific version
pip install nexus-framework==2.0.0

# Install version range
pip install "nexus-framework>=2.0.0,<3.0.0"
```

#### Development Dependencies
```bash
# Install with development tools
pip install nexus-framework[dev]

# Install with testing tools
pip install nexus-framework[test]

# Install with documentation tools
pip install nexus-framework[docs]

# Install everything
pip install nexus-framework[dev,test,docs]
```

### Method 2: Virtual Environment (Recommended)

#### Using venv
```bash
# Create virtual environment
python -m venv nexus-env

# Activate virtual environment
# On Linux/macOS:
source nexus-env/bin/activate
# On Windows:
nexus-env\Scripts\activate

# Install Nexus Framework
pip install nexus-framework

# Verify installation
nexus --version
```

#### Using conda
```bash
# Create conda environment
conda create -n nexus-env python=3.11

# Activate environment
conda activate nexus-env

# Install Nexus Framework
pip install nexus-framework
```

### Method 3: From Source

#### Development Installation
```bash
# Clone repository
git clone https://github.com/nexus-framework/nexus.git
cd nexus

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e .[dev,test,docs]
```

#### Build from Source
```bash
# Clone and build
git clone https://github.com/nexus-framework/nexus.git
cd nexus

# Install build dependencies
pip install build

# Build package
python -m build

# Install built package
pip install dist/nexus_framework-*.whl
```

### Method 4: Docker Installation

#### Official Docker Image
```bash
# Pull latest image
docker pull nexusframework/nexus:latest

# Run container
docker run -p 8000:8000 nexusframework/nexus:latest

# Run with volume for persistence
docker run -p 8000:8000 -v $(pwd)/data:/app/data nexusframework/nexus:latest
```

#### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  nexus:
    image: nexusframework/nexus:latest
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./plugins:/app/plugins
    environment:
      - NEXUS_DEBUG=false
      - DATABASE_URL=sqlite:///data/nexus.db
```

```bash
# Start services
docker-compose up -d
```

## ⚙️ Installation Verification

### Basic Verification
```bash
# Check version
nexus --version
nexus-admin --version

# Test import
python -c "import nexus; print(f'✅ Nexus {nexus.__version__} installed successfully!')"

# Check CLI help
nexus --help
nexus-admin --help
```

### Comprehensive Verification
```bash
# Run health check
nexus health

# Check system status
nexus status

# List available commands
nexus --help
nexus-admin --help

# Create test project
mkdir test-nexus
cd test-nexus
nexus init

# Verify project creation
ls -la
# Should show: main.py, nexus_config.yaml, plugins/, etc.
```

### Test Application
```bash
# In your test project directory
python main.py &
sleep 3

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/docs

# Stop test server
pkill -f "python main.py"
```

## 🔧 Configuration After Installation

### Initial Setup
```bash
# Create your first project
mkdir my-nexus-app
cd my-nexus-app
nexus init

# Start development server
python main.py
```

### Environment Configuration
```bash
# Create .env file for local development
cat > .env << EOF
NEXUS_DEBUG=true
DATABASE_URL=sqlite:///./dev.db
SECRET_KEY=dev-secret-key-change-in-production
CORS_ORIGINS=["http://localhost:3000"]
EOF
```

### Database Setup
```bash
# For SQLite (default) - no setup needed

# For PostgreSQL
pip install psycopg2-binary
# Set DATABASE_URL=postgresql://user:pass@localhost/dbname

# For MySQL
pip install pymysql
# Set DATABASE_URL=mysql://user:pass@localhost/dbname
```

## 🛠️ Troubleshooting

### Common Installation Issues

#### Issue: Python Version Not Supported
```bash
# Error: Python 3.10 is not supported
# Solution: Upgrade Python
python --version  # Should be 3.11+

# Install Python 3.11+ using pyenv
curl https://pyenv.run | bash
pyenv install 3.11.7
pyenv global 3.11.7
```

#### Issue: Permission Denied
```bash
# Error: Permission denied when installing
# Solution: Use virtual environment or user install
pip install --user nexus-framework

# Or create virtual environment
python -m venv nexus-env
source nexus-env/bin/activate
pip install nexus-framework
```

#### Issue: Package Conflicts
```bash
# Error: Dependency conflicts
# Solution: Use fresh virtual environment
python -m venv fresh-env
source fresh-env/bin/activate
pip install nexus-framework
```

#### Issue: Command Not Found
```bash
# Error: nexus: command not found
# Solution: Check PATH or use full path
which nexus
python -m nexus.cli --help

# Add to PATH (Linux/macOS)
export PATH="$HOME/.local/bin:$PATH"

# Add to PATH (Windows)
# Add %APPDATA%\Python\Python311\Scripts to PATH
```

#### Issue: Import Errors
```bash
# Error: ModuleNotFoundError: No module named 'nexus'
# Solution: Verify installation
pip show nexus-framework
pip list | grep nexus

# Reinstall if needed
pip uninstall nexus-framework
pip install nexus-framework
```

### Platform-Specific Issues

#### Windows Issues
```powershell
# Issue: SSL certificate errors
# Solution: Upgrade certificates
pip install --upgrade certifi

# Issue: Long path names
# Solution: Enable long paths in Windows
# Run as Administrator:
# New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

#### macOS Issues
```bash
# Issue: Command line tools missing
# Solution: Install Xcode command line tools
xcode-select --install

# Issue: SSL certificate issues
# Solution: Update certificates
/Applications/Python\ 3.11/Install\ Certificates.command
```

#### Linux Issues
```bash
# Issue: Missing system packages
# Solution: Install build essentials
# Ubuntu/Debian:
sudo apt-get update
sudo apt-get install python3-dev python3-pip build-essential

# CentOS/RHEL:
sudo yum groupinstall "Development Tools"
sudo yum install python3-devel

# Alpine:
apk add python3-dev gcc musl-dev
```

### Docker Issues
```bash
# Issue: Container fails to start
# Solution: Check logs
docker logs <container-id>

# Issue: Port already in use
# Solution: Use different port
docker run -p 8080:8000 nexusframework/nexus:latest

# Issue: Permission issues with volumes
# Solution: Fix permissions
sudo chown -R 1000:1000 ./data
```

## 🔍 Verification Commands

### Installation Health Check
```bash
#!/bin/bash
# health_check.sh

echo "🔍 Nexus Framework Installation Health Check"
echo "============================================"

# Check Python version
echo "Python version:"
python --version

# Check pip version
echo "Pip version:"
pip --version

# Check if nexus-framework is installed
echo "Nexus Framework installation:"
pip show nexus-framework

# Check CLI tools
echo "CLI tools:"
nexus --version 2>/dev/null && echo "✅ nexus CLI working" || echo "❌ nexus CLI failed"
nexus-admin --version 2>/dev/null && echo "✅ nexus-admin CLI working" || echo "❌ nexus-admin CLI failed"

# Test Python import
echo "Python import test:"
python -c "import nexus; print(f'✅ Nexus {nexus.__version__} import successful')" 2>/dev/null || echo "❌ Import failed"

# Test project creation
echo "Project creation test:"
mkdir -p /tmp/nexus-test
cd /tmp/nexus-test
nexus init >/dev/null 2>&1 && echo "✅ Project creation successful" || echo "❌ Project creation failed"
cd - >/dev/null
rm -rf /tmp/nexus-test

echo "============================================"
echo "Health check complete!"
```

### Performance Test
```bash
# Test application startup time
time python -c "
import nexus
app = nexus.create_nexus_app()
print('✅ Application created successfully')
"
```

## 📊 Installation Options Comparison

| Method | Pros | Cons | Best For |
|--------|------|------|----------|
| **PyPI** | ✅ Easy<br>✅ Stable<br>✅ Fast | ❌ Latest features may lag | Production use |
| **Virtual Environment** | ✅ Isolated<br>✅ Clean<br>✅ Safe | ❌ Extra setup step | Development |
| **From Source** | ✅ Latest features<br>✅ Customizable | ❌ More complex<br>❌ Less stable | Contributing |
| **Docker** | ✅ Consistent<br>✅ Isolated<br>✅ Reproducible | ❌ Resource overhead | Deployment |

## 🎯 Post-Installation Steps

### 1. Create Your First Project
```bash
mkdir my-nexus-app
cd my-nexus-app
nexus init
```

### 2. Explore the CLI
```bash
# Main CLI
nexus --help
nexus status
nexus health

# Admin CLI
nexus-admin --help
nexus-admin system info
```

### 3. Create Your First Plugin
```bash
nexus plugin create hello_world
```

### 4. Start Development
```bash
python main.py
# Visit http://localhost:8000/docs
```

### 5. Read Documentation
- [Quick Start Tutorial](docs/TUTORIAL.md)
- [Plugin Development Guide](docs/PLUGIN_DEVELOPMENT.md)
- [Configuration Reference](docs/CONFIGURATION.md)

## 🔄 Updating Nexus Framework

### Check for Updates
```bash
# Check current version
nexus --version

# Check for available updates
pip list --outdated | grep nexus-framework
```

### Update to Latest Version
```bash
# Update to latest
pip install --upgrade nexus-framework

# Update to specific version
pip install --upgrade nexus-framework==2.1.0

# Force reinstall
pip install --force-reinstall nexus-framework
```

### Migration Between Versions
```bash
# Before updating, backup your projects
cp -r my-nexus-app my-nexus-app-backup

# Update framework
pip install --upgrade nexus-framework

# Check for breaking changes in release notes
# https://github.com/nexus-framework/nexus/releases

# Test your application
cd my-nexus-app
python main.py
```

## 🗑️ Uninstallation

### Remove Nexus Framework
```bash
# Uninstall package
pip uninstall nexus-framework

# Remove virtual environment (if used)
rm -rf nexus-env/

# Remove Docker images (if used)
docker rmi nexusframework/nexus:latest
```

### Clean Uninstall
```bash
# Remove all traces
pip uninstall nexus-framework
pip cache purge
rm -rf ~/.cache/pip/wheels/nexus*
```

## 📞 Getting Help

### If Installation Fails
1. **Check Requirements**: Ensure Python 3.11+
2. **Try Virtual Environment**: Isolate dependencies
3. **Check Network**: Ensure internet connectivity
4. **Read Error Messages**: Look for specific error details
5. **Search Issues**: Check GitHub issues
6. **Ask for Help**: Use our support channels

### Support Channels
- **GitHub Issues**: https://github.com/nexus-framework/nexus/issues
- **Discord Community**: https://discord.gg/nexus-framework
- **Documentation**: https://docs.nexus-framework.dev
- **Stack Overflow**: Tag with `nexus-framework`

### Before Seeking Help
Please provide:
- Operating system and version
- Python version (`python --version`)
- Pip version (`pip --version`)
- Complete error message
- Installation method used
- Virtual environment details

## 📚 Next Steps

After successful installation:

1. **[Follow the Tutorial](docs/TUTORIAL.md)** - Build your first app
2. **[Read the Architecture Guide](docs/ARCHITECTURE.md)** - Understand the framework
3. **[Create Plugins](docs/PLUGIN_DEVELOPMENT.md)** - Extend functionality
4. **[Join the Community](docs/COMMUNITY.md)** - Connect with other developers

---

**Installation complete!** 🎉 Start building amazing applications with Nexus Framework.

For the latest installation instructions, visit: https://docs.nexus-framework.dev/installation/