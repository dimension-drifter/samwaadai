from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.call import Call
from datetime import datetime
import json
import asyncio

router = APIRouter()

# Store active WebSocket connections
active_connections: dict = {}

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
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connections"""
        for websocket in self.active_connections.values():
            await websocket.send_json(message)

manager = ConnectionManager()

@router.websocket("/call/{call_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    call_id: str,
    db: Session = Depends(get_db)
):
    """
    Main WebSocket endpoint for real-time call processing
    
    Flow:
    1. Client connects and sends audio chunks
    2. Server transcribes audio in real-time
    3. Server sends back transcripts and insights
    4. Server sends action notifications
    """
    
    await manager.connect(call_id, websocket)
    
    # Create or get call record
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        # Create new call
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
        # Send initial connection success message
        await websocket.send_json({
            "type": "connected",
            "call_id": call_id,
            "message": "WebSocket connection established"
        })
        
        transcript_buffer = []
        
        while True:
            # Receive message from client
            data = await websocket.receive()
            
            # Handle different message types
            if "text" in data:
                # Text message (commands/control)
                message = json.loads(data["text"])
                message_type = message.get("type")
                
                if message_type == "start_recording":
                    await websocket.send_json({
                        "type": "recording_started",
                        "message": "Recording started"
                    })
                
                elif message_type == "stop_recording":
                    # Update call end time
                    call.end_time = datetime.utcnow()
                    call.duration_seconds = int(
                        (call.end_time - call.start_time).total_seconds()
                    )
                    call.status = "completed"
                    db.commit()
                    
                    await websocket.send_json({
                        "type": "recording_stopped",
                        "message": "Recording stopped"
                    })
                
                elif message_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            elif "bytes" in data:
                # Audio data received
                audio_data = data["bytes"]
                
                # TODO: Process audio with STT service
                # For now, send mock transcript
                mock_transcript = {
                    "text": "Sample transcription text",
                    "start": 0.0,
                    "end": 2.0,
                    "confidence": 0.95
                }
                
                await websocket.send_json({
                    "type": "transcript",
                    "data": mock_transcript
                })
                
                transcript_buffer.append(mock_transcript)
                
                # Every 10 segments, send insights
                if len(transcript_buffer) >= 10:
                    await websocket.send_json({
                        "type": "insights",
                        "data": {
                            "summary": "Sample meeting summary",
                            "action_items": [],
                            "sentiment": "neutral"
                        }
                    })
                    transcript_buffer = []
    
    except WebSocketDisconnect:
        manager.disconnect(call_id)
        print(f"Client disconnected from call: {call_id}")
        
        # Update call status
        if call.status == "in_progress":
            call.end_time = datetime.utcnow()
            call.duration_seconds = int(
                (call.end_time - call.start_time).total_seconds()
            )
            call.status = "completed"
            db.commit()
    
    except Exception as e:
        print(f"Error in WebSocket: {str(e)}")
        manager.disconnect(call_id)
        call.status = "failed"
        db.commit()
        await websocket.close()

@router.websocket("/test")
async def test_websocket(websocket: WebSocket):
    """Simple test WebSocket endpoint"""
    await websocket.accept()
    
    try:
        await websocket.send_json({
            "message": "WebSocket test connection successful",
            "status": "connected"
        })
        
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({
                "echo": data,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    except WebSocketDisconnect:
        print("Test WebSocket disconnected")