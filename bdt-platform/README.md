# Behavioral Digital Twin (BDT) Platform

## Overview

Production-ready implementation of the Behavioral Digital Twin platform featuring:
- **Fourth Ontology Framework**: Maps human behavior across 5 dimensions
- **L1-L4 Capability Levels**: From basic Q&A to fully autonomous agents
- **Multi-Persona Support**: Individual and team behavioral analysis
- **Enterprise Integration**: Microsoft 365, Google Workspace, Slack
- **Production Infrastructure**: Kubernetes, monitoring, CI/CD

## Architecture

### Capability Levels
| Level | Name | Description | Status |
|-------|------|-------------|--------|
| L1 | Basic Q&A | RAG-based retrieval from indexed data | ✅ Complete |
| L2 | Behavioral Mimic | Responds using learned communication patterns | ✅ Complete |
| L3 | Guided Twin | Task execution with human oversight (HILT) | ✅ Complete |
| L4 | Delegated Agent | Autonomous operation within learned boundaries | ✅ Complete |

### Fourth Ontology Dimensions
- **Decisions**: Analysis depth, data requirements, approval patterns
- **Power**: Autonomy boundaries, escalation triggers, delegation comfort
- **Fear**: Risk tolerance, safety requirements, verification needs
- **Reward**: Motivation patterns, achievement metrics, feedback preferences
- **Meaning**: Value alignments, priority frameworks, significance thresholds

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

### Using Docker Compose

```bash
# Development environment
docker-compose -f docker-compose.dev.yml up -d

# Production environment
docker-compose up -d
```

### Manual Setup

1. **Install dependencies:**
```bash
# Backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Initialize database:**
```bash
python scripts/migrate.py
```

4. **Start services:**
```bash
# Backend API
uvicorn backend.api.main:app --reload --port 8000

# Frontend (in separate terminal)
cd frontend
npm run dev
```

5. **Access the platform:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Project Structure

```
bdt-platform/
├── backend/           # Core backend services
│   ├── agents/        # L4 autonomous agents
│   ├── api/           # FastAPI REST/WebSocket API
│   ├── core/          # Core engines (ontology, HILT, decisions)
│   ├── ingestion/     # Data connectors and processing
│   ├── memory/        # Vector store and RAG
│   ├── services/      # Business logic services
│   └── twin_engine/   # Behavioral twin implementation
├── frontend/          # React/Next.js UI
├── monitoring/        # Prometheus, Grafana configs
├── kubernetes/        # K8s deployment manifests
├── docs/              # Documentation
└── tests/             # Test suites
```

## Key Features

### Data Integration
- Microsoft 365 (Outlook, Teams, OneDrive, SharePoint)
- Google Workspace (Gmail, Drive, Calendar)
- Slack
- Local/Network file systems

### Behavioral Analysis
- Communication pattern extraction
- Decision-making approach mapping
- Problem-solving strategy identification
- Tool and resource proficiency assessment
- Work rhythm and temporal pattern analysis

### Safety & Control
- Negative Space boundaries (what NOT to do)
- Human-in-the-Loop (HILT) approval workflows
- Risk assessment and escalation logic
- Comprehensive audit logging

## Documentation

- [Implementation Guide](docs/IMPLEMENTATION_GUIDE.md) - Architecture details
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) - Production deployment
- [Quick Reference](docs/QUICK_REFERENCE.md) - Developer guide
- [Production Checklist](docs/PRODUCTION_CHECKLIST.md) - Pre-deployment checklist

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Load testing
locust -f tests/locustfile.py
```

## Deployment

### Kubernetes
```bash
kubectl apply -f kubernetes/
```

### Docker Swarm
```bash
docker stack deploy -c docker-compose.yml bdt
```

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Proprietary - Airiam Technologies

## Support

For support, please contact the BDT development team.

---
*Version: 5.0.0 | Consolidated from 5 development sessions*
