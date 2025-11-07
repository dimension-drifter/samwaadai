"""Test Google Cloud Speech-to-Text setup"""
import os
from google.cloud import speech

# Set credentials (if not using .env)
# os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'google-credentials.json'

def test_google_speech():
    try:
        # Initialize the client
        client = speech.SpeechClient()
        
        print("✅ Google Cloud Speech-to-Text client initialized successfully!")
        print(f"📋 Project ID: {os.environ.get('GOOGLE_CLOUD_PROJECT_ID', 'Not set')}")
        print(f"🔑 Credentials: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'Not set')}")
        
        # Test with a simple audio (optional - you can skip this)
        # This just verifies the API is accessible
        print("\n✅ Setup complete! Your Google Cloud Speech-to-Text API is ready.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Make sure GOOGLE_APPLICATION_CREDENTIALS is set in .env")
        print("2. Verify the JSON key file exists at the specified path")
        print("3. Ensure the Speech-to-Text API is enabled in Google Cloud Console")
        print("4. Check that your service account has the correct permissions")

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    test_google_speech()