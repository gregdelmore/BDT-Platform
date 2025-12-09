"""
Multi-Service Integration Configuration
Supports individual user authentication for each service
"""
import os
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import httpx
from msal import PublicClientApplication, ConfidentialClientApplication

logger = logging.getLogger(__name__)

@dataclass
class UserCredentials:
    """Store user credentials for each service"""
    email: str
    password: str
    requires_2fa: bool = True
    services: Dict[str, bool] = None
    
    def __post_init__(self):
        if self.services is None:
            self.services = {
                "email": False,
                "calendar": False,
                "onedrive": False,
                "teams": False,
                "sharepoint": False
            }

class IntegrationManager:
    """Manage all integrations for multiple users"""
    
    def __init__(self):
        # Your Azure app registration
        self.client_id = "98f8baa3-5127-4ef1-83d7-cdec8b9cb791"
        self.client_secret = "mpX8Q~mrLGi-dcQF-kpNGiC2ZkiXOB0Bi6I_BbCq"
        self.tenant_id = "ae228585-fff9-4624-8d69-77facf28d996"
        self.redirect_uri = "https://bdt-platform-bfc3g7g6eabbf2a4.eastus2-01.azurewebsites.net/auth/callback"
        
        # Store configured users
        self.users = {}
        
        # Tyler's configuration
        self.add_user(
            "tyler.helwig@airiam.com",
            "B14h10vior$",
            requires_2fa=True
        )
        
        # Service endpoints
        self.graph_base = "https://graph.microsoft.com/v1.0"
        
    def add_user(self, email: str, password: str, requires_2fa: bool = False):
        """Add a user for data extraction"""
        self.users[email] = UserCredentials(
            email=email,
            password=password,
            requires_2fa=requires_2fa
        )
        logger.info(f"Added user configuration for {email}")
    
    async def authenticate_user(self, email: str) -> Dict:
        """Authenticate a specific user"""
        if email not in self.users:
            return {"error": f"User {email} not configured"}
        
        user = self.users[email]
        
        # For users with passwords, we need delegated auth
        # This would typically use OAuth2 Resource Owner Password flow
        # But Microsoft is deprecating this, so we'll use device flow
        
        app = PublicClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}"
        )
        
        # Device flow for 2FA support
        flow = app.initiate_device_flow(
            scopes=[
                "Mail.Read",
                "Calendar.Read", 
                "Files.Read.All",
                "Chat.Read",
                "ChannelMessage.Read.All",
                "User.Read"
            ]
        )
        
        if "user_code" in flow:
            logger.info(f"Device auth initiated for {email}")
            logger.info(f"User code: {flow['user_code']}")
            logger.info(f"URL: {flow['verification_uri']}")
            
            # In production, you'd show this to the user
            # For now, return the flow info
            return {
                "status": "pending_2fa",
                "user_code": flow["user_code"],
                "verification_url": flow["verification_uri"],
                "message": f"Go to {flow['verification_uri']} and enter code: {flow['user_code']}"
            }
        
        return {"error": "Failed to initiate authentication"}
    
    async def get_user_emails(self, email: str, limit: int = 100) -> List[Dict]:
        """Get emails for specific user"""
        logger.info(f"Fetching emails for {email}")
        
        # For Tyler, we'll use application permissions to read his mailbox
        app = ConfidentialClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            client_credential=self.client_secret
        )
        
        result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        
        if "access_token" not in result:
            return []
        
        headers = {"Authorization": f"Bearer {result['access_token']}"}
        emails = []
        
        async with httpx.AsyncClient() as client:
            try:
                # Get Tyler's emails specifically
                response = await client.get(
                    f"{self.graph_base}/users/{email}/messages?$top={limit}&$select=subject,from,receivedDateTime,bodyPreview,importance",
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    for msg in data.get("value", []):
                        emails.append({
                            "id": msg.get("id"),
                            "subject": msg.get("subject"),
                            "from": msg.get("from", {}).get("emailAddress", {}).get("address"),
                            "preview": msg.get("bodyPreview", "")[:200],
                            "date": msg.get("receivedDateTime"),
                            "importance": msg.get("importance"),
                            "user": email,
                            "source": "email"
                        })
                    logger.info(f"Retrieved {len(emails)} emails for {email}")
                else:
                    logger.error(f"Failed to get emails: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.error(f"Error fetching emails: {e}")
        
        return emails
    
    async def get_user_onedrive(self, email: str) -> List[Dict]:
        """Get OneDrive files for specific user"""
        logger.info(f"Fetching OneDrive files for {email}")
        
        app = ConfidentialClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            client_credential=self.client_secret
        )
        
        result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        
        if "access_token" not in result:
            return []
        
        headers = {"Authorization": f"Bearer {result['access_token']}"}
        files = []
        
        async with httpx.AsyncClient() as client:
            try:
                # Get Tyler's recent files
                response = await client.get(
                    f"{self.graph_base}/users/{email}/drive/recent?$top=50",
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("value", []):
                        files.append({
                            "id": item.get("id"),
                            "name": item.get("name"),
                            "type": item.get("file", {}).get("mimeType", "folder"),
                            "modified": item.get("lastModifiedDateTime"),
                            "size": item.get("size", 0),
                            "path": item.get("parentReference", {}).get("path", ""),
                            "user": email,
                            "source": "onedrive"
                        })
                    logger.info(f"Retrieved {len(files)} files for {email}")
                    
            except Exception as e:
                logger.error(f"Error fetching OneDrive: {e}")
        
        return files
    
    async def get_user_teams_chats(self, email: str) -> List[Dict]:
        """Get Teams chat messages for specific user"""
        logger.info(f"Fetching Teams chats for {email}")
        
        app = ConfidentialClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            client_credential=self.client_secret
        )
        
        result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        
        if "access_token" not in result:
            return []
        
        headers = {"Authorization": f"Bearer {result['access_token']}"}
        chats = []
        
        async with httpx.AsyncClient() as client:
            try:
                # Get user's chat list first
                response = await client.get(
                    f"{self.graph_base}/users/{email}/chats?$top=20",
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # For each chat, get recent messages
                    for chat in data.get("value", []):
                        chat_id = chat.get("id")
                        
                        # Get messages from this chat
                        msg_response = await client.get(
                            f"{self.graph_base}/chats/{chat_id}/messages?$top=10",
                            headers=headers,
                            timeout=30.0
                        )
                        
                        if msg_response.status_code == 200:
                            msg_data = msg_response.json()
                            for msg in msg_data.get("value", []):
                                chats.append({
                                    "id": msg.get("id"),
                                    "content": msg.get("body", {}).get("content", ""),
                                    "from": msg.get("from", {}).get("user", {}).get("displayName", "Unknown"),
                                    "timestamp": msg.get("createdDateTime"),
                                    "chat_id": chat_id,
                                    "user": email,
                                    "source": "teams"
                                })
                    
                    logger.info(f"Retrieved {len(chats)} Teams messages for {email}")
                    
            except Exception as e:
                logger.error(f"Error fetching Teams chats: {e}")
        
        return chats
    
    async def sync_all_services(self, email: str) -> Dict:
        """Sync all enabled services for a user"""
        if email not in self.users:
            return {"error": f"User {email} not configured"}
        
        user = self.users[email]
        results = {
            "user": email,
            "timestamp": datetime.utcnow().isoformat(),
            "services": {}
        }
        
        # Sync each enabled service
        if user.services.get("email", False):
            results["services"]["email"] = await self.get_user_emails(email)
        
        if user.services.get("onedrive", False):
            results["services"]["onedrive"] = await self.get_user_onedrive(email)
        
        if user.services.get("teams", False):
            results["services"]["teams"] = await self.get_user_teams_chats(email)
        
        return results

# Global instance
integration_manager = IntegrationManager()
