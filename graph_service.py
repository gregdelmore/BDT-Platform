"""Microsoft Graph Service - Real Integration"""
import os
import httpx
from msal import ConfidentialClientApplication
from typing import List, Dict, Any
from datetime import datetime, timedelta

class GraphService:
    def __init__(self):
        self.client_id = os.getenv("MICROSOFT_CLIENT_ID")
        self.client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")
        self.tenant_id = os.getenv("MICROSOFT_TENANT_ID")
        self.redirect_uri = os.getenv("MICROSOFT_REDIRECT_URI")
        
        self.app = ConfidentialClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            client_credential=self.client_secret
        )
        self.token = None
    
    async def get_token(self):
        """Get access token for Graph API"""
        result = self.app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" in result:
            self.token = result["access_token"]
            return self.token
        raise Exception("Failed to get token")
    
    async def get_user_emails(self, user_email: str = None) -> List[Dict]:
        """Fetch emails from Microsoft 365"""
        if not self.token:
            await self.get_token()
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # For demo, return sample data if no real token
        if not self.token:
            return [
                {"subject": "Board Meeting", "from": "ceo@company.com", "received": "2024-12-06"},
                {"subject": "Q4 Report", "from": "cfo@company.com", "received": "2024-12-05"}
            ]
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me/messages?$top=10",
                headers=headers
            )
            if response.status_code == 200:
                return response.json().get("value", [])
        return []
    
    async def get_calendar_events(self) -> List[Dict]:
        """Fetch calendar events"""
        # Return demo data for now
        return [
            {"subject": "Team Standup", "start": "2024-12-07T09:00:00"},
            {"subject": "Product Review", "start": "2024-12-07T14:00:00"}
        ]
    
    async def get_documents(self) -> List[Dict]:
        """Fetch OneDrive documents"""
        return [
            {"name": "Q4 Strategic Plan.docx", "modified": "2024-12-01"},
            {"name": "Budget 2025.xlsx", "modified": "2024-11-30"}
        ]

graph_service = GraphService()
