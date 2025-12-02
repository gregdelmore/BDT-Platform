"""
BDT Phase 2: Microsoft 365 Connector
Production-ready connector for ingesting data from Microsoft 365
Handles: Email, Calendar, OneDrive, Teams
"""

import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import msal
from O365 import Account, FileSystemTokenBackend
from O365.message import Message
from O365.calendar import Event
from O365.drive import Drive, File
import aiohttp
from tqdm.asyncio import tqdm

from core.config import settings
from core.database import Document


@dataclass
class IngestionStats:
    """Statistics for ingestion process"""
    emails_processed: int = 0
    calendar_events_processed: int = 0
    files_processed: int = 0
    teams_messages_processed: int = 0
    errors: List[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    
    @property
    def total_processed(self) -> int:
        return (
            self.emails_processed + 
            self.calendar_events_processed + 
            self.files_processed + 
            self.teams_messages_processed
        )
    
    @property
    def elapsed_time(self) -> timedelta:
        return datetime.now() - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "emails": self.emails_processed,
            "calendar": self.calendar_events_processed,
            "files": self.files_processed,
            "teams": self.teams_messages_processed,
            "total": self.total_processed,
            "errors": len(self.errors),
            "elapsed_seconds": self.elapsed_time.total_seconds()
        }


class Microsoft365Connector:
    """
    Production connector for Microsoft 365 data ingestion
    Uses O365 library for robust API interaction
    """
    
    def __init__(self, 
                 client_id: Optional[str] = None,
                 client_secret: Optional[str] = None,
                 tenant_id: Optional[str] = None):
        """
        Initialize Microsoft 365 connector
        
        Args:
            client_id: Azure AD application ID
            client_secret: Application secret
            tenant_id: Azure AD tenant ID
        """
        self.client_id = client_id or settings.ms365_client_id
        self.client_secret = client_secret or settings.ms365_client_secret
        self.tenant_id = tenant_id or settings.ms365_tenant_id
        
        # Token storage
        self.token_path = Path("./tokens")
        self.token_path.mkdir(exist_ok=True)
        
        # Initialize account
        self.account = None
        self.authenticated = False
        
        # Statistics
        self.stats = IngestionStats()
        
    async def authenticate(self, interactive: bool = False) -> bool:
        """
        Authenticate with Microsoft 365
        
        Args:
            interactive: Whether to use interactive browser authentication
            
        Returns:
            True if authentication successful
        """
        print("🔐 Authenticating with Microsoft 365...")
        
        try:
            # Setup token backend
            token_backend = FileSystemTokenBackend(
                token_path=self.token_path,
                token_filename='o365_token.txt'
            )
            
            # Create account
            self.account = Account(
                (self.client_id, self.client_secret),
                tenant_id=self.tenant_id,
                token_backend=token_backend
            )
            
            # Check if token exists
            if self.account.is_authenticated:
                print("✅ Using existing authentication token")
                self.authenticated = True
                return True
            
            # Authenticate
            if interactive:
                # Interactive browser authentication
                result = self.account.authenticate(
                    scopes=settings.ms365_scopes,
                    redirect_uri=settings.ms365_redirect_uri
                )
            else:
                # Non-interactive authentication (requires app permissions)
                result = self.account.authenticate(
                    scopes=settings.ms365_scopes,
                    grant_type='client_credentials'
                )
            
            if result:
                print("✅ Authentication successful")
                self.authenticated = True
                return True
            else:
                print("❌ Authentication failed")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            self.stats.errors.append(f"Auth error: {str(e)}")
            return False
    
    async def ingest_all(
        self,
        email_days: int = 90,
        calendar_days: int = 90,
        max_files: int = 1000,
        include_teams: bool = False
    ) -> IngestionStats:
        """
        Ingest all available data from Microsoft 365
        
        Args:
            email_days: Number of days of email history to ingest
            calendar_days: Number of days of calendar history
            max_files: Maximum number of files to ingest
            include_teams: Whether to include Teams messages
            
        Returns:
            IngestionStats with processing summary
        """
        if not self.authenticated:
            await self.authenticate()
        
        print(f"📥 Starting Microsoft 365 data ingestion...")
        print(f"   Email: {email_days} days")
        print(f"   Calendar: {calendar_days} days")
        print(f"   Files: max {max_files}")
        print(f"   Teams: {'Yes' if include_teams else 'No'}")
        
        # Run ingestion tasks in parallel
        tasks = [
            self._ingest_emails(email_days),
            self._ingest_calendar(calendar_days),
            self._ingest_files(max_files)
        ]
        
        if include_teams:
            tasks.append(self._ingest_teams_messages())
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for errors
        for result in results:
            if isinstance(result, Exception):
                self.stats.errors.append(str(result))
        
        print(f"✅ Ingestion complete!")
        print(f"   Total processed: {self.stats.total_processed}")
        print(f"   Time elapsed: {self.stats.elapsed_time}")
        
        return self.stats
    
    async def _ingest_emails(self, days: int = 90) -> List[Document]:
        """Ingest emails from all folders"""
        documents = []
        
        try:
            mailbox = self.account.mailbox()
            
            # Calculate date filter
            start_date = datetime.now() - timedelta(days=days)
            query = f"ReceivedDateTime ge {start_date.strftime('%Y-%m-%d')}"
            
            # Get all folders
            folders = mailbox.get_folders()
            
            for folder in folders:
                print(f"  📧 Processing folder: {folder.name}")
                
                # Get messages
                messages = folder.get_messages(
                    limit=None,
                    query=query,
                    download_attachments=False
                )
                
                async for doc in self._process_messages(messages, folder.name):
                    documents.append(doc)
                    self.stats.emails_processed += 1
                    
                    # Yield periodically for better performance
                    if len(documents) % 100 == 0:
                        await asyncio.sleep(0.01)
            
            print(f"  ✅ Processed {self.stats.emails_processed} emails")
            
        except Exception as e:
            print(f"  ❌ Email ingestion error: {e}")
            self.stats.errors.append(f"Email error: {str(e)}")
        
        return documents
    
    async def _process_messages(
        self, messages: Any, folder_name: str
    ) -> AsyncGenerator[Document, None]:
        """Process email messages into documents"""
        
        for message in messages:
            try:
                # Extract all metadata
                metadata = {
                    "type": "email",
                    "folder": folder_name,
                    "message_id": message.message_id,
                    "subject": message.subject,
                    "sender": str(message.sender),
                    "sender_email": message.sender.address if message.sender else None,
                    "recipients": [str(r) for r in message.to] if message.to else [],
                    "cc": [str(r) for r in message.cc] if message.cc else [],
                    "bcc": [str(r) for r in message.bcc] if message.bcc else [],
                    "timestamp": message.received.isoformat() if message.received else None,
                    "sent_time": message.sent.isoformat() if message.sent else None,
                    "has_attachments": message.has_attachments,
                    "importance": message.importance.value if message.importance else "normal",
                    "is_read": message.is_read,
                    "is_reply": bool(message.in_reply_to),
                    "in_reply_to": message.in_reply_to,
                    "thread_id": message.conversation_id,
                    "categories": message.categories if message.categories else []
                }
                
                # Get body text
                body = message.get_body_text() or message.get_body_soup() or ""
                if hasattr(body, 'get_text'):
                    body = body.get_text()
                
                # Calculate response time if it's a reply
                response_time = None
                if message.in_reply_to and message.received and message.sent:
                    response_time = (message.sent - message.received).total_seconds() / 60
                    metadata["response_time_minutes"] = response_time
                
                # Create document
                doc = Document(
                    id=self._generate_doc_id("email", message.message_id),
                    content=f"Subject: {message.subject}\n\n{body}",
                    metadata=metadata,
                    embedding=None  # Will be generated later
                )
                
                yield doc
                
            except Exception as e:
                self.stats.errors.append(f"Message processing error: {str(e)[:100]}")
                continue
    
    async def _ingest_calendar(self, days: int = 90) -> List[Document]:
        """Ingest calendar events"""
        documents = []
        
        try:
            schedule = self.account.schedule()
            calendar = schedule.get_default_calendar()
            
            # Calculate date range
            start_date = datetime.now() - timedelta(days=days)
            end_date = datetime.now() + timedelta(days=30)  # Include future events
            
            # Get events
            query = calendar.new_query('start').greater_equal(start_date)
            query.chain('and').on_attribute('end').less_equal(end_date)
            
            events = calendar.get_events(query=query, limit=None)
            
            print(f"  📅 Processing calendar events...")
            
            for event in events:
                doc = await self._process_calendar_event(event)
                if doc:
                    documents.append(doc)
                    self.stats.calendar_events_processed += 1
            
            print(f"  ✅ Processed {self.stats.calendar_events_processed} calendar events")
            
        except Exception as e:
            print(f"  ❌ Calendar ingestion error: {e}")
            self.stats.errors.append(f"Calendar error: {str(e)}")
        
        return documents
    
    async def _process_calendar_event(self, event: Event) -> Optional[Document]:
        """Process a calendar event into a document"""
        
        try:
            # Extract attendees
            attendees = []
            if event.attendees:
                for attendee in event.attendees:
                    attendees.append({
                        "name": str(attendee),
                        "email": attendee.address if hasattr(attendee, 'address') else None,
                        "response": attendee.response_status.value if hasattr(attendee, 'response_status') else None
                    })
            
            # Calculate duration
            duration = None
            if event.start and event.end:
                duration = (event.end - event.start).total_seconds() / 60
            
            # Check for back-to-back pattern
            is_back_to_back = False  # Would need to check against other events
            
            metadata = {
                "type": "calendar",
                "event_id": event.event_id,
                "subject": event.subject,
                "location": event.location.display_name if event.location else None,
                "start_time": event.start.isoformat() if event.start else None,
                "end_time": event.end.isoformat() if event.end else None,
                "duration_minutes": duration,
                "is_all_day": event.is_all_day,
                "is_recurring": event.is_recurring,
                "organizer": str(event.organizer) if event.organizer else None,
                "attendees": attendees,
                "attendee_count": len(attendees),
                "response_requested": event.response_requested,
                "show_as": event.show_as.value if event.show_as else None,
                "importance": event.importance.value if event.importance else "normal",
                "is_online_meeting": event.is_online_meeting,
                "categories": event.categories if event.categories else [],
                "is_back_to_back": is_back_to_back,
                "timestamp": event.start.isoformat() if event.start else None
            }
            
            # Build content
            content_parts = [f"Event: {event.subject}"]
            if event.body:
                content_parts.append(f"Description: {event.body}")
            if attendees:
                content_parts.append(f"Attendees: {', '.join([a['name'] for a in attendees])}")
            
            doc = Document(
                id=self._generate_doc_id("calendar", event.event_id),
                content="\n".join(content_parts),
                metadata=metadata,
                embedding=None
            )
            
            return doc
            
        except Exception as e:
            self.stats.errors.append(f"Event processing error: {str(e)[:100]}")
            return None
    
    async def _ingest_files(self, max_files: int = 1000) -> List[Document]:
        """Ingest files from OneDrive"""
        documents = []
        
        try:
            storage = self.account.storage()
            drive = storage.get_default_drive()
            
            print(f"  📁 Processing OneDrive files...")
            
            # Get root items
            items = drive.get_items(limit=max_files)
            
            file_count = 0
            for item in items:
                if file_count >= max_files:
                    break
                
                if item.is_file:
                    doc = await self._process_file(item)
                    if doc:
                        documents.append(doc)
                        self.stats.files_processed += 1
                        file_count += 1
                
                elif item.is_folder:
                    # Recursively process folder
                    folder_docs = await self._process_folder(item, max_files - file_count)
                    documents.extend(folder_docs)
                    file_count += len(folder_docs)
            
            print(f"  ✅ Processed {self.stats.files_processed} files")
            
        except Exception as e:
            print(f"  ❌ File ingestion error: {e}")
            self.stats.errors.append(f"File error: {str(e)}")
        
        return documents
    
    async def _process_file(self, file: File) -> Optional[Document]:
        """Process a file into a document"""
        
        try:
            # Get file metadata
            metadata = {
                "type": "file",
                "file_id": file.file_id,
                "name": file.name,
                "path": file.parent_path,
                "size": file.size,
                "mime_type": file.mime_type,
                "created": file.created.isoformat() if file.created else None,
                "modified": file.modified.isoformat() if file.modified else None,
                "timestamp": file.modified.isoformat() if file.modified else None,
                "created_by": str(file.created_by) if file.created_by else None,
                "modified_by": str(file.modified_by) if file.modified_by else None,
                "is_shared": file.is_shared
            }
            
            # Extract text content based on file type
            content = f"File: {file.name}\n"
            
            # For text-based files, try to extract content
            text_extensions = ['.txt', '.md', '.csv', '.json', '.xml', '.log']
            doc_extensions = ['.docx', '.pdf', '.xlsx', '.pptx']
            
            if any(file.name.lower().endswith(ext) for ext in text_extensions):
                # Download and read text files
                try:
                    file_content = file.download()
                    if file_content:
                        content += file_content.decode('utf-8', errors='ignore')[:5000]
                except:
                    content += "[Content extraction failed]"
            
            elif any(file.name.lower().endswith(ext) for ext in doc_extensions):
                # For document files, we'd use specialized extractors
                content += f"[Document file - content extraction pending]"
                metadata["requires_extraction"] = True
            
            doc = Document(
                id=self._generate_doc_id("file", file.file_id),
                content=content,
                metadata=metadata,
                embedding=None
            )
            
            return doc
            
        except Exception as e:
            self.stats.errors.append(f"File processing error: {str(e)[:100]}")
            return None
    
    async def _process_folder(self, folder: Any, remaining_files: int) -> List[Document]:
        """Recursively process folder contents"""
        documents = []
        
        try:
            items = folder.get_items(limit=remaining_files)
            
            for item in items:
                if len(documents) >= remaining_files:
                    break
                
                if item.is_file:
                    doc = await self._process_file(item)
                    if doc:
                        documents.append(doc)
                        self.stats.files_processed += 1
                
        except Exception as e:
            self.stats.errors.append(f"Folder processing error: {str(e)[:100]}")
        
        return documents
    
    async def _ingest_teams_messages(self) -> List[Document]:
        """Ingest Teams messages (requires additional permissions)"""
        documents = []
        
        try:
            # Teams API requires different authentication and permissions
            # This is a placeholder for Teams integration
            print(f"  💬 Teams ingestion not yet implemented")
            
        except Exception as e:
            print(f"  ❌ Teams ingestion error: {e}")
            self.stats.errors.append(f"Teams error: {str(e)}")
        
        return documents
    
    def _generate_doc_id(self, doc_type: str, source_id: str) -> str:
        """Generate unique document ID"""
        hash_input = f"{doc_type}:{source_id}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    async def test_connection(self) -> bool:
        """Test the Microsoft 365 connection"""
        
        try:
            if not self.authenticated:
                success = await self.authenticate()
                if not success:
                    return False
            
            # Try to access mailbox
            mailbox = self.account.mailbox()
            folders = list(mailbox.get_folders(limit=1))
            
            print("✅ Connection test successful")
            return True
            
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False
    
    def get_ingestion_summary(self) -> Dict[str, Any]:
        """Get summary of ingestion process"""
        
        return {
            "stats": self.stats.to_dict(),
            "authenticated": self.authenticated,
            "errors": self.stats.errors[-10:] if self.stats.errors else []  # Last 10 errors
        }


# Simplified connector for quick demos
class SimpleMS365Connector:
    """
    Simplified connector for rapid prototyping and demos
    No async, minimal dependencies
    """
    
    def __init__(self, client_id: str, client_secret: str):
        self.account = Account((client_id, client_secret))
        
    def quick_ingest(self, email_limit: int = 100) -> List[Dict[str, Any]]:
        """Quick ingestion for demos"""
        
        if not self.account.is_authenticated:
            print("Please authenticate first:")
            self.account.authenticate()
        
        documents = []
        
        # Get recent emails
        mailbox = self.account.mailbox()
        inbox = mailbox.inbox_folder()
        
        for message in inbox.get_messages(limit=email_limit):
            doc = {
                "id": message.message_id,
                "type": "email",
                "subject": message.subject,
                "content": message.get_body_text() or "",
                "sender": str(message.sender),
                "timestamp": str(message.received),
                "metadata": {
                    "folder": "inbox",
                    "has_attachments": message.has_attachments,
                    "is_read": message.is_read
                }
            }
            documents.append(doc)
        
        print(f"✅ Ingested {len(documents)} documents")
        return documents


# Export classes
__all__ = [
    "Microsoft365Connector",
    "SimpleMS365Connector",
    "IngestionStats"
]
