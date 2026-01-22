"""
AI Router for Employee Finder Agent
Decides when to use AI (LLM) vs direct database queries
"""
from typing import Dict, Literal, Optional
from enum import Enum
import re


class QueryType(Enum):
    """Types of queries the system can handle"""
    DIRECT_LOOKUP = "direct_lookup"          # "Find john.doe@sample.com"
    SIMPLE_SEARCH = "simple_search"          # "Find someone in billing team"
    COMPLEX_INTENT = "complex_intent"        # "I need help setting up BIA provisioning"
    CONVERSATIONAL = "conversational"        # "Thanks!" or "Can you explain more?"
    AMBIGUOUS = "ambiguous"                  # Unclear intent, needs clarification


class QueryRouter:
    """
    Intelligent router that decides the query handling strategy
    
    Decision Flow:
    1. Direct Lookup (email/name) → Direct DB query (no AI needed)
    2. Simple Search (team/role) → Pattern matching + DB query (no AI needed)
    3. Complex Intent → AI-powered understanding + DB query (AI needed)
    4. Conversational → AI response (AI needed)
    5. Ambiguous → AI clarification (AI needed)
    """
    
    # Patterns for direct lookups
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    # Keywords that indicate simple searches
    SIMPLE_SEARCH_KEYWORDS = [
        'team', 'department', 'group', 'unit', 'division',
        'location', 'office', 'site', 'function', 'business unit'
    ]
    
    # Conversational patterns
    CONVERSATIONAL_PATTERNS = [
        r'\b(thanks|thank you|thx)\b',
        r'\b(hi|hello|hey)\b',
        r'\b(bye|goodbye)\b',
        r'\b(yes|no|ok|okay)\b',
    ]
    
    def __init__(self):
        pass
    
    def route_query(self, query: str) -> Dict[str, any]:
        """
        Analyze query and determine routing strategy
        
        Returns:
        {
            'query_type': QueryType,
            'strategy': 'direct' | 'pattern' | 'ai',
            'confidence': float,
            'extracted_info': dict,
            'reasoning': str
        }
        """
        query_lower = query.lower().strip()
        
        # 1. Check for direct email lookup
        email_match = re.search(self.EMAIL_PATTERN, query)
        if email_match:
            return {
                'query_type': QueryType.DIRECT_LOOKUP,
                'strategy': 'direct',
                'confidence': 1.0,
                'extracted_info': {'email': email_match.group()},
                'reasoning': 'Email address detected - direct database lookup'
            }
        
        # 2. Check for conversational queries
        for pattern in self.CONVERSATIONAL_PATTERNS:
            if re.search(pattern, query_lower):
                return {
                    'query_type': QueryType.CONVERSATIONAL,
                    'strategy': 'ai',
                    'confidence': 0.9,
                    'extracted_info': {},
                    'reasoning': 'Conversational query - AI response needed'
                }
        
        # 3. Check for simple search patterns
        simple_search_info = self._detect_simple_search(query_lower)
        if simple_search_info['is_simple']:
            return {
                'query_type': QueryType.SIMPLE_SEARCH,
                'strategy': 'pattern',
                'confidence': simple_search_info['confidence'],
                'extracted_info': simple_search_info['extracted'],
                'reasoning': f"Simple search detected: {simple_search_info['reason']}"
            }
        
        # 4. Check if query is too short/ambiguous
        word_count = len(query.split())
        if word_count < 3:
            return {
                'query_type': QueryType.AMBIGUOUS,
                'strategy': 'ai',
                'confidence': 0.3,
                'extracted_info': {},
                'reasoning': 'Query too short - AI clarification needed'
            }
        
        # 5. Default to complex intent (AI-powered)
        return {
            'query_type': QueryType.COMPLEX_INTENT,
            'strategy': 'ai',
            'confidence': 0.7,
            'extracted_info': {},
            'reasoning': 'Complex intent detected - AI understanding needed'
        }
    
    def _detect_simple_search(self, query: str) -> Dict[str, any]:
        """
        Detect if this is a simple search that can be handled with pattern matching
        
        Examples:
        - "Find someone in billing team" → team search
        - "Who is in Auckland office?" → location search
        - "Show me network engineers" → role search
        """
        result = {
            'is_simple': False,
            'confidence': 0.0,
            'extracted': {},
            'reason': ''
        }
        
        # Pattern: "find/show/who [someone/people] in/from [team/location]"
        patterns = [
            (r'(?:find|show|who).*?(?:in|from)\s+(\w+)\s+(team|department|group)', 'team'),
            (r'(?:find|show|who).*?(?:in|from)\s+(\w+)\s+(office|location|site)', 'location'),
            (r'(?:find|show|who).*?(\w+)\s+(engineer|specialist|manager|lead|analyst)', 'role'),
        ]
        
        for pattern, search_type in patterns:
            match = re.search(pattern, query)
            if match:
                result['is_simple'] = True
                result['confidence'] = 0.8
                result['extracted'] = {
                    'search_type': search_type,
                    'value': match.group(1)
                }
                result['reason'] = f"{search_type} search pattern matched"
                return result
        
        # Check for simple keyword presence
        for keyword in self.SIMPLE_SEARCH_KEYWORDS:
            if keyword in query:
                result['is_simple'] = True
                result['confidence'] = 0.6
                result['extracted'] = {'keyword': keyword}
                result['reason'] = f"Simple keyword '{keyword}' detected"
                return result
        
        return result
    
    def should_use_ai(self, routing_result: Dict[str, any]) -> bool:
        """
        Determine if AI (LLM) should be used based on routing result
        """
        return routing_result['strategy'] == 'ai'

