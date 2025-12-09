from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import msal
import os
import json
import uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Microsoft OAuth Configuration
CLIENT_ID = "98f8baa3-5127-4ef1-83d7-cdec8b9cb791"
CLIENT_SECRET = "mpX8Q~mrLGi-dcQF-kpNGiC2ZkiXOB0Bi6I_BbCq"
TENANT_ID = "ae228585-fff9-4624-8d69-77facf28d996"
REDIRECT_URI = "https://bdt-platform-bfc3g7g6eabbf2a4.eastus2-01.azurewebsites.net/auth/callback"

# MSAL setup
msal_app = msal.ConfidentialClientApplication(
    CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{TENANT_ID}",
    client_credential=CLIENT_SECRET
)

# Store user tokens (use database in production)
user_tokens = {}

@app.get("/", response_class=HTMLResponse)
async def root():
    return '''
    <html>
    <head><title>BDT Platform - User Data Integration</title></head>
    <style>
        body { font-family: Arial; padding: 40px; }
        .card { border: 1px solid #ddd; padding: 20px; margin: 20px 0; border-radius: 8px; }
        .btn { background: #0078d4; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
    </style>
    <body>
        <h1>BDT Platform - Data Integration</h1>
        
        <div class="card">
            <h2>Connect Your Microsoft Account</h2>
            <p>Authorize access to analyze your Microsoft 365 data:</p>
            <ul>
                <li> Emails</li>
                <li> OneDrive Files</li>  
                <li> Teams Messages</li>
                <li> Calendar Events</li>
            </ul>
            <a href="/auth/login" class="btn">Sign in with Microsoft</a>
        </div>
        
        <div class="card">
            <h2>For Managers/Admins</h2>
            <p>To analyze a departed employee's data (like Tyler Helwig):</p>
            <ol>
                <li>Sign in with YOUR admin account</li>
                <li>Grant permissions to access organizational data</li>
                <li>Select the user to analyze</li>
            </ol>
            <a href="/auth/admin-login" class="btn">Admin Sign In</a>
        </div>
    </body>
    </html>
    '''

@app.get("/auth/login")
async def login():
    """Start OAuth flow for regular users"""
    auth_url = msal_app.get_authorization_request_url(
        scopes=["User.Read", "Mail.Read", "Files.Read", "Chat.Read", "Calendars.Read"],
        state=str(uuid.uuid4()),
        redirect_uri=REDIRECT_URI
    )
    return RedirectResponse(auth_url)

@app.get("/auth/admin-login")  
async def admin_login():
    """Start OAuth flow for admins to access other users"""
    auth_url = msal_app.get_authorization_request_url(
        scopes=["User.Read.All", "Mail.Read", "Files.Read.All", "Chat.Read.All"],
        state="admin_" + str(uuid.uuid4()),
        redirect_uri=REDIRECT_URI
    )
    return RedirectResponse(auth_url)

@app.get("/auth/callback")
async def auth_callback(code: str, state: str):
    """Handle OAuth callback"""
    try:
        # Exchange code for token
        result = msal_app.acquire_token_by_authorization_code(
            code,
            scopes=["User.Read", "Mail.Read", "Files.Read"],
            redirect_uri=REDIRECT_URI
        )
        
        if "access_token" in result:
            # Store token
            user_id = result.get("id_token_claims", {}).get("oid", str(uuid.uuid4()))
            user_tokens[user_id] = result
            
            # Get user info
            import requests
            headers = {"Authorization": f"Bearer {result['access_token']}"}
            user_info = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers).json()
            
            return HTMLResponse(f'''
            <html>
            <body style="font-family: Arial; padding: 40px;">
                <h1> Successfully Connected!</h1>
                <p>Logged in as: <b>{user_info.get("displayName", "Unknown")}</b></p>
                <p>Email: {user_info.get("mail", "Unknown")}</p>
                
                <div style="margin-top: 30px;">
                    <h2>Now you can:</h2>
                    <button onclick="syncData()">Sync My Data</button>
                    <button onclick="selectUser()">Select User to Analyze (Admins)</button>
                </div>
                
                <script>
                function syncData() {{
                    fetch("/api/sync-user-data", {{
                        method: "POST",
                        headers: {{"Content-Type": "application/json"}},
                        body: JSON.stringify({{user_id: "{user_id}"}})
                    }}).then(r => r.json()).then(data => {{
                        alert("Synced: " + data.emails + " emails, " + data.files + " files");
                    }});
                }}
                
                function selectUser() {{
                    const email = prompt("Enter user email to analyze (e.g., tyler.helwig@airiam.com):");
                    if (email) {{
                        fetch("/api/sync-other-user", {{
                            method: "POST",
                            headers: {{"Content-Type": "application/json"}},
                            body: JSON.stringify({{admin_id: "{user_id}", target_email: email}})
                        }}).then(r => r.json()).then(data => {{
                            alert("Synced " + email + ": " + data.emails + " emails");
                        }});
                    }}
                }}
                </script>
            </body>
            </html>
            ''')
        else:
            raise HTTPException(status_code=400, detail=result.get("error_description"))
    except Exception as e:
        return HTMLResponse(f"<h1>Error</h1><p>{str(e)}</p>")

@app.post("/api/sync-user-data")
async def sync_user_data(request: dict):
    """Sync logged-in user's data"""
    user_id = request.get("user_id")
    token = user_tokens.get(user_id, {}).get("access_token")
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    import requests
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get emails
    emails_response = requests.get(
        "https://graph.microsoft.com/v1.0/me/messages?$top=100",
        headers=headers
    )
    emails = emails_response.json().get("value", []) if emails_response.status_code == 200 else []
    
    # Get files
    files_response = requests.get(
        "https://graph.microsoft.com/v1.0/me/drive/recent?$top=50",
        headers=headers
    )
    files = files_response.json().get("value", []) if files_response.status_code == 200 else []
    
    # Store in your databases (PostgreSQL, Azure AI Search, etc.)
    # ... your existing storage code ...
    
    return {"emails": len(emails), "files": len(files)}

@app.post("/api/sync-other-user")
async def sync_other_user(request: dict):
    """Admin syncing another user's data"""
    admin_id = request.get("admin_id")
    target_email = request.get("target_email")
    token = user_tokens.get(admin_id, {}).get("access_token")
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    import requests
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get target user's emails (requires admin permissions)
    emails_response = requests.get(
        f"https://graph.microsoft.com/v1.0/users/{target_email}/messages?$top=100",
        headers=headers
    )
    
    if emails_response.status_code == 200:
        emails = emails_response.json().get("value", [])
        # Store in databases...
        return {"emails": len(emails), "user": target_email}
    else:
        return {"error": "Insufficient permissions or user not found"}
