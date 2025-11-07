import asyncio
import os
import json
from datetime import datetime, timedelta
from app.services.calendar_service import CalendarService

async def test_calendar():
    """Test Google Calendar connection"""
    
    # Use absolute path for credentials
    base_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(base_dir, "credentials.json")
    
    print(f"Looking for credentials at: {creds_path}")
    
    # Check if credentials file exists
    if not os.path.exists(creds_path):
        print(f"❌ Error: {creds_path} not found!")
        return
    
    # Validate credentials file format
    try:
        with open(creds_path, 'r') as f:
            content = f.read()
            if not content.strip():
                print("❌ Error: credentials.json is empty!")
                return
            
            creds_data = json.loads(content)
            if 'installed' not in creds_data:
                print("❌ Error: Invalid credentials format!")
                print("Expected format:")
                print('''
{
    "installed": {
        "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
        "project_id": "call-tracker-ai",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": "YOUR_CLIENT_SECRET",
        "redirect_uris": ["http://localhost"]
    }
}''')
                return
            
            print("✅ Credentials file format is valid")
            
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in credentials file: {str(e)}")
        print(f"File contents: {content[:100]}...")  # Show start of file
        return
    except Exception as e:
        print(f"❌ Error reading credentials: {str(e)}")
        return
    
    service = CalendarService()
    print("\n🔐 Authenticating with Google Calendar...")
    
    try:
        if service.authenticate():
            print("✅ Authentication successful!\n")
            
            print("📅 Fetching your upcoming events...")
            events = await service.get_upcoming_events(max_results=5)
            
            print(f"\nFound {len(events)} upcoming events:")
            for event in events:
                print(f"  📌 {event['summary']}")
                print(f"     🕐 {event['start']}\n")
        else:
            print("❌ Authentication failed")
            print("\nTroubleshooting steps:")
            print("1. Enable Google Calendar API at: https://console.cloud.google.com/apis/library/calendar-json.googleapis.com")
            print("2. Configure OAuth consent screen")
            print("3. Add your email as test user")
            print("4. Download new credentials and try again")
    
    except Exception as e:
        print(f"❌ Error during authentication: {str(e)}")
        print("\nDetailed troubleshooting:")
        print("1. Go to Google Cloud Console")
        print("2. Select project 'Call Tracker AI'")
        print("3. Go to APIs & Services → OAuth consent screen")
        print("4. Add your email under 'Test users'")
        print("5. Go to Credentials → Create OAuth client ID")
        print("6. Download new credentials and replace existing credentials.json")

if __name__ == "__main__":
    asyncio.run(test_calendar())