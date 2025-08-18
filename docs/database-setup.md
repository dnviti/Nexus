# Database Setup Guide

This guide explains how to configure and set up different database backends with the Nexus Platform. Nexus supports SQLite (default), PostgreSQL, MariaDB/MySQL, and MongoDB with full ORM integration.

## Quick Start

The Nexus Platform uses **SQLite by default** with zero configuration required. For production deployments, we recommend PostgreSQL or MongoDB depending on your needs.

### Default SQLite Setup

```yaml
# No configuration needed - SQLite works out of the box
database:
  type: "sqlite"
  path: "./nexus.db"
```

### Installation Commands

```bash
# Default (SQLite only)
pip install nexus-platform

# With PostgreSQL support
pip install nexus-platform[postgresql]

# With MySQL/MariaDB support
pip install nexus-platform[mysql]

# With MongoDB support
pip install nexus-platform[mongodb]

# With all database drivers
pip install nexus-platform[all-databases]
```

## Database Types

### 1. SQLite (Default)

**Best for:** Development, small deployments, single-server applications

**Pros:**
- Zero configuration
- No external dependencies
- Perfect for development
- ACID compliant
- Built into Python

**Cons:**
- Single writer limitation
- Not suitable for high-concurrency applications
- Limited scalability

**Configuration:**

```yaml
database:
  type: "sqlite"
  path: "./nexus.db"           # Database file path
  pool_size: 5                 # Connection pool size
  pool_timeout: 30             # Pool timeout in seconds
```

**Connection URL format:**
```
sqlite+aiosqlite:///./nexus.db
sqlite+aiosqlite:////absolute/path/to/nexus.db
```

### 2. PostgreSQL (Recommended for Production)

**Best for:** Production applications, high concurrency, complex queries

**Pros:**
- Excellent performance and scalability
- Advanced features (JSON, arrays, full-text search)
- Strong ACID compliance
- Excellent ecosystem
- Great for complex applications

**Cons:**
- Requires separate server setup
- More complex configuration

**Prerequisites:**
```bash
# Install PostgreSQL driver
pip install asyncpg psycopg2-binary

# Or install with extras
pip install nexus-platform[postgresql]
```

**Configuration:**

```yaml
database:
  type: "postgresql"
  host: "localhost"
  port: 5432
  database: "nexus"
  username: "nexus_user"
  password: "secure_password"
  pool_size: 20
  max_overflow: 30
  pool_timeout: 60

  # SSL configuration (production)
  ssl_enabled: true
  ssl_cert_path: "/path/to/client-cert.pem"
  ssl_key_path: "/path/to/client-key.pem"
  ssl_ca_path: "/path/to/ca-cert.pem"
```

**Connection URL format:**
```
postgresql+asyncpg://user:password@localhost:5432/nexus
```

**PostgreSQL Server Setup:**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE nexus;
CREATE USER nexus_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE nexus TO nexus_user;
\q
```

### 3. MariaDB/MySQL

**Best for:** Web applications, existing MySQL infrastructure

**Pros:**
- Wide adoption and support
- Good performance
- Familiar to many developers
- Strong ecosystem

**Cons:**
- Some limitations compared to PostgreSQL
- JSON support varies by version

**Prerequisites:**
```bash
# Install MySQL driver
pip install aiomysql pymysql

# Or install with extras
pip install nexus-platform[mysql]
```

**Configuration:**

```yaml
database:
  type: "mariadb"  # or "mysql"
  host: "localhost"
  port: 3306
  database: "nexus"
  username: "nexus_user"
  password: "secure_password"
  pool_size: 20
  max_overflow: 30
  pool_timeout: 60

  # SSL configuration
  ssl_enabled: true
  ssl_cert_path: "/path/to/client-cert.pem"
  ssl_key_path: "/path/to/client-key.pem"
  ssl_ca_path: "/path/to/ca-cert.pem"
```

**Connection URL format:**
```
mysql+aiomysql://user:password@localhost:3306/nexus
```

**MariaDB Server Setup:**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install mariadb-server

# Secure installation
sudo mysql_secure_installation

# Create database and user
sudo mysql
CREATE DATABASE nexus;
CREATE USER 'nexus_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON nexus.* TO 'nexus_user'@'localhost';
FLUSH PRIVILEGES;
exit
```

### 4. MongoDB

**Best for:** Document-based applications, flexible schemas, horizontal scaling

**Pros:**
- Schema flexibility
- Excellent horizontal scaling
- Rich query language
- Great for modern applications

**Cons:**
- Different from SQL paradigm
- Learning curve for SQL developers
- Eventual consistency by default

**Prerequisites:**
```bash
# Install MongoDB driver
pip install motor pymongo

# Or install with extras
pip install nexus-platform[mongodb]
```

**Configuration:**

```yaml
database:
  type: "mongodb"
  host: "localhost"
  port: 27017
  database: "nexus"
  username: "nexus_user"
  password: "secure_password"
  auth_source: "admin"

  # Replica set (production)
  replica_set: "nexus-replica-set"

  # SSL configuration
  ssl_enabled: true
  ssl_cert_path: "/path/to/client-cert.pem"
  ssl_ca_path: "/path/to/ca-cert.pem"
```

**Connection URL format:**
```
mongodb://user:password@localhost:27017/nexus
mongodb+srv://user:password@cluster.mongodb.net/nexus
```

**MongoDB Server Setup:**

```bash
# Ubuntu/Debian
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update
sudo apt install mongodb-org

# Start MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod

# Create user
mongosh
use admin
db.createUser({
  user: "nexus_user",
  pwd: "secure_password",
  roles: [{ role: "readWrite", db: "nexus" }]
})
```

## Environment Variables

Use environment variables for sensitive configuration:

```bash
# Database credentials
export NEXUS_DB_TYPE="postgresql"
export NEXUS_DB_HOST="localhost"
export NEXUS_DB_PORT="5432"
export NEXUS_DB_NAME="nexus"
export NEXUS_DB_USER="nexus_user"
export NEXUS_DB_PASSWORD="secure_password"

# SSL configuration
export NEXUS_DB_SSL_ENABLED="true"
export NEXUS_DB_SSL_CERT="/path/to/cert.pem"
export NEXUS_DB_SSL_KEY="/path/to/key.pem"
export NEXUS_DB_SSL_CA="/path/to/ca.pem"
```

Configuration with environment variables:

```yaml
database:
  type: "${NEXUS_DB_TYPE:-sqlite}"
  host: "${NEXUS_DB_HOST:-localhost}"
  port: "${NEXUS_DB_PORT:-5432}"
  database: "${NEXUS_DB_NAME:-nexus}"
  username: "${NEXUS_DB_USER}"
  password: "${NEXUS_DB_PASSWORD}"
  ssl_enabled: "${NEXUS_DB_SSL_ENABLED:-false}"
```

## Docker Configurations

### PostgreSQL with Docker

```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: nexus
      POSTGRES_USER: nexus_user
      POSTGRES_PASSWORD: nexus123
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  nexus:
    image: nexus-platform:latest
    environment:
      NEXUS_DB_TYPE: postgresql
      NEXUS_DB_HOST: postgres
      NEXUS_DB_PORT: 5432
      NEXUS_DB_NAME: nexus
      NEXUS_DB_USER: nexus_user
      NEXUS_DB_PASSWORD: nexus123
    depends_on:
      - postgres

volumes:
  postgres_data:
```

### MongoDB with Docker

```yaml
# docker-compose.yml
version: '3.8'
services:
  mongodb:
    image: mongo:7
    environment:
      MONGO_INITDB_ROOT_USERNAME: nexus_user
      MONGO_INITDB_ROOT_PASSWORD: nexus123
      MONGO_INITDB_DATABASE: nexus
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db

  nexus:
    image: nexus-platform:latest
    environment:
      NEXUS_DB_TYPE: mongodb
      NEXUS_DB_HOST: mongodb
      NEXUS_DB_PORT: 27017
      NEXUS_DB_NAME: nexus
      NEXUS_DB_USER: nexus_user
      NEXUS_DB_PASSWORD: nexus123
    depends_on:
      - mongodb

volumes:
  mongodb_data:
```

## Cloud Database Services

### AWS RDS (PostgreSQL)

```yaml
database:
  type: "postgresql"
  host: "nexus-db.cluster-xyz.us-east-1.rds.amazonaws.com"
  port: 5432
  database: "nexus"
  username: "nexus_admin"
  password: "${AWS_RDS_PASSWORD}"
  pool_size: 20
  max_overflow: 40
  ssl_enabled: true
```

### Azure Database for PostgreSQL

```yaml
database:
  type: "postgresql"
  host: "nexus-db.postgres.database.azure.com"
  port: 5432
  database: "nexus"
  username: "nexus@nexus-db"
  password: "${AZURE_DB_PASSWORD}"
  ssl_enabled: true
```

### Google Cloud SQL

```yaml
database:
  type: "postgresql"
  # Unix socket connection for Cloud SQL
  host: "/cloudsql/project-id:region:instance-name"
  database: "nexus"
  username: "nexus"
  password: "${GCP_DB_PASSWORD}"
```

### MongoDB Atlas

```yaml
database:
  type: "mongodb"
  url: "mongodb+srv://nexus:${MONGODB_PASSWORD}@cluster.mongodb.net/nexus?retryWrites=true&w=majority"
  auth_source: "admin"
```

## Performance Tuning

### Connection Pool Settings

```yaml
database:
  # For high-traffic applications
  pool_size: 50              # Base connections
  max_overflow: 100          # Additional connections
  pool_timeout: 120          # Timeout in seconds

  # For low-traffic applications
  pool_size: 5
  max_overflow: 10
  pool_timeout: 30
```

### PostgreSQL Optimization

```sql
-- postgresql.conf optimizations
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
```

### MongoDB Optimization

```javascript
// Create indexes for better performance
db.nexus_kv_store.createIndex({ "key": 1 }, { unique: true })
db.nexus_kv_store.createIndex({ "created_at": 1 })
db.nexus_kv_store.createIndex({ "updated_at": 1 })
```

## Migration and Backup

### Database Migration

```bash
# Create backup before migration
nexus admin backup create --output backup.sql

# Test migration on staging
NEXUS_DB_NAME=nexus_staging nexus admin system migrate

# Production migration
nexus admin system migrate
```

### Backup Strategies

```bash
# PostgreSQL backup
pg_dump -h localhost -U nexus_user nexus > nexus_backup.sql

# MongoDB backup
mongodump --host localhost --db nexus --out ./backup/

# SQLite backup
cp nexus.db nexus_backup.db
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   ```bash
   # Check if database server is running
   sudo systemctl status postgresql
   sudo systemctl status mongod

   # Check port availability
   netstat -tulpn | grep :5432
   netstat -tulpn | grep :27017
   ```

2. **Authentication Failed**
   ```bash
   # Test database connection
   psql -h localhost -U nexus_user -d nexus
   mongosh --host localhost --username nexus_user --authenticationDatabase admin
   ```

3. **Pool Exhaustion**
   ```yaml
   # Increase pool size
   database:
     pool_size: 50
     max_overflow: 100
   ```

4. **SSL Connection Issues**
   ```bash
   # Check SSL certificate validity
   openssl x509 -in client-cert.pem -text -noout

   # Test SSL connection
   psql "sslmode=require host=localhost user=nexus_user dbname=nexus"
   ```

### Debugging

Enable database debugging:

```yaml
logging:
  level: "DEBUG"
  loggers:
    nexus.database: "DEBUG"
    sqlalchemy.engine: "INFO"  # SQL query logging
```

### Health Checks

```bash
# Check database health
nexus admin system health --component database

# Test database connection
python -c "
import asyncio
from nexus.database import create_database_adapter, DatabaseConfig

async def test():
    config = DatabaseConfig(type='postgresql', host='localhost')
    adapter = create_database_adapter(config)
    await adapter.connect()
    health = await adapter.health_check()
    print(health)
    await adapter.disconnect()

asyncio.run(test())
"
```

## Security Best Practices

1. **Use Environment Variables**
   ```bash
   # Never hardcode passwords
   export NEXUS_DB_PASSWORD="$(openssl rand -base64 32)"
   ```

2. **Enable SSL/TLS**
   ```yaml
   database:
     ssl_enabled: true
     ssl_cert_path: "/path/to/cert.pem"
   ```

3. **Restrict Database User Permissions**
   ```sql
   -- PostgreSQL: Grant minimal necessary permissions
   GRANT CONNECT ON DATABASE nexus TO nexus_user;
   GRANT USAGE ON SCHEMA public TO nexus_user;
   GRANT CREATE ON SCHEMA public TO nexus_user;
   ```

4. **Network Security**
   ```bash
   # Configure firewall
   sudo ufw allow from 10.0.0.0/8 to any port 5432
   ```

5. **Regular Backups**
   ```bash
   # Automated backup script
   #!/bin/bash
   DATE=$(date +%Y%m%d_%H%M%S)
   pg_dump -h localhost -U nexus_user nexus > "backup_${DATE}.sql"
   ```

## Next Steps

- [Plugin Development](plugins/basics.md) - Learn how plugins interact with the database
- [API Documentation](api/core.md) - Database-related API endpoints
- [Deployment Guide](deployment/docker.md) - Production deployment with databases
- [Monitoring](deployment/monitoring.md) - Database monitoring and alerting
