from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.call import Call
from app.services.stt_service import STTService
from app.services.ai_service import AIService
from app.services.email_service import EmailService
from app.services.calendar_service import CalendarService
from app.services.crm_service import CRMService
from datetime import datetime
import json
import asyncio

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

@router.websocket("/call/{call_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    call_id: str,
    db: Session = Depends(get_db)
):
    """
    Main WebSocket endpoint with full service integration
    """
    
    await manager.connect(call_id, websocket)
    
    # Initialize services
    stt_service = STTService()
    ai_service = AIService()
    email_service = EmailService()
    calendar_service = CalendarService()
    crm_service = CRMService()
    
    # Create or get call record
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        call = Call(
            id=int(call_id),
            user_id=1,  # TODO: Get from auth
            platform="unknown",
            start_time=datetime.utcnow(),
            status="in_progress"
        )
        db.add(call)
        db.commit()
    
    try:
        # Send initial connection success
        await websocket.send_json({
            "type": "connected",
            "call_id": call_id,
            "message": "WebSocket connection established"
        })
        
        # Start STT service
        await stt_service.start_transcription()
        
        transcript_buffer = []
        full_transcript = []
        
        while True:
            # Receive message from client
            data = await websocket.receive()
            
            if "text" in data:
                # Handle text commands
                message = json.loads(data["text"])
                message_type = message.get("type")
                
                if message_type == "stop_recording":
                    # Stop recording and process final transcript
                    await stt_service.close()
                    
                    # Generate final insights
                    full_text = " ".join([t['text'] for t in full_transcript])
                    insights = await ai_service.extract_meeting_insights(full_text)
                    
                    # Update call record
                    call.end_time = datetime.utcnow()
                    call.duration_seconds = int((call.end_time - call.start_time).total_seconds())
                    call.full_transcript_text = full_text
                    call.transcript = full_transcript
                    call.summary = insights.get('summary')
                    call.sentiment = insights.get('sentiment')
                    call.action_items = insights.get('action_items', [])
                    call.key_decisions = insights.get('key_decisions', [])
                    call.status = "completed"
                    db.commit()
                    
                    # Log to CRM
                    await crm_service.log_interaction({
                        'contact_email': 'participant@example.com',  # TODO: Extract from insights
                        'contact_name': 'Participant',
                        'type': 'call',
                        'duration_seconds': call.duration_seconds,
                        'summary': insights.get('summary'),
                        'sentiment': insights.get('sentiment'),
                        'action_items': insights.get('action_items', [])
                    })
                    
                    await websocket.send_json({
                        "type": "call_completed",
                        "insights": insights
                    })
                    break
            
            elif "bytes" in data:
                # Process audio data
                audio_data = data["bytes"]
                
                # Stream to STT
                await stt_service.stream_audio(audio_data)
                
                # Check for new transcripts
                transcript = await stt_service.get_transcript()
                if transcript:
                    # Send to frontend
                    await websocket.send_json({
                        "type": "transcript",
                        "data": transcript
                    })
                    
                    transcript_buffer.append(transcript)
                    full_transcript.append(transcript)
                    
                    # Every 10 segments, analyze
                    if len(transcript_buffer) >= 10:
                        partial_text = " ".join([t['text'] for t in transcript_buffer])
                        insights = await ai_service.extract_meeting_insights(partial_text)
                        
                        await websocket.send_json({
                            "type": "partial_insights",
                            "data": insights
                        })
                        
                        transcript_buffer = transcript_buffer[-5:]  # Keep context
    
    except WebSocketDisconnect:
        manager.disconnect(call_id)
        await stt_service.close()
        crm_service.close()
        
        if call.status == "in_progress":
            call.end_time = datetime.utcnow()
            call.duration_seconds = int((call.end_time - call.start_time).total_seconds())
            call.status = "completed"
            db.commit()
    
    except Exception as e:
        print(f"❌ Error in WebSocket: {str(e)}")
        manager.disconnect(call_id)
        await stt_service.close()
        crm_service.close()
        call.status = "failed"
        db.commit()