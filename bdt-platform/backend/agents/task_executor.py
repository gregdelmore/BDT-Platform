"""
Task Executor - Handles actual task execution
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import logging
import aiohttp
import asyncio
from enum import Enum

from ..config import settings
from ..database import get_db, DelegatedTask

logger = logging.getLogger(__name__)

class ExecutionMethod(str, Enum):
    """Task execution methods"""
    API_CALL = "api_call"
    EMAIL_SEND = "email_send"
    FILE_OPERATION = "file_operation"
    DATABASE_QUERY = "database_query"
    WEBHOOK = "webhook"
    SCRIPT = "script"
    LLM_COMPLETION = "llm_completion"

class TaskExecutor:
    """
    Executes tasks based on decision actions
    """
    
    def __init__(self, persona_id: str):
        self.persona_id = persona_id
        self.session = None
        
        # Execution handlers
        self.handlers = {
            ExecutionMethod.API_CALL: self._execute_api_call,
            ExecutionMethod.EMAIL_SEND: self._execute_email_send,
            ExecutionMethod.FILE_OPERATION: self._execute_file_operation,
            ExecutionMethod.DATABASE_QUERY: self._execute_database_query,
            ExecutionMethod.WEBHOOK: self._execute_webhook,
            ExecutionMethod.SCRIPT: self._execute_script,
            ExecutionMethod.LLM_COMPLETION: self._execute_llm_completion
        }
    
    async def execute(
        self,
        task: DelegatedTask,
        actions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute task actions
        """
        results = {
            "success": True,
            "actions_executed": [],
            "outputs": {},
            "errors": []
        }
        
        try:
            # Initialize session if needed
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Execute each action
            for i, action in enumerate(actions):
                action_result = await self._execute_action(action)
                
                results["actions_executed"].append({
                    "index": i,
                    "action": action.get("action"),
                    "success": action_result.get("success", False),
                    "output": action_result.get("output")
                })
                
                if action_result.get("success"):
                    results["outputs"][f"action_{i}"] = action_result.get("output")
                else:
                    results["errors"].append(action_result.get("error"))
                    if not action.get("continue_on_error", False):
                        results["success"] = False
                        break
            
            return results
            
        except Exception as e:
            logger.error(f"Task execution failed: {str(e)}")
            results["success"] = False
            results["errors"].append(str(e))
            return results
    
    async def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single action"""
        try:
            method = ExecutionMethod(action.get("method", "api_call"))
            
            if method in self.handlers:
                return await self.handlers[method](action)
            else:
                return {
                    "success": False,
                    "error": f"Unknown execution method: {method}"
                }
                
        except Exception as e:
            logger.error(f"Action execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_api_call(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API call"""
        try:
            url = action.get("url")
            method = action.get("http_method", "GET")
            headers = action.get("headers", {})
            data = action.get("data")
            
            async with self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=data if method != "GET" else None,
                params=data if method == "GET" else None
            ) as response:
                response_data = await response.json()
                
                return {
                    "success": response.status < 400,
                    "output": {
                        "status": response.status,
                        "data": response_data
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"API call failed: {str(e)}"
            }
    
    async def _execute_email_send(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute email send"""
        try:
            # This would integrate with email service
            # For now, simulate
            await asyncio.sleep(0.5)
            
            return {
                "success": True,
                "output": {
                    "message_id": "simulated-message-id",
                    "recipients": action.get("recipients", [])
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Email send failed: {str(e)}"
            }
    
    async def _execute_file_operation(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute file operation"""
        try:
            operation = action.get("operation")
            file_path = action.get("file_path")
            
            # Simulate file operations
            await asyncio.sleep(0.3)
            
            return {
                "success": True,
                "output": {
                    "operation": operation,
                    "file_path": file_path,
                    "status": "completed"
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"File operation failed: {str(e)}"
            }
    
    async def _execute_database_query(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute database query"""
        try:
            # This would execute actual queries
            # For now, simulate
            query = action.get("query")
            
            # Simulate query execution
            await asyncio.sleep(0.2)
            
            return {
                "success": True,
                "output": {
                    "query": query,
                    "rows_affected": 0,
                    "results": []
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Database query failed: {str(e)}"
            }
    
    async def _execute_webhook(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute webhook call"""
        try:
            # Similar to API call but with webhook-specific handling
            return await self._execute_api_call(action)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Webhook failed: {str(e)}"
            }
    
    async def _execute_script(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute script"""
        try:
            # This would execute scripts safely
            # For now, simulate
            script_type = action.get("script_type", "python")
            script_content = action.get("script_content")
            
            # Simulate script execution
            await asyncio.sleep(1.0)
            
            return {
                "success": True,
                "output": {
                    "script_type": script_type,
                    "execution_time": 1.0,
                    "result": "Script executed successfully"
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Script execution failed: {str(e)}"
            }
    
    async def _execute_llm_completion(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute LLM completion"""
        try:
            from langchain.chat_models import ChatOpenAI
            
            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                temperature=action.get("temperature", 0.3),
                openai_api_key=settings.OPENAI_API_KEY
            )
            
            prompt = action.get("prompt")
            response = await llm.apredict(prompt)
            
            return {
                "success": True,
                "output": {
                    "completion": response,
                    "model": settings.OPENAI_MODEL
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"LLM completion failed: {str(e)}"
            }
    
    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
            self.session = None

# Export executor class
__all__ = ["TaskExecutor", "ExecutionMethod"]