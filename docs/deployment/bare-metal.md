# Bare Metal Deployment

This guide covers deploying Nexus on bare metal servers, providing complete control over the infrastructure and optimal performance for high-throughput applications.

## Overview

Bare metal deployment offers the highest performance and control but requires more operational overhead. This approach is ideal for organizations with specific compliance requirements, latency-sensitive applications, or those wanting to maximize resource utilization.

## Prerequisites

### Hardware Requirements

#### Minimum Requirements
- **CPU**: 4 cores, 2.4 GHz
- **Memory**: 8 GB RAM
- **Storage**: 100 GB SSD
- **Network**: 1 Gbps Ethernet

#### Recommended Requirements
- **CPU**: 16 cores, 3.0 GHz
- **Memory**: 32 GB RAM
- **Storage**: 500 GB NVMe SSD
- **Network**: 10 Gbps Ethernet

#### High Availability Setup
- **Load Balancer**: 2 servers (active/passive)
- **Application Servers**: 3+ servers
- **Database Servers**: 3 servers (primary + 2 replicas)
- **Storage**: Shared storage or distributed filesystem

### Software Requirements

- **Operating System**: Ubuntu 20.04 LTS / CentOS 8 / RHEL 8
- **Container Runtime**: Docker 20.10+ or Podman 3.0+
- **Orchestration**: Kubernetes 1.20+ or Docker Swarm
- **Database**: PostgreSQL 13+ or MongoDB 5.0+
- **Cache**: Redis 6.0+
- **Load Balancer**: HAProxy 2.4+ or NGINX 1.20+

## Server Preparation

### Operating System Setup

#### Ubuntu 20.04 LTS

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y curl wget git unzip htop iotop nethogs

# Configure firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8080/tcp

# Disable swap for Kubernetes
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab
```

#### CentOS 8 / RHEL 8

```bash
# Update system
sudo dnf update -y

# Install essential packages
sudo dnf install -y curl wget git unzip htop iotop

# Configure firewall
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload

# Disable SELinux (for Kubernetes)
sudo setenforce 0
sudo sed -i 's/^SELINUX=enforcing$/SELINUX=permissive/' /etc/selinux/config
```

### Docker Installation

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Enable and start Docker
sudo systemctl enable docker
sudo systemctl start docker

# Configure Docker daemon
sudo mkdir -p /etc/docker
cat <<EOF | sudo tee /etc/docker/daemon.json
{
  "exec-opts": ["native.cgroupdriver=systemd"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m"
  },
  "storage-driver": "overlay2"
}
EOF

sudo systemctl restart docker
```

## Single Server Deployment

### Docker Compose Setup

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  nexus:
    image: nexus/nexus:latest
    container_name: nexus
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - NODE_ENV=production
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=nexus
      - DB_USERNAME=nexus
      - DB_PASSWORD=${DB_PASSWORD}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    volumes:
      - nexus_data:/app/data
      - nexus_logs:/app/logs
      - ./config:/app/config:ro
    depends_on:
      - postgres
      - redis
    networks:
      - nexus_network

  postgres:
    image: postgres:15
    container_name: nexus_postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=nexus
      - POSTGRES_USER=nexus
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    ports:
      - "5432:5432"
    networks:
      - nexus_network

  redis:
    image: redis:7-alpine
    container_name: nexus_redis
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - nexus_network

  nginx:
    image: nginx:alpine
    container_name: nexus_nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - nginx_logs:/var/log/nginx
    depends_on:
      - nexus
    networks:
      - nexus_network

volumes:
  nexus_data:
  nexus_logs:
  postgres_data:
  redis_data:
  nginx_logs:

networks:
  nexus_network:
    driver: bridge
```

### Environment Configuration

Create a `.env` file:

```bash
# Database configuration
DB_PASSWORD=your_secure_database_password_here

# Redis configuration
REDIS_PASSWORD=your_secure_redis_password_here

# Application configuration
NEXUS_SECRET_KEY=your_application_secret_key_here
JWT_SECRET=your_jwt_secret_key_here

# External services
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=nexus@example.com
SMTP_PASSWORD=your_smtp_password_here
```

### NGINX Configuration

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream nexus_backend {
        server nexus:8080;
    }

    server {
        listen 80;
        server_name nexus.example.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name nexus.example.com;

        ssl_certificate /etc/nginx/ssl/nexus.crt;
        ssl_certificate_key /etc/nginx/ssl/nexus.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;

        client_max_body_size 100M;

        location / {
            proxy_pass http://nexus_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /health {
            proxy_pass http://nexus_backend/health;
            access_log off;
        }
    }
}
```

### Start the Stack

```bash
# Create necessary directories
mkdir -p config ssl backups

# Generate SSL certificates (self-signed for testing)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/nexus.key \
  -out ssl/nexus.crt \
  -subj "/C=US/ST=CA/L=San Francisco/O=Nexus/CN=nexus.example.com"

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

## High Availability Deployment

### Multi-Server Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   Load Balancer │
│    (HAProxy)    │    │    (HAProxy)    │
│   Primary       │    │   Backup        │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          └──────────┬───────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
┌────────▼────────┐    ┌─────────▼────────┐    ┌─────────────────┐
│  Application    │    │  Application     │    │  Application    │
│  Server 1       │    │  Server 2        │    │  Server 3       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────┬───────────┴───────────┬───────────┘
                     │                       │
         ┌───────────▼───────────┐    ┌──────▼──────────────┐
         │  Database Cluster     │    │  Redis Cluster      │
         │  (PostgreSQL)         │    │                     │
         └───────────────────────┘    └─────────────────────┘
```

### HAProxy Load Balancer Setup

#### Install HAProxy

```bash
# Ubuntu/Debian
sudo apt install -y haproxy

# CentOS/RHEL
sudo dnf install -y haproxy
```

#### Configure HAProxy

Edit `/etc/haproxy/haproxy.cfg`:

```haproxy
global
    log 127.0.0.1:514 local0
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin
    stats timeout 30s
    user haproxy
    group haproxy
    daemon

defaults
    mode http
    log global
    option httplog
    option dontlognull
    option log-health-checks
    timeout connect 5000
    timeout client 50000
    timeout server 50000
    errorfile 400 /etc/haproxy/errors/400.http
    errorfile 403 /etc/haproxy/errors/403.http
    errorfile 408 /etc/haproxy/errors/408.http
    errorfile 500 /etc/haproxy/errors/500.http
    errorfile 502 /etc/haproxy/errors/502.http
    errorfile 503 /etc/haproxy/errors/503.http
    errorfile 504 /etc/haproxy/errors/504.http

frontend nexus_frontend
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/nexus.pem
    redirect scheme https if !{ ssl_fc }
    default_backend nexus_servers

backend nexus_servers
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200
    server app1 10.0.1.10:8080 check
    server app2 10.0.1.11:8080 check
    server app3 10.0.1.12:8080 check

listen stats
    bind *:8404
    stats enable
    stats uri /stats
    stats refresh 30s
    stats admin if TRUE
```

### Database Cluster Setup

#### PostgreSQL with Streaming Replication

##### Primary Server Configuration

```bash
# Install PostgreSQL
sudo apt install -y postgresql-15 postgresql-contrib-15

# Configure PostgreSQL
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'secure_password';"
sudo -u postgres createuser -s nexus
sudo -u postgres createdb nexus -O nexus

# Edit postgresql.conf
sudo nano /etc/postgresql/15/main/postgresql.conf
```

Add to `postgresql.conf`:

```
listen_addresses = '*'
wal_level = replica
max_wal_senders = 3
max_replication_slots = 3
synchronous_commit = on
synchronous_standby_names = 'standby1,standby2'
```

Edit `pg_hba.conf`:

```
# Replication connections
host replication nexus 10.0.1.0/24 md5
host all nexus 10.0.1.0/24 md5
```

##### Replica Server Configuration

```bash
# Stop PostgreSQL
sudo systemctl stop postgresql

# Remove existing data
sudo rm -rf /var/lib/postgresql/15/main/*

# Create base backup
sudo -u postgres pg_basebackup -h 10.0.1.20 -D /var/lib/postgresql/15/main -U nexus -v -P -W

# Create standby.signal
sudo -u postgres touch /var/lib/postgresql/15/main/standby.signal

# Configure recovery
echo "primary_conninfo = 'host=10.0.1.20 port=5432 user=nexus password=secure_password'" | sudo -u postgres tee /var/lib/postgresql/15/main/postgresql.auto.conf

# Start PostgreSQL
sudo systemctl start postgresql
```

### Redis Cluster Setup

#### Redis Cluster Configuration

Create `redis.conf` for each node:

```
port 7000
cluster-enabled yes
cluster-config-file nodes.conf
cluster-node-timeout 5000
appendonly yes
```

#### Start Redis Cluster

```bash
# Start Redis instances on each server
redis-server /etc/redis/redis.conf

# Create cluster
redis-cli --cluster create \
  10.0.1.10:7000 10.0.1.11:7000 10.0.1.12:7000 \
  10.0.1.13:7000 10.0.1.14:7000 10.0.1.15:7000 \
  --cluster-replicas 1
```

## Monitoring and Logging

### System Monitoring with Prometheus

#### Install Prometheus

```bash
# Create prometheus user
sudo useradd --no-create-home --shell /bin/false prometheus

# Download and install
wget https://github.com/prometheus/prometheus/releases/download/v2.40.0/prometheus-2.40.0.linux-amd64.tar.gz
tar xzf prometheus-2.40.0.linux-amd64.tar.gz
sudo cp prometheus-2.40.0.linux-amd64/prometheus /usr/local/bin/
sudo cp prometheus-2.40.0.linux-amd64/promtool /usr/local/bin/
sudo chown prometheus:prometheus /usr/local/bin/prometheus
sudo chown prometheus:prometheus /usr/local/bin/promtool

# Create directories
sudo mkdir /etc/prometheus
sudo mkdir /var/lib/prometheus
sudo chown prometheus:prometheus /etc/prometheus
sudo chown prometheus:prometheus /var/lib/prometheus
```

#### Configure Prometheus

Create `/etc/prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'nexus'
    static_configs:
      - targets: ['10.0.1.10:8080', '10.0.1.11:8080', '10.0.1.12:8080']

  - job_name: 'node'
    static_configs:
      - targets: ['10.0.1.10:9100', '10.0.1.11:9100', '10.0.1.12:9100']

  - job_name: 'postgres'
    static_configs:
      - targets: ['10.0.1.20:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['10.0.1.30:9121']
```

### Log Management with ELK Stack

#### Elasticsearch Installation

```bash
# Install Java
sudo apt install -y openjdk-11-jdk

# Add Elasticsearch repository
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
echo "deb https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list

# Install Elasticsearch
sudo apt update
sudo apt install -y elasticsearch

# Configure Elasticsearch
sudo nano /etc/elasticsearch/elasticsearch.yml
```

Add to `elasticsearch.yml`:

```yaml
cluster.name: nexus-logs
node.name: node-1
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: 0.0.0.0
http.port: 9200
discovery.type: single-node
```

## Backup and Disaster Recovery

### Database Backup Strategy

#### Automated Backup Script

Create `/opt/scripts/backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="nexus"
DB_USER="nexus"

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -h localhost -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/nexus_db_$DATE.sql.gz

# Redis backup
redis-cli --rdb $BACKUP_DIR/redis_$DATE.rdb

# Application data backup
tar -czf $BACKUP_DIR/nexus_data_$DATE.tar.gz /opt/nexus/data

# Clean old backups (keep 7 days)
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +7 -delete

echo "Backup completed: $DATE"
```

#### Schedule Backups

```bash
# Add to crontab
crontab -e

# Add this line for daily backups at 2 AM
0 2 * * * /opt/scripts/backup.sh >> /var/log/backup.log 2>&1
```

### Disaster Recovery Procedures

#### Database Recovery

```bash
# Stop application
docker-compose stop nexus

# Restore database
gunzip -c /backups/nexus_db_20240101_020000.sql.gz | psql -h localhost -U nexus nexus

# Restore Redis
redis-cli --rdb /backups/redis_20240101_020000.rdb

# Restore application data
tar -xzf /backups/nexus_data_20240101_020000.tar.gz -C /

# Start application
docker-compose start nexus
```

## Security Hardening

### Firewall Configuration

```bash
# Install and configure UFW
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow ssh

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow application ports (from specific networks)
sudo ufw allow from 10.0.1.0/24 to any port 8080
sudo ufw allow from 10.0.1.0/24 to any port 5432
sudo ufw allow from 10.0.1.0/24 to any port 6379

# Enable firewall
sudo ufw enable
```

### SSL/TLS Configuration

#### Generate Production Certificates

```bash
# Install Certbot
sudo apt install -y certbot

# Generate Let's Encrypt certificate
sudo certbot certonly --standalone -d nexus.example.com

# Configure automatic renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

### System Hardening

```bash
# Disable root login
sudo passwd -l root

# Configure SSH
sudo nano /etc/ssh/sshd_config
```

SSH configuration:

```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
Protocol 2
ClientAliveInterval 300
ClientAliveCountMax 2
```

## Performance Optimization

### System Tuning

#### Kernel Parameters

Add to `/etc/sysctl.conf`:

```
# Network performance
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 12582912 16777216
net.ipv4.tcp_wmem = 4096 12582912 16777216

# File descriptor limits
fs.file-max = 2097152

# Virtual memory
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
```

#### Application Limits

Add to `/etc/security/limits.conf`:

```
nexus soft nofile 65536
nexus hard nofile 65536
nexus soft nproc 4096
nexus hard nproc 4096
```

### Database Optimization

#### PostgreSQL Tuning

Add to `postgresql.conf`:

```
# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# Checkpoint settings
checkpoint_completion_target = 0.9
wal_buffers = 16MB

# Query planner
random_page_cost = 1.1
effective_io_concurrency = 200
```

## Troubleshooting

### Common Issues

#### High CPU Usage

```bash
# Check top processes
htop

# Check Docker container resources
docker stats

# Check database queries
sudo -u postgres psql nexus -c "SELECT query, state, query_start FROM pg_stat_activity WHERE state = 'active';"
```

#### Memory Issues

```bash
# Check memory usage
free -h

# Check swap usage
swapon -s

# Clear page cache if needed
sudo sysctl vm.drop_caches=3
```

#### Network Issues

```bash
# Check network connections
netstat -tulpn

# Check firewall status
sudo ufw status

# Test connectivity
telnet nexus.example.com 443
```

## See Also

- [Docker Deployment](docker.md)
- [Kubernetes Deployment](kubernetes.md)
- [Monitoring Setup](monitoring.md)
- [Security Configuration](../architecture/security.md)
