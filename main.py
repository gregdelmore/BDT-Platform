from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import requests
import uuid
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
CLIENT_ID = "98f8baa3-5127-4ef1-83d7-cdec8b9cb791"
CLIENT_SECRET = "mpX8Q~mrLGi-dcQF-kpNGiC2ZkiXOB0Bi6I_BbCq"
REDIRECT_URI = "https://bdt-platform-bfc3g7g6eabbf2a4.eastus2-01.azurewebsites.net/auth/callback"
AUTHORITY = "https://login.microsoftonline.com/common"

# Storage
authenticated_users = {}
real_data_counts = {}
chat_histories = {}
pending_auth = {}

@app.get("/", response_class=HTMLResponse)
async def root():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>BDT Platform - Production</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, Arial, sans-serif; display: flex; height: 100vh; }
        .sidebar { width: 260px; background: #1e3a8a; color: white; }
        .sidebar h1 { padding: 20px; font-size: 24px; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .nav-item { padding: 15px 20px; cursor: pointer; transition: 0.2s; }
        .nav-item:hover { background: rgba(255,255,255,0.1); }
        .nav-item.active { background: rgba(255,255,255,0.2); border-left: 4px solid white; }
        .main { flex: 1; display: flex; flex-direction: column; }
        .header { background: white; padding: 20px 30px; border-bottom: 1px solid #e5e7eb; }
        .content { flex: 1; padding: 30px; background: #f5f5f5; overflow: auto; }
        .view { display: none; }
        .view.active { display: block; }
        .card { background: white; border-radius: 8px; padding: 24px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .btn { padding: 12px 24px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; }
        .btn:hover { background: #2563eb; }
        .btn-success { background: #10b981; }
        input, select { width: 100%; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px; margin: 5px 0; }
        
        /* Integration styles */
        .auth-warning { background: #fef3c7; border: 1px solid #f59e0b; padding: 15px; border-radius: 8px; margin: 20px 0; }
        .data-metric { display: flex; justify-content: space-between; padding: 12px; margin: 8px 0; border-left: 4px solid #3b82f6; background: #f9fafb; }
        .user-data-card { border: 2px solid #e5e7eb; padding: 20px; margin: 15px 0; border-radius: 8px; }
        .user-data-card.authenticated { border-color: #10b981; }
        .real-count { font-weight: bold; color: #059669; }
        .no-data { color: #9ca3af; font-style: italic; }
        
        /* Analysis page styles */
        .analysis-container { display: flex; gap: 20px; height: calc(100vh - 300px); }
        .chat-history { width: 300px; background: white; border-radius: 8px; padding: 20px; overflow-y: auto; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .chat-history h4 { margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #e5e7eb; }
        .history-item { padding: 10px; margin: 5px 0; background: #f9fafb; border-radius: 6px; cursor: pointer; transition: 0.2s; }
        .history-item:hover { background: #eff6ff; }
        .history-item.active { background: #dbeafe; border-left: 3px solid #3b82f6; }
        .history-date { font-size: 10px; color: #9ca3af; }
        .history-preview { font-size: 12px; color: #4b5563; margin-top: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .chat-main { flex: 1; display: flex; flex-direction: column; }
        .chat-window { background: white; border-radius: 8px; padding: 20px; flex: 1; overflow-y: auto; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .message { margin: 15px 0; padding: 10px 15px; border-radius: 8px; }
        .message.user { background: #eff6ff; border-left: 3px solid #3b82f6; }
        .message.assistant { background: #f0fdf4; border-left: 3px solid #10b981; }
        .source-filters { background: white; border-radius: 8px; padding: 15px; margin-top: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .filter-buttons { display: flex; gap: 10px; flex-wrap: wrap; }
        .filter-btn { padding: 8px 16px; background: #f3f4f6; border: 2px solid #e5e7eb; border-radius: 6px; cursor: pointer; transition: 0.2s; }
        .filter-btn:hover { background: #e5e7eb; }
        .filter-btn.active { background: #3b82f6; color: white; border-color: #3b82f6; }
        .input-area { display: flex; gap: 10px; margin-top: 20px; }
        .input-area input { flex: 1; padding: 12px; border: 2px solid #e5e7eb; border-radius: 6px; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h1> BDT Platform</h1>
        <div class="nav-item active" data-view="dashboard"> Dashboard</div>
        <div class="nav-item" data-view="integration"> Integration</div>
        <div class="nav-item" data-view="analysis"> Analysis</div>
        <div class="nav-item" data-view="executive"> Executive Summary</div>
        <div class="nav-item" data-view="behavioral"> Behavioral Analysis</div>
        <div class="nav-item" data-view="team"> Team Dynamics</div>
        <div class="nav-item" data-view="risk"> Risk Assessment</div>
        <div class="nav-item" data-view="predictions"> Predictions</div>
        <div class="nav-item" data-view="recommendations"> Recommendations</div>
        <div class="nav-item" data-view="ontology"> Fourth Ontology</div>
        <div class="nav-item" data-view="processes"> Processes</div>
        <div class="nav-item" data-view="settings"> Settings</div>
    </div>
    
    <div class="main">
        <div class="header">
            <h2 id="page-title">Dashboard</h2>
        </div>
        
        <div class="content">
            <!-- DASHBOARD TAB -->
            <div id="dashboard" class="view active">
                <div class="card">
                    <h3>Production System Status</h3>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-top: 20px;">
                        <div style="text-align: center; padding: 20px; background: #d1fae5; border-radius: 8px;">
                            <div style="font-size: 24px;"></div>
                            <div>PostgreSQL</div>
                        </div>
                        <div style="text-align: center; padding: 20px; background: #d1fae5; border-radius: 8px;">
                            <div style="font-size: 24px;"></div>
                            <div>Azure AI Search</div>
                        </div>
                        <div style="text-align: center; padding: 20px; background: #d1fae5; border-radius: 8px;">
                            <div style="font-size: 24px;"></div>
                            <div>Graph DB</div>
                        </div>
                        <div style="text-align: center; padding: 20px; background: #d1fae5; border-radius: 8px;">
                            <div style="font-size: 24px;"></div>
                            <div>OpenAI</div>
                        </div>
                    </div>
                </div>
                <div class="card">
                    <h3>Platform Overview</h3>
                    <p>BDT Platform ready for production use. Configure users in the Integration tab to begin data extraction.</p>
                </div>
            </div>
            
            <!-- INTEGRATION TAB -->
            <div id="integration" class="view">
                <div class="card">
                    <h3>Production Data Integration</h3>
                    
                    <div class="auth-warning">
                        <strong> Production Environment</strong><br>
                        Users from ANY Microsoft 365 organization can authenticate to grant data access.
                        Real data extraction only - no demo mode.
                    </div>
                    
                    <div style="margin: 30px 0;">
                        <h4>Configure User Access</h4>
                        <label><strong>User Email Address</strong></label>
                        <input type="email" id="user-email" placeholder="user@anycompany.com">
                        <p style="color: #6b7280; margin: 10px 0;">User will authenticate with their Microsoft 365 credentials</p>
                    </div>
                    
                    <div style="margin: 30px 0;">
                        <h4>Data Sources to Extract</h4>
                        <div class="data-metric">
                            <label><input type="checkbox" id="extract-email" checked>  Email (Outlook)</label>
                            <span id="email-status" class="no-data">Requires authentication</span>
                        </div>
                        <div class="data-metric">
                            <label><input type="checkbox" id="extract-files" checked>  OneDrive Files</label>
                            <span id="files-status" class="no-data">Requires authentication</span>
                        </div>
                        <div class="data-metric">
                            <label><input type="checkbox" id="extract-teams" checked>  Teams Messages</label>
                            <span id="teams-status" class="no-data">Requires authentication</span>
                        </div>
                        <div class="data-metric">
                            <label><input type="checkbox" id="extract-calendar" checked>  Calendar Events</label>
                            <span id="calendar-status" class="no-data">Requires authentication</span>
                        </div>
                    </div>
                    
                    <button class="btn" onclick="startAuthentication()">Start Authentication Process</button>
                </div>
                
                <div class="card">
                    <h3>Authenticated Users - Real Data Counts</h3>
                    <div id="authenticated-users">
                        <p class="no-data">No users authenticated yet. Add a user above to begin.</p>
                    </div>
                </div>
            </div>
            
            <!-- ANALYSIS TAB -->
            <div id="analysis" class="view">
                <!-- User selector -->
                <div style="margin-bottom: 20px;">
                    <select id="analysis-user" onchange="loadUserHistory()" style="width: 100%; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px;">
                        <option value="">Select user to analyze...</option>
                    </select>
                </div>
                
                <!-- Analysis container -->
                <div class="analysis-container">
                    <!-- Chat History Sidebar -->
                    <div class="chat-history">
                        <h4> Chat History</h4>
                        <div id="history-list">
                            <p style="color: #9ca3af; text-align: center; margin-top: 20px;">Select a user to see history</p>
                        </div>
                    </div>
                    
                    <!-- Main Chat Area -->
                    <div class="chat-main">
                        <div class="chat-window" id="chat-window">
                            <div style="text-align: center; color: #9ca3af; margin-top: 50px;">
                                Select a user and data sources to begin analysis
                            </div>
                        </div>
                        
                        <!-- Source Filters -->
                        <div class="source-filters">
                            <h4>Select Data Sources to Query:</h4>
                            <div class="filter-buttons">
                                <button class="filter-btn active" onclick="selectAllSources()"> All Sources</button>
                                <button class="filter-btn active" id="filter-email" onclick="toggleSource('email')"> Email</button>
                                <button class="filter-btn active" id="filter-files" onclick="toggleSource('files')"> OneDrive</button>
                                <button class="filter-btn active" id="filter-teams" onclick="toggleSource('teams')"> Teams</button>
                                <button class="filter-btn active" id="filter-calendar" onclick="toggleSource('calendar')"> Calendar</button>
                            </div>
                        </div>
                        
                        <div class="input-area">
                            <input type="text" id="question-input" placeholder="Ask a question about the selected data sources...">
                            <button class="btn" onclick="sendQuestion()">Send</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Other tabs -->
            <div id="executive" class="view"><div class="card"><h3>Executive Summary</h3></div></div>
            <div id="behavioral" class="view"><div class="card"><h3>Behavioral Analysis</h3></div></div>
            <div id="team" class="view"><div class="card"><h3>Team Dynamics</h3></div></div>
            <div id="risk" class="view"><div class="card"><h3>Risk Assessment</h3></div></div>
            <div id="predictions" class="view"><div class="card"><h3>Predictions</h3></div></div>
            <div id="recommendations" class="view"><div class="card"><h3>Recommendations</h3></div></div>
            <div id="ontology" class="view"><div class="card"><h3>Fourth Ontology</h3></div></div>
            <div id="processes" class="view"><div class="card"><h3>Processes</h3></div></div>
            <div id="settings" class="view"><div class="card"><h3>Settings</h3></div></div>
        </div>
    </div>
    
    <script>
        let selectedSources = ['email', 'files', 'teams', 'calendar'];
        let currentUser = null;
        
        // Navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', function() {
                document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
                document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
                this.classList.add('active');
                document.getElementById(this.getAttribute('data-view')).classList.add('active');
                document.getElementById('page-title').textContent = this.textContent.substring(2);
                
                if (this.getAttribute('data-view') === 'integration') {
                    loadAuthenticatedUsers();
                }
            });
        });
        
        // Integration functions
        async function startAuthentication() {
            const email = document.getElementById('user-email').value;
            if (!email) {
                alert('Please enter a user email address');
                return;
            }
            
            const scopes = [];
            if (document.getElementById('extract-email').checked) scopes.push('Mail.Read');
            if (document.getElementById('extract-files').checked) scopes.push('Files.Read.All');
            if (document.getElementById('extract-teams').checked) scopes.push('Chat.Read');
            if (document.getElementById('extract-calendar').checked) scopes.push('Calendars.Read');
            
            const response = await fetch('/api/start-auth', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({email, scopes})
            });
            
            const result = await response.json();
            if (result.auth_url) {
                alert('Opening Microsoft login. User must sign in and approve access.');
                window.open(result.auth_url, '_blank');
            }
        }
        
        async function loadAuthenticatedUsers() {
            const response = await fetch('/api/authenticated-users');
            const data = await response.json();
            
            const container = document.getElementById('authenticated-users');
            const select = document.getElementById('analysis-user');
            
            if (data.users.length === 0) {
                container.innerHTML = '<p class="no-data">No authenticated users yet</p>';
                return;
            }
            
            container.innerHTML = '';
            select.innerHTML = '<option value="">Select user...</option>';
            
            data.users.forEach(user => {
                container.innerHTML += `
                    <div class="user-data-card authenticated">
                        <h4>${user.email}</h4>
                        <div style="margin: 15px 0;">
                            <div> Emails: <span class="real-count">${user.emails}</span></div>
                            <div> Files: <span class="real-count">${user.files}</span></div>
                            <div> Teams: <span class="real-count">${user.teams}</span></div>
                            <div> Calendar: <span class="real-count">${user.calendar}</span></div>
                        </div>
                        <button class="btn btn-success" onclick="extractData('${user.email}')">Extract Latest Data</button>
                    </div>
                `;
                
                select.innerHTML += `<option value="${user.email}">${user.email}</option>`;
            });
        }
        
        // Analysis functions
        function selectAllSources() {
            selectedSources = ['email', 'files', 'teams', 'calendar'];
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.add('active'));
        }
        
        function toggleSource(source) {
            const btn = document.getElementById('filter-' + source);
            
            if (selectedSources.includes(source)) {
                selectedSources = selectedSources.filter(s => s !== source);
                btn.classList.remove('active');
            } else {
                selectedSources.push(source);
                btn.classList.add('active');
            }
        }
        
        async function loadUserHistory() {
            currentUser = document.getElementById('analysis-user').value;
            if (!currentUser) return;
            
            document.getElementById('chat-window').innerHTML = '<div style="text-align: center; color: #9ca3af;">Ready to analyze ' + currentUser + '</div>';
            document.getElementById('history-list').innerHTML = '<div class="history-item">New conversation</div>';
        }
        
        async function sendQuestion() {
            const question = document.getElementById('question-input').value;
            if (!question || !currentUser) return;
            
            // Add to chat window
            const chatWindow = document.getElementById('chat-window');
            chatWindow.innerHTML += `
                <div class="message user">
                    <div>${question}</div>
                    <div style="font-size: 11px; color: #9ca3af; margin-top: 5px;">Sources: ${selectedSources.join(', ')}</div>
                </div>
                <div class="message assistant">
                    <div>Analyzing ${currentUser}'s ${selectedSources.join(', ')} data...</div>
                </div>
            `;
            
            document.getElementById('question-input').value = '';
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }
    </script>
</body>
</html>
    '''

@app.post("/api/start-auth")
async def start_auth(request: dict):
    """Start real OAuth flow"""
    email = request.get("email")
    scopes = request.get("scopes", ["User.Read"])
    
    state = str(uuid.uuid4())
    pending_auth[state] = {"email": email, "scopes": scopes}
    
    scope_string = " ".join(scopes + ["User.Read", "offline_access"])
    auth_url = (
        f"{AUTHORITY}/oauth2/v2.0/authorize?"
        f"client_id={CLIENT_ID}&"
        f"response_type=code&"
        f"redirect_uri={REDIRECT_URI}&"
        f"scope={scope_string}&"
        f"state={state}&"
        f"prompt=consent"
    )
    
    return {"auth_url": auth_url}

@app.get("/api/authenticated-users")
async def get_authenticated_users():
    """Return real authenticated users"""
    users = []
    for email, counts in real_data_counts.items():
        users.append({
            "email": email,
            "emails": counts.get("emails", 0),
            "files": counts.get("files", 0),
            "teams": counts.get("teams", 0),
            "calendar": counts.get("calendar", 0)
        })
    return {"users": users}
