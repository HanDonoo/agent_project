"""
OpenWebUI Function for Employee Finder Agent
This can be imported as a custom function in OpenWebUI
"""

import requests
from typing import Optional
from pydantic import BaseModel, Field


class Tools:
    """Employee Finder Tools"""
    
    class Valves(BaseModel):
        """Configuration for the tool"""
        AGENT_API_URL: str = Field(
            default="http://localhost:8000",
            description="Base URL of the Employee Finder Agent API"
        )
    
    def __init__(self):
        self.valves = self.Valves()
    
    def find_employee(
        self,
        query: str,
        __user__: Optional[dict] = None
    ) -> str:
        """
        Find employees by name, team, role, or responsibility.

        Args:
            query: Search query (e.g., "I need help with BIA provisioning", "billing team", "john.smith@sample.com")
        
        Returns:
            Formatted employee information with contact details
        """
        try:
            # Call the agent API
            response = requests.post(
                f"{self.valves.AGENT_API_URL}/query",
                json={"query": query},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Format the response
            if data.get('recommendations'):
                result = f"✅ {data['understanding']}\n\n"
                result += "👥 **Recommended Contacts:**\n\n"
                
                for i, rec in enumerate(data['recommendations'][:5], 1):
                    emp = rec['employee']
                    result += f"**{i}. {emp['formal_name']}**"
                    if rec.get('ownership_type'):
                        result += f" ({rec['ownership_type']})"
                    result += f"\n"
                    result += f"   📧 {emp['email_address']}\n"
                    result += f"   💼 {emp['position_title']}\n"
                    result += f"   👥 Team: {emp['team']}\n"
                    result += f"   🎯 Match: {int(rec['match_score']*100)}%"
                    if rec.get('match_reasons'):
                        result += f" - {', '.join(rec['match_reasons'])}"
                    result += "\n\n"
                
                if data.get('next_steps'):
                    result += "🚀 **Next Steps:**\n"
                    for step in data['next_steps']:
                        result += f"  • {step}\n"
                
                return result
            else:
                return f"❌ {data.get('disclaimer', 'No results found')}\n\nTry:\n" + "\n".join(f"  • {step}" for step in data.get('next_steps', []))
        
        except requests.exceptions.RequestException as e:
            return f"❌ Error connecting to Employee Finder Agent: {str(e)}\n\nMake sure the agent is running at {self.valves.AGENT_API_URL}"
        except Exception as e:
            return f"❌ Error: {str(e)}"

