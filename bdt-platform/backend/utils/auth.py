"""
backend/utils/auth.py
OAuth Authentication Helpers for Microsoft 365
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import httpx
from pathlib import Path

logger = logging.getLogger(__name__)


class TokenManager:
    """
    Manages OAuth tokens with automatic refresh
    Based on O365 library patterns
    """
    
    def __init__(self, client_id: str, client_secret: str, tenant_id: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.token_path = Path("tokens")
        self.token_path.mkdir(exist_ok=True)
        self.token_file = self.token_path / f"{client_id}_token.json"
        
    def save_token(self, token: Dict[str, Any]) -> None:
        """Save token to file"""
        token['saved_at'] = datetime.utcnow().isoformat()
        with open(self.token_file, 'w') as f:
            json.dump(token, f)
        logger.info("Token saved successfully")
        
    def load_token(self) -> Optional[Dict[str, Any]]:
        """Load token from file"""
        if not self.token_file.exists():
            return None
            
        try:
            with open(self.token_file, 'r') as f:
                token = json.load(f)
                
            # Check if token is expired
            if self.is_token_expired(token):
                logger.info("Token expired, needs refresh")
                return None
                
            return token
        except Exception as e:
            logger.error(f"Error loading token: {e}")
            return None
            
    def is_token_expired(self, token: Dict[str, Any]) -> bool:
        """Check if token is expired"""
        if 'expires_in' not in token or 'saved_at' not in token:
            return True
            
        saved_at = datetime.fromisoformat(token['saved_at'])
        expires_in = token['expires_in']
        expiry_time = saved_at + timedelta(seconds=expires_in - 300)  # 5 min buffer
        
        return datetime.utcnow() > expiry_time
        
    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh OAuth token"""
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'offline_access User.Read Mail.Read Calendars.Read Files.Read.All Sites.Read.All'
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(token_url, data=data)
                response.raise_for_status()
                
                new_token = response.json()
                self.save_token(new_token)
                return new_token
                
            except httpx.HTTPError as e:
                logger.error(f"Token refresh failed: {e}")
                return None
                
    def get_auth_url(self, redirect_uri: str = "http://localhost:8000/callback") -> str:
        """Get OAuth authorization URL"""
        auth_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"
        
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'response_mode': 'query',
            'scope': 'offline_access User.Read Mail.Read Calendars.Read Files.Read.All Sites.Read.All Chat.Read ChannelMessage.Read.All',
            'state': 'bdt_auth'
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{auth_url}?{query_string}"
        
    async def exchange_code_for_token(self, code: str, redirect_uri: str = "http://localhost:8000/callback") -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token"""
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'offline_access User.Read Mail.Read Calendars.Read Files.Read.All Sites.Read.All'
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(token_url, data=data)
                response.raise_for_status()
                
                token = response.json()
                self.save_token(token)
                return token
                
            except httpx.HTTPError as e:
                logger.error(f"Code exchange failed: {e}")
                return None


class PermissionChecker:
    """Check and validate required permissions"""
    
    REQUIRED_PERMISSIONS = [
        'Mail.Read',
        'Calendars.Read',
        'Files.Read.All',
        'Sites.Read.All',
        'User.Read',
        'offline_access'
    ]
    
    OPTIONAL_PERMISSIONS = [
        'Chat.Read',
        'ChannelMessage.Read.All',
        'Mail.Send',
        'Calendars.ReadWrite'
    ]
    
    @classmethod
    def check_token_scopes(cls, token: Dict[str, Any]) -> Dict[str, bool]:
        """Check which scopes are available in token"""
        scopes = token.get('scope', '').split()
        
        result = {
            'required': {},
            'optional': {},
            'missing_required': []
        }
        
        for perm in cls.REQUIRED_PERMISSIONS:
            result['required'][perm] = perm in scopes
            if perm not in scopes:
                result['missing_required'].append(perm)
                
        for perm in cls.OPTIONAL_PERMISSIONS:
            result['optional'][perm] = perm in scopes
            
        result['all_required_present'] = len(result['missing_required']) == 0
        
        return result
        
    @classmethod
    def get_scope_string(cls, include_optional: bool = False) -> str:
        """Get scope string for OAuth request"""
        scopes = cls.REQUIRED_PERMISSIONS.copy()
        if include_optional:
            scopes.extend(cls.OPTIONAL_PERMISSIONS)
        return ' '.join(scopes)


class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_calls: int = 100, period: int = 60):
        self.max_calls = max_calls
        self.period = period  # seconds
        self.calls = []
        
    def check_limit(self) -> bool:
        """Check if we can make another call"""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.period)
        
        # Remove old calls
        self.calls = [call_time for call_time in self.calls if call_time > cutoff]
        
        # Check limit
        if len(self.calls) >= self.max_calls:
            return False
            
        # Record this call
        self.calls.append(now)
        return True
        
    def wait_time(self) -> float:
        """Get seconds to wait before next call is allowed"""
        if len(self.calls) < self.max_calls:
            return 0.0
            
        oldest_call = min(self.calls)
        cutoff = datetime.utcnow() - timedelta(seconds=self.period)
        
        if oldest_call > cutoff:
            wait = (oldest_call - cutoff).total_seconds()
            return wait
            
        return 0.0


# Singleton instances
_token_manager = None
_rate_limiter = None


def get_token_manager() -> TokenManager:
    """Get singleton TokenManager instance"""
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager(
            os.getenv("MS_CLIENT_ID"),
            os.getenv("MS_CLIENT_SECRET"),
            os.getenv("MS_TENANT_ID")
        )
    return _token_manager


def get_rate_limiter() -> RateLimiter:
    """Get singleton RateLimiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            max_calls=int(os.getenv("RATE_LIMIT_REQUESTS", 100)),
            period=int(os.getenv("RATE_LIMIT_PERIOD", 60))
        )
    return _rate_limiter
