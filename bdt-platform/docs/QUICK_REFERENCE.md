# 🚀 BDT Platform Quick Reference Card

## Essential Commands

```bash
# First Time Setup
chmod +x setup.sh && ./setup.sh

# Start Platform
./start.sh

# Stop Platform  
./stop.sh

# Access Application
http://localhost:8000

# View Logs
tail -f logs/bdt.log

# Database Access
psql -h localhost -U bdt -d bdt_poc
```

## In-App Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/ingest` | Start data ingestion |
| `/stats` | Show system statistics |
| `/ontology` | View Fourth Ontology dimensions |
| `/patterns` | Show behavioral patterns |
| `/boundaries` | View negative space |
| `/level [L1-L4]` | Set capability level |
| `/filter [type]` | Set data filter |

## Capability Levels

| Level | Name | Description | Risk |
|-------|------|-------------|------|
| **L1** | Basic Q&A | RAG retrieval from data | None |
| **L2** | Behavioral Mimic | Responds in your style | Low |
| **L3** | Guided Twin | Executes with approval | Medium |
| **L4** | Delegated Agent | Autonomous operation | High |

## Fourth Ontology Dimensions

```
Decision ━━━━━━━━━━ 75/100 [Analytical]
Power    ━━━━━━━━━━ 60/100 [Leader]
Fear     ━━━━━━━━━━ 40/100 [Confident]
Reward   ━━━━━━━━━━ 85/100 [Achievement]
Meaning  ━━━━━━━━━━ 70/100 [Purpose-driven]
```

## Architecture Components

```
Frontend (Chainlit)
    ↓
Twin Engine (L1-L4)
    ↓
┌──────────┬──────────┐
│ Vector   │ Database │
│ ChromaDB │ PostgreSQL│
└──────────┴──────────┘
    ↑
Ingestion Engine
    ↑
Microsoft 365 APIs
```

## Key Files Reference

| Component | File | Purpose |
|-----------|------|---------|
| **Ingestion** | `backend/ingestion.py` | M365 data import |
| **Database** | `backend/database.py` | Schema & models |
| **Vectors** | `backend/vector_store.py` | Embeddings |
| **Engine** | `backend/twin_engine.py` | Query processing |
| **Patterns** | `backend/utils/patterns.py` | Behavior extraction |
| **UI** | `frontend/app.py` | Chat interface |

## Environment Variables

```env
# Required
MS_CLIENT_ID=xxx
MS_CLIENT_SECRET=xxx
MS_TENANT_ID=xxx
OPENAI_API_KEY=sk-xxx

# Database
DATABASE_URL=postgresql://bdt:bdt123@localhost:5432/bdt_poc

# Performance
MAX_WORKERS=4
BATCH_SIZE=100
CHUNK_SIZE=500
```

## Microsoft Graph Permissions

- ✅ User.Read
- ✅ Mail.Read
- ✅ Calendars.Read
- ✅ Files.Read.All
- ✅ Sites.Read.All
- ✅ offline_access
- ⚠️ Chat.Read (optional)
- ⚠️ ChannelMessage.Read.All (optional)

## Performance Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Ingestion | 10K docs/hr | ✅ |
| Query | <2 sec | ✅ |
| Patterns | <5 min | ✅ |
| Search | <100ms | ✅ |

## Troubleshooting

```bash
# Check Docker
docker ps
docker-compose logs postgres

# Reset Database
docker-compose down -v
docker-compose up -d
python backend/database.py --init

# Clear Vector Store
rm -rf chroma_db/*

# View Python Logs
tail -f logs/bdt.log

# Test Connection
curl http://localhost:8000
```

## API Endpoints (Internal)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Chat UI |
| `/auth/callback` | GET | OAuth callback |
| `/api/ingest` | POST | Start ingestion |
| `/api/query` | POST | Query twin |
| `/api/stats` | GET | Get statistics |

## Data Flow

```
1. User asks question
   ↓
2. Classify query type
   ↓
3. Apply capability level
   ↓
4. Vector search + RAG
   ↓
5. Apply behavioral style
   ↓
6. Apply Fourth Ontology
   ↓
7. Check boundaries
   ↓
8. Return response
```

## Security Checklist

- [ ] Strong passwords in .env
- [ ] HTTPS in production
- [ ] Rate limiting enabled
- [ ] Audit logging active
- [ ] Data encryption at rest
- [ ] Regular token rotation
- [ ] RBAC implemented
- [ ] PII handling compliant

## Contact & Support

- **Docs**: README.md
- **Issues**: GitHub Issues
- **Email**: support@airiam.com
- **Version**: 1.0.0
- **License**: Proprietary

---

**Remember**: The BDT learns from YOUR data. The more data ingested, the better it mimics your behavior. Start with L2 for safety, progress to L3/L4 as confidence builds.

**Pro Tip**: Use `/filter email` to focus on email patterns, `/filter calendar` for meetings, or `/filter all` for complete context.
