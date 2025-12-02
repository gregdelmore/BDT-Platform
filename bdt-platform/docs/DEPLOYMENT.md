# BDT Platform - Phase 5: Production Deployment Guide

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Local Development Setup](#local-development-setup)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Configuration](#configuration)
7. [Testing](#testing)
8. [Monitoring](#monitoring)
9. [Troubleshooting](#troubleshooting)
10. [Production Checklist](#production-checklist)

---

## Overview

Phase 5 integrates all previous phases into a production-ready platform with:
- **API Gateway** (Kong) for routing and rate limiting
- **Security Service** with OAuth, RBAC, and encryption
- **Monitoring Service** with Prometheus, Grafana, and Jaeger
- **Orchestration Service** coordinating all components
- **Load Balancing** with Nginx
- **Container Orchestration** with Kubernetes
- **CI/CD Pipeline** with GitHub Actions

## Prerequisites

### Required Software
```bash
# Development Tools
- Git 2.30+
- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+
- Node.js 18+
- kubectl 1.25+

# Optional (for production)
- Kubernetes cluster (1.25+)
- Helm 3.10+
- Terraform 1.3+
```

### Cloud Resources (Production)
- Kubernetes cluster (EKS, GKE, or AKS)
- PostgreSQL database (RDS or Cloud SQL)
- Redis cluster (ElastiCache or Cloud Memorystore)
- Object storage (S3, GCS, or Azure Blob)
- SSL certificates
- Domain name

## Local Development Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-org/bdt-platform.git
cd bdt-platform
```

### 2. Create Environment Configuration
```bash
cp .env.example .env
# Edit .env with your credentials
nano .env
```

### 3. Install Python Dependencies
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r phase5-integration/requirements.txt
```

### 4. Initialize Database
```bash
# Start PostgreSQL
docker-compose up -d postgres

# Run initialization script
docker exec -i bdt-postgres psql -U bdt < scripts/init_db.sql

# Run migrations
python scripts/migrate.py
```

### 5. Start Services Individually (for development)
```bash
# Terminal 1: Orchestration Service
cd phase5-integration/orchestration
python orchestration_service.py

# Terminal 2: Security Service
cd phase5-integration/security
python security_service.py

# Terminal 3: Monitoring Service
cd phase5-integration/monitoring
python monitoring_service.py
```

## Docker Deployment

### 1. Build All Images
```bash
# Build all services
docker-compose build

# Or build individually
docker-compose build orchestration-service
docker-compose build security-service
docker-compose build monitoring-service
```

### 2. Start All Services
```bash
# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### 3. Initialize Services
```bash
# Initialize database
docker-compose exec postgres psql -U bdt -f /docker-entrypoint-initdb.d/init.sql

# Create admin user
docker-compose exec orchestration-service python scripts/create_admin.py

# Load sample data (optional)
docker-compose exec orchestration-service python scripts/load_sample_data.py
```

### 4. Access Services
- **Frontend**: http://localhost:3000
- **API Gateway**: http://localhost:8080
- **API Documentation**: http://localhost:8000/docs
- **Grafana Dashboard**: http://localhost:3001 (admin/admin123)
- **Prometheus**: http://localhost:9091
- **Jaeger Tracing**: http://localhost:16686
- **RabbitMQ Management**: http://localhost:15672 (bdt/bdt123)
- **Flower (Celery)**: http://localhost:5555

## Kubernetes Deployment

### 1. Setup Kubernetes Cluster

#### For EKS (AWS)
```bash
eksctl create cluster \
  --name bdt-cluster \
  --version 1.28 \
  --region us-east-1 \
  --nodegroup-name workers \
  --node-type t3.large \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 5 \
  --managed
```

#### For GKE (Google Cloud)
```bash
gcloud container clusters create bdt-cluster \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-2 \
  --enable-autoscaling \
  --min-nodes 2 \
  --max-nodes 5
```

### 2. Install Required Components
```bash
# Install NGINX Ingress Controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml

# Install cert-manager for SSL
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.12.0/cert-manager.yaml

# Install metrics-server for HPA
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### 3. Create Namespace and Secrets
```bash
# Create namespace
kubectl create namespace bdt-platform

# Create secrets from .env file
kubectl create secret generic bdt-secrets \
  --from-env-file=.env \
  -n bdt-platform

# Create Docker registry secret (if using private registry)
kubectl create secret docker-registry regcred \
  --docker-server=your-registry.com \
  --docker-username=your-username \
  --docker-password=your-password \
  --docker-email=your-email \
  -n bdt-platform
```

### 4. Deploy Application
```bash
# Apply all manifests
kubectl apply -f kubernetes/

# Or deploy individually
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secrets.yaml
kubectl apply -f kubernetes/postgres.yaml
kubectl apply -f kubernetes/redis.yaml
kubectl apply -f kubernetes/services.yaml
kubectl apply -f kubernetes/deployments.yaml
kubectl apply -f kubernetes/ingress.yaml

# Check deployment status
kubectl get all -n bdt-platform

# Watch pods
kubectl get pods -n bdt-platform -w
```

### 5. Setup SSL Certificate
```bash
# Create Let's Encrypt issuer
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

### 6. Configure DNS
Point your domain to the Ingress Controller's external IP:
```bash
# Get external IP
kubectl get service -n ingress-nginx

# Update DNS records
# A record: app.bdt.example.com -> EXTERNAL_IP
# A record: api.bdt.example.com -> EXTERNAL_IP
```

## Configuration

### Microsoft 365 OAuth Setup

1. **Register Application in Azure AD**
   - Go to [Azure Portal](https://portal.azure.com)
   - Navigate to Azure Active Directory > App registrations
   - Click "New registration"
   - Name: "BDT Platform"
   - Redirect URI: `https://api.bdt.example.com/api/v1/auth/microsoft/callback`

2. **Configure API Permissions**
   - Add Microsoft Graph permissions:
     - User.Read
     - Mail.Read
     - Calendars.Read
     - Files.Read.All
     - Sites.Read.All
     - Chat.Read
     - ChannelMessage.Read.All

3. **Create Client Secret**
   - Go to Certificates & secrets
   - New client secret
   - Copy the secret value to `.env`

### OpenAI Configuration

1. **Get API Key**
   - Sign up at [OpenAI](https://openai.com)
   - Go to API Keys section
   - Create new secret key
   - Add to `.env` as `OPENAI_API_KEY`

2. **Configure Models**
   ```env
   OPENAI_MODEL=gpt-4-turbo-preview
   OPENAI_EMBEDDING_MODEL=text-embedding-3-large
   ```

### Database Configuration

1. **Production Database Setup**
   ```sql
   -- Create production database
   CREATE DATABASE bdt_production;
   
   -- Create read replica user
   CREATE USER bdt_read WITH PASSWORD 'secure_password';
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO bdt_read;
   
   -- Enable extensions
   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
   CREATE EXTENSION IF NOT EXISTS "pgcrypto";
   CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
   ```

2. **Connection Pooling**
   ```env
   DATABASE_URL=postgresql+asyncpg://bdt:password@pgbouncer:6432/bdt_poc?pool_size=20&max_overflow=40
   ```

## Testing

### Unit Tests
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=phase5-integration tests/

# Run specific test file
pytest tests/test_orchestration.py
```

### Integration Tests
```bash
# Run integration tests
pytest tests/integration/ --integration

# Test API endpoints
python tests/test_api.py
```

### Load Testing
```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load_test.py --host=http://localhost:8000
```

### Security Testing
```bash
# Run security scan
docker run --rm -v $(pwd):/zap/wrk/:rw \
  -t owasp/zap2docker-stable zap-baseline.py \
  -t http://localhost:8000 -r security_report.html
```

## Monitoring

### Grafana Dashboards

1. **Access Grafana**
   ```
   URL: http://localhost:3001
   Username: admin
   Password: admin123
   ```

2. **Import Dashboards**
   - Go to Create > Import
   - Upload JSON files from `monitoring/grafana/dashboards/`

3. **Available Dashboards**
   - System Overview
   - Service Health
   - API Performance
   - Fourth Ontology Analytics
   - User Activity
   - Error Tracking

### Prometheus Alerts

1. **Configure Alertmanager**
   ```yaml
   # alertmanager.yml
   global:
     smtp_smarthost: 'smtp.gmail.com:587'
     smtp_from: 'alerts@bdt.example.com'
     smtp_auth_username: 'your-email@gmail.com'
     smtp_auth_password: 'your-app-password'
   
   route:
     receiver: 'email-notifications'
   
   receivers:
   - name: 'email-notifications'
     email_configs:
     - to: 'team@example.com'
   ```

2. **Alert Rules**
   - High CPU usage (>80%)
   - High memory usage (>80%)
   - Service down
   - High error rate (>5%)
   - Slow response time (>2s)

### Distributed Tracing

1. **Access Jaeger UI**
   ```
   URL: http://localhost:16686
   ```

2. **View Traces**
   - Select service from dropdown
   - Set time range
   - Click "Find Traces"

3. **Analyze Performance**
   - Identify slow operations
   - Find bottlenecks
   - Track cross-service calls

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed
```bash
# Check PostgreSQL status
docker-compose ps postgres

# View logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres psql -U bdt -c "SELECT 1"
```

#### 2. Service Not Starting
```bash
# Check logs
docker-compose logs [service-name]

# Restart service
docker-compose restart [service-name]

# Rebuild and restart
docker-compose up -d --build [service-name]
```

#### 3. Out of Memory
```bash
# Increase Docker memory
# Docker Desktop > Preferences > Resources > Memory: 8GB

# Or adjust in docker-compose.yml
services:
  processing-service:
    mem_limit: 4g
```

#### 4. Port Already in Use
```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 [PID]

# Or change port in .env
```

### Debugging

#### Enable Debug Mode
```env
DEBUG=true
LOG_LEVEL=DEBUG
```

#### Interactive Shell
```bash
# Python shell with app context
docker-compose exec orchestration-service python
>>> from orchestration_service import app, db
>>> # Debug here
```

#### Database Queries
```bash
# Connect to database
docker-compose exec postgres psql -U bdt -d bdt_poc

# Show slow queries
SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;
```

## Production Checklist

### Security
- [ ] Change all default passwords
- [ ] Enable SSL/TLS everywhere
- [ ] Configure firewall rules
- [ ] Enable audit logging
- [ ] Set up intrusion detection
- [ ] Implement rate limiting
- [ ] Enable CORS properly
- [ ] Rotate secrets regularly

### Performance
- [ ] Enable caching (Redis)
- [ ] Configure CDN for static assets
- [ ] Enable gzip compression
- [ ] Optimize database indexes
- [ ] Set up connection pooling
- [ ] Configure auto-scaling
- [ ] Enable query optimization

### Reliability
- [ ] Set up automated backups
- [ ] Configure disaster recovery
- [ ] Implement health checks
- [ ] Set up monitoring alerts
- [ ] Configure log aggregation
- [ ] Test failover procedures
- [ ] Document runbooks

### Compliance
- [ ] Enable encryption at rest
- [ ] Enable encryption in transit
- [ ] Configure data retention policies
- [ ] Implement GDPR compliance
- [ ] Set up audit trails
- [ ] Document data flows
- [ ] Perform security audit

### Deployment
- [ ] Set up CI/CD pipeline
- [ ] Configure staging environment
- [ ] Implement blue-green deployment
- [ ] Set up rollback procedures
- [ ] Configure feature flags
- [ ] Document deployment process
- [ ] Train operations team

## Support

### Documentation
- API Documentation: `/docs`
- Architecture Guide: `docs/architecture.md`
- Security Guide: `docs/security.md`
- Operations Manual: `docs/operations.md`

### Getting Help
- GitHub Issues: https://github.com/your-org/bdt-platform/issues
- Email: support@airiam.com
- Slack: #bdt-platform

### Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

---

## Quick Commands Reference

```bash
# Start everything
docker-compose up -d

# Stop everything
docker-compose down

# View logs
docker-compose logs -f [service]

# Restart service
docker-compose restart [service]

# Run migrations
docker-compose exec orchestration-service python manage.py migrate

# Create superuser
docker-compose exec orchestration-service python manage.py createsuperuser

# Backup database
docker-compose exec postgres pg_dump -U bdt bdt_poc > backup.sql

# Restore database
docker-compose exec -T postgres psql -U bdt bdt_poc < backup.sql

# Scale service
docker-compose up -d --scale processing-service=3

# Update service
docker-compose pull [service]
docker-compose up -d [service]
```

---

*Last Updated: November 2024*
*Version: 5.0.0*
