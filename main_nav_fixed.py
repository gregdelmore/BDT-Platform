"""
BDT Platform - Fixed Navigation Version
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
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

# Store demo data
demo_data = {
    "emails": [
        {"content": "Board meeting tomorrow at 2pm", "source": "email"},
        {"content": "Q4 revenue projections need review", "source": "email"}
    ],
    "calendar": [
        {"content": "Annual Performance Review - Dec 15", "source": "calendar"},
        {"content": "Team Standup Daily 9am", "source": "calendar"}
    ]
}

@app.get("/", response_class=HTMLResponse)
async def root():
    return '''<!DOCTYPE html>
<html>
<head>
    <title>BDT Platform</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .sidebar-item { cursor: pointer; transition: all 0.2s; }
        .sidebar-item:hover { background: rgba(255,255,255,0.1); }
        .sidebar-item.active { background: #1e3a8a; }
        .view-panel { display: none; }
        .view-panel.active { display: block; }
    </style>
</head>
<body class="bg-gray-100">
    <div class="flex h-screen">
        <!-- Sidebar -->
        <div class="w-64 bg-gray-800 text-white">
            <div class="p-4">
                <h1 class="text-2xl font-bold"> BDT Platform</h1>
                <p class="text-sm text-gray-400">Production v2.0</p>
            </div>
            
            <nav class="mt-4">
                <div class="sidebar-item active p-3" data-view="chat"> Chat Interface</div>
                <div class="sidebar-item p-3" data-view="executive"> Executive Summary</div>
                <div class="sidebar-item p-3" data-view="behavioral"> Behavioral Analysis</div>
                <div class="sidebar-item p-3" data-view="team"> Team Dynamics</div>
                <div class="sidebar-item p-3" data-view="risk"> Risk Assessment</div>
                <div class="sidebar-item p-3" data-view="predictions"> Predictions</div>
                <div class="sidebar-item p-3" data-view="recommendations"> Recommendations</div>
                <div class="sidebar-item p-3" data-view="integration"> Integration Status</div>
                <div class="sidebar-item p-3" data-view="ontology"> Fourth Ontology</div>
                <div class="sidebar-item p-3" data-view="settings"> Settings</div>
            </nav>
        </div>
        
        <!-- Main Content -->
        <div class="flex-1 flex flex-col">
            <!-- Header -->
            <header class="bg-white shadow px-6 py-4">
                <h2 id="page-title" class="text-2xl font-bold">Chat Interface</h2>
            </header>
            
            <!-- Content Area -->
            <main class="flex-1 p-6 overflow-auto">
                
                <!-- Chat View -->
                <div id="chat" class="view-panel active">
                    <div class="bg-white rounded-lg shadow p-4 h-full flex flex-col">
                        <div class="mb-4">
                            <label class="text-sm font-medium">Filter by Source:</label>
                            <div class="flex gap-2 mt-2">
                                <button class="px-3 py-1 bg-blue-600 text-white rounded text-sm">All</button>
                                <button class="px-3 py-1 bg-gray-200 rounded text-sm">Email</button>
                                <button class="px-3 py-1 bg-gray-200 rounded text-sm">Calendar</button>
                            </div>
                        </div>
                        <div id="chat-messages" class="flex-1 border rounded p-4 bg-gray-50 overflow-y-auto">
                            <div class="bg-blue-100 p-3 rounded mb-2">
                                Welcome! Ask me about your emails, calendar, or documents.
                            </div>
                        </div>
                        <div class="flex gap-2 mt-4">
                            <input type="text" id="chat-input" placeholder="Type your message..." 
                                   class="flex-1 px-4 py-2 border rounded-lg">
                            <button onclick="sendMessage()" class="px-6 py-2 bg-blue-600 text-white rounded-lg">Send</button>
                        </div>
                    </div>
                </div>
                
                <!-- Executive View -->
                <div id="executive" class="view-panel">
                    <div class="grid grid-cols-3 gap-4">
                        <div class="bg-white p-6 rounded-lg shadow">
                            <h3 class="font-semibold mb-3">Active Twins</h3>
                            <p class="text-3xl font-bold">3</p>
                        </div>
                        <div class="bg-white p-6 rounded-lg shadow">
                            <h3 class="font-semibold mb-3">Data Points</h3>
                            <p class="text-3xl font-bold">12,845</p>
                        </div>
                        <div class="bg-white p-6 rounded-lg shadow">
                            <h3 class="font-semibold mb-3">Insights Generated</h3>
                            <p class="text-3xl font-bold">47</p>
                        </div>
                    </div>
                </div>
                
                <!-- Behavioral View -->
                <div id="behavioral" class="view-panel">
                    <div class="bg-white p-6 rounded-lg shadow">
                        <h3 class="text-lg font-semibold mb-4">Behavioral Analysis</h3>
                        <div class="grid grid-cols-2 gap-4">
                            <div class="border rounded p-4">
                                <h4 class="font-medium mb-2">Communication Style</h4>
                                <p class="text-sm text-gray-600">Direct, analytical, data-driven</p>
                            </div>
                            <div class="border rounded p-4">
                                <h4 class="font-medium mb-2">Decision Pattern</h4>
                                <p class="text-sm text-gray-600">Collaborative with quick execution</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Team View -->
                <div id="team" class="view-panel">
                    <div class="bg-white p-6 rounded-lg shadow">
                        <h3 class="text-lg font-semibold mb-4">Team Dynamics</h3>
                        <p>Collaboration Score: <span class="text-2xl font-bold text-green-600">82%</span></p>
                        <div class="mt-4">
                            <div class="flex justify-between mb-2">
                                <span>Communication Frequency</span>
                                <span>High</span>
                            </div>
                            <div class="flex justify-between">
                                <span>Response Time</span>
                                <span>< 2 hours avg</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Risk View -->
                <div id="risk" class="view-panel">
                    <div class="bg-white p-6 rounded-lg shadow">
                        <h3 class="text-lg font-semibold mb-4">Risk Assessment</h3>
                        <div class="space-y-3">
                            <div class="p-3 border-l-4 border-red-500">
                                <p class="font-medium">High Risk: Knowledge Transfer</p>
                                <p class="text-sm text-gray-600">Key personnel dependency identified</p>
                            </div>
                            <div class="p-3 border-l-4 border-yellow-500">
                                <p class="font-medium">Medium Risk: Process Documentation</p>
                                <p class="text-sm text-gray-600">30% of processes undocumented</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Predictions View -->
                <div id="predictions" class="view-panel">
                    <div class="bg-white p-6 rounded-lg shadow">
                        <h3 class="text-lg font-semibold mb-4">Predictions</h3>
                        <div class="space-y-3">
                            <div>
                                <p class="font-medium">Project Completion</p>
                                <div class="bg-gray-200 rounded-full h-4 mt-1">
                                    <div class="bg-blue-600 h-4 rounded-full" style="width: 87%"></div>
                                </div>
                                <p class="text-sm text-gray-600 mt-1">87% confidence for on-time delivery</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Recommendations View -->
                <div id="recommendations" class="view-panel">
                    <div class="bg-white p-6 rounded-lg shadow">
                        <h3 class="text-lg font-semibold mb-4">Recommendations</h3>
                        <div class="space-y-3">
                            <div class="flex gap-3 p-3 bg-blue-50 rounded">
                                <span class="text-2xl"></span>
                                <div>
                                    <p class="font-medium">Delegate Weekly Reports</p>
                                    <p class="text-sm text-gray-600">Save 3 hours per week</p>
                                </div>
                            </div>
                            <div class="flex gap-3 p-3 bg-green-50 rounded">
                                <span class="text-2xl"></span>
                                <div>
                                    <p class="font-medium">Automate Status Updates</p>
                                    <p class="text-sm text-gray-600">Reduce manual communication by 40%</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Integration View -->
                <div id="integration" class="view-panel">
                    <div class="bg-white p-6 rounded-lg shadow">
                        <h3 class="text-lg font-semibold mb-4">Integration Status</h3>
                        <div class="space-y-3">
                            <div class="flex justify-between items-center p-4 border rounded">
                                <div class="flex items-center gap-3">
                                    <span class="text-2xl"></span>
                                    <div>
                                        <p class="font-medium">Microsoft 365</p>
                                        <p class="text-sm text-gray-600">Email, Calendar, OneDrive</p>
                                    </div>
                                </div>
                                <span class="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm">Connected</span>
                            </div>
                            <div class="flex justify-between items-center p-4 border rounded">
                                <div class="flex items-center gap-3">
                                    <span class="text-2xl"></span>
                                    <div>
                                        <p class="font-medium">Slack</p>
                                        <p class="text-sm text-gray-600">Messages, Channels</p>
                                    </div>
                                </div>
                                <button class="px-4 py-2 bg-blue-600 text-white rounded text-sm">Connect</button>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Ontology View -->
                <div id="ontology" class="view-panel">
                    <div class="bg-white p-6 rounded-lg shadow">
                        <h3 class="text-lg font-semibold mb-4">Fourth Ontology</h3>
                        <p class="mb-4">Cultural Analysis Framework</p>
                        <div class="grid grid-cols-2 gap-4">
                            <div>
                                <p class="font-medium">Innovation Index</p>
                                <p class="text-2xl font-bold text-blue-600">72%</p>
                            </div>
                            <div>
                                <p class="font-medium">Adaptability Score</p>
                                <p class="text-2xl font-bold text-green-600">High</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Settings View -->
                <div id="settings" class="view-panel">
                    <div class="bg-white p-6 rounded-lg shadow">
                        <h3 class="text-lg font-semibold mb-4">Settings</h3>
                        <div class="space-y-4">
                            <div>
                                <label class="block text-sm font-medium mb-1">Sync Frequency</label>
                                <select class="w-full border rounded px-3 py-2">
                                    <option>Every 30 minutes</option>
                                    <option>Every hour</option>
                                    <option>Daily</option>
                                </select>
                            </div>
                            <div>
                                <label class="block text-sm font-medium mb-1">Data Retention</label>
                                <select class="w-full border rounded px-3 py-2">
                                    <option>90 days</option>
                                    <option>180 days</option>
                                    <option>1 year</option>
                                </select>
                            </div>
                        </div>
                    </div>
                </div>
                
            </main>
        </div>
    </div>
    
    <script>
        // Fixed navigation
        document.addEventListener("DOMContentLoaded", function() {
            // Add click handlers to all sidebar items
            document.querySelectorAll(".sidebar-item").forEach(item => {
                item.addEventListener("click", function() {
                    const viewName = this.getAttribute("data-view");
                    
                    // Update active sidebar item
                    document.querySelectorAll(".sidebar-item").forEach(si => {
                        si.classList.remove("active");
                    });
                    this.classList.add("active");
                    
                    // Hide all views
                    document.querySelectorAll(".view-panel").forEach(panel => {
                        panel.classList.remove("active");
                    });
                    
                    // Show selected view
                    const selectedView = document.getElementById(viewName);
                    if (selectedView) {
                        selectedView.classList.add("active");
                    }
                    
                    // Update title
                    const titles = {
                        chat: "Chat Interface",
                        executive: "Executive Summary",
                        behavioral: "Behavioral Analysis",
                        team: "Team Dynamics",
                        risk: "Risk Assessment",
                        predictions: "Predictions",
                        recommendations: "Recommendations",
                        integration: "Integration Status",
                        ontology: "Fourth Ontology",
                        settings: "Settings"
                    };
                    document.getElementById("page-title").textContent = titles[viewName] || viewName;
                });
            });
        });
        
        async function sendMessage() {
            const input = document.getElementById("chat-input");
            const message = input.value.trim();
            if (!message) return;
            
            const messagesDiv = document.getElementById("chat-messages");
            
            // Add user message
            messagesDiv.innerHTML += '<div class="bg-blue-600 text-white p-3 rounded mb-2 ml-auto" style="max-width: 70%">' + message + '</div>';
            
            // Clear input
            input.value = "";
            
            // Add response
            setTimeout(() => {
                messagesDiv.innerHTML += '<div class="bg-gray-200 p-3 rounded mb-2" style="max-width: 70%">I found information related to: ' + message + '</div>';
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }, 500);
        }
    </script>
</body>
</html>'''

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.0.0"}

@app.post("/api/chat")
async def chat(request: dict):
    return {
        "response": f"Searching for: {request.get('message', '')}",
        "sources": ["email", "calendar"],
        "count": 2
    }

@app.get("/api/dashboard/{view}")
async def dashboard(view: str):
    return {"view": view, "data": "Dashboard data"}

@app.get("/api/v1/integrations")
async def integrations():
    return [
        {"name": "Microsoft 365", "connected": True},
        {"name": "Slack", "connected": False}
    ]
