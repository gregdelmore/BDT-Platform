"""
BDT Platform - COMPLETE FUNCTIONAL VERSION WITH CHAT
"""
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import json
import asyncio

app = FastAPI(title="BDT Platform", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store demo data and chat history
demo_data = {
    "emails": [
        {"id": 1, "content": "Board meeting tomorrow at 2pm with agenda attached", "source": "email", "date": "2024-12-05"},
        {"id": 2, "content": "Q4 revenue projections need review by EOD", "source": "email", "date": "2024-12-04"},
        {"id": 3, "content": "Customer complaint about service delays", "source": "email", "date": "2024-12-03"}
    ],
    "calendar": [
        {"id": 4, "content": "Annual Performance Review - December 15", "source": "calendar", "date": "2024-12-15"},
        {"id": 5, "content": "Team Standup - Daily at 9am", "source": "calendar", "date": "2024-12-06"}
    ],
    "documents": [
        {"id": 6, "content": "2024 Strategic Plan - Final Version", "source": "document", "date": "2024-12-01"},
        {"id": 7, "content": "Product Roadmap Q1 2025", "source": "document", "date": "2024-11-30"}
    ],
    "teams": [
        {"id": 8, "content": "Great work on the presentation!", "source": "teams", "date": "2024-12-05"},
        {"id": 9, "content": "Can someone review my PR?", "source": "teams", "date": "2024-12-04"}
    ]
}

chat_history = []

@app.get("/", response_class=HTMLResponse)
async def root():
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BDT Platform - Complete with Chat</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .sidebar-item { 
            cursor: pointer;
            transition: all 0.2s;
        }
        .sidebar-item:hover {
            background: rgba(255,255,255,0.1);
        }
        .sidebar-item.active {
            background: #1e3a8a;
        }
        .chat-message {
            max-width: 70%;
            margin: 10px;
            padding: 10px 15px;
            border-radius: 10px;
        }
        .user-message {
            background: #1e3a8a;
            color: white;
            align-self: flex-end;
            margin-left: auto;
        }
        .assistant-message {
            background: #e0f7fa;
            color: #333;
            align-self: flex-start;
        }
        #chat-container {
            height: 400px;
            overflow-y: auto;
            border: 1px solid #e5e7eb;
            background: white;
            border-radius: 8px;
        }
    </style>
</head>
<body class="bg-gray-100">
    <div class="flex h-screen">
        <!-- Sidebar -->
        <div class="w-64 bg-gray-800 text-white">
            <div class="p-4">
                <h1 class="text-2xl font-bold">🚀 BDT Platform</h1>
                <p class="text-sm text-gray-400 mt-1">Enterprise v2.0</p>
            </div>
            
            <nav class="mt-4">
                <div class="sidebar-item p-3 active" onclick="showView('chat')">💬 Chat Interface</div>
                <div class="sidebar-item p-3" onclick="showView('executive')">📊 Executive Summary</div>
                <div class="sidebar-item p-3" onclick="showView('behavioral')">🧠 Behavioral Analysis</div>
                <div class="sidebar-item p-3" onclick="showView('team')">👥 Team Dynamics</div>
                <div class="sidebar-item p-3" onclick="showView('data')">📁 Data Sources</div>
                <div class="sidebar-item p-3" onclick="showView('settings')">⚙️ Settings</div>
            </nav>
            
            <div class="p-4 mt-8">
                <div class="bg-gray-700 rounded p-3">
                    <p class="text-sm">Demo Active</p>
                    <p class="text-xs text-gray-400">demo@bdt-platform.com</p>
                </div>
            </div>
        </div>
        
        <!-- Main Content -->
        <div class="flex-1 flex flex-col">
            <!-- Header -->
            <header class="bg-white shadow px-6 py-4 flex justify-between items-center">
                <h2 id="page-title" class="text-2xl font-bold">Chat Interface</h2>
                <div class="flex items-center gap-4">
                    <button onclick="syncData()" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                        Sync Data
                    </button>
                    <span class="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm">
                        ✓ Connected
                    </span>
                </div>
            </header>
            
            <!-- Dynamic Content Area -->
            <main class="flex-1 p-6 overflow-auto">
                <!-- Chat View -->
                <div id="chat-view" class="h-full">
                    <div class="bg-white rounded-lg shadow p-4 h-full flex flex-col">
                        <!-- Source Filter -->
                        <div class="mb-4">
                            <label class="text-sm font-medium text-gray-700">Filter by Source:</label>
                            <div class="flex gap-2 mt-2">
                                <button onclick="filterSource('all')" class="px-3 py-1 bg-blue-600 text-white rounded text-sm">All</button>
                                <button onclick="filterSource('email')" class="px-3 py-1 bg-gray-200 rounded text-sm">Email</button>
                                <button onclick="filterSource('calendar')" class="px-3 py-1 bg-gray-200 rounded text-sm">Calendar</button>
                                <button onclick="filterSource('document')" class="px-3 py-1 bg-gray-200 rounded text-sm">Documents</button>
                                <button onclick="filterSource('teams')" class="px-3 py-1 bg-gray-200 rounded text-sm">Teams</button>
                            </div>
                        </div>
                        
                        <!-- Chat Messages -->
                        <div id="chat-container" class="flex-1 flex flex-col p-4">
                            <div class="assistant-message chat-message">
                                Hello! I'm your BDT assistant. I can help you search and analyze your data. 
                                Try asking me about meetings, emails, or documents.
                            </div>
                        </div>
                        
                        <!-- Input Area -->
                        <div class="flex gap-2 mt-4">
                            <input 
                                type="text" 
                                id="chat-input"
                                placeholder="Ask me anything about your data..."
                                class="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                onkeypress="if(event.key==='Enter') sendMessage()"
                            >
                            <button onclick="sendMessage()" class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                                Send
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- Executive View -->
                <div id="executive-view" class="hidden">
                    <div class="grid grid-cols-3 gap-4">
                        <div class="bg-white p-6 rounded-lg shadow">
                            <h3 class="font-semibold mb-3">Twin Status</h3>
                            <div class="space-y-2">
                                <div class="flex justify-between">
                                    <span>Active</span>
                                    <span class="font-bold">3</span>
                                </div>
                                <div class="flex justify-between">
                                    <span>Learning</span>
                                    <span class="font-bold">1</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="bg-white p-6 rounded-lg shadow">
                            <h3 class="font-semibold mb-3">Data Processed</h3>
                            <div class="space-y-2">
                                <div class="flex justify-between">
                                    <span>Emails</span>
                                    <span class="font-bold">3</span>
                                </div>
                                <div class="flex justify-between">
                                    <span>Documents</span>
                                    <span class="font-bold">2</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="bg-white p-6 rounded-lg shadow">
                            <h3 class="font-semibold mb-3">System Health</h3>
                            <div class="space-y-2">
                                <div class="flex justify-between">
                                    <span>API</span>
                                    <span class="text-green-600">✓ Online</span>
                                </div>
                                <div class="flex justify-between">
                                    <span>Database</span>
                                    <span class="text-green-600">✓ Connected</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Data View -->
                <div id="data-view" class="hidden">
                    <div class="bg-white rounded-lg shadow p-6">
                        <h3 class="text-lg font-semibold mb-4">Available Data Sources</h3>
                        <div id="data-list" class="space-y-3"></div>
                    </div>
                </div>
                
                <!-- Other Views -->
                <div id="behavioral-view" class="hidden">
                    <div class="bg-white p-6 rounded-lg shadow">
                        <h3 class="text-lg font-semibold">Behavioral Analysis</h3>
                        <p class="mt-2">Communication patterns and decision-making analysis will appear here.</p>
                    </div>
                </div>
                
                <div id="team-view" class="hidden">
                    <div class="bg-white p-6 rounded-lg shadow">
                        <h3 class="text-lg font-semibold">Team Dynamics</h3>
                        <p class="mt-2">Team collaboration metrics and relationship mapping.</p>
                    </div>
                </div>
                
                <div id="settings-view" class="hidden">
                    <div class="bg-white p-6 rounded-lg shadow">
                        <h3 class="text-lg font-semibold">Settings</h3>
                        <div class="mt-4 space-y-3">
                            <div>
                                <label class="block text-sm font-medium">Sync Frequency</label>
                                <select class="mt-1 block w-full border rounded px-3 py-2">
                                    <option>Every 30 minutes</option>
                                    <option>Every hour</option>
                                    <option>Daily</option>
                                </select>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    </div>
    
    <script>
        let currentSource = "all";
        
        function showView(view) {
            // Hide all views
            ["chat", "executive", "data", "behavioral", "team", "settings"].forEach(v => {
                document.getElementById(v + "-view").classList.add("hidden");
            });
            
            // Show selected view
            document.getElementById(view + "-view").classList.remove("hidden");
            
            // Update sidebar
            document.querySelectorAll(".sidebar-item").forEach(item => {
                item.classList.remove("active");
            });
            event.target.classList.add("active");
            
            // Update title
            const titles = {
                chat: "Chat Interface",
                executive: "Executive Summary",
                behavioral: "Behavioral Analysis",
                team: "Team Dynamics",
                data: "Data Sources",
                settings: "Settings"
            };
            document.getElementById("page-title").textContent = titles[view];
            
            // Load data view if selected
            if (view === "data") {
                loadDataView();
            }
        }
        
        async function sendMessage() {
            const input = document.getElementById("chat-input");
            const message = input.value.trim();
            if (!message) return;
            
            // Add user message to chat
            const container = document.getElementById("chat-container");
            container.innerHTML += `<div class="user-message chat-message">${message}</div>`;
            
            // Clear input
            input.value = "";
            
            // Send to API
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({message, source: currentSource})
            });
            
            const data = await response.json();
            
            // Add assistant response
            container.innerHTML += `
                <div class="assistant-message chat-message">
                    ${data.response}
                    <div class="text-xs text-gray-500 mt-2">
                        Sources: ${data.sources.join(", ")}
                    </div>
                </div>
            `;
            
            // Scroll to bottom
            container.scrollTop = container.scrollHeight;
        }
        
        function filterSource(source) {
            currentSource = source;
            
            // Update button styles
            document.querySelectorAll("button").forEach(btn => {
                if (btn.textContent.toLowerCase().includes(source) || 
                    (source === "all" && btn.textContent === "All")) {
                    btn.classList.add("bg-blue-600", "text-white");
                    btn.classList.remove("bg-gray-200");
                } else if (btn.textContent === "All" || 
                           ["Email", "Calendar", "Documents", "Teams"].includes(btn.textContent)) {
                    btn.classList.remove("bg-blue-600", "text-white");
                    btn.classList.add("bg-gray-200");
                }
            });
            
            // Add feedback
            const container = document.getElementById("chat-container");
            container.innerHTML += `
                <div class="assistant-message chat-message">
                    Now filtering by: <strong>${source}</strong>
                </div>
            `;
        }
        
        async function loadDataView() {
            const response = await fetch("/api/v1/data");
            const data = await response.json();
            
            const list = document.getElementById("data-list");
            list.innerHTML = "";
            
            for (const [source, items] of Object.entries(data.data)) {
                list.innerHTML += `
                    <div class="border rounded p-3">
                        <h4 class="font-semibold capitalize">${source} (${items.length} items)</h4>
                        <ul class="mt-2 text-sm text-gray-600">
                            ${items.slice(0, 3).map(item => 
                                `<li>• ${item.content.substring(0, 50)}...</li>`
                            ).join("")}
                        </ul>
                    </div>
                `;
            }
        }
        
        async function syncData() {
            alert("Data sync initiated! New data will appear in the chat.");
            
            // Add some new data
            await fetch("/api/v1/data/ingest", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    source_type: "email",
                    content: "New email: Meeting rescheduled to 3pm"
                })
            });
            
            location.reload();
        }
    </script>
</body>
</html>'''

# API endpoints
@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.0.0", "features": ["chat", "filtering", "ingestion"]}

@app.post("/api/auth/demo-login")
async def demo_login():
    return {"access_token": "demo-token-123456", "user": "demo@bdt-platform.com"}

@app.post("/api/chat")
async def chat(request: dict):
    """Handle chat messages with source filtering"""
    message = request.get("message", "")
    source = request.get("source", "all")
    
    # Simple response logic
    response = f"I found information related to '{message}'"
    
    # Filter data by source
    filtered_data = []
    if source == "all":
        for items in demo_data.values():
            filtered_data.extend(items)
    elif source in demo_data:
        filtered_data = demo_data[source]
    
    # Search in filtered data
    results = [item for item in filtered_data if message.lower() in item["content"].lower()]
    
    if results:
        response = f"I found {len(results)} items matching '{message}':\n"
        for r in results[:3]:
            response += f"• {r['content'][:100]}... (from {r['source']})\n"
    else:
        response = f"No results found for '{message}' in {source} data."
    
    return {
        "response": response,
        "sources": [r["source"] for r in results[:3]] if results else ["No sources"],
        "count": len(results)
    }

@app.get("/api/v1/data")
async def get_all_data(source: str = None):
    """Get data with optional source filtering"""
    if source and source in demo_data:
        return {"source": source, "data": {source: demo_data[source]}}
    return {"data": demo_data}

@app.post("/api/v1/data/ingest")
async def ingest_data(data: dict):
    """Add new data to the system"""
    source_type = data.get("source_type", "unknown")
    content = data.get("content", "")
    
    if source_type in demo_data:
        new_item = {
            "id": len(demo_data[source_type]) + 100,
            "content": content,
            "source": source_type,
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        demo_data[source_type].append(new_item)
        return {"status": "success", "item": new_item}
    
    return {"status": "error", "message": "Invalid source type"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
