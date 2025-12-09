"""
BDT Platform - Complete Integration Configuration
With individual service controls for each user
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="BDT Platform - Integration Manager", version="5.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import integration manager
try:
    from integration_manager import integration_manager
    INTEGRATION_READY = True
    logger.info(" Integration Manager loaded!")
except Exception as e:
    logger.error(f"Integration Manager error: {e}")
    INTEGRATION_READY = False
    integration_manager = None

# Store synced data
USER_DATA = {
    "tyler.helwig@airiam.com": {
        "emails": [],
        "onedrive": [],
        "teams": [],
        "calendar": [],
        "last_sync": None
    }
}

@app.get("/", response_class=HTMLResponse)
async def root():
    """Main dashboard with integration configuration"""
    return '''<!DOCTYPE html>
<html>
<head>
    <title>BDT Platform - Integration Configuration</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, Arial, sans-serif; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .grid { display: grid; grid-template-columns: 350px 1fr; gap: 20px; }
        .sidebar { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .main { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .user-card { border: 1px solid #e5e7eb; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
        .user-card.active { border-color: #3b82f6; background: #eff6ff; }
        .service-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 10px; }
        .service-toggle { display: flex; align-items: center; justify-content: space-between; padding: 10px; background: #f9fafb; border-radius: 6px; }
        .toggle { width: 50px; height: 24px; background: #cbd5e1; border-radius: 12px; position: relative; cursor: pointer; }
        .toggle.active { background: #3b82f6; }
        .toggle-handle { width: 20px; height: 20px; background: white; border-radius: 50%; position: absolute; top: 2px; left: 2px; transition: 0.3s; }
        .toggle.active .toggle-handle { left: 28px; }
        .btn { padding: 10px 20px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer; }
        .btn:hover { background: #2563eb; }
        .status { padding: 4px 8px; border-radius: 4px; font-size: 12px; }
        .status.connected { background: #d1fae5; color: #065f46; }
        .status.pending { background: #fed7aa; color: #9a3412; }
        .status.disconnected { background: #fee2e2; color: #991b1b; }
        .data-section { margin-top: 20px; }
        .data-item { padding: 10px; border-bottom: 1px solid #e5e7eb; }
        .chat-box { border: 1px solid #e5e7eb; padding: 20px; border-radius: 8px; height: 400px; overflow-y: auto; background: #fafafa; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1> BDT Platform - Integration Configuration</h1>
            <p style="color: #6b7280; margin-top: 5px;">Configure individual service access for each user</p>
        </div>
        
        <div class="grid">
            <!-- Sidebar with user list -->
            <div class="sidebar">
                <h2 style="margin-bottom: 20px;">User Accounts</h2>
                
                <!-- Tyler's Account -->
                <div class="user-card active" id="user-tyler">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong>Tyler Helwig</strong>
                            <div style="font-size: 12px; color: #6b7280;">tyler.helwig@airiam.com</div>
                        </div>
                        <span class="status connected">Configured</span>
                    </div>
                    
                    <div class="service-grid">
                        <div class="service-toggle">
                            <span> Email</span>
                            <div class="toggle" id="tyler-email" onclick="toggleService('tyler.helwig@airiam.com', 'email', this)">
                                <div class="toggle-handle"></div>
                            </div>
                        </div>
                        
                        <div class="service-toggle">
                            <span> OneDrive</span>
                            <div class="toggle" id="tyler-onedrive" onclick="toggleService('tyler.helwig@airiam.com', 'onedrive', this)">
                                <div class="toggle-handle"></div>
                            </div>
                        </div>
                        
                        <div class="service-toggle">
                            <span> Teams</span>
                            <div class="toggle" id="tyler-teams" onclick="toggleService('tyler.helwig@airiam.com', 'teams', this)">
                                <div class="toggle-handle"></div>
                            </div>
                        </div>
                        
                        <div class="service-toggle">
                            <span> Calendar</span>
                            <div class="toggle" id="tyler-calendar" onclick="toggleService('tyler.helwig@airiam.com', 'calendar', this)">
                                <div class="toggle-handle"></div>
                            </div>
                        </div>
                    </div>
                    
                    <div style="margin-top: 15px;">
                        <button class="btn" onclick="authenticateUser('tyler.helwig@airiam.com')" style="width: 100%;">
                            Authenticate Tyler
                        </button>
                        <button class="btn" onclick="syncUser('tyler.helwig@airiam.com')" style="width: 100%; margin-top: 10px; background: #10b981;">
                            Sync Tyler's Data
                        </button>
                    </div>
                </div>
                
                <!-- Add more users -->
                <button class="btn" onclick="addUser()" style="width: 100%; margin-top: 20px;">
                    + Add User Account
                </button>
            </div>
            
            <!-- Main content area -->
            <div class="main">
                <h2>Tyler Helwig's Data</h2>
                <p style="color: #6b7280; margin-bottom: 20px;">Departed employee - Knowledge extraction mode</p>
                
                <!-- Chat interface for querying Tyler's data -->
                <div style="margin-bottom: 20px;">
                    <h3>Ask about Tyler's work</h3>
                    <div class="chat-box" id="chat-box">
                        <div class="data-item">
                            Ask questions about Tyler's emails, files, and communications...
                        </div>
                    </div>
                    <div style="display: flex; gap: 10px; margin-top: 10px;">
                        <input type="text" id="chat-input" placeholder="What projects was Tyler working on?" 
                               style="flex: 1; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px;">
                        <button class="btn" onclick="askAboutTyler()">Ask</button>
                    </div>
                </div>
                
                <!-- Data sections -->
                <div class="data-section">
                    <h3>Recent Emails</h3>
                    <div id="tyler-emails">
                        <div class="data-item">No emails synced yet</div>
                    </div>
                </div>
                
                <div class="data-section">
                    <h3>OneDrive Files</h3>
                    <div id="tyler-files">
                        <div class="data-item">No files synced yet</div>
                    </div>
                </div>
                
                <div class="data-section">
                    <h3>Teams Messages</h3>
                    <div id="tyler-teams-msgs">
                        <div class="data-item">No Teams messages synced yet</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Store service states
        const serviceStates = {
            'tyler.helwig@airiam.com': {
                email: false,
                onedrive: false,
                teams: false,
                calendar: false
            }
        };
        
        function toggleService(email, service, element) {
            element.classList.toggle('active');
            serviceStates[email][service] = element.classList.contains('active');
            
            // Send to backend
            fetch('/api/integration/toggle', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    email: email,
                    service: service,
                    enabled: serviceStates[email][service]
                })
            });
        }
        
        async function authenticateUser(email) {
            alert(`Authenticating ${email}...\\n\\nNote: This will require 2FA approval`);
            
            const response = await fetch('/api/integration/authenticate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({email: email})
            });
            
            const data = await response.json();
            
            if (data.verification_url) {
                alert(`Please go to: ${data.verification_url}\\nEnter code: ${data.user_code}`);
            }
        }
        
        async function syncUser(email) {
            const enabledServices = Object.entries(serviceStates[email])
                .filter(([k, v]) => v)
                .map(([k]) => k);
            
            if (enabledServices.length === 0) {
                alert('Please enable at least one service first');
                return;
            }
            
            alert(`Syncing Tyler's data for: ${enabledServices.join(', ')}`);
            
            const response = await fetch('/api/integration/sync', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    email: email,
                    services: enabledServices
                })
            });
            
            const data = await response.json();
            
            if (data.emails) {
                updateEmails(data.emails);
            }
            if (data.files) {
                updateFiles(data.files);
            }
            if (data.teams) {
                updateTeams(data.teams);
            }
            
            alert(`Synced: ${data.email_count || 0} emails, ${data.file_count || 0} files, ${data.teams_count || 0} Teams messages`);
        }
        
        function updateEmails(emails) {
            const container = document.getElementById('tyler-emails');
            container.innerHTML = emails.slice(0, 5).map(email => 
                `<div class="data-item">
                    <strong>${email.subject}</strong><br>
                    From: ${email.from}<br>
                    <small>${email.date}</small>
                </div>`
            ).join('');
        }
        
        function updateFiles(files) {
            const container = document.getElementById('tyler-files');
            container.innerHTML = files.slice(0, 5).map(file => 
                `<div class="data-item">
                     ${file.name}<br>
                    <small>Modified: ${file.modified}</small>
                </div>`
            ).join('');
        }
        
        function updateTeams(messages) {
            const container = document.getElementById('tyler-teams-msgs');
            container.innerHTML = messages.slice(0, 5).map(msg => 
                `<div class="data-item">
                    <strong>${msg.from}</strong>: ${msg.content}<br>
                    <small>${msg.timestamp}</small>
                </div>`
            ).join('');
        }
        
        async function askAboutTyler() {
            const input = document.getElementById('chat-input');
            const question = input.value;
            
            if (!question) return;
            
            const chatBox = document.getElementById('chat-box');
            chatBox.innerHTML += `<div class="data-item"><strong>You:</strong> ${question}</div>`;
            
            const response = await fetch('/api/chat/tyler', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({question: question})
            });
            
            const data = await response.json();
            chatBox.innerHTML += `<div class="data-item"><strong>BDT:</strong> ${data.answer}</div>`;
            
            input.value = '';
            chatBox.scrollTop = chatBox.scrollHeight;
        }
        
        function addUser() {
            const email = prompt('Enter user email:');
            if (email) {
                alert(`Would add configuration for ${email}`);
            }
        }
    </script>
</body>
</html>'''

@app.post("/api/integration/toggle")
async def toggle_service(request: dict):
    """Toggle a service for a user"""
    email = request.get("email")
    service = request.get("service")
    enabled = request.get("enabled")
    
    if integration_manager and email in integration_manager.users:
        integration_manager.users[email].services[service] = enabled
        return {"status": "success", "service": service, "enabled": enabled}
    
    return {"error": "User not found"}

@app.post("/api/integration/authenticate")
async def authenticate_user(request: dict):
    """Start authentication for a user"""
    email = request.get("email")
    
    if not integration_manager:
        return {"error": "Integration manager not available"}
    
    result = await integration_manager.authenticate_user(email)
    return result

@app.post("/api/integration/sync")
async def sync_user_data(request: dict):
    """Sync data for specific services"""
    email = request.get("email")
    services = request.get("services", [])
    
    if not integration_manager:
        return {"error": "Integration manager not available"}
    
    # Enable requested services
    if email in integration_manager.users:
        for service in services:
            integration_manager.users[email].services[service] = True
    
    # Sync data
    emails = []
    files = []
    teams = []
    
    if "email" in services:
        emails = await integration_manager.get_user_emails(email)
        USER_DATA[email]["emails"] = emails
    
    if "onedrive" in services:
        files = await integration_manager.get_user_onedrive(email)
        USER_DATA[email]["onedrive"] = files
    
    if "teams" in services:
        teams = await integration_manager.get_user_teams_chats(email)
        USER_DATA[email]["teams"] = teams
    
    USER_DATA[email]["last_sync"] = datetime.utcnow().isoformat()
    
    return {
        "status": "success",
        "email_count": len(emails),
        "file_count": len(files),
        "teams_count": len(teams),
        "emails": emails[:5],
        "files": files[:5],
        "teams": teams[:5]
    }

@app.post("/api/chat/tyler")
async def chat_about_tyler(request: dict):
    """Answer questions about Tyler's data"""
    question = request.get("question", "").lower()
    
    tyler_data = USER_DATA.get("tyler.helwig@airiam.com", {})
    
    # Search through Tyler's data
    relevant_items = []
    
    # Search emails
    for email in tyler_data.get("emails", []):
        if question in email.get("subject", "").lower() or question in email.get("preview", "").lower():
            relevant_items.append(f"Email: {email['subject']} from {email['from']}")
    
    # Search files
    for file in tyler_data.get("onedrive", []):
        if question in file.get("name", "").lower():
            relevant_items.append(f"File: {file['name']}")
    
    # Search Teams
    for msg in tyler_data.get("teams", []):
        if question in msg.get("content", "").lower():
            relevant_items.append(f"Teams: {msg['from']} said '{msg['content'][:100]}'")
    
    if relevant_items:
        answer = f"Based on Tyler's data, I found {len(relevant_items)} relevant items:\\n" + "\\n".join(relevant_items[:5])
    else:
        answer = f"I couldn't find specific information about '{question}' in Tyler's synced data. Try syncing more services or asking a different question."
    
    return {"answer": answer}

@app.get("/health")
async def health():
    return {"status": "healthy", "integration_ready": INTEGRATION_READY}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
