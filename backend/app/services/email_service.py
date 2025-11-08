"""
Email Service using SendGrid
Handles automated email sending for follow-ups, meeting summaries, etc.
"""

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, Cc
from typing import List, Optional, Dict
import os
from app.config import settings

class EmailService:
    """SendGrid Email Automation Service"""
    
    def __init__(self):
        """Initialize SendGrid client"""
        if not settings.SENDGRID_API_KEY:
            print("⚠️ WARNING: SENDGRID_API_KEY not set. Email service will not work.")
            self.client = None
        else:
            self.client = SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        
        # Default sender email (configure in settings)
        self.from_email = os.getenv("SENDER_EMAIL", "pkmpunit2003@gmail.com")
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        is_html: bool = True
    ) -> Dict:
        """
        Send a single email
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (HTML or plain text)
            cc: Optional list of CC recipients
            is_html: Whether body is HTML (default True)
            
        Returns:
            Dict with success status and details
        """
        
        if not self.client:
            return {
                "success": False,
                "error": "SendGrid not configured"
            }
        
        try:
            # Create message
            message = Mail(
                from_email=Email(self.from_email),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", body) if is_html else Content("text/plain", body)
            )
            
            # Add CC recipients
            if cc:
                for cc_email in cc:
                    message.add_cc(Cc(cc_email))
            
            # Send email
            response = self.client.send(message)
            
            return {
                "success": True,
                "status_code": response.status_code,
                "message_id": response.headers.get('X-Message-Id'),
                "to": to_email
            }
        
        except Exception as e:
            print(f"❌ Failed to send email: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    async def send_post_meeting_analysis(
        self,
        to_email: str,
        insights: Dict,
        transcript_text: str
    ) -> Dict:
        """
        Generates and sends the complete post-meeting analysis email.
        """
        subject = f"Analysis for Your Meeting: {insights.get('title', 'Meeting Summary')}"
        
        body = self._generate_analysis_html(insights, transcript_text)
        
        print(f"📧 Preparing to send analysis email to {to_email}...")
        
        return await self.send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            is_html=True
        )

    def _generate_analysis_html(self, insights: Dict, transcript_text: str) -> str:
        """Generates a professional HTML email body for the meeting analysis."""

        # Safely get sentiment information
        sentiment = insights.get('sentiment', {})
        sentiment_label = sentiment.get('overall_sentiment', 'NEUTRAL').upper()
        sentiment_reason = sentiment.get('reasoning', 'Not available.')

        # Dynamically build HTML for lists to avoid empty sections
        def build_list_html(title, items, formatter):
            if not items:
                return ""
            list_items = "".join(formatter(item) for item in items)
            return f"""
                <h3 style="color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 8px; margin-top: 25px;">{title}</h3>
                <ul style="padding-left: 20px; line-height: 1.7;">{list_items}</ul>
            """

        action_items_html = build_list_html(
            "✅ Action Items", insights.get('action_items', []),
            lambda item: f"<li><strong>{item.get('task', 'N/A')}</strong> (Owner: {item.get('owner', 'Unassigned')})</li>"
        )
        decisions_html = build_list_html(
            "🎯 Key Decisions", insights.get('key_decisions', []),
            lambda item: f"<li>{item}</li>"
        )
        questions_html = build_list_html(
            "❓ Key Questions", insights.get('questions_asked', []),
            lambda item: f"<li><em>{item}</em></li>"
        )

        # Main HTML structure
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f9f9f9; padding: 20px;">
            <div style="max-width: 700px; margin: 0 auto; background-color: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
                <div style="background-color: #5a4fb7; color: white; padding: 20px; text-align: center;">
                    <h1 style="margin: 0; font-size: 24px;">Samwaad AI Meeting Analysis</h1>
                </div>
                <div style="padding: 25px;">
                    <h2 style="color: #1d1d1f; font-size: 20px;">{insights.get('title', 'Meeting Summary')}</h2>
                    
                    <div style="background: #f5f5f7; padding: 15px; border-radius: 6px; margin: 20px 0;">
                        <h3 style="margin-top:0; color: #2c3e50;">💡 AI Summary</h3>
                        {insights.get('summary', 'Not available.').replace('### Abstract', '<strong>Abstract:</strong><br/>').replace('### Key Points', '<br/><strong>Key Points:</strong>').replace('### Next Steps', '<br/><strong>Next Steps:</strong>').replace('- ', '<br/>- ')}
                    </div>

                    <div style="margin: 20px 0;">
                         <strong>Sentiment:</strong> <span style="font-weight: bold; color: {'#dc3545' if sentiment_label == 'NEGATIVE' else '#28a745' if sentiment_label == 'POSITIVE' else '#6c757d'};">{sentiment_label}</span><br>
                         <small style="color: #6c757d;">{sentiment_reason}</small>
                    </div>

                    {action_items_html}
                    {decisions_html}
                    {questions_html}

                    <details style="margin-top: 25px;">
                        <summary style="font-weight: bold; color: #5a4fb7; cursor: pointer;">View Full Transcript</summary>
                        <div style="background-color: #f8f9fa; border: 1px solid #eee; padding: 15px; margin-top: 10px; border-radius: 4px; max-height: 200px; overflow-y: auto;">
                            <p style="white-space: pre-wrap; font-size: 14px;">{transcript_text}</p>
                        </div>
                    </details>
                </div>
                <div style="background-color: #f8f9fa; text-align: center; padding: 15px; font-size: 12px; color: #999;">
                    <p>This email was automatically generated by Samwaad AI.</p>
                </div>
            </div>
        </body>
        </html>
        """
    async def send_meeting_summary(
        self,
        attendees: List[str],
        meeting_data: Dict
    ) -> Dict:
        """
        Send meeting summary to all attendees
        
        Args:
            attendees: List of attendee email addresses
            meeting_data: Dict containing meeting details
            
        Returns:
            Dict with results for each recipient
        """
        
        subject = f"Meeting Summary: {meeting_data.get('title', 'Call Summary')}"
        
        # Generate HTML email body
        body = self._generate_meeting_summary_html(meeting_data)
        
        results = []
        for email in attendees:
            result = await self.send_email(
                to_email=email,
                subject=subject,
                body=body,
                is_html=True
            )
            results.append({
                "email": email,
                "success": result["success"]
            })
        
        return {
            "total_sent": len(attendees),
            "successful": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"]),
            "details": results
        }
    
    async def send_follow_up_email(
        self,
        to_email: str,
        action_item: Dict,
        context: Dict
    ) -> Dict:
        """
        Send follow-up email for a specific action item
        
        Args:
            to_email: Recipient email
            action_item: Action item details
            context: Meeting context
            
        Returns:
            Send result
        """
        
        subject = f"Action Item: {action_item.get('task', 'Follow-up Required')}"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #2c3e50;">Action Item Follow-up</h2>
            
            <p>Hi there,</p>
            
            <p>This is a follow-up regarding an action item from our recent meeting:</p>
            
            <div style="background: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #007bff;">Task Details</h3>
                <p><strong>Task:</strong> {action_item.get('task', 'N/A')}</p>
                <p><strong>Assigned to:</strong> {action_item.get('person', 'You')}</p>
                <p><strong>Priority:</strong> {action_item.get('priority', 'Medium').upper()}</p>
                {f"<p><strong>Deadline:</strong> {action_item.get('deadline', 'TBD')}</p>" if action_item.get('deadline') else ''}
            </div>
            
            <p><strong>Meeting Context:</strong><br>
            {context.get('summary', 'No additional context available.')}</p>
            
            <p>Please let us know if you have any questions or need clarification.</p>
            
            <p>Best regards,<br>
            Call Tracker AI</p>
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="font-size: 12px; color: #999;">
                This email was automatically generated by Call Tracker AI.
            </p>
        </body>
        </html>
        """
        
        return await self.send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            is_html=True
        )
    
    async def send_task_reminder(
        self,
        to_email: str,
        task: Dict
    ) -> Dict:
        """
        Send reminder email for an upcoming task
        
        Args:
            to_email: Recipient email
            task: Task details
            
        Returns:
            Send result
        """
        
        subject = f"⏰ Reminder: {task.get('title', 'Upcoming Task')}"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #e67e22;">🔔 Task Reminder</h2>
            
            <p>Hi there,</p>
            
            <p>This is a friendly reminder about an upcoming task:</p>
            
            <div style="background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #856404;">{task.get('title', 'Task')}</h3>
                <p>{task.get('description', 'No description provided.')}</p>
                <p><strong>Deadline:</strong> {task.get('deadline', 'Not specified')}</p>
                <p><strong>Priority:</strong> <span style="color: {'#dc3545' if task.get('priority') == 'high' else '#ffc107' if task.get('priority') == 'medium' else '#28a745'};">{task.get('priority', 'medium').upper()}</span></p>
            </div>
            
            <p>Please make sure to complete this task on time.</p>
            
            <p>Best regards,<br>
            Call Tracker AI</p>
        </body>
        </html>
        """
        
        return await self.send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            is_html=True
        )
    
    def _generate_meeting_summary_html(self, meeting_data: Dict) -> str:
        """Generate HTML for meeting summary email"""
        
        action_items_html = ""
        if meeting_data.get('action_items'):
            action_items_html = "<ul>"
            for item in meeting_data['action_items']:
                action_items_html += f"""
                <li>
                    <strong>{item.get('task', 'N/A')}</strong>
                    {f" - {item.get('person', 'Unassigned')}" if item.get('person') else ''}
                    {f" (Due: {item.get('deadline', 'TBD')})" if item.get('deadline') else ''}
                </li>
                """
            action_items_html += "</ul>"
        else:
            action_items_html = "<p>No action items recorded.</p>"
        
        decisions_html = ""
        if meeting_data.get('key_decisions'):
            decisions_html = "<ul>"
            for decision in meeting_data['key_decisions']:
                decisions_html += f"<li>{decision}</li>"
            decisions_html += "</ul>"
        else:
            decisions_html = "<p>No key decisions recorded.</p>"
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; color: white;">
                <h1 style="margin: 0;">📋 Meeting Summary</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">{meeting_data.get('date', 'Recent Meeting')}</p>
            </div>
            
            <div style="padding: 30px; background: #fff;">
                <h2 style="color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 10px;">
                    📝 Summary
                </h2>
                <p>{meeting_data.get('summary', 'No summary available.')}</p>
                
                <h2 style="color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 10px; margin-top: 30px;">
                    ✅ Action Items
                </h2>
                {action_items_html}
                
                <h2 style="color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 10px; margin-top: 30px;">
                    💡 Key Decisions
                </h2>
                {decisions_html}
                
                {f'''
                <h2 style="color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 10px; margin-top: 30px;">
                    👥 Participants
                </h2>
                <p>{", ".join(meeting_data.get('participants', []))}</p>
                ''' if meeting_data.get('participants') else ''}
                
                <div style="background: #f8f9fa; padding: 20px; margin-top: 30px; border-radius: 5px;">
                    <p style="margin: 0; color: #666; font-size: 14px;">
                        <strong>💬 Sentiment:</strong> 
                        <span style="text-transform: capitalize;">{meeting_data.get('sentiment', 'neutral')}</span>
                    </p>
                </div>
            </div>
            
            <div style="background: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 12px;">
                <p>Generated automatically by Call Tracker AI</p>
                <p style="margin: 10px 0 0 0;">
                    If you have questions about any action items, please reply to this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        return html


# Example usage
async def test_email_service():
    """Test function for email service"""
    service = EmailService()
    
    # Test simple email
    result = await service.send_email(
        to_email="test@example.com",
        subject="Test Email",
        body="<h1>This is a test email</h1><p>From Call Tracker AI</p>",
        is_html=True
    )
    print("Send result:", result)
    
    # Test meeting summary
    meeting_data = {
        "title": "Q4 Planning Meeting",
        "date": "2024-11-07",
        "summary": "Discussed Q4 goals and marketing strategy",
        "action_items": [
            {"task": "Prepare marketing materials", "person": "Sarah", "deadline": "2024-11-15", "priority": "high"},
            {"task": "Schedule follow-up", "person": "John", "priority": "medium"}
        ],
        "key_decisions": [
            "Launch new feature in December",
            "Increase marketing budget by 20%"
        ],
        "participants": ["John", "Sarah", "Mike"],
        "sentiment": "positive"
    }
    
    result = await service.send_meeting_summary(
        attendees=["test1@example.com", "test2@example.com"],
        meeting_data=meeting_data
    )
    print("Meeting summary result:", result)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_email_service())