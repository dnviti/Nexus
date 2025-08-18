# Development Deployment

This guide covers setting up Nexus for local development, including development environments, debugging tools, and best practices for contributors.

## Overview

Development deployment focuses on ease of setup, rapid iteration, and debugging capabilities. This guide provides multiple approaches to get Nexus running locally for development purposes.

## Prerequisites

### System Requirements

- **Operating System**: Windows 10+, macOS 10.15+, or Linux (Ubuntu 18.04+)
- **CPU**: 4 cores minimum, 8 cores recommended
- **Memory**: 8 GB RAM minimum, 16 GB recommended
- **Storage**: 20 GB free space minimum
- **Network**: Stable internet connection for dependencies

### Required Software

- **Node.js**: 18.x or later
- **npm/yarn**: Latest version
- **Git**: 2.x or later
- **Docker**: 20.10+ (optional but recommended)
- **Docker Compose**: 2.x+ (optional but recommended)

### Development Tools

- **IDE/Editor**: VS Code, WebStorm, or Vim/Neovim
- **Database Client**: pgAdmin, DBeaver, or similar
- **API Testing**: Postman, Insomnia, or curl
- **Version Control**: Git with SSH keys configured

## Quick Start

### Clone Repository

```bash
# Clone the repository
git clone git@github.com:nexus/nexus.git
cd nexus

# Install dependencies
npm install

# Copy environment template
cp .env.example .env.local
```

### Environment Configuration

Edit `.env.local`:

```bash
# Application settings
NODE_ENV=development
PORT=8080
HOST=localhost

# Database configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nexus_dev
DB_USERNAME=nexus
DB_PASSWORD=nexus_dev_password

# Redis configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Authentication
JWT_SECRET=your_jwt_secret_for_development
SESSION_SECRET=your_session_secret_for_development

# External services (optional for development)
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USERNAME=
SMTP_PASSWORD=

# Logging
LOG_LEVEL=debug
LOG_FORMAT=pretty

# Development features
ENABLE_HOT_RELOAD=true
ENABLE_DEBUG_ROUTES=true
ENABLE_MOCK_DATA=true
```

### Database Setup

#### Option 1: Local PostgreSQL

```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib

# Install PostgreSQL (macOS with Homebrew)
brew install postgresql
brew services start postgresql

# Create development database
sudo -u postgres createuser nexus
sudo -u postgres createdb nexus_dev -O nexus
sudo -u postgres psql -c "ALTER USER nexus PASSWORD 'nexus_dev_password';"

# Run migrations
npm run db:migrate
npm run db:seed
```

#### Option 2: Docker PostgreSQL

```bash
# Start PostgreSQL in Docker
docker run -d \
  --name nexus-postgres-dev \
  -e POSTGRES_DB=nexus_dev \
  -e POSTGRES_USER=nexus \
  -e POSTGRES_PASSWORD=nexus_dev_password \
  -p 5432:5432 \
  postgres:15

# Run migrations
npm run db:migrate
npm run db:seed
```

### Redis Setup

#### Option 1: Local Redis

```bash
# Install Redis (Ubuntu/Debian)
sudo apt install redis-server

# Install Redis (macOS with Homebrew)
brew install redis
brew services start redis

# Test Redis connection
redis-cli ping
```

#### Option 2: Docker Redis

```bash
# Start Redis in Docker
docker run -d \
  --name nexus-redis-dev \
  -p 6379:6379 \
  redis:7-alpine
```

### Start Development Server

```bash
# Start in development mode
npm run dev

# Or with debugging
npm run dev:debug

# Or with specific port
PORT=3000 npm run dev
```

## Docker Development Environment

### Docker Compose Setup

Create `docker-compose.dev.yml`:

```yaml
version: '3.8'

services:
  nexus:
    build:
      context: .
      dockerfile: Dockerfile.dev
    container_name: nexus-dev
    ports:
      - "8080:8080"
      - "9229:9229"  # Debug port
    environment:
      - NODE_ENV=development
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=nexus_dev
      - DB_USERNAME=nexus
      - DB_PASSWORD=nexus_dev_password
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    volumes:
      - ./src:/app/src
      - ./config:/app/config
      - ./public:/app/public
      - node_modules:/app/node_modules
    depends_on:
      - postgres
      - redis
    networks:
      - nexus-dev

  postgres:
    image: postgres:15
    container_name: nexus-postgres-dev
    environment:
      - POSTGRES_DB=nexus_dev
      - POSTGRES_USER=nexus
      - POSTGRES_PASSWORD=nexus_dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data
      - ./sql/init:/docker-entrypoint-initdb.d
    networks:
      - nexus-dev

  redis:
    image: redis:7-alpine
    container_name: nexus-redis-dev
    ports:
      - "6379:6379"
    volumes:
      - redis_dev_data:/data
    networks:
      - nexus-dev

  mailhog:
    image: mailhog/mailhog
    container_name: nexus-mailhog-dev
    ports:
      - "1025:1025"  # SMTP
      - "8025:8025"  # Web UI
    networks:
      - nexus-dev

volumes:
  postgres_dev_data:
  redis_dev_data:
  node_modules:

networks:
  nexus-dev:
    driver: bridge
```

### Development Dockerfile

Create `Dockerfile.dev`:

```dockerfile
FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Expose ports
EXPOSE 8080 9229

# Development command with nodemon and debugging
CMD ["npm", "run", "dev:debug"]
```

### Start Docker Development Environment

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f nexus

# Stop services
docker-compose -f docker-compose.dev.yml down
```

## Development Scripts

### Package.json Scripts

```json
{
  "scripts": {
    "dev": "nodemon src/index.js",
    "dev:debug": "nodemon --inspect=0.0.0.0:9229 src/index.js",
    "dev:watch": "nodemon --watch src --watch config src/index.js",
    "dev:production": "NODE_ENV=production npm run dev",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "test:e2e": "npm run test:e2e:setup && jest --config jest.e2e.config.js",
    "lint": "eslint src/**/*.js",
    "lint:fix": "eslint src/**/*.js --fix",
    "format": "prettier --write src/**/*.js",
    "db:migrate": "knex migrate:latest",
    "db:rollback": "knex migrate:rollback",
    "db:seed": "knex seed:run",
    "db:reset": "npm run db:rollback && npm run db:migrate && npm run db:seed",
    "build": "webpack --mode production",
    "build:dev": "webpack --mode development",
    "build:watch": "webpack --mode development --watch"
  }
}
```

### Development Helper Scripts

Create `scripts/dev-setup.sh`:

```bash
#!/bin/bash

# Development setup script
echo "Setting up Nexus development environment..."

# Check dependencies
command -v node >/dev/null 2>&1 || { echo "Node.js is required"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "npm is required"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "Git is required"; exit 1; }

# Install dependencies
echo "Installing dependencies..."
npm install

# Setup environment
if [ ! -f .env.local ]; then
    echo "Creating environment file..."
    cp .env.example .env.local
    echo "Please edit .env.local with your configuration"
fi

# Setup database
echo "Setting up database..."
npm run db:migrate
npm run db:seed

# Setup git hooks
echo "Setting up git hooks..."
npx husky install

echo "Development environment setup complete!"
echo "Run 'npm run dev' to start the development server"
```

## IDE Configuration

### VS Code Setup

Create `.vscode/settings.json`:

```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "eslint.validate": ["javascript", "javascriptreact"],
  "files.exclude": {
    "node_modules": true,
    "dist": true,
    "coverage": true
  },
  "search.exclude": {
    "node_modules": true,
    "dist": true,
    "coverage": true
  }
}
```

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Launch Nexus",
      "type": "node",
      "request": "launch",
      "program": "${workspaceFolder}/src/index.js",
      "env": {
        "NODE_ENV": "development"
      },
      "console": "integratedTerminal",
      "restart": true,
      "runtimeExecutable": "nodemon",
      "skipFiles": ["<node_internals>/**"]
    },
    {
      "name": "Debug Nexus",
      "type": "node",
      "request": "launch",
      "program": "${workspaceFolder}/src/index.js",
      "env": {
        "NODE_ENV": "development",
        "DEBUG": "nexus:*"
      },
      "console": "integratedTerminal"
    },
    {
      "name": "Attach to Docker",
      "type": "node",
      "request": "attach",
      "port": 9229,
      "address": "localhost",
      "localRoot": "${workspaceFolder}",
      "remoteRoot": "/app",
      "skipFiles": ["<node_internals>/**"]
    }
  ]
}
```

Create `.vscode/extensions.json`:

```json
{
  "recommendations": [
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "ms-vscode.vscode-json",
    "bradlc.vscode-tailwindcss",
    "formulahendry.auto-rename-tag",
    "christian-kohler.path-intellisense",
    "ms-vscode.vscode-typescript-next"
  ]
}
```

## Testing Setup

### Jest Configuration

Create `jest.config.js`:

```javascript
module.exports = {
  testEnvironment: 'node',
  roots: ['<rootDir>/src', '<rootDir>/tests'],
  testMatch: [
    '**/__tests__/**/*.js',
    '**/?(*.)+(spec|test).js'
  ],
  collectCoverageFrom: [
    'src/**/*.js',
    '!src/**/*.spec.js',
    '!src/**/*.test.js'
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  setupFilesAfterEnv: ['<rootDir>/tests/setup.js'],
  testTimeout: 10000
};
```

### Test Database Setup

Create `tests/setup.js`:

```javascript
const { Pool } = require('pg');

let testDb;

beforeAll(async () => {
  // Setup test database
  testDb = new Pool({
    host: process.env.TEST_DB_HOST || 'localhost',
    port: process.env.TEST_DB_PORT || 5432,
    database: process.env.TEST_DB_NAME || 'nexus_test',
    user: process.env.TEST_DB_USER || 'nexus',
    password: process.env.TEST_DB_PASSWORD || 'nexus_test_password'
  });

  // Run migrations
  await runMigrations(testDb);
});

afterAll(async () => {
  if (testDb) {
    await testDb.end();
  }
});

beforeEach(async () => {
  // Clear test data
  await clearTestData(testDb);
});
```

## Debugging

### Debug Configuration

Create `debug.js`:

```javascript
const debug = require('debug');

// Create debug namespaces
module.exports = {
  app: debug('nexus:app'),
  db: debug('nexus:db'),
  auth: debug('nexus:auth'),
  api: debug('nexus:api'),
  plugins: debug('nexus:plugins'),
  events: debug('nexus:events')
};
```

### Debug Usage

```javascript
const { app, db } = require('./debug');

// Use in your code
app('Application starting on port %d', port);
db('Database connection established');
```

### Chrome DevTools

```bash
# Start with debugging enabled
npm run dev:debug

# Open Chrome and navigate to:
# chrome://inspect/#devices
```

## Hot Reloading

### Nodemon Configuration

Create `nodemon.json`:

```json
{
  "watch": ["src", "config"],
  "ext": "js,json",
  "ignore": ["src/**/*.test.js", "src/**/*.spec.js"],
  "env": {
    "NODE_ENV": "development"
  },
  "delay": 1000
}
```

### Webpack Hot Module Replacement

Create `webpack.dev.js`:

```javascript
const webpack = require('webpack');
const path = require('path');

module.exports = {
  mode: 'development',
  entry: './src/client/index.js',
  output: {
    path: path.resolve(__dirname, 'public/dist'),
    filename: 'bundle.js',
    publicPath: '/dist/'
  },
  devServer: {
    hot: true,
    port: 3001,
    proxy: {
      '/api': 'http://localhost:8080'
    }
  },
  plugins: [
    new webpack.HotModuleReplacementPlugin()
  ]
};
```

## Mock Data and Services

### Mock Data Generator

Create `scripts/generate-mock-data.js`:

```javascript
const faker = require('faker');
const db = require('../src/database');

async function generateMockData() {
  console.log('Generating mock data...');

  // Generate users
  const users = [];
  for (let i = 0; i < 50; i++) {
    users.push({
      username: faker.internet.userName(),
      email: faker.internet.email(),
      firstName: faker.name.firstName(),
      lastName: faker.name.lastName(),
      createdAt: faker.date.past()
    });
  }

  await db('users').insert(users);
  console.log(`Generated ${users.length} users`);

  // Generate other mock data...
}

generateMockData().catch(console.error);
```

### Mock External Services

Create `src/mocks/email.js`:

```javascript
class MockEmailService {
  async sendEmail(to, subject, body) {
    console.log('Mock Email:', { to, subject, body });
    return { success: true, messageId: 'mock-123' };
  }
}

module.exports = MockEmailService;
```

## Performance Profiling

### Memory Usage Monitoring

```javascript
const process = require('process');

// Monitor memory usage
setInterval(() => {
  const usage = process.memoryUsage();
  console.log('Memory Usage:', {
    rss: Math.round(usage.rss / 1024 / 1024) + 'MB',
    heapTotal: Math.round(usage.heapTotal / 1024 / 1024) + 'MB',
    heapUsed: Math.round(usage.heapUsed / 1024 / 1024) + 'MB'
  });
}, 30000);
```

### CPU Profiling

```bash
# Start with CPU profiling
node --prof src/index.js

# Generate profile report
node --prof-process isolate-*.log > profile.txt
```

## Common Development Tasks

### Database Operations

```bash
# Reset database
npm run db:reset

# Create new migration
npx knex migrate:make create_new_table

# Create new seed
npx knex seed:make new_seed_data

# Check database status
npm run db:status
```

### Code Quality

```bash
# Run linting
npm run lint

# Fix linting issues
npm run lint:fix

# Format code
npm run format

# Run tests
npm test

# Run tests in watch mode
npm run test:watch
```

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/new-feature

# Commit with conventional commits
git commit -m "feat: add new feature"

# Run pre-commit hooks
npm run pre-commit

# Push and create PR
git push -u origin feature/new-feature
```

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Find process using port
lsof -i :8080

# Kill process
kill -9 <PID>

# Or use different port
PORT=3000 npm run dev
```

#### Database Connection Issues

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U nexus -d nexus_dev

# Check environment variables
printenv | grep DB_
```

#### Node Modules Issues

```bash
# Clear npm cache
npm cache clean --force

# Remove node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Debug Logging

```bash
# Enable debug logging
DEBUG=nexus:* npm run dev

# Enable specific namespace
DEBUG=nexus:db npm run dev

# Disable debug logging
DEBUG= npm run dev
```

## Best Practices

### Development Workflow

1. Always work on feature branches
2. Write tests for new features
3. Use conventional commit messages
4. Run linting and tests before committing
5. Keep dependencies up to date
6. Document new features and APIs

### Code Organization

- Use meaningful file and directory names
- Keep functions small and focused
- Write self-documenting code
- Use consistent naming conventions
- Separate concerns properly

### Environment Management

- Never commit sensitive data
- Use environment-specific configuration
- Document all environment variables
- Use secure defaults for development

## See Also

- [Getting Started](../getting-started/README.md)
- [Configuration Guide](../guides/configuration.md)
- [Plugin Development](../plugins/README.md)
- [Testing Documentation](../plugins/testing.md)
