"""
BDT Platform - Fixed Production Version
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="BDT Platform",
    version="2.0.0",
    docs_url="/api/docs"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import services with error handling
try:
    from graph_service import graph_service
    GRAPH_AVAILABLE = True
except:
    GRAPH_AVAILABLE = False
    
try:
    from dashboard_service import dashboard_service
    DASHBOARD_AVAILABLE = True
except:
    DASHBOARD_AVAILABLE = False

try:
    from cache_service import cache
    CACHE_AVAILABLE = True
except:
    CACHE_AVAILABLE = False

try:
    from tasks import celery_app
    TASKS_AVAILABLE = True
except:
    TASKS_AVAILABLE = False

# Main dashboard route - PROPERLY INDENTED
@app.get("/", response_class=HTMLResponse)
async def root():
    return """<!DOCTYPE html>
<html>
<head>
    <title>BDT Platform Production</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { 
            max-width: 1200px; 
            margin: auto; 
            background: white; 
            padding: 40px; 
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 { color: #1e3a8a; }
        .status { 
            background: #10b981; 
            color: white; 
            padding: 10px 20px; 
            border-radius: 8px; 
            display: inline-block;
            margin: 20px 0;
        }
        .services {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .service {
            padding: 20px;
            background: #f3f4f6;
            border-radius: 8px;
            text-align: center;
        }
        .service.ready { background: #d1fae5; }
        .service.error { background: #fee2e2; }
        button {
            background: #1e3a8a;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            margin: 5px;
            font-size: 16px;
        }
        button:hover { background: #1e40af; }
    </style>
</head>
<body>
    <div class="container">
        <h1> BDT Platform v2.0 - Production</h1>
        <div class="status"> System Online</div>
        
        <h2>Service Status:</h2>
        <div class="services">
            <div class="service ready">
                <h3>Core API</h3>
                <p> Running</p>
            </div>
            <div class="service">
                <h3>Graph Service</h3>
                <p>Loading...</p>
            </div>
            <div class="service">
                <h3>Dashboard Service</h3>
                <p>Loading...</p>
            </div>
            <div class="service">
                <h3>Cache Service</h3>
                <p>Loading...</p>
            </div>
        </div>
        
        <h2>Quick Actions:</h2>
        <div>
            <button onclick="location.href='/health'">Health Check</button>
            <button onclick="location.href='/api/docs'">API Documentation</button>
            <button onclick="testDemo()">Test Demo Login</button>
            <button onclick="location.href='/api/v1/data?source=email'">Email Data</button>
        </div>
        
        <h2>Demo Account:</h2>
        <p>Email: demo@bdt-platform.com</p>
        <div id="response"></div>
    </div>
    
    <script>
        async function testDemo() {
            const res = await fetch('/api/auth/demo-login', {method: 'POST'});
            const data = await res.json();
            document.getElementById('response').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
        }
    </script>
</body>
</html>"""

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "graph": GRAPH_AVAILABLE,
            "dashboard": DASHBOARD_AVAILABLE,
            "cache": CACHE_AVAILABLE,
            "tasks": TASKS_AVAILABLE
        }
    }

@app.post("/api/auth/demo-login")
async def demo_login():
    return {
        "access_token": "demo-token-123456",
        "token_type": "bearer",
        "user": "demo@bdt-platform.com"
    }

@app.get("/api/v1/data")
async def get_data(source: str = None):
    demo_data = {
        "email": [
            {"id": 1, "content": "Meeting tomorrow at 2pm", "source": "email"},
            {"id": 2, "content": "Project update required", "source": "email"}
        ],
        "calendar": [
            {"id": 3, "content": "Q4 Planning Session", "source": "calendar"}
        ],
        "document": [
            {"id": 4, "content": "Quarterly Report", "source": "document"}
        ]
    }
    
    if source and source in demo_data:
        return {"source": source, "data": demo_data[source]}
    return {"data": demo_data}

# Dashboard endpoints
@app.get("/api/dashboard/{view}")
async def get_dashboard(view: str):
    return {
        "view": view,
        "message": f"Dashboard {view} endpoint working",
        "data": "Full data would be here when services are connected"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
