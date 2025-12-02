# 🚀 START HERE - BDT Platform

Welcome to your consolidated BDT Platform! This is the complete, production-ready system merged from all 5 development sessions.

## ⚡ Quick Start (5 minutes)

### Option 1: Automatic Setup (Recommended)
```bash
chmod +x setup.sh
./setup.sh
```
This will install everything and start all services automatically.

### Option 2: Docker Only
```bash
docker-compose up -d
```
Then visit http://localhost:3000

## 📁 What's In This Package

```
bdt-platform/
├── backend/          → Python backend (FastAPI, AI agents, Fourth Ontology)
├── frontend/         → React UI (dashboards, HILT controls, monitoring)
├── docs/            → All documentation
├── tests/           → Test suites
├── docker-compose.yml → Production setup
├── setup.sh         → One-click setup script
├── .env.example     → Environment template (COPY TO .env!)
└── requirements.txt → Python dependencies
```

## 🔑 First Steps

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Add your API keys to .env:**
   - `OPENAI_API_KEY` - Required for AI features
   - `MS365_CLIENT_ID` - For Microsoft integration
   - `GOOGLE_CLIENT_ID` - For Google integration

3. **Start the platform:**
   ```bash
   docker-compose up -d
   ```

4. **Access the system:**
   - Frontend: http://localhost:3000
   - API: http://localhost:8000/docs

## 🎯 Key Features You Now Have

### ✅ L1-L4 Capabilities
- **L1**: Q&A with your data (RAG)
- **L2**: Behavioral mimicry 
- **L3**: Guided tasks with approval
- **L4**: Fully autonomous agents

### ✅ Fourth Ontology Framework
Maps behavior across 5 dimensions:
- Decisions
- Power
- Fear  
- Reward
- Meaning

### ✅ Enterprise Integrations
- Microsoft 365 (Email, Teams, OneDrive)
- Google Workspace
- Slack
- Custom data sources

### ✅ Production Infrastructure
- Docker & Kubernetes ready
- CI/CD pipelines
- Monitoring & logging
- Security scanning

## 📊 Architecture Overview

```
User → React Frontend → FastAPI Backend → AI Engines
                              ↓
                     PostgreSQL + Redis + Vector DB
                              ↓
                     MS365/Google/Slack APIs
```

## 🧪 Testing Your Setup

1. **Check if services are running:**
   ```bash
   docker-compose ps
   ```

2. **Run the test suite:**
   ```bash
   pytest
   ```

3. **Check API health:**
   ```bash
   curl http://localhost:8000/health
   ```

## 📖 Documentation

- **[README.md](README.md)** - Complete platform overview
- **[CHANGELOG.md](CHANGELOG.md)** - What came from each session
- **[docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md)** - Technical architecture
- **[docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)** - Production deployment
- **[docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)** - Developer reference

## 🛠️ Development Mode

For active development with hot-reload:

**Backend:**
```bash
source venv/bin/activate
uvicorn backend.api.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm run dev
```

## 🐛 Troubleshooting

### Port Already in Use?
```bash
docker-compose down
# Then check what's using the ports:
lsof -i :3000  # Frontend
lsof -i :8000  # Backend
```

### Database Connection Failed?
```bash
# Restart PostgreSQL
docker-compose restart postgres
# Run migrations
python scripts/migrate.py
```

### Import Errors?
The consolidation merged code from 5 sessions. If you see import errors:
1. Check the import path matches the new structure
2. Ensure all `__init__.py` files are present
3. Update relative imports to absolute

## 💡 Pro Tips

1. **Use the Fourth Ontology Visualizer** at http://localhost:3000/ontology to see behavioral mappings

2. **Monitor agents in real-time** at http://localhost:3000/monitoring

3. **Test HILT workflows** at http://localhost:3000/agent with approval controls

4. **Check API documentation** at http://localhost:8000/docs for all endpoints

## 🚢 Ready for Production?

See [docs/PRODUCTION_CHECKLIST.md](docs/PRODUCTION_CHECKLIST.md) for deployment steps.

## 🆘 Need Help?

1. Check the comprehensive [README.md](README.md)
2. Review the [CHANGELOG.md](CHANGELOG.md) to understand the evolution
3. Look at test files for usage examples
4. API docs at http://localhost:8000/docs

---

**You're all set!** Your BDT Platform is the complete system evolved through 5 development sessions, now consolidated and production-ready.

Start with `./setup.sh` and you'll have everything running in minutes! 🎉
