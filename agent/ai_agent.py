"""
Enhanced AI Agent with Router and LLM Integration
Intelligently decides when to use AI vs direct queries
"""
from typing import Optional, Dict, Any, List
import uuid
import json

from database.db_manager import DatabaseManager
from database.models import Employee, RecommendationResult, AgentResponse
from .router import QueryRouter, QueryType
from .tools import EmployeeSearchTools
from .llm_integration import LLMManager, LLMProvider


class EnhancedEmployeeFinderAgent:
    """
    AI-powered Employee Finder Agent with intelligent routing
    
    Architecture:
    1. Router: Decides query handling strategy (direct/pattern/AI)
    2. Tools: Database search functions
    3. LLM: AI understanding for complex queries
    4. Orchestrator: Combines results and generates response
    """
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        llm_provider: Optional[LLMProvider] = None,
        enable_ai: bool = True
    ):
        self.db = db_manager
        self.router = QueryRouter()
        self.tools = EmployeeSearchTools(db_manager)
        self.llm_manager = LLMManager(llm_provider) if enable_ai else None
        self.enable_ai = enable_ai
    
    def process_query(self, user_query: str, session_id: Optional[str] = None) -> AgentResponse:
        """
        Main entry point: Process user query with intelligent routing
        
        Flow:
        1. Route query → determine strategy
        2. Execute strategy:
           - Direct: Use tools directly
           - Pattern: Use pattern matching + tools
           - AI: Use LLM to understand + tools
        3. Generate response
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Step 1: Route the query
        routing_result = self.router.route_query(user_query)
        
        # Step 2: Execute based on routing decision
        if routing_result['strategy'] == 'direct':
            return self._handle_direct_query(user_query, routing_result, session_id)
        
        elif routing_result['strategy'] == 'pattern':
            return self._handle_pattern_query(user_query, routing_result, session_id)
        
        elif routing_result['strategy'] == 'ai':
            if self.enable_ai and self.llm_manager:
                return self._handle_ai_query(user_query, routing_result, session_id)
            else:
                # Fallback to pattern matching if AI disabled
                return self._handle_pattern_query(user_query, routing_result, session_id)
        
        else:
            # Default fallback
            return self._handle_pattern_query(user_query, routing_result, session_id)
    
    def _handle_direct_query(
        self,
        user_query: str,
        routing_result: Dict,
        session_id: str
    ) -> AgentResponse:
        """
        Handle direct queries (e.g., email lookup)
        No AI needed - direct database query
        """
        extracted = routing_result['extracted_info']
        
        if 'email' in extracted:
            # Direct email lookup
            employee_dict = self.tools.find_by_email(extracted['email'])
            
            if employee_dict:
                # Get full info with leader
                full_info = self.tools.get_employee_with_leader(employee_dict['id'])
                
                recommendations = [
                    RecommendationResult(
                        employee=self._dict_to_employee(full_info),
                        match_score=1.0,
                        match_reasons=["Exact email match"],
                        ownership_type="direct_match",
                        people_leader=self._dict_to_employee(full_info.get('people_leader')) if full_info.get('people_leader') else None
                    )
                ]
                
                return AgentResponse(
                    understanding=f"Found employee with email: {extracted['email']}",
                    recommended_roles=[full_info['position']],
                    recommendations=recommendations,
                    confidence_level='high',
                    disclaimer="Direct email match - 100% confidence",
                    estimated_time_saved=0.5,  # Very fast
                    next_steps=["Contact this person directly"]
                )
            else:
                return self._no_results_response(user_query, "No employee found with that email address")
        
        return self._no_results_response(user_query, "Could not process direct query")
    
    def _handle_pattern_query(
        self,
        user_query: str,
        routing_result: Dict,
        session_id: str
    ) -> AgentResponse:
        """
        Handle pattern-based queries (e.g., team search)
        Uses pattern matching + database queries (no AI needed)
        """
        extracted = routing_result['extracted_info']
        results = []

        # First, try to find by responsibility/ownership (highest priority)
        # Look for keywords that suggest responsibility queries
        responsibility_keywords = ['provisioning', 'billing', 'security', 'compliance', 'support',
                                   'network', 'infrastructure', 'BIA', 'help with', 'responsible for']
        query_lower = user_query.lower()

        for keyword in responsibility_keywords:
            if keyword.lower() in query_lower:
                ownership_results = self.tools.find_by_responsibility(keyword)
                if ownership_results:
                    results = ownership_results
                    break

        # If no ownership results, try other search strategies
        if not results and 'search_type' in extracted:
            search_type = extracted['search_type']
            value = extracted.get('value', '')

            if search_type == 'team':
                results = self.tools.find_by_team(value)
            elif search_type == 'location':
                # Search by location (would need to add this to tools)
                results = self.tools.search_fulltext(value)
            elif search_type == 'role':
                results = self.tools.find_by_role(value)

        # Fallback to full-text search
        if not results:
            if 'keyword' in extracted:
                results = self.tools.search_fulltext(user_query)
            else:
                results = self.tools.search_fulltext(user_query)
        
        if results:
            recommendations = self._convert_results_to_recommendations(results)
            
            return AgentResponse(
                understanding=f"Found {len(results)} people matching your search",
                recommended_roles=list(set([r['position'] for r in results[:5]])),
                recommendations=recommendations[:10],
                confidence_level='medium',
                disclaimer="Results based on keyword matching. For more accurate results, try being more specific.",
                estimated_time_saved=0.65,
                next_steps=[
                    "Review the recommended contacts",
                    "Refine your search if needed"
                ]
            )
        else:
            return self._no_results_response(user_query, "No matches found. Try different keywords.")

    def _handle_ai_query(
        self,
        user_query: str,
        routing_result: Dict,
        session_id: str
    ) -> AgentResponse:
        """
        Handle AI-powered queries
        Uses LLM to understand intent, then executes appropriate tools
        """
        # Use LLM to understand the query
        understanding = self.llm_manager.understand_query(user_query)

        # Execute searches based on LLM understanding
        all_results = []

        # Strategy 1: Search by responsibility (highest priority)
        if understanding.get('search_strategy') == 'responsibility':
            for domain in understanding.get('domains', []):
                responsibility_results = self.tools.find_by_responsibility(domain)
                all_results.extend(responsibility_results)

        # Strategy 2: Search by skills
        if understanding.get('search_strategy') == 'skill' or understanding.get('requirements', {}).get('skills'):
            skills = understanding.get('requirements', {}).get('skills', [])
            for skill in skills:
                skill_results = self.tools.find_by_skill(skill)
                all_results.extend(skill_results)

        # Strategy 3: Search by team
        if understanding.get('requirements', {}).get('team'):
            team = understanding['requirements']['team']
            team_results = self.tools.find_by_team(team)
            all_results.extend(team_results)

        # Strategy 4: Fallback to full-text search
        if not all_results:
            all_results = self.tools.search_fulltext(user_query)

        # Remove duplicates and rank
        unique_results = self._deduplicate_results(all_results)

        if unique_results:
            recommendations = self._convert_results_to_recommendations(unique_results)

            return AgentResponse(
                understanding=understanding.get('intent', user_query),
                recommended_roles=list(set([r['position'] for r in unique_results[:5]])),
                recommendations=recommendations[:10],
                confidence_level='high',
                disclaimer="AI-powered search with ownership prioritization. Results verified against database.",
                estimated_time_saved=0.65,
                next_steps=[
                    "Contact the primary owner first",
                    "If unavailable, try the backup contact",
                    "Escalate to people leader if needed"
                ]
            )
        else:
            return self._no_results_response(
                user_query,
                "No matches found. The AI couldn't identify relevant employees. Try rephrasing your query."
            )

    # ============================================
    # Helper Methods
    # ============================================

    def _convert_results_to_recommendations(
        self,
        results: List[Dict[str, Any]]
    ) -> List[RecommendationResult]:
        """Convert tool results to RecommendationResult objects"""
        recommendations = []

        for idx, result in enumerate(results):
            # Calculate match score based on position and ownership
            match_score = 0.8 - (idx * 0.05)  # Decrease score for lower ranked results
            match_score = max(match_score, 0.3)  # Minimum score

            # Determine match reasons
            match_reasons = []
            if 'ownership_type' in result:
                match_reasons.append(f"{result['ownership_type']} owner")
            if 'position' in result:
                match_reasons.append(f"Role: {result['position']}")
            if 'team' in result:
                match_reasons.append(f"Team: {result['team']}")

            # Get people leader if available
            people_leader = None
            if 'people_leader' in result:
                people_leader = self._dict_to_employee(result['people_leader'])

            recommendations.append(
                RecommendationResult(
                    employee=self._dict_to_employee(result),
                    match_score=match_score,
                    match_reasons=match_reasons or ["Keyword match"],
                    ownership_type=result.get('ownership_type', 'contributor'),
                    people_leader=people_leader
                )
            )

        return recommendations

    def _dict_to_employee(self, emp_dict: Dict[str, Any]) -> Employee:
        """Convert dictionary to Employee object"""
        return Employee(
            id=emp_dict.get('id'),
            formal_name=emp_dict.get('name', ''),
            email_address=emp_dict.get('email', ''),
            position_title=emp_dict.get('position', ''),
            function=emp_dict.get('function'),
            business_unit=emp_dict.get('business_unit'),
            team=emp_dict.get('team'),
            location=emp_dict.get('location'),
            people_leader_id=emp_dict.get('people_leader_id')
        )

    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate employees from results"""
        seen_ids = set()
        unique = []

        for result in results:
            emp_id = result.get('id')
            if emp_id and emp_id not in seen_ids:
                seen_ids.add(emp_id)
                unique.append(result)

        return unique

    def _no_results_response(self, query: str, message: str) -> AgentResponse:
        """Generate a 'no results' response"""
        return AgentResponse(
            understanding=f"Searched for: {query}",
            recommended_roles=[],
            recommendations=[],
            confidence_level='low',
            disclaimer=message,
            estimated_time_saved=0.1,
            next_steps=[
                "Try rephrasing your query",
                "Use more specific keywords",
                "Try searching by team or role instead"
            ]
        )

    def clarify_query(self, query: str) -> Optional[str]:
        """
        Check if query is too ambiguous and needs clarification
        Returns clarification question if needed, None otherwise
        """
        # Very short queries might need clarification
        if len(query.strip()) < 5:
            return "Could you provide more details about what you need help with? For example, mention the specific area (like provisioning, billing, support) or the type of expertise you're looking for."

        # Single word queries (except emails)
        if len(query.split()) == 1 and '@' not in query:
            return "Could you be more specific? For example, are you looking for a person, a team, or help with a specific task?"

        return None

