# Deployment Guide

Comprehensive deployment options and strategies for the Nexus platform.

## 🎯 Overview

This guide covers various deployment methods for Nexus applications, from development setups to production-ready configurations. Whether you're deploying locally, in the cloud, or on-premises, we have you covered.

## 📋 Table of Contents

| Section                            | Description                | Best For                         |
| ---------------------------------- | -------------------------- | -------------------------------- |
| **[Docker Deployment](docker.md)** | Containerized deployment   | Development, testing, production |
| **[Kubernetes](kubernetes.md)**    | Container orchestration    | Large-scale production           |
| **[Cloud Platforms](cloud.md)**    | Cloud-specific deployments | Managed infrastructure           |
| **[Bare Metal](bare-metal.md)**    | Direct server deployment   | On-premises, custom setups       |
| **[Development](development.md)**  | Local development setup    | Development workflow             |

## 🚀 Quick Start

### Docker (Recommended)

The fastest way to get Nexus running:

```bash
# Clone the repository
git clone https://github.com/dnviti/nexus-platform.git
cd nexus

# Build and run with Docker Compose
docker-compose up -d

# Access the application
curl http://localhost:8000/api/v1/status
```

### Python Virtual Environment

For development and testing:

```bash
# Create virtual environment
python -m venv nexus-env
source nexus-env/bin/activate  # On Windows: nexus-env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run the application
python main.py
```

## 🐳 Docker Deployment

### Single Container

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash nexus
USER nexus

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Start application
CMD ["python", "main.py"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: "3.8"

services:
  nexus:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://nexus:password@postgres:5432/nexus
      - REDIS_URL=redis://redis:6379/0
      - LOG_LEVEL=INFO
    depends_on:
      - postgres
      - redis
    volumes:
      - ./config:/app/config
      - ./plugins:/app/plugins
      - ./logs:/app/logs
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: nexus
      POSTGRES_USER: nexus
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - nexus
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

## ☸️ Kubernetes Deployment

### Basic Deployment

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: nexus
---
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nexus
  namespace: nexus
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nexus
  template:
    metadata:
      labels:
        app: nexus
    spec:
      containers:
        - name: nexus
          image: nexus:latest
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: nexus-secrets
                  key: database-url
            - name: REDIS_URL
              valueFrom:
                configMapKeyRef:
                  name: nexus-config
                  key: redis-url
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /api/v1/health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /api/v1/health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
---
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: nexus-service
  namespace: nexus
spec:
  selector:
    app: nexus
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: ClusterIP
---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: nexus-ingress
  namespace: nexus
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - nexus.yourdomain.com
      secretName: nexus-tls
  rules:
    - host: nexus.yourdomain.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: nexus-service
                port:
                  number: 80
```

### Helm Chart

```yaml
# charts/nexus/Chart.yaml
apiVersion: v2
name: nexus
description: A Helm chart for Nexus Platform
type: application
version: 1.0.0
appVersion: "1.0.0"

# charts/nexus/values.yaml
replicaCount: 3

image:
  repository: nexus
  pullPolicy: IfNotPresent
  tag: "latest"

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: nexus.local
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: nexus-tls
      hosts:
        - nexus.local

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80
  targetMemoryUtilizationPercentage: 80

postgresql:
  enabled: true
  auth:
    database: nexus
    username: nexus
    password: nexus123

redis:
  enabled: true
  auth:
    enabled: false
```

## ☁️ Cloud Deployments

### AWS ECS

```json
{
  "family": "nexus",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "nexus",
      "image": "your-account.dkr.ecr.region.amazonaws.com/nexus:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:nexus/database-url"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/nexus",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:8000/api/v1/health || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

### Google Cloud Run

```yaml
# cloudrun.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: nexus
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "10"
        run.googleapis.com/cpu-throttling: "false"
    spec:
      containerConcurrency: 80
      timeoutSeconds: 300
      containers:
        - image: gcr.io/PROJECT_ID/nexus:latest
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: nexus-secrets
                  key: database-url
          resources:
            limits:
              cpu: "2"
              memory: "2Gi"
          livenessProbe:
            httpGet:
              path: /api/v1/health
            initialDelaySeconds: 60
            periodSeconds: 10
```

### Azure Container Instances

```yaml
# azure-container-group.yaml
apiVersion: 2019-12-01
location: eastus
name: nexus-container-group
properties:
  containers:
    - name: nexus
      properties:
        image: youracr.azurecr.io/nexus:latest
        resources:
          requests:
            cpu: 1.0
            memoryInGb: 1.5
        ports:
          - port: 8000
            protocol: TCP
        environmentVariables:
          - name: LOG_LEVEL
            value: INFO
          - name: DATABASE_URL
            secureValue: postgresql://...
  osType: Linux
  restartPolicy: Always
  ipAddress:
    type: Public
    ports:
      - protocol: tcp
        port: 8000
```

## 🛠️ Production Considerations

### Security

```yaml
# Security checklist
security:
  - Use HTTPS/TLS encryption
  - Enable authentication and authorization
  - Configure firewall rules
  - Use secrets management
  - Enable audit logging
  - Regular security updates
  - Network segmentation
  - Container image scanning
```

### Monitoring

```yaml
# monitoring.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
    - job_name: 'nexus'
      static_configs:
      - targets: ['nexus-service:8000']
      metrics_path: /api/v1/metrics
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
        - name: grafana
          image: grafana/grafana:latest
          ports:
            - containerPort: 3000
          env:
            - name: GF_SECURITY_ADMIN_PASSWORD
              value: admin123
```

### Backup Strategy

```bash
#!/bin/bash
# backup.sh

# Database backup
pg_dump $DATABASE_URL > backups/nexus-$(date +%Y%m%d_%H%M%S).sql

# Configuration backup
tar -czf backups/config-$(date +%Y%m%d_%H%M%S).tar.gz config/

# Plugin backup
tar -czf backups/plugins-$(date +%Y%m%d_%H%M%S).tar.gz plugins/

# Upload to cloud storage
aws s3 cp backups/ s3://nexus-backups/ --recursive

# Cleanup old backups (keep last 30 days)
find backups/ -name "*.sql" -mtime +30 -delete
find backups/ -name "*.tar.gz" -mtime +30 -delete
```

### Scaling

```yaml
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: nexus-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: nexus
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

## 🔧 Environment Configuration

### Development

```yaml
# config/development.yaml
database:
  url: "sqlite:///nexus_dev.db"
  echo: true

server:
  host: "127.0.0.1"
  port: 8000
  debug: true
  reload: true

logging:
  level: "DEBUG"
  format: "detailed"

cache:
  backend: "memory"

plugins:
  auto_reload: true
  development_mode: true
```

### Staging

```yaml
# config/staging.yaml
database:
  url: "${DATABASE_URL}"
  pool_size: 10

server:
  host: "0.0.0.0"
  port: 8000
  workers: 2

logging:
  level: "INFO"
  format: "json"

cache:
  backend: "redis"
  url: "${REDIS_URL}"

monitoring:
  enabled: true
  metrics_port: 9090
```

### Production

```yaml
# config/production.yaml
database:
  url: "${DATABASE_URL}"
  pool_size: 20
  ssl_mode: "require"

server:
  host: "0.0.0.0"
  port: 8000
  workers: 4

logging:
  level: "WARNING"
  format: "json"
  output: "file"

security:
  force_https: true
  session_timeout: 3600

cache:
  backend: "redis"
  url: "${REDIS_URL}"
  cluster_mode: true

monitoring:
  enabled: true
  metrics_port: 9090
  health_checks: true

backup:
  enabled: true
  schedule: "0 2 * * *" # Daily at 2 AM
  retention_days: 30
```

## 📊 Performance Tuning

### Database Optimization

```sql
-- PostgreSQL optimization
-- shared_preload_libraries = 'pg_stat_statements'
-- max_connections = 200
-- shared_buffers = 256MB
-- effective_cache_size = 1GB
-- maintenance_work_mem = 64MB
-- checkpoint_completion_target = 0.9
-- wal_buffers = 16MB
-- default_statistics_target = 100

-- Indexes for common queries
CREATE INDEX CONCURRENTLY idx_events_timestamp ON events(timestamp);
CREATE INDEX CONCURRENTLY idx_events_type ON events(event_type);
CREATE INDEX CONCURRENTLY idx_plugins_status ON plugins(status);
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);

-- Analyze tables
ANALYZE;
```

### Application Tuning

```python
# Performance configuration
import uvloop
import asyncio

# Use uvloop for better performance
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# Optimize connection pools
DATABASE_CONFIG = {
    "pool_size": 20,
    "max_overflow": 30,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "pool_pre_ping": True
}

REDIS_CONFIG = {
    "max_connections": 50,
    "retry_on_timeout": True,
    "health_check_interval": 30
}

# HTTP server optimization
UVICORN_CONFIG = {
    "workers": 4,
    "worker_class": "uvicorn.workers.UvicornWorker",
    "max_requests": 1000,
    "max_requests_jitter": 100,
    "preload_app": True,
    "keepalive": 5
}
```

## 🚨 Troubleshooting

### Common Issues

```bash
# Check application logs
docker logs nexus-app

# Check database connectivity
docker exec nexus-app python -c "from nexus.database import test_connection; test_connection()"

# Check plugin status
curl http://localhost:8000/api/v1/plugins

# Check system health
curl http://localhost:8000/api/v1/health

# Debug mode
export DEBUG=true
docker-compose up
```

### Health Checks

```python
# health_check.py
import aiohttp
import asyncio
import sys

async def health_check():
    """Comprehensive health check."""
    checks = []

    # HTTP health check
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/api/v1/health') as resp:
                if resp.status == 200:
                    checks.append(("HTTP", "OK"))
                else:
                    checks.append(("HTTP", f"FAIL ({resp.status})"))
    except Exception as e:
        checks.append(("HTTP", f"FAIL ({e})"))

    # Database check
    try:
        from nexus.database import get_database
        db = get_database()
        await db.execute("SELECT 1")
        checks.append(("Database", "OK"))
    except Exception as e:
        checks.append(("Database", f"FAIL ({e})"))

    # Print results
    for check, status in checks:
        print(f"{check}: {status}")

    # Exit with error if any check failed
    if any("FAIL" in status for _, status in checks):
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(health_check())
```

## 📚 Additional Resources

- **[Docker Documentation](docker.md)** - Detailed Docker deployment guide
- **[Kubernetes Guide](kubernetes.md)** - Complete Kubernetes setup
- **[Cloud Deployments](cloud.md)** - Platform-specific guides
- **[Security Guide](../architecture/security.md)** - Production security
- **[Monitoring Setup](monitoring.md)** - Observability and monitoring

## 🆘 Support

### Getting Help

- **Documentation**: Check deployment-specific guides
- **Community**: Join our deployment discussions
- **Issues**: Report deployment problems on GitHub
- **Professional Support**: Available for enterprise customers

### Deployment Checklist

```markdown
## Pre-deployment Checklist

- [ ] Environment configuration reviewed
- [ ] Database migrations applied
- [ ] SSL certificates configured
- [ ] Security settings verified
- [ ] Monitoring setup completed
- [ ] Backup strategy implemented
- [ ] Load testing completed
- [ ] Rollback plan documented
- [ ] Team training completed
- [ ] Documentation updated
```

---

**Ready to deploy Nexus?** Choose your deployment method and follow the detailed guides for a successful production deployment.
