from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def root():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Behavioral Digital Twin Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, Arial, sans-serif; background: #f0f2f5; }
        
        /* Header */
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px 40px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header h1 { font-size: 28px; font-weight: 300; }
        .header .subtitle { opacity: 0.9; margin-top: 5px; }
        
        /* Tab Navigation */
        .tab-nav { background: white; padding: 0 40px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-bottom: 1px solid #e5e7eb; }
        .tab-nav ul { list-style: none; display: flex; margin: 0; padding: 0; }
        .tab-nav li { margin-right: 30px; }
        .tab-nav a { display: block; padding: 20px 0; color: #4b5563; text-decoration: none; border-bottom: 3px solid transparent; transition: 0.2s; }
        .tab-nav a:hover { color: #1f2937; }
        .tab-nav a.active { color: #7c3aed; border-bottom-color: #7c3aed; }
        
        /* Main Content */
        .content { padding: 30px 40px; }
        .view { display: none; }
        .view.active { display: block; }
        
        /* Cards */
        .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .card h2 { font-size: 20px; margin-bottom: 20px; color: #1f2937; }
        .card h3 { font-size: 16px; margin-bottom: 15px; color: #4b5563; }
        
        /* Grid Layouts */
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
        .metric-card { padding: 20px; background: linear-gradient(135deg, #f3f4f6, #ffffff); border-radius: 8px; border-left: 4px solid #7c3aed; }
        .metric-value { font-size: 32px; font-weight: bold; color: #1f2937; }
        .metric-label { color: #6b7280; margin-top: 5px; }
        
        /* Analysis Sections */
        .analysis-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .insight-card { background: #fafafa; padding: 15px; border-radius: 8px; margin: 10px 0; }
        .relationship-node { display: inline-block; padding: 8px 16px; background: #e0e7ff; border-radius: 20px; margin: 5px; }
        .process-flow { display: flex; align-items: center; margin: 15px 0; }
        .process-step { padding: 10px 20px; background: #f3f4f6; border-radius: 6px; margin-right: 10px; }
        .process-arrow { color: #9ca3af; margin-right: 10px; }
        
        /* Chat Interface (Analysis Tab) */
        .chat-container { display: flex; gap: 20px; height: 600px; }
        .chat-history { width: 300px; background: white; border-radius: 8px; padding: 20px; overflow-y: auto; }
        .chat-main { flex: 1; display: flex; flex-direction: column; }
        .chat-window { background: white; border-radius: 8px; padding: 20px; flex: 1; overflow-y: auto; }
        .chat-input-area { background: white; border-radius: 8px; padding: 15px; margin-top: 20px; }
        
        /* Fourth Ontology Specific */
        .ontology-quadrant { padding: 20px; background: white; border-radius: 8px; text-align: center; }
        .cultural-dimension { padding: 15px; margin: 10px 0; background: linear-gradient(90deg, #fef3c7, #fde68a); border-radius: 8px; }
        
        /* Integration Section (Bottom) */
        .integration-bar { position: fixed; bottom: 0; left: 0; right: 0; background: white; border-top: 1px solid #e5e7eb; padding: 15px 40px; display: flex; justify-content: space-between; align-items: center; }
        .integration-status { display: flex; gap: 20px; }
        .source-badge { padding: 6px 12px; background: #10b981; color: white; border-radius: 20px; font-size: 12px; }
        .source-badge.pending { background: #f59e0b; }
        
        /* Buttons */
        .btn { padding: 10px 20px; background: #7c3aed; color: white; border: none; border-radius: 6px; cursor: pointer; }
        .btn:hover { background: #6d28d9; }
        .btn-secondary { background: #6b7280; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Behavioral Digital Twin Platform</h1>
        <div class="subtitle">Comprehensive Analysis & Intelligence System</div>
    </div>
    
    <nav class="tab-nav">
        <ul>
            <li><a href="#" class="tab-link active" data-tab="overview">Overview</a></li>
            <li><a href="#" class="tab-link" data-tab="knowledge">Knowledge</a></li>
            <li><a href="#" class="tab-link" data-tab="processes">Processes & Procedures</a></li>
            <li><a href="#" class="tab-link" data-tab="calendar">Calendar & Triggers</a></li>
            <li><a href="#" class="tab-link" data-tab="relationships">Relationships</a></li>
            <li><a href="#" class="tab-link" data-tab="rhythm">Rhythm</a></li>
            <li><a href="#" class="tab-link" data-tab="persona">Persona & Culture</a></li>
            <li><a href="#" class="tab-link" data-tab="tools">Tools</a></li>
            <li><a href="#" class="tab-link" data-tab="ontology">Fourth Ontology</a></li>
            <li><a href="#" class="tab-link" data-tab="analysis">AI Analysis</a></li>
        </ul>
    </nav>
    
    <div class="content">
        <!-- Overview Tab -->
        <div class="view active" id="overview">
            <div class="card">
                <h2>Behavioral Digital Twin Overview</h2>
                <div class="metrics-grid" id="overview-metrics">
                    <!-- Populated from ingested data -->
                </div>
            </div>
            
            <div class="analysis-grid">
                <div class="card">
                    <h3>Recent Activity Patterns</h3>
                    <div id="activity-patterns"></div>
                </div>
                <div class="card">
                    <h3>Key Insights</h3>
                    <div id="key-insights"></div>
                </div>
            </div>
        </div>
        
        <!-- Knowledge Tab -->
        <div class="view" id="knowledge">
            <div class="card">
                <h2>Knowledge Map</h2>
                <div id="knowledge-domains"></div>
            </div>
            <div class="card">
                <h3>Unique Expertise Areas</h3>
                <div id="expertise-areas"></div>
            </div>
        </div>
        
        <!-- Processes & Procedures Tab -->
        <div class="view" id="processes">
            <div class="card">
                <h2>Documented Processes</h2>
                <div id="process-list"></div>
            </div>
            <div class="card">
                <h2>Standard Procedures</h2>
                <div id="procedures-list"></div>
            </div>
        </div>
        
        <!-- Calendar & Triggers Tab -->
        <div class="view" id="calendar">
            <div class="card">
                <h2>Calendar Patterns</h2>
                <div id="calendar-patterns"></div>
            </div>
            <div class="card">
                <h2>Event Triggers</h2>
                <div id="event-triggers"></div>
            </div>
        </div>
        
        <!-- Relationships Tab -->
        <div class="view" id="relationships">
            <div class="card">
                <h2>Relationship Network</h2>
                <div id="relationship-graph"></div>
            </div>
            <div class="card">
                <h2>Key Collaborators</h2>
                <div id="collaborators-list"></div>
            </div>
        </div>
        
        <!-- Rhythm Tab -->
        <div class="view" id="rhythm">
            <div class="card">
                <h2>Work Rhythm Analysis</h2>
                <div id="rhythm-patterns"></div>
            </div>
        </div>
        
        <!-- Persona & Culture Tab -->
        <div class="view" id="persona">
            <div class="card">
                <h2>Behavioral Persona</h2>
                <div id="persona-profile"></div>
            </div>
            <div class="card">
                <h2>Cultural Indicators</h2>
                <div id="cultural-indicators"></div>
            </div>
        </div>
        
        <!-- Tools Tab -->
        <div class="view" id="tools">
            <div class="card">
                <h2>Tools & Technologies Used</h2>
                <div id="tools-list"></div>
            </div>
        </div>
        
        <!-- Fourth Ontology Tab -->
        <div class="view" id="ontology">
            <div class="card">
                <h2>Fourth Ontology Analysis</h2>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div class="ontology-quadrant">
                        <h3>Individual Values</h3>
                        <div id="individual-values"></div>
                    </div>
                    <div class="ontology-quadrant">
                        <h3>Collective Values</h3>
                        <div id="collective-values"></div>
                    </div>
                    <div class="ontology-quadrant">
                        <h3>External Expression</h3>
                        <div id="external-expression"></div>
                    </div>
                    <div class="ontology-quadrant">
                        <h3>Internal Beliefs</h3>
                        <div id="internal-beliefs"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- AI Analysis Tab (Chat) -->
        <div class="view" id="analysis">
            <div class="chat-container">
                <div class="chat-history">
                    <h3>Chat History</h3>
                    <div id="history-list"></div>
                </div>
                <div class="chat-main">
                    <div class="chat-window" id="chat-window"></div>
                    <div class="chat-input-area">
                        <div style="display: flex; gap: 10px;">
                            <input type="text" id="chat-input" placeholder="Ask about the behavioral data..." style="flex: 1; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px;">
                            <button class="btn" onclick="sendMessage()">Send</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Integration Bar (Bottom) -->
    <div class="integration-bar">
        <div class="integration-status">
            <span>Data Sources:</span>
            <span class="source-badge" id="email-badge"> 0 Emails</span>
            <span class="source-badge" id="files-badge"> 0 Files</span>
            <span class="source-badge" id="teams-badge"> 0 Teams</span>
            <span class="source-badge" id="calendar-badge"> 0 Events</span>
        </div>
        <button class="btn btn-secondary" onclick="openIntegrationModal()">Configure Integration</button>
    </div>
    
    <script>
        // Tab navigation
        document.querySelectorAll('.tab-link').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                document.querySelectorAll('.tab-link').forEach(l => l.classList.remove('active'));
                document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
                this.classList.add('active');
                document.getElementById(this.dataset.tab).classList.add('active');
                
                // Load data for this tab
                loadTabData(this.dataset.tab);
            });
        });
        
        async function loadTabData(tab) {
            // Load preprocessed data for each tab
            const response = await fetch(`/api/bdt-data/${tab}`);
            const data = await response.json();
            
            // Populate the tab with data
            populateTab(tab, data);
        }
        
        function populateTab(tab, data) {
            // Implementation for each tab's data population
            switch(tab) {
                case 'knowledge':
                    // Populate knowledge domains
                    break;
                case 'processes':
                    // Populate processes
                    break;
                // etc...
            }
        }
        
        // Load initial data
        loadTabData('overview');
    </script>
</body>
</html>
    '''
