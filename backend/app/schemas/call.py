from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class CallBase(BaseModel):
    """Base call schema"""
    platform: str
    meeting_url: Optional[str] = None

class CallCreate(CallBase):
    """Schema for creating a call"""
    pass

class TranscriptSegment(BaseModel):
    """Single transcript segment"""
    text: str
    start: float
    end: float
    confidence: float
    speaker: Optional[str] = None

class CallUpdate(BaseModel):
    """Schema for updating a call"""
    end_time: Optional[datetime] = None
    transcript: Optional[List[Dict]] = None
    summary: Optional[str] = None
    sentiment: Optional[Dict] = None 
    action_items: Optional[List[Dict]] = None

class CallResponse(CallBase):
    """Schema for call response (UPDATED FOR FULL DETAILS)"""
    id: int
    user_id: int
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: int
    status: str
    
    # AI Analysis & Transcription Fields (ADDED)
    title: Optional[str] = None
    summary: Optional[str]
    sentiment: Optional[Dict] = None 
    action_items: List[Dict] = []
    key_decisions: List[str] = [] # ADDED
    questions_asked: List[str] = [] # ADDED
    chapters: List[Dict] = [] # ADDED
    full_transcript_text: Optional[str] = None # ADDED
    
    class Config:
        from_attributes = True