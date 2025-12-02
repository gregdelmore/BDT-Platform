"""
BDT Phase 2: Fourth Ontology Engine
Core behavioral framework that maps human patterns across five dimensions:
- Decisions: Analysis depth, data requirements, approval patterns
- Power: Autonomy boundaries, escalation triggers, delegation comfort
- Fear: Risk tolerance, safety requirements, verification needs
- Reward: Motivation patterns, achievement metrics, feedback preferences
- Meaning: Value alignments, priority frameworks, significance thresholds
"""

import asyncio
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
import json
from enum import Enum
import re
from openai import AsyncOpenAI
import hashlib

from core.config import OntologyDimension, settings
from core.database import Document, Pattern, PersonaOntology


@dataclass
class OntologyScore:
    """Individual dimension score with evidence"""
    dimension: OntologyDimension
    score: float  # 0-100
    confidence: float  # 0-1
    evidence_count: int
    evidence_sources: List[str] = field(default_factory=list)
    extracted_patterns: List[str] = field(default_factory=list)
    adjustable_parameter: str = ""
    parameter_value: float = 0.5
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class BehavioralPattern:
    """Extracted behavioral pattern with metadata"""
    pattern_type: str
    description: str
    frequency: float
    confidence: float
    supporting_documents: List[str]
    temporal_distribution: Dict[str, float]  # hour -> frequency
    related_entities: List[str]  # people, systems, topics
    dimension_impacts: Dict[OntologyDimension, float]


@dataclass
class FourthOntology:
    """Complete Fourth Ontology profile for a persona"""
    persona_id: str
    dimensions: Dict[OntologyDimension, OntologyScore]
    behavioral_patterns: List[BehavioralPattern]
    negative_space: List[str]  # Things they DON'T do
    confidence_overall: float
    data_coverage: float  # Percentage of expected data types available
    last_extraction: datetime
    extraction_metadata: Dict[str, Any]


class FourthOntologyEngine:
    """
    Production-ready Fourth Ontology extraction and management engine
    Analyzes behavioral patterns from ingested data to build ontology profiles
    """
    
    def __init__(self):
        self.openai = AsyncOpenAI(api_key=settings.openai_api_key)
        self.dimension_prompts = self._initialize_dimension_prompts()
        self.pattern_extractors = self._initialize_pattern_extractors()
        self.negative_space_detector = NegativeSpaceDetector()
        
    def _initialize_dimension_prompts(self) -> Dict[OntologyDimension, str]:
        """Initialize analysis prompts for each dimension"""
        return {
            OntologyDimension.DECISION: """
                Analyze decision-making patterns:
                1. How quickly do they make decisions? (immediate vs deliberate)
                2. What data/information do they require before deciding?
                3. Do they seek consensus or decide independently?
                4. What's their comfort level with reversible vs irreversible decisions?
                5. How do they handle ambiguity in decision-making?
                
                Look for: response times, research depth, consultation patterns, 
                approval seeking, decision reversal frequency.
            """,
            
            OntologyDimension.POWER: """
                Analyze power and autonomy patterns:
                1. What's their delegation style and frequency?
                2. Which decisions do they keep vs delegate?
                3. When do they escalate vs handle independently?
                4. How do they react to authority and control?
                5. What are their autonomy boundaries?
                
                Look for: delegation language, escalation triggers, control retention,
                authority references, independence indicators.
            """,
            
            OntologyDimension.FEAR: """
                Analyze risk tolerance and safety patterns:
                1. What risks do they consistently avoid?
                2. What safety measures do they always implement?
                3. How many verification steps do they require?
                4. What triggers defensive or cautious behavior?
                5. What are their "never touch" areas?
                
                Look for: verification requests, backup plans, safety buffers,
                avoidance patterns, protection mechanisms.
            """,
            
            OntologyDimension.REWARD: """
                Analyze motivation and reward patterns:
                1. What achievements do they celebrate or mention?
                2. How do they seek or respond to recognition?
                3. What metrics do they track for success?
                4. What type of feedback motivates them?
                5. What are their intrinsic vs extrinsic motivators?
                
                Look for: achievement mentions, metric tracking, feedback seeking,
                celebration patterns, goal-setting behavior.
            """,
            
            OntologyDimension.MEANING: """
                Analyze value and purpose patterns:
                1. What themes appear consistently in their communication?
                2. What do they prioritize when resources are limited?
                3. What values guide their decision-making?
                4. How do they define importance and significance?
                5. What gives them a sense of purpose?
                
                Look for: value statements, prioritization patterns, mission alignment,
                significance markers, purpose-driven language.
            """
        }
    
    def _initialize_pattern_extractors(self) -> Dict[str, Any]:
        """Initialize behavioral pattern extraction rules"""
        return {
            "communication": CommunicationPatternExtractor(),
            "temporal": TemporalPatternExtractor(),
            "collaboration": CollaborationPatternExtractor(),
            "decision": DecisionPatternExtractor(),
            "tool_usage": ToolUsagePatternExtractor()
        }
    
    async def extract_ontology(
        self,
        persona_id: str,
        documents: List[Document],
        existing_patterns: Optional[List[Pattern]] = None
    ) -> FourthOntology:
        """
        Main extraction method - analyzes documents to build Fourth Ontology
        
        Args:
            persona_id: Unique identifier for the persona
            documents: List of ingested documents to analyze
            existing_patterns: Previously extracted patterns to build upon
            
        Returns:
            Complete FourthOntology profile
        """
        print(f"🧬 Extracting Fourth Ontology for persona: {persona_id}")
        
        # Step 1: Extract behavioral patterns from documents
        behavioral_patterns = await self._extract_behavioral_patterns(documents)
        
        # Step 2: Analyze each dimension
        dimension_scores = await self._analyze_dimensions(documents, behavioral_patterns)
        
        # Step 3: Detect negative space (what they DON'T do)
        negative_space = await self.negative_space_detector.detect(
            documents, behavioral_patterns
        )
        
        # Step 4: Calculate overall confidence and coverage
        confidence = self._calculate_confidence(dimension_scores, len(documents))
        coverage = self._calculate_coverage(documents)
        
        # Step 5: Build complete ontology
        ontology = FourthOntology(
            persona_id=persona_id,
            dimensions=dimension_scores,
            behavioral_patterns=behavioral_patterns,
            negative_space=negative_space,
            confidence_overall=confidence,
            data_coverage=coverage,
            last_extraction=datetime.now(),
            extraction_metadata={
                "document_count": len(documents),
                "pattern_count": len(behavioral_patterns),
                "extraction_version": "2.0",
                "model_used": settings.openai_model
            }
        )
        
        print(f"✅ Fourth Ontology extraction complete. Confidence: {confidence:.2%}")
        return ontology
    
    async def _extract_behavioral_patterns(
        self, documents: List[Document]
    ) -> List[BehavioralPattern]:
        """Extract behavioral patterns using specialized extractors"""
        all_patterns = []
        
        for extractor_name, extractor in self.pattern_extractors.items():
            patterns = await extractor.extract(documents)
            all_patterns.extend(patterns)
            print(f"  📊 {extractor_name}: {len(patterns)} patterns found")
        
        # Deduplicate and merge similar patterns
        merged_patterns = self._merge_similar_patterns(all_patterns)
        
        return merged_patterns
    
    async def _analyze_dimensions(
        self,
        documents: List[Document],
        patterns: List[BehavioralPattern]
    ) -> Dict[OntologyDimension, OntologyScore]:
        """Analyze each ontology dimension using GPT-4"""
        dimension_scores = {}
        
        # Prepare document context (sample for efficiency)
        doc_sample = self._sample_documents(documents, max_docs=50)
        context = self._prepare_context(doc_sample, patterns)
        
        # Analyze each dimension in parallel
        tasks = []
        for dimension in OntologyDimension:
            task = self._analyze_single_dimension(dimension, context, patterns)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Map results to dimensions
        for dimension, score in zip(OntologyDimension, results):
            dimension_scores[dimension] = score
            
        return dimension_scores
    
    async def _analyze_single_dimension(
        self,
        dimension: OntologyDimension,
        context: str,
        patterns: List[BehavioralPattern]
    ) -> OntologyScore:
        """Analyze a single ontology dimension using GPT-4"""
        
        # Get relevant patterns for this dimension
        relevant_patterns = [
            p for p in patterns 
            if dimension in p.dimension_impacts and p.dimension_impacts[dimension] > 0.3
        ]
        
        # Build analysis prompt
        prompt = f"""
        Analyze the following behavioral data for the {dimension.value} dimension.
        
        {self.dimension_prompts[dimension]}
        
        Context from documents:
        {context[:3000]}  # Truncate for token limits
        
        Relevant behavioral patterns detected:
        {json.dumps([p.description for p in relevant_patterns[:10]], indent=2)}
        
        Provide analysis in JSON format:
        {{
            "score": <0-100>,
            "confidence": <0-1>,
            "key_patterns": [<list of observed patterns>],
            "adjustable_parameter": "<parameter name>",
            "parameter_value": <0-1>,
            "evidence_summary": "<brief summary>"
        }}
        """
        
        try:
            response = await self.openai.chat.completions.create(
                model=settings.ontology_extraction_model,
                messages=[
                    {"role": "system", "content": "You are a behavioral analysis expert."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3  # Lower temperature for consistent analysis
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return OntologyScore(
                dimension=dimension,
                score=result["score"],
                confidence=result["confidence"],
                evidence_count=len(relevant_patterns),
                evidence_sources=[p.supporting_documents[0] for p in relevant_patterns[:5]],
                extracted_patterns=result["key_patterns"],
                adjustable_parameter=result["adjustable_parameter"],
                parameter_value=result["parameter_value"]
            )
            
        except Exception as e:
            print(f"⚠️ Error analyzing dimension {dimension.value}: {e}")
            return OntologyScore(
                dimension=dimension,
                score=50.0,  # Default neutral score
                confidence=0.0,
                evidence_count=0
            )
    
    def _sample_documents(self, documents: List[Document], max_docs: int = 50) -> List[Document]:
        """Sample documents for analysis (stratified by type and time)"""
        if len(documents) <= max_docs:
            return documents
        
        # Stratified sampling by document type
        type_groups = defaultdict(list)
        for doc in documents:
            type_groups[doc.metadata.get("type", "unknown")].append(doc)
        
        sampled = []
        per_type = max_docs // len(type_groups)
        
        for doc_type, docs in type_groups.items():
            if len(docs) <= per_type:
                sampled.extend(docs)
            else:
                # Sample evenly across time range
                docs.sort(key=lambda d: d.metadata.get("timestamp", 0))
                indices = np.linspace(0, len(docs)-1, per_type, dtype=int)
                sampled.extend([docs[i] for i in indices])
        
        return sampled[:max_docs]
    
    def _prepare_context(self, documents: List[Document], patterns: List[BehavioralPattern]) -> str:
        """Prepare context string from documents and patterns"""
        context_parts = []
        
        # Add document summaries
        for doc in documents[:20]:  # Limit for token management
            summary = f"[{doc.metadata.get('type', 'doc')}] {doc.metadata.get('timestamp', '')}: "
            summary += doc.content[:200] if len(doc.content) > 200 else doc.content
            context_parts.append(summary)
        
        # Add pattern summaries
        for pattern in patterns[:10]:
            context_parts.append(f"Pattern: {pattern.description} (freq: {pattern.frequency:.2f})")
        
        return "\n".join(context_parts)
    
    def _merge_similar_patterns(self, patterns: List[BehavioralPattern]) -> List[BehavioralPattern]:
        """Merge similar patterns to avoid redundancy"""
        if not patterns:
            return []
        
        # Simple clustering based on description similarity
        merged = []
        used = set()
        
        for i, p1 in enumerate(patterns):
            if i in used:
                continue
                
            similar_group = [p1]
            used.add(i)
            
            for j, p2 in enumerate(patterns[i+1:], i+1):
                if j in used:
                    continue
                    
                if self._calculate_similarity(p1.description, p2.description) > 0.8:
                    similar_group.append(p2)
                    used.add(j)
            
            # Merge the group
            if len(similar_group) > 1:
                merged.append(self._merge_pattern_group(similar_group))
            else:
                merged.append(p1)
        
        return merged
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings (simple version)"""
        # In production, use proper embeddings or edit distance
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _merge_pattern_group(self, patterns: List[BehavioralPattern]) -> BehavioralPattern:
        """Merge a group of similar patterns"""
        # Aggregate pattern data
        merged = BehavioralPattern(
            pattern_type=patterns[0].pattern_type,
            description=patterns[0].description,  # Use most frequent
            frequency=np.mean([p.frequency for p in patterns]),
            confidence=np.mean([p.confidence for p in patterns]),
            supporting_documents=list(set(
                doc for p in patterns for doc in p.supporting_documents
            )),
            temporal_distribution=self._merge_temporal_distributions(
                [p.temporal_distribution for p in patterns]
            ),
            related_entities=list(set(
                entity for p in patterns for entity in p.related_entities
            )),
            dimension_impacts=self._merge_dimension_impacts(
                [p.dimension_impacts for p in patterns]
            )
        )
        
        return merged
    
    def _merge_temporal_distributions(self, distributions: List[Dict[str, float]]) -> Dict[str, float]:
        """Merge temporal distribution data"""
        merged = defaultdict(list)
        for dist in distributions:
            for key, value in dist.items():
                merged[key].append(value)
        
        return {key: np.mean(values) for key, values in merged.items()}
    
    def _merge_dimension_impacts(
        self, impacts: List[Dict[OntologyDimension, float]]
    ) -> Dict[OntologyDimension, float]:
        """Merge dimension impact scores"""
        merged = defaultdict(list)
        for impact in impacts:
            for dim, score in impact.items():
                merged[dim].append(score)
        
        return {dim: np.mean(scores) for dim, scores in merged.items()}
    
    def _calculate_confidence(
        self, dimension_scores: Dict[OntologyDimension, OntologyScore], doc_count: int
    ) -> float:
        """Calculate overall confidence score"""
        if not dimension_scores:
            return 0.0
        
        # Weighted average of dimension confidences
        weights = {
            OntologyDimension.DECISION: 1.2,  # Slightly higher weight
            OntologyDimension.POWER: 1.0,
            OntologyDimension.FEAR: 1.1,
            OntologyDimension.REWARD: 0.9,
            OntologyDimension.MEANING: 1.0
        }
        
        weighted_sum = sum(
            score.confidence * weights.get(dim, 1.0)
            for dim, score in dimension_scores.items()
        )
        total_weight = sum(weights.get(dim, 1.0) for dim in dimension_scores.keys())
        
        base_confidence = weighted_sum / total_weight if total_weight > 0 else 0
        
        # Adjust for data volume
        volume_factor = min(1.0, doc_count / 100)  # Full confidence at 100+ docs
        
        return base_confidence * (0.7 + 0.3 * volume_factor)
    
    def _calculate_coverage(self, documents: List[Document]) -> float:
        """Calculate data coverage percentage"""
        expected_types = {"email", "calendar", "chat", "document", "task"}
        found_types = set()
        
        for doc in documents:
            doc_type = doc.metadata.get("type", "").lower()
            if doc_type in expected_types:
                found_types.add(doc_type)
        
        return len(found_types) / len(expected_types) if expected_types else 0


class NegativeSpaceDetector:
    """Detect what the persona DOESN'T do - critical for safety boundaries"""
    
    async def detect(
        self, documents: List[Document], patterns: List[BehavioralPattern]
    ) -> List[str]:
        """Detect negative space boundaries"""
        boundaries = []
        
        # Temporal boundaries
        temporal = self._detect_temporal_boundaries(documents)
        boundaries.extend(temporal)
        
        # Technical boundaries
        technical = self._detect_technical_boundaries(documents, patterns)
        boundaries.extend(technical)
        
        # Social boundaries
        social = self._detect_social_boundaries(documents)
        boundaries.extend(social)
        
        # Process boundaries
        process = self._detect_process_boundaries(patterns)
        boundaries.extend(process)
        
        return boundaries
    
    def _detect_temporal_boundaries(self, documents: List[Document]) -> List[str]:
        """Detect time-based boundaries"""
        boundaries = []
        
        # Analyze timestamp distribution
        timestamps = []
        for doc in documents:
            if ts := doc.metadata.get("timestamp"):
                timestamps.append(datetime.fromisoformat(ts))
        
        if not timestamps:
            return boundaries
        
        # Find never-work hours
        hour_distribution = defaultdict(int)
        for ts in timestamps:
            hour_distribution[ts.hour] += 1
        
        never_hours = [h for h in range(24) if hour_distribution[h] == 0]
        if never_hours:
            boundaries.append(f"Never works during hours: {never_hours}")
        
        # Find never-work days
        day_distribution = defaultdict(int)
        for ts in timestamps:
            day_distribution[ts.weekday()] += 1
        
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        never_days = [day_names[d] for d in range(7) if day_distribution[d] == 0]
        if never_days:
            boundaries.append(f"Never works on: {', '.join(never_days)}")
        
        return boundaries
    
    def _detect_technical_boundaries(
        self, documents: List[Document], patterns: List[BehavioralPattern]
    ) -> List[str]:
        """Detect technical/tool boundaries"""
        boundaries = []
        
        # Analyze mentioned but never used tools
        mentioned_tools = set()
        used_tools = set()
        
        for doc in documents:
            content = doc.content.lower()
            # Simple tool detection (production would use NER)
            if "production" in content and "never" in content:
                boundaries.append("Never touches production directly")
            
            # Detect tool mentions vs usage
            for tool in ["git", "kubernetes", "docker", "terraform", "ansible"]:
                if tool in content:
                    if "used" in content or "ran" in content or "executed" in content:
                        used_tools.add(tool)
                    else:
                        mentioned_tools.add(tool)
        
        never_used = mentioned_tools - used_tools
        if never_used:
            boundaries.append(f"Never uses: {', '.join(never_used)}")
        
        return boundaries
    
    def _detect_social_boundaries(self, documents: List[Document]) -> List[str]:
        """Detect social/communication boundaries"""
        boundaries = []
        
        # Analyze communication patterns
        recipients = defaultdict(int)
        escalation_levels = defaultdict(int)
        
        for doc in documents:
            if doc.metadata.get("type") == "email":
                if recipients_list := doc.metadata.get("recipients"):
                    for recipient in recipients_list:
                        recipients[recipient] += 1
                        # Detect seniority (simple heuristic)
                        if any(title in recipient.lower() for title in ["ceo", "cto", "vp", "director"]):
                            escalation_levels["executive"] += 1
        
        # Never contacts
        if escalation_levels["executive"] == 0 and len(documents) > 50:
            boundaries.append("Never directly contacts executive level")
        
        return boundaries
    
    def _detect_process_boundaries(self, patterns: List[BehavioralPattern]) -> List[str]:
        """Detect process-related boundaries"""
        boundaries = []
        
        for pattern in patterns:
            if "always" in pattern.description.lower():
                boundary = pattern.description.replace("always", "never skips")
                boundaries.append(boundary)
            
            if "never" in pattern.description.lower():
                boundaries.append(pattern.description)
        
        return boundaries


# Specialized Pattern Extractors

class CommunicationPatternExtractor:
    """Extract communication-specific patterns"""
    
    async def extract(self, documents: List[Document]) -> List[BehavioralPattern]:
        patterns = []
        
        # Response time analysis
        response_pattern = self._analyze_response_times(documents)
        if response_pattern:
            patterns.append(response_pattern)
        
        # Message length preferences
        length_pattern = self._analyze_message_lengths(documents)
        if length_pattern:
            patterns.append(length_pattern)
        
        # Formality analysis
        formality_pattern = self._analyze_formality(documents)
        if formality_pattern:
            patterns.append(formality_pattern)
        
        return patterns
    
    def _analyze_response_times(self, documents: List[Document]) -> Optional[BehavioralPattern]:
        """Analyze email response time patterns"""
        response_times = []
        
        # Group documents by thread
        threads = defaultdict(list)
        for doc in documents:
            if thread_id := doc.metadata.get("thread_id"):
                threads[thread_id].append(doc)
        
        # Calculate response times
        for thread_docs in threads.values():
            thread_docs.sort(key=lambda d: d.metadata.get("timestamp", ""))
            
            for i in range(1, len(thread_docs)):
                if thread_docs[i].metadata.get("is_reply"):
                    time1 = datetime.fromisoformat(thread_docs[i-1].metadata["timestamp"])
                    time2 = datetime.fromisoformat(thread_docs[i].metadata["timestamp"])
                    response_time = (time2 - time1).total_seconds() / 60  # minutes
                    response_times.append(response_time)
        
        if not response_times:
            return None
        
        # Analyze pattern
        avg_response = np.median(response_times)
        
        if avg_response < 15:
            description = "Immediate responder - typically replies within 15 minutes"
            dimension_impacts = {OntologyDimension.DECISION: 0.8, OntologyDimension.POWER: 0.6}
        elif avg_response < 60:
            description = "Quick responder - typically replies within an hour"
            dimension_impacts = {OntologyDimension.DECISION: 0.6, OntologyDimension.POWER: 0.5}
        else:
            description = "Deliberate responder - takes time to craft responses"
            dimension_impacts = {OntologyDimension.DECISION: 0.4, OntologyDimension.FEAR: 0.3}
        
        return BehavioralPattern(
            pattern_type="communication_response_time",
            description=description,
            frequency=0.8,
            confidence=min(0.9, len(response_times) / 20),  # Confidence based on sample size
            supporting_documents=[d.id for d in documents[:5]],
            temporal_distribution=self._calculate_temporal_distribution(response_times),
            related_entities=[],
            dimension_impacts=dimension_impacts
        )
    
    def _analyze_message_lengths(self, documents: List[Document]) -> Optional[BehavioralPattern]:
        """Analyze message length preferences"""
        lengths = []
        
        for doc in documents:
            if doc.metadata.get("type") == "email":
                lengths.append(len(doc.content.split()))
        
        if not lengths:
            return None
        
        avg_length = np.median(lengths)
        
        if avg_length < 50:
            description = "Concise communicator - prefers brief messages"
        elif avg_length < 150:
            description = "Balanced communicator - moderate message length"
        else:
            description = "Detailed communicator - writes comprehensive messages"
        
        return BehavioralPattern(
            pattern_type="communication_length",
            description=description,
            frequency=0.9,
            confidence=min(0.85, len(lengths) / 30),
            supporting_documents=[d.id for d in documents[:5]],
            temporal_distribution={},
            related_entities=[],
            dimension_impacts={OntologyDimension.DECISION: 0.3}
        )
    
    def _analyze_formality(self, documents: List[Document]) -> Optional[BehavioralPattern]:
        """Analyze communication formality"""
        formality_scores = []
        
        formal_indicators = ["regards", "sincerely", "please", "kindly", "would you"]
        informal_indicators = ["hey", "thanks", "cool", "awesome", "btw"]
        
        for doc in documents:
            if doc.metadata.get("type") == "email":
                content_lower = doc.content.lower()
                formal_count = sum(1 for ind in formal_indicators if ind in content_lower)
                informal_count = sum(1 for ind in informal_indicators if ind in content_lower)
                
                if formal_count + informal_count > 0:
                    formality_scores.append(formal_count / (formal_count + informal_count))
        
        if not formality_scores:
            return None
        
        avg_formality = np.mean(formality_scores)
        
        if avg_formality > 0.7:
            description = "Formal communicator - maintains professional tone"
        elif avg_formality > 0.3:
            description = "Adaptive communicator - adjusts formality to context"
        else:
            description = "Casual communicator - prefers informal tone"
        
        return BehavioralPattern(
            pattern_type="communication_formality",
            description=description,
            frequency=0.85,
            confidence=min(0.8, len(formality_scores) / 25),
            supporting_documents=[d.id for d in documents[:5]],
            temporal_distribution={},
            related_entities=[],
            dimension_impacts={OntologyDimension.POWER: 0.4}
        )
    
    def _calculate_temporal_distribution(self, data: List[float]) -> Dict[str, float]:
        """Calculate temporal distribution (placeholder)"""
        # In production, this would analyze when patterns occur
        return {"morning": 0.3, "afternoon": 0.5, "evening": 0.2}


class TemporalPatternExtractor:
    """Extract time-based behavioral patterns"""
    
    async def extract(self, documents: List[Document]) -> List[BehavioralPattern]:
        patterns = []
        
        # Work rhythm analysis
        rhythm_pattern = self._analyze_work_rhythm(documents)
        if rhythm_pattern:
            patterns.append(rhythm_pattern)
        
        # Meeting patterns
        meeting_pattern = self._analyze_meeting_patterns(documents)
        if meeting_pattern:
            patterns.append(meeting_pattern)
        
        return patterns
    
    def _analyze_work_rhythm(self, documents: List[Document]) -> Optional[BehavioralPattern]:
        """Analyze daily work rhythm"""
        hour_distribution = defaultdict(int)
        
        for doc in documents:
            if timestamp := doc.metadata.get("timestamp"):
                hour = datetime.fromisoformat(timestamp).hour
                hour_distribution[hour] += 1
        
        if not hour_distribution:
            return None
        
        # Find peak hours
        sorted_hours = sorted(hour_distribution.items(), key=lambda x: x[1], reverse=True)
        peak_hours = [h for h, _ in sorted_hours[:3]]
        
        if all(h < 12 for h in peak_hours):
            description = "Morning person - peak productivity before noon"
        elif all(h >= 17 for h in peak_hours):
            description = "Evening worker - active after standard hours"
        else:
            description = "Standard hours - peak productivity during business hours"
        
        return BehavioralPattern(
            pattern_type="temporal_rhythm",
            description=description,
            frequency=0.9,
            confidence=0.85,
            supporting_documents=[],
            temporal_distribution={str(h): c/sum(hour_distribution.values()) 
                                 for h, c in hour_distribution.items()},
            related_entities=[],
            dimension_impacts={OntologyDimension.MEANING: 0.3}
        )
    
    def _analyze_meeting_patterns(self, documents: List[Document]) -> Optional[BehavioralPattern]:
        """Analyze meeting behavior patterns"""
        meetings = []
        
        for doc in documents:
            if doc.metadata.get("type") == "calendar":
                meetings.append(doc)
        
        if len(meetings) < 5:
            return None
        
        # Analyze back-to-back meetings
        back_to_back_count = 0
        meetings.sort(key=lambda m: m.metadata.get("start_time", ""))
        
        for i in range(1, len(meetings)):
            end1 = datetime.fromisoformat(meetings[i-1].metadata.get("end_time", ""))
            start2 = datetime.fromisoformat(meetings[i].metadata.get("start_time", ""))
            
            if (start2 - end1).total_seconds() < 300:  # Less than 5 minutes
                back_to_back_count += 1
        
        back_to_back_ratio = back_to_back_count / len(meetings)
        
        if back_to_back_ratio > 0.5:
            description = "Back-to-back scheduler - minimal breaks between meetings"
            dimension_impacts = {OntologyDimension.FEAR: 0.6, OntologyDimension.POWER: 0.4}
        else:
            description = "Buffer scheduler - maintains breaks between meetings"
            dimension_impacts = {OntologyDimension.FEAR: 0.3}
        
        return BehavioralPattern(
            pattern_type="meeting_scheduling",
            description=description,
            frequency=back_to_back_ratio,
            confidence=0.75,
            supporting_documents=[m.id for m in meetings[:5]],
            temporal_distribution={},
            related_entities=[],
            dimension_impacts=dimension_impacts
        )


class CollaborationPatternExtractor:
    """Extract collaboration and team interaction patterns"""
    
    async def extract(self, documents: List[Document]) -> List[BehavioralPattern]:
        patterns = []
        
        # Solo vs collaborative work
        collab_pattern = self._analyze_collaboration_style(documents)
        if collab_pattern:
            patterns.append(collab_pattern)
        
        return patterns
    
    def _analyze_collaboration_style(self, documents: List[Document]) -> Optional[BehavioralPattern]:
        """Analyze collaboration preferences"""
        solo_indicators = ["i will", "i'll handle", "let me", "i can"]
        collab_indicators = ["we should", "let's", "team", "together", "our"]
        
        solo_count = 0
        collab_count = 0
        
        for doc in documents:
            content_lower = doc.content.lower()
            solo_count += sum(1 for ind in solo_indicators if ind in content_lower)
            collab_count += sum(1 for ind in collab_indicators if ind in content_lower)
        
        if solo_count + collab_count < 10:
            return None
        
        collab_ratio = collab_count / (solo_count + collab_count)
        
        if collab_ratio > 0.7:
            description = "Team collaborator - prefers group work and consensus"
            dimension_impacts = {OntologyDimension.POWER: 0.3, OntologyDimension.DECISION: 0.5}
        elif collab_ratio > 0.3:
            description = "Balanced collaborator - mixes solo and team work"
            dimension_impacts = {OntologyDimension.POWER: 0.5, OntologyDimension.DECISION: 0.4}
        else:
            description = "Independent worker - prefers solo execution"
            dimension_impacts = {OntologyDimension.POWER: 0.7, OntologyDimension.DECISION: 0.3}
        
        return BehavioralPattern(
            pattern_type="collaboration_style",
            description=description,
            frequency=0.8,
            confidence=0.7,
            supporting_documents=[d.id for d in documents[:5]],
            temporal_distribution={},
            related_entities=[],
            dimension_impacts=dimension_impacts
        )


class DecisionPatternExtractor:
    """Extract decision-making patterns"""
    
    async def extract(self, documents: List[Document]) -> List[BehavioralPattern]:
        patterns = []
        
        # Decision speed analysis
        speed_pattern = self._analyze_decision_speed(documents)
        if speed_pattern:
            patterns.append(speed_pattern)
        
        return patterns
    
    def _analyze_decision_speed(self, documents: List[Document]) -> Optional[BehavioralPattern]:
        """Analyze decision-making speed"""
        decision_indicators = ["decided", "let's go with", "we'll do", "approve", "confirmed"]
        research_indicators = ["need to check", "let me research", "i'll investigate", "need more info"]
        
        quick_decisions = 0
        researched_decisions = 0
        
        for doc in documents:
            content_lower = doc.content.lower()
            if any(ind in content_lower for ind in decision_indicators):
                if any(ind in content_lower for ind in research_indicators):
                    researched_decisions += 1
                else:
                    quick_decisions += 1
        
        total_decisions = quick_decisions + researched_decisions
        if total_decisions < 5:
            return None
        
        quick_ratio = quick_decisions / total_decisions
        
        if quick_ratio > 0.7:
            description = "Fast decision maker - minimal research needed"
            dimension_impacts = {OntologyDimension.DECISION: 0.8, OntologyDimension.FEAR: 0.2}
        elif quick_ratio > 0.3:
            description = "Balanced decision maker - research when needed"
            dimension_impacts = {OntologyDimension.DECISION: 0.5, OntologyDimension.FEAR: 0.5}
        else:
            description = "Thorough decision maker - extensive research preferred"
            dimension_impacts = {OntologyDimension.DECISION: 0.3, OntologyDimension.FEAR: 0.7}
        
        return BehavioralPattern(
            pattern_type="decision_speed",
            description=description,
            frequency=0.75,
            confidence=min(0.8, total_decisions / 15),
            supporting_documents=[d.id for d in documents[:5]],
            temporal_distribution={},
            related_entities=[],
            dimension_impacts=dimension_impacts
        )


class ToolUsagePatternExtractor:
    """Extract tool and technology usage patterns"""
    
    async def extract(self, documents: List[Document]) -> List[BehavioralPattern]:
        patterns = []
        
        # Tool preference analysis
        tool_pattern = self._analyze_tool_preferences(documents)
        if tool_pattern:
            patterns.append(tool_pattern)
        
        return patterns
    
    def _analyze_tool_preferences(self, documents: List[Document]) -> Optional[BehavioralPattern]:
        """Analyze tool usage preferences"""
        tool_mentions = defaultdict(int)
        
        common_tools = [
            "excel", "powerpoint", "word", "outlook", "teams",
            "slack", "jira", "github", "vscode", "python",
            "javascript", "sql", "tableau", "power bi"
        ]
        
        for doc in documents:
            content_lower = doc.content.lower()
            for tool in common_tools:
                if tool in content_lower:
                    tool_mentions[tool] += 1
        
        if not tool_mentions:
            return None
        
        # Find most used tools
        top_tools = sorted(tool_mentions.items(), key=lambda x: x[1], reverse=True)[:3]
        tool_names = [tool for tool, _ in top_tools]
        
        if any(tool in ["python", "javascript", "sql", "github"] for tool in tool_names):
            description = f"Technical user - frequently uses {', '.join(tool_names)}"
            dimension_impacts = {OntologyDimension.POWER: 0.6}
        else:
            description = f"Business user - primarily uses {', '.join(tool_names)}"
            dimension_impacts = {OntologyDimension.DECISION: 0.4}
        
        return BehavioralPattern(
            pattern_type="tool_usage",
            description=description,
            frequency=0.8,
            confidence=0.7,
            supporting_documents=[d.id for d in documents[:5]],
            temporal_distribution={},
            related_entities=tool_names,
            dimension_impacts=dimension_impacts
        )


# Main exports
__all__ = [
    "FourthOntologyEngine",
    "FourthOntology",
    "OntologyScore",
    "BehavioralPattern",
    "OntologyDimension",
    "NegativeSpaceDetector"
]
