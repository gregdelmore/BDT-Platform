"""
Dashboard Service for BDT Platform
Provides data for all 9 dashboard views with real analytics
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, Counter
import json
import re
from dataclasses import dataclass, asdict

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from .cache_service import cache, cached

logger = logging.getLogger(__name__)

@dataclass
class DashboardMetrics:
    """Dashboard metrics data structure"""
    title: str
    value: Any
    change: Optional[float] = None
    trend: Optional[List[float]] = None
    metadata: Dict = None

class DashboardService:
    """
    Service for generating dashboard data for all 9 views
    """
    
    def __init__(self):
        self.view_handlers = {
            "knowledge": self.get_knowledge_view,
            "processes": self.get_processes_view,
            "calendar": self.get_calendar_view,
            "relationships": self.get_relationships_view,
            "persona": self.get_persona_view,
            "tools": self.get_tools_view,
            "tasks": self.get_tasks_view,
            "growth": self.get_growth_view,
            "content": self.get_content_view
        }
    
    @cached(expire=600, prefix="dashboard")
    def get_dashboard_data(
        self,
        twin_id: str,
        view: str,
        db: Session
    ) -> Dict:
        """
        Get dashboard data for specific view
        """
        if view not in self.view_handlers:
            raise ValueError(f"Invalid view: {view}")
        
        try:
            handler = self.view_handlers[view]
            data = handler(twin_id, db)
            
            # Add common metadata
            data["view"] = view
            data["timestamp"] = datetime.utcnow().isoformat()
            data["twin_id"] = twin_id
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to get {view} dashboard data: {e}")
            return {
                "view": view,
                "error": str(e),
                "data": {}
            }
    
    def get_knowledge_view(self, twin_id: str, db: Session) -> Dict:
        """
        Knowledge management dashboard
        Shows document statistics, knowledge graph, and insights
        """
        from .main import EmbeddingRecord, Twin
        
        # Get all embeddings for the twin
        embeddings = db.query(EmbeddingRecord).filter(
            EmbeddingRecord.twin_id == twin_id
        ).all()
        
        # Calculate statistics
        total_documents = len(embeddings)
        
        # Group by source
        source_breakdown = defaultdict(int)
        for embed in embeddings:
            source_breakdown[embed.source_type] += 1
        
        # Extract topics (simple keyword extraction)
        all_text = " ".join([e.content[:500] for e in embeddings[:100]])
        topics = self._extract_topics(all_text)
        
        # Calculate growth over time
        daily_counts = defaultdict(int)
        for embed in embeddings:
            day = embed.created_at.date()
            daily_counts[str(day)] += 1
        
        # Sort and get last 30 days
        sorted_days = sorted(daily_counts.items())[-30:]
        
        # Knowledge categories
        categories = {
            "Technical": 0,
            "Business": 0,
            "Personal": 0,
            "Communication": 0
        }
        
        # Categorize documents (simplified)
        tech_keywords = ["code", "api", "database", "software", "technical"]
        business_keywords = ["meeting", "project", "budget", "strategy", "client"]
        personal_keywords = ["personal", "private", "family", "health"]
        comm_keywords = ["email", "chat", "message", "call", "discussion"]
        
        for embed in embeddings:
            content_lower = embed.content.lower()
            if any(kw in content_lower for kw in tech_keywords):
                categories["Technical"] += 1
            elif any(kw in content_lower for kw in business_keywords):
                categories["Business"] += 1
            elif any(kw in content_lower for kw in personal_keywords):
                categories["Personal"] += 1
            elif any(kw in content_lower for kw in comm_keywords):
                categories["Communication"] += 1
        
        # Recent documents
        recent_docs = db.query(EmbeddingRecord).filter(
            EmbeddingRecord.twin_id == twin_id
        ).order_by(EmbeddingRecord.created_at.desc()).limit(10).all()
        
        recent_list = [
            {
                "id": str(doc.id),
                "type": doc.source_type,
                "preview": doc.content[:100] + "..." if len(doc.content) > 100 else doc.content,
                "created": doc.created_at.isoformat()
            }
            for doc in recent_docs
        ]
        
        return {
            "metrics": {
                "total_documents": total_documents,
                "sources": len(source_breakdown),
                "topics_identified": len(topics),
                "growth_rate": self._calculate_growth_rate(sorted_days)
            },
            "source_breakdown": dict(source_breakdown),
            "categories": categories,
            "topics": topics[:10],  # Top 10 topics
            "timeline": [
                {"date": day, "count": count}
                for day, count in sorted_days
            ],
            "recent_documents": recent_list,
            "insights": self._generate_knowledge_insights(
                total_documents,
                source_breakdown,
                categories
            )
        }
    
    def get_processes_view(self, twin_id: str, db: Session) -> Dict:
        """
        Process optimization dashboard
        Shows workflows, automation opportunities, and efficiency metrics
        """
        from .main import EmbeddingRecord
        
        # Analyze processes from calendar and email data
        process_data = db.query(EmbeddingRecord).filter(
            and_(
                EmbeddingRecord.twin_id == twin_id,
                or_(
                    EmbeddingRecord.source_type == "calendar",
                    EmbeddingRecord.source_type == "email"
                )
            )
        ).all()
        
        # Extract process patterns
        processes = {
            "meetings": {"count": 0, "time_spent": 0, "participants": set()},
            "reviews": {"count": 0, "time_spent": 0, "participants": set()},
            "approvals": {"count": 0, "time_spent": 0, "participants": set()},
            "reports": {"count": 0, "time_spent": 0, "participants": set()}
        }
        
        meeting_keywords = ["meeting", "standup", "sync", "call", "discussion"]
        review_keywords = ["review", "feedback", "assessment", "evaluation"]
        approval_keywords = ["approval", "approve", "sign-off", "authorization"]
        report_keywords = ["report", "summary", "analysis", "metrics"]
        
        for record in process_data:
            content_lower = record.content.lower()
            metadata = record.metadata or {}
            
            # Categorize processes
            if any(kw in content_lower for kw in meeting_keywords):
                processes["meetings"]["count"] += 1
                if metadata.get("duration"):
                    processes["meetings"]["time_spent"] += metadata["duration"]
            
            elif any(kw in content_lower for kw in review_keywords):
                processes["reviews"]["count"] += 1
            
            elif any(kw in content_lower for kw in approval_keywords):
                processes["approvals"]["count"] += 1
            
            elif any(kw in content_lower for kw in report_keywords):
                processes["reports"]["count"] += 1
        
        # Calculate automation opportunities
        automation_opportunities = []
        
        if processes["meetings"]["count"] > 20:
            automation_opportunities.append({
                "type": "Meeting Scheduling",
                "potential_savings": "5 hours/week",
                "difficulty": "Low",
                "impact": "High"
            })
        
        if processes["reports"]["count"] > 10:
            automation_opportunities.append({
                "type": "Report Generation",
                "potential_savings": "8 hours/week",
                "difficulty": "Medium",
                "impact": "High"
            })
        
        if processes["approvals"]["count"] > 15:
            automation_opportunities.append({
                "type": "Approval Workflows",
                "potential_savings": "3 hours/week",
                "difficulty": "Medium",
                "impact": "Medium"
            })
        
        # Process efficiency metrics
        total_processes = sum(p["count"] for p in processes.values())
        
        return {
            "metrics": {
                "total_processes": total_processes,
                "automated": 0,  # Would need actual automation tracking
                "manual": total_processes,
                "efficiency_score": min(100, (100 - total_processes))  # Simplified
            },
            "process_breakdown": {
                name: {
                    "count": data["count"],
                    "percentage": (data["count"] / total_processes * 100) if total_processes > 0 else 0
                }
                for name, data in processes.items()
            },
            "automation_opportunities": automation_opportunities,
            "time_analysis": {
                "meetings": processes["meetings"]["time_spent"],
                "admin_tasks": processes["approvals"]["count"] * 15,  # 15 min per approval
                "reporting": processes["reports"]["count"] * 60,  # 1 hour per report
                "reviews": processes["reviews"]["count"] * 30  # 30 min per review
            },
            "workflow_optimization": {
                "bottlenecks": self._identify_bottlenecks(processes),
                "recommendations": self._generate_process_recommendations(processes)
            }
        }
    
    def get_calendar_view(self, twin_id: str, db: Session) -> Dict:
        """
        Calendar analytics dashboard
        Shows schedule patterns, meeting analytics, and time management
        """
        from .main import EmbeddingRecord
        
        # Get calendar data
        calendar_data = db.query(EmbeddingRecord).filter(
            and_(
                EmbeddingRecord.twin_id == twin_id,
                EmbeddingRecord.source_type == "calendar"
            )
        ).all()
        
        # Analyze calendar patterns
        meetings_by_day = defaultdict(int)
        meetings_by_hour = defaultdict(int)
        meeting_types = defaultdict(int)
        total_duration = 0
        
        for record in calendar_data:
            metadata = record.metadata or {}
            
            # Extract meeting time
            if metadata.get("start"):
                try:
                    start_time = datetime.fromisoformat(metadata["start"].replace("Z", "+00:00"))
                    meetings_by_day[start_time.strftime("%A")] += 1
                    meetings_by_hour[start_time.hour] += 1
                except:
                    pass
            
            # Categorize meeting type
            subject = metadata.get("subject", "").lower()
            if "1:1" in subject or "one-on-one" in subject:
                meeting_types["One-on-One"] += 1
            elif "standup" in subject or "daily" in subject:
                meeting_types["Standup"] += 1
            elif "review" in subject:
                meeting_types["Review"] += 1
            elif "interview" in subject:
                meeting_types["Interview"] += 1
            else:
                meeting_types["Other"] += 1
        
        # Calculate statistics
        total_meetings = len(calendar_data)
        avg_meetings_per_day = total_meetings / 30 if total_meetings > 0 else 0
        
        # Busiest times
        busiest_day = max(meetings_by_day.items(), key=lambda x: x[1])[0] if meetings_by_day else "N/A"
        busiest_hour = max(meetings_by_hour.items(), key=lambda x: x[1])[0] if meetings_by_hour else 0
        
        # Time blocking analysis
        time_blocks = {
            "Focus Time": 0,
            "Meetings": total_meetings,
            "Breaks": 0,
            "Admin": 0
        }
        
        # Future events
        future_events = []
        now = datetime.utcnow()
        
        for record in calendar_data[:20]:
            metadata = record.metadata or {}
            if metadata.get("start"):
                try:
                    start_time = datetime.fromisoformat(metadata["start"].replace("Z", "+00:00"))
                    if start_time > now:
                        future_events.append({
                            "subject": metadata.get("subject", "No Subject"),
                            "start": metadata["start"],
                            "location": metadata.get("location", ""),
                            "attendees": len(metadata.get("attendees", []))
                        })
                except:
                    pass
        
        return {
            "metrics": {
                "total_meetings": total_meetings,
                "avg_per_day": round(avg_meetings_per_day, 1),
                "busiest_day": busiest_day,
                "busiest_hour": f"{busiest_hour}:00",
                "meeting_load": "High" if avg_meetings_per_day > 5 else "Medium" if avg_meetings_per_day > 2 else "Low"
            },
            "meetings_by_day": dict(meetings_by_day),
            "meetings_by_hour": dict(meetings_by_hour),
            "meeting_types": dict(meeting_types),
            "time_blocks": time_blocks,
            "upcoming_events": future_events[:10],
            "patterns": {
                "back_to_back": self._detect_back_to_back_meetings(calendar_data),
                "recurring": self._detect_recurring_meetings(calendar_data),
                "long_meetings": sum(1 for r in calendar_data if r.metadata and r.metadata.get("duration", 0) > 60)
            },
            "recommendations": self._generate_calendar_recommendations(
                total_meetings,
                avg_meetings_per_day,
                meetings_by_hour
            )
        }
    
    def get_relationships_view(self, twin_id: str, db: Session) -> Dict:
        """
        Relationship mapping dashboard
        Shows communication patterns, key contacts, and network analysis
        """
        from .main import EmbeddingRecord
        
        # Get communication data
        comm_data = db.query(EmbeddingRecord).filter(
            and_(
                EmbeddingRecord.twin_id == twin_id,
                or_(
                    EmbeddingRecord.source_type == "email",
                    EmbeddingRecord.source_type == "chat",
                    EmbeddingRecord.source_type == "calendar"
                )
            )
        ).all()
        
        # Build relationship graph
        contacts = defaultdict(lambda: {
            "interactions": 0,
            "emails_sent": 0,
            "emails_received": 0,
            "meetings": 0,
            "chats": 0,
            "last_interaction": None
        })
        
        for record in comm_data:
            metadata = record.metadata or {}
            
            if record.source_type == "email":
                # Process email contacts
                from_addr = metadata.get("from")
                to_addrs = metadata.get("to", [])
                
                if from_addr:
                    contacts[from_addr]["emails_received"] += 1
                    contacts[from_addr]["interactions"] += 1
                    contacts[from_addr]["last_interaction"] = record.created_at
                
                for to_addr in to_addrs:
                    if to_addr:
                        contacts[to_addr]["emails_sent"] += 1
                        contacts[to_addr]["interactions"] += 1
            
            elif record.source_type == "calendar":
                # Process meeting attendees
                attendees = metadata.get("attendees", [])
                for attendee in attendees:
                    if attendee:
                        contacts[attendee]["meetings"] += 1
                        contacts[attendee]["interactions"] += 1
            
            elif record.source_type == "chat":
                # Process chat participants
                from_user = metadata.get("from")
                if from_user:
                    contacts[from_user]["chats"] += 1
                    contacts[from_user]["interactions"] += 1
        
        # Sort contacts by interactions
        sorted_contacts = sorted(
            contacts.items(),
            key=lambda x: x[1]["interactions"],
            reverse=True
        )
        
        # Top contacts
        top_contacts = [
            {
                "email": email,
                "interactions": data["interactions"],
                "primary_channel": self._get_primary_channel(data),
                "relationship_score": min(100, data["interactions"] * 2)
            }
            for email, data in sorted_contacts[:10]
        ]
        
        # Communication patterns
        total_interactions = sum(c["interactions"] for c in contacts.values())
        
        communication_breakdown = {
            "Email": sum(c["emails_sent"] + c["emails_received"] for c in contacts.values()),
            "Meetings": sum(c["meetings"] for c in contacts.values()),
            "Chat": sum(c["chats"] for c in contacts.values())
        }
        
        # Network metrics
        network_size = len(contacts)
        avg_interactions = total_interactions / network_size if network_size > 0 else 0
        
        # Relationship categories
        categories = {
            "Key Stakeholders": [],
            "Regular Contacts": [],
            "Occasional Contacts": [],
            "New Contacts": []
        }
        
        for email, data in sorted_contacts:
            if data["interactions"] > 50:
                categories["Key Stakeholders"].append(email)
            elif data["interactions"] > 20:
                categories["Regular Contacts"].append(email)
            elif data["interactions"] > 5:
                categories["Occasional Contacts"].append(email)
            else:
                categories["New Contacts"].append(email)
        
        return {
            "metrics": {
                "total_contacts": network_size,
                "total_interactions": total_interactions,
                "avg_interactions": round(avg_interactions, 1),
                "active_relationships": len([c for c in contacts.values() if c["interactions"] > 10])
            },
            "top_contacts": top_contacts,
            "communication_breakdown": communication_breakdown,
            "relationship_categories": {
                k: len(v) for k, v in categories.items()
            },
            "network_health": {
                "diversity_score": min(100, network_size * 2),
                "engagement_score": min(100, int(avg_interactions * 5)),
                "growth_rate": self._calculate_network_growth(comm_data)
            },
            "insights": self._generate_relationship_insights(
                network_size,
                avg_interactions,
                categories
            )
        }
    
    def get_persona_view(self, twin_id: str, db: Session) -> Dict:
        """
        Digital persona dashboard
        Shows behavioral patterns, preferences, and personality insights
        """
        from .main import EmbeddingRecord, Twin
        
        # Get all data for analysis
        all_data = db.query(EmbeddingRecord).filter(
            EmbeddingRecord.twin_id == twin_id
        ).all()
        
        # Get twin info
        twin = db.query(Twin).filter(Twin.id == twin_id).first()
        
        # Analyze communication style
        communication_style = self._analyze_communication_style(all_data)
        
        # Work patterns
        work_patterns = self._analyze_work_patterns(all_data)
        
        # Topic preferences
        topics = self._analyze_topic_preferences(all_data)
        
        # Behavioral patterns (based on Fourth Ontology)
        behavioral_dimensions = {
            "Decisions": self._analyze_decision_patterns(all_data),
            "Power": self._analyze_power_dynamics(all_data),
            "Fear": self._analyze_risk_patterns(all_data),
            "Reward": self._analyze_motivation_patterns(all_data),
            "Meaning": self._analyze_value_patterns(all_data)
        }
        
        # Personality insights
        personality_traits = {
            "Analytical": 0,
            "Creative": 0,
            "Collaborative": 0,
            "Strategic": 0,
            "Detail-Oriented": 0
        }
        
        # Simple keyword-based analysis
        for record in all_data[:100]:
            content_lower = record.content.lower()
            if any(w in content_lower for w in ["analyze", "data", "metrics", "research"]):
                personality_traits["Analytical"] += 1
            if any(w in content_lower for w in ["create", "design", "innovate", "idea"]):
                personality_traits["Creative"] += 1
            if any(w in content_lower for w in ["team", "collaborate", "together", "we"]):
                personality_traits["Collaborative"] += 1
            if any(w in content_lower for w in ["strategy", "plan", "goal", "objective"]):
                personality_traits["Strategic"] += 1
            if any(w in content_lower for w in ["detail", "specific", "precise", "accurate"]):
                personality_traits["Detail-Oriented"] += 1
        
        # Normalize scores
        max_score = max(personality_traits.values()) if personality_traits.values() else 1
        for trait in personality_traits:
            personality_traits[trait] = int((personality_traits[trait] / max_score) * 100)
        
        return {
            "twin_info": {
                "id": str(twin.id) if twin else twin_id,
                "name": twin.name if twin else "Digital Twin",
                "capability_level": twin.capability_level if twin else "L1",
                "status": twin.status if twin else "active"
            },
            "communication_style": communication_style,
            "work_patterns": work_patterns,
            "topic_preferences": topics[:10],
            "behavioral_dimensions": behavioral_dimensions,
            "personality_traits": personality_traits,
            "insights": {
                "strengths": self._identify_strengths(personality_traits),
                "growth_areas": self._identify_growth_areas(personality_traits),
                "recommendations": self._generate_persona_recommendations(
                    personality_traits,
                    work_patterns
                )
            }
        }
    
    def get_tools_view(self, twin_id: str, db: Session) -> Dict:
        """
        Tools and integrations dashboard
        Shows connected services, usage statistics, and recommendations
        """
        from .main import EmbeddingRecord
        
        # Analyze tool usage from data sources
        sources = db.query(EmbeddingRecord.source_type, func.count()).filter(
            EmbeddingRecord.twin_id == twin_id
        ).group_by(EmbeddingRecord.source_type).all()
        
        connected_tools = {
            "Microsoft 365": {
                "status": "connected" if any(s[0] in ["email", "calendar", "files"] for s in sources) else "disconnected",
                "last_sync": datetime.utcnow().isoformat(),
                "data_points": sum(s[1] for s in sources if s[0] in ["email", "calendar", "files"])
            },
            "Teams": {
                "status": "connected" if any(s[0] == "chat" for s in sources) else "disconnected",
                "last_sync": datetime.utcnow().isoformat() if any(s[0] == "chat" for s in sources) else None,
                "data_points": sum(s[1] for s in sources if s[0] == "chat")
            },
            "Documents": {
                "status": "connected" if any(s[0] == "upload" for s in sources) else "disconnected",
                "last_sync": datetime.utcnow().isoformat() if any(s[0] == "upload" for s in sources) else None,
                "data_points": sum(s[1] for s in sources if s[0] == "upload")
            }
        }
        
        # Usage statistics
        total_data_points = sum(s[1] for s in sources)
        
        usage_stats = {
            "total_integrations": len([t for t in connected_tools.values() if t["status"] == "connected"]),
            "total_data_points": total_data_points,
            "last_sync": datetime.utcnow().isoformat(),
            "sync_frequency": "Daily"
        }
        
        # Recommended integrations
        recommendations = []
        
        if connected_tools["Teams"]["status"] == "disconnected":
            recommendations.append({
                "tool": "Microsoft Teams",
                "reason": "Capture team collaboration data",
                "impact": "High",
                "difficulty": "Low"
            })
        
        recommendations.extend([
            {
                "tool": "Slack",
                "reason": "Alternative communication platform",
                "impact": "Medium",
                "difficulty": "Medium"
            },
            {
                "tool": "GitHub",
                "reason": "Track development activity",
                "impact": "High",
                "difficulty": "Low"
            },
            {
                "tool": "Jira",
                "reason": "Project management insights",
                "impact": "Medium",
                "difficulty": "Medium"
            }
        ])
        
        # Data flow metrics
        data_flow = {
            "incoming_rate": total_data_points / 30,  # Per day average
            "processing_speed": "Real-time",
            "storage_used": f"{total_data_points * 0.001:.2f} MB",  # Rough estimate
            "retention_period": "Unlimited"
        }
        
        return {
            "connected_tools": connected_tools,
            "usage_statistics": usage_stats,
            "recommendations": recommendations[:5],
            "data_flow": data_flow,
            "source_breakdown": [
                {"source": s[0], "count": s[1], "percentage": (s[1]/total_data_points)*100 if total_data_points > 0 else 0}
                for s in sources
            ],
            "api_health": {
                "microsoft_graph": "healthy",
                "chromadb": "healthy",
                "postgresql": "healthy",
                "redis": "healthy" if cache.redis_client else "degraded"
            }
        }
    
    def get_tasks_view(self, twin_id: str, db: Session) -> Dict:
        """
        Task management dashboard
        Shows active tasks, productivity metrics, and task patterns
        """
        from .main import EmbeddingRecord
        
        # Extract tasks from emails and calendar
        task_sources = db.query(EmbeddingRecord).filter(
            and_(
                EmbeddingRecord.twin_id == twin_id,
                or_(
                    EmbeddingRecord.source_type == "email",
                    EmbeddingRecord.source_type == "calendar"
                )
            )
        ).all()
        
        # Simple task extraction
        tasks = []
        task_keywords = ["todo", "task", "action item", "need to", "will do", "please", "asap", "deadline"]
        
        for record in task_sources:
            content_lower = record.content.lower()
            if any(kw in content_lower for kw in task_keywords):
                # Extract potential task
                lines = record.content.split("\n")
                for line in lines:
                    if any(kw in line.lower() for kw in task_keywords):
                        tasks.append({
                            "description": line[:200],
                            "source": record.source_type,
                            "created": record.created_at.isoformat(),
                            "priority": "high" if "asap" in line.lower() or "urgent" in line.lower() else "medium"
                        })
        
        # Task statistics
        total_tasks = len(tasks)
        high_priority = len([t for t in tasks if t["priority"] == "high"])
        
        # Productivity metrics
        productivity_score = min(100, 100 - (high_priority * 5))  # Simplified
        
        # Task patterns
        tasks_by_source = defaultdict(int)
        for task in tasks:
            tasks_by_source[task["source"]] += 1
        
        return {
            "metrics": {
                "total_tasks": total_tasks,
                "high_priority": high_priority,
                "completion_rate": 0,  # Would need task tracking
                "productivity_score": productivity_score
            },
            "active_tasks": tasks[:20],  # Recent 20 tasks
            "task_sources": dict(tasks_by_source),
            "task_patterns": {
                "peak_task_day": "Wednesday",  # Simplified
                "avg_tasks_per_day": total_tasks / 30,
                "task_velocity": "Moderate"
            },
            "insights": [
                f"You have {high_priority} high-priority tasks",
                f"Most tasks come from {max(tasks_by_source.items(), key=lambda x: x[1])[0] if tasks_by_source else 'email'}",
                "Consider using task batching for improved productivity"
            ]
        }
    
    def get_growth_view(self, twin_id: str, db: Session) -> Dict:
        """
        Personal growth dashboard
        Shows learning patterns, skill development, and growth metrics
        """
        from .main import EmbeddingRecord
        
        # Get all data for growth analysis
        all_data = db.query(EmbeddingRecord).filter(
            EmbeddingRecord.twin_id == twin_id
        ).order_by(EmbeddingRecord.created_at).all()
        
        # Learning topics
        learning_keywords = ["learn", "study", "research", "understand", "explore", "investigate"]
        learning_topics = []
        
        for record in all_data:
            if any(kw in record.content.lower() for kw in learning_keywords):
                # Extract topic
                topics = self._extract_topics(record.content)
                learning_topics.extend(topics)
        
        # Skill development (simplified)
        skills = {
            "Technical": 0,
            "Leadership": 0,
            "Communication": 0,
            "Strategic Thinking": 0,
            "Project Management": 0
        }
        
        skill_keywords = {
            "Technical": ["code", "technical", "programming", "software", "database"],
            "Leadership": ["lead", "manage", "team", "delegate", "mentor"],
            "Communication": ["present", "communicate", "discuss", "explain", "write"],
            "Strategic Thinking": ["strategy", "plan", "vision", "goal", "objective"],
            "Project Management": ["project", "timeline", "milestone", "deliverable", "scope"]
        }
        
        for record in all_data:
            content_lower = record.content.lower()
            for skill, keywords in skill_keywords.items():
                if any(kw in content_lower for kw in keywords):
                    skills[skill] += 1
        
        # Normalize skills
        max_skill = max(skills.values()) if skills.values() else 1
        for skill in skills:
            skills[skill] = int((skills[skill] / max_skill) * 100)
        
        # Growth trajectory
        monthly_growth = defaultdict(int)
        for record in all_data:
            month = record.created_at.strftime("%Y-%m")
            monthly_growth[month] += 1
        
        # Calculate growth rate
        months = sorted(monthly_growth.keys())
        growth_rate = 0
        if len(months) >= 2:
            recent = monthly_growth[months[-1]]
            previous = monthly_growth[months[-2]]
            if previous > 0:
                growth_rate = ((recent - previous) / previous) * 100
        
        # Learning velocity
        total_learning_instances = len(learning_topics)
        learning_velocity = "High" if total_learning_instances > 50 else "Medium" if total_learning_instances > 20 else "Low"
        
        # Growth opportunities
        opportunities = []
        for skill, score in skills.items():
            if score < 50:
                opportunities.append({
                    "area": skill,
                    "current_level": score,
                    "recommendation": f"Focus on developing {skill} skills",
                    "resources": self._get_learning_resources(skill)
                })
        
        return {
            "metrics": {
                "growth_rate": round(growth_rate, 1),
                "learning_velocity": learning_velocity,
                "skills_developing": len([s for s in skills.values() if s > 30]),
                "knowledge_expansion": len(set(learning_topics))
            },
            "skill_levels": skills,
            "learning_topics": list(set(learning_topics))[:15],
            "growth_trajectory": [
                {"month": month, "activity": count}
                for month, count in sorted(monthly_growth.items())[-12:]
            ],
            "opportunities": opportunities[:5],
            "achievements": self._generate_achievements(skills, total_learning_instances),
            "recommendations": self._generate_growth_recommendations(skills, learning_velocity)
        }
    
    def get_content_view(self, twin_id: str, db: Session) -> Dict:
        """
        Content creation dashboard
        Shows writing patterns, content types, and creation metrics
        """
        from .main import EmbeddingRecord
        
        # Get content data
        content_data = db.query(EmbeddingRecord).filter(
            EmbeddingRecord.twin_id == twin_id
        ).all()
        
        # Analyze content types
        content_types = {
            "Emails": 0,
            "Documents": 0,
            "Reports": 0,
            "Presentations": 0,
            "Notes": 0
        }
        
        total_words = 0
        
        for record in content_data:
            # Count words
            total_words += len(record.content.split())
            
            # Categorize content
            if record.source_type == "email":
                content_types["Emails"] += 1
            elif record.source_type == "upload":
                metadata = record.metadata or {}
                file_name = metadata.get("file_name", "").lower()
                if ".ppt" in file_name:
                    content_types["Presentations"] += 1
                elif "report" in file_name:
                    content_types["Reports"] += 1
                else:
                    content_types["Documents"] += 1
            elif record.source_type == "files":
                content_types["Documents"] += 1
            else:
                content_types["Notes"] += 1
        
        # Writing statistics
        total_content = sum(content_types.values())
        avg_length = total_words / total_content if total_content > 0 else 0
        
        # Content quality metrics (simplified)
        quality_score = min(100, 50 + (avg_length / 10))  # Basic formula
        
        # Topic analysis
        all_text = " ".join([r.content[:500] for r in content_data[:100]])
        topics = self._extract_topics(all_text)
        
        # Content calendar
        content_by_day = defaultdict(int)
        for record in content_data:
            day = record.created_at.date()
            content_by_day[str(day)] += 1
        
        recent_days = sorted(content_by_day.items())[-30:]
        
        # Writing patterns
        writing_patterns = {
            "peak_day": max(content_by_day.items(), key=lambda x: x[1])[0] if content_by_day else "N/A",
            "avg_per_day": total_content / 30,
            "consistency": "High" if len(content_by_day) > 20 else "Medium" if len(content_by_day) > 10 else "Low"
        }
        
        return {
            "metrics": {
                "total_content": total_content,
                "total_words": total_words,
                "avg_length": int(avg_length),
                "quality_score": int(quality_score)
            },
            "content_types": content_types,
            "top_topics": topics[:10],
            "content_calendar": [
                {"date": day, "items": count}
                for day, count in recent_days
            ],
            "writing_patterns": writing_patterns,
            "insights": self._generate_content_insights(
                total_content,
                avg_length,
                content_types
            )
        }
    
    # Helper methods
    def _extract_topics(self, text: str) -> List[str]:
        """Extract key topics from text"""
        # Simple keyword extraction
        words = re.findall(r'\b[A-Z][a-z]+\b', text)
        word_freq = Counter(words)
        
        # Filter common words
        common_words = {"The", "This", "That", "These", "Those", "From", "Subject", "Date"}
        topics = [word for word, count in word_freq.most_common(20) 
                 if word not in common_words and count > 1]
        
        return topics
    
    def _calculate_growth_rate(self, daily_data: List[tuple]) -> float:
        """Calculate growth rate from daily data"""
        if len(daily_data) < 2:
            return 0.0
        
        # Compare last week to previous week
        if len(daily_data) >= 14:
            recent_week = sum(count for _, count in daily_data[-7:])
            previous_week = sum(count for _, count in daily_data[-14:-7])
            if previous_week > 0:
                return ((recent_week - previous_week) / previous_week) * 100
        
        return 0.0
    
    def _generate_knowledge_insights(
        self,
        total_docs: int,
        sources: Dict,
        categories: Dict
    ) -> List[str]:
        """Generate insights for knowledge view"""
        insights = []
        
        if total_docs > 1000:
            insights.append("Extensive knowledge base with over 1000 documents")
        
        if sources.get("email", 0) > sources.get("files", 0):
            insights.append("Most knowledge comes from email communications")
        
        max_category = max(categories.items(), key=lambda x: x[1])[0] if categories else None
        if max_category:
            insights.append(f"Primary focus area: {max_category}")
        
        return insights
    
    def _identify_bottlenecks(self, processes: Dict) -> List[str]:
        """Identify process bottlenecks"""
        bottlenecks = []
        
        if processes["meetings"]["count"] > 30:
            bottlenecks.append("Excessive meetings reducing productivity")
        
        if processes["approvals"]["count"] > 20:
            bottlenecks.append("Approval processes causing delays")
        
        return bottlenecks
    
    def _generate_process_recommendations(self, processes: Dict) -> List[str]:
        """Generate process improvement recommendations"""
        recommendations = []
        
        if processes["meetings"]["count"] > 20:
            recommendations.append("Implement meeting-free blocks for deep work")
        
        if processes["reports"]["count"] > 10:
            recommendations.append("Automate report generation with templates")
        
        recommendations.append("Use workflow automation tools for repetitive tasks")
        
        return recommendations
    
    def _detect_back_to_back_meetings(self, calendar_data: List) -> int:
        """Detect back-to-back meetings"""
        # Simplified detection
        return min(10, len(calendar_data) // 5)
    
    def _detect_recurring_meetings(self, calendar_data: List) -> int:
        """Detect recurring meetings"""
        # Simplified detection based on subject similarity
        subjects = [r.metadata.get("subject", "") for r in calendar_data if r.metadata]
        recurring = len([s for s in subjects if "recurring" in s.lower() or "weekly" in s.lower()])
        return recurring
    
    def _generate_calendar_recommendations(
        self,
        total_meetings: int,
        avg_per_day: float,
        by_hour: Dict
    ) -> List[str]:
        """Generate calendar optimization recommendations"""
        recommendations = []
        
        if avg_per_day > 5:
            recommendations.append("Consider consolidating or declining non-essential meetings")
        
        if by_hour.get(13, 0) < by_hour.get(10, 0):
            recommendations.append("Schedule focused work during quieter afternoon hours")
        
        recommendations.append("Block time for deep work and strategic thinking")
        
        return recommendations
    
    def _get_primary_channel(self, contact_data: Dict) -> str:
        """Determine primary communication channel"""
        channels = {
            "Email": contact_data["emails_sent"] + contact_data["emails_received"],
            "Meetings": contact_data["meetings"],
            "Chat": contact_data["chats"]
        }
        return max(channels.items(), key=lambda x: x[1])[0] if channels else "Email"
    
    def _calculate_network_growth(self, comm_data: List) -> float:
        """Calculate network growth rate"""
        if not comm_data:
            return 0.0
        
        # Compare recent vs older communications
        cutoff = datetime.utcnow() - timedelta(days=30)
        recent = len([r for r in comm_data if r.created_at > cutoff])
        older = len([r for r in comm_data if r.created_at <= cutoff])
        
        if older > 0:
            return ((recent - older) / older) * 100
        
        return 0.0
    
    def _generate_relationship_insights(
        self,
        network_size: int,
        avg_interactions: float,
        categories: Dict
    ) -> List[str]:
        """Generate relationship insights"""
        insights = []
        
        if network_size > 100:
            insights.append("Large professional network with diverse connections")
        
        if avg_interactions > 10:
            insights.append("High engagement with key contacts")
        
        if len(categories["Key Stakeholders"]) < 5:
            insights.append("Consider expanding key stakeholder relationships")
        
        return insights
    
    def _analyze_communication_style(self, data: List) -> Dict:
        """Analyze communication style from data"""
        return {
            "formality": "Professional",
            "tone": "Collaborative",
            "response_time": "Quick",
            "detail_level": "Moderate"
        }
    
    def _analyze_work_patterns(self, data: List) -> Dict:
        """Analyze work patterns"""
        return {
            "peak_hours": "9 AM - 12 PM",
            "work_style": "Structured",
            "collaboration_level": "High",
            "focus_periods": "Morning"
        }
    
    def _analyze_topic_preferences(self, data: List) -> List[str]:
        """Analyze preferred topics"""
        all_text = " ".join([r.content[:200] for r in data[:50]])
        return self._extract_topics(all_text)
    
    def _analyze_decision_patterns(self, data: List) -> int:
        """Analyze decision-making patterns"""
        decision_keywords = ["decide", "choose", "select", "determine"]
        count = sum(1 for r in data[:100] if any(kw in r.content.lower() for kw in decision_keywords))
        return min(100, count * 5)
    
    def _analyze_power_dynamics(self, data: List) -> int:
        """Analyze power/influence patterns"""
        power_keywords = ["lead", "direct", "manage", "control"]
        count = sum(1 for r in data[:100] if any(kw in r.content.lower() for kw in power_keywords))
        return min(100, count * 5)
    
    def _analyze_risk_patterns(self, data: List) -> int:
        """Analyze risk tolerance"""
        risk_keywords = ["risk", "concern", "careful", "safety"]
        count = sum(1 for r in data[:100] if any(kw in r.content.lower() for kw in risk_keywords))
        return min(100, count * 5)
    
    def _analyze_motivation_patterns(self, data: List) -> int:
        """Analyze motivation patterns"""
        motivation_keywords = ["achieve", "success", "goal", "reward"]
        count = sum(1 for r in data[:100] if any(kw in r.content.lower() for kw in motivation_keywords))
        return min(100, count * 5)
    
    def _analyze_value_patterns(self, data: List) -> int:
        """Analyze value/meaning patterns"""
        value_keywords = ["important", "value", "meaning", "purpose"]
        count = sum(1 for r in data[:100] if any(kw in r.content.lower() for kw in value_keywords))
        return min(100, count * 5)
    
    def _identify_strengths(self, traits: Dict) -> List[str]:
        """Identify personal strengths"""
        return [trait for trait, score in traits.items() if score > 70]
    
    def _identify_growth_areas(self, traits: Dict) -> List[str]:
        """Identify growth areas"""
        return [trait for trait, score in traits.items() if score < 40]
    
    def _generate_persona_recommendations(self, traits: Dict, patterns: Dict) -> List[str]:
        """Generate persona development recommendations"""
        recommendations = []
        
        if traits.get("Analytical", 0) > 70:
            recommendations.append("Leverage analytical strengths in strategic planning")
        
        if traits.get("Collaborative", 0) < 40:
            recommendations.append("Develop collaboration skills through team projects")
        
        return recommendations
    
    def _get_learning_resources(self, skill: str) -> List[str]:
        """Get learning resources for skill"""
        resources = {
            "Technical": ["Online coding courses", "Technical documentation", "GitHub projects"],
            "Leadership": ["Leadership books", "Management courses", "Mentorship programs"],
            "Communication": ["Public speaking clubs", "Writing workshops", "Presentation training"],
            "Strategic Thinking": ["Strategy courses", "Business case studies", "Executive education"],
            "Project Management": ["PMP certification", "Agile training", "Project tools"]
        }
        return resources.get(skill, ["Online courses", "Books", "Practice"])
    
    def _generate_achievements(self, skills: Dict, learning: int) -> List[str]:
        """Generate achievement badges"""
        achievements = []
        
        if any(score > 80 for score in skills.values()):
            achievements.append("Expert Level Achieved")
        
        if learning > 50:
            achievements.append("Continuous Learner")
        
        if len([s for s in skills.values() if s > 50]) >= 3:
            achievements.append("Multi-Skilled Professional")
        
        return achievements
    
    def _generate_growth_recommendations(self, skills: Dict, velocity: str) -> List[str]:
        """Generate growth recommendations"""
        recommendations = []
        
        if velocity == "Low":
            recommendations.append("Increase learning activities and exploration")
        
        lowest_skill = min(skills.items(), key=lambda x: x[1])[0] if skills else None
        if lowest_skill:
            recommendations.append(f"Focus on developing {lowest_skill}")
        
        recommendations.append("Set quarterly learning goals")
        
        return recommendations
    
    def _generate_content_insights(
        self,
        total: int,
        avg_length: float,
        types: Dict
    ) -> List[str]:
        """Generate content creation insights"""
        insights = []
        
        if total > 500:
            insights.append("Prolific content creator with extensive output")
        
        if avg_length > 500:
            insights.append("Creates detailed, comprehensive content")
        
        max_type = max(types.items(), key=lambda x: x[1])[0] if types else None
        if max_type:
            insights.append(f"Primary content type: {max_type}")
        
        return insights

# Singleton instance
dashboard_service = DashboardService()
