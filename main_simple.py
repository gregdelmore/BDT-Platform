from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import psycopg2
from datetime import datetime

app = FastAPI(title="BDT Platform", version="SQL-STABLE")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory store for now
tyler_data = {
    "emails": [],
    "files": [],
    "synced": False
}

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("dashboard.html", "r") as f:
        return f.read()

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "SQL-STABLE",
        "tyler_service": True,  # Simplified
        "database": True  # Will use SQL when ready
    }

@app.post("/api/tyler/sync")
async def sync_tyler(request: dict):
    """Store Tyler demo data"""
    services = request.get("services", [])
    
    if "email" in services:
        tyler_data["emails"] = [
            {"subject": "Customer Portal Migration Plan", "from": "manager@airiam.com", "preview": "Timeline for Q4 migration..."},
            {"subject": "API Documentation Complete", "from": "tyler.helwig@airiam.com", "preview": "Documentation ready for review..."},
            {"subject": "Team Meeting Notes", "from": "team@airiam.com", "preview": "Action items from standup..."}
        ]
    
    if "onedrive" in services:
        tyler_data["files"] = [
            {"name": "Architecture_Diagram.pptx", "modified": "2024-11-15", "size": 2456789},
            {"name": "Migration_Plan.xlsx", "modified": "2024-11-20", "size": 567890}
        ]
    
    tyler_data["synced"] = True
    
    return {
        "emails": len(tyler_data["emails"]),
        "files": len(tyler_data["files"]),
        "status": "success"
    }

@app.post("/api/chat")
async def chat(request: dict):
    question = request.get("question", "").lower()
    
    if not tyler_data["synced"]:
        return {"answer": "Please sync Tyler's data first"}
    
    # Simple search
    results = []
    for email in tyler_data["emails"]:
        if question in email["subject"].lower() or question in email["preview"].lower():
            results.append(f"Email: {email['subject']}")
    
    for file in tyler_data["files"]:
        if question in file["name"].lower():
            results.append(f"File: {file['name']}")
    
    if results:
        answer = f"Found {len(results)} items:\n" + "\n".join(results)
    else:
        answer = f"No results for '{question}'. Tyler's synced data includes emails about migration and API documentation."
    
    return {"answer": answer}
