from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class SentEmail(Base):
    """Model to store a record of sent emails"""
    
    __tablename__ = "sent_emails"
    
    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    recipient = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=True)  # Store the HTML body
    sent_at = Column(DateTime, default=datetime.utcnow)
    sendgrid_message_id = Column(String, nullable=True)

    # Relationships
    call = relationship("Call", back_populates="sent_emails")
    user = relationship("User", back_populates="sent_emails")

    def __repr__(self):
        return f"<SentEmail {self.id} to {self.recipient}>"