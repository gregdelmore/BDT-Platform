# BDT PLATFORM v2.0 - COMPLETE DEPLOYMENT & RECOVERY SCRIPT
# ============================================================
# This script handles everything from checking status to complete deployment
# Works around Azure CLI popup window issues on Windows PowerShell

<#
.SYNOPSIS
    Complete deployment script for BDT Platform v2.0
.DESCRIPTION
    - Checks current deployment status
    - Builds and pushes Docker image if needed
    - Deploys to Azure Web App
    - Handles Azure CLI output issues
    - Includes all troubleshooting
.NOTES
    Project: BDT Platform v2.0
    Location: C:\Customers\Airiam\DigitalTwin\Code\BDT-Deployment\bdt-complete
    Azure Resources:
    - Registry: bdtplatformacr
    - Web App: bdt-platform-app
    - Resource Group: BDT-Platform-RG
    - URL: https://bdt-platform-bfc3g7g6eabbf2a4.eastus2-01.azurewebsites.net
#>

param(
    [string]$ProjectPath = "C:\Customers\Airiam\DigitalTwin\Code\BDT-Deployment\bdt-complete",
    [switch]$SkipBuild,
    [switch]$ForceRebuild,
    [switch]$CheckOnly
)

# ============================================================
# SECTION 1: SETUP & FUNCTIONS
# ============================================================

# Colors for output
$colors = @{
    Success = "Green"
    Error = "Red"
    Warning = "Yellow"
    Info = "Cyan"
    Detail = "Gray"
}

# Move to project directory
Set-Location $ProjectPath -ErrorAction SilentlyContinue

Write-Host "`n╔══════════════════════════════════════════════════════════════╗" -ForegroundColor $colors.Info
Write-Host   "║           BDT PLATFORM v2.0 - DEPLOYMENT SCRIPT             ║" -ForegroundColor $colors.Info
Write-Host   "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor $colors.Info

# Function to run Azure CLI commands and capture output (fixes popup issue)
function Invoke-AzCommand {
    param(
        [string]$Command,
        [string]$Description = "Running Azure command..."
    )
    
    Write-Host "`n→ $Description" -ForegroundColor $colors.Warning
    
    # Method 1: Try with output redirection
    $output = cmd /c "az $Command 2>&1"
    
    # If that fails, try method 2
    if ([string]::IsNullOrEmpty($output)) {
        $tempFile = [System.IO.Path]::GetTempFileName()
        Start-Process -FilePath "cmd.exe" `
            -ArgumentList "/c az $Command > `"$tempFile`" 2>&1" `
            -NoNewWindow -Wait
        
        if (Test-Path $tempFile) {
            $output = Get-Content $tempFile -Raw
            Remove-Item $tempFile -Force
        }
    }
    
    return $output
}

# Function to test web endpoint
function Test-WebEndpoint {
    param([string]$Url)
    
    try {
        $response = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 30
        return $response
    } catch {
        return $null
    }
}

# ============================================================
# SECTION 2: STATUS CHECK
# ============================================================

if (-not $SkipBuild) {
    Write-Host "`n════════════════════════════════════════" -ForegroundColor $colors.Info
    Write-Host " STEP 1: CHECKING CURRENT STATUS" -ForegroundColor $colors.Info
    Write-Host "════════════════════════════════════════" -ForegroundColor $colors.Info

    # Check if Docker is running
    Write-Host "`n→ Checking Docker..." -ForegroundColor $colors.Warning
    $dockerRunning = docker ps 2>&1
    if ($dockerRunning -like "*error*" -or $dockerRunning -like "*cannot*") {
        Write-Host "  ✗ Docker is not running" -ForegroundColor $colors.Error
        Write-Host "  Starting Docker Desktop..." -ForegroundColor $colors.Warning
        Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 20
    } else {
        Write-Host "  ✓ Docker is running" -ForegroundColor $colors.Success
    }

    # Check local Docker images
    Write-Host "`n→ Checking local Docker images..." -ForegroundColor $colors.Warning
    $localImages = docker images --format "{{.Repository}}:{{.Tag}}" 2>&1 | Select-String "bdt-platform"
    if ($localImages) {
        Write-Host "  ✓ Found local images:" -ForegroundColor $colors.Success
        $localImages | ForEach-Object { Write-Host "    - $_" -ForegroundColor $colors.Detail }
    } else {
        Write-Host "  ✗ No local bdt-platform images found" -ForegroundColor $colors.Warning
    }

    # Check ACR images
    Write-Host "`n→ Checking Azure Container Registry..." -ForegroundColor $colors.Warning
    $acrTags = Invoke-AzCommand `
        -Command "acr repository show-tags --name bdtplatformacr --repository bdt-platform --output tsv" `
        -Description "Getting ACR tags"
    
    if ($acrTags) {
        Write-Host "  ✓ Found tags in ACR:" -ForegroundColor $colors.Success
        $acrTags -split "`n" | Where-Object { $_ } | ForEach-Object { 
            $color = if ($_ -eq "v2") { $colors.Success } else { $colors.Detail }
            Write-Host "    - $_" -ForegroundColor $color
        }
        $hasV2InACR = $acrTags -match "v2"
    } else {
        Write-Host "  ✗ Could not retrieve ACR tags" -ForegroundColor $colors.Error
        $hasV2InACR = $false
    }

    # Check current web app configuration
    Write-Host "`n→ Checking Web App configuration..." -ForegroundColor $colors.Warning
    $currentImage = Invoke-AzCommand `
        -Command "webapp config container show --name bdt-platform-app --resource-group BDT-Platform-RG --query dockerCustomImageName --output tsv" `
        -Description "Getting current Web App image"
    
    if ($currentImage) {
        Write-Host "  Current image: $currentImage" -ForegroundColor $colors.Detail
        $isUsingV2 = $currentImage -match "v2"
    } else {
        Write-Host "  ✗ Could not retrieve current image" -ForegroundColor $colors.Error
        $isUsingV2 = $false
    }

    # Check app health
    Write-Host "`n→ Testing application health..." -ForegroundColor $colors.Warning
    $health = Test-WebEndpoint -Url "https://bdt-platform-bfc3g7g6eabbf2a4.eastus2-01.azurewebsites.net/health"
    if ($health) {
        Write-Host "  ✓ Application is responding" -ForegroundColor $colors.Success
        Write-Host "    Status: $($health.status)" -ForegroundColor $colors.Detail
        if ($health.checks) {
            Write-Host "    Database: $($health.checks.database)" -ForegroundColor $colors.Detail
            Write-Host "    ChromaDB: $($health.checks.chromadb)" -ForegroundColor $colors.Detail
            Write-Host "    Cache: $($health.checks.cache)" -ForegroundColor $colors.Detail
        }
        $appHealthy = $health.status -eq "healthy"
    } else {
        Write-Host "  ✗ Application not responding" -ForegroundColor $colors.Error
        $appHealthy = $false
    }
}

if ($CheckOnly) {
    Write-Host "`n════════════════════════════════════════" -ForegroundColor $colors.Info
    Write-Host " STATUS CHECK COMPLETE" -ForegroundColor $colors.Info
    Write-Host "════════════════════════════════════════" -ForegroundColor $colors.Info
    
    Write-Host "`nSummary:" -ForegroundColor $colors.Info
    Write-Host "  ACR has v2: $(if($hasV2InACR){'Yes'}else{'No'})" -ForegroundColor $(if($hasV2InACR){$colors.Success}else{$colors.Error})
    Write-Host "  Web App using v2: $(if($isUsingV2){'Yes'}else{'No'})" -ForegroundColor $(if($isUsingV2){$colors.Success}else{$colors.Error})
    Write-Host "  App healthy: $(if($appHealthy){'Yes'}else{'No'})" -ForegroundColor $(if($appHealthy){$colors.Success}else{$colors.Error})
    
    exit 0
}

# ============================================================
# SECTION 3: BUILD & PUSH (if needed)
# ============================================================

$needsBuild = $ForceRebuild -or -not $hasV2InACR

if ($needsBuild -and -not $SkipBuild) {
    Write-Host "`n════════════════════════════════════════" -ForegroundColor $colors.Info
    Write-Host " STEP 2: BUILD & PUSH DOCKER IMAGE" -ForegroundColor $colors.Info
    Write-Host "════════════════════════════════════════" -ForegroundColor $colors.Info

    # Ensure Dockerfile exists
    if (-not (Test-Path ".\Dockerfile")) {
        if (Test-Path ".\Dockerfile.v2") {
            Write-Host "→ Renaming Dockerfile.v2 to Dockerfile..." -ForegroundColor $colors.Warning
            Move-Item -Path ".\Dockerfile.v2" -Destination ".\Dockerfile" -Force
            Write-Host "  ✓ Dockerfile ready" -ForegroundColor $colors.Success
        } else {
            Write-Host "  ✗ No Dockerfile found!" -ForegroundColor $colors.Error
            exit 1
        }
    }

    # Build Docker image
    Write-Host "`n→ Building Docker image (this takes 5-10 minutes)..." -ForegroundColor $colors.Warning
    $buildResult = docker build -t bdt-platform:v2 . 2>&1
    $buildSuccess = $LASTEXITCODE -eq 0
    
    if ($buildSuccess) {
        Write-Host "  ✓ Docker image built successfully" -ForegroundColor $colors.Success
    } else {
        Write-Host "  ✗ Docker build failed" -ForegroundColor $colors.Error
        Write-Host "Error output:" -ForegroundColor $colors.Error
        Write-Host $buildResult -ForegroundColor $colors.Detail
        exit 1
    }

    # Tag image
    Write-Host "`n→ Tagging Docker image..." -ForegroundColor $colors.Warning
    docker tag bdt-platform:v2 bdtplatformacr.azurecr.io/bdt-platform:v2
    Write-Host "  ✓ Image tagged" -ForegroundColor $colors.Success

    # Login to ACR
    Write-Host "`n→ Logging into Azure Container Registry..." -ForegroundColor $colors.Warning
    $loginResult = Invoke-AzCommand `
        -Command "acr login --name bdtplatformacr" `
        -Description "ACR login"
    
    if ($loginResult -match "Login Succeeded" -or $loginResult -match "successful") {
        Write-Host "  ✓ ACR login successful" -ForegroundColor $colors.Success
    } else {
        Write-Host "  ⚠ ACR login may have failed" -ForegroundColor $colors.Warning
    }

    # Push to ACR
    Write-Host "`n→ Pushing to ACR (this takes 3-5 minutes)..." -ForegroundColor $colors.Warning
    $pushResult = docker push bdtplatformacr.azurecr.io/bdt-platform:v2 2>&1
    $pushSuccess = $LASTEXITCODE -eq 0
    
    if ($pushSuccess) {
        Write-Host "  ✓ Image pushed to ACR successfully" -ForegroundColor $colors.Success
        $hasV2InACR = $true
    } else {
        Write-Host "  ✗ Push failed" -ForegroundColor $colors.Error
        Write-Host "Error output:" -ForegroundColor $colors.Error
        Write-Host $pushResult -ForegroundColor $colors.Detail
        exit 1
    }
} elseif ($hasV2InACR) {
    Write-Host "`n✓ v2 already exists in ACR, skipping build" -ForegroundColor $colors.Success
}

# ============================================================
# SECTION 4: DEPLOY TO WEB APP
# ============================================================

if ($hasV2InACR -and -not $isUsingV2) {
    Write-Host "`n════════════════════════════════════════" -ForegroundColor $colors.Info
    Write-Host " STEP 3: DEPLOY TO AZURE WEB APP" -ForegroundColor $colors.Info
    Write-Host "════════════════════════════════════════" -ForegroundColor $colors.Info

    # Update container image
    Write-Host "`n→ Updating Web App to v2..." -ForegroundColor $colors.Warning
    $updateResult = Invoke-AzCommand `
        -Command "webapp config container set --name bdt-platform-app --resource-group BDT-Platform-RG --docker-custom-image-name bdtplatformacr.azurecr.io/bdt-platform:v2 --docker-registry-server-url https://bdtplatformacr.azurecr.io" `
        -Description "Updating container"
    
    if ($updateResult) {
        Write-Host "  ✓ Container updated" -ForegroundColor $colors.Success
    }

    # Add environment variables
    Write-Host "`n→ Adding environment variables..." -ForegroundColor $colors.Warning
    $envResult = Invoke-AzCommand `
        -Command 'webapp config appsettings set --name bdt-platform-app --resource-group BDT-Platform-RG --settings REDIS_URL="redis://localhost:6379/0" ENABLE_MICROSOFT_AUTH="true" ENABLE_BACKGROUND_TASKS="true" ENABLE_CACHING="true" ENABLE_ANALYTICS="true" CELERY_BROKER_URL="redis://localhost:6379/0" CELERY_RESULT_BACKEND="redis://localhost:6379/0"' `
        -Description "Setting environment variables"
    
    Write-Host "  ✓ Environment variables set" -ForegroundColor $colors.Success

    # Restart web app
    Write-Host "`n→ Restarting Web App..." -ForegroundColor $colors.Warning
    $restartResult = Invoke-AzCommand `
        -Command "webapp restart --name bdt-platform-app --resource-group BDT-Platform-RG" `
        -Description "Restarting app"
    
    Write-Host "  ✓ Web App restarted" -ForegroundColor $colors.Success
    
    # Wait for startup
    Write-Host "`n→ Waiting for app to start (45 seconds)..." -ForegroundColor $colors.Warning
    Start-Sleep -Seconds 45
} elseif ($isUsingV2) {
    Write-Host "`n✓ Web App already using v2" -ForegroundColor $colors.Success
}

# ============================================================
# SECTION 5: FINAL VERIFICATION
# ============================================================

Write-Host "`n════════════════════════════════════════" -ForegroundColor $colors.Info
Write-Host " STEP 4: FINAL VERIFICATION" -ForegroundColor $colors.Info
Write-Host "════════════════════════════════════════" -ForegroundColor $colors.Info

# Check app state
Write-Host "`n→ Checking app state..." -ForegroundColor $colors.Warning
$appState = Invoke-AzCommand `
    -Command "webapp show --name bdt-platform-app --resource-group BDT-Platform-RG --query state --output tsv" `
    -Description "Getting app state"

Write-Host "  App State: $appState" -ForegroundColor $(if($appState -eq "Running"){$colors.Success}else{$colors.Error})

# Test health endpoint
Write-Host "`n→ Testing health endpoint..." -ForegroundColor $colors.Warning
$finalHealth = Test-WebEndpoint -Url "https://bdt-platform-bfc3g7g6eabbf2a4.eastus2-01.azurewebsites.net/health"

if ($finalHealth -and $finalHealth.status -eq "healthy") {
    Write-Host "  ✓ Application is healthy!" -ForegroundColor $colors.Success
    Write-Host "    Database: $($finalHealth.checks.database)" -ForegroundColor $colors.Detail
    Write-Host "    ChromaDB: $($finalHealth.checks.chromadb)" -ForegroundColor $colors.Detail
    Write-Host "    Cache: $($finalHealth.checks.cache)" -ForegroundColor $colors.Detail
} else {
    Write-Host "  ⚠ Application may need more time to start" -ForegroundColor $colors.Warning
}

# Test demo login
Write-Host "`n→ Testing demo login..." -ForegroundColor $colors.Warning
try {
    $loginTest = Invoke-RestMethod `
        -Uri "https://bdt-platform-bfc3g7g6eabbf2a4.eastus2-01.azurewebsites.net/api/auth/demo-login" `
        -Method Post `
        -ContentType "application/json" `
        -TimeoutSec 30
    
    if ($loginTest.access_token) {
        Write-Host "  ✓ Demo login successful!" -ForegroundColor $colors.Success
    }
} catch {
    Write-Host "  ⚠ Demo login not responding yet" -ForegroundColor $colors.Warning
}

# ============================================================
# SECTION 6: SUMMARY & NEXT STEPS
# ============================================================

Write-Host "`n╔══════════════════════════════════════════════════════════════╗" -ForegroundColor $colors.Info
Write-Host   "║                    DEPLOYMENT COMPLETE                      ║" -ForegroundColor $colors.Info
Write-Host   "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor $colors.Info

Write-Host "`nApplication URL:" -ForegroundColor $colors.Info
Write-Host "  https://bdt-platform-bfc3g7g6eabbf2a4.eastus2-01.azurewebsites.net" -ForegroundColor $colors.Success

Write-Host "`nAPI Documentation:" -ForegroundColor $colors.Info
Write-Host "  https://bdt-platform-bfc3g7g6eabbf2a4.eastus2-01.azurewebsites.net/api/docs" -ForegroundColor $colors.Success

Write-Host "`nNext Steps:" -ForegroundColor $colors.Info
Write-Host "  1. Open the application in your browser" -ForegroundColor $colors.Detail
Write-Host "  2. Click 'Demo Login' to test" -ForegroundColor $colors.Detail
Write-Host "  3. Connect Microsoft account for full functionality" -ForegroundColor $colors.Detail
Write-Host "  4. Run test_api.py for comprehensive testing" -ForegroundColor $colors.Detail

# Open in browser
$openBrowser = Read-Host "`nOpen application in browser? (Y/N)"
if ($openBrowser -eq "Y" -or $openBrowser -eq "y") {
    Start-Process "https://bdt-platform-bfc3g7g6eabbf2a4.eastus2-01.azurewebsites.net"
}

# ============================================================
# SECTION 7: TROUBLESHOOTING COMMANDS (if needed)
# ============================================================

Write-Host "`n════════════════════════════════════════" -ForegroundColor $colors.Info
Write-Host " TROUBLESHOOTING COMMANDS" -ForegroundColor $colors.Info
Write-Host "════════════════════════════════════════" -ForegroundColor $colors.Info

Write-Host @"

If you encounter issues, use these commands:

Check logs:
  az webapp log tail --name bdt-platform-app --resource-group BDT-Platform-RG

Force restart:
  az webapp restart --name bdt-platform-app --resource-group BDT-Platform-RG

Check configuration:
  az webapp config show --name bdt-platform-app --resource-group BDT-Platform-RG

View environment variables:
  az webapp config appsettings list --name bdt-platform-app --resource-group BDT-Platform-RG --output table

Build directly in Azure (if local Docker fails):
  az acr build --registry bdtplatformacr --image bdt-platform:v2 .

"@ -ForegroundColor $colors.Detail

Write-Host "Script completed at: $(Get-Date)" -ForegroundColor $colors.Info

# ============================================================
# END OF SCRIPT
# ============================================================