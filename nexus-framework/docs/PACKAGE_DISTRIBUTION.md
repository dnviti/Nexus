# Nexus Framework - Package Distribution Guide

This guide provides complete instructions for building, testing, and distributing the Nexus Framework as a pip package.

## 📦 Package Overview

**Package Name**: `nexus-framework`  
**Current Version**: 2.0.0  
**License**: MIT  
**Python Support**: 3.11+  

### What's Included

- **Core Framework**: Plugin-based architecture with FastAPI integration
- **CLI Tools**: `nexus` and `nexus-admin` command-line interfaces
- **Authentication**: JWT-based user management system
- **Monitoring**: Health checks and metrics collection
- **Database**: SQLAlchemy integration with multiple database support
- **Configuration**: Flexible YAML/JSON configuration management
- **Plugin System**: Dynamic plugin loading and management

## 🏗️ Building the Package

### Prerequisites

```bash
# Install build dependencies
pip install build wheel setuptools twine

# Or using the virtual environment
source .venv/bin/activate
pip install build wheel setuptools twine
```

### Build Process

1. **Clean Previous Builds** (Optional)
```bash
rm -rf dist/ build/ *.egg-info
```

2. **Build the Package**
```bash
# Using Python build module (recommended)
python -m build

# This creates both:
# - dist/nexus_framework-2.0.0.tar.gz (source distribution)
# - dist/nexus_framework-2.0.0-py3-none-any.whl (wheel distribution)
```

3. **Verify Build**
```bash
ls -la dist/
# Should show:
# nexus_framework-2.0.0-py3-none-any.whl
# nexus_framework-2.0.0.tar.gz
```

## 🧪 Testing the Package

### Local Installation Testing

1. **Install from Local Wheel**
```bash
# Create a fresh virtual environment for testing
python -m venv test_env
source test_env/bin/activate

# Install the package
pip install dist/nexus_framework-2.0.0-py3-none-any.whl
```

2. **Test CLI Commands**
```bash
# Test version
nexus --version
nexus-admin --version

# Test help
nexus --help
nexus-admin --help

# Test functionality
nexus status
nexus health
```

3. **Test Package Import**
```python
# Create test_import.py
python -c "
import nexus
print(f'Nexus Framework {nexus.__version__} imported successfully!')
app = nexus.create_nexus_app()
print('Application created successfully!')
"
```

4. **Test Project Creation**
```bash
# Create a new test project
mkdir test_nexus_project
cd test_nexus_project
nexus init

# Verify project structure
ls -la
# Should show: main.py, nexus_config.yaml, plugins/, config/, logs/, etc.
```

### Integration Testing

```bash
# Test the generated project
cd test_nexus_project
python main.py &
PID=$!

# Wait for server to start
sleep 3

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/docs

# Stop server
kill $PID
```

## 📋 Package Information

### Dependencies

**Core Dependencies**:
- `fastapi ^0.109.0` - Web framework
- `uvicorn[standard] ^0.27.0` - ASGI server
- `pydantic ^2.5.3` - Data validation
- `sqlalchemy ^2.0.25` - Database ORM
- `python-jose[cryptography] ^3.3.0` - JWT handling
- `pyyaml ^6.0.1` - Configuration parsing
- `click ^8.1.7` - CLI framework
- `aiofiles ^23.2.1` - Async file operations

**Development Dependencies** (optional):
- `pytest ^7.4.4` - Testing framework
- `black ^23.12.1` - Code formatting
- `mypy ^1.8.0` - Type checking
- `flake8 ^7.0.0` - Linting

### Entry Points

The package provides two CLI commands:

```toml
[tool.poetry.scripts]
nexus = "nexus.cli:main"
nexus-admin = "nexus.admin:main"
```

### Package Structure

```
nexus_framework-2.0.0/
├── nexus/                          # Main package
│   ├── __init__.py                 # Package exports
│   ├── core.py                     # Core framework components
│   ├── auth.py                     # Authentication system
│   ├── api.py                      # API utilities
│   ├── plugins.py                  # Plugin system
│   ├── monitoring.py               # Health checks and metrics
│   ├── middleware.py               # HTTP middleware
│   ├── config.py                   # Configuration management
│   ├── utils.py                    # Utility functions
│   ├── cli.py                      # Main CLI interface
│   └── admin.py                    # Admin CLI interface
├── LICENSE                         # MIT License
├── README.md                       # Documentation
├── CHANGELOG.md                    # Version history
└── pyproject.toml                  # Package configuration
```

## 🚀 Distribution Options

### 1. Private Distribution

**For Internal Use or Testing**

```bash
# Install directly from wheel file
pip install /path/to/nexus_framework-2.0.0-py3-none-any.whl

# Install from Git repository (if hosted)
pip install git+https://github.com/your-org/nexus-framework.git

# Install from local directory (development)
pip install -e .
```

### 2. PyPI Distribution

**For Public Release**

#### TestPyPI (Recommended for Testing)

```bash
# Upload to TestPyPI first
twine upload --repository testpypi dist/*

# Install from TestPyPI to test
pip install --index-url https://test.pypi.org/simple/ nexus-framework
```

#### Production PyPI

```bash
# Configure PyPI credentials (one-time setup)
# Option 1: Using .pypirc file
cat > ~/.pypirc << EOF
[distutils]
index-servers = pypi

[pypi]
username = __token__
password = pypi-your-api-token-here
EOF

# Option 2: Using environment variables
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-your-api-token-here

# Upload to PyPI
twine upload dist/*

# After upload, users can install with:
pip install nexus-framework
```

### 3. Private Package Index

**For Enterprise Distribution**

```bash
# Upload to private index
twine upload --repository-url https://your-private-pypi.com/simple/ dist/*

# Install from private index
pip install --index-url https://your-private-pypi.com/simple/ nexus-framework
```

## 📝 Usage Examples

### Quick Start

```bash
# Install the framework
pip install nexus-framework

# Create a new project
mkdir my_nexus_app
cd my_nexus_app
nexus init

# Run the application
python main.py
```

### Programmatic Usage

```python
from nexus import create_nexus_app, BasePlugin

# Create a simple application
app = create_nexus_app(
    title="My API",
    description="Built with Nexus Framework",
    version="1.0.0"
)

# Create a custom plugin
class MyPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "my_plugin"
        self.version = "1.0.0"
    
    async def initialize(self):
        self.logger.info("Plugin initialized!")
        return True

# Run with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Plugin Development

```bash
# Create a new plugin
nexus plugin create my_awesome_plugin

# Plugin structure created at:
# plugins/my_awesome_plugin/
# ├── __init__.py
# ├── plugin.py
# └── manifest.json
```

## 🛠️ Development Workflow

### For Package Maintainers

1. **Development Setup**
```bash
git clone <repository>
cd nexus-framework
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

2. **Make Changes**
- Update version in `pyproject.toml` and `nexus/__init__.py`
- Update `CHANGELOG.md`
- Add/modify features

3. **Test Changes**
```bash
# Run tests
python -m pytest

# Test CLI
nexus --help
nexus-admin --help

# Test package build
python -m build
```

4. **Release Process**
```bash
# Build package
python -m build

# Test on TestPyPI
twine upload --repository testpypi dist/*

# If tests pass, release to PyPI
twine upload dist/*

# Tag release
git tag v2.0.0
git push origin v2.0.0
```

## 📊 Package Metrics

### Size Information
- **Wheel Size**: ~42 KB
- **Source Distribution**: ~136 KB
- **Installed Size**: ~200 KB

### Performance
- **Import Time**: <500ms
- **CLI Startup**: <200ms
- **Application Startup**: <3 seconds

## 🔧 Configuration

### Package Configuration (pyproject.toml)

```toml
[tool.poetry]
name = "nexus-framework"
version = "2.0.0"
description = "The Ultimate Plugin-Based Application Platform"
authors = ["Nexus Team <team@nexus-framework.dev>"]
license = "MIT"
packages = [{ include = "nexus", from = "app" }]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.109.0"
# ... other dependencies

[tool.poetry.scripts]
nexus = "nexus.cli:main"
nexus-admin = "nexus.admin:main"
```

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**
```bash
# Issue: Module not found
# Solution: Ensure proper installation
pip install --force-reinstall nexus-framework
```

2. **CLI Commands Not Found**
```bash
# Issue: Command 'nexus' not found
# Solution: Check PATH or reinstall
pip install --force-reinstall nexus-framework
which nexus
```

3. **Version Conflicts**
```bash
# Issue: Dependency conflicts
# Solution: Use fresh virtual environment
python -m venv fresh_env
source fresh_env/bin/activate
pip install nexus-framework
```

### Debug Information

```bash
# Check installation
pip show nexus-framework

# Verify CLI tools
nexus --version
nexus-admin --version

# Test import
python -c "import nexus; print(nexus.__version__)"
```

## 📚 Additional Resources

- **Documentation**: [https://docs.nexus-framework.dev](https://docs.nexus-framework.dev)
- **PyPI Package**: [https://pypi.org/project/nexus-framework/](https://pypi.org/project/nexus-framework/)
- **Source Code**: [https://github.com/nexus-framework/nexus](https://github.com/nexus-framework/nexus)
- **Issues**: [https://github.com/nexus-framework/nexus/issues](https://github.com/nexus-framework/nexus/issues)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Package Built**: 2024-12-21  
**Python Compatibility**: 3.11+  
**Package Format**: Universal Wheel  
**Distribution Ready**: ✅ Yes