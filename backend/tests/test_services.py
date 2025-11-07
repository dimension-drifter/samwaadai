"""
Comprehensive service testing script
Run this to test all services independently
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.stt_service import STTService
from app.services.ai_service import AIService
from app.services.email_service import EmailService
from app.services.calendar_service import CalendarService
from app.services.crm_service import CRMService
from app.config import settings

class ServiceTester:
    """Test all services"""
    
    def __init__(self):
        self.results = {}
    
    async def test_ai_service(self):
        """Test AI Service"""
        print("\n" + "="*60)
        print("🧠 TESTING AI SERVICE (Gemini)")
        print("="*60)
        
        try:
            service = AIService()
            
            # Test transcript
            sample_transcript = """
            John: Hey team, thanks for joining today's meeting.
            Sarah: Happy to be here. What's on the agenda?
            John: We need to discuss the Q4 product launch. Sarah, can you handle the marketing materials?
            Sarah: Sure, I'll have them ready by next Friday, November 15th.
            Mike: I'll coordinate with the development team for the release schedule.
            John: Perfect. Let's also schedule a follow-up meeting next week to review progress.
            Sarah: Sounds good. I think this launch will be very successful.
            John: Great! One more thing - Mike, please send the technical specs to the client by end of day.
            Mike: Will do!
            """
            
            print("\n📝 Sample Transcript:")
            print(sample_transcript[:200] + "...")
            
            # Extract insights
            print("\n⏳ Extracting insights...")
            insights = await service.extract_meeting_insights(sample_transcript)
            
            print("\n✅ Insights Extracted:")
            print(f"   Summary: {insights.get('summary', 'N/A')}")
            print(f"   Sentiment: {insights.get('sentiment', 'N/A')}")
            print(f"   Action Items: {len(insights.get('action_items', []))}")
            print(f"   Key Decisions: {len(insights.get('key_decisions', []))}")
            
            print("\n📋 Action Items:")
            for i, item in enumerate(insights.get('action_items', []), 1):
                print(f"   {i}. {item.get('task')} - {item.get('person', 'Unassigned')} (Priority: {item.get('priority', 'medium')})")
            
            print("\n💡 Key Decisions:")
            for i, decision in enumerate(insights.get('key_decisions', []), 1):
                print(f"   {i}. {decision}")
            
            # Test email generation
            print("\n📧 Testing email generation...")
            email_content = await service.generate_email_content(
                context=insights,
                recipient="Sarah",
                purpose="Follow-up on action items"
            )
            
            print(f"   Subject: {email_content.get('subject')}")
            print(f"   Body preview: {email_content.get('body', '')[:100]}...")
            
            self.results['ai_service'] = {
                'status': 'PASSED ✅',
                'insights_extracted': True,
                'email_generated': True
            }
            
        except Exception as e:
            print(f"\n❌ AI Service Test Failed: {str(e)}")
            self.results['ai_service'] = {
                'status': 'FAILED ❌',
                'error': str(e)
            }
    
    async def test_email_service(self):
        """Test Email Service"""
        print("\n" + "="*60)
        print("📧 TESTING EMAIL SERVICE (SendGrid)")
        print("="*60)
        
        try:
            service = EmailService()
            
            if not service.client:
                print("\n⚠️ SendGrid not configured - skipping email test")
                self.results['email_service'] = {
                    'status': 'SKIPPED ⚠️',
                    'reason': 'API key not configured'
                }
                return
            
            print("\n📨 Testing email generation (not sending)...")
            
            # Generate meeting summary email
            meeting_data = {
                'title': 'Q4 Strategy Meeting',
                'date': '2024-11-07',
                'summary': 'Discussed Q4 product launch and marketing strategy',
                'action_items': [
                    {'task': 'Prepare marketing materials', 'person': 'Sarah', 'priority': 'high', 'deadline': '2024-11-15'},
                    {'task': 'Send technical specs', 'person': 'Mike', 'priority': 'high'}
                ],
                'key_decisions': [
                    'Launch product in December',
                    'Increase marketing budget by 20%'
                ],
                'participants': ['John', 'Sarah', 'Mike'],
                'sentiment': 'positive'
            }
            
            # Generate HTML
            html_body = service._generate_meeting_summary_html(meeting_data)
            
            print(f"   ✅ Email HTML generated ({len(html_body)} characters)")
            print(f"   Preview: Meeting summary with {len(meeting_data['action_items'])} action items")
            
            # Note: Uncomment below to actually send test email
            # result = await service.send_email(
            #     to_email="your-email@example.com",
            #     subject="Test Email from Call Tracker AI",
            #     body=html_body
            # )
            # print(f"   Send result: {result}")
            
            self.results['email_service'] = {
                'status': 'PASSED ✅',
                'html_generated': True
            }
            
        except Exception as e:
            print(f"\n❌ Email Service Test Failed: {str(e)}")
            self.results['email_service'] = {
                'status': 'FAILED ❌',
                'error': str(e)
            }
    
    async def test_calendar_service(self):
        """Test Calendar Service"""
        print("\n" + "="*60)
        print("📅 TESTING CALENDAR SERVICE (Google Calendar)")
        print("="*60)
        
        try:
            service = CalendarService()
            
            print("\n🔐 Attempting to authenticate...")
            
            # Check if credentials exist
            if not os.path.exists(service.credentials_path):
                print(f"\n⚠️ Credentials file not found: {service.credentials_path}")
                print("   To enable Google Calendar:")
                print("   1. Go to https://console.cloud.google.com/")
                print("   2. Create a project and enable Google Calendar API")
                print("   3. Create OAuth 2.0 credentials")
                print("   4. Download credentials.json to project root")
                
                self.results['calendar_service'] = {
                    'status': 'SKIPPED ⚠️',
                    'reason': 'Credentials not configured'
                }
                return
            
            # Try to authenticate
            if service.authenticate():
                print("   ✅ Authentication successful!")
                
                # Get upcoming events
                print("\n📋 Fetching upcoming events...")
                events = await service.get_upcoming_events(max_results=5)
                
                print(f"   Found {len(events)} upcoming events:")
                for event in events[:3]:
                    print(f"   - {event['summary']} at {event['start']}")
                
                # Note: Uncomment to create test event
                # print("\n📝 Creating test event...")
                # result = await service.create_event(
                #     summary="Test Event from Call Tracker AI",
                #     description="This is a test event",
                #     start_time=datetime.utcnow() + timedelta(days=1),
                #     duration_minutes=30
                # )
                # print(f"   Created: {result}")
                
                self.results['calendar_service'] = {
                    'status': 'PASSED ✅',
                    'authenticated': True,
                    'events_fetched': len(events)
                }
            else:
                print("   ❌ Authentication failed")
                self.results['calendar_service'] = {
                    'status': 'FAILED ❌',
                    'error': 'Authentication failed'
                }
            
        except Exception as e:
            print(f"\n❌ Calendar Service Test Failed: {str(e)}")
            self.results['calendar_service'] = {
                'status': 'FAILED ❌',
                'error': str(e)
            }
    
    async def test_crm_service(self):
        """Test CRM Service"""
        print("\n" + "="*60)
        print("📊 TESTING CRM SERVICE (SQLite)")
        print("="*60)
        
        try:
            service = CRMService(use_google_sheets=False)
            
            # Create test contact
            print("\n👤 Creating test contact...")
            contact_id = await service.create_or_update_contact({
                'name': 'John Doe',
                'email': 'john.doe@example.com',
                'company': 'Acme Corporation',
                'title': 'CEO',
                'phone': '+1-555-0123',
                'tags': ['vip', 'customer', 'test']
            })
            
            print(f"   ✅ Contact created with ID: {contact_id}")
            
            # Log interaction
            print("\n📝 Logging test interaction...")
            await service.log_interaction({
                'contact_email': 'john.doe@example.com',
                'contact_name': 'John Doe',
                'type': 'call',
                'duration_seconds': 1800,
                'summary': 'Discussed Q4 strategy and partnership opportunities',
                'sentiment': 'positive',
                'action_items': [
                    {'task': 'Send proposal', 'deadline': '2024-11-15'},
                    {'task': 'Schedule follow-up', 'deadline': '2024-11-20'}
                ]
            })
            
            print("   ✅ Interaction logged")
            
            # Retrieve contact
            print("\n🔍 Retrieving contact...")
            contact = await service.get_contact_by_email('john.doe@example.com')
            print(f"   Name: {contact.get('name')}")
            print(f"   Company: {contact.get('company')}")
            print(f"   Last Interaction: {contact.get('last_interaction')}")
            print(f"   Total Interactions: {contact.get('interaction_count')}")
            
            # Get stats
            print("\n📊 CRM Statistics:")
            stats = await service.get_stats()
            print(f"   Total Contacts: {stats['total_contacts']}")
            print(f"   Total Interactions: {stats['total_interactions']}")
            print(f"   This Week: {stats['interactions_this_week']}")
            
            # Search contacts
            print("\n🔎 Testing search...")
            results = await service.search_contacts('john')
            print(f"   Found {len(results)} contacts matching 'john'")
            
            # Get recent interactions
            print("\n📅 Recent interactions:")
            recent = await service.get_recent_interactions(limit=5)
            for interaction in recent[:3]:
                print(f"   - {interaction.get('contact_name')}: {interaction.get('summary', 'N/A')[:50]}...")
            
            service.close()
            
            self.results['crm_service'] = {
                'status': 'PASSED ✅',
                'contact_created': True,
                'interaction_logged': True,
                'search_works': True
            }
            
        except Exception as e:
            print(f"\n❌ CRM Service Test Failed: {str(e)}")
            self.results['crm_service'] = {
                'status': 'FAILED ❌',
                'error': str(e)
            }
    
    async def test_stt_service(self):
        """Test STT Service"""
        print("\n" + "="*60)
        print("🎤 TESTING STT SERVICE (AssemblyAI)")
        print("="*60)
        
        try:
            if not settings.ASSEMBLYAI_API_KEY:
                print("\n⚠️ AssemblyAI API key not configured")
                print("   Set ASSEMBLYAI_API_KEY in .env file")
                self.results['stt_service'] = {
                    'status': 'SKIPPED ⚠️',
                    'reason': 'API key not configured'
                }
                return
            
            service = STTService()
            
            print("\n✅ STT Service initialized")
            print("   Note: Real-time transcription requires audio stream")
            print("   This test verifies initialization only")
            
            # Note: Full test requires actual audio data
            # In production, audio would come from WebSocket
            
            self.results['stt_service'] = {
                'status': 'PASSED ✅',
                'initialized': True,
                'note': 'Full test requires audio stream'
            }
            
        except Exception as e:
            print(f"\n❌ STT Service Test Failed: {str(e)}")
            self.results['stt_service'] = {
                'status': 'FAILED ❌',
                'error': str(e)
            }
    
    async def run_all_tests(self):
        """Run all service tests"""
        print("\n" + "="*60)
        print("🚀 STARTING SERVICE TESTS")
        print("="*60)
        
        # Run tests
        await self.test_ai_service()
        await self.test_email_service()
        await self.test_calendar_service()
        await self.test_crm_service()
        await self.test_stt_service()
        
        # Print summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        for service_name, result in self.results.items():
            status = result.get('status', 'UNKNOWN')
            print(f"\n{service_name.replace('_', ' ').title()}: {status}")
            
            if 'error' in result:
                print(f"   Error: {result['error']}")
            elif 'reason' in result:
                print(f"   Reason: {result['reason']}")
        
        # Overall result
        passed = sum(1 for r in self.results.values() if 'PASSED' in r.get('status', ''))
        total = len(self.results)
        
        print("\n" + "="*60)
        print(f"🎯 OVERALL: {passed}/{total} services passed")
        print("="*60)


async def main():
    """Main test runner"""
    tester = ServiceTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())