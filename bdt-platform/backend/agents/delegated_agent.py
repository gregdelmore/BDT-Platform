"""
L4 Delegated Agent - Main autonomous agent implementation
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import asyncio
import json
import logging
from dataclasses import dataclass
from enum import Enum
import traceback

from ..config import settings
from ..database import (
    get_db, DelegatedTask, TaskStatus, Persona,
    CapabilityLevel, OntologyMapping
)
from ..core.decision_engine import AutonomousDecisionEngine, DecisionContext
from ..core.negative_space import NegativeSpaceAnalyzer
from ..core.hilt_controller import HILTController, HILTMode
from ..core.ontology_engine import FourthOntologyEngine
from .task_executor import TaskExecutor
from .boundary_enforcer import BoundaryEnforcer
from .audit_logger import AuditLogger

logger = logging.getLogger(__name__)

class AgentState(str, Enum):
    """Agent operational states"""
    IDLE = "idle"
    PROCESSING = "processing"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    LEARNING = "learning"
    ERROR = "error"
    PAUSED = "paused"

@dataclass
class AgentMetrics:
    """Agent performance metrics"""
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_requiring_approval: int = 0
    average_confidence: float = 0.0
    average_execution_time: float = 0.0
    boundary_violations: int = 0
    learning_cycles: int = 0
    uptime_seconds: float = 0.0

class L4DelegatedAgent:
    """
    Level 4 Autonomous Delegated Agent
    Operates within learned behavioral boundaries with HILT oversight
    """
    
    def __init__(self, persona_id: str):
        self.persona_id = persona_id
        self.state = AgentState.IDLE
        self.metrics = AgentMetrics()
        self.start_time = datetime.utcnow()
        
        # Initialize components
        self.decision_engine = AutonomousDecisionEngine()
        self.boundary_analyzer = NegativeSpaceAnalyzer()
        self.hilt_controller = HILTController()
        self.ontology_engine = FourthOntologyEngine()
        self.task_executor = TaskExecutor(persona_id)
        self.boundary_enforcer = BoundaryEnforcer(persona_id)
        self.audit_logger = AuditLogger(persona_id)
        
        # Task queue
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.active_tasks: Dict[str, DelegatedTask] = {}
        
        # Configuration
        self.max_concurrent_tasks = 5
        self.learning_enabled = True
        self.auto_pause_on_error = True
        
        logger.info(f"L4 Agent initialized for persona {persona_id}")
    
    async def start(self):
        """Start the agent processing loop"""
        logger.info(f"Starting L4 Agent for persona {self.persona_id}")
        self.state = AgentState.IDLE
        
        try:
            # Load persona configuration
            await self._load_persona_config()
            
            # Start processing loop
            await self._processing_loop()
            
        except Exception as e:
            logger.error(f"Agent start failed: {str(e)}")
            self.state = AgentState.ERROR
            raise
    
    async def stop(self):
        """Stop the agent gracefully"""
        logger.info(f"Stopping L4 Agent for persona {self.persona_id}")
        self.state = AgentState.IDLE
        
        # Wait for active tasks to complete
        if self.active_tasks:
            logger.info(f"Waiting for {len(self.active_tasks)} active tasks to complete")
            await asyncio.gather(
                *[self._wait_for_task(task_id) for task_id in self.active_tasks],
                return_exceptions=True
            )
    
    async def delegate_task(
        self,
        task_type: str,
        task_description: str,
        input_data: Dict[str, Any],
        priority: int = 5
    ) -> str:
        """
        Delegate a new task to the agent
        
        Returns: task_id
        """
        try:
            # Create task in database
            with get_db() as db:
                task = DelegatedTask(
                    persona_id=self.persona_id,
                    task_type=task_type,
                    task_description=task_description,
                    input_data=input_data,
                    status=TaskStatus.PENDING,
                    confidence_score=0.0,
                    risk_score=0.0
                )
                db.add(task)
                db.commit()
                db.refresh(task)
                
                task_id = str(task.id)
                
                # Log task creation
                await self.audit_logger.log_task_created(task)
                
                # Add to queue
                await self.task_queue.put((priority, task_id))
                
                logger.info(f"Task {task_id} delegated to agent")
                return task_id
                
        except Exception as e:
            logger.error(f"Failed to delegate task: {str(e)}")
            raise
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "persona_id": self.persona_id,
            "state": self.state.value,
            "active_tasks": len(self.active_tasks),
            "queued_tasks": self.task_queue.qsize(),
            "metrics": {
                "tasks_completed": self.metrics.tasks_completed,
                "tasks_failed": self.metrics.tasks_failed,
                "tasks_requiring_approval": self.metrics.tasks_requiring_approval,
                "average_confidence": self.metrics.average_confidence,
                "average_execution_time": self.metrics.average_execution_time,
                "boundary_violations": self.metrics.boundary_violations,
                "learning_cycles": self.metrics.learning_cycles,
                "uptime_seconds": uptime
            },
            "configuration": {
                "max_concurrent_tasks": self.max_concurrent_tasks,
                "learning_enabled": self.learning_enabled,
                "hilt_mode": self.hilt_controller.mode.value
            }
        }
    
    async def pause(self):
        """Pause agent processing"""
        logger.info(f"Pausing L4 Agent for persona {self.persona_id}")
        self.state = AgentState.PAUSED
    
    async def resume(self):
        """Resume agent processing"""
        logger.info(f"Resuming L4 Agent for persona {self.persona_id}")
        self.state = AgentState.IDLE
    
    async def _processing_loop(self):
        """Main processing loop"""
        while self.state not in [AgentState.ERROR, AgentState.PAUSED]:
            try:
                # Check for new tasks
                if self.state == AgentState.IDLE and not self.task_queue.empty():
                    # Process tasks up to concurrent limit
                    tasks_to_process = min(
                        self.max_concurrent_tasks - len(self.active_tasks),
                        self.task_queue.qsize()
                    )
                    
                    if tasks_to_process > 0:
                        # Start processing tasks concurrently
                        tasks = []
                        for _ in range(tasks_to_process):
                            priority, task_id = await self.task_queue.get()
                            tasks.append(self._process_task(task_id))
                        
                        # Run tasks concurrently
                        await asyncio.gather(*tasks, return_exceptions=True)
                
                # Brief pause to prevent CPU spinning
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Processing loop error: {str(e)}")
                if self.auto_pause_on_error:
                    self.state = AgentState.PAUSED
    
    async def _process_task(self, task_id: str):
        """Process a single task"""
        try:
            logger.info(f"Processing task {task_id}")
            self.state = AgentState.PROCESSING
            self.active_tasks[task_id] = None
            
            # Load task from database
            with get_db() as db:
                task = db.query(DelegatedTask).filter(
                    DelegatedTask.id == task_id
                ).first()
                
                if not task:
                    logger.error(f"Task {task_id} not found")
                    return
                
                self.active_tasks[task_id] = task
                
                # Update task status
                task.status = TaskStatus.EXECUTING
                task.started_at = datetime.utcnow()
                db.commit()
            
            # Phase 1: Decision Making
            decision_result = await self._make_decision(task)
            
            # Phase 2: Boundary Checking
            boundary_result = await self._check_boundaries(task, decision_result)
            
            if not boundary_result["allowed"]:
                # Task blocked by boundaries
                await self._handle_blocked_task(task, boundary_result["reason"])
                return
            
            # Phase 3: HILT Approval
            if decision_result.requires_approval:
                self.state = AgentState.AWAITING_APPROVAL
                approval = await self.hilt_controller.request_approval(
                    task, decision_result
                )
                
                if approval.action != "APPROVE":
                    await self._handle_rejected_task(task, approval)
                    return
                
                # Update decision if modified
                if approval.modified_decision:
                    decision_result.decision = approval.modified_decision
            
            # Phase 4: Task Execution
            self.state = AgentState.EXECUTING
            execution_result = await self._execute_task(task, decision_result)
            
            # Phase 5: Learning
            if self.learning_enabled:
                self.state = AgentState.LEARNING
                await self._learn_from_execution(task, execution_result)
            
            # Update metrics
            self._update_metrics(task, execution_result)
            
            # Mark task complete
            await self._complete_task(task, execution_result)
            
        except Exception as e:
            logger.error(f"Task processing failed: {str(e)}\n{traceback.format_exc()}")
            await self._handle_task_error(task_id, e)
            
        finally:
            # Remove from active tasks
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            self.state = AgentState.IDLE
    
    async def _make_decision(self, task: DelegatedTask) -> Any:
        """Make autonomous decision for task"""
        try:
            with get_db() as db:
                # Get persona data
                ontology = db.query(OntologyMapping).filter(
                    OntologyMapping.persona_id == self.persona_id
                ).first()
                
                boundaries = self.boundary_analyzer.get_active_boundaries(
                    self.persona_id
                )
                
                patterns = self.decision_engine.get_relevant_patterns(
                    self.persona_id,
                    task.task_type
                )
                
                historical = self.decision_engine.get_historical_decisions(
                    self.persona_id,
                    task.task_type,
                    limit=10
                )
                
                # Create decision context
                context = DecisionContext(
                    task=task,
                    ontology=ontology,
                    boundaries=boundaries,
                    patterns=patterns,
                    historical_decisions=historical,
                    confidence_threshold=settings.HILT_CONFIDENCE_THRESHOLD,
                    risk_tolerance=1 - (ontology.fear_value / 100) if ontology else 0.5
                )
                
                # Make decision
                decision_result = self.decision_engine.make_decision(context)
                
                # Update task with decision info
                task.confidence_score = decision_result.confidence
                task.risk_score = decision_result.risk_score
                db.commit()
                
                # Log decision
                await self.audit_logger.log_decision_made(task, decision_result)
                
                return decision_result
                
        except Exception as e:
            logger.error(f"Decision making failed: {str(e)}")
            raise
    
    async def _check_boundaries(
        self,
        task: DelegatedTask,
        decision_result: Any
    ) -> Dict[str, Any]:
        """Check if task execution violates boundaries"""
        try:
            # Use boundary enforcer for comprehensive check
            result = await self.boundary_enforcer.check_task_boundaries(
                task,
                decision_result
            )
            
            # Log boundary checks
            await self.audit_logger.log_boundary_check(task, result)
            
            # Update violation metrics
            if result.get("violations"):
                self.metrics.boundary_violations += len(result["violations"])
            
            return result
            
        except Exception as e:
            logger.error(f"Boundary checking failed: {str(e)}")
            return {"allowed": False, "reason": str(e)}
    
    async def _execute_task(
        self,
        task: DelegatedTask,
        decision_result: Any
    ) -> Dict[str, Any]:
        """Execute the task based on decision"""
        try:
            start_time = datetime.utcnow()
            
            # Execute using task executor
            execution_result = await self.task_executor.execute(
                task,
                decision_result.suggested_actions
            )
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Update task
            with get_db() as db:
                task_db = db.query(DelegatedTask).filter(
                    DelegatedTask.id == task.id
                ).first()
                
                if task_db:
                    task_db.execution_time = execution_time
                    task_db.output_data = execution_result
                    task_db.success = execution_result.get("success", False)
                    db.commit()
            
            # Log execution
            await self.audit_logger.log_task_executed(task, execution_result)
            
            return execution_result
            
        except Exception as e:
            logger.error(f"Task execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": 0
            }
    
    async def _learn_from_execution(
        self,
        task: DelegatedTask,
        execution_result: Dict[str, Any]
    ):
        """Learn from task execution outcome"""
        try:
            self.metrics.learning_cycles += 1
            
            # Use decision engine's learning capability
            await self.decision_engine.learn_from_outcome(
                str(task.id),
                execution_result,
                execution_result.get("feedback")
            )
            
            # Update ontology if needed
            if execution_result.get("ontology_mismatch"):
                await self._adjust_ontology(execution_result["ontology_mismatch"])
            
            # Update boundaries if needed
            if execution_result.get("boundary_adjustment"):
                await self._adjust_boundaries(execution_result["boundary_adjustment"])
            
            logger.info(f"Learning cycle {self.metrics.learning_cycles} completed")
            
        except Exception as e:
            logger.error(f"Learning failed: {str(e)}")
    
    async def _complete_task(
        self,
        task: DelegatedTask,
        execution_result: Dict[str, Any]
    ):
        """Mark task as complete and update metrics"""
        try:
            with get_db() as db:
                task_db = db.query(DelegatedTask).filter(
                    DelegatedTask.id == task.id
                ).first()
                
                if task_db:
                    task_db.status = TaskStatus.COMPLETED
                    task_db.completed_at = datetime.utcnow()
                    task_db.success = execution_result.get("success", False)
                    db.commit()
            
            # Update metrics
            if execution_result.get("success"):
                self.metrics.tasks_completed += 1
            else:
                self.metrics.tasks_failed += 1
            
            # Log completion
            await self.audit_logger.log_task_completed(task, execution_result)
            
        except Exception as e:
            logger.error(f"Task completion failed: {str(e)}")
    
    async def _handle_blocked_task(self, task: DelegatedTask, reason: str):
        """Handle task blocked by boundaries"""
        try:
            with get_db() as db:
                task_db = db.query(DelegatedTask).filter(
                    DelegatedTask.id == task.id
                ).first()
                
                if task_db:
                    task_db.status = TaskStatus.FAILED
                    task_db.error_message = f"Blocked: {reason}"
                    task_db.completed_at = datetime.utcnow()
                    db.commit()
            
            # Log blocking
            await self.audit_logger.log_task_blocked(task, reason)
            
            self.metrics.tasks_failed += 1
            
        except Exception as e:
            logger.error(f"Failed to handle blocked task: {str(e)}")
    
    async def _handle_rejected_task(self, task: DelegatedTask, approval: Any):
        """Handle task rejected by human approval"""
        try:
            with get_db() as db:
                task_db = db.query(DelegatedTask).filter(
                    DelegatedTask.id == task.id
                ).first()
                
                if task_db:
                    task_db.status = TaskStatus.REJECTED
                    task_db.error_message = f"Rejected: {approval.feedback}"
                    task_db.completed_at = datetime.utcnow()
                    db.commit()
            
            # Log rejection
            await self.audit_logger.log_task_rejected(task, approval)
            
            self.metrics.tasks_failed += 1
            
        except Exception as e:
            logger.error(f"Failed to handle rejected task: {str(e)}")
    
    async def _handle_task_error(self, task_id: str, error: Exception):
        """Handle task processing error"""
        try:
            with get_db() as db:
                task = db.query(DelegatedTask).filter(
                    DelegatedTask.id == task_id
                ).first()
                
                if task:
                    task.status = TaskStatus.FAILED
                    task.error_message = str(error)
                    task.completed_at = datetime.utcnow()
                    db.commit()
                    
                    # Log error
                    await self.audit_logger.log_task_error(task, error)
            
            self.metrics.tasks_failed += 1
            
        except Exception as e:
            logger.error(f"Failed to handle task error: {str(e)}")
    
    async def _load_persona_config(self):
        """Load persona configuration"""
        try:
            with get_db() as db:
                persona = db.query(Persona).filter(
                    Persona.id == self.persona_id
                ).first()
                
                if not persona:
                    raise ValueError(f"Persona {self.persona_id} not found")
                
                # Check capability level
                if persona.capability_level != CapabilityLevel.L4_DELEGATED_AGENT:
                    logger.warning(
                        f"Persona capability is {persona.capability_level.value}, "
                        f"expected L4_DELEGATED_AGENT"
                    )
                
                # Load configuration
                config = persona.config or {}
                
                # Apply configuration
                self.max_concurrent_tasks = config.get("max_concurrent_tasks", 5)
                self.learning_enabled = config.get("learning_enabled", True)
                self.auto_pause_on_error = config.get("auto_pause_on_error", True)
                
                # Set HILT mode
                hilt_mode = config.get("hilt_mode", "selective")
                self.hilt_controller.set_mode(HILTMode(hilt_mode))
                
                logger.info(f"Loaded configuration for persona {self.persona_id}")
                
        except Exception as e:
            logger.error(f"Failed to load persona config: {str(e)}")
            raise
    
    async def _wait_for_task(self, task_id: str):
        """Wait for a specific task to complete"""
        max_wait = 300  # 5 minutes
        start = datetime.utcnow()
        
        while task_id in self.active_tasks:
            if (datetime.utcnow() - start).total_seconds() > max_wait:
                logger.warning(f"Timeout waiting for task {task_id}")
                break
            await asyncio.sleep(1)
    
    def _update_metrics(self, task: DelegatedTask, execution_result: Dict[str, Any]):
        """Update agent metrics"""
        try:
            # Update confidence average
            if task.confidence_score:
                if self.metrics.average_confidence == 0:
                    self.metrics.average_confidence = task.confidence_score
                else:
                    # Running average
                    total_tasks = (
                        self.metrics.tasks_completed + 
                        self.metrics.tasks_failed
                    )
                    self.metrics.average_confidence = (
                        (self.metrics.average_confidence * (total_tasks - 1) + 
                         task.confidence_score) / total_tasks
                    )
            
            # Update execution time average
            if task.execution_time:
                if self.metrics.average_execution_time == 0:
                    self.metrics.average_execution_time = task.execution_time
                else:
                    total_tasks = (
                        self.metrics.tasks_completed + 
                        self.metrics.tasks_failed
                    )
                    self.metrics.average_execution_time = (
                        (self.metrics.average_execution_time * (total_tasks - 1) + 
                         task.execution_time) / total_tasks
                    )
            
            # Update approval metrics
            if task.requires_approval:
                self.metrics.tasks_requiring_approval += 1
                
        except Exception as e:
            logger.error(f"Failed to update metrics: {str(e)}")
    
    async def _adjust_ontology(self, adjustment: Dict[str, Any]):
        """Adjust ontology based on learning"""
        try:
            for dimension, change in adjustment.items():
                await self.ontology_engine.adjust_dimension(
                    self.persona_id,
                    dimension,
                    change["new_value"],
                    f"Agent learning: {change.get('reason', 'Execution feedback')}"
                )
        except Exception as e:
            logger.error(f"Failed to adjust ontology: {str(e)}")
    
    async def _adjust_boundaries(self, adjustment: Dict[str, Any]):
        """Adjust boundaries based on learning"""
        try:
            for boundary_id, change in adjustment.items():
                await self.boundary_enforcer.adjust_boundary(
                    boundary_id,
                    change
                )
        except Exception as e:
            logger.error(f"Failed to adjust boundaries: {str(e)}")

# Export main agent class
__all__ = ["L4DelegatedAgent", "AgentState", "AgentMetrics"]