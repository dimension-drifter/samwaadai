"""
Speech-to-Text Service using Google Cloud Speech-to-Text
Handles batch audio transcription with speaker diarization
"""
from google.cloud import speech
from typing import Dict, List
from app.config import settings
import os
import wave
from google.cloud import storage


class STTService:
    """Google Cloud Speech-to-Text Service with diarization"""
    
    def __init__(self):
        """Initialize Google Cloud Speech client"""
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.GOOGLE_APPLICATION_CREDENTIALS
        
        self.client = speech.SpeechClient()
        self.client = speech.SpeechClient()
        self.storage_client = storage.Client()
        self.bucket_name = "samwaad-audio" # IMPORTANT: REPLACE WITH YOUR BUCKET NAME

    def _upload_to_gcs(self, source_file_name: str, destination_blob_name: str) -> str:
        """Uploads a file to the GCS bucket."""
        print(f"☁️ Uploading {source_file_name} to GCS bucket {self.bucket_name}...")
        bucket = self.storage_client.bucket(self.bucket_name)
        blob = bucket.blob(destination_blob_name)

        blob.upload_from_filename(source_file_name)

        gcs_uri = f"gs://{self.bucket_name}/{destination_blob_name}"
        print(f"✅ File uploaded to {gcs_uri}")
        return gcs_uri
    
    async def transcribe_audio_file(self, audio_path: str) -> Dict:
        """
        Transcribes a long audio file using Google's asynchronous API via GCS.
        """
        try:
            # Step 1: Upload the local audio file to Google Cloud Storage
            # Use a unique name for the file in the bucket, e.g., using a timestamp
            blob_name = f"audio_recordings/{os.path.basename(audio_path)}"
            gcs_uri = self._upload_to_gcs(audio_path, blob_name)

            # Step 2: Configure the long-running recognition request
            with wave.open(audio_path, 'rb') as wf:
                sample_rate = wf.getframerate()
                channels = wf.getnchannels()
                duration = wf.getnframes() / sample_rate

            print(f"🎤 Starting LONG AUDIO transcription for {gcs_uri}")
            print(f"   - Duration: {duration:.2f}s")
            
            audio = speech.RecognitionAudio(uri=gcs_uri)
            
            diarization_config = speech.SpeakerDiarizationConfig(
                enable_speaker_diarization=True, min_speaker_count=1, max_speaker_count=6
            )
            
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=sample_rate,
                language_code="en-US",
                enable_automatic_punctuation=True,
                enable_word_time_offsets=True,
                diarization_config=diarization_config,
                model="latest_long",
                use_enhanced=True,
                audio_channel_count=channels,
            )

            # Step 3: Start the asynchronous transcription job
            print("📤 Sending job to Google Cloud Speech API...")
            print("   (This will take time depending on audio length...)")
            operation = self.client.long_running_recognize(config=config, audio=audio)

            # Step 4: Wait for the job to complete
            response = operation.result(timeout=900)
            
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
                for word_info in alternative.words:
                    words_info.append({
                        'word': word_info.word, 'start': word_info.start_time.total_seconds(),
                        'end': word_info.end_time.total_seconds(), 'speaker': word_info.speaker_tag
                    })
                full_transcript.append(alternative.transcript)

            if words_info:
                # Group words into utterances (your existing logic is great)
                current_speaker = words_info[0]['speaker']
                current_text = []
                current_start = words_info[0]['start']
                for i, word_data in enumerate(words_info):
                    if word_data['speaker'] != current_speaker:
                        utterances.append({
                            'text': ' '.join(current_text), 'start': current_start,
                            'end': words_info[i - 1]['end'], 'confidence': 0.9, 'speaker': f"Speaker {current_speaker}"
                        })
                        current_speaker = word_data['speaker']
                        current_text = [word_data['word']]
                        current_start = word_data['start']
                    else:
                        current_text.append(word_data['word'])
                if current_text:
                    utterances.append({
                        'text': ' '.join(current_text), 'start': current_start,
                        'end': words_info[-1]['end'], 'confidence': 0.9, 'speaker': f"Speaker {current_speaker}"
                    })

            full_text = ' '.join(full_transcript)
            result_payload = {
                'id': 'google-cloud-speech-long', 'text': full_text,
                'confidence': response.results[0].alternatives[0].confidence if response.results else 0.0,
                'audio_duration': int(duration * 1000), 'utterances': utterances, 'words': words_info
            }
            print("✅ Long audio transcription SUCCESS!")
            return result_payload

        except Exception as e:
            print(f"❌ Google Cloud Speech (Long Audio) error: {str(e)}")
            import traceback
            traceback.print_exc()
            raise