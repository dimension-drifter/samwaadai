"""
Simple Test for Google Cloud Speech-to-Text API
This uses a pre-recorded test audio file
"""
import os
from google.cloud import speech
import wave
import struct

# Set your credentials path here
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'google-credentials.json'

def create_test_audio(filename="test_audio.wav"):
    """Create a simple beep tone for testing (if you can't record)"""
    print(f"\n🎵 Creating test audio file...")
    
    sample_rate = 16000
    duration = 2  # seconds
    frequency = 440  # A4 note
    
    # Generate sine wave
    import math
    samples = []
    for i in range(int(sample_rate * duration)):
        value = int(32767 * 0.3 * math.sin(2 * math.pi * frequency * i / sample_rate))
        samples.append(struct.pack('h', value))
    
    # Save to WAV file
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(samples))
    
    print(f"✅ Test audio created: {filename}")
    return filename

def download_sample_audio():
    """Instructions to get a sample audio file"""
    print("\n📥 To test with real speech, you can:")
    print("1. Download a sample: https://www.voiptroubleshooter.com/open_speech/american/OSR_us_000_0010_8k.wav")
    print("2. Or record yourself saying something and save as 'test_audio.wav'")
    print("3. Make sure it's 16-bit PCM WAV format, mono, 16kHz")

def transcribe_audio(audio_file):
    """Transcribe audio file using Google Cloud Speech-to-Text"""
    print(f"\n📤 Transcribing: {audio_file}")
    
    try:
        # Initialize client
        client = speech.SpeechClient()
        print("✅ Google Cloud Speech client initialized")
        
        # Read the audio file
        with open(audio_file, 'rb') as audio:
            content = audio.read()
        
        print(f"📊 Audio file size: {len(content)} bytes")
        
        audio = speech.RecognitionAudio(content=content)
        
        # Get audio info
        with wave.open(audio_file, 'rb') as wf:
            sample_rate = wf.getframerate()
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            duration = wf.getnframes() / sample_rate
        
        print(f"📊 Audio info:")
        print(f"   - Sample rate: {sample_rate}Hz")
        print(f"   - Channels: {channels}")
        print(f"   - Sample width: {sample_width} bytes")
        print(f"   - Duration: {duration:.2f} seconds")
        
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=sample_rate,
            language_code="en-US",
            enable_automatic_punctuation=True,
        )
        
        print("\n⏳ Sending to Google Cloud Speech-to-Text API...")
        
        # Perform the transcription
        response = client.recognize(config=config, audio=audio)
        
        print("\n" + "="*60)
        print("📝 TRANSCRIPTION RESULTS:")
        print("="*60)
        
        if not response.results:
            print("❌ No speech detected in the audio!")
            print("\nThis could mean:")
            print("  1. The audio file contains no speech")
            print("  2. The audio is too quiet")
            print("  3. Wrong audio format/encoding")
            return None
        
        # Print all results
        for i, result in enumerate(response.results):
            alternative = result.alternatives[0]
            print(f"\nResult {i+1}:")
            print(f"  Text: '{alternative.transcript}'")
            print(f"  Confidence: {alternative.confidence:.2%}")
        
        print("="*60)
        
        return response.results[0].alternatives[0].transcript
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("="*60)
    print("  GOOGLE CLOUD SPEECH-TO-TEXT - SIMPLE TEST")
    print("="*60)
    
    # Check if credentials are set
    cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '')
    if not os.path.exists(cred_path):
        print("\n❌ ERROR: Google Cloud credentials file not found!")
        print(f"Looking for: {cred_path}")
        print("\nPlease:")
        print("1. Download your service account JSON key from Google Cloud Console")
        print("2. Save it as 'google-credentials.json' in this directory")
        print("3. Or update the path at the top of this script")
        return
    
    print(f"✅ Credentials file found: {cred_path}")
    
    # Check if test audio exists
    audio_file = "test_audio.wav"
    
    if not os.path.exists(audio_file):
        print(f"\n⚠️ Audio file '{audio_file}' not found")
        print("\nYou have two options:")
        print("1. Create your own: Record yourself and save as 'test_audio.wav'")
        print("2. Use a sample from the internet")
        
        choice = input("\nCreate a test beep file? (y/n): ").lower()
        if choice == 'y':
            audio_file = create_test_audio()
        else:
            download_sample_audio()
            return
    
    print(f"\n📁 Using audio file: {audio_file}")
    
    # Transcribe
    transcript = transcribe_audio(audio_file)
    
    if transcript:
        print("\n✅ SUCCESS! Google Cloud Speech-to-Text is working!")
        print(f"📝 Transcription: \"{transcript}\"")
    else:
        print("\n⚠️ Transcription failed. See error above.")

if __name__ == "__main__":
    main()