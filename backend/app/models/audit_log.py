from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, Text
from datetime import datetime
from app.database import Base

class AuditLog(Base):
    """Audit trail for all autonomous actions"""
    
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    task_id = Column(Integer, nullable=True)
    
    # Action details
    action = Column(String, nullable=False)  # email_sent, calendar_created, etc.
    action_type = Column(String, nullable=False)  # automated, manual, approved
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=True)
    details = Column(JSON, default={})
    error_message = Column(Text, nullable=True)
    
    # Context
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<AuditLog {self.id} - {self.action}>"