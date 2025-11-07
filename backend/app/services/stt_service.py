"""
Speech-to-Text Service using Google Cloud Speech-to-Text
Handles batch audio transcription with speaker diarization
"""
from google.cloud import speech
from typing import Dict, List
from app.config import settings
import os
import wave

class STTService:
    """Google Cloud Speech-to-Text Service with diarization"""
    
    def __init__(self):
        """Initialize Google Cloud Speech client"""
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.GOOGLE_APPLICATION_CREDENTIALS
        
        self.client = speech.SpeechClient()
    
    async def transcribe_audio_file(self, audio_path: str) -> Dict:
        """
        Transcribe a pre-recorded audio file with speaker diarization.
        
        Args:
            audio_path: Local path to the audio file (must be 16kHz WAV).
            
        Returns:
            Full transcription result with speaker labels as a dictionary.
        """
        try:
            # Get WAV file info
            with wave.open(audio_path, 'rb') as wf:
                sample_rate = wf.getframerate()
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                frames = wf.getnframes()
                duration = frames / sample_rate
            
            print(f"🎤 Starting Google Cloud Speech transcription")
            print(f"   - File: {audio_path}")
            print(f"   - Sample rate: {sample_rate}Hz")
            print(f"   - Channels: {channels}")
            print(f"   - Duration: {duration:.2f}s")
            
            # Read audio file
            with open(audio_path, 'rb') as audio_file:
                audio_content = audio_file.read()
            
            print(f"   - Audio size: {len(audio_content)} bytes")
            
            audio = speech.RecognitionAudio(content=audio_content)
            
            # Configure diarization
            diarization_config = speech.SpeakerDiarizationConfig(
                enable_speaker_diarization=True,
                min_speaker_count=1,
                max_speaker_count=6,
            )
            
            # Configure recognition - MUST match the actual WAV file format
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=sample_rate,  # Use actual sample rate from WAV
                language_code="en-US",
                enable_automatic_punctuation=True,
                enable_word_time_offsets=True,
                diarization_config=diarization_config,
                model="latest_long",
                use_enhanced=True,
                audio_channel_count=channels,
            )
            
            print("📤 Sending to Google Cloud Speech API...")
            print("   (This may take 5-15 seconds...)")
            
            # Perform transcription
            response = self.client.recognize(config=config, audio=audio)
            
            print(f"📥 Response received!")
            print(f"   - Results: {len(response.results)}")
            
            if not response.results:
                print("❌ No transcription results returned")
                print("   Troubleshooting:")
                print("   1. Check if audio contains clear speech")
                print("   2. Verify microphone is working")
                print("   3. Ensure audio is loud enough")
                print("   4. Try speaking for 3-5 seconds")
                return {
                    'id': 'google-cloud-speech',
                    'text': '',
                    'confidence': 0.0,
                    'audio_duration': int(duration * 1000),
                    'sentiment_analysis_results': [],
                    'chapters': [],
                    'utterances': []
                }
            
            # Process results with diarization
            full_transcript = []
            utterances = []
            words_info = []
            
            for i, result in enumerate(response.results):
                alternative = result.alternatives[0]
                print(f"   ✓ Result {i+1}: '{alternative.transcript}'")
                print(f"     Confidence: {alternative.confidence:.1%}")
                
                # Get words with speaker tags
                for word_info in alternative.words:
                    word = word_info.word
                    start_time = word_info.start_time.total_seconds()
                    end_time = word_info.end_time.total_seconds()
                    speaker_tag = word_info.speaker_tag if hasattr(word_info, 'speaker_tag') else 1
                    
                    words_info.append({
                        'word': word,
                        'start': start_time,
                        'end': end_time,
                        'speaker': speaker_tag
                    })
                
                full_transcript.append(alternative.transcript)
            
            # Group words into utterances by speaker
            if words_info:
                current_speaker = words_info[0]['speaker']
                current_text = []
                current_start = words_info[0]['start']
                
                for i, word_data in enumerate(words_info):
                    if word_data['speaker'] != current_speaker:
                        # Save previous utterance
                        utterances.append({
                            'text': ' '.join(current_text),
                            'start': current_start,
                            'end': words_info[i - 1]['end'],
                            'confidence': 0.9,
                            'speaker': f"Speaker {current_speaker}"
                        })
                        
                        # Start new utterance
                        current_speaker = word_data['speaker']
                        current_text = [word_data['word']]
                        current_start = word_data['start']
                    else:
                        current_text.append(word_data['word'])
                
                # Add final utterance
                if current_text:
                    utterances.append({
                        'text': ' '.join(current_text),
                        'start': current_start,
                        'end': words_info[-1]['end'],
                        'confidence': 0.9,
                        'speaker': f"Speaker {current_speaker}"
                    })
            
            full_text = ' '.join(full_transcript)
            
            # Calculate audio duration
            audio_duration = int(duration * 1000)
            if words_info:
                audio_duration = int(words_info[-1]['end'] * 1000)
            
            result = {
                'id': 'google-cloud-speech',
                'text': full_text,
                'confidence': response.results[0].alternatives[0].confidence if response.results else 0.0,
                'audio_duration': audio_duration,
                'sentiment_analysis_results': [],
                'chapters': [],
                'utterances': utterances,
                'words': words_info
            }
            
            unique_speakers = len(set([u['speaker'] for u in utterances])) if utterances else 0
            
            print(f"✅ Transcription SUCCESS!")
            print(f"   📝 Text: '{full_text}'")
            print(f"   📏 Length: {len(full_text)} characters")
            print(f"   ⏱️  Duration: {audio_duration/1000:.2f}s")
            print(f"   📊 Confidence: {result['confidence']:.1%}")
            print(f"   💬 Utterances: {len(utterances)}")
            print(f"   👥 Speakers: {unique_speakers}")
            
            return result
        
        except Exception as e:
            print(f"❌ Google Cloud Speech error: {str(e)}")
            import traceback
            traceback.print_exc()
            raise