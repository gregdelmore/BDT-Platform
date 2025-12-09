# BDT Platform v2.0 - Deployment Guide

## 🚀 Quick Deployment (20 minutes)

### Prerequisites
- Docker installed locally
- Azure CLI installed and logged in
- Access to Azure Portal
- All files from this package

### Step 1: Prepare Files (2 minutes)

1. Copy all files to your project directory:
```bash
mkdir ~/bdt-platform-v2
cd ~/bdt-platform-v2
# Copy all files here
```

2. Update backend files:
```bash
# Replace existing backend files with new ones
cp backend/main.py backend/main.py.backup
cp backend/graph_service.py backend/
cp backend/tasks.py backend/
cp backend/cache_service.py backend/
cp backend/dashboard_service.py backend/
cp backend/requirements.txt backend/
```

3. Use new Dockerfile:
```bash
mv Dockerfile Dockerfile.old
mv Dockerfile.v2 Dockerfile
```

### Step 2: Build Docker Image (5 minutes)

```bash
# Build the image
docker build -t bdt-platform:v2 .

# Test locally (optional)
docker run -p 80:80 --env-file .env.template bdt-platform:v2
```

### Step 3: Push to Azure Container Registry (3 minutes)

```bash
# Login to ACR
az acr login --name bdtplatformacr

# Tag image
docker tag bdt-platform:v2 bdtplatformacr.azurecr.io/bdt-platform:v2

# Push image
docker push bdtplatformacr.azurecr.io/bdt-platform:v2
```

### Step 4: Update Azure Web App (5 minutes)

1. Go to Azure Portal
2. Navigate to your Web App: `bdt-platform-app`
3. Go to Deployment Center
4. Update the image tag to `v2`
5. Click Save
6. Go to Configuration > Application settings
7. Add these NEW environment variables:

```
REDIS_URL=redis://localhost:6379/0
ENABLE_MICROSOFT_AUTH=true
ENABLE_BACKGROUND_TASKS=true
ENABLE_CACHING=true
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

8. Click Save and restart the app

### Step 5: Verify Deployment (5 minutes)

1. Check health endpoint:
```bash
curl https://bdt-platform-bfc3g7g6eabbf2a4.eastus2-01.azurewebsites.net/health
```

2. Check API documentation:
```
https://bdt-platform-bfc3g7g6eabbf2a4.eastus2-01.azurewebsites.net/api/docs
```

3. Test demo login:
```bash
curl -X POST https://bdt-platform-bfc3g7g6eabbf2a4.eastus2-01.azurewebsites.net/api/auth/demo-login
```

## 📋 Complete Feature Checklist

### ✅ Working Features (Already Deployed)
- [x] FastAPI backend
- [x] ChromaDB vector database
- [x] PostgreSQL database
- [x] JWT authentication
- [x] Demo login
- [x] Document upload
- [x] Source filtering
- [x] Basic frontend

### 🆕 New Features (This Deployment)
- [x] Microsoft Graph OAuth login
- [x] Email synchronization
- [x] Calendar synchronization
- [x] OneDrive files synchronization
- [x] Teams chat synchronization
- [x] Background task processing (Celery)
- [x] Redis caching
- [x] All 9 dashboard views with real data
- [x] Task status tracking
- [x] Analytics generation
- [x] Rate limiting
- [x] Comprehensive error handling

## 🔧 Configuration Details

### Database Connection
The platform handles both possible PostgreSQL usernames:
- Primary: `bdtadmin`
- Fallback: `btadmin`

No action needed - automatic fallback is implemented.

### Microsoft Graph Permissions
Already configured in Azure AD:
- User.Read
- Mail.Read
- Calendars.Read
- Files.Read.All
- Chat.Read
- offline_access

### Background Tasks
Celery workers automatically started with:
- 4 concurrent workers
- Daily sync at 2 AM
- Cleanup at 3 AM
- Analytics generation at 6 AM

## 🎯 Testing the New Features

### 1. Microsoft Login
```
Navigate to: /api/auth/microsoft
Complete OAuth flow
System will automatically sync initial data
```

### 2. Manual Data Sync
```bash
curl -X POST https://[your-app]/api/twin/{twin_id}/sync \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sources": ["emails", "calendar", "files", "teams"]}'
```

### 3. Dashboard Views
Access each dashboard:
- `/api/dashboard/knowledge` - Document statistics
- `/api/dashboard/processes` - Process optimization
- `/api/dashboard/calendar` - Calendar analytics
- `/api/dashboard/relationships` - Network analysis
- `/api/dashboard/persona` - Behavioral patterns
- `/api/dashboard/tools` - Integration status
- `/api/dashboard/tasks` - Task management
- `/api/dashboard/growth` - Personal development
- `/api/dashboard/content` - Content creation

### 4. Check Task Status
```bash
curl https://[your-app]/api/tasks/{task_id} \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🐛 Troubleshooting

### Issue: Database connection fails
**Solution**: Check both usernames in Azure Portal under PostgreSQL server

### Issue: Microsoft login fails
**Solution**: Verify redirect URI matches exactly:
```
https://bdt-platform-bfc3g7g6eabbf2a4.eastus2-01.azurewebsites.net/api/auth/microsoft/callback
```

### Issue: Redis not starting
**Solution**: Container includes embedded Redis, check logs:
```bash
az webapp log tail --name bdt-platform-app --resource-group BDT-Platform-RG
```

### Issue: Slow performance
**Solution**: Scale up App Service Plan or enable Application Insights

## 📊 Monitoring

### View Logs
```bash
# Stream logs
az webapp log tail --name bdt-platform-app --resource-group BDT-Platform-RG

# Download logs
az webapp log download --name bdt-platform-app --resource-group BDT-Platform-RG
```

### Check Metrics
1. Azure Portal > Web App > Metrics
2. Monitor:
   - CPU usage
   - Memory usage
   - Request count
   - Response time

### Celery Monitoring
Access Flower UI (if enabled):
```
https://[your-app]/flower
```

## 🔒 Security Notes

1. **Rotate Secrets**: Change all secrets in production
2. **Enable HTTPS**: Already configured in Azure
3. **Review CORS**: Update allowed origins for production
4. **Database SSL**: Already enforced
5. **API Rate Limiting**: Configured at 1000 req/min

## 📈 Scaling Considerations

### Vertical Scaling
- Upgrade App Service Plan to P2v3 or higher
- Increase database tier to Standard or higher

### Horizontal Scaling
- Enable autoscaling rules in App Service
- Consider Azure Redis Cache service for production
- Use Azure Service Bus for task queue at scale

## 🎉 Success Indicators

Your deployment is successful when:
1. Health endpoint returns `{"status": "healthy"}`
2. Demo login works
3. Microsoft OAuth redirects properly
4. Dashboard views return data
5. Background tasks appear in task list
6. No errors in application logs

## 📞 Support

For issues or questions:
1. Check logs first
2. Verify all environment variables
3. Ensure Docker image built successfully
4. Confirm Azure resources are running

## 🚢 Production Checklist

Before going to production:
- [ ] Change all default passwords
- [ ] Update JWT secret
- [ ] Configure custom domain
- [ ] Enable Azure Application Insights
- [ ] Set up backup strategy
- [ ] Configure alerts
- [ ] Update CORS origins
- [ ] Enable WAF (Web Application Firewall)
- [ ] Document API endpoints
- [ ] Create user documentation

---

**Deployment Time Estimate**: 20-30 minutes
**Complexity**: Medium
**Prerequisites Met**: ✅ All Azure resources configured

Good luck with your deployment! 🚀
