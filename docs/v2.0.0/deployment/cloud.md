# Cloud Deployment

This guide covers deploying Nexus on major cloud platforms including AWS, Google Cloud Platform (GCP), and Microsoft Azure.

## Overview

Nexus can be deployed on cloud platforms using various services and deployment strategies. This documentation provides platform-specific guidance for production-ready cloud deployments.

## AWS Deployment

### EKS (Elastic Kubernetes Service)

#### Prerequisites

- AWS CLI configured
- eksctl installed
- kubectl installed
- Helm 3.x

#### Create EKS Cluster

```bash
# Create cluster
eksctl create cluster \
  --name nexus-cluster \
  --region us-west-2 \
  --nodegroup-name nexus-nodes \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 10 \
  --managed

# Update kubeconfig
aws eks update-kubeconfig --region us-west-2 --name nexus-cluster
```

#### Deploy with Application Load Balancer

```yaml
# values-aws.yaml
ingress:
  enabled: true
  className: alb
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-west-2:123456789012:certificate/12345678-1234-1234-1234-123456789012
  hosts:
    - host: nexus.example.com
      paths:
        - path: /
          pathType: Prefix

# Storage class for EBS
storageClass: gp3

# Database configuration (RDS)
database:
  type: postgresql
  host: nexus-db.cluster-xyz.us-west-2.rds.amazonaws.com
  port: 5432
  name: nexus
  username: nexus
  passwordSecret: nexus-rds-secret

# Redis configuration (ElastiCache)
redis:
  enabled: true
  host: nexus-redis.abc123.0001.usw2.cache.amazonaws.com
  port: 6379
```

#### RDS Database Setup

```bash
# Create RDS PostgreSQL instance
aws rds create-db-cluster \
  --db-cluster-identifier nexus-db-cluster \
  --engine aurora-postgresql \
  --engine-version 14.6 \
  --master-username nexus \
  --master-user-password $(aws secretsmanager get-random-password --password-length 32 --exclude-punctuation --output text --query RandomPassword) \
  --database-name nexus \
  --vpc-security-group-ids sg-12345678 \
  --db-subnet-group-name nexus-db-subnet-group
```

#### ElastiCache Redis Setup

```bash
# Create ElastiCache Redis cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id nexus-redis \
  --engine redis \
  --cache-node-type cache.t3.micro \
  --num-cache-nodes 1 \
  --security-group-ids sg-87654321 \
  --cache-subnet-group-name nexus-cache-subnet-group
```

### ECS (Elastic Container Service)

#### Task Definition

```json
{
  "family": "nexus",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::123456789012:role/nexusTaskRole",
  "containerDefinitions": [
    {
      "name": "nexus",
      "image": "nexus/nexus:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "NODE_ENV",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "DB_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:us-west-2:123456789012:secret:nexus/database-password-abc123"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/nexus",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

## Google Cloud Platform (GCP)

### GKE (Google Kubernetes Engine)

#### Create GKE Cluster

```bash
# Set project and zone
gcloud config set project nexus-project-123456
gcloud config set compute/zone us-central1-a

# Create cluster
gcloud container clusters create nexus-cluster \
  --num-nodes=3 \
  --machine-type=e2-standard-4 \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10 \
  --enable-autorepair \
  --enable-autoupgrade

# Get credentials
gcloud container clusters get-credentials nexus-cluster
```

#### Deploy with Google Load Balancer

```yaml
# values-gcp.yaml
ingress:
  enabled: true
  className: gce
  annotations:
    kubernetes.io/ingress.global-static-ip-name: nexus-ip
    networking.gke.io/managed-certificates: nexus-ssl-cert
    kubernetes.io/ingress.class: gce
  hosts:
    - host: nexus.example.com
      paths:
        - path: /*
          pathType: ImplementationSpecific

# Storage class for Persistent Disks
storageClass: standard-rwo

# Database configuration (Cloud SQL)
database:
  type: postgresql
  host: 127.0.0.1
  port: 5432
  name: nexus
  username: nexus
  passwordSecret: nexus-cloudsql-secret

# Redis configuration (Memorystore)
redis:
  enabled: true
  host: 10.1.2.3
  port: 6379
```

#### Cloud SQL Setup

```bash
# Create Cloud SQL instance
gcloud sql instances create nexus-db \
  --database-version=POSTGRES_14 \
  --tier=db-custom-2-4096 \
  --region=us-central1 \
  --storage-type=SSD \
  --storage-size=100GB

# Create database
gcloud sql databases create nexus --instance=nexus-db

# Create user
gcloud sql users create nexus \
  --instance=nexus-db \
  --password=$(openssl rand -base64 32)
```

#### Memorystore Redis Setup

```bash
# Create Redis instance
gcloud redis instances create nexus-redis \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_6_x
```

### Cloud Run

#### Deploy to Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/nexus-project-123456/nexus

# Deploy to Cloud Run
gcloud run deploy nexus \
  --image gcr.io/nexus-project-123456/nexus \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 100 \
  --set-env-vars NODE_ENV=production \
  --set-secrets DB_PASSWORD=nexus-db-password:latest
```

## Microsoft Azure

### AKS (Azure Kubernetes Service)

#### Create AKS Cluster

```bash
# Create resource group
az group create --name nexus-rg --location eastus

# Create AKS cluster
az aks create \
  --resource-group nexus-rg \
  --name nexus-aks \
  --node-count 3 \
  --node-vm-size Standard_D2s_v3 \
  --enable-cluster-autoscaler \
  --min-count 1 \
  --max-count 10 \
  --generate-ssh-keys

# Get credentials
az aks get-credentials --resource-group nexus-rg --name nexus-aks
```

#### Deploy with Application Gateway

```yaml
# values-azure.yaml
ingress:
  enabled: true
  className: azure/application-gateway
  annotations:
    appgw.ingress.kubernetes.io/ssl-redirect: "true"
    appgw.ingress.kubernetes.io/certificate-name: nexus-cert
  hosts:
    - host: nexus.example.com
      paths:
        - path: /
          pathType: Prefix

# Storage class for Azure Disks
storageClass: managed-premium

# Database configuration (Azure Database for PostgreSQL)
database:
  type: postgresql
  host: nexus-db.postgres.database.azure.com
  port: 5432
  name: nexus
  username: nexus@nexus-db
  passwordSecret: nexus-azure-db-secret

# Redis configuration (Azure Cache for Redis)
redis:
  enabled: true
  host: nexus-cache.redis.cache.windows.net
  port: 6380
  ssl: true
```

#### Azure Database for PostgreSQL

```bash
# Create PostgreSQL server
az postgres server create \
  --resource-group nexus-rg \
  --name nexus-db \
  --location eastus \
  --admin-user nexus \
  --admin-password $(openssl rand -base64 32) \
  --sku-name GP_Gen5_2 \
  --version 11

# Create database
az postgres db create \
  --resource-group nexus-rg \
  --server-name nexus-db \
  --name nexus
```

#### Azure Cache for Redis

```bash
# Create Redis cache
az redis create \
  --resource-group nexus-rg \
  --name nexus-cache \
  --location eastus \
  --sku Standard \
  --vm-size c1
```

### Container Instances

#### Deploy to Azure Container Instances

```bash
# Create container group
az container create \
  --resource-group nexus-rg \
  --name nexus-container \
  --image nexus/nexus:latest \
  --cpu 2 \
  --memory 4 \
  --ports 8080 \
  --dns-name-label nexus-app \
  --environment-variables NODE_ENV=production \
  --secure-environment-variables DB_PASSWORD=$DB_PASSWORD
```

## Multi-Cloud Considerations

### Infrastructure as Code

#### Terraform Example

```hcl
# main.tf
provider "aws" {
  region = var.aws_region
}

provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

provider "azurerm" {
  features {}
}

module "nexus_aws" {
  source = "./modules/aws"

  cluster_name = "nexus-aws"
  region       = var.aws_region
  node_count   = 3
}

module "nexus_gcp" {
  source = "./modules/gcp"

  cluster_name = "nexus-gcp"
  project      = var.gcp_project
  region       = var.gcp_region
  node_count   = 3
}

module "nexus_azure" {
  source = "./modules/azure"

  cluster_name    = "nexus-azure"
  resource_group  = "nexus-rg"
  location        = var.azure_location
  node_count      = 3
}
```

### Disaster Recovery

#### Cross-Region Backup Strategy

```yaml
# Backup configuration
backup:
  enabled: true
  schedule: "0 2 * * *"
  destinations:
    - type: s3
      bucket: nexus-backups-us-west-2
      region: us-west-2
    - type: gcs
      bucket: nexus-backups-us-central1
      region: us-central1
    - type: azure-blob
      account: nexusbackups
      container: backups
      region: East US
```

## Cost Optimization

### Resource Sizing

#### Production Recommendations

```yaml
# Small deployment (< 1000 users)
resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 1000m
    memory: 2Gi

# Medium deployment (1000-10000 users)
resources:
  requests:
    cpu: 1000m
    memory: 2Gi
  limits:
    cpu: 2000m
    memory: 4Gi

# Large deployment (> 10000 users)
resources:
  requests:
    cpu: 2000m
    memory: 4Gi
  limits:
    cpu: 4000m
    memory: 8Gi
```

### Autoscaling Configuration

#### Horizontal Pod Autoscaler

```yaml
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 50
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

## Security Best Practices

### Network Security

- Use private subnets for database and cache services
- Implement network segmentation with security groups/firewall rules
- Enable VPC flow logs for network monitoring
- Use service mesh for encrypted inter-service communication

### Identity and Access Management

- Use cloud-native identity providers (AWS IAM, GCP IAM, Azure AD)
- Implement least-privilege access policies
- Enable audit logging for all API calls
- Use managed secrets services (AWS Secrets Manager, GCP Secret Manager, Azure Key Vault)

### Data Protection

- Enable encryption at rest for all storage services
- Use TLS 1.3 for all communications
- Implement database backup encryption
- Use managed certificate services for TLS certificates

## Monitoring and Observability

### Cloud-Native Monitoring

#### AWS CloudWatch

```yaml
monitoring:
  cloudwatch:
    enabled: true
    namespace: "Nexus/Application"
    metrics:
      - name: RequestCount
        unit: Count
      - name: ResponseTime
        unit: Milliseconds
```

#### GCP Cloud Monitoring

```yaml
monitoring:
  stackdriver:
    enabled: true
    project: nexus-project-123456
    metrics:
      - name: nexus_requests_total
        type: counter
      - name: nexus_response_duration
        type: histogram
```

#### Azure Monitor

```yaml
monitoring:
  azure:
    enabled: true
    workspace: nexus-logs
    metrics:
      - name: RequestsPerSecond
        category: Application
      - name: DatabaseConnections
        category: Database
```

## Troubleshooting

### Common Cloud Issues

#### AWS EKS Issues

```bash
# Check node status
kubectl get nodes

# Check AWS Load Balancer Controller
kubectl logs -n kube-system deployment/aws-load-balancer-controller

# Verify IAM roles
aws sts get-caller-identity
```

#### GCP GKE Issues

```bash
# Check cluster status
gcloud container clusters describe nexus-cluster

# Verify service account permissions
gcloud projects get-iam-policy nexus-project-123456
```

#### Azure AKS Issues

```bash
# Check cluster health
az aks show --resource-group nexus-rg --name nexus-aks

# Verify Azure AD integration
az aks get-credentials --resource-group nexus-rg --name nexus-aks --admin
```

## See Also

- [Kubernetes Deployment](kubernetes.md)
- [Docker Deployment](docker.md)
- [Monitoring Setup](monitoring.md)
- [Security Configuration](../architecture/security.md)
