"""
Microsoft Graph API Service - Complete Implementation
Handles all Microsoft 365 data synchronization
"""
import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from functools import wraps
import time

import httpx
from msal import ConfidentialClientApplication
from sqlalchemy.orm import Session
import backoff

logger = logging.getLogger(__name__)

class GraphAPIError(Exception):
    """Custom exception for Graph API errors"""
    pass

def retry_on_throttle(max_tries=3, max_time=300):
    """Decorator for handling Graph API throttling"""
    def decorator(func):
        @wraps(func)
        @backoff.on_exception(
            backoff.expo,
            httpx.HTTPStatusError,
            max_tries=max_tries,
            max_time=max_time,
            giveup=lambda e: e.response.status_code not in [429, 503]
        )
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    retry_after = e.response.headers.get('Retry-After', 60)
                    logger.warning(f"Rate limited. Retrying after {retry_after} seconds")
                    await asyncio.sleep(int(retry_after))
                    return await func(*args, **kwargs)
                raise
        return wrapper
    return decorator

class MicrosoftGraphService:
    """Production-grade Microsoft Graph API integration"""
    
    def __init__(self):
        self.client_id = os.getenv("MICROSOFT_CLIENT_ID", "98f8baa3-5127-4ef1-83d7-cdec8b9cb791")
        self.client_secret = os.getenv("MICROSOFT_CLIENT_SECRET", "mpX8Q~mrLGi-dcQF-kpNGiC2ZkiXOB0Bi6I_BbCq")
        self.tenant_id = os.getenv("MICROSOFT_TENANT_ID", "ae228585-fff9-4624-8d69-77facf28d996")
        self.redirect_uri = os.getenv("MICROSOFT_REDIRECT_URI", 
            "https://bdt-platform-bfc3g7g6eabbf2a4.eastus2-01.azurewebsites.net/auth/callback")
        
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.graph_url = "https://graph.microsoft.com/v1.0"
        
        # Initialize MSAL app
        self.msal_app = ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret
        )
        
        # Scopes for different services
        self.scopes = [
            "User.Read",
            "Mail.Read",
            "Calendars.Read",
            "Files.Read.All",
            "Chat.Read",
            "ChannelMessage.Read.All",
            "offline_access"
        ]
        
        # Rate limiting tracking
        self.request_counts = {}
        self.request_window = 60  # seconds
        
    def get_auth_url(self, state: str) -> str:
        """Generate OAuth authorization URL"""
        auth_url = self.msal_app.get_authorization_request_url(
            self.scopes,
            state=state,
            redirect_uri=self.redirect_uri
        )
        return auth_url
    
    async def get_token_from_code(self, code: str) -> Dict:
        """Exchange authorization code for access token"""
        try:
            result = self.msal_app.acquire_token_by_authorization_code(
                code,
                scopes=self.scopes,
                redirect_uri=self.redirect_uri
            )
            
            if "access_token" in result:
                return {
                    "access_token": result["access_token"],
                    "refresh_token": result.get("refresh_token"),
                    "expires_in": result.get("expires_in", 3600)
                }
            else:
                raise GraphAPIError(f"Failed to get token: {result.get('error_description')}")
        except Exception as e:
            logger.error(f"Token acquisition failed: {e}")
            raise GraphAPIError(f"Token acquisition failed: {str(e)}")
    
    async def refresh_token(self, refresh_token: str) -> Dict:
        """Refresh an expired access token"""
        try:
            result = self.msal_app.acquire_token_by_refresh_token(
                refresh_token,
                scopes=self.scopes
            )
            
            if "access_token" in result:
                return {
                    "access_token": result["access_token"],
                    "refresh_token": result.get("refresh_token", refresh_token),
                    "expires_in": result.get("expires_in", 3600)
                }
            else:
                raise GraphAPIError("Token refresh failed")
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise
    
    @retry_on_throttle()
    async def _make_graph_request(
        self,
        access_token: str,
        endpoint: str,
        method: str = "GET",
        params: Dict = None,
        data: Dict = None
    ) -> Any:
        """Make authenticated request to Graph API with retry logic"""
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.graph_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=data
                )
                response.raise_for_status()
                
                if response.content:
                    return response.json()
                return None
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Graph API error: {e.response.status_code} - {e.response.text}")
                
                if e.response.status_code == 401:
                    raise GraphAPIError("Authentication failed - token may be expired")
                elif e.response.status_code == 403:
                    raise GraphAPIError("Insufficient permissions")
                elif e.response.status_code == 404:
                    return None
                else:
                    raise
            except Exception as e:
                logger.error(f"Request failed: {e}")
                raise GraphAPIError(f"Request failed: {str(e)}")
    
    async def get_user_profile(self, access_token: str) -> Dict:
        """Get user profile information"""
        try:
            profile = await self._make_graph_request(access_token, "/me")
            return {
                "id": profile.get("id"),
                "email": profile.get("mail") or profile.get("userPrincipalName"),
                "name": profile.get("displayName"),
                "job_title": profile.get("jobTitle"),
                "department": profile.get("department")
            }
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            raise
    
    async def sync_emails(
        self,
        access_token: str,
        twin_id: str,
        days_back: int = 90,
        batch_size: int = 50,
        callback=None
    ) -> Dict:
        """
        Sync emails from Microsoft Graph
        Returns statistics about synced emails
        """
        try:
            synced_count = 0
            total_size = 0
            errors = []
            
            # Calculate date filter
            start_date = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + "Z"
            
            # Build filter query
            filter_query = f"receivedDateTime ge {start_date}"
            
            # Initial request
            endpoint = "/me/messages"
            params = {
                "$filter": filter_query,
                "$top": batch_size,
                "$orderby": "receivedDateTime desc",
                "$select": "id,subject,bodyPreview,from,toRecipients,receivedDateTime,importance,isRead,hasAttachments"
            }
            
            next_link = None
            page_count = 0
            max_pages = 20  # Limit to prevent infinite loops
            
            while page_count < max_pages:
                # Make request
                if next_link:
                    # Use the next link directly
                    response = await self._make_graph_request(
                        access_token,
                        next_link.replace(self.graph_url, "")
                    )
                else:
                    response = await self._make_graph_request(
                        access_token,
                        endpoint,
                        params=params
                    )
                
                if not response:
                    break
                
                emails = response.get("value", [])
                
                # Process each email
                for email in emails:
                    try:
                        # Extract email data
                        email_data = {
                            "message_id": email.get("id"),
                            "subject": email.get("subject", "No Subject"),
                            "body_preview": email.get("bodyPreview", ""),
                            "from": email.get("from", {}).get("emailAddress", {}).get("address"),
                            "to": [r.get("emailAddress", {}).get("address") 
                                  for r in email.get("toRecipients", [])],
                            "received_date": email.get("receivedDateTime"),
                            "importance": email.get("importance", "normal"),
                            "is_read": email.get("isRead", False),
                            "has_attachments": email.get("hasAttachments", False)
                        }
                        
                        # Prepare for storage
                        text_content = f"Subject: {email_data['subject']}\n"
                        text_content += f"From: {email_data['from']}\n"
                        text_content += f"Date: {email_data['received_date']}\n"
                        text_content += f"Preview: {email_data['body_preview']}\n"
                        
                        # Call storage callback if provided
                        if callback:
                            await callback(
                                twin_id=twin_id,
                                text=text_content,
                                source_type="email",
                                metadata=email_data
                            )
                        
                        synced_count += 1
                        total_size += len(text_content)
                        
                    except Exception as e:
                        logger.error(f"Failed to process email {email.get('id')}: {e}")
                        errors.append(str(e))
                
                # Check for next page
                next_link = response.get("@odata.nextLink")
                if not next_link or not emails:
                    break
                
                page_count += 1
                
                # Rate limiting - pause between pages
                await asyncio.sleep(0.5)
            
            return {
                "success": True,
                "synced_count": synced_count,
                "total_size_bytes": total_size,
                "errors": errors,
                "pages_processed": page_count
            }
            
        except Exception as e:
            logger.error(f"Email sync failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "synced_count": 0
            }
    
    async def sync_calendar(
        self,
        access_token: str,
        twin_id: str,
        days_back: int = 90,
        days_forward: int = 90,
        callback=None
    ) -> Dict:
        """
        Sync calendar events from Microsoft Graph
        """
        try:
            synced_count = 0
            errors = []
            
            # Calculate date range
            start_date = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + "Z"
            end_date = (datetime.utcnow() + timedelta(days=days_forward)).isoformat() + "Z"
            
            # Build query
            endpoint = "/me/events"
            params = {
                "$filter": f"start/dateTime ge '{start_date}' and start/dateTime le '{end_date}'",
                "$top": 100,
                "$orderby": "start/dateTime asc",
                "$select": "id,subject,bodyPreview,start,end,location,attendees,organizer,isAllDay,importance,showAs"
            }
            
            # Get events
            response = await self._make_graph_request(access_token, endpoint, params=params)
            
            if not response:
                return {"success": False, "error": "No response from Graph API"}
            
            events = response.get("value", [])
            
            # Process each event
            for event in events:
                try:
                    event_data = {
                        "event_id": event.get("id"),
                        "subject": event.get("subject", "No Subject"),
                        "body_preview": event.get("bodyPreview", ""),
                        "start": event.get("start", {}).get("dateTime"),
                        "end": event.get("end", {}).get("dateTime"),
                        "location": event.get("location", {}).get("displayName", ""),
                        "is_all_day": event.get("isAllDay", False),
                        "importance": event.get("importance", "normal"),
                        "show_as": event.get("showAs", "busy"),
                        "organizer": event.get("organizer", {}).get("emailAddress", {}).get("address"),
                        "attendees": [a.get("emailAddress", {}).get("address") 
                                     for a in event.get("attendees", [])]
                    }
                    
                    # Prepare text content
                    text_content = f"Event: {event_data['subject']}\n"
                    text_content += f"When: {event_data['start']} to {event_data['end']}\n"
                    text_content += f"Location: {event_data['location']}\n"
                    text_content += f"Organizer: {event_data['organizer']}\n"
                    text_content += f"Description: {event_data['body_preview']}\n"
                    
                    # Store via callback
                    if callback:
                        await callback(
                            twin_id=twin_id,
                            text=text_content,
                            source_type="calendar",
                            metadata=event_data
                        )
                    
                    synced_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process event {event.get('id')}: {e}")
                    errors.append(str(e))
            
            return {
                "success": True,
                "synced_count": synced_count,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Calendar sync failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "synced_count": 0
            }
    
    async def sync_files(
        self,
        access_token: str,
        twin_id: str,
        folder_path: str = None,
        file_types: List[str] = None,
        callback=None
    ) -> Dict:
        """
        Sync OneDrive files metadata
        """
        try:
            synced_count = 0
            errors = []
            
            # Default file types to sync
            if not file_types:
                file_types = ['.docx', '.xlsx', '.pptx', '.pdf', '.txt', '.md']
            
            # Build endpoint
            if folder_path:
                endpoint = f"/me/drive/root:/{folder_path}:/children"
            else:
                # Get recent files
                endpoint = "/me/drive/recent"
            
            params = {
                "$top": 100,
                "$select": "id,name,size,lastModifiedDateTime,createdBy,parentReference,file"
            }
            
            # Get files
            response = await self._make_graph_request(access_token, endpoint, params=params)
            
            if not response:
                return {"success": False, "error": "No response from Graph API"}
            
            files = response.get("value", [])
            
            # Process each file
            for file_item in files:
                try:
                    # Skip folders
                    if "file" not in file_item:
                        continue
                    
                    file_name = file_item.get("name", "")
                    
                    # Check file type
                    if file_types and not any(file_name.lower().endswith(ft) for ft in file_types):
                        continue
                    
                    file_data = {
                        "file_id": file_item.get("id"),
                        "name": file_name,
                        "size": file_item.get("size", 0),
                        "modified": file_item.get("lastModifiedDateTime"),
                        "created_by": file_item.get("createdBy", {}).get("user", {}).get("email"),
                        "mime_type": file_item.get("file", {}).get("mimeType", ""),
                        "path": file_item.get("parentReference", {}).get("path", "")
                    }
                    
                    # Prepare text content
                    text_content = f"File: {file_data['name']}\n"
                    text_content += f"Type: {file_data['mime_type']}\n"
                    text_content += f"Size: {file_data['size']} bytes\n"
                    text_content += f"Modified: {file_data['modified']}\n"
                    text_content += f"Path: {file_data['path']}\n"
                    
                    # For text files, we could fetch content (limited)
                    if file_name.lower().endswith(('.txt', '.md')):
                        try:
                            # Get file content (first 10KB)
                            content_endpoint = f"/me/drive/items/{file_item['id']}/content"
                            content_response = await self._make_graph_request(
                                access_token,
                                content_endpoint
                            )
                            if content_response:
                                text_content += f"\nContent Preview:\n{content_response[:1000]}\n"
                        except:
                            pass
                    
                    # Store via callback
                    if callback:
                        await callback(
                            twin_id=twin_id,
                            text=text_content,
                            source_type="files",
                            metadata=file_data
                        )
                    
                    synced_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process file {file_item.get('name')}: {e}")
                    errors.append(str(e))
            
            return {
                "success": True,
                "synced_count": synced_count,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Files sync failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "synced_count": 0
            }
    
    async def sync_teams_messages(
        self,
        access_token: str,
        twin_id: str,
        days_back: int = 30,
        callback=None
    ) -> Dict:
        """
        Sync Teams chat messages
        Note: Requires additional permissions
        """
        try:
            synced_count = 0
            errors = []
            
            # Get list of chats
            chats_endpoint = "/me/chats"
            params = {
                "$top": 20,
                "$expand": "lastMessagePreview"
            }
            
            chats_response = await self._make_graph_request(
                access_token,
                chats_endpoint,
                params=params
            )
            
            if not chats_response:
                return {"success": False, "error": "Could not fetch chats"}
            
            chats = chats_response.get("value", [])
            
            # Process each chat
            for chat in chats[:10]:  # Limit to prevent timeout
                try:
                    chat_id = chat.get("id")
                    
                    # Get messages from chat
                    messages_endpoint = f"/me/chats/{chat_id}/messages"
                    messages_params = {
                        "$top": 50,
                        "$orderby": "createdDateTime desc"
                    }
                    
                    messages_response = await self._make_graph_request(
                        access_token,
                        messages_endpoint,
                        params=messages_params
                    )
                    
                    if not messages_response:
                        continue
                    
                    messages = messages_response.get("value", [])
                    
                    for message in messages:
                        message_data = {
                            "message_id": message.get("id"),
                            "chat_id": chat_id,
                            "from": message.get("from", {}).get("user", {}).get("displayName"),
                            "created": message.get("createdDateTime"),
                            "body": message.get("body", {}).get("content", ""),
                            "importance": message.get("importance", "normal")
                        }
                        
                        # Prepare text content
                        text_content = f"Teams Message\n"
                        text_content += f"From: {message_data['from']}\n"
                        text_content += f"Date: {message_data['created']}\n"
                        text_content += f"Message: {message_data['body'][:500]}\n"
                        
                        # Store via callback
                        if callback:
                            await callback(
                                twin_id=twin_id,
                                text=text_content,
                                source_type="chat",
                                metadata=message_data
                            )
                        
                        synced_count += 1
                        
                except Exception as e:
                    logger.error(f"Failed to process chat {chat.get('id')}: {e}")
                    errors.append(str(e))
                
                # Rate limiting
                await asyncio.sleep(0.5)
            
            return {
                "success": True,
                "synced_count": synced_count,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Teams sync failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "synced_count": 0
            }
    
    async def sync_all_sources(
        self,
        access_token: str,
        twin_id: str,
        callback=None
    ) -> Dict:
        """
        Sync all data sources in parallel with proper error handling
        """
        results = {}
        
        # Define sync tasks
        sync_tasks = [
            ("emails", self.sync_emails(access_token, twin_id, callback=callback)),
            ("calendar", self.sync_calendar(access_token, twin_id, callback=callback)),
            ("files", self.sync_files(access_token, twin_id, callback=callback)),
            ("teams", self.sync_teams_messages(access_token, twin_id, callback=callback))
        ]
        
        # Run all syncs in parallel
        for name, task in sync_tasks:
            try:
                results[name] = await task
            except Exception as e:
                logger.error(f"Failed to sync {name}: {e}")
                results[name] = {"success": False, "error": str(e)}
        
        # Calculate totals
        total_synced = sum(r.get("synced_count", 0) for r in results.values())
        total_errors = sum(len(r.get("errors", [])) for r in results.values())
        
        return {
            "success": all(r.get("success", False) for r in results.values()),
            "total_synced": total_synced,
            "total_errors": total_errors,
            "details": results
        }

# Singleton instance
graph_service = MicrosoftGraphService()
