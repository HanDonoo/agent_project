"""
One NZ Employee Finder Agent
Core AI agent for finding the right people based on user queries
Implements survey insights: ownership-first, role-before-person, time-saving focus
"""
import re
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import uuid

from database.models import Employee, RecommendationResult, AgentResponse
from database.db_manager import DatabaseManager


class EmployeeFinderAgent:
    """
    AI Agent for employee discovery and team formation
    Designed based on One NZ survey insights
    """
    
    # Keywords for different domains (extracted from survey)
    DOMAIN_KEYWORDS = {
        'provisioning': ['provision', 'provisioning', 'setup', 'configure', 'deployment'],
        'network': ['network', 'networking', 'infrastructure', 'connectivity', 'wan', 'lan'],
        'security': ['security', 'secure', 'compliance', 'risk', 'audit', 'governance', 'rai'],
        'billing': ['billing', 'invoice', 'payment', 'charge', 'revenue'],
        'support': ['support', 'help', 'issue', 'problem', 'troubleshoot', 'fix'],
        'sales': ['sales', 'sell', 'customer', 'client', 'account', 'commercial'],
        'product': ['product', 'feature', 'roadmap', 'requirement'],
        'engineering': ['engineer', 'develop', 'build', 'code', 'technical', 'software'],
        'data': ['data', 'analytics', 'reporting', 'bi', 'insight'],
        'project': ['project', 'programme', 'initiative', 'delivery'],
    }
    
    # Common responsibility areas (for ownership matching)
    RESPONSIBILITY_AREAS = {
        'bia provisioning': ['bia', 'business impact analysis', 'provisioning'],
        'network setup': ['network', 'setup', 'infrastructure'],
        'compliance': ['compliance', 'risk', 'audit', 'governance'],
        'customer support': ['customer support', 'helpdesk', 'service desk'],
        'billing operations': ['billing', 'invoice', 'payment'],
    }
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def process_query(self, user_query: str, session_id: Optional[str] = None) -> AgentResponse:
        """
        Main entry point: Process user query and return recommendations
        
        Flow (based on survey insights):
        1. Understand the query
        2. Identify required roles/teams FIRST
        3. Find people with ownership
        4. Provide recommendations with context
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Step 1: Parse and understand the query
        parsed_intent = self._parse_query(user_query)
        
        # Step 2: Identify recommended roles/teams (Survey insight: role before person)
        recommended_roles = self._identify_roles(parsed_intent)
        
        # Step 3: Find matching employees
        recommendations = self._find_matching_employees(parsed_intent)
        
        # Step 4: Enrich with people leader info (Survey insight: show backup/escalation)
        recommendations = self._enrich_with_leaders(recommendations)
        
        # Step 5: Determine confidence level
        confidence = self._calculate_confidence(recommendations, parsed_intent)
        
        # Step 6: Generate understanding summary
        understanding = self._generate_understanding(user_query, parsed_intent, recommended_roles)
        
        # Step 7: Generate next steps
        next_steps = self._generate_next_steps(recommendations)
        
        # Step 8: Create response with RAI disclaimer
        response = AgentResponse(
            understanding=understanding,
            recommended_roles=recommended_roles,
            recommendations=recommendations[:10],  # Top 10
            confidence_level=confidence,
            disclaimer=self._get_rai_disclaimer(confidence),
            estimated_time_saved=39.3 / 60,  # Survey average: 39.3 min/week
            next_steps=next_steps
        )
        
        # Log the query (for analytics and improvement)
        self._log_query(session_id, user_query, parsed_intent, recommendations)
        
        return response
    
    def _parse_query(self, query: str) -> Dict[str, any]:
        """
        Parse user query to extract intent
        Returns: {
            'keywords': [...],
            'domains': [...],
            'responsibilities': [...],
            'teams': [...],
            'functions': [...]
        }
        """
        query_lower = query.lower()
        
        # Extract keywords
        keywords = re.findall(r'\b\w+\b', query_lower)
        
        # Identify domains
        domains = []
        for domain, patterns in self.DOMAIN_KEYWORDS.items():
            if any(pattern in query_lower for pattern in patterns):
                domains.append(domain)
        
        # Identify responsibility areas
        responsibilities = []
        for resp, patterns in self.RESPONSIBILITY_AREAS.items():
            if any(pattern in query_lower for pattern in patterns):
                responsibilities.append(resp)
        
        # Extract potential team/function mentions
        teams = self._extract_teams(query_lower)
        functions = self._extract_functions(query_lower)
        
        return {
            'original_query': query,
            'keywords': keywords,
            'domains': domains,
            'responsibilities': responsibilities,
            'teams': teams,
            'functions': functions
        }
    
    def _extract_teams(self, query: str) -> List[str]:
        """Extract team names from query"""
        # This could be enhanced with actual team names from DB
        team_keywords = ['team', 'group', 'department', 'unit']
        teams = []
        
        # Simple extraction - can be improved
        for keyword in team_keywords:
            if keyword in query:
                # Extract words around the keyword
                pattern = rf'(\w+\s+)?{keyword}(\s+\w+)?'
                matches = re.findall(pattern, query)
                teams.extend([' '.join(m).strip() for m in matches if m])
        
        return teams
    
    def _extract_functions(self, query: str) -> List[str]:
        """Extract function names from query"""
        # Common function names
        functions = ['IT', 'Technology', 'Sales', 'Marketing', 'Finance', 'HR', 'Operations']
        found = [f for f in functions if f.lower() in query]
        return found

    def _identify_roles(self, parsed_intent: Dict) -> List[str]:
        """
        Identify recommended roles/teams FIRST (Survey insight)
        Returns list of role titles or team names
        """
        roles = []

        # Based on domains identified
        domain_to_roles = {
            'provisioning': ['Provisioning Specialist', 'Network Engineer', 'Technical Lead'],
            'network': ['Network Engineer', 'Infrastructure Specialist', 'Network Architect'],
            'security': ['Security Specialist', 'Compliance Officer', 'Risk Manager'],
            'billing': ['Billing Specialist', 'Revenue Operations', 'Finance Analyst'],
            'support': ['Support Engineer', 'Customer Support Lead', 'Service Desk'],
            'sales': ['Sales Engineer', 'Account Manager', 'Commercial Lead'],
            'product': ['Product Manager', 'Product Owner', 'Product Lead'],
            'engineering': ['Software Engineer', 'Technical Lead', 'Engineering Manager'],
            'data': ['Data Analyst', 'BI Specialist', 'Analytics Lead'],
            'project': ['Project Manager', 'Programme Manager', 'Delivery Lead'],
        }

        for domain in parsed_intent.get('domains', []):
            if domain in domain_to_roles:
                roles.extend(domain_to_roles[domain])

        # Remove duplicates while preserving order
        seen = set()
        unique_roles = []
        for role in roles:
            if role not in seen:
                seen.add(role)
                unique_roles.append(role)

        return unique_roles[:5]  # Top 5 roles

    def _find_matching_employees(self, parsed_intent: Dict) -> List[RecommendationResult]:
        """
        Find employees matching the parsed intent
        Priority: Ownership > Skills > Team/Function
        """
        candidates = []

        # Strategy 1: Find by responsibility ownership (HIGHEST PRIORITY - Survey insight)
        for responsibility in parsed_intent.get('responsibilities', []):
            owners = self.db.get_owners_by_responsibility(responsibility)
            for owner_data in owners:
                employee = owner_data['employee']
                score = 0.9 if owner_data['ownership_type'] == 'primary' else 0.7

                candidates.append(RecommendationResult(
                    employee=employee,
                    match_score=score,
                    match_reasons=[
                        f"Primary owner of: {owner_data['responsibility_area']}"
                    ],
                    ownership_type=owner_data['ownership_type']
                ))

        # Strategy 2: Find by skills/domains
        for domain in parsed_intent.get('domains', []):
            employees = self.db.get_employees_by_skill(domain, min_confidence=0.5)
            for emp in employees:
                # Check if already added
                if not any(c.employee.id == emp.id for c in candidates):
                    candidates.append(RecommendationResult(
                        employee=emp,
                        match_score=0.6,
                        match_reasons=[f"Has expertise in: {domain}"]
                    ))

        # Strategy 3: Search by keywords (fallback)
        if len(candidates) < 5:
            keywords = ' '.join(parsed_intent.get('keywords', [])[:5])
            if keywords:
                employees = self.db.search_employees_fulltext(keywords, limit=10)
                for emp in employees:
                    if not any(c.employee.id == emp.id for c in candidates):
                        candidates.append(RecommendationResult(
                            employee=emp,
                            match_score=0.4,
                            match_reasons=["Keyword match in profile"]
                        ))

        # Strategy 4: Search by team/function
        if parsed_intent.get('teams') or parsed_intent.get('functions'):
            employees = self.db.search_employees_by_criteria(
                team=parsed_intent.get('teams', [None])[0] if parsed_intent.get('teams') else None,
                function=parsed_intent.get('functions', [None])[0] if parsed_intent.get('functions') else None,
                limit=10
            )
            for emp in employees:
                if not any(c.employee.id == emp.id for c in candidates):
                    candidates.append(RecommendationResult(
                        employee=emp,
                        match_score=0.5,
                        match_reasons=["Team/Function match"]
                    ))

        # Sort by match score
        candidates.sort(key=lambda x: x.match_score, reverse=True)

        return candidates

    def _enrich_with_leaders(self, recommendations: List[RecommendationResult]) -> List[RecommendationResult]:
        """
        Add people leader info for backup/escalation (Survey insight)
        """
        for rec in recommendations:
            if rec.employee.people_leader_id:
                leader = self.db.get_employee_by_id(rec.employee.people_leader_id)
                if leader:
                    rec.people_leader = leader

        return recommendations

    def _calculate_confidence(self, recommendations: List[RecommendationResult], parsed_intent: Dict) -> str:
        """
        Calculate confidence level based on match quality
        """
        if not recommendations:
            return 'low'

        top_score = recommendations[0].match_score
        has_ownership = any(r.ownership_type == 'primary' for r in recommendations[:3])

        if top_score >= 0.8 and has_ownership:
            return 'high'
        elif top_score >= 0.5 or has_ownership:
            return 'medium'
        else:
            return 'low'

    def _generate_understanding(self, query: str, parsed_intent: Dict, roles: List[str]) -> str:
        """
        Generate understanding summary (Survey insight: confirm understanding)
        """
        domains = parsed_intent.get('domains', [])
        responsibilities = parsed_intent.get('responsibilities', [])

        if responsibilities:
            return f"You're looking for help with {', '.join(responsibilities)}. Let me find the right people for this."
        elif domains:
            return f"You need expertise in {', '.join(domains)}. I'll connect you with the relevant team members."
        elif roles:
            return f"You're looking for {roles[0]} or similar roles. Here's who can help."
        else:
            return f"I understand you need help with: '{query}'. Let me find the most relevant contacts."

    def _generate_next_steps(self, recommendations: List[RecommendationResult]) -> List[str]:
        """
        Generate suggested next steps (Survey insight: actionable guidance)
        """
        steps = []

        if recommendations:
            steps.append("Review the recommended contacts below")
            steps.append("Reach out to the primary contact first")

            if any(r.people_leader for r in recommendations[:3]):
                steps.append("If needed, escalate to their People Leader")

            steps.append("Consider creating a Teams group for collaboration")
        else:
            steps.append("Try refining your query with more specific keywords")
            steps.append("Contact your People Leader for guidance")

        return steps

    def _get_rai_disclaimer(self, confidence: str) -> str:
        """
        Generate RAI-compliant disclaimer (Survey insight: set expectations)
        """
        base = "This recommendation is based on current role, team ownership, and derived skills. "

        if confidence == 'high':
            return base + "The suggested contacts are highly likely to help with your query."
        elif confidence == 'medium':
            return base + "If this doesn't fully resolve your query, I can help you find additional contacts or escalate further."
        else:
            return base + "The match confidence is lower than usual. Please verify with the contact or try a more specific query."

    def _log_query(self, session_id: str, query: str, parsed_intent: Dict, recommendations: List[RecommendationResult]):
        """
        Log query for analytics (privacy-compliant: no PII stored beyond session)
        """
        from database.models import QueryLog

        employee_ids = [r.employee.id for r in recommendations[:10]]

        log = QueryLog(
            session_id=session_id,
            user_query=query,
            parsed_intent=json.dumps(parsed_intent),
            recommended_employees=json.dumps(employee_ids),
            time_saved_minutes=39.3 / 60  # Survey average
        )

        try:
            self.db.log_query(log)
        except Exception as e:
            # Don't fail the request if logging fails
            print(f"Warning: Failed to log query: {e}")

    def clarify_query(self, query: str) -> Optional[str]:
        """
        Check if query is too ambiguous and needs clarification
        Returns clarification question if needed, None otherwise
        """
        parsed = self._parse_query(query)

        # Check if query is too vague
        if len(parsed['keywords']) < 2:
            return "Could you provide more details about what you need help with? For example, mention the specific area (like provisioning, billing, support) or the type of expertise you're looking for."

        # Check if no domains or responsibilities identified
        if not parsed['domains'] and not parsed['responsibilities']:
            return "I want to make sure I find the right people for you. Could you clarify: Are you looking for help with a technical issue, a business process, or something else?"

        return None  # Query is clear enough

