"""
backend/utils/patterns.py
Behavioral Pattern Extraction Utilities
Core logic for extracting patterns from Microsoft 365 data
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics
import re
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class BehavioralPatternExtractor:
    """
    Extracts behavioral patterns from ingested data
    This is the core innovation - patterns are extracted DURING ingestion
    """
    
    def __init__(self):
        self.patterns = {}
        self.metrics = defaultdict(list)
        
    def extract_email_patterns(self, email_documents: List[Any]) -> Dict[str, Any]:
        """
        Extract patterns from email data
        Returns dictionary of pattern types and their data
        """
        patterns = {}
        
        # Response time patterns
        response_times = self._extract_response_times(email_documents)
        patterns['response_time'] = {
            'avg_minutes': statistics.mean(response_times) if response_times else 0,
            'median_minutes': statistics.median(response_times) if response_times else 0,
            'immediate_threshold': self._find_immediate_threshold(response_times),
            'working_hours_avg': self._calculate_working_hours_response(email_documents),
            'after_hours_avg': self._calculate_after_hours_response(email_documents),
            'evidence_count': len(response_times),
            'confidence': min(len(response_times) / 100, 1.0)  # Confidence based on sample size
        }
        
        # Communication style patterns
        comm_style = self._extract_communication_style(email_documents)
        patterns['communication_style'] = comm_style
        
        # Email volume patterns
        volume_patterns = self._extract_volume_patterns(email_documents)
        patterns['volume'] = volume_patterns
        
        # Sender/recipient patterns
        network_patterns = self._extract_network_patterns(email_documents)
        patterns['network'] = network_patterns
        
        # Topic patterns
        topic_patterns = self._extract_topic_patterns(email_documents)
        patterns['topics'] = topic_patterns
        
        # Stress indicators
        stress_patterns = self._extract_stress_indicators(email_documents)
        patterns['stress'] = stress_patterns
        
        return patterns
        
    def extract_calendar_patterns(self, calendar_documents: List[Any]) -> Dict[str, Any]:
        """Extract patterns from calendar data"""
        patterns = {}
        
        # Meeting patterns
        meeting_patterns = self._extract_meeting_patterns(calendar_documents)
        patterns['meetings'] = meeting_patterns
        
        # Time management patterns
        time_patterns = self._extract_time_management_patterns(calendar_documents)
        patterns['time_management'] = time_patterns
        
        # Collaboration patterns
        collab_patterns = self._extract_collaboration_patterns(calendar_documents)
        patterns['collaboration'] = collab_patterns
        
        return patterns
        
    def analyze_meeting_patterns(self, meeting_data: Dict[str, List]) -> Dict[str, Any]:
        """Analyze meeting patterns from aggregated data"""
        patterns = {}
        
        if 'day_of_week' in meeting_data and meeting_data['day_of_week']:
            # Most common meeting days
            day_counts = Counter(meeting_data['day_of_week'])
            patterns['preferred_days'] = [day for day, _ in day_counts.most_common(3)]
            
        if 'hour_of_day' in meeting_data and meeting_data['hour_of_day']:
            # Peak meeting hours
            hour_counts = Counter(meeting_data['hour_of_day'])
            patterns['peak_hours'] = [hour for hour, _ in hour_counts.most_common(3)]
            
        if 'duration' in meeting_data and meeting_data['duration']:
            # Meeting duration patterns
            durations = [d for d in meeting_data['duration'] if d]
            if durations:
                patterns['avg_duration'] = statistics.mean(durations)
                patterns['typical_duration'] = statistics.median(durations)
                
        if 'dates' in meeting_data and meeting_data['dates']:
            # Back-to-back meeting detection
            dates = sorted(meeting_data['dates'])
            back_to_back_count = 0
            for i in range(1, len(dates)):
                if (dates[i] - dates[i-1]).total_seconds() < 900:  # Within 15 minutes
                    back_to_back_count += 1
            patterns['back_to_back_frequency'] = back_to_back_count / max(len(dates) - 1, 1)
            
        return patterns
        
    # ==================== Email Pattern Extraction ====================
    
    def _extract_response_times(self, documents: List[Any]) -> List[float]:
        """Extract response times from emails"""
        response_times = []
        
        for doc in documents:
            metadata = json.loads(doc.metadata) if isinstance(doc.metadata, str) else doc.metadata
            if 'response_time_minutes' in metadata and metadata['response_time_minutes']:
                response_times.append(metadata['response_time_minutes'])
                
        return response_times
        
    def _find_immediate_threshold(self, response_times: List[float]) -> float:
        """Find threshold for immediate responses (typically under 5-10 minutes)"""
        if not response_times:
            return 5.0
            
        # Use clustering to find immediate vs delayed responses
        if len(response_times) > 10:
            times_array = np.array(response_times).reshape(-1, 1)
            
            # Log transform to handle skewed distribution
            log_times = np.log1p(times_array)
            
            # Try to find 2 clusters (immediate vs delayed)
            try:
                kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
                kmeans.fit(log_times)
                
                # Get cluster centers and convert back from log space
                centers = np.expm1(kmeans.cluster_centers_.flatten())
                threshold = min(centers) * 1.5  # 1.5x the lower cluster center
                
                return min(threshold, 15.0)  # Cap at 15 minutes
            except:
                pass
                
        # Fallback to percentile-based threshold
        return min(np.percentile(response_times, 10), 10.0)
        
    def _calculate_working_hours_response(self, documents: List[Any]) -> float:
        """Calculate average response time during working hours"""
        working_responses = []
        
        for doc in documents:
            metadata = json.loads(doc.metadata) if isinstance(doc.metadata, str) else doc.metadata
            
            if 'sent_time' in metadata and 'response_time_minutes' in metadata:
                sent_time = datetime.fromisoformat(metadata['sent_time'])
                
                # Check if during working hours (9 AM - 6 PM weekdays)
                if sent_time.weekday() < 5 and 9 <= sent_time.hour < 18:
                    if metadata['response_time_minutes']:
                        working_responses.append(metadata['response_time_minutes'])
                        
        return statistics.mean(working_responses) if working_responses else 0
        
    def _calculate_after_hours_response(self, documents: List[Any]) -> float:
        """Calculate average response time after hours"""
        after_hours_responses = []
        
        for doc in documents:
            metadata = json.loads(doc.metadata) if isinstance(doc.metadata, str) else doc.metadata
            
            if 'sent_time' in metadata and 'response_time_minutes' in metadata:
                sent_time = datetime.fromisoformat(metadata['sent_time'])
                
                # Check if after hours
                if sent_time.weekday() >= 5 or sent_time.hour < 9 or sent_time.hour >= 18:
                    if metadata['response_time_minutes']:
                        after_hours_responses.append(metadata['response_time_minutes'])
                        
        return statistics.mean(after_hours_responses) if after_hours_responses else 0
        
    def _extract_communication_style(self, documents: List[Any]) -> Dict[str, Any]:
        """Extract communication style patterns"""
        message_lengths = []
        greetings = []
        signoffs = []
        formality_scores = []
        
        for doc in documents:
            # Message length
            content_length = len(doc.content.split()) if doc.content else 0
            message_lengths.append(content_length)
            
            # Extract greeting and signoff
            lines = doc.content.split('\n') if doc.content else []
            if lines:
                # First non-empty line as greeting
                for line in lines[:3]:
                    if line.strip():
                        greetings.append(line.strip()[:50])
                        break
                        
                # Last non-empty line as signoff
                for line in reversed(lines[-3:]):
                    if line.strip():
                        signoffs.append(line.strip()[:50])
                        break
                        
            # Calculate formality score
            formality = self._calculate_formality_score(doc.content)
            formality_scores.append(formality)
            
        # Find most common patterns
        greeting_counts = Counter(greetings)
        signoff_counts = Counter(signoffs)
        
        return {
            'avg_message_length': statistics.mean(message_lengths) if message_lengths else 0,
            'median_message_length': statistics.median(message_lengths) if message_lengths else 0,
            'common_greetings': [g for g, _ in greeting_counts.most_common(5)],
            'common_signoffs': [s for s, _ in signoff_counts.most_common(5)],
            'formality_score': statistics.mean(formality_scores) if formality_scores else 50,
            'evidence_count': len(documents),
            'confidence': min(len(documents) / 100, 1.0)
        }
        
    def _calculate_formality_score(self, content: str) -> float:
        """Calculate formality score (0-100) based on language patterns"""
        if not content:
            return 50
            
        score = 50  # Neutral baseline
        
        # Formal indicators
        formal_patterns = [
            r'\bDear\b', r'\bSincerely\b', r'\bRegards\b', r'\bKindly\b',
            r'\bPlease\b', r'\bThank you\b', r'\bI would\b', r'\bCould you\b'
        ]
        
        # Informal indicators
        informal_patterns = [
            r'\bHey\b', r'\bHi\b', r'\bthanks\b', r'\bThanx\b',
            r'\bLOL\b', r'\b:\)\b', r'\b!\b{2,}', r'\bASAP\b'
        ]
        
        content_lower = content.lower()
        
        for pattern in formal_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                score += 5
                
        for pattern in informal_patterns:
            if re.search(pattern, content_lower):
                score -= 5
                
        # Cap between 0 and 100
        return max(0, min(100, score))
        
    def _extract_volume_patterns(self, documents: List[Any]) -> Dict[str, Any]:
        """Extract email volume patterns"""
        hourly_volume = defaultdict(int)
        daily_volume = defaultdict(int)
        weekly_volume = defaultdict(int)
        
        for doc in documents:
            metadata = json.loads(doc.metadata) if isinstance(doc.metadata, str) else doc.metadata
            
            if 'sent_time' in metadata and metadata['sent_time']:
                sent_time = datetime.fromisoformat(metadata['sent_time'])
                
                hourly_volume[sent_time.hour] += 1
                daily_volume[sent_time.weekday()] += 1
                weekly_volume[sent_time.isocalendar()[1]] += 1
                
        # Find peak times
        peak_hours = sorted(hourly_volume.items(), key=lambda x: x[1], reverse=True)[:3]
        peak_days = sorted(daily_volume.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            'peak_hours': [hour for hour, _ in peak_hours],
            'peak_days': [day for day, _ in peak_days],
            'total_emails': len(documents),
            'avg_daily': len(documents) / max(len(daily_volume), 1),
            'weekend_activity': (daily_volume.get(5, 0) + daily_volume.get(6, 0)) / max(sum(daily_volume.values()), 1),
            'evidence_count': len(documents)
        }
        
    def _extract_network_patterns(self, documents: List[Any]) -> Dict[str, Any]:
        """Extract sender/recipient network patterns"""
        senders = []
        recipients = []
        domains = []
        
        for doc in documents:
            metadata = json.loads(doc.metadata) if isinstance(doc.metadata, str) else doc.metadata
            
            if 'sender' in metadata and metadata['sender']:
                senders.append(metadata['sender'])
                domain = metadata['sender'].split('@')[-1] if '@' in metadata['sender'] else 'unknown'
                domains.append(domain)
                
            if 'recipients' in metadata and metadata['recipients']:
                recipients.extend(metadata['recipients'])
                for recipient in metadata['recipients']:
                    if '@' in recipient:
                        domains.append(recipient.split('@')[-1])
                        
        # Find most frequent contacts
        sender_counts = Counter(senders)
        recipient_counts = Counter(recipients)
        domain_counts = Counter(domains)
        
        return {
            'top_senders': [s for s, _ in sender_counts.most_common(10)],
            'top_recipients': [r for r, _ in recipient_counts.most_common(10)],
            'top_domains': [d for d, _ in domain_counts.most_common(10)],
            'unique_contacts': len(set(senders + recipients)),
            'internal_ratio': self._calculate_internal_ratio(domains),
            'evidence_count': len(documents)
        }
        
    def _calculate_internal_ratio(self, domains: List[str]) -> float:
        """Calculate ratio of internal vs external communications"""
        if not domains:
            return 0.5
            
        # Assume most common domain is the user's organization
        domain_counts = Counter(domains)
        if domain_counts:
            internal_domain = domain_counts.most_common(1)[0][0]
            internal_count = domain_counts[internal_domain]
            return internal_count / len(domains)
            
        return 0.5
        
    def _extract_topic_patterns(self, documents: List[Any]) -> Dict[str, Any]:
        """Extract topic patterns from email subjects"""
        subjects = []
        keywords = []
        
        for doc in documents:
            if doc.title:
                subjects.append(doc.title.lower())
                # Extract keywords (simple approach)
                words = re.findall(r'\b\w{4,}\b', doc.title.lower())
                keywords.extend(words)
                
        # Find common topics/keywords
        keyword_counts = Counter(keywords)
        
        # Filter out common words
        stop_words = {'this', 'that', 'with', 'from', 'about', 'your', 'have', 'will', 'been', 'were', 'there'}
        filtered_keywords = [(k, c) for k, c in keyword_counts.items() if k not in stop_words]
        filtered_keywords.sort(key=lambda x: x[1], reverse=True)
        
        return {
            'top_keywords': [k for k, _ in filtered_keywords[:20]],
            'keyword_frequency': dict(filtered_keywords[:20]),
            'unique_subjects': len(set(subjects)),
            'evidence_count': len(subjects)
        }
        
    def _extract_stress_indicators(self, documents: List[Any]) -> Dict[str, Any]:
        """Extract stress indicators from email patterns"""
        weekend_emails = 0
        late_night_emails = 0
        early_morning_emails = 0
        short_responses = []
        high_importance_count = 0
        
        for doc in documents:
            metadata = json.loads(doc.metadata) if isinstance(doc.metadata, str) else doc.metadata
            
            if 'sent_time' in metadata and metadata['sent_time']:
                sent_time = datetime.fromisoformat(metadata['sent_time'])
                
                # Weekend activity
                if sent_time.weekday() >= 5:
                    weekend_emails += 1
                    
                # Time-based stress indicators
                if sent_time.hour >= 22 or sent_time.hour < 6:
                    late_night_emails += 1
                elif sent_time.hour < 7:
                    early_morning_emails += 1
                    
            # Response length as stress indicator
            if doc.content and len(doc.content.split()) < 20:
                short_responses.append(doc)
                
            # Importance/urgency
            if 'importance' in metadata and metadata['importance'] == 'high':
                high_importance_count += 1
                
        total = len(documents) if documents else 1
        
        return {
            'weekend_activity_rate': weekend_emails / total,
            'late_night_activity_rate': late_night_emails / total,
            'early_morning_activity_rate': early_morning_emails / total,
            'short_response_rate': len(short_responses) / total,
            'high_importance_rate': high_importance_count / total,
            'stress_level': self._calculate_stress_level(
                weekend_emails / total,
                late_night_emails / total,
                len(short_responses) / total
            ),
            'evidence_count': len(documents)
        }
        
    def _calculate_stress_level(self, weekend_rate: float, late_night_rate: float, short_response_rate: float) -> str:
        """Calculate overall stress level"""
        score = (weekend_rate * 30) + (late_night_rate * 40) + (short_response_rate * 30)
        
        if score > 0.6:
            return 'high'
        elif score > 0.3:
            return 'medium'
        else:
            return 'low'
            
    # ==================== Calendar Pattern Extraction ====================
    
    def _extract_meeting_patterns(self, documents: List[Any]) -> Dict[str, Any]:
        """Extract meeting patterns from calendar data"""
        meeting_times = []
        durations = []
        attendee_counts = []
        recurring_meetings = 0
        
        for doc in documents:
            metadata = json.loads(doc.metadata) if isinstance(doc.metadata, str) else doc.metadata
            
            if 'start_time' in metadata and metadata['start_time']:
                start_time = datetime.fromisoformat(metadata['start_time'])
                meeting_times.append(start_time)
                
            if 'duration_minutes' in metadata and metadata['duration_minutes']:
                durations.append(metadata['duration_minutes'])
                
            if 'attendees' in metadata and metadata['attendees']:
                attendee_counts.append(len(metadata['attendees']))
                
            if metadata.get('is_recurring'):
                recurring_meetings += 1
                
        # Analyze patterns
        patterns = {}
        
        if meeting_times:
            # Peak meeting times
            hours = [t.hour for t in meeting_times]
            hour_counts = Counter(hours)
            patterns['peak_meeting_hours'] = [h for h, _ in hour_counts.most_common(3)]
            
            # Meeting day preferences
            days = [t.weekday() for t in meeting_times]
            day_counts = Counter(days)
            patterns['preferred_meeting_days'] = [d for d, _ in day_counts.most_common(3)]
            
        if durations:
            patterns['avg_meeting_duration'] = statistics.mean(durations)
            patterns['typical_meeting_duration'] = statistics.median(durations)
            
        if attendee_counts:
            patterns['avg_attendee_count'] = statistics.mean(attendee_counts)
            patterns['large_meeting_threshold'] = np.percentile(attendee_counts, 75)
            
        patterns['recurring_meeting_ratio'] = recurring_meetings / max(len(documents), 1)
        patterns['evidence_count'] = len(documents)
        
        return patterns
        
    def _extract_time_management_patterns(self, documents: List[Any]) -> Dict[str, Any]:
        """Extract time management patterns"""
        buffer_times = []
        back_to_back_count = 0
        free_time_blocks = []
        
        # Sort meetings by time
        meetings = []
        for doc in documents:
            metadata = json.loads(doc.metadata) if isinstance(doc.metadata, str) else doc.metadata
            if 'start_time' in metadata and 'end_time' in metadata:
                meetings.append({
                    'start': datetime.fromisoformat(metadata['start_time']),
                    'end': datetime.fromisoformat(metadata['end_time']),
                    'duration': metadata.get('duration_minutes', 0)
                })
                
        meetings.sort(key=lambda x: x['start'])
        
        # Analyze gaps between meetings
        for i in range(1, len(meetings)):
            gap = (meetings[i]['start'] - meetings[i-1]['end']).total_seconds() / 60
            
            if gap < 5:
                back_to_back_count += 1
            elif gap < 30:
                buffer_times.append(gap)
            else:
                free_time_blocks.append(gap)
                
        patterns = {
            'back_to_back_frequency': back_to_back_count / max(len(meetings) - 1, 1),
            'avg_buffer_time': statistics.mean(buffer_times) if buffer_times else 15,
            'free_time_blocks': len(free_time_blocks),
            'time_management_style': self._classify_time_management_style(
                back_to_back_count / max(len(meetings) - 1, 1),
                statistics.mean(buffer_times) if buffer_times else 15
            ),
            'evidence_count': len(meetings)
        }
        
        return patterns
        
    def _classify_time_management_style(self, back_to_back_ratio: float, avg_buffer: float) -> str:
        """Classify time management style"""
        if back_to_back_ratio > 0.5:
            return 'packed_schedule'
        elif avg_buffer > 20:
            return 'buffer_conscious'
        else:
            return 'balanced'
            
    def _extract_collaboration_patterns(self, documents: List[Any]) -> Dict[str, Any]:
        """Extract collaboration patterns from calendar data"""
        organizers = []
        attendee_lists = []
        meeting_types = defaultdict(int)
        
        for doc in documents:
            metadata = json.loads(doc.metadata) if isinstance(doc.metadata, str) else doc.metadata
            
            if 'organizer' in metadata and metadata['organizer']:
                organizers.append(metadata['organizer'])
                
            if 'attendees' in metadata and metadata['attendees']:
                attendees = [a['email'] if isinstance(a, dict) else a for a in metadata['attendees']]
                attendee_lists.append(attendees)
                
                # Classify meeting type by size
                if len(attendees) <= 2:
                    meeting_types['one_on_one'] += 1
                elif len(attendees) <= 5:
                    meeting_types['small_group'] += 1
                elif len(attendees) <= 15:
                    meeting_types['team'] += 1
                else:
                    meeting_types['large'] += 1
                    
        # Find frequent collaborators
        all_attendees = [a for attendees in attendee_lists for a in attendees]
        collaborator_counts = Counter(all_attendees)
        
        # Check if user organizes or attends more
        user_organized = len([o for o in organizers if o])  # Simplified check
        
        return {
            'top_collaborators': [c for c, _ in collaborator_counts.most_common(10)],
            'meeting_type_distribution': dict(meeting_types),
            'organizer_ratio': user_organized / max(len(documents), 1),
            'collaboration_style': 'organizer' if user_organized / max(len(documents), 1) > 0.5 else 'participant',
            'unique_collaborators': len(set(all_attendees)),
            'evidence_count': len(documents)
        }


class FourthOntologyExtractor:
    """
    Extracts Fourth Ontology dimensions from behavioral patterns
    This is the key differentiator of the BDT system
    """
    
    def __init__(self):
        self.dimensions = {
            'decision': {'score': 50, 'evidence': []},
            'power': {'score': 50, 'evidence': []},
            'fear': {'score': 50, 'evidence': []},
            'reward': {'score': 50, 'evidence': []},
            'meaning': {'score': 50, 'evidence': []}
        }
        
    def extract_from_patterns(self, email_patterns: Dict, calendar_patterns: Dict) -> Dict[str, Any]:
        """Extract Fourth Ontology dimensions from behavioral patterns"""
        
        # Decision Dimension
        self._extract_decision_dimension(email_patterns, calendar_patterns)
        
        # Power Dimension
        self._extract_power_dimension(email_patterns, calendar_patterns)
        
        # Fear Dimension
        self._extract_fear_dimension(email_patterns, calendar_patterns)
        
        # Reward Dimension
        self._extract_reward_dimension(email_patterns, calendar_patterns)
        
        # Meaning Dimension
        self._extract_meaning_dimension(email_patterns, calendar_patterns)
        
        return self.dimensions
        
    def _extract_decision_dimension(self, email_patterns: Dict, calendar_patterns: Dict):
        """Extract decision-making patterns"""
        score = 50  # Baseline
        evidence = []
        
        # Analytical indicators (increase score)
        if email_patterns.get('communication_style', {}).get('avg_message_length', 0) > 200:
            score += 10
            evidence.append("Long, detailed emails suggest analytical approach")
            
        # Quick decision indicators (decrease score)
        response_time = email_patterns.get('response_time', {}).get('immediate_threshold', 10)
        if response_time < 5:
            score -= 10
            evidence.append("Very quick responses suggest intuitive decisions")
            
        # Collaboration indicators
        if calendar_patterns.get('collaboration', {}).get('meeting_type_distribution', {}).get('large', 0) > 5:
            score += 5
            evidence.append("Many large meetings suggest consensus-seeking")
            
        self.dimensions['decision'] = {
            'score': max(0, min(100, score)),
            'evidence': evidence,
            'adjustable_parameter': 'analysis_depth',
            'current_value': {'depth': 'extensive' if score > 70 else 'moderate' if score > 40 else 'quick'}
        }
        
    def _extract_power_dimension(self, email_patterns: Dict, calendar_patterns: Dict):
        """Extract power and autonomy patterns"""
        score = 50
        evidence = []
        
        # Organizer ratio indicates leadership
        organizer_ratio = calendar_patterns.get('collaboration', {}).get('organizer_ratio', 0.5)
        if organizer_ratio > 0.6:
            score += 15
            evidence.append("Frequently organizes meetings - leadership indicator")
        elif organizer_ratio < 0.3:
            score -= 10
            evidence.append("Rarely organizes - follower pattern")
            
        # Email network size indicates influence
        unique_contacts = email_patterns.get('network', {}).get('unique_contacts', 0)
        if unique_contacts > 100:
            score += 10
            evidence.append("Large network suggests high influence")
            
        self.dimensions['power'] = {
            'score': max(0, min(100, score)),
            'evidence': evidence,
            'adjustable_parameter': 'autonomy_radius',
            'current_value': {'autonomy': 'high' if score > 60 else 'collaborative' if score > 40 else 'dependent'}
        }
        
    def _extract_fear_dimension(self, email_patterns: Dict, calendar_patterns: Dict):
        """Extract risk tolerance and fear patterns"""
        score = 50
        evidence = []
        
        # Stress indicators suggest fear/caution
        stress_level = email_patterns.get('stress', {}).get('stress_level', 'medium')
        if stress_level == 'high':
            score += 20
            evidence.append("High stress indicators suggest high fear/caution")
        elif stress_level == 'low':
            score -= 10
            evidence.append("Low stress suggests comfort with risk")
            
        # After-hours work suggests fear of falling behind
        weekend_rate = email_patterns.get('stress', {}).get('weekend_activity_rate', 0)
        if weekend_rate > 0.2:
            score += 10
            evidence.append("Weekend work suggests fear of falling behind")
            
        # Back-to-back meetings suggest fear of saying no
        back_to_back = calendar_patterns.get('time_management', {}).get('back_to_back_frequency', 0)
        if back_to_back > 0.5:
            score += 5
            evidence.append("Many back-to-back meetings suggest difficulty saying no")
            
        self.dimensions['fear'] = {
            'score': max(0, min(100, score)),
            'evidence': evidence,
            'adjustable_parameter': 'safety_buffer',
            'current_value': {'risk_tolerance': 'low' if score > 60 else 'moderate' if score > 40 else 'high'}
        }
        
    def _extract_reward_dimension(self, email_patterns: Dict, calendar_patterns: Dict):
        """Extract motivation and reward patterns"""
        score = 50
        evidence = []
        
        # High importance emails suggest achievement focus
        importance_rate = email_patterns.get('stress', {}).get('high_importance_rate', 0)
        if importance_rate > 0.3:
            score += 10
            evidence.append("Many high-importance items suggest achievement focus")
            
        # Large meetings might indicate recognition seeking
        large_meetings = calendar_patterns.get('collaboration', {}).get('meeting_type_distribution', {}).get('large', 0)
        if large_meetings > 10:
            score += 5
            evidence.append("Frequent large meetings may indicate visibility seeking")
            
        self.dimensions['reward'] = {
            'score': max(0, min(100, score)),
            'evidence': evidence,
            'adjustable_parameter': 'recognition_threshold',
            'current_value': {'motivation': 'achievement' if score > 60 else 'balanced' if score > 40 else 'intrinsic'}
        }
        
    def _extract_meaning_dimension(self, email_patterns: Dict, calendar_patterns: Dict):
        """Extract purpose and meaning patterns"""
        score = 50
        evidence = []
        
        # Recurring meetings suggest commitment to processes
        recurring_ratio = calendar_patterns.get('meetings', {}).get('recurring_meeting_ratio', 0)
        if recurring_ratio > 0.3:
            score += 10
            evidence.append("Many recurring meetings suggest process commitment")
            
        # Topic diversity suggests broad interests
        unique_subjects = email_patterns.get('topics', {}).get('unique_subjects', 0)
        if unique_subjects > 100:
            score += 5
            evidence.append("Diverse topics suggest broad value alignment")
            
        self.dimensions['meaning'] = {
            'score': max(0, min(100, score)),
            'evidence': evidence,
            'adjustable_parameter': 'significance_threshold',
            'current_value': {'alignment': 'critical' if score > 70 else 'important' if score > 40 else 'flexible'}
        }
