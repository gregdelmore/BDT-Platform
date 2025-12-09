@echo off
REM BDT Platform v2 - Simple Deployment Batch File
REM This keeps Azure CLI output in the same window

echo.
echo ========================================
echo  BDT PLATFORM v2 - DEPLOYMENT
echo ========================================
echo.

REM Set project path
cd /d C:\Customers\Airiam\DigitalTwin\Code\BDT-Deployment\bdt-complete

echo [1/6] Checking Azure Container Registry...
echo.
call az acr repository show-tags --name bdtplatformacr --repository bdt-platform --output table
echo.
pause

echo [2/6] Checking Web App Status...
echo.
call az webapp show --name bdt-platform-app --resource-group BDT-Platform-RG --query "state" --output tsv
echo.
pause

echo [3/6] Deploying v2 to Web App...
echo.
call az webapp config container set --name bdt-platform-app --resource-group BDT-Platform-RG --docker-custom-image-name bdtplatformacr.azurecr.io/bdt-platform:v2
echo.
pause

echo [4/6] Adding Environment Variables...
echo.
call az webapp config appsettings set --name bdt-platform-app --resource-group BDT-Platform-RG --settings REDIS_URL="redis://localhost:6379/0" ENABLE_MICROSOFT_AUTH="true" ENABLE_BACKGROUND_TASKS="true" ENABLE_CACHING="true" ENABLE_ANALYTICS="true" CELERY_BROKER_URL="redis://localhost:6379/0" CELERY_RESULT_BACKEND="redis://localhost:6379/0"
echo.
pause

echo [5/6] Restarting Web App...
echo.
call az webapp restart --name bdt-platform-app --resource-group BDT-Platform-RG
echo.
echo Waiting 45 seconds for app to start...
timeout /t 45 /nobreak

echo [6/6] Testing Health Endpoint...
echo.
curl https://bdt-platform-bfc3g7g6eabbf2a4.eastus2-01.azurewebsites.net/health
echo.
echo.

echo ========================================
echo  DEPLOYMENT COMPLETE
echo ========================================
echo.
echo URL: https://bdt-platform-bfc3g7g6eabbf2a4.eastus2-01.azurewebsites.net
echo.
pause