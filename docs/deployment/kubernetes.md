# Kubernetes Deployment

This guide covers deploying Nexus on Kubernetes clusters using various deployment strategies and configurations.

## Overview

Nexus can be deployed on Kubernetes using Helm charts, raw manifests, or operators. This documentation provides comprehensive guidance for production-ready deployments.

## Prerequisites

- Kubernetes cluster (v1.20+)
- kubectl configured to access your cluster
- Helm 3.x (for Helm deployments)
- Persistent storage provisioner
- Load balancer or ingress controller

## Quick Start with Helm

### Add Nexus Helm Repository

```bash
helm repo add nexus https://charts.nexus.io
helm repo update
```

### Install Nexus

```bash
helm install nexus nexus/nexus \
  --namespace nexus-system \
  --create-namespace \
  --set image.tag=latest \
  --set persistence.enabled=true \
  --set persistence.size=10Gi
```

## Configuration

### Values File

Create a `values.yaml` file for customization:

```yaml
# Nexus configuration
image:
  repository: nexus/nexus
  tag: "v1.0.0"
  pullPolicy: IfNotPresent

# Service configuration
service:
  type: ClusterIP
  port: 8080
  targetPort: 8080

# Ingress configuration
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: nexus.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: nexus-tls
      hosts:
        - nexus.example.com

# Database configuration
database:
  type: postgresql
  host: postgres.database.svc.cluster.local
  port: 5432
  name: nexus
  username: nexus
  passwordSecret: nexus-db-secret

# Redis configuration
redis:
  enabled: true
  host: redis.cache.svc.cluster.local
  port: 6379
  passwordSecret: redis-secret

# Persistence
persistence:
  enabled: true
  storageClass: fast-ssd
  size: 20Gi
  accessMode: ReadWriteOnce

# Resource limits
resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 500m
    memory: 1Gi

# Autoscaling
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

# Security context
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 2000
```

### Install with Custom Values

```bash
helm install nexus nexus/nexus \
  --namespace nexus-system \
  --create-namespace \
  --values values.yaml
```

## Manual Deployment

### Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: nexus-system
  labels:
    app.kubernetes.io/name: nexus
```

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: nexus-config
  namespace: nexus-system
data:
  config.yaml: |
    server:
      host: 0.0.0.0
      port: 8080
    database:
      host: ${DB_HOST}
      port: ${DB_PORT}
      name: ${DB_NAME}
      username: ${DB_USERNAME}
      password: ${DB_PASSWORD}
    redis:
      host: ${REDIS_HOST}
      port: ${REDIS_PORT}
      password: ${REDIS_PASSWORD}
    logging:
      level: info
      format: json
```

### Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: nexus-secrets
  namespace: nexus-system
type: Opaque
stringData:
  db-password: "your-database-password"
  redis-password: "your-redis-password"
  jwt-secret: "your-jwt-secret"
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nexus
  namespace: nexus-system
  labels:
    app.kubernetes.io/name: nexus
    app.kubernetes.io/version: "1.0.0"
spec:
  replicas: 3
  selector:
    matchLabels:
      app.kubernetes.io/name: nexus
  template:
    metadata:
      labels:
        app.kubernetes.io/name: nexus
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 2000
      containers:
      - name: nexus
        image: nexus/nexus:v1.0.0
        imagePullPolicy: IfNotPresent
        ports:
        - name: http
          containerPort: 8080
          protocol: TCP
        env:
        - name: DB_HOST
          value: "postgres.database.svc.cluster.local"
        - name: DB_PORT
          value: "5432"
        - name: DB_NAME
          value: "nexus"
        - name: DB_USERNAME
          value: "nexus"
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: nexus-secrets
              key: db-password
        - name: REDIS_HOST
          value: "redis.cache.svc.cluster.local"
        - name: REDIS_PORT
          value: "6379"
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: nexus-secrets
              key: redis-password
        livenessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          limits:
            cpu: 2000m
            memory: 4Gi
          requests:
            cpu: 500m
            memory: 1Gi
        volumeMounts:
        - name: config
          mountPath: /app/config
        - name: data
          mountPath: /app/data
      volumes:
      - name: config
        configMap:
          name: nexus-config
      - name: data
        persistentVolumeClaim:
          claimName: nexus-data
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nexus
  namespace: nexus-system
  labels:
    app.kubernetes.io/name: nexus
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: http
    protocol: TCP
    name: http
  selector:
    app.kubernetes.io/name: nexus
```

### Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: nexus
  namespace: nexus-system
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
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
            name: nexus
            port:
              number: 80
```

### Persistent Volume Claim

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: nexus-data
  namespace: nexus-system
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: fast-ssd
  resources:
    requests:
      storage: 20Gi
```

## High Availability Setup

### Multi-Zone Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nexus
spec:
  replicas: 6
  template:
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app.kubernetes.io/name
                  operator: In
                  values:
                  - nexus
              topologyKey: kubernetes.io/hostname
          - weight: 50
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app.kubernetes.io/name
                  operator: In
                  values:
                  - nexus
              topologyKey: topology.kubernetes.io/zone
```

### HorizontalPodAutoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: nexus-hpa
  namespace: nexus-system
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

## Monitoring and Observability

### ServiceMonitor for Prometheus

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: nexus
  namespace: nexus-system
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: nexus
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

### Grafana Dashboard

Deploy monitoring dashboards:

```bash
kubectl apply -f https://raw.githubusercontent.com/nexus/nexus/main/deploy/k8s/monitoring/grafana-dashboard.yaml
```

## Security

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: nexus-network-policy
  namespace: nexus-system
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: nexus
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: database
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - namespaceSelector:
        matchLabels:
          name: cache
    ports:
    - protocol: TCP
      port: 6379
```

### Pod Security Standards

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: nexus-system
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

## Backup and Disaster Recovery

### Database Backup Job

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: nexus-db-backup
  namespace: nexus-system
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            image: postgres:15
            command:
            - /bin/bash
            - -c
            - |
              pg_dump -h $DB_HOST -U $DB_USERNAME -d $DB_NAME | \
              gzip > /backup/nexus-$(date +%Y%m%d-%H%M%S).sql.gz
            env:
            - name: DB_HOST
              value: postgres.database.svc.cluster.local
            - name: DB_USERNAME
              value: nexus
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: nexus-secrets
                  key: db-password
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

## Troubleshooting

### Common Issues

#### Pod Startup Issues

```bash
# Check pod status
kubectl get pods -n nexus-system

# View pod logs
kubectl logs -n nexus-system deployment/nexus

# Describe pod for events
kubectl describe pod -n nexus-system <pod-name>
```

#### Database Connection Issues

```bash
# Test database connectivity
kubectl run -it --rm debug --image=postgres:15 --restart=Never -- \
  psql -h postgres.database.svc.cluster.local -U nexus -d nexus
```

#### Performance Issues

```bash
# Check resource usage
kubectl top pods -n nexus-system

# Check HPA status
kubectl get hpa -n nexus-system
```

## Upgrading

### Rolling Update

```bash
# Update image tag
helm upgrade nexus nexus/nexus \
  --namespace nexus-system \
  --set image.tag=v1.1.0 \
  --reuse-values
```

### Blue-Green Deployment

```bash
# Deploy new version
helm install nexus-green nexus/nexus \
  --namespace nexus-system \
  --set image.tag=v1.1.0 \
  --set service.name=nexus-green

# Switch traffic
kubectl patch ingress nexus -n nexus-system \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/rules/0/http/paths/0/backend/service/name", "value": "nexus-green"}]'
```

## See Also

- [Docker Deployment](docker.md)
- [Cloud Deployment](cloud.md)
- [Monitoring Setup](monitoring.md)
- [Security Configuration](../architecture/security.md)
