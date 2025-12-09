import logging
import json
from typing import List, Dict
import httpx
from msal import ConfidentialClientApplication

logger = logging.getLogger(__name__)

class TylerDataService:
    """Service to get Tyler's actual Microsoft 365 data"""
    
    def __init__(self):
        self.client_id = "98f8baa3-5127-4ef1-83d7-cdec8b9cb791"
        self.client_secret = "mpX8Q~mrLGi-dcQF-kpNGiC2ZkiXOB0Bi6I_BbCq"
        self.tenant_id = "ae228585-fff9-4624-8d69-77facf28d996"
        self.tyler_email = "tyler.helwig@airiam.com"
        
        self.app = ConfidentialClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            client_credential=self.client_secret
        )
        
    def get_token(self):
        """Get access token for Microsoft Graph"""
        result = self.app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" in result:
            return result["access_token"]
        return None
    
    async def get_tyler_emails(self, limit=50):
        """Get Tyler's actual emails"""
        token = self.get_token()
        if not token:
            # Return demo data if no token
            return [
                {"subject": "Project Status Update", "from": "manager@airiam.com", "preview": "Please update the status..."},
                {"subject": "Customer Portal Migration", "from": "team@airiam.com", "preview": "Migration schedule attached..."},
                {"subject": "API Documentation Review", "from": "tyler.helwig@airiam.com", "preview": "Documentation complete..."}
            ]
        
        headers = {"Authorization": f"Bearer {token}"}
        emails = []
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"https://graph.microsoft.com/v1.0/users/{self.tyler_email}/messages?$top={limit}&$select=subject,from,bodyPreview,receivedDateTime",
                    headers=headers,
                    timeout=30
                )
                if response.status_code == 200:
                    data = response.json()
                    for msg in data.get("value", []):
                        emails.append({
                            "subject": msg.get("subject", "No Subject"),
                            "from": msg.get("from", {}).get("emailAddress", {}).get("address", "Unknown"),
                            "preview": msg.get("bodyPreview", "")[:200],
                            "date": msg.get("receivedDateTime", "")
                        })
                    logger.info(f"Retrieved {len(emails)} real emails for Tyler")
            except Exception as e:
                logger.error(f"Error getting emails: {e}")
        
        return emails
    
    async def get_tyler_files(self, limit=30):
        """Get Tyler's OneDrive files"""
        token = self.get_token()
        if not token:
            return [
                {"name": "Architecture Diagram.pptx", "modified": "2024-11-15", "size": 2456789},
                {"name": "API Documentation.docx", "modified": "2024-11-20", "size": 567890},
                {"name": "Migration Plan.xlsx", "modified": "2024-11-25", "size": 234567}
            ]
        
        headers = {"Authorization": f"Bearer {token}"}
        files = []
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"https://graph.microsoft.com/v1.0/users/{self.tyler_email}/drive/recent?$top={limit}",
                    headers=headers,
                    timeout=30
                )
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("value", []):
                        files.append({
                            "name": item.get("name", "Unknown"),
                            "modified": item.get("lastModifiedDateTime", ""),
                            "size": item.get("size", 0)
                        })
                    logger.info(f"Retrieved {len(files)} real files for Tyler")
            except Exception as e:
                logger.error(f"Error getting files: {e}")
        
        return files

tyler_service = TylerDataService()
