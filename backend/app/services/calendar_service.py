"""
Calendar Service using Google Calendar API
Handles automated calendar event creation and reminders
"""

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
import json
from app.config import settings

# Scopes required for Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Define the project's base directory (the 'backend' folder)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class CalendarService:
    """Google Calendar Automation Service"""
    
    def __init__(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None):
        """
        Initialize Google Calendar service
        
        Args:
            credentials_path: Path to OAuth2 credentials JSON file
            token_path: Path to store user tokens
        """
        # Use absolute paths to avoid ambiguity
        self.credentials_path = credentials_path or os.path.join(BASE_DIR, settings.GOOGLE_CREDENTIALS_PATH)
        self.token_path = token_path or os.path.join(BASE_DIR, settings.GOOGLE_TOKEN_PATH)
        self.service = None
        self.creds = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google Calendar API
        
        Returns:
            True if authentication successful
        """
        try:
            # Load existing token
            if os.path.exists(self.token_path):
                self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            
            # Refresh token if expired
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            
            # Get new token if needed
            elif not self.creds or not self.creds.valid:
                if not os.path.exists(self.credentials_path):
                    print(f"⚠️ Credentials file not found: {self.credentials_path}")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_path, 'w') as token:
                token.write(self.creds.to_json())
            
            # Build service
            self.service = build('calendar', 'v3', credentials=self.creds)
            print("✅ Google Calendar authenticated successfully")
            return True
        
        except Exception as e:
            print(f"❌ Failed to authenticate Google Calendar: {str(e)}")
            return False
    
    async def create_event(
        self,
        summary: str,
        description: str,
        start_time: datetime,
        duration_minutes: int = 30,
        attendees: Optional[List[str]] = None,
        location: Optional[str] = None,
        timezone: str = "UTC"
    ) -> Optional[Dict]:
        """
        Create a calendar event
        
        Args:
            summary: Event title
            description: Event description
            start_time: Event start time
            duration_minutes: Duration in minutes
            attendees: List of attendee emails
            location: Event location (or meeting URL)
            
        Returns:
            Created event details or None
        """
        
        if not self.service:
            if not self.authenticate():
                return None
        
        try:
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': timezone, # MODIFICATION 2: Use the timezone variable
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': timezone,
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 30},       # 30 min before
                    ],
                },
            }
            
            # Add attendees
            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]
            
            # Add location
            if location:
                event['location'] = location
            
            # Create event
            event = self.service.events().insert(
                calendarId='primary',
                body=event,
                sendUpdates='all'  # Send notifications to attendees
            ).execute()
            
            print(f"✅ Calendar event created: {event.get('htmlLink')}")
            
            return {
                'id': event['id'],
                'summary': event['summary'],
                'start': event['start']['dateTime'],
                'end': event['end']['dateTime'],
                'link': event.get('htmlLink'),
                'hangout_link': event.get('hangoutLink')
            }
        
        except HttpError as error:
            print(f"❌ Failed to create calendar event: {error}")
            return None
    
    async def create_reminder(
        self,
        title: str,
        reminder_time: datetime,
        description: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Create a reminder (0-minute event)
        
        Args:
            title: Reminder title
            reminder_time: When to show the reminder
            description: Optional description
            
        Returns:
            Created reminder details or None
        """
        
        if not self.service:
            if not self.authenticate():
                return None
        
        try:
            event = {
                'summary': f"⏰ Reminder: {title}",
                'description': description or f"Reminder: {title}",
                'start': {
                    'dateTime': reminder_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': reminder_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 0},
                    ],
                },
            }
            
            event = self.service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            print(f"✅ Reminder created: {title}")
            
            return {
                'id': event['id'],
                'summary': event['summary'],
                'time': event['start']['dateTime']
            }
        
        except HttpError as error:
            print(f"❌ Failed to create reminder: {error}")
            return None
    
    async def create_follow_up_meeting(
        self,
        action_item: Dict,
        days_from_now: int = 7
    ) -> Optional[Dict]:
        """
        Create a follow-up meeting based on action item
        
        Args:
            action_item: Action item details
            days_from_now: Days from now to schedule meeting
            
        Returns:
            Created event details
        """
        
        start_time = datetime.utcnow() + timedelta(days=days_from_now)
        
        # Round to next hour
        start_time = start_time.replace(minute=0, second=0, microsecond=0)
        
        summary = f"Follow-up: {action_item.get('task', 'Discussion')}"
        description = f"""
        Follow-up meeting to discuss:
        
        Task: {action_item.get('task', 'N/A')}
        Assigned to: {action_item.get('person', 'TBD')}
        Priority: {action_item.get('priority', 'medium')}
        
        This meeting was automatically scheduled by Call Tracker AI.
        """
        
        attendees = []
        if action_item.get('person'):
            # In real scenario, map person name to email
            attendees.append(action_item['person'])
        
        return await self.create_event(
            summary=summary,
            description=description,
            start_time=start_time,
            duration_minutes=30,
            attendees=attendees
        )
    
    async def get_upcoming_events(self, max_results: int = 10) -> List[Dict]:
        """
        Get upcoming calendar events
        
        Args:
            max_results: Maximum number of events to return
            
        Returns:
            List of upcoming events
        """
        
        if not self.service:
            if not self.authenticate():
                return []
        
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            return [
                {
                    'id': event['id'],
                    'summary': event.get('summary', 'No title'),
                    'start': event['start'].get('dateTime', event['start'].get('date')),
                    'end': event['end'].get('dateTime', event['end'].get('date')),
                    'link': event.get('htmlLink')
                }
                for event in events
            ]
        
        except HttpError as error:
            print(f"❌ Failed to get events: {error}")
            return []
    
    async def delete_event(self, event_id: str) -> bool:
        """
        Delete a calendar event
        
        Args:
            event_id: Google Calendar event ID
            
        Returns:
            True if successful
        """
        
        if not self.service:
            if not self.authenticate():
                return False
        
        try:
            self.service.events().delete(
                calendarId='primary',
                eventId=event_id
            ).execute()
            
            print(f"✅ Event deleted: {event_id}")
            return True
        
        except HttpError as error:
            print(f"❌ Failed to delete event: {error}")
            return False


# Example usage
async def test_calendar_service():
    """Test function for calendar service"""
    service = CalendarService()
    
    # Authenticate
    if service.authenticate():
        # Create a test event
        result = await service.create_event(
            summary="Test Meeting from Call Tracker AI",
            description="This is a test event",
            start_time=datetime.utcnow() + timedelta(days=1),
            duration_minutes=60,
            attendees=["test@example.com"]
        )
        print("Event created:", result)
        
        # Create a reminder
        reminder = await service.create_reminder(
            title="Test Task Deadline",
            reminder_time=datetime.utcnow() + timedelta(hours=2)
        )
        print("Reminder created:", reminder)
        
        # Get upcoming events
        events = await service.get_upcoming_events()
        print(f"Upcoming events: {len(events)}")
        for event in events:
            print(f"  - {event['summary']} at {event['start']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_calendar_service())