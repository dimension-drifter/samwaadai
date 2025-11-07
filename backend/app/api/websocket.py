from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.call import Call
from app.services.stt_service import STTService
from app.services.ai_service import AIService
from app.services.crm_service import CRMService
from datetime import datetime
import json
import os
import wave
import tempfile
import struct
import array
import shutil

router = APIRouter()

class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, call_id: str, websocket: WebSocket):
        """Connect a new WebSocket client"""
        await websocket.accept()
        self.active_connections[call_id] = websocket
        print(f"✅ WebSocket connected for call: {call_id}")
    
    def disconnect(self, call_id: str):
        """Disconnect a WebSocket client"""
        if call_id in self.active_connections:
            del self.active_connections[call_id]
            print(f"❌ WebSocket disconnected for call: {call_id}")
    
    async def send_message(self, call_id: str, message: dict):
        """Send message to specific call"""
        if call_id in self.active_connections:
            websocket = self.active_connections[call_id]
            await websocket.send_json(message)

manager = ConnectionManager()

def resample_audio(audio_bytes: bytes, from_rate: int, to_rate: int) -> bytes:
    """Resample audio from one rate to another using linear interpolation"""
    if from_rate == to_rate:
        return audio_bytes
    
    print(f"🔄 Resampling from {from_rate}Hz to {to_rate}Hz...")
    
    # Convert bytes to samples
    samples = struct.unpack(f'{len(audio_bytes)//2}h', audio_bytes)
    
    # Calculate resampling ratio
    ratio = to_rate / from_rate
    new_length = int(len(samples) * ratio)
    
    # Simple linear interpolation resampling
    resampled = []
    for i in range(new_length):
        # Map new index to old index
        old_index = i / ratio
        index_floor = int(old_index)
        index_ceil = min(index_floor + 1, len(samples) - 1)
        
        # Linear interpolation
        fraction = old_index - index_floor
        value = samples[index_floor] * (1 - fraction) + samples[index_ceil] * fraction
        resampled.append(int(value))
    
    # Convert back to bytes
    return struct.pack(f'{len(resampled)}h', *resampled)

def save_audio_to_wav(audio_bytes: bytes, path: str, sample_rate: int = 48000):
    """
    Saves raw PCM audio bytes to a WAV file at 16kHz for Google Cloud Speech.
    """
    print(f"💾 Processing {len(audio_bytes)} bytes of audio data...")
    
    if len(audio_bytes) == 0:
        raise ValueError("No audio data to save")
    
    # Ensure even number of bytes for 16-bit audio
    if len(audio_bytes) % 2 != 0:
        print(f"⚠️ Trimming 1 byte to align audio buffer")
        audio_bytes = audio_bytes[:-1]
    
    # Check original audio level
    samples = struct.unpack(f'{len(audio_bytes)//2}h', audio_bytes)
    max_amplitude = max(abs(s) for s in samples)
    rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
    
    print(f"🔊 Original audio analysis:")
    print(f"   - Max amplitude: {max_amplitude} (out of 32768)")
    print(f"   - RMS level: {rms:.0f}")
    print(f"   - Sample rate: {sample_rate}Hz")
    print(f"   - Duration: {len(samples)/sample_rate:.2f}s")
    
    if max_amplitude < 100:
        print(f"⚠️ WARNING: Audio is very quiet! Max amplitude is only {max_amplitude}")
        print(f"   Amplifying audio by 10x...")
        # Amplify quiet audio
        samples = [min(32767, max(-32768, s * 10)) for s in samples]
        audio_bytes = struct.pack(f'{len(samples)}h', *samples)
        max_amplitude = max(abs(s) for s in samples)
        print(f"   New max amplitude: {max_amplitude}")
    
    # Resample to 16kHz if needed (Google Cloud Speech works best with 16kHz)
    if sample_rate != 16000:
        audio_bytes = resample_audio(audio_bytes, sample_rate, 16000)
        sample_rate = 16000
    
    try:
        # Save as 16kHz WAV
        with wave.open(path, 'wb') as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(16000)  # 16kHz for Google Cloud Speech
            wf.writeframes(audio_bytes)
        
        file_size = os.path.getsize(path)
        duration = len(audio_bytes) / (2 * 16000)
        
        print(f"✅ Audio saved successfully:")
        print(f"   - File: {path}")
        print(f"   - Size: {file_size} bytes")
        print(f"   - Duration: {duration:.2f} seconds")
        print(f"   - Format: 16kHz, 16-bit, mono")
        
        if duration < 1.0:
            print(f"⚠️ WARNING: Audio is very short ({duration:.2f}s)")
        
        return duration
        
    except Exception as e:
        print(f"❌ Error saving audio: {str(e)}")
        raise

@router.websocket("/call/{call_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    call_id: str,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for recording a call and processing it upon completion.
    """
    await manager.connect(call_id, websocket)
    
    # Initialize services
    stt_service = STTService()
    ai_service = AIService()
    crm_service = CRMService()
    
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        call = Call(
            id=int(call_id),
            user_id=1,
            platform="web",
            start_time=datetime.utcnow(),
            status="in_progress"
        )
        db.add(call)
        db.commit()
    
    audio_buffer = []
    temp_audio_path = None
    debug_audio_path = None
    sample_rate = 48000  # Default browser sample rate

    try:
        await websocket.send_json({
            "type": "connected",
            "call_id": call_id,
            "message": "Connection established. Ready to receive audio."
        })
        
        while True:
            data = await websocket.receive()
            
            if "text" in data:
                message = json.loads(data["text"])
                message_type = message.get("type")
                
                print(f"📩 Received message: {message_type}")
                
                # Get audio config from frontend
                if message_type == "audio_config":
                    sample_rate = message.get("sampleRate", 48000)
                    print(f"🎛️ Audio config: {sample_rate}Hz")
                    continue
                
                if message_type == "stop_recording":
                    await websocket.send_json({
                        "type": "processing_started",
                        "message": "Processing your recording with Google Cloud Speech..."
                    })
                    
                    # 1. Validate and save audio
                    if not audio_buffer:
                        raise ValueError("No audio data received. Please ensure microphone permissions are granted.")
                    
                    print(f"📊 Total audio chunks received: {len(audio_buffer)}")
                    combined_audio = b"".join(audio_buffer)
                    print(f"📊 Combined audio size: {len(combined_audio)} bytes")
                    
                    if len(combined_audio) < 4000:
                        raise ValueError(f"Audio recording too short. Please speak for at least 2-3 seconds.")
                    
                    fd, temp_audio_path = tempfile.mkstemp(suffix=".wav")
                    os.close(fd)
                    
                    duration = save_audio_to_wav(combined_audio, temp_audio_path, sample_rate=sample_rate)
                    
                    # Save a debug copy that won't be deleted
                    debug_audio_path = f"debug_recording_{call_id}.wav"
                    shutil.copy2(temp_audio_path, debug_audio_path)
                    print(f"🐛 Debug audio saved to: {debug_audio_path}")
                    print(f"   You can test this file with: python test_speech_simple_no_mic.py")

                    # 2. Transcribe the audio file with Google Cloud Speech
                    print("🎯 Starting Google Cloud Speech transcription...")
                    transcript_data = await stt_service.transcribe_audio_file(temp_audio_path)
                    
                    # 3. Generate insights from the transcript
                    if transcript_data.get('text') and len(transcript_data.get('text', '')) > 5:
                        print("🧠 Generating insights with Gemini AI...")
                        insights = await ai_service.extract_meeting_insights(transcript_data)
                    else:
                        print("⚠️ No meaningful transcript content")
                        error_msg = f'No speech detected. Debug file saved as: {debug_audio_path}\n'
                        error_msg += 'To test manually, run: python test_speech_simple_no_mic.py and rename the debug file to test_audio.wav'
                        
                        insights = {
                            'summary': error_msg,
                            'action_items': [],
                            'key_decisions': [],
                            'sentiment': 'NEUTRAL'
                        }
                    
                    # 4. Update call record in DB
                    call.end_time = datetime.utcnow()
                    call.duration_seconds = int((call.end_time - call.start_time).total_seconds())
                    call.full_transcript_text = transcript_data.get('text', '')
                    call.transcript = transcript_data
                    call.summary = insights.get('summary')
                    call.sentiment = insights.get('sentiment')
                    call.action_items = insights.get('action_items', [])
                    call.key_decisions = insights.get('key_decisions', [])
                    call.status = "completed"
                    db.commit()
                    
                    # 5. Log to CRM
                    await crm_service.log_interaction({
                        'contact_email': 'participant@example.com',
                        'contact_name': 'Participant',
                        'type': 'call',
                        'duration_seconds': call.duration_seconds,
                        'summary': insights.get('summary'),
                        'sentiment': insights.get('sentiment'),
                        'action_items': insights.get('action_items', [])
                    })
                    
                    # 6. Send final results to client
                    await websocket.send_json({
                        "type": "call_completed",
                        "insights": insights,
                        "transcript": transcript_data,
                        "call_id": call_id
                    })
                    print(f"✅ Call {call_id} completed successfully")
                    break
            
            elif "bytes" in data:
                audio_chunk = data["bytes"]
                if len(audio_chunk) > 1:
                    audio_buffer.append(audio_chunk)
    
    except WebSocketDisconnect:
        print("🔌 Client disconnected.")
    
    except Exception as e:
        print(f"❌ Error in WebSocket: {str(e)}")
        import traceback
        traceback.print_exc()
        
        call.status = "failed"
        call.end_time = datetime.utcnow()
        db.commit()
        
        try:
            await websocket.send_json({
                "type": "error", 
                "message": f"Processing failed: {str(e)}"
            })
        except:
            pass

    finally:
        manager.disconnect(call_id)
        crm_service.close()
        
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
            print(f"🗑️ Deleted temporary audio file: {temp_audio_path}")
        
        # Keep debug file for manual testing
        if debug_audio_path and os.path.exists(debug_audio_path):
            print(f"🐛 Debug file kept at: {debug_audio_path}")
        
        if call.status == "in_progress":
            call.status = "interrupted"
            call.end_time = datetime.utcnow()
            db.commit()