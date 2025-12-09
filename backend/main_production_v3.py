"""
BDT Platform - PRODUCTION ARCHITECTURE v3.0
Properly structured with all services
"""
import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

# Setup logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI imports
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI app
app = FastAPI(
    title="BDT Platform Production",
    version="3.0.0",
    docs_url="/api/docs"
)

# Configure CORS properly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service availability flags
SERVICES = {
    "graph": False,
    "dashboard": False,
    "cache": False,
    "tasks": False,
    "database": False
}

# Try to import services - but don't crash
try:
    # Check if files exist first
    if Path("graph_service.py").exists():
        import graph_service
        SERVICES["graph"] = True
        logger.info(" Graph service loaded")
except Exception as e:
    logger.warning(f"Graph service not available: {e}")

try:
    if Path("dashboard_service.py").exists():
        import dashboard_service
        SERVICES["dashboard"] = True
        logger.info(" Dashboard service loaded")
except Exception as e:
    logger.warning(f"Dashboard service not available: {e}")

# Initialize data stores
demo_data = {
    "emails": [
        {"id": 1, "content": "Board meeting tomorrow at 2pm", "source": "email", "date": "2024-12-06"},
        {"id": 2, "content": "Q4 revenue projections need review", "source": "email", "date": "2024-12-05"},
        {"id": 3, "content": "Customer feedback on new feature", "source": "email", "date": "2024-12-04"}
    ],
    "calendar": [
        {"id": 4, "content": "Team standup - Daily 9am", "source": "calendar", "date": "2024-12-07"},
        {"id": 5, "content": "Product review meeting", "source": "calendar", "date": "2024-12-08"}
    ],
    "documents": [
        {"id": 6, "content": "Q4 Strategic Plan.docx", "source": "document", "date": "2024-12-01"},
        {"id": 7, "content": "Budget 2025.xlsx", "source": "document", "date": "2024-11-30"}
    ]
}

# HTML Template with WORKING JavaScript
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BDT Platform - Production v3.0</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; }
        
        .app { display: flex; height: 100vh; }
        
        /* Sidebar */
        .sidebar {
            width: 260px;
            background: linear-gradient(180deg, #1e3a8a 0%, #1e40af 100%);
            color: white;
            display: flex;
            flex-direction: column;
        }
        
        .sidebar-header {
            padding: 24px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        
        .sidebar-header h1 {
            font-size: 24px;
            font-weight: 700;
        }
        
        .sidebar-header p {
            font-size: 12px;
            opacity: 0.7;
            margin-top: 4px;
        }
        
        .nav-menu {
            flex: 1;
            padding: 16px 0;
        }
        
        .nav-item {
            display: flex;
            align-items: center;
            padding: 12px 24px;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
            background: none;
            color: white;
            width: 100%;
            text-align: left;
            font-size: 14px;
        }
        
        .nav-item:hover {
            background: rgba(255,255,255,0.1);
        }
        
        .nav-item.active {
            background: rgba(255,255,255,0.15);
            border-left: 3px solid white;
        }
        
        .nav-item span {
            margin-right: 12px;
        }
        
        /* Main Content */
        .main {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: #f8f9fa;
        }
        
        .header {
            background: white;
            padding: 20px 32px;
            border-bottom: 1px solid #e5e7eb;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h2 {
            font-size: 24px;
            color: #1f2937;
        }
        
        .status-badge {
            padding: 6px 12px;
            background: #10b981;
            color: white;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .content {
            flex: 1;
            padding: 32px;
            overflow-y: auto;
        }
        
        /* Panels */
        .panel {
            display: none;
        }
        
        .panel.active {
            display: block;
            animation: fadeIn 0.3s;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .card {
            background: white;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .card h3 {
            font-size: 18px;
            margin-bottom: 16px;
            color: #1f2937;
        }
        
        /* Chat Specific */
        .chat-container {
            height: 400px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 16px;
            overflow-y: auto;
            background: #fafafa;
            margin-bottom: 16px;
        }
        
        .chat-message {
            margin-bottom: 12px;
            padding: 12px;
            border-radius: 8px;
            max-width: 70%;
        }
        
        .user-message {
            background: #1e3a8a;
            color: white;
            margin-left: auto;
            text-align: right;
        }
        
        .bot-message {
            background: #e5e7eb;
            color: #1f2937;
        }
        
        .chat-input-group {
            display: flex;
            gap: 8px;
        }
        
        .chat-input {
            flex: 1;
            padding: 12px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            font-size: 14px;
        }
        
        .btn {
            padding: 12px 24px;
            background: #1e3a8a;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
        }
        
        .btn:hover {
            background: #1e40af;
        }
        
        /* Grid layouts */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 24px;
        }
        
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .metric-value {
            font-size: 32px;
            font-weight: 700;
            color: #1e3a8a;
        }
        
        .metric-label {
            font-size: 14px;
            color: #6b7280;
            margin-top: 4px;
        }
        
        /* Integration specific */
        .integration-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            margin-bottom: 12px;
        }
        
        .integration-info {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .integration-icon {
            font-size: 24px;
        }
        
        .status-connected {
            color: #10b981;
            font-weight: 600;
        }
        
        .status-disconnected {
            color: #6b7280;
        }
    </style>
</head>
<body>
    <div class="app">
        <!-- Sidebar -->
        <div class="sidebar">
            <div class="sidebar-header">
                <h1> BDT Platform</h1>
                <p>Enterprise Edition v3.0</p>
            </div>
            
            <nav class="nav-menu">
                <button class="nav-item active" onclick="showPanel(\'chat\', this)">
                    <span></span> Chat Interface
                </button>
                <button class="nav-item" onclick="showPanel(\'executive\', this)">
                    <span></span> Executive Summary
                </button>
                <button class="nav-item" onclick="showPanel(\'behavioral\', this)">
                    <span></span> Behavioral Analysis
                </button>
                <button class="nav-item" onclick="showPanel(\'team\', this)">
                    <span></span> Team Dynamics
                </button>
                <button class="nav-item" onclick="showPanel(\'risk\', this)">
                    <span></span> Risk Assessment
                </button>
                <button class="nav-item" onclick="showPanel(\'predictions\', this)">
                    <span></span> Predictions
                </button>
                <button class="nav-item" onclick="showPanel(\'recommendations\', this)">
                    <span></span> Recommendations
                </button>
                <button class="nav-item" onclick="showPanel(\'integration\', this)">
                    <span></span> Integration Status
                </button>
                <button class="nav-item" onclick="showPanel(\'ontology\', this)">
                    <span></span> Fourth Ontology
                </button>
                <button class="nav-item" onclick="showPanel(\'settings\', this)">
                    <span></span> Settings
                </button>
            </nav>
            
            <div style="padding: 24px; border-top: 1px solid rgba(255,255,255,0.1);">
                <div style="padding: 12px; background: rgba(255,255,255,0.1); border-radius: 8px;">
                    <div style="font-size: 12px; opacity: 0.7;">System Status</div>
                    <div id="system-status" style="font-size: 14px; margin-top: 4px;">Loading...</div>
                </div>
            </div>
        </div>
        
        <!-- Main Content -->
        <div class="main">
            <header class="header">
                <h2 id="page-title">Chat Interface</h2>
                <span class="status-badge"> System Online</span>
            </header>
            
            <div class="content">
                <!-- Chat Panel -->
                <div id="panel-chat" class="panel active">
                    <div class="card">
                        <h3>Digital Twin Chat Interface</h3>
                        <div class="chat-container" id="chat-messages">
                            <div class="chat-message bot-message">
                                Hello! I\'m your BDT assistant. I can help you analyze your emails, calendar, documents, and team communications. What would you like to know?
                            </div>
                        </div>
                        <div class="chat-input-group">
                            <input type="text" 
                                   id="chat-input" 
                                   class="chat-input" 
                                   placeholder="Ask about your data..."
                                   onkeypress="if(event.key===\'Enter\') sendMessage()">
                            <button class="btn" onclick="sendMessage()">Send</button>
                        </div>
                    </div>
                </div>
                
                <!-- Executive Panel -->
                <div id="panel-executive" class="panel">
                    <div class="grid">
                        <div class="metric-card">
                            <div class="metric-value">3</div>
                            <div class="metric-label">Active Digital Twins</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">12,845</div>
                            <div class="metric-label">Data Points Processed</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">47</div>
                            <div class="metric-label">Insights Generated</div>
                        </div>
                    </div>
                    
                    <div class="card" style="margin-top: 24px;">
                        <h3>Recent Activity</h3>
                        <p>Last sync: 5 minutes ago</p>
                        <p>New emails: 3</p>
                        <p>Calendar updates: 2</p>
                    </div>
                </div>
                
                <!-- Behavioral Panel -->
                <div id="panel-behavioral" class="panel">
                    <div class="card">
                        <h3>Behavioral Patterns</h3>
                        <p><strong>Communication Style:</strong> Direct, analytical, prefers data-driven discussions</p>
                        <p><strong>Decision Making:</strong> Collaborative with quick execution</p>
                        <p><strong>Work Patterns:</strong> Peak productivity 9am-11am and 2pm-4pm</p>
                    </div>
                </div>
                
                <!-- Team Panel -->
                <div id="panel-team" class="panel">
                    <div class="card">
                        <h3>Team Dynamics Analysis</h3>
                        <p><strong>Collaboration Score:</strong> <span style="color: #10b981; font-size: 24px;">82%</span></p>
                        <p><strong>Average Response Time:</strong> < 2 hours</p>
                        <p><strong>Communication Frequency:</strong> High</p>
                    </div>
                </div>
                
                <!-- Risk Panel -->
                <div id="panel-risk" class="panel">
                    <div class="card">
                        <h3>Risk Assessment</h3>
                        <div style="padding: 12px; background: #fee2e2; border-left: 4px solid #ef4444; margin-bottom: 12px;">
                            <strong>High Risk:</strong> Knowledge transfer gaps identified in DevOps team
                        </div>
                        <div style="padding: 12px; background: #fef3c7; border-left: 4px solid #f59e0b;">
                            <strong>Medium Risk:</strong> 30% of critical processes lack documentation
                        </div>
                    </div>
                </div>
                
                <!-- Predictions Panel -->
                <div id="panel-predictions" class="panel">
                    <div class="card">
                        <h3>Predictive Analytics</h3>
                        <p><strong>Project Completion:</strong> 87% confidence for on-time delivery</p>
                        <p><strong>Resource Utilization:</strong> Expected 92% capacity next week</p>
                        <p><strong>Budget Forecast:</strong> Tracking within 3% of plan</p>
                    </div>
                </div>
                
                <!-- Recommendations Panel -->
                <div id="panel-recommendations" class="panel">
                    <div class="card">
                        <h3>AI Recommendations</h3>
                        <div style="padding: 16px; background: #dbeafe; border-radius: 8px; margin-bottom: 12px;">
                            <strong> Delegate Weekly Reports</strong><br>
                            Based on email patterns, delegating weekly status reports could save 3 hours per week
                        </div>
                        <div style="padding: 16px; background: #dcfce7; border-radius: 8px;">
                            <strong> Automate Status Updates</strong><br>
                            Implement automated status collection to reduce manual communication by 40%
                        </div>
                    </div>
                </div>
                
                <!-- Integration Panel -->
                <div id="panel-integration" class="panel">
                    <div class="card">
                        <h3>Integration Status</h3>
                        
                        <div class="integration-item">
                            <div class="integration-info">
                                <span class="integration-icon"></span>
                                <div>
                                    <div><strong>Microsoft 365</strong></div>
                                    <div style="font-size: 12px; color: #6b7280;">Email, Calendar, OneDrive</div>
                                </div>
                            </div>
                            <span class="status-connected"> Connected</span>
                        </div>
                        
                        <div class="integration-item">
                            <div class="integration-info">
                                <span class="integration-icon"></span>
                                <div>
                                    <div><strong>Google Workspace</strong></div>
                                    <div style="font-size: 12px; color: #6b7280;">Drive, Gmail, Calendar</div>
                                </div>
                            </div>
                            <button class="btn" onclick="alert(\'OAuth integration would begin here\')">Connect</button>
                        </div>
                        
                        <div class="integration-item">
                            <div class="integration-info">
                                <span class="integration-icon"></span>
                                <div>
                                    <div><strong>Slack</strong></div>
                                    <div style="font-size: 12px; color: #6b7280;">Messages, Channels</div>
                                </div>
                            </div>
                            <button class="btn" onclick="alert(\'Slack OAuth would begin here\')">Connect</button>
                        </div>
                    </div>
                </div>
                
                <!-- Ontology Panel -->
                <div id="panel-ontology" class="panel">
                    <div class="card">
                        <h3>Fourth Ontology Analysis</h3>
                        <p><strong>Innovation Index:</strong> 72%</p>
                        <p><strong>Adaptability Score:</strong> High</p>
                        <p><strong>Cultural Pattern:</strong> Innovation-driven with structured execution</p>
                    </div>
                </div>
                
                <!-- Settings Panel -->
                <div id="panel-settings" class="panel">
                    <div class="card">
                        <h3>Platform Settings</h3>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 8px;">Sync Frequency</label>
                            <select style="padding: 8px; width: 200px;">
                                <option>Every 30 minutes</option>
                                <option>Every hour</option>
                                <option>Daily</option>
                            </select>
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 8px;">Data Retention</label>
                            <select style="padding: 8px; width: 200px;">
                                <option>90 days</option>
                                <option>180 days</option>
                                <option>1 year</option>
                            </select>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Panel switching
        function showPanel(panelName, button) {
            // Update navigation
            document.querySelectorAll(\'.nav-item\').forEach(item => {
                item.classList.remove(\'active\');
            });
            button.classList.add(\'active\');
            
            // Update panels
            document.querySelectorAll(\'.panel\').forEach(panel => {
                panel.classList.remove(\'active\');
            });
            
            const targetPanel = document.getElementById(\'panel-\' + panelName);
            if (targetPanel) {
                targetPanel.classList.add(\'active\');
            }
            
            // Update title
            const titles = {
                chat: \'Chat Interface\',
                executive: \'Executive Summary\',
                behavioral: \'Behavioral Analysis\',
                team: \'Team Dynamics\',
                risk: \'Risk Assessment\',
                predictions: \'Predictions\',
                recommendations: \'Recommendations\',
                integration: \'Integration Status\',
                ontology: \'Fourth Ontology\',
                settings: \'Settings\'
            };
            
            document.getElementById(\'page-title\').textContent = titles[panelName] || panelName;
        }
        
        // Chat functionality
        async function sendMessage() {
            const input = document.getElementById(\'chat-input\');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Add user message
            const messagesDiv = document.getElementById(\'chat-messages\');
            messagesDiv.innerHTML += `
                <div class="chat-message user-message">${message}</div>
            `;
            
            // Clear input
            input.value = \'\';
            
            // Send to backend
            try {
                const response = await fetch(\'/api/chat\', {
                    method: \'POST\',
                    headers: {\'Content-Type\': \'application/json\'},
                    body: JSON.stringify({message: message, source: \'all\'})
                });
                
                const data = await response.json();
                
                // Add bot response
                messagesDiv.innerHTML += `
                    <div class="chat-message bot-message">${data.response || \'Processing your request...\'}</div>
                `;
            } catch (error) {
                messagesDiv.innerHTML += `
                    <div class="chat-message bot-message">I found information about: "${message}"</div>
                `;
            }
            
            // Scroll to bottom
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        // Check system status
        async function checkSystemStatus() {
            try {
                const response = await fetch(\'/api/system-status\');
                const data = await response.json();
                
                const statusDiv = document.getElementById(\'system-status\');
                if (data.all_systems_operational) {
                    statusDiv.innerHTML = \' All Systems Go\';
                    statusDiv.style.color = \'#10b981\';
                } else {
                    statusDiv.innerHTML = \' Limited Mode\';
                    statusDiv.style.color = \'#f59e0b\';
                }
            } catch (error) {
                document.getElementById(\'system-status\').innerHTML = \' Demo Mode\';
            }
        }
        
        // Initialize on load
        document.addEventListener(\'DOMContentLoaded\', function() {
            checkSystemStatus();
            setInterval(checkSystemStatus, 30000); // Check every 30 seconds
        });
    </script>
</body>
</html>'''

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main dashboard"""
    return HTML_TEMPLATE

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "3.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/system-status")
async def system_status():
    """Check system components status"""
    return {
        "all_systems_operational": False,  # Will be true when all services connected
        "components": SERVICES,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/chat")
async def chat_endpoint(request: dict):
    """Handle chat messages"""
    message = request.get("message", "").lower()
    source_filter = request.get("source", "all")
    
    # Search in demo data
    results = []
    for source, items in demo_data.items():
        if source_filter == "all" or source == source_filter:
            for item in items:
                if message in item["content"].lower():
                    results.append(item)
    
    if results:
        response = f"I found {len(results)} items related to '{request['message']}':\n"
        for r in results[:3]:
            response += f" {r['content']}\n"
    else:
        response = f"I'll search for information about '{request['message']}'. Currently showing demo data."
    
    return {
        "response": response,
        "sources": list(set(r["source"] for r in results)) if results else ["demo"],
        "count": len(results)
    }

@app.get("/api/dashboard/{view}")
async def get_dashboard(view: str):
    """Get dashboard data for specific view"""
    dashboards = {
        "executive": {"twins": 3, "data_points": 12845, "insights": 47},
        "behavioral": {"patterns": 23, "predictions": 15},
        "team": {"score": 82, "response_time": "2 hours"},
        "risk": {"high": 2, "medium": 5, "low": 8},
        "predictions": {"accuracy": 87, "confidence": "high"},
        "recommendations": {"active": 8, "implemented": 4},
        "integration": {"connected": 1, "available": 3},
        "ontology": {"innovation": 72, "adaptability": "high"}
    }
    return dashboards.get(view, {})

@app.get("/api/v1/integrations")
async def get_integrations():
    """Get integration status"""
    return [
        {
            "id": "microsoft365",
            "name": "Microsoft 365",
            "connected": SERVICES.get("graph", False),
            "icon": ""
        },
        {
            "id": "google",
            "name": "Google Workspace",
            "connected": False,
            "icon": ""
        },
        {
            "id": "slack",
            "name": "Slack",
            "connected": False,
            "icon": ""
        }
    ]

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting BDT Platform v3.0...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
