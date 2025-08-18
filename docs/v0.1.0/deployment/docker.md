# Docker Deployment

Complete guide for deploying Nexus using Docker containers.

## 🎯 Overview

Docker provides the easiest and most consistent way to deploy Nexus across different environments. This guide covers everything from basic single-container setups to production-ready multi-service deployments.

## 🏗️ Architecture

```mermaid
graph TB
    subgraph "Docker Environment"
        A[Nginx Container]
        B[Nexus App Container]
        C[PostgreSQL Container]
        D[Redis Container]
        E[Monitoring Container]
    end

    subgraph "External"
        F[Load Balancer]
        G[Storage]
        H[Backup System]
    end

    F --> A
    A --> B
    B --> C
    B --> D
    B --> E
    G --> B
    H --> C
```

## 🚀 Quick Start

### Single Container

For development and testing:

```bash
# Pull the official image
docker pull nexus/platform:latest

# Run with basic configuration
docker run -d \
  --name nexus \
  -p 8000:8000 \
  -e DATABASE_URL=sqlite:///nexus.db \
  nexus/platform:latest

# Check if it's running
curl http://localhost:8000/api/v1/health
```

### Docker Compose (Recommended)

For complete development and production setups:

```yaml
# docker-compose.yml
version: "3.8"

services:
  nexus:
    image: nexus/platform:latest
    container_name: nexus-app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://nexus:nexus123@postgres:5432/nexus
      - REDIS_URL=redis://redis:6379/0
      - LOG_LEVEL=INFO
      - ENVIRONMENT=production
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./config:/app/config:ro
      - ./plugins:/app/plugins
      - ./logs:/app/logs
      - nexus_data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  postgres:
    image: postgres:15-alpine
    container_name: nexus-postgres
    environment:
      POSTGRES_DB: nexus
      POSTGRES_USER: nexus
      POSTGRES_PASSWORD: nexus123
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8 --lc-collate=C --lc-ctype=C"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init:/docker-entrypoint-initdb.d:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nexus -d nexus"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: nexus-redis
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  nginx:
    image: nginx:alpine
    container_name: nexus-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./nginx/logs:/var/log/nginx
    depends_on:
      - nexus
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  nexus_data:

networks:
  default:
    name: nexus-network
```

## 🔧 Building Custom Images

### Basic Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create application directory
WORKDIR /app

# Create non-root user
RUN groupadd -r nexus && useradd -r -g nexus nexus

# Copy application code
COPY --chown=nexus:nexus . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/plugins && \
    chown -R nexus:nexus /app

# Switch to non-root user
USER nexus

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Start application
CMD ["python", "main.py"]
```

### Multi-stage Build with Optimization

```dockerfile
# Dockerfile.optimized
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Build stage
FROM base as builder

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base as development

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install development dependencies
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy source code
COPY . .

# Development server
CMD ["python", "main.py", "--reload", "--debug"]

# Production stage
FROM base as production

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Create non-root user
RUN groupadd -r nexus && useradd -r -g nexus nexus

# Copy application code (exclude development files)
COPY --chown=nexus:nexus nexus/ ./nexus/
COPY --chown=nexus:nexus config/ ./config/
COPY --chown=nexus:nexus main.py .
COPY --chown=nexus:nexus pyproject.toml .

# Create directories
RUN mkdir -p /app/logs /app/data /app/plugins && \
    chown -R nexus:nexus /app

USER nexus

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["python", "main.py"]
```

## ⚙️ Configuration

### Environment Variables

```bash
# .env file
# Database Configuration
DATABASE_URL=postgresql://nexus:password@postgres:5432/nexus
DATABASE_POOL_SIZE=20
DATABASE_TIMEOUT=30

# Redis Configuration
REDIS_URL=redis://redis:6379/0
REDIS_POOL_SIZE=10

# Application Configuration
LOG_LEVEL=INFO
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-secret-key-here

# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Security Configuration
ALLOWED_HOSTS=localhost,yourdomain.com
CORS_ORIGINS=https://yourdomain.com

# Plugin Configuration
PLUGINS_DIR=/app/plugins
PLUGIN_AUTO_LOAD=true

# Monitoring Configuration
METRICS_ENABLED=true
HEALTH_CHECK_PATH=/api/v1/health

# External Services
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### Volume Mounts

```yaml
services:
  nexus:
    volumes:
      # Configuration (read-only)
      - ./config:/app/config:ro

      # Plugins (read-write)
      - ./plugins:/app/plugins:rw

      # Logs (write-only)
      - ./logs:/app/logs:rw

      # Data persistence
      - nexus_data:/app/data:rw

      # Temporary files
      - /tmp:/tmp:rw

      # SSL certificates (read-only)
      - ./ssl:/app/ssl:ro
```

## 🔒 Security Configuration

### Secure Compose File

```yaml
# docker-compose.security.yml
version: "3.8"

services:
  nexus:
    image: nexus/platform:latest
    user: "1000:1000" # Non-root user
    read_only: true # Read-only filesystem
    tmpfs:
      - /tmp
      - /app/logs
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
    security_opt:
      - no-new-privileges:true
    environment:
      - DATABASE_URL_FILE=/run/secrets/db_url
      - REDIS_URL_FILE=/run/secrets/redis_url
    secrets:
      - db_url
      - redis_url
      - jwt_secret
    networks:
      - backend
      - frontend

  postgres:
    image: postgres:15-alpine
    user: "999:999"
    read_only: true
    tmpfs:
      - /tmp
      - /var/run/postgresql
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - DAC_OVERRIDE
      - FOWNER
      - SETGID
      - SETUID
    security_opt:
      - no-new-privileges:true
    environment:
      - POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password
    secrets:
      - postgres_password
    networks:
      - backend

secrets:
  db_url:
    file: ./secrets/database_url.txt
  redis_url:
    file: ./secrets/redis_url.txt
  jwt_secret:
    file: ./secrets/jwt_secret.txt
  postgres_password:
    file: ./secrets/postgres_password.txt

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true
```

### Nginx Configuration

```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream nexus_backend {
        server nexus:8000;
        keepalive 32;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    server {
        listen 80;
        server_name localhost;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name localhost;

        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;

        # Compression
        gzip on;
        gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

        # API endpoints
        location /api/ {
            limit_req zone=api burst=20 nodelay;

            proxy_pass http://nexus_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Timeouts
            proxy_connect_timeout 5s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Authentication endpoints (stricter rate limiting)
        location /api/v1/auth/ {
            limit_req zone=login burst=5 nodelay;

            proxy_pass http://nexus_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Health check (no rate limiting)
        location /api/v1/health {
            proxy_pass http://nexus_backend;
            access_log off;
        }

        # Static files (if any)
        location /static/ {
            alias /app/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

## 📊 Monitoring Setup

### Monitoring Stack

```yaml
# docker-compose.monitoring.yml
version: "3.8"

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: nexus-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--web.console.libraries=/etc/prometheus/console_libraries"
      - "--web.console.templates=/etc/prometheus/consoles"
      - "--storage.tsdb.retention.time=200h"
      - "--web.enable-lifecycle"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: nexus-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources:ro
    restart: unless-stopped

  loki:
    image: grafana/loki:latest
    container_name: nexus-loki
    ports:
      - "3100:3100"
    volumes:
      - ./monitoring/loki.yml:/etc/loki/local-config.yaml:ro
      - loki_data:/loki
    command: -config.file=/etc/loki/local-config.yaml
    restart: unless-stopped

  promtail:
    image: grafana/promtail:latest
    container_name: nexus-promtail
    volumes:
      - ./logs:/var/log/nexus:ro
      - ./monitoring/promtail.yml:/etc/promtail/config.yml:ro
      - /var/log:/var/log:ro
    command: -config.file=/etc/promtail/config.yml
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
  loki_data:
```

### Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "nexus_rules.yml"

scrape_configs:
  - job_name: "nexus"
    static_configs:
      - targets: ["nexus:8000"]
    metrics_path: "/api/v1/metrics"
    scrape_interval: 10s

  - job_name: "postgres"
    static_configs:
      - targets: ["postgres-exporter:9187"]

  - job_name: "redis"
    static_configs:
      - targets: ["redis-exporter:9121"]

  - job_name: "node"
    static_configs:
      - targets: ["node-exporter:9100"]

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093
```

## 🚀 Deployment Scripts

### Deployment Script

```bash
#!/bin/bash
# deploy.sh

set -e

# Configuration
IMAGE_NAME="nexus/platform"
TAG="${1:-latest}"
COMPOSE_FILE="docker-compose.yml"
BACKUP_DIR="./backups"

echo "🚀 Starting Nexus deployment..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup current database
echo "📦 Creating database backup..."
docker-compose exec -T postgres pg_dump -U nexus nexus > "$BACKUP_DIR/backup-$(date +%Y%m%d_%H%M%S).sql"

# Pull latest images
echo "📥 Pulling latest images..."
docker-compose pull

# Build application image
echo "🔨 Building application image..."
docker build -t "$IMAGE_NAME:$TAG" .

# Stop and remove old containers
echo "🛑 Stopping old containers..."
docker-compose down --remove-orphans

# Start new containers
echo "▶️ Starting new containers..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
timeout=300
counter=0

while [ $counter -lt $timeout ]; do
    if docker-compose ps | grep -q "Up (healthy)"; then
        echo "✅ Services are healthy!"
        break
    fi

    sleep 10
    counter=$((counter + 10))
    echo "Waiting... ($counter/$timeout seconds)"
done

if [ $counter -ge $timeout ]; then
    echo "❌ Services failed to become healthy within $timeout seconds"
    exit 1
fi

# Run database migrations
echo "📊 Running database migrations..."
docker-compose exec nexus python -m alembic upgrade head

# Verify deployment
echo "🔍 Verifying deployment..."
if curl -f http://localhost:8000/api/v1/health; then
    echo "✅ Deployment successful!"
else
    echo "❌ Health check failed!"
    exit 1
fi

# Cleanup old images
echo "🧹 Cleaning up old images..."
docker image prune -f

echo "🎉 Deployment completed successfully!"
```

### Rollback Script

```bash
#!/bin/bash
# rollback.sh

set -e

BACKUP_FILE="${1:-latest}"
COMPOSE_FILE="docker-compose.yml"

echo "🔄 Starting rollback process..."

if [ "$BACKUP_FILE" = "latest" ]; then
    BACKUP_FILE=$(ls -t ./backups/backup-*.sql | head -n1)
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "📦 Using backup file: $BACKUP_FILE"

# Stop current containers
echo "🛑 Stopping current containers..."
docker-compose down

# Restore database
echo "🗄️ Restoring database..."
docker-compose up -d postgres redis
sleep 10

# Wait for PostgreSQL to be ready
docker-compose exec postgres pg_isready -U nexus

# Drop and recreate database
docker-compose exec postgres psql -U nexus -c "DROP DATABASE IF EXISTS nexus;"
docker-compose exec postgres psql -U nexus -c "CREATE DATABASE nexus;"

# Restore from backup
docker-compose exec -T postgres psql -U nexus nexus < "$BACKUP_FILE"

# Start all services
echo "▶️ Starting all services..."
docker-compose up -d

# Verify rollback
echo "🔍 Verifying rollback..."
if curl -f http://localhost:8000/api/v1/health; then
    echo "✅ Rollback successful!"
else
    echo "❌ Rollback verification failed!"
    exit 1
fi

echo "🎉 Rollback completed successfully!"
```

## 🧪 Testing

### Health Check Script

```bash
#!/bin/bash
# health_check.sh

echo "🔍 Running comprehensive health checks..."

# Test database connectivity
echo "Testing database..."
if docker-compose exec postgres pg_isready -U nexus; then
    echo "✅ Database is healthy"
else
    echo "❌ Database is not responding"
    exit 1
fi

# Test Redis connectivity
echo "Testing Redis..."
if docker-compose exec redis redis-cli ping | grep -q PONG; then
    echo "✅ Redis is healthy"
else
    echo "❌ Redis is not responding"
    exit 1
fi

# Test application health
echo "Testing application..."
if curl -f http://localhost:8000/api/v1/health; then
    echo "✅ Application is healthy"
else
    echo "❌ Application is not responding"
    exit 1
fi

# Test API endpoints
echo "Testing API endpoints..."
if curl -f http://localhost:8000/api/v1/status; then
    echo "✅ API endpoints are working"
else
    echo "❌ API endpoints are not responding"
    exit 1
fi

echo "🎉 All health checks passed!"
```

### Load Testing

```bash
#!/bin/bash
# load_test.sh

echo "🚀 Starting load test..."

# Install hey if not present
if ! command -v hey &> /dev/null; then
    echo "Installing hey..."
    go install github.com/rakyll/hey@latest
fi

# Basic load test
echo "Running basic load test..."
hey -n 1000 -c 10 http://localhost:8000/api/v1/health

# API endpoint load test
echo "Running API load test..."
hey -n 500 -c 5 http://localhost:8000/api/v1/status

echo "✅ Load test completed!"
```

## 🔧 Troubleshooting

### Common Issues

```bash
# Check container logs
docker-compose logs nexus
docker-compose logs postgres
docker-compose logs redis

# Check container status
docker-compose ps

# Restart specific service
docker-compose restart nexus

# Rebuild and restart
docker-compose up --build -d

# Check resource usage
docker stats

# Enter container for debugging
docker-compose exec nexus bash

# Check network connectivity
docker-compose exec nexus ping postgres
docker-compose exec nexus ping redis

# Database troubleshooting
docker-compose exec postgres psql -U nexus -d nexus -c "SELECT version();"

# Redis troubleshooting
docker-compose exec redis redis-cli info
```

### Debug Mode

```yaml
# docker-compose.debug.yml
version: "3.8"

services:
  nexus:
    image: nexus/platform:development
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
      - RELOAD=true
    volumes:
      - .:/app
    ports:
      - "8000:8000"
      - "5678:5678" # Debugger port
```

## 📚 Best Practices

### 1. Image Optimization

- Use multi-stage builds
- Minimize layer count
- Use specific base image versions
- Remove unnecessary packages

### 2. Security

- Run as non-root user
- Use read-only filesystems
- Limit container capabilities
- Use secrets for sensitive data

### 3. Resource Management

- Set memory and CPU limits
- Use health checks
- Configure restart policies
- Monitor resource usage

### 4. Data Persistence

- Use named volumes for data
- Regular database backups
- Test restore procedures
- Monitor disk usage

### 5. Networking

- Use custom networks
- Limit exposed ports
- Configure proper firewalls
- Use reverse proxy

## 🎯 Next Steps

- **[Kubernetes Deployment](kubernetes.md)** - Scale with Kubernetes
- **[Cloud Deployment](cloud.md)** - Deploy to cloud platforms
- **[Monitoring Setup](monitoring.md)** - Complete monitoring stack
- **[Security Guide](../architecture/security.md)** - Secure your deployment

---

**Docker deployment provides the foundation for consistent, scalable Nexus deployments.** Follow this guide to get your Nexus instance running reliably in any environment.
