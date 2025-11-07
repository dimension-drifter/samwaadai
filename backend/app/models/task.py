from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Task(Base):
    """Automated task model"""
    
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Task details
    task_type = Column(String, nullable=False)  # email, calendar, crm, notification
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Assignment
    assigned_to = Column(String, nullable=True)
    deadline = Column(DateTime, nullable=True)
    priority = Column(String, default="medium")  # high, medium, low
    
    # Status
    status = Column(String, default="pending")  # pending, approved, executed, failed, cancelled
    requires_approval = Column(Boolean, default=True)
    
    # Execution details
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    
    # Additional data (email content, calendar event details, etc.)
    # CHANGED: metadata -> task_metadata to avoid reserved keyword
    task_metadata = Column(JSON, default={})
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Relationships
    call = relationship("Call", back_populates="tasks")
    user = relationship("User", back_populates="tasks")
    
    def __repr__(self):
        return f"<Task {self.id} - {self.task_type}>"