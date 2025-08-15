# Nexus Framework Deployment Guide

## Table of Contents
- [Overview](#overview)
- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Deployment Strategies](#deployment-strategies)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Cloud Platform Deployment](#cloud-platform-deployment)
- [Production Configuration](#production-configuration)
- [Scaling Strategies](#scaling-strategies)
- [Load Balancing](#load-balancing)
- [Database Deployment](#database-deployment)
- [Caching and Performance](#caching-and-performance)
- [Monitoring and Logging](#monitoring-and-logging)
- [Security Hardening](#security-hardening)
- [CI/CD Pipeline](#cicd-pipeline)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Overview

This guide provides comprehensive instructions for deploying Nexus Framework applications in various environments, from development to production scale deployments.

### Deployment Options

1. **Standalone Server** - Single server deployment for small applications
2. **Docker Containers** - Containerized deployment for consistency
3. **Kubernetes** - Orchestrated deployment for scale
4. **Cloud Platforms** - Managed services on AWS, GCP, Azure
5. **Hybrid Cloud** - Mix of on-premise and cloud resources

## Pre-Deployment Checklist

### System Requirements

```yaml
# Minimum Requirements
cpu: 2 cores
memory: 4GB RAM
storage: 20GB SSD
os: Ubuntu 20.04+ / Debian 10+ / RHEL 8+ / Alpine 3.14+

# Recommended Production Requirements
cpu: 8+ cores
memory: 16GB+ RAM
storage: 100GB+ SSD
network: 1Gbps+
```

### Software Dependencies

```bash
# Core Dependencies
Python 3.11+
PostgreSQL 14+ / MongoDB 5+ / MySQL 8+
Redis 6+
Nginx / Apache
Supervisor / systemd

# Optional Dependencies
Docker 20.10+
Kubernetes 1.24+
Prometheus
Grafana
ElasticSearch
```

### Pre-Deployment Tasks

- [ ] Review and update configuration files
- [ ] Set up environment variables
- [ ] Configure database connections
- [ ] Set up SSL certificates
- [ ] Configure firewall rules
- [ ] Set up monitoring and alerting
- [ ] Create backup strategy
- [ ] Prepare rollback plan
- [ ] Load test the application
- [ ] Security audit

## Deployment Strategies

### Blue-Green Deployment

```yaml
# docker-compose.blue-green.yml
version: '3.8'

services:
  nexus-blue:
    image: nexus-app:${BLUE_VERSION}
    ports:
      - "8001:8000"
    environment:
      - DEPLOYMENT=blue
    networks:
      - nexus-network

  nexus-green:
    image: nexus-app:${GREEN_VERSION}
    ports:
      - "8002:8000"
    environment:
      - DEPLOYMENT=green
    networks:
      - nexus-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/blue-green.conf:/etc/nginx/conf.d/default.conf
    networks:
      - nexus-network

networks:
  nexus-network:
    driver: bridge
```

### Rolling Deployment

```bash
#!/bin/bash
# rolling-deploy.sh

SERVERS=("server1" "server2" "server3" "server4")
NEW_VERSION=$1

for server in "${SERVERS[@]}"; do
    echo "Deploying to $server..."
    
    # Remove from load balancer
    ./remove-from-lb.sh $server
    
    # Deploy new version
    ssh $server "cd /app && git pull && docker-compose up -d"
    
    # Health check
    ./health-check.sh $server
    
    # Add back to load balancer
    ./add-to-lb.sh $server
    
    # Wait before next server
    sleep 30
done
```

### Canary Deployment

```yaml
# kubernetes-canary.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nexus-canary
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nexus
      version: canary
  template:
    metadata:
      labels:
        app: nexus
        version: canary
    spec:
      containers:
      - name: nexus
        image: nexus-app:2.0.0-canary
        ports:
        - containerPort: 8000

---
apiVersion: v1
kind: Service
metadata:
  name: nexus-service
spec:
  selector:
    app: nexus
  ports:
  - port: 80
    targetPort: 8000
  sessionAffinity: ClientIP
```

## Docker Deployment

### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 nexus && \
    mkdir -p /app /data /logs && \
    chown -R nexus:nexus /app /data /logs

# Copy from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Set working directory
WORKDIR /app

# Copy application
COPY --chown=nexus:nexus . .

# Switch to non-root user
USER nexus

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  nexus:
    build:
      context: .
      dockerfile: Dockerfile
    image: nexus-app:latest
    container_name: nexus-app
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - NEXUS_APP_ENVIRONMENT=production
      - NEXUS_DATABASE_HOST=postgres
      - NEXUS_CACHE_HOST=redis
    volumes:
      - ./config:/app/config:ro
      - ./plugins:/app/plugins:ro
      - nexus-data:/data
      - nexus-logs:/logs
    depends_on:
      - postgres
      - redis
    networks:
      - nexus-network

  postgres:
    image: postgres:14-alpine
    container_name: nexus-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=nexus_db
      - POSTGRES_USER=nexus_user
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      - nexus-network

  redis:
    image: redis:7-alpine
    container_name: nexus-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data
    networks:
      - nexus-network

  nginx:
    image: nginx:alpine
    container_name: nexus-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./static:/usr/share/nginx/html/static:ro
    depends_on:
      - nexus
    networks:
      - nexus-network

volumes:
  nexus-data:
  nexus-logs:
  postgres-data:
  redis-data:

networks:
  nexus-network:
    driver: bridge
```

### Docker Swarm Deployment

```yaml
# docker-stack.yml
version: '3.8'

services:
  nexus:
    image: nexus-app:latest
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      placement:
        constraints:
          - node.role == worker
    ports:
      - "8000:8000"
    environment:
      - NEXUS_APP_ENVIRONMENT=production
    secrets:
      - db_password
      - jwt_secret
    configs:
      - source: nexus_config
        target: /app/config/config.yaml
    networks:
      - nexus-network

secrets:
  db_password:
    external: true
  jwt_secret:
    external: true

configs:
  nexus_config:
    file: ./config.prod.yaml

networks:
  nexus-network:
    driver: overlay
    attachable: true
```

## Kubernetes Deployment

### Kubernetes Manifests

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: nexus-app

---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: nexus-config
  namespace: nexus-app
data:
  config.yaml: |
    app:
      name: "Nexus Application"
      environment: "production"
      debug: false
    database:
      host: "postgres-service"
      port: 5432
    cache:
      host: "redis-service"
      port: 6379

---
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: nexus-secrets
  namespace: nexus-app
type: Opaque
data:
  db-password: <base64-encoded-password>
  jwt-secret: <base64-encoded-secret>

---
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nexus-deployment
  namespace: nexus-app
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
        image: nexus-app:latest
        ports:
        - containerPort: 8000
        env:
        - name: NEXUS_DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: nexus-secrets
              key: db-password
        - name: NEXUS_AUTH_JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: nexus-secrets
              key: jwt-secret
        volumeMounts:
        - name: config
          mountPath: /app/config
        - name: data
          mountPath: /data
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: config
        configMap:
          name: nexus-config
      - name: data
        persistentVolumeClaim:
          claimName: nexus-pvc

---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: nexus-service
  namespace: nexus-app
spec:
  selector:
    app: nexus
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer

---
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: nexus-ingress
  namespace: nexus-app
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - nexus.example.com
    secretName: nexus-tls
  rules:
  - host: nexus.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: nexus-service
            port:
              number: 80

---
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: nexus-hpa
  namespace: nexus-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: nexus-deployment
  minReplicas: 3
  maxReplicas: 10
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

### Helm Chart

```yaml
# helm/nexus/values.yaml
replicaCount: 3

image:
  repository: nexus-app
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
    - host: nexus.example.com
      paths:
        - path: /
          pathType: ImplementationSpecific
  tls:
    - secretName: nexus-tls
      hosts:
        - nexus.example.com

resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 500m
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

postgresql:
  enabled: true
  auth:
    postgresPassword: "changeme"
    database: "nexus_db"
  persistence:
    enabled: true
    size: 10Gi

redis:
  enabled: true
  auth:
    enabled: true
    password: "changeme"
  persistence:
    enabled: true
    size: 5Gi
```

## Cloud Platform Deployment

### AWS Deployment

#### Using Elastic Beanstalk

```yaml
# .ebextensions/01_nexus.config
option_settings:
  aws:elasticbeanstalk:container:python:
    WSGIPath: app.main:app
  aws:elasticbeanstalk:application:environment:
    NEXUS_APP_ENVIRONMENT: production
    NEXUS_DATABASE_HOST: !Ref RDSEndpoint
    NEXUS_CACHE_HOST: !Ref ElastiCacheEndpoint
  aws:autoscaling:launchconfiguration:
    InstanceType: t3.medium
    EC2KeyName: nexus-key
  aws:autoscaling:asg:
    MinSize: 2
    MaxSize: 10
  aws:elasticbeanstalk:healthreporting:system:
    SystemType: enhanced

Resources:
  RDSDatabase:
    Type: AWS::RDS::DBInstance
    Properties:
      DBInstanceIdentifier: nexus-db
      DBName: nexus
      Engine: postgres
      EngineVersion: 14.7
      DBInstanceClass: db.t3.medium
      AllocatedStorage: 100
      StorageEncrypted: true
      MasterUsername: nexus_user
      MasterUserPassword: !Ref DBPassword
      VPCSecurityGroups:
        - !Ref DBSecurityGroup
      DBSubnetGroupName: !Ref DBSubnetGroup
      BackupRetentionPeriod: 7
      PreferredBackupWindow: "03:00-04:00"
      PreferredMaintenanceWindow: "sun:04:00-sun:05:00"
      MultiAZ: true

  ElastiCacheCluster:
    Type: AWS::ElastiCache::CacheCluster
    Properties:
      CacheNodeType: cache.t3.micro
      Engine: redis
      NumCacheNodes: 1
      VpcSecurityGroupIds:
        - !Ref CacheSecurityGroup
      CacheSubnetGroupName: !Ref CacheSubnetGroup
```

#### Using ECS/Fargate

```json
{
  "family": "nexus-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "nexus",
      "image": "nexus-app:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "NEXUS_APP_ENVIRONMENT",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "NEXUS_DATABASE_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:nexus/db-password"
        },
        {
          "name": "NEXUS_AUTH_JWT_SECRET",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:nexus/jwt-secret"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/nexus-app",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

### Google Cloud Platform

```yaml
# app.yaml for App Engine
runtime: python311
env: standard

instance_class: F4

automatic_scaling:
  min_instances: 2
  max_instances: 10
  target_cpu_utilization: 0.7
  target_throughput_utilization: 0.7

env_variables:
  NEXUS_APP_ENVIRONMENT: "production"

vpc_access_connector:
  name: projects/PROJECT_ID/locations/REGION/connectors/nexus-connector

resources:
  cpu: 2
  memory_gb: 4
  disk_size_gb: 20

handlers:
- url: /static
  static_dir: static
  expiration: "30d"

- url: /.*
  script: auto
  secure: always
```

### Azure Deployment

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "appName": {
      "type": "string",
      "defaultValue": "nexus-app"
    }
  },
  "resources": [
    {
      "type": "Microsoft.Web/serverfarms",
      "apiVersion": "2021-02-01",
      "name": "[concat(parameters('appName'), '-plan')]",
      "location": "[resourceGroup().location]",
      "sku": {
        "name": "P1v2",
        "tier": "PremiumV2",
        "size": "P1v2",
        "family": "Pv2",
        "capacity": 2
      },
      "kind": "linux",
      "properties": {
        "reserved": true
      }
    },
    {
      "type": "Microsoft.Web/sites",
      "apiVersion": "2021-02-01",
      "name": "[parameters('appName')]",
      "location": "[resourceGroup().location]",
      "dependsOn": [
        "[resourceId('Microsoft.Web/serverfarms', concat(parameters('appName'), '-plan'))]"
      ],
      "properties": {
        "serverFarmId": "[resourceId('Microsoft.Web/serverfarms', concat(parameters('appName'), '-plan'))]",
        "siteConfig": {
          "linuxFxVersion": "DOCKER|nexus-app:latest",
          "appSettings": [
            {
              "name": "NEXUS_APP_ENVIRONMENT",
              "value": "production"
            },
            {
              "name": "NEXUS_DATABASE_HOST",
              "value": "[reference(resourceId('Microsoft.DBforPostgreSQL/servers', concat(parameters('appName'), '-db'))).fullyQualifiedDomainName]"
            }
          ]
        }
      }
    }
  ]
}
```

## Production Configuration

### Environment Variables

```bash
# .env.production
# Application
NEXUS_APP_NAME=Nexus Production
NEXUS_APP_ENVIRONMENT=production
NEXUS_APP_DEBUG=false
NEXUS_APP_HOST=0.0.0.0
NEXUS_APP_PORT=8000
NEXUS_APP_WORKERS=4

# Database
NEXUS_DATABASE_TYPE=postgresql
NEXUS_DATABASE_HOST=db.production.local
NEXUS_DATABASE_PORT=5432
NEXUS_DATABASE_NAME=nexus_prod
NEXUS_DATABASE_USER=nexus_prod_user
NEXUS_DATABASE_PASSWORD=${SECRET_DB_PASSWORD}
NEXUS_DATABASE_POOL_SIZE=20
NEXUS_DATABASE_MAX_OVERFLOW=10

# Redis Cache
NEXUS_CACHE_TYPE=redis
NEXUS_CACHE_REDIS_HOST=redis.production.local
NEXUS_CACHE_REDIS_PORT=6379
NEXUS_CACHE_REDIS_PASSWORD=${SECRET_REDIS_PASSWORD}
NEXUS_CACHE_REDIS_DB=0
NEXUS_CACHE_REDIS_MAX_CONNECTIONS=50

# Authentication
NEXUS_AUTH_JWT_SECRET=${SECRET_JWT_KEY}
NEXUS_AUTH_JWT_ALGORITHM=HS256
NEXUS_AUTH_TOKEN_EXPIRY=3600
NEXUS_AUTH_REFRESH_TOKEN_EXPIRY=604800

# Security
NEXUS_SECURITY_HTTPS_ENABLED=true
NEXUS_SECURITY_HTTPS_REDIRECT=true
NEXUS_SECURITY_RATE_LIMIT_ENABLED=true
NEXUS_SECURITY_RATE_LIMIT_REQUESTS=1000
NEXUS_SECURITY_RATE_LIMIT_WINDOW=3600

# Monitoring
NEXUS_MONITORING_SENTRY_DSN=${SENTRY_DSN}
NEXUS_MONITORING_SENTRY_ENVIRONMENT=production
NEXUS_MONITORING_PROMETHEUS_ENABLED=true
NEXUS_MONITORING_METRICS_PORT=9090
```

### Nginx Configuration

```nginx
# /etc/nginx/sites-available/nexus
upstream nexus_backend {
    least_conn;
    server 127.0.0.1:8001 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8003 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8004 weight=1 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 80;
    server_name nexus.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name nexus.example.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/nexus.crt;
    ssl_certificate_key /etc/ssl/private/nexus.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self'" always;

    # Logging
    access_log /var/log/nginx/nexus_access.log combined;
    error_log /var/log/nginx/nexus_error.log error;

    # Client Configuration
    client_max_body_size 100M;
    client_body_buffer_size 1M;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 8k;

    # Timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
    send_timeout 60s;

    # Gzip Compression
    gzip on;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/rss+xml application/atom+xml image/svg+xml text/javascript application/vnd.ms-fontobject application/x-font-ttf font/opentype;
    gzip_vary on;
    gzip_disable "msie6";

    # Static Files
    location /static/ {
        alias /var/www/nexus/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /var/www/nexus/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # WebSocket Support
    location /ws/ {
        proxy_pass http://nexus_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API Routes
    location / {
        proxy_pass http://nexus_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_http_version 1.1;
    }

    # Health Check Endpoint
    location /health {
        access_log off;
        proxy_pass http://nexus_backend/health;
    }
}
```

## Scaling Strategies

### Horizontal Scaling

```python
# scaling/horizontal.py
import os
from multiprocessing import cpu_count

# Gunicorn configuration for horizontal scaling
bind = "0.0.0.0:8000"
workers = int(os.environ.get("WORKERS", cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2
threads = 4

# Preload application
preload_app = True

# Process naming
proc_name = "nexus-app"

# Logging
accesslog = "/var/log/nexus/access.log"
errorlog = "/var/log/nexus/error.log"
loglevel = "info"

# StatsD integration
statsd_host = "localhost:8125"
statsd_prefix = "nexus"
```

### Database Connection Pooling

```python
# scaling/database_pool.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
import os

def create_db_engine():
    """Create database engine with connection pooling."""
    return create_engine(
        os.environ.get("DATABASE_URL"),
        poolclass=QueuePool,
        pool_size=20,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
        echo_pool=False,
        connect_args={
            "server_settings": {
                "application_name": "nexus-app",
                "jit": "off"
            },
            "command_timeout": 60,
            "options": "-c statement_timeout=30000"
        }
    )
```

## Monitoring and Logging

### Prometheus Metrics

```python
# monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import FastAPI, Response
import time

# Define metrics
request_count = Counter(
    'nexus_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'nexus_request_duration_seconds',
    'Request duration',
    ['method', 'endpoint']
)

active_connections = Gauge(
    'nexus_active_connections',
    'Active connections'
)

plugin_count = Gauge(
    'nexus_plugins_loaded',
    'Number of loaded plugins'
)

def setup_metrics(app: FastAPI):
    """Setup Prometheus metrics."""
    
    @app.middleware("http")
    async def track_metrics(request, call_next):
        start_time = time.time()
        
        # Track active connections
        active_connections.inc()