from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Call(Base):
    """Call/Meeting model"""
    
    __tablename__ = "calls"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Call metadata
    platform = Column(String)  # zoom, meet, teams, phone
    meeting_url = Column(String, nullable=True)
    
    # Timing
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, default=0)
    
    # Transcription
    transcript = Column(JSON, default=[])  # List of transcript segments
    full_transcript_text = Column(Text, nullable=True)
    
    # AI Analysis
    summary = Column(Text, nullable=True)
    sentiment = Column(JSON, nullable=True)  # positive, negative, neutral
    confidence_score = Column(Float, nullable=True)
    
    # Extracted data
    action_items = Column(JSON, default=[])
    key_decisions = Column(JSON, default=[])
    topics = Column(JSON, default=[])
    attendees = Column(JSON, default=[])
    # Status
    status = Column(String, default="in_progress")  # in_progress, completed, failed
    
    # Relationships
    user = relationship("User", back_populates="calls")
    tasks = relationship("Task", back_populates="call")
    
    def __repr__(self):
        return f"<Call {self.id} - {self.platform}>"