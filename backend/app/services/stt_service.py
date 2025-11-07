"""
Speech-to-Text Service using AssemblyAI
Handles real-time audio transcription
"""

import assemblyai as aai
from typing import Optional, Callable, Dict, List
import asyncio
from app.config import settings

class STTService:
    """AssemblyAI Speech-to-Text Service"""
    
    def __init__(self):
        """Initialize AssemblyAI with API key"""
        if not settings.ASSEMBLYAI_API_KEY:
            raise ValueError("ASSEMBLYAI_API_KEY not set in environment")
        
        aai.settings.api_key = settings.ASSEMBLYAI_API_KEY
        self.transcriber: Optional[aai.RealtimeTranscriber] = None
        self.transcript_queue = asyncio.Queue()
        self.is_connected = False
        
    def on_open(self, session_opened: aai.RealtimeSessionOpened):
        """Callback when connection opens"""
        print(f"✅ AssemblyAI connection opened - Session ID: {session_opened.session_id}")
        self.is_connected = True
    
    def on_data(self, transcript: aai.RealtimeTranscript):
        """Callback when transcript data is received"""
        if not transcript.text:
            return
        
        # Only process final transcripts
        if isinstance(transcript, aai.RealtimeFinalTranscript):
            transcript_data = {
                'text': transcript.text,
                'confidence': transcript.confidence,
                'created': transcript.created,
                'audio_start': transcript.audio_start,
                'audio_end': transcript.audio_end,
                'words': [
                    {
                        'text': word.text,
                        'start': word.start,
                        'end': word.end,
                        'confidence': word.confidence
                    }
                    for word in transcript.words
                ] if transcript.words else []
            }
            
            # Put in queue for async retrieval
            asyncio.create_task(self.transcript_queue.put(transcript_data))
            print(f"📝 Transcript: {transcript.text}")
        
        # Partial transcripts (optional - for live display)
        elif isinstance(transcript, aai.RealtimePartialTranscript):
            print(f"⏳ Partial: {transcript.text}")
    
    def on_error(self, error: aai.RealtimeError):
        """Callback when error occurs"""
        print(f"❌ AssemblyAI Error: {error}")
        self.is_connected = False
    
    def on_close(self):
        """Callback when connection closes"""
        print("👋 AssemblyAI connection closed")
        self.is_connected = False
    
    async def start_transcription(self):
        """Start real-time transcription session"""
        try:
            self.transcriber = aai.RealtimeTranscriber(
                sample_rate=16000,
                on_data=self.on_data,
                on_error=self.on_error,
                on_open=self.on_open,
                on_close=self.on_close,
                # Optional configuration
                encoding=aai.AudioEncoding.pcm_s16le,
                # Enable word-level timestamps
                word_boost=["action", "task", "follow-up", "deadline", "meeting"],
                # Disable automatic punctuation if needed
                # disable_automatic_punctuation=False
            )
            
            # Connect to AssemblyAI
            self.transcriber.connect()
            
            # Wait for connection
            await asyncio.sleep(1)
            
            return True
        
        except Exception as e:
            print(f"❌ Failed to start transcription: {str(e)}")
            return False
    
    async def stream_audio(self, audio_data: bytes):
        """
        Stream audio data to AssemblyAI
        
        Args:
            audio_data: Raw audio bytes (PCM 16-bit, 16kHz, mono)
        """
        if not self.transcriber or not self.is_connected:
            raise Exception("Transcriber not connected. Call start_transcription() first.")
        
        try:
            self.transcriber.stream(audio_data)
        except Exception as e:
            print(f"❌ Error streaming audio: {str(e)}")
            raise
    
    async def get_transcript(self) -> Optional[Dict]:
        """
        Get next transcript from queue (non-blocking)
        
        Returns:
            Transcript dict or None if queue is empty
        """
        try:
            transcript = await asyncio.wait_for(
                self.transcript_queue.get(), 
                timeout=0.1
            )
            return transcript
        except asyncio.TimeoutError:
            return None
    
    async def close(self):
        """Close the transcription session"""
        if self.transcriber:
            self.transcriber.close()
            self.is_connected = False
            print("✅ Transcription session closed")
    
    # Batch transcription (for recorded audio files)
    async def transcribe_audio_file(self, audio_url: str) -> Dict:
        """
        Transcribe a pre-recorded audio file
        
        Args:
            audio_url: URL or local path to audio file
            
        Returns:
            Full transcription with timestamps
        """
        try:
            config = aai.TranscriptionConfig(
                speaker_labels=True,  # Enable speaker diarization
                auto_chapters=True,   # Auto-generate chapters
                sentiment_analysis=True  # Sentiment analysis
            )
            
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(audio_url, config=config)
            
            if transcript.status == aai.TranscriptStatus.error:
                raise Exception(f"Transcription failed: {transcript.error}")
            
            return {
                'id': transcript.id,
                'text': transcript.text,
                'confidence': transcript.confidence,
                'words': [
                    {
                        'text': word.text,
                        'start': word.start,
                        'end': word.end,
                        'confidence': word.confidence,
                        'speaker': getattr(word, 'speaker', None)
                    }
                    for word in transcript.words
                ],
                'utterances': [
                    {
                        'text': utterance.text,
                        'start': utterance.start,
                        'end': utterance.end,
                        'confidence': utterance.confidence,
                        'speaker': utterance.speaker
                    }
                    for utterance in (transcript.utterances or [])
                ] if hasattr(transcript, 'utterances') else [],
                'sentiment_analysis': transcript.sentiment_analysis_results if hasattr(transcript, 'sentiment_analysis_results') else None
            }
        
        except Exception as e:
            print(f"❌ Batch transcription error: {str(e)}")
            raise


# Example usage
async def test_stt_service():
    """Test function for STT service"""
    service = STTService()
    
    # Start transcription
    await service.start_transcription()
    
    # Simulate streaming audio (in real scenario, this comes from WebSocket)
    # For testing, you'd need actual audio bytes
    
    # Get transcripts
    while True:
        transcript = await service.get_transcript()
        if transcript:
            print(f"Got transcript: {transcript}")
        await asyncio.sleep(0.1)
    
    # Close when done
    await service.close()


if __name__ == "__main__":
    # Test the service
    asyncio.run(test_stt_service())