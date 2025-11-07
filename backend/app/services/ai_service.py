"""
AI Service using Google Gemini
Handles meeting analysis, insight extraction, and decision making
"""

import google.generativeai as genai
from typing import Dict, List, Optional
import json
from datetime import datetime
from app.config import settings

class AIService:
    """Google Gemini AI Service for meeting analysis"""
    
    def __init__(self):
        """Initialize Gemini API"""
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set in environment")
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        # Use Gemini 1.5 Flash for fast responses
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Generation config for structured output
        self.json_config = {
            "temperature": 0.3,
            "top_p": 0.8,
            "top_k": 40,
            "response_mime_type": "application/json"
        }
    
    async def extract_meeting_insights(self, transcript: str) -> Dict:
        """
        Extract comprehensive insights from meeting transcript
        
        Args:
            transcript: Full meeting transcript text
            
        Returns:
            Dict with action_items, decisions, follow_ups, sentiment, summary, etc.
        """
        
        prompt = f"""
        Analyze this meeting transcript and extract the following information in JSON format:
        
        1. **action_items**: List of action items with:
           - task: Clear description of what needs to be done
           - person: Who is responsible (if mentioned)
           - deadline: When it's due (if mentioned, format as ISO date string)
           - priority: "high", "medium", or "low"
           
        2. **key_decisions**: List of important decisions made during the meeting
        
        3. **follow_ups**: Things that need to be followed up on
        
        4. **participants**: List of people mentioned or involved
        
        5. **topics**: Main topics discussed
        
        6. **sentiment**: Overall sentiment - "positive", "neutral", "negative", or "mixed"
        
        7. **summary**: 2-3 sentence summary of the meeting
        
        8. **next_steps**: What should happen next
        
        Transcript:
        {transcript}
        
        Return ONLY valid JSON with this structure:
        {{
            "action_items": [
                {{
                    "task": "string",
                    "person": "string or null",
                    "deadline": "ISO date string or null",
                    "priority": "high|medium|low"
                }}
            ],
            "key_decisions": ["string"],
            "follow_ups": ["string"],
            "participants": ["string"],
            "topics": ["string"],
            "sentiment": "positive|neutral|negative|mixed",
            "summary": "string",
            "next_steps": ["string"]
        }}
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=self.json_config
            )
            
            result = json.loads(response.text)
            return result
        
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON from Gemini: {str(e)}")
            print(f"Raw response: {response.text}")
            # Return default structure
            return self._default_insights()
        
        except Exception as e:
            print(f"❌ Error extracting insights: {str(e)}")
            return self._default_insights()
    
    async def analyze_sentiment(self, text: str) -> Dict:
        """
        Analyze sentiment of a text segment
        
        Returns:
            Dict with sentiment label and confidence
        """
        
        prompt = f"""
        Analyze the sentiment of this text and return JSON:
        
        Text: {text}
        
        Return:
        {{
            "sentiment": "positive|neutral|negative",
            "confidence": 0.0-1.0,
            "reasoning": "brief explanation"
        }}
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=self.json_config
            )
            return json.loads(response.text)
        except:
            return {"sentiment": "neutral", "confidence": 0.5, "reasoning": "Unable to analyze"}
    
    async def decide_autonomous_actions(
        self,
        insights: Dict,
        user_preferences: Dict
    ) -> Dict:
        """
        Decide what actions should be taken autonomously
        
        Args:
            insights: Meeting insights from extract_meeting_insights()
            user_preferences: User's automation settings
            
        Returns:
            Dict with immediate_actions, approval_required, suggestions
        """
        
        prompt = f"""
        You are an AI assistant that decides what actions to take based on meeting insights.
        
        Meeting Insights:
        {json.dumps(insights, indent=2)}
        
        User Automation Preferences:
        {json.dumps(user_preferences, indent=2)}
        
        Based on the insights and user preferences, categorize actions into:
        
        1. **immediate_actions**: Can be executed without approval
           - Send meeting summary to attendees
           - Create calendar reminders for deadlines
           - Log call in CRM
           
        2. **approval_required**: Need user approval before execution
           - Send emails to external contacts
           - Schedule meetings with specific people
           - Create high-priority tasks
           
        3. **suggestions**: Require human judgment
           - Strategic decisions
           - Sensitive communications
        
        For each action, provide:
        - action_type: "email"|"calendar"|"crm"|"task"|"notification"
        - priority: "high"|"medium"|"low"
        - details: Specific parameters needed to execute
        - reasoning: Why this action is suggested
        
        Return JSON:
        {{
            "immediate_actions": [
                {{
                    "action_type": "string",
                    "title": "string",
                    "priority": "string",
                    "details": {{}},
                    "reasoning": "string"
                }}
            ],
            "approval_required": [...],
            "suggestions": [...]
        }}
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=self.json_config
            )
            return json.loads(response.text)
        
        except Exception as e:
            print(f"❌ Error deciding actions: {str(e)}")
            return {
                "immediate_actions": [],
                "approval_required": [],
                "suggestions": []
            }
    
    async def generate_email_content(
        self,
        context: Dict,
        recipient: str,
        purpose: str
    ) -> Dict:
        """
        Generate professional email content
        
        Args:
            context: Meeting context and action items
            recipient: Email recipient name/email
            purpose: Purpose of the email (follow-up, summary, etc.)
            
        Returns:
            Dict with subject and body
        """
        
        prompt = f"""
        Generate a professional email based on:
        
        Purpose: {purpose}
        Recipient: {recipient}
        Context: {json.dumps(context, indent=2)}
        
        The email should:
        - Be professional and concise
        - Reference the meeting appropriately
        - Clearly state action items or next steps
        - Use appropriate tone
        - Be properly formatted
        
        Return JSON:
        {{
            "subject": "string",
            "body": "string (HTML formatted)",
            "cc": ["optional recipients"]
        }}
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=self.json_config
            )
            return json.loads(response.text)
        
        except Exception as e:
            print(f"❌ Error generating email: {str(e)}")
            return {
                "subject": f"Follow-up: {purpose}",
                "body": "Error generating email content",
                "cc": []
            }
    
    async def generate_meeting_summary(self, transcript: str) -> str:
        """
        Generate a concise meeting summary
        
        Returns:
            Formatted meeting summary text
        """
        
        prompt = f"""
        Create a concise, professional meeting summary from this transcript:
        
        {transcript}
        
        Include:
        - Meeting date and participants (if mentioned)
        - Main topics discussed
        - Key decisions
        - Action items
        - Next steps
        
        Format as professional meeting minutes.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        
        except Exception as e:
            print(f"❌ Error generating summary: {str(e)}")
            return "Unable to generate meeting summary"
    
    def _default_insights(self) -> Dict:
        """Return default insights structure"""
        return {
            "action_items": [],
            "key_decisions": [],
            "follow_ups": [],
            "participants": [],
            "topics": [],
            "sentiment": "neutral",
            "summary": "Unable to extract insights",
            "next_steps": []
        }


# Example usage
async def test_ai_service():
    """Test function for AI service"""
    service = AIService()
    
    sample_transcript = """
    John: Hey everyone, thanks for joining. Let's discuss the Q4 roadmap.
    Sarah: Sounds good. I think we should focus on the new feature launch.
    John: Agreed. Sarah, can you prepare the marketing materials by next Friday?
    Sarah: Sure, I'll have them ready by then.
    Mike: I'll coordinate with the dev team for the release.
    John: Perfect. Let's schedule a follow-up for next week to review progress.
    """
    
    # Extract insights
    insights = await service.extract_meeting_insights(sample_transcript)
    print("Insights:", json.dumps(insights, indent=2))
    
    # Decide actions
    user_prefs = {
        "auto_send_emails": False,
        "auto_create_calendar": True,
        "auto_update_crm": True
    }
    actions = await service.decide_autonomous_actions(insights, user_prefs)
    print("Actions:", json.dumps(actions, indent=2))


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_ai_service())