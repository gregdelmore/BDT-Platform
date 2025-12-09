"""
REAL DATA SYNC - Tyler Helwig's Microsoft 365
"""
import os
import json
import logging
from datetime import datetime, timedelta
import requests
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="BDT Platform - REAL DATA", version="PRODUCTION")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= MICROSOFT GRAPH CONNECTION =============
TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "ae228585-fff9-4624-8d69-77facf28d996")
CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "98f8baa3-5127-4ef1-83d7-cdec8b9cb791")
CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "YOUR_AZURE_SECRET_HERE")

def get_access_token():
    """Get Microsoft Graph access token"""
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        logger.error(f"Token error: {response.text}")
        return None

def get_tyler_emails(token, count=100):
    """Get Tyler's REAL emails"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get last 30 days of emails
    date_filter = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    url = f"https://graph.microsoft.com/v1.0/users/tyler.helwig@airiam.com/messages"
    params = {
        "$filter": f"receivedDateTime ge {date_filter}",
        "$select": "subject,from,bodyPreview,receivedDateTime,hasAttachments",
        "$orderby": "receivedDateTime desc",
        "$top": count
    }
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get("value", [])
    else:
        logger.error(f"Email error: {response.text}")
        return []

def get_tyler_files(token, count=100):
    """Get Tyler's OneDrive files"""
    headers = {"Authorization": f"Bearer {token}"}
    
    url = f"https://graph.microsoft.com/v1.0/users/tyler.helwig@airiam.com/drive/recent"
    params = {"$top": count}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get("value", [])
    else:
        logger.error(f"Files error: {response.text}")
        return []

def get_tyler_teams_messages(token, count=50):
    """Get Tyler's Teams messages"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get Tyler's chats
    url = f"https://graph.microsoft.com/v1.0/users/tyler.helwig@airiam.com/chats"
    params = {"$top": 10}
    
    response = requests.get(url, headers=headers, params=params)
    messages = []
    
    if response.status_code == 200:
        chats = response.json().get("value", [])
        # Get messages from each chat
        for chat in chats[:5]:  # Top 5 chats
            chat_id = chat["id"]
            msg_url = f"https://graph.microsoft.com/v1.0/chats/{chat_id}/messages"
            msg_params = {"$top": 10}
            msg_response = requests.get(msg_url, headers=headers, params=msg_params)
            if msg_response.status_code == 200:
                messages.extend(msg_response.json().get("value", []))
    
    return messages

def get_tyler_calendar(token, days=30):
    """Get Tyler's calendar events"""
    headers = {"Authorization": f"Bearer {token}"}
    
    start_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    end_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    
    url = f"https://graph.microsoft.com/v1.0/users/tyler.helwig@airiam.com/calendar/events"
    params = {
        "$filter": f"start/dateTime ge '{end_date}' and start/dateTime le '{start_date}'",
        "$orderby": "start/dateTime desc",
        "$top": 50
    }
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get("value", [])
    else:
        logger.error(f"Calendar error: {response.text}")
        return []

# ============= DATABASE CONNECTIONS =============
import psycopg2
from psycopg2.pool import SimpleConnectionPool

DB_URL = os.getenv("DATABASE_URL", "postgresql://btadmin:PumpkinPi14$@bdt-platform-db.postgres.database.azure.com:5432/bdtplatform?sslmode=require")

try:
    pg_pool = SimpleConnectionPool(1, 10, DB_URL)
    logger.info(" PostgreSQL connected")
except Exception as e:
    logger.error(f"PostgreSQL error: {e}")
    pg_pool = None

# ============= API ENDPOINTS =============

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("dashboard.html", "r") as f:
        return f.read()

@app.post("/api/tyler/sync")
async def sync_tyler_real(request: dict):
    """Sync Tyler's REAL Microsoft 365 data"""
    services = request.get("services", [])
    
    # Get Microsoft Graph token
    token = get_access_token()
    if not token:
        return {"error": "Failed to authenticate with Microsoft", "emails": 0, "files": 0}
    
    results = {
        "emails": 0,
        "files": 0,
        "teams": 0,
        "calendar": 0,
        "total_imported": 0
    }
    
    # Import REAL emails
    if "email" in services:
        emails = get_tyler_emails(token, 100)
        results["emails"] = len(emails)
        
        # Store in PostgreSQL
        if pg_pool and emails:
            conn = pg_pool.getconn()
            cur = conn.cursor()
            for email in emails:
                try:
                    cur.execute("""
                        INSERT INTO tyler_data (data_type, subject, content, metadata)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        "email",
                        email.get("subject", ""),
                        email.get("bodyPreview", ""),
                        json.dumps(email)
                    ))
                except Exception as e:
                    logger.error(f"Insert error: {e}")
            conn.commit()
            pg_pool.putconn(conn)
    
    # Import REAL files
    if "onedrive" in services:
        files = get_tyler_files(token, 100)
        results["files"] = len(files)
        
        # Store in PostgreSQL
        if pg_pool and files:
            conn = pg_pool.getconn()
            cur = conn.cursor()
            for file in files:
                try:
                    cur.execute("""
                        INSERT INTO tyler_data (data_type, subject, content, metadata)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        "file",
                        file.get("name", ""),
                        f"File: {file.get('name', '')} - Modified: {file.get('lastModifiedDateTime', '')}",
                        json.dumps(file)
                    ))
                except Exception as e:
                    logger.error(f"Insert error: {e}")
            conn.commit()
            pg_pool.putconn(conn)
    
    # Import REAL Teams messages
    if "teams" in services:
        messages = get_tyler_teams_messages(token, 50)
        results["teams"] = len(messages)
        
        # Store in PostgreSQL
        if pg_pool and messages:
            conn = pg_pool.getconn()
            cur = conn.cursor()
            for msg in messages:
                try:
                    cur.execute("""
                        INSERT INTO tyler_data (data_type, subject, content, metadata)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        "teams",
                        f"Teams: {msg.get('from', {}).get('user', {}).get('displayName', 'Unknown')}",
                        msg.get("body", {}).get("content", ""),
                        json.dumps(msg)
                    ))
                except Exception as e:
                    logger.error(f"Insert error: {e}")
            conn.commit()
            pg_pool.putconn(conn)
    
    # Import REAL calendar
    if "calendar" in services:
        events = get_tyler_calendar(token, 30)
        results["calendar"] = len(events)
        
        # Store in PostgreSQL
        if pg_pool and events:
            conn = pg_pool.getconn()
            cur = conn.cursor()
            for event in events:
                try:
                    cur.execute("""
                        INSERT INTO tyler_data (data_type, subject, content, metadata)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        "calendar",
                        event.get("subject", ""),
                        f"Meeting with: {', '.join([a.get('emailAddress', {}).get('name', '') for a in event.get('attendees', [])])}",
                        json.dumps(event)
                    ))
                except Exception as e:
                    logger.error(f"Insert error: {e}")
            conn.commit()
            pg_pool.putconn(conn)
    
    results["total_imported"] = sum([results["emails"], results["files"], results["teams"], results["calendar"]])
    
    return results

@app.get("/health")
async def health():
    return {
        "status": "operational",
        "database": pg_pool is not None,
        "microsoft_configured": bool(CLIENT_ID and CLIENT_SECRET)
    }

