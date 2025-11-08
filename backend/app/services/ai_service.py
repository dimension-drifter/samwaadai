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

        # Use Gemini 2.5 Pro for advanced capabilities
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        
        # Generation config for structured output
        self.json_config = {
            "temperature": 0.3,
            "top_p": 0.8,
            "top_k": 40,
            "response_mime_type": "application/json"
        }
    
    async def extract_meeting_insights(self, transcript_data: dict) -> dict:
        """
        Extracts summary, action items, and key decisions from a transcript object.
        
        Args:
            transcript_data: The full transcript object from AssemblyAI.
        
        Returns:
            A dictionary containing the extracted insights.
        """
        
        # Use speaker-labeled utterances for better context
        full_text = "\n".join([f"Speaker {u['speaker']}: {u['text']}" for u in transcript_data.get('utterances', [])])
        
        if not full_text or len(full_text) < 20: # Added a length check for very short inputs
            return self._default_insights() # Use a helper to return a default structure

        # --- START OF THE NEW, SUPERCHARGED PROMPT ---
        prompt = f"""
            You are a world-class AI meeting analyst for a platform called Samwaad AI. Your task is to analyze the following meeting transcript and provide a deep, structured analysis.

            Transcript:
            ---
            {full_text}
            ---

            Carefully analyze the entire transcript and respond ONLY with a single, valid JSON object. The JSON object must have the following keys:

            1. "title": A short, descriptive title for the meeting, max 5-7 words.

            2. "summary": A concise, professional summary formatted as a markdown string. It must include three sections: 'Abstract' (2-3 sentence overview), 'Key Points' (a bulleted list of 3-5 main topics), and 'Next Steps' (a brief closing sentence).

            3. "sentiment": An object analyzing the meeting's tone. It must contain:
            - "overall_sentiment": A single word: "POSITIVE", "NEGATIVE", or "NEUTRAL".
            - "reasoning": A brief sentence explaining why this sentiment was chosen, citing parts of the conversation.

            4. "attendees": A list of strings identifying the names of the speakers or people mentioned (e.g., ["John", "Sarah", "Mike"]).

            5. "action_items": A list of JSON objects. Each object represents a clear, actionable task and must contain:
            - "task": A string describing the specific action.
            - "owner": A string identifying the person responsible. Default to "Unassigned".
            - "deadline": A string for the due date mentioned. Default to "Not specified".

            6. "key_decisions": A list of strings, where each string is a significant decision or firm commitment made.

            7. "questions_asked": A list of strings, where each string is an important question that was asked during the meeting.

            8. "chapters": A list of JSON objects that break the meeting into logical sections. Each object must contain:
            - "title": A short title for the chapter (e.g., "Introductions", "Project Update", "Q&A").
            - "summary": A one-sentence summary of what was discussed in that chapter.
            
            Do not include any text, explanations, or markdown formatting outside of the main JSON object.
            """
        try:
            # Your existing Gemini call is perfect. No changes needed here.
            response = await self.model.generate_content_async(
                prompt,
                generation_config=self.json_config # Assuming this sets response_mime_type to json
            )
            
            # Clean and parse the JSON response
            cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
            insights = json.loads(cleaned_response)
            
            # Ensure all keys exist to prevent errors later
            for key in ['title', 'summary', 'sentiment', 'attendees', 'action_items', 'key_decisions', 'questions_asked', 'chapters']:
                if key not in insights:
                    insights[key] = self._default_insights()[key]
            
            print("✅ AI generated professional-grade insights.")
            return insights
        except Exception as e:
            print(f"❌ Error generating insights with Gemini: {str(e)}")
            # Fallback in case of AI failure
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
        """Return a default, empty insights structure to prevent errors."""
        return {
            "title": "Meeting Analysis",
            "summary": "### Abstract\nNo summary could be generated.\n\n### Key Points\n- Analysis could not be completed.\n\n### Next Steps\nN/A",
            "sentiment": {
                "overall_sentiment": "UNKNOWN",
                "reasoning": "Analysis could not be completed."
            },
            "attendees": [],
            "action_items": [],
            "key_decisions": [],
            "questions_asked": [],
            "chapters": []
        }
    # Add this method inside the AIService class in ai_service.py

    async def extract_actionable_tasks(self, full_text: str) -> List[Dict]:
        """
        Extracts specific, structured tasks like calendar events from a transcript.
        """
        if not full_text:
            return []

        # We will give the AI an example to ensure it returns the correct format.
        # This is called "few-shot prompting" and is incredibly powerful.
        prompt = f"""
        Analyze the following meeting transcript. Your goal is to identify and extract any tasks that involve scheduling a meeting.
        If you find a scheduling task, you MUST format it as a JSON object within a list.

        The current date is: {datetime.now().strftime('%Y-%m-%d')}

        Example:
        Transcript: "...okay so let's schedule a follow-up with the design team for next Friday at 3 PM to review the mockups for about 45 minutes..."
        Your JSON output:
        [
            {{
                "type": "CREATE_CALENDAR_EVENT",
                "summary": "Follow-up with design team to review mockups",
                "attendees": ["design_team@example.com"],
                "start_time": "YYYY-MM-DDTHH:MM:SS",  // Calculate 'next Friday at 3 PM' and put it here
                "duration_minutes": 45,
                "description": "Follow-up meeting to review the latest design mockups."
            }}
        ]
        
        Now, analyze this new transcript:
        ---
        {full_text}
        ---

        Based on the transcript, extract all calendar scheduling tasks into a JSON list.
        If no scheduling tasks are found, return an empty list: [].
        """

        try:
            # We use the same JSON-configured model
            response = await self.model.generate_content_async(
                prompt,
                generation_config=self.json_config
            )
            
            # Clean and parse the JSON response
            cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
            tasks = json.loads(cleaned_response)
            
            print(f"✅ AI extracted actionable tasks: {tasks}")
            return tasks

        except Exception as e:
            print(f"❌ Error extracting actionable tasks with Gemini: {str(e)}")
            return []
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