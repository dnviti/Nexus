# Monitoring Setup

This guide covers comprehensive monitoring setup for Nexus deployments, including metrics collection, alerting, logging, and observability best practices.

## Overview

Monitoring is crucial for maintaining the health, performance, and reliability of Nexus deployments. This documentation provides guidance for setting up monitoring across different deployment scenarios using industry-standard tools.

## Monitoring Stack Components

### Core Components

- **Metrics Collection**: Prometheus, InfluxDB, or cloud-native solutions
- **Visualization**: Grafana, Kibana, or cloud dashboards
- **Alerting**: Alertmanager, PagerDuty, or cloud alerting
- **Log Aggregation**: ELK Stack, Fluentd, or cloud logging
- **Distributed Tracing**: Jaeger, Zipkin, or cloud tracing
- **Uptime Monitoring**: Pingdom, UptimeRobot, or synthetic monitoring

## Prometheus Setup

### Installation

#### Docker Deployment

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: nexus-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./rules:/etc/prometheus/rules:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
      - '--web.enable-admin-api'

  alertmanager:
    image: prom/alertmanager:latest
    container_name: nexus-alertmanager
    restart: unless-stopped
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager_data:/alertmanager

  node-exporter:
    image: prom/node-exporter:latest
    container_name: nexus-node-exporter
    restart: unless-stopped
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'

volumes:
  prometheus_data:
  alertmanager_data:
```

### Prometheus Configuration

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: 'nexus-monitor'

rule_files:
  - "rules/*.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'nexus'
    static_configs:
      - targets: ['nexus:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'nginx-exporter'
    static_configs:
      - targets: ['nginx-exporter:9113']
```

### Alert Rules

Create `rules/nexus-alerts.yml`:

```yaml
groups:
  - name: nexus.rules
    rules:
      - alert: NexusDown
        expr: up{job="nexus"} == 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Nexus instance is down"
          description: "Nexus instance {{ $labels.instance }} has been down for more than 0 minutes."

      - alert: NexusHighCPU
        expr: (100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage"
          description: "CPU usage is above 80% for 5 minutes on {{ $labels.instance }}"

      - alert: NexusHighMemory
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High memory usage"
          description: "Memory usage is above 90% for 5 minutes on {{ $labels.instance }}"

      - alert: NexusHighDiskUsage
        expr: (1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High disk usage"
          description: "Disk usage is above 85% on {{ $labels.instance }}"

      - alert: NexusHighErrorRate
        expr: rate(nexus_http_requests_total{status=~"5.."}[5m]) / rate(nexus_http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate"
          description: "Error rate is above 5% for 5 minutes"

      - alert: NexusSlowResponse
        expr: histogram_quantile(0.95, rate(nexus_http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow response times"
          description: "95th percentile response time is above 1 second"

      - alert: DatabaseConnectionHigh
        expr: nexus_db_connections_active / nexus_db_connections_max > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High database connection usage"
          description: "Database connection pool is 80% utilized"

      - alert: RedisMemoryHigh
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Redis memory usage high"
          description: "Redis memory usage is above 90%"
```

## Grafana Setup

### Installation

```yaml
grafana:
  image: grafana/grafana:latest
  container_name: nexus-grafana
  restart: unless-stopped
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin123
    - GF_USERS_ALLOW_SIGN_UP=false
  volumes:
    - grafana_data:/var/lib/grafana
    - ./grafana/provisioning:/etc/grafana/provisioning
    - ./grafana/dashboards:/var/lib/grafana/dashboards

volumes:
  grafana_data:
```

### Dashboard Configuration

Create `grafana/provisioning/dashboards/dashboard.yml`:

```yaml
apiVersion: 1

providers:
  - name: 'nexus-dashboards'
    orgId: 1
    folder: 'Nexus'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
```

Create `grafana/provisioning/datasources/datasource.yml`:

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

### Nexus Dashboard

Create `grafana/dashboards/nexus-overview.json`:

```json
{
  "dashboard": {
    "id": null,
    "title": "Nexus Overview",
    "tags": ["nexus"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Request Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(nexus_http_requests_total[5m])",
            "legendFormat": "Requests/sec"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "reqps"
          }
        }
      },
      {
        "id": 2,
        "title": "Response Time",
        "type": "stat",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(nexus_http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "s"
          }
        }
      },
      {
        "id": 3,
        "title": "Error Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(nexus_http_requests_total{status=~\"5..\"}[5m]) / rate(nexus_http_requests_total[5m]) * 100",
            "legendFormat": "Error %"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent"
          }
        }
      },
      {
        "id": 4,
        "title": "Active Users",
        "type": "stat",
        "targets": [
          {
            "expr": "nexus_active_users",
            "legendFormat": "Active Users"
          }
        ]
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
```

## Application Metrics

### Metrics Implementation

Add to your Nexus application:

```javascript
const promClient = require('prom-client');

// Create metrics registry
const register = new promClient.Registry();

// Default metrics
promClient.collectDefaultMetrics({ register });

// Custom metrics
const httpRequestsTotal = new promClient.Counter({
  name: 'nexus_http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status'],
  registers: [register]
});

const httpRequestDuration = new promClient.Histogram({
  name: 'nexus_http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route'],
  buckets: [0.1, 0.5, 1, 2, 5],
  registers: [register]
});

const activeUsers = new promClient.Gauge({
  name: 'nexus_active_users',
  help: 'Number of active users',
  registers: [register]
});

const dbConnections = new promClient.Gauge({
  name: 'nexus_db_connections_active',
  help: 'Number of active database connections',
  registers: [register]
});

// Middleware for metrics collection
function metricsMiddleware(req, res, next) {
  const start = Date.now();

  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;

    httpRequestsTotal
      .labels(req.method, req.route?.path || req.path, res.statusCode)
      .inc();

    httpRequestDuration
      .labels(req.method, req.route?.path || req.path)
      .observe(duration);
  });

  next();
}

// Metrics endpoint
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});

module.exports = {
  register,
  httpRequestsTotal,
  httpRequestDuration,
  activeUsers,
  dbConnections,
  metricsMiddleware
};
```

## Alerting Setup

### Alertmanager Configuration

Create `alertmanager.yml`:

```yaml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@nexus.example.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    email_configs:
      - to: 'admin@nexus.example.com'
        subject: 'Nexus Alert: {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          {{ end }}

    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#alerts'
        title: 'Nexus Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'dev', 'instance']
```

### PagerDuty Integration

```yaml
receivers:
  - name: 'pagerduty'
    pagerduty_configs:
      - routing_key: 'YOUR_PAGERDUTY_INTEGRATION_KEY'
        description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'
        details:
          summary: '{{ .CommonAnnotations.summary }}'
          description: '{{ .CommonAnnotations.description }}'
          severity: '{{ .CommonLabels.severity }}'
```

## Log Management

### ELK Stack Setup

#### Elasticsearch

```yaml
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
  container_name: nexus-elasticsearch
  environment:
    - discovery.type=single-node
    - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    - xpack.security.enabled=false
  ports:
    - "9200:9200"
  volumes:
    - elasticsearch_data:/usr/share/elasticsearch/data

volumes:
  elasticsearch_data:
```

#### Logstash

```yaml
logstash:
  image: docker.elastic.co/logstash/logstash:8.5.0
  container_name: nexus-logstash
  ports:
    - "5044:5044"
  volumes:
    - ./logstash/pipeline:/usr/share/logstash/pipeline:ro
    - ./logstash/config:/usr/share/logstash/config:ro
  depends_on:
    - elasticsearch
```

Create `logstash/pipeline/nexus.conf`:

```
input {
  beats {
    port => 5044
  }
}

filter {
  if [fields][service] == "nexus" {
    json {
      source => "message"
    }

    date {
      match => [ "timestamp", "ISO8601" ]
    }

    mutate {
      add_tag => [ "nexus" ]
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "nexus-%{+YYYY.MM.dd}"
  }
}
```

#### Kibana

```yaml
kibana:
  image: docker.elastic.co/kibana/kibana:8.5.0
  container_name: nexus-kibana
  ports:
    - "5601:5601"
  environment:
    - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
  depends_on:
    - elasticsearch
```

### Filebeat Configuration

Create `filebeat.yml`:

```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/nexus/*.log
    fields:
      service: nexus
    fields_under_root: true

output.logstash:
  hosts: ["logstash:5044"]

processors:
  - add_host_metadata:
      when.not.contains.tags: forwarded
```

## Application Logging

### Structured Logging

```javascript
const winston = require('winston');

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: {
    service: 'nexus',
    environment: process.env.NODE_ENV
  },
  transports: [
    new winston.transports.File({
      filename: '/var/log/nexus/error.log',
      level: 'error'
    }),
    new winston.transports.File({
      filename: '/var/log/nexus/combined.log'
    })
  ]
});

if (process.env.NODE_ENV !== 'production') {
  logger.add(new winston.transports.Console({
    format: winston.format.simple()
  }));
}

module.exports = logger;
```

### Request Logging Middleware

```javascript
const logger = require('./logger');

function requestLogger(req, res, next) {
  const start = Date.now();

  res.on('finish', () => {
    const duration = Date.now() - start;

    logger.info('HTTP Request', {
      method: req.method,
      url: req.url,
      status: res.statusCode,
      duration,
      userAgent: req.get('User-Agent'),
      ip: req.ip,
      userId: req.user?.id
    });
  });

  next();
}

module.exports = requestLogger;
```

## Distributed Tracing

### Jaeger Setup

```yaml
jaeger:
  image: jaegertracing/all-in-one:latest
  container_name: nexus-jaeger
  ports:
    - "16686:16686"
    - "14268:14268"
  environment:
    - COLLECTOR_OTLP_ENABLED=true
```

### Application Tracing

```javascript
const { NodeTracerProvider } = require('@opentelemetry/sdk-node');
const { JaegerExporter } = require('@opentelemetry/exporter-jaeger');
const { Resource } = require('@opentelemetry/resources');
const { SemanticResourceAttributes } = require('@opentelemetry/semantic-conventions');

const provider = new NodeTracerProvider({
  resource: new Resource({
    [SemanticResourceAttributes.SERVICE_NAME]: 'nexus',
    [SemanticResourceAttributes.SERVICE_VERSION]: '1.0.0',
  }),
});

const jaegerExporter = new JaegerExporter({
  endpoint: 'http://jaeger:14268/api/traces',
});

provider.addSpanProcessor(new BatchSpanProcessor(jaegerExporter));
provider.register();
```

## Health Checks

### Application Health Endpoint

```javascript
const express = require('express');
const app = express();

app.get('/health', (req, res) => {
  const health = {
    status: 'ok',
    timestamp: new Date().toISOString(),
    checks: {
      database: 'ok',
      redis: 'ok',
      external_apis: 'ok'
    }
  };

  res.json(health);
});

app.get('/ready', async (req, res) => {
  try {
    // Check database connection
    await db.raw('SELECT 1');

    // Check Redis connection
    await redis.ping();

    res.json({ status: 'ready' });
  } catch (error) {
    res.status(503).json({
      status: 'not ready',
      error: error.message
    });
  }
});
```

## Cloud Monitoring

### AWS CloudWatch

```javascript
const AWS = require('aws-sdk');
const cloudwatch = new AWS.CloudWatch();

function publishMetric(metricName, value, unit = 'Count') {
  const params = {
    Namespace: 'Nexus/Application',
    MetricData: [
      {
        MetricName: metricName,
        Value: value,
        Unit: unit,
        Timestamp: new Date()
      }
    ]
  };

  cloudwatch.putMetricData(params).promise()
    .catch(err => console.error('CloudWatch error:', err));
}
```

### Google Cloud Monitoring

```javascript
const monitoring = require('@google-cloud/monitoring');
const client = new monitoring.MetricServiceClient();

async function publishMetric(metricType, value) {
  const projectId = process.env.GOOGLE_CLOUD_PROJECT;
  const projectPath = client.projectPath(projectId);

  const dataPoint = {
    interval: {
      endTime: {
        seconds: Date.now() / 1000,
      },
    },
    value: {
      doubleValue: value,
    },
  };

  const timeSeries = {
    metric: {
      type: `custom.googleapis.com/nexus/${metricType}`,
    },
    resource: {
      type: 'global',
    },
    points: [dataPoint],
  };

  const request = {
    name: projectPath,
    timeSeries: [timeSeries],
  };

  await client.createTimeSeries(request);
}
```

## Performance Monitoring

### APM Integration

```javascript
// New Relic
require('newrelic');

// DataDog
const tracer = require('dd-trace').init({
  service: 'nexus',
  env: process.env.NODE_ENV
});

// AppDynamics
require('appdynamics').profile({
  controllerHostName: 'controller.appdynamics.com',
  controllerPort: 443,
  controllerSslEnabled: true,
  accountName: 'your-account',
  accountAccessKey: 'your-access-key',
  applicationName: 'Nexus',
  tierName: 'Web',
  nodeName: process.env.HOSTNAME
});
```

## Monitoring Best Practices

### Metric Guidelines

1. **Use appropriate metric types**:
   - Counters for cumulative values
   - Gauges for point-in-time values
   - Histograms for distributions

2. **Label wisely**:
   - Keep cardinality low
   - Use meaningful label names
   - Avoid user-specific labels

3. **Monitor what matters**:
   - Business metrics
   - Application performance
   - Infrastructure health
   - User experience

### Alert Guidelines

1. **Alert on symptoms, not causes**
2. **Keep alerts actionable**
3. **Avoid alert fatigue**
4. **Use appropriate severities**
5. **Include runbook links**

### Dashboard Guidelines

1. **Focus on key metrics**
2. **Use consistent time ranges**
3. **Include context and annotations**
4. **Organize by audience**
5. **Keep it simple and readable**

## Troubleshooting

### Common Issues

#### High Cardinality Metrics

```bash
# Check metric cardinality
curl -s http://prometheus:9090/api/v1/label/__name__/values | jq '.data[]' | wc -l

# Find high cardinality metrics
promtool query instant 'topk(10, count by (__name__)({__name__=~".+"}))'
```

#### Missing Metrics

```bash
# Check target status
curl -s http://prometheus:9090/api/v1/targets

# Check service discovery
curl -s http://prometheus:9090/api/v1/targets?state=active
```

#### Grafana Dashboard Issues

```bash
# Check Grafana logs
docker logs nexus-grafana

# Test data source connection
curl -H "Authorization: Bearer $API_KEY" \
  http://grafana:3000/api/datasources/proxy/1/api/v1/query?query=up
```

## See Also

- [Kubernetes Deployment](kubernetes.md)
- [Docker Deployment](docker.md)
- [Cloud Deployment](cloud.md)
- [Security Configuration](../architecture/security.md)
