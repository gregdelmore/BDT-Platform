"""
BDT Platform - Your Actual Enterprise Dashboard
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import json

app = FastAPI(title="BDT Platform", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Your ACTUAL dashboard from the prototype
@app.get("/", response_class=HTMLResponse)
async def root():
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Behavioral Digital Twin (BDT) Enterprise Platform</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Inter', -apple-system, sans-serif; background: #f1f5f9; }
        .sidebar-item { 
            transition: all 0.2s ease; 
            padding: 14px 16px; 
            border-radius: 8px; 
            font-weight: 600; 
            color: #4b5563;
            cursor: pointer;
            margin-bottom: 4px;
        }
        .sidebar-item.active { 
            background-color: #1e3a8a; 
            color: white; 
            box-shadow: 0 4px 10px rgba(30, 58, 138, 0.4);
        }
        .sidebar-item:hover:not(.active) { 
            background-color: #e5e7eb; 
            color: #1f2937;
        }
        .card { 
            box-shadow: 0 1px 3px rgba(0,0,0,0.1); 
            border-radius: 12px; 
            background: white;
        }
        .status-connected { background: #10b981; color: white; }
        .status-pending { background: #fcd34d; color: #78350f; }
        .confidence-high { background: #34d399; }
        .confidence-medium { background: #fcd34d; }
        .confidence-low { background: #fca5a5; }
    </style>
</head>
<body>
    <div class="flex h-screen">
        <!-- Sidebar Navigation -->
        <div class="w-64 bg-gray-800 text-white p-4">
            <div class="mb-8">
                <h1 class="text-2xl font-bold"> BDT Platform</h1>
                <p class="text-sm text-gray-400 mt-2">Enterprise Edition v2.0</p>
            </div>
            
            <nav class="space-y-1">
                <div class="sidebar-item active" onclick="loadDashboard(\'executive\')">
                     Executive Summary
                </div>
                <div class="sidebar-item" onclick="loadDashboard(\'behavioral\')">
                     Behavioral Analysis
                </div>
                <div class="sidebar-item" onclick="loadDashboard(\'team\')">
                     Team Dynamics
                </div>
                <div class="sidebar-item" onclick="loadDashboard(\'risk\')">
                     Risk Assessment
                </div>
                <div class="sidebar-item" onclick="loadDashboard(\'predictions\')">
                     Predictions
                </div>
                <div class="sidebar-item" onclick="loadDashboard(\'recommendations\')">
                     Recommendations
                </div>
                <div class="sidebar-item" onclick="loadDashboard(\'integration\')">
                     Integration Status
                </div>
                <div class="sidebar-item" onclick="loadDashboard(\'ontology\')">
                     Fourth Ontology
                </div>
                <div class="sidebar-item" onclick="loadDashboard(\'settings\')">
                     Settings
                </div>
            </nav>
            
            <div class="mt-8 p-4 bg-gray-700 rounded-lg">
                <p class="text-sm text-gray-300">Demo Account Active</p>
                <p class="text-xs text-gray-400 mt-1">demo@bdt-platform.com</p>
            </div>
        </div>
        
        <!-- Main Content Area -->
        <div class="flex-1 flex flex-col">
            <!-- Header -->
            <header class="bg-white shadow-sm px-8 py-4 flex justify-between items-center">
                <h2 id="dashboard-title" class="text-2xl font-bold text-gray-800">Executive Summary</h2>
                <div class="flex items-center gap-4">
                    <span class="text-sm text-gray-600">Last sync: <span id="sync-time">5 minutes ago</span></span>
                    <span class="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                         Connected
                    </span>
                </div>
            </header>
            
            <!-- Dashboard Content -->
            <main class="flex-1 overflow-auto p-8 bg-gray-50">
                <div id="dashboard-content">
                    <!-- Executive Summary Grid -->
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        <!-- Twin Status Card -->
                        <div class="card p-6">
                            <h3 class="text-lg font-semibold text-gray-800 mb-4">Digital Twin Status</h3>
                            <div class="space-y-3">
                                <div class="flex justify-between">
                                    <span class="text-gray-600">Active Twins</span>
                                    <span class="font-bold text-blue-600">3</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-gray-600">Learning Phase</span>
                                    <span class="font-bold text-yellow-600">1</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-gray-600">Ready for L4</span>
                                    <span class="font-bold text-green-600">2</span>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Data Sources Card -->
                        <div class="card p-6">
                            <h3 class="text-lg font-semibold text-gray-800 mb-4">Data Sources</h3>
                            <div class="space-y-3">
                                <div class="flex items-center justify-between">
                                    <span class="text-gray-600">Microsoft 365</span>
                                    <span class="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">Connected</span>
                                </div>
                                <div class="flex items-center justify-between">
                                    <span class="text-gray-600">Google Workspace</span>
                                    <span class="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs">Pending</span>
                                </div>
                                <div class="flex items-center justify-between">
                                    <span class="text-gray-600">Slack</span>
                                    <span class="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">Not Connected</span>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Processing Metrics Card -->
                        <div class="card p-6">
                            <h3 class="text-lg font-semibold text-gray-800 mb-4">Processing Metrics</h3>
                            <div class="space-y-3">
                                <div class="flex justify-between">
                                    <span class="text-gray-600">Documents</span>
                                    <span class="font-bold">12,845</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-gray-600">Emails</span>
                                    <span class="font-bold">45,234</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-gray-600">Relationships</span>
                                    <span class="font-bold">287</span>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Active Twins Table -->
                        <div class="card p-6 lg:col-span-3">
                            <h3 class="text-lg font-semibold text-gray-800 mb-4">Active Digital Twins</h3>
                            <div class="overflow-x-auto">
                                <table class="w-full">
                                    <thead>
                                        <tr class="text-left text-sm text-gray-600 border-b">
                                            <th class="pb-3">Twin Name</th>
                                            <th class="pb-3">Type</th>
                                            <th class="pb-3">Status</th>
                                            <th class="pb-3">Capability Level</th>
                                            <th class="pb-3">Last Activity</th>
                                            <th class="pb-3">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr class="border-b hover:bg-gray-50">
                                            <td class="py-3">Davinci (Renaissance Man)</td>
                                            <td class="py-3">Individual</td>
                                            <td class="py-3">
                                                <span class="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">Ready</span>
                                            </td>
                                            <td class="py-3">Level 4</td>
                                            <td class="py-3 text-sm text-gray-600">2 min ago</td>
                                            <td class="py-3">
                                                <button onclick="viewTwin(\'davinci\')" class="text-blue-600 hover:text-blue-800 text-sm">View</button>
                                            </td>
                                        </tr>
                                        <tr class="border-b hover:bg-gray-50">
                                            <td class="py-3">Product Team</td>
                                            <td class="py-3">Team</td>
                                            <td class="py-3">
                                                <span class="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs">Learning</span>
                                            </td>
                                            <td class="py-3">Level 2</td>
                                            <td class="py-3 text-sm text-gray-600">1 hour ago</td>
                                            <td class="py-3">
                                                <button onclick="viewTwin(\'product-team\')" class="text-blue-600 hover:text-blue-800 text-sm">View</button>
                                            </td>
                                        </tr>
                                        <tr class="hover:bg-gray-50">
                                            <td class="py-3">Sales Department</td>
                                            <td class="py-3">Department</td>
                                            <td class="py-3">
                                                <span class="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">Ready</span>
                                            </td>
                                            <td class="py-3">Level 3</td>
                                            <td class="py-3 text-sm text-gray-600">15 min ago</td>
                                            <td class="py-3">
                                                <button onclick="viewTwin(\'sales-dept\')" class="text-blue-600 hover:text-blue-800 text-sm">View</button>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        
                        <!-- Quick Actions -->
                        <div class="card p-6 lg:col-span-3">
                            <h3 class="text-lg font-semibold text-gray-800 mb-4">Quick Actions</h3>
                            <div class="flex flex-wrap gap-3">
                                <button onclick="syncData()" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                                    Sync Data
                                </button>
                                <button onclick="createTwin()" class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
                                    Create New Twin
                                </button>
                                <button onclick="testDemo()" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700">
                                    Test Demo Account
                                </button>
                                <button onclick="location.href=\'/api/docs\'" class="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700">
                                    API Documentation
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    </div>
    
    <script>
        // Dashboard functionality
        function loadDashboard(name) {
            document.querySelectorAll(\'.sidebar-item\').forEach(item => {
                item.classList.remove(\'active\');
            });
            event.target.classList.add(\'active\');
            
            const titles = {
                \'executive\': \'Executive Summary\',
                \'behavioral\': \'Behavioral Analysis\',
                \'team\': \'Team Dynamics\',
                \'risk\': \'Risk Assessment\',
                \'predictions\': \'Predictions\',
                \'recommendations\': \'Recommendations\',
                \'integration\': \'Integration Status\',
                \'ontology\': \'Fourth Ontology\',
                \'settings\': \'Settings\'
            };
            
            document.getElementById(\'dashboard-title\').textContent = titles[name] || name;
            
            // Load dashboard content via API
            fetch(\`/api/dashboard/${name}\`)
                .then(res => res.json())
                .then(data => console.log(\'Dashboard data:\', data));
        }
        
        async function testDemo() {
            const res = await fetch(\'/api/auth/demo-login\', {method: \'POST\'});
            const data = await res.json();
            alert(\'Demo login successful! Token: \' + data.access_token);
        }
        
        function viewTwin(id) {
            console.log(\'Viewing twin:\', id);
            // Would load twin details
        }
        
        function syncData() {
            alert(\'Data sync initiated\');
        }
        
        function createTwin() {
            alert(\'Create twin dialog would open\');
        }
        
        // Update sync time
        setInterval(() => {
            const mins = Math.floor(Math.random() * 60) + 1;
            document.getElementById(\'sync-time\').textContent = `${mins} minutes ago`;
        }, 30000);
    </script>
</body>
</html>'''

# API endpoints
@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.0.0"}

@app.post("/api/auth/demo-login")
async def demo_login():
    return {"access_token": "demo-token-123456", "user": "demo@bdt-platform.com"}

@app.get("/api/dashboard/{view}")
async def get_dashboard(view: str):
    dashboards = {
        "executive": {"twins": 3, "documents": 12845, "emails": 45234},
        "behavioral": {"patterns": 47, "insights": 23},
        "team": {"teams": 5, "collaboration_score": 82},
        "risk": {"risks": 7, "mitigation": 5},
        "predictions": {"predictions": 23, "accuracy": 87.5},
        "recommendations": {"active": 12, "implemented": 8},
        "integration": {"connected": 1, "pending": 1, "disconnected": 1},
        "ontology": {"patterns": 15, "innovation_index": 72},
        "settings": {"sync_frequency": "30 minutes", "retention": "90 days"}
    }
    return dashboards.get(view, {})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
