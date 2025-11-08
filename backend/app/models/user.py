from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    """User model for authentication and settings"""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Automation settings stored as JSON
    automation_settings = Column(JSON, default={
        "auto_send_emails": False,
        "auto_create_calendar": True,
        "auto_update_crm": True,
        "require_approval_for_external_emails": True
    })
    
    # Integration credentials (encrypted in production)
    integrations = Column(JSON, default={})
    
    # Relationships
    calls = relationship("Call", back_populates="user")
    tasks = relationship("Task", back_populates="user")
    sent_emails = relationship("SentEmail", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.email}>"