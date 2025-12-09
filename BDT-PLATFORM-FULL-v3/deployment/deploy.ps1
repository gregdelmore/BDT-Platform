# Deploy to Azure
Write-Host "Deploying BDT Platform to Azure..." -ForegroundColor Green
$registry = "bdtplatformacr"
$app = "bdt-platform"
$rg = "BDT-Platform-RG"

# Build
cmd /c "az acr build --registry $registry --image bdt-platform:latest ."

# Deploy
cmd /c "az webapp config container set --name $app --resource-group $rg --docker-custom-image-name $registry.azurecr.io/bdt-platform:latest"

# Configure
cmd /c "az webapp config appsettings set --name $app --resource-group $rg --settings WEBSITES_PORT=8000"

# Restart
cmd /c "az webapp restart --name $app --resource-group $rg"

Write-Host "Deployment complete!" -ForegroundColor Green
Start-Sleep -Seconds 60
Start-Process "https://bdt-platform-bfc3g7g6eabbf2a4.eastus2-01.azurewebsites.net"
