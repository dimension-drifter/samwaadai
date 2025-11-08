from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.call import Call
from app.services.stt_service import STTService
from app.services.ai_service import AIService
from app.services.crm_service import CRMService
from datetime import datetime
from app.services.calendar_service import CalendarService
import json
import os
import wave
import tempfile
import struct
import shutil
from datetime import datetime
import dateutil.parser
import pytz
from app.services.email_service import EmailService



router = APIRouter()

class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, call_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[call_id] = websocket
        print(f"✅ WebSocket connected for call: {call_id}")
    
    def disconnect(self, call_id: str):
        if call_id in self.active_connections:
            del self.active_connections[call_id]
            print(f"❌ WebSocket disconnected for call: {call_id}")
    
    async def send_message(self, call_id: str, message: dict):
        if call_id in self.active_connections:
            websocket = self.active_connections[call_id]
            await websocket.send_json(message)

manager = ConnectionManager()

def convert_float32_to_int16(float32_data: bytes) -> bytes:
    """Convert Float32 PCM to Int16 PCM"""
    # Unpack as float32
    float_samples = struct.unpack(f'{len(float32_data)//4}f', float32_data)
    # Convert to int16 range
    int16_samples = [int(max(-1.0, min(1.0, sample)) * 32767) for sample in float_samples]
    # Pack as int16
    return struct.pack(f'{len(int16_samples)}h', *int16_samples)

def save_audio_to_wav(audio_bytes: bytes, path: str, sample_rate: int = 48000, is_float32: bool = False):
    """
    Saves audio bytes to a WAV file at 16kHz for Google Cloud Speech.
    """
    print(f"💾 Processing {len(audio_bytes)} bytes of audio data...")
    print(f"   Format: {'Float32' if is_float32 else 'Int16'} @ {sample_rate}Hz")
    
    if len(audio_bytes) == 0:
        raise ValueError("No audio data to save")
    
    # Convert Float32 to Int16 if needed
    if is_float32:
        print("🔄 Converting Float32 to Int16...")
        if len(audio_bytes) % 4 != 0:
            audio_bytes = audio_bytes[:-(len(audio_bytes) % 4)]
        audio_bytes = convert_float32_to_int16(audio_bytes)
    else:
        # Ensure even number of bytes for 16-bit audio
        if len(audio_bytes) % 2 != 0:
            print(f"⚠️ Trimming 1 byte to align audio buffer")
            audio_bytes = audio_bytes[:-1]
    
    # Analyze audio
    samples = struct.unpack(f'{len(audio_bytes)//2}h', audio_bytes)
    max_amplitude = max(abs(s) for s in samples)
    rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
    
    print(f"🔊 Audio analysis:")
    print(f"   - Samples: {len(samples)}")
    print(f"   - Max amplitude: {max_amplitude} / 32768")
    print(f"   - RMS level: {rms:.0f}")
    print(f"   - Duration: {len(samples)/sample_rate:.2f}s")
    
    if max_amplitude < 10:
        raise ValueError(f"Audio is silent or corrupted (max amplitude: {max_amplitude}). Please check microphone.")
    
    # Amplify if too quiet
    if max_amplitude < 1000:
        print(f"⚠️ Audio very quiet, amplifying by 20x...")
        samples = [min(32767, max(-32768, s * 20)) for s in samples]
        audio_bytes = struct.pack(f'{len(samples)}h', *samples)
        max_amplitude = max(abs(s) for s in samples)
        print(f"   New max amplitude: {max_amplitude}")
    
    # Resample to 16kHz for Google Cloud Speech
    if sample_rate != 16000:
        print(f"🔄 Resampling from {sample_rate}Hz to 16000Hz...")
        ratio = 16000 / sample_rate
        new_length = int(len(samples) * ratio)
        resampled = []
        
        for i in range(new_length):
            old_index = i / ratio
            index_floor = int(old_index)
            index_ceil = min(index_floor + 1, len(samples) - 1)
            fraction = old_index - index_floor
            value = samples[index_floor] * (1 - fraction) + samples[index_ceil] * fraction
            resampled.append(int(value))
        
        audio_bytes = struct.pack(f'{len(resampled)}h', *resampled)
        sample_rate = 16000
    
    # Save WAV file
    with wave.open(path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(audio_bytes)
    
    file_size = os.path.getsize(path)
    duration = len(audio_bytes) / (2 * 16000)
    
    print(f"✅ Audio saved: {file_size} bytes, {duration:.2f}s, 16kHz mono")
    return duration

@router.websocket("/call/{call_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    call_id: str,
    db: Session = Depends(get_db)
):
    await manager.connect(call_id, websocket)
    
    stt_service = STTService()
    ai_service = AIService()
    crm_service = CRMService()
    calendar_service = CalendarService()
    email_service = EmailService()
    
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
    sample_rate = 48000
    is_float32 = False
    user_timezone = "UTC"

    try:
        await websocket.send_json({
            "type": "connected",
            "call_id": call_id,
            "message": "Ready to record. Please allow microphone access."
        })
        
        while True:
            data = await websocket.receive()
            
            if "text" in data:
                message = json.loads(data["text"])
                message_type = message.get("type")
                
                if message_type == "audio_config":
                    sample_rate = message.get("sampleRate", 48000)
                    is_float32 = message.get("isFloat32", False)
                    
                    # This is the new, robust logic:
                    new_timezone = message.get("timezone")
                    # Only update the timezone if it's currently the default ("UTC")
                    # and the new one is not empty.
                    if new_timezone and user_timezone == "UTC":
                        user_timezone = new_timezone
                        print(f"🌍 User timezone LOCKED to: {user_timezone}")
                    
                    print(f"🎛️ Audio config received: {sample_rate}Hz, {'Float32' if is_float32 else 'Int16'}")
                    continue

                if message_type == "start_recording":
                    await websocket.send_json({
                        "type": "recording_started",
                        "message": "Recording audio..."
                    })
                    continue

                if message_type == "stop_recording":
                    await websocket.send_json({
                        "type": "processing_started",
                        "message": "Processing recording..."
                    })
                    
                    if not audio_buffer:
                        raise ValueError("No audio data received. Check microphone permissions.")
                    
                    print(f"📊 Chunks: {len(audio_buffer)}, Total: {sum(len(c) for c in audio_buffer)} bytes")
                    combined_audio = b"".join(audio_buffer)
                    
                    fd, temp_audio_path = tempfile.mkstemp(suffix=".wav")
                    os.close(fd)
                    
                    try:
                        duration = save_audio_to_wav(combined_audio, temp_audio_path, sample_rate, is_float32)
                        
                        # Save debug copy
                        debug_audio_path = f"debug_recording_{call_id}.wav"
                        shutil.copy2(temp_audio_path, debug_audio_path)
                        print(f"🐛 Debug saved: {debug_audio_path}")
                        
                        # Transcribe
                        print("🎯 Transcribing...")
                        transcript_data = await stt_service.transcribe_audio_file(temp_audio_path)
                        
                        # if transcript_data.get('text') and len(transcript_data['text']) > 5:
                        #     print("🧠 Generating insights...")
                        #     insights = await ai_service.extract_meeting_insights(transcript_data)
                        # else:
                        #     insights = {
                        #         'summary': f'No speech detected. Debug file: {debug_audio_path}',
                        #         'action_items': [],
                        #         'key_decisions': [],
                        #         'sentiment': 'NEUTRAL'
                        #     }
                        
                        full_text = transcript_data.get('text', '')

                        # --- START OF NEW LOGIC ---

                        # 1. Generate general insights (as before)
                        print("🧠 Generating general insights...")
                        insights = await ai_service.extract_meeting_insights(transcript_data)

                        # 2. Extract specific actionable tasks
                        print("🤖 Looking for actionable tasks like scheduling...")
                        actionable_tasks = await ai_service.extract_actionable_tasks(full_text)

                        # 3. Loop through tasks and execute them
                        for task in actionable_tasks:
                            if task.get("type") == "CREATE_CALENDAR_EVENT":
                                print(f"📅 Found a calendar event task: {task.get('summary')}")
                                
                                if calendar_service.authenticate():
                                    try:
                                        # --- START OF MODIFICATION ---
                                        # 1. Parse the naive datetime string from the AI
                                        naive_start_time = dateutil.parser.isoparse(task.get("start_time"))
                                        
                                        # 2. Get the timezone object for the user's timezone
                                        local_tz = pytz.timezone(user_timezone)
                                        
                                        # 3. Localize the naive datetime, making it timezone-aware
                                        aware_start_time = local_tz.localize(naive_start_time)
                                        
                                        print(f"🌍 Correctly interpreted start time: {aware_start_time.isoformat()}")

                                        event_result = await calendar_service.create_event(
                                            summary=task.get("summary"),
                                            description=task.get("description", "Event scheduled by Samwaad AI."),
                                            start_time=aware_start_time, # 4. Use the new aware datetime object
                                            duration_minutes=int(task.get("duration_minutes", 30)),
                                            attendees=task.get("attendees", []),
                                            timezone=user_timezone
                                        )

                                        if event_result:
                                            print(f"✅ Successfully created calendar event: {event_result.get('link')}")
                                            # Notify the frontend that a task was completed!
                                            await websocket.send_json({
                                                "type": "task_executed",
                                                "task_type": "Calendar Event",
                                                "summary": f"Created event: {task.get('summary')}",
                                                "details": event_result
                                            })
                                        else:
                                            print("❌ Failed to create calendar event.")

                                    except Exception as cal_error:
                                        print(f"❌ Error executing calendar task: {cal_error}")
                                else:
                                    print("⚠️ Could not authenticate with Google Calendar. Skipping task.")
                        # Update database
                        call.end_time = datetime.utcnow()
                        call.duration_seconds = int((call.end_time - call.start_time).total_seconds())
                        call.full_transcript_text = transcript_data.get('text', '')
                        call.transcript = transcript_data # Storing the full STT result is good practice
                        
                        # Save the new structured data
                        call.title = insights.get('title')
                        call.summary = insights.get('summary')
                        call.sentiment = insights.get('sentiment')
                        call.action_items = insights.get('action_items', [])
                        call.key_decisions = insights.get('key_decisions', [])
                        call.attendees = insights.get('attendees', [])
                        call.questions_asked = insights.get('questions_asked', [])
                        call.chapters = insights.get('chapters', [])
                        
                        call.status = "completed"
                        db.commit()

                                                # In a real app, this would come from the call object or frontend.
                        recipient_email = "iambossdiscord01@gmail.com"
                        
                        if recipient_email:
                            print(f"🚀 Attempting to send analysis email to {recipient_email}...")
                            email_result = await email_service.send_post_meeting_analysis(
                                to_email=recipient_email,
                                insights=insights,
                                transcript_text=full_text
                            )
                            if email_result.get("success"):
                                print(f"✅ Analysis email sent successfully. Message ID: {email_result.get('message_id')}")
                            else:
                                print(f"❌ Failed to send analysis email. Error: {email_result.get('error')}")
                        else:
                            print("🤷 No recipient email found, skipping analysis email.")

                        
                        await crm_service.log_interaction({
                            'contact_email': 'participant@example.com',
                            'contact_name': 'Participant',
                            'type': 'call',
                            'duration_seconds': call.duration_seconds,
                            'summary': insights.get('summary'),
                            'sentiment': insights.get('sentiment'),
                            'action_items': insights.get('action_items', [])
                        })
                        
                        await websocket.send_json({
                            "type": "call_completed",
                            "insights": insights,
                            "transcript": transcript_data,
                            "call_id": call_id
                        })
                        print(f"✅ Call {call_id} processing complete. Notifying client.")
                        
                    except ValueError as ve:
                        # This handles errors like silent audio
                        print(f"❌ Value Error during processing: {ve}")
                        await websocket.send_json({"type": "error", "message": str(ve)})
                    
                    print("🏁 Breaking WebSocket loop.")
                    break
            
            elif "bytes" in data:
                audio_chunk = data["bytes"]
                if len(audio_chunk) > 0:
                    audio_buffer.append(audio_chunk)
    
    except WebSocketDisconnect:
        print("🔌 Disconnected")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        call.status = "failed"
        call.end_time = datetime.utcnow()
        db.commit()
        
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        manager.disconnect(call_id)
        crm_service.close()
        
        if temp_audio_path and os.path.exists(temp_audio_path):
            print(f"🧹 Deleting temporary file: {temp_audio_path}")
            os.remove(temp_audio_path)
        if debug_audio_path and os.path.exists(debug_audio_path):
             print(f"🧹 Deleting debug file: {debug_audio_path}")
             os.remove(debug_audio_path)