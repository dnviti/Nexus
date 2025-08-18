# Development Guide

This comprehensive guide covers development practices, workflows, and best practices for contributing to the Nexus platform.

## Overview

The Nexus development guide provides developers with everything they need to contribute effectively to the platform, including coding standards, development workflows, testing practices, and contribution guidelines.

## Getting Started

### Development Environment Setup

#### Prerequisites

- **Node.js**: 18.x or later
- **npm/yarn**: Latest version
- **Git**: 2.x or later
- **Docker**: 20.10+ (recommended)
- **PostgreSQL**: 13+ (or Docker)
- **Redis**: 6.0+ (or Docker)

#### Initial Setup

```bash
# Clone the repository
git clone https://github.com/nexus/nexus.git
cd nexus

# Install dependencies
npm install

# Copy environment configuration
cp .env.example .env.local

# Setup database
npm run db:setup

# Start development server
npm run dev
```

## Project Structure

### Directory Layout

```
nexus/
├── src/                    # Source code
│   ├── api/               # API routes and controllers
│   ├── core/              # Core application logic
│   ├── plugins/           # Plugin system
│   ├── services/          # Business logic services
│   ├── models/            # Data models
│   ├── middleware/        # Express middleware
│   ├── utils/             # Utility functions
│   └── index.js           # Application entry point
├── tests/                 # Test files
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   ├── e2e/               # End-to-end tests
│   └── fixtures/          # Test data
├── docs/                  # Documentation
├── config/                # Configuration files
├── migrations/            # Database migrations
├── seeds/                 # Database seeds
├── public/                # Static assets
├── scripts/               # Build and utility scripts
└── tools/                 # Development tools
```

### Key Files

- `package.json`: Dependencies and scripts
- `.env.example`: Environment variables template
- `docker-compose.yml`: Docker services configuration
- `jest.config.js`: Testing configuration
- `eslint.config.js`: Linting configuration
- `prettier.config.js`: Code formatting configuration

## Coding Standards

### JavaScript/ES6+ Guidelines

#### Code Style

```javascript
// Use const for immutable values
const API_VERSION = 'v1';

// Use let for mutable values
let currentUser = null;

// Use arrow functions for short functions
const transform = (data) => data.map(item => item.value);

// Use async/await instead of callbacks
async function fetchUser(id) {
  try {
    const user = await userService.findById(id);
    return user;
  } catch (error) {
    logger.error('Failed to fetch user', { id, error });
    throw error;
  }
}
```

#### Naming Conventions

```javascript
// Use camelCase for variables and functions
const userName = 'john_doe';
const getUserById = (id) => { /* ... */ };

// Use PascalCase for classes and constructors
class UserService {
  constructor(database) {
    this.database = database;
  }
}

// Use UPPER_SNAKE_CASE for constants
const MAX_RETRY_ATTEMPTS = 3;
const DEFAULT_TIMEOUT = 5000;

// Use descriptive names
const isUserAuthenticated = checkAuthStatus();
const userPermissions = getUserPermissions(userId);
```

#### Error Handling

```javascript
// Custom error classes
class ValidationError extends Error {
  constructor(message, field) {
    super(message);
    this.name = 'ValidationError';
    this.field = field;
  }
}

// Error handling in async functions
async function createUser(userData) {
  try {
    const validatedData = await validateUserData(userData);
    const user = await userRepository.create(validatedData);

    logger.info('User created successfully', { userId: user.id });
    return user;
  } catch (error) {
    if (error instanceof ValidationError) {
      throw new BadRequestError(error.message);
    }

    logger.error('Failed to create user', { userData, error });
    throw new InternalServerError('User creation failed');
  }
}
```

### API Design Principles

#### RESTful Endpoints

```javascript
// Resource-based URLs
GET    /api/users           // List users
POST   /api/users           // Create user
GET    /api/users/:id       // Get user
PUT    /api/users/:id       // Update user
DELETE /api/users/:id       // Delete user

// Nested resources
GET    /api/users/:id/posts // Get user's posts
POST   /api/users/:id/posts // Create post for user
```

#### Response Format

```javascript
// Success responses
{
  "success": true,
  "data": {
    "id": "user-123",
    "username": "johndoe",
    "email": "john@example.com"
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "1.0.0"
  }
}

// Error responses
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid email format",
    "details": {
      "field": "email",
      "value": "invalid-email"
    }
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "requestId": "req-123"
  }
}
```

## Development Workflow

### Git Workflow

#### Branch Strategy

```bash
# Main branches
main            # Production-ready code
develop         # Integration branch

# Feature branches
feature/user-authentication
feature/plugin-system
feature/dashboard-ui

# Release branches
release/v1.2.0

# Hotfix branches
hotfix/security-patch
```

#### Commit Messages

```bash
# Format: type(scope): description

feat(auth): add OAuth2 authentication support
fix(api): resolve user endpoint validation error
docs(readme): update installation instructions
test(users): add unit tests for user service
refactor(core): simplify plugin loading mechanism
```

#### Pull Request Process

1. **Create feature branch from develop**
2. **Implement changes with tests**
3. **Update documentation**
4. **Run linting and tests**
5. **Create pull request**
6. **Request code review**
7. **Address feedback**
8. **Merge after approval**

### Code Review Guidelines

#### Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] No security vulnerabilities
- [ ] Performance considerations addressed
- [ ] Error handling is appropriate
- [ ] API changes are backward compatible

#### Review Comments

```javascript
// Good: Specific and actionable
// Consider using a Map for O(1) lookup instead of array.find()
const userMap = new Map(users.map(u => [u.id, u]));

// Good: Suggests improvement
// This function is doing too much. Consider splitting into smaller functions.

// Good: Explains reasoning
// We should validate input here to prevent SQL injection attacks.
```

## Testing Strategy

### Test Types

#### Unit Tests

```javascript
// src/services/userService.test.js
const UserService = require('./userService');
const userRepository = require('../repositories/userRepository');

jest.mock('../repositories/userRepository');

describe('UserService', () => {
  let userService;

  beforeEach(() => {
    userService = new UserService();
    jest.clearAllMocks();
  });

  describe('createUser', () => {
    it('should create user with valid data', async () => {
      // Arrange
      const userData = {
        username: 'testuser',
        email: 'test@example.com'
      };

      const expectedUser = { id: '123', ...userData };
      userRepository.create.mockResolvedValue(expectedUser);

      // Act
      const result = await userService.createUser(userData);

      // Assert
      expect(userRepository.create).toHaveBeenCalledWith(userData);
      expect(result).toEqual(expectedUser);
    });

    it('should throw error for invalid email', async () => {
      // Arrange
      const userData = {
        username: 'testuser',
        email: 'invalid-email'
      };

      // Act & Assert
      await expect(userService.createUser(userData))
        .rejects.toThrow('Invalid email format');
    });
  });
});
```

#### Integration Tests

```javascript
// tests/integration/api/users.test.js
const request = require('supertest');
const app = require('../../../src/app');
const db = require('../../../src/database');

describe('Users API', () => {
  beforeEach(async () => {
    await db.migrate.latest();
    await db.seed.run();
  });

  afterEach(async () => {
    await db.migrate.rollback();
  });

  describe('POST /api/users', () => {
    it('should create new user', async () => {
      const userData = {
        username: 'newuser',
        email: 'newuser@example.com',
        password: 'password123'
      };

      const response = await request(app)
        .post('/api/users')
        .send(userData)
        .expect(201);

      expect(response.body.success).toBe(true);
      expect(response.body.data.username).toBe(userData.username);
      expect(response.body.data.password).toBeUndefined();
    });
  });
});
```

#### End-to-End Tests

```javascript
// tests/e2e/userJourney.test.js
const { chromium } = require('playwright');

describe('User Journey', () => {
  let browser, page;

  beforeAll(async () => {
    browser = await chromium.launch();
    page = await browser.newPage();
  });

  afterAll(async () => {
    await browser.close();
  });

  test('user can register and login', async () => {
    // Navigate to registration page
    await page.goto('http://localhost:8080/register');

    // Fill registration form
    await page.fill('#username', 'testuser');
    await page.fill('#email', 'test@example.com');
    await page.fill('#password', 'password123');
    await page.click('#submit');

    // Verify redirect to dashboard
    await page.waitForURL('**/dashboard');
    expect(await page.textContent('h1')).toBe('Dashboard');
  });
});
```

### Test Data Management

#### Fixtures

```javascript
// tests/fixtures/users.js
module.exports = {
  validUser: {
    username: 'testuser',
    email: 'test@example.com',
    firstName: 'Test',
    lastName: 'User'
  },

  adminUser: {
    username: 'admin',
    email: 'admin@example.com',
    role: 'admin',
    permissions: ['read', 'write', 'admin']
  },

  userList: [
    {
      id: '1',
      username: 'user1',
      email: 'user1@example.com'
    },
    {
      id: '2',
      username: 'user2',
      email: 'user2@example.com'
    }
  ]
};
```

#### Test Factories

```javascript
// tests/factories/userFactory.js
const { faker } = require('@faker-js/faker');

class UserFactory {
  static create(overrides = {}) {
    return {
      id: faker.datatype.uuid(),
      username: faker.internet.userName(),
      email: faker.internet.email(),
      firstName: faker.name.firstName(),
      lastName: faker.name.lastName(),
      createdAt: faker.date.past(),
      ...overrides
    };
  }

  static createMany(count = 5, overrides = {}) {
    return Array.from({ length: count }, () => this.create(overrides));
  }
}

module.exports = UserFactory;
```

## Database Development

### Migration Management

#### Creating Migrations

```javascript
// migrations/20240115_create_users_table.js
exports.up = function(knex) {
  return knex.schema.createTable('users', function(table) {
    table.uuid('id').primary().defaultTo(knex.raw('gen_random_uuid()'));
    table.string('username').unique().notNullable();
    table.string('email').unique().notNullable();
    table.string('password_hash').notNullable();
    table.string('first_name');
    table.string('last_name');
    table.enum('role', ['user', 'admin']).defaultTo('user');
    table.boolean('active').defaultTo(true);
    table.timestamps(true, true);

    table.index(['username']);
    table.index(['email']);
    table.index(['role']);
  });
};

exports.down = function(knex) {
  return knex.schema.dropTable('users');
};
```

#### Seeding Data

```javascript
// seeds/01_users.js
const bcrypt = require('bcrypt');

exports.seed = async function(knex) {
  await knex('users').del();

  const adminPassword = await bcrypt.hash('admin123', 10);
  const userPassword = await bcrypt.hash('user123', 10);

  await knex('users').insert([
    {
      username: 'admin',
      email: 'admin@nexus.local',
      password_hash: adminPassword,
      first_name: 'Admin',
      last_name: 'User',
      role: 'admin'
    },
    {
      username: 'testuser',
      email: 'user@nexus.local',
      password_hash: userPassword,
      first_name: 'Test',
      last_name: 'User',
      role: 'user'
    }
  ]);
};
```

### Query Optimization

#### Efficient Queries

```javascript
// Good: Use specific columns
const users = await db('users')
  .select('id', 'username', 'email')
  .where('active', true)
  .limit(10);

// Good: Use joins instead of N+1 queries
const usersWithPosts = await db('users')
  .select('users.*', 'posts.title')
  .leftJoin('posts', 'users.id', 'posts.user_id')
  .where('users.active', true);

// Good: Use indexes
const user = await db('users')
  .where('email', email) // email column should be indexed
  .first();
```

## Performance Optimization

### Code Performance

#### Async Operations

```javascript
// Good: Parallel execution
const [users, posts, comments] = await Promise.all([
  fetchUsers(),
  fetchPosts(),
  fetchComments()
]);

// Good: Use streaming for large datasets
const processLargeDataset = async () => {
  const stream = db('large_table').stream();

  stream.on('data', (chunk) => {
    // Process chunk
    processChunk(chunk);
  });

  return new Promise((resolve, reject) => {
    stream.on('end', resolve);
    stream.on('error', reject);
  });
};
```

#### Memory Management

```javascript
// Good: Clean up resources
class DatabaseConnection {
  constructor() {
    this.pool = createConnectionPool();
  }

  async query(sql, params) {
    const connection = await this.pool.getConnection();
    try {
      return await connection.query(sql, params);
    } finally {
      connection.release();
    }
  }

  async close() {
    await this.pool.end();
  }
}
```

### Caching Strategies

#### Redis Caching

```javascript
const redis = require('redis');
const client = redis.createClient();

class CacheService {
  async get(key) {
    try {
      const cached = await client.get(key);
      return cached ? JSON.parse(cached) : null;
    } catch (error) {
      logger.error('Cache get error', { key, error });
      return null;
    }
  }

  async set(key, value, ttl = 3600) {
    try {
      await client.setex(key, ttl, JSON.stringify(value));
    } catch (error) {
      logger.error('Cache set error', { key, error });
    }
  }

  async invalidate(pattern) {
    try {
      const keys = await client.keys(pattern);
      if (keys.length > 0) {
        await client.del(keys);
      }
    } catch (error) {
      logger.error('Cache invalidation error', { pattern, error });
    }
  }
}
```

## Security Considerations

### Input Validation

```javascript
const Joi = require('joi');

const userSchema = Joi.object({
  username: Joi.string().alphanum().min(3).max(30).required(),
  email: Joi.string().email().required(),
  password: Joi.string().min(8).pattern(new RegExp('^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#\$%\^&\*])')).required(),
  age: Joi.number().integer().min(18).max(100)
});

const validateUser = (userData) => {
  const { error, value } = userSchema.validate(userData);
  if (error) {
    throw new ValidationError(error.details[0].message);
  }
  return value;
};
```

### SQL Injection Prevention

```javascript
// Good: Use parameterized queries
const getUserByEmail = async (email) => {
  return await db('users')
    .where('email', email) // Knex automatically escapes
    .first();
};

// Good: Validate input
const searchUsers = async (query) => {
  if (typeof query !== 'string' || query.length > 100) {
    throw new ValidationError('Invalid search query');
  }

  return await db('users')
    .where('username', 'like', `%${query}%`)
    .orWhere('email', 'like', `%${query}%`);
};
```

### Authentication & Authorization

```javascript
const jwt = require('jsonwebtoken');

const authenticateToken = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({ error: 'Access token required' });
  }

  jwt.verify(token, process.env.JWT_SECRET, (err, user) => {
    if (err) {
      return res.status(403).json({ error: 'Invalid token' });
    }
    req.user = user;
    next();
  });
};

const requireRole = (role) => {
  return (req, res, next) => {
    if (!req.user || req.user.role !== role) {
      return res.status(403).json({ error: 'Insufficient permissions' });
    }
    next();
  };
};
```

## Debugging Techniques

### Logging Best Practices

```javascript
const logger = require('winston').createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' })
  ]
});

// Usage in application
const createUser = async (userData) => {
  const correlationId = generateCorrelationId();

  logger.info('Creating user', {
    correlationId,
    username: userData.username,
    email: userData.email
  });

  try {
    const user = await userService.create(userData);

    logger.info('User created successfully', {
      correlationId,
      userId: user.id
    });

    return user;
  } catch (error) {
    logger.error('User creation failed', {
      correlationId,
      error: error.message,
      stack: error.stack,
      userData: sanitizeUserData(userData)
    });
    throw error;
  }
};
```

### Debugging Tools

#### Debug Configuration

```javascript
// Use debug module for development
const debug = require('debug');

const dbDebug = debug('nexus:db');
const apiDebug = debug('nexus:api');
const authDebug = debug('nexus:auth');

// Usage
const executeQuery = async (sql, params) => {
  dbDebug('Executing query: %s', sql);
  dbDebug('Parameters: %O', params);

  const result = await db.raw(sql, params);

  dbDebug('Query result: %O', result);
  return result;
};
```

## Documentation Standards

### Code Documentation

```javascript
/**
 * Creates a new user in the system
 * @param {Object} userData - User data object
 * @param {string} userData.username - Unique username
 * @param {string} userData.email - User's email address
 * @param {string} userData.password - Plain text password (will be hashed)
 * @param {string} [userData.firstName] - User's first name
 * @param {string} [userData.lastName] - User's last name
 * @returns {Promise<Object>} Created user object (without password)
 * @throws {ValidationError} When user data is invalid
 * @throws {ConflictError} When username or email already exists
 * @example
 * const user = await createUser({
 *   username: 'johndoe',
 *   email: 'john@example.com',
 *   password: 'securePassword123'
 * });
 */
async function createUser(userData) {
  // Implementation
}
```

### API Documentation

```javascript
/**
 * @swagger
 * /api/users:
 *   post:
 *     summary: Create a new user
 *     tags: [Users]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - username
 *               - email
 *               - password
 *             properties:
 *               username:
 *                 type: string
 *                 minLength: 3
 *                 maxLength: 30
 *               email:
 *                 type: string
 *                 format: email
 *               password:
 *                 type: string
 *                 minLength: 8
 *     responses:
 *       201:
 *         description: User created successfully
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/User'
 *       400:
 *         description: Invalid input data
 *       409:
 *         description: Username or email already exists
 */
```

## Contribution Guidelines

### Before Contributing

1. **Read the documentation**
2. **Check existing issues**
3. **Discuss major changes**
4. **Follow coding standards**
5. **Write tests**
6. **Update documentation**

### Submitting Changes

#### Pull Request Template

```markdown
## Description
Brief description of the changes made.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

### Issue Reporting

#### Bug Reports

```markdown
## Bug Description
A clear description of the bug.

## Steps to Reproduce
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

## Expected Behavior
What you expected to happen.

## Actual Behavior
What actually happened.

## Environment
- OS: [e.g., Windows 10]
- Node.js version: [e.g., 18.15.0]
- Nexus version: [e.g., 1.2.0]
```

## Development Tools

### Recommended Extensions

#### VS Code Extensions

- ESLint
- Prettier
- Jest
- GitLens
- REST Client
- Docker
- PostgreSQL

#### Configuration Files

```json
// .vscode/settings.json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "eslint.validate": ["javascript"],
  "files.exclude": {
    "node_modules": true,
    "coverage": true
  }
}
```

### Useful Scripts

```json
// package.json scripts
{
  "scripts": {
    "dev": "nodemon src/index.js",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "lint": "eslint src/**/*.js",
    "lint:fix": "eslint src/**/*.js --fix",
    "format": "prettier --write src/**/*.js",
    "db:migrate": "knex migrate:latest",
    "db:seed": "knex seed:run",
    "db:reset": "knex migrate:rollback && npm run db:migrate && npm run db:seed"
  }
}
```

## Common Patterns

### Service Layer Pattern

```javascript
// services/userService.js
class UserService {
  constructor(userRepository, emailService, logger) {
    this.userRepository = userRepository;
    this.emailService = emailService;
    this.logger = logger;
  }

  async createUser(userData) {
    // Validate input
    const validatedData = this.validateUserData(userData);

    // Check for duplicates
    await this.checkDuplicates(validatedData);

    // Hash password
    const hashedPassword = await this.hashPassword(validatedData.password);

    // Create user
    const user = await this.userRepository.create({
      ...validatedData,
      password: hashedPassword
    });

    // Send welcome email
    await this.emailService.sendWelcomeEmail(user);

    // Log success
    this.logger.info('User created', { userId: user.id });

    return this.sanitizeUser(user);
  }
}
```

### Repository Pattern

```javascript
// repositories/userRepository.js
class UserRepository {
  constructor(database) {
    this.db = database;
  }

  async findById(id) {
    return await this.db('users').where('id', id).first();
  }

  async findByEmail(email) {
    return await this.db('users').where('email', email).first();
  }

  async create(userData) {
    const [user] = await this.db('users').insert(userData).returning('*');
    return user;
  }

  async update(id, updateData) {
    const [user] = await this.db('users')
      .where('id', id)
      .update(updateData)
      .returning('*');
    return user;
  }

  async delete(id) {
    return await this.db('users').where('id', id).del();
  }
}
```

## Troubleshooting

### Common Issues

#### Database Connection Problems

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U nexus -d nexus_dev

# Check environment variables
echo $DB_HOST $DB_PORT $DB_NAME
```

#### Node Modules Issues

```bash
# Clear npm cache
npm cache clean --force

# Remove and reinstall
rm -rf node_modules package-lock.json
npm install
```

#### Port Conflicts

```bash
# Find process using port
lsof -i :8080

# Kill process
kill -9 <PID>

# Use different port
PORT=3000 npm run dev
```

### Debug Mode

```bash
# Enable debug output
DEBUG=nexus:* npm run dev

# Enable specific modules
DEBUG=nexus:db,nexus:auth npm run dev

# Debug with VS Code
npm run dev:debug
```

## Resources

### External Documentation

- [Node.js Best Practices](https://github.com/goldbergyoni/nodebestpractices)
- [JavaScript Style Guide](https://github.com/airbnb/javascript)
- [Express.js Documentation](https://expressjs.com/)
- [Jest Testing Framework](https://jestjs.io/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

### Internal Links

- [API Documentation](../api/README.md)
- [Plugin Development](../plugins/README.md)
- [Configuration Guide](configuration.md)
- [Deployment Guide](../deployment/README.md)

---

This development guide is a living document. Please contribute improvements and keep it updated as the project evolves.
