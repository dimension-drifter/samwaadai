from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.sent_email import SentEmail
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# Pydantic schema for the API response
class SentEmailResponse(BaseModel):
    id: int
    recipient: str
    subject: str
    body: str
    sent_at: datetime
    call_id: int | None

    class Config:
        from_attributes = True

@router.get("/", response_model=List[SentEmailResponse])
async def get_sent_emails(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all sent emails for the current user, most recent first.
    """
    # TODO: In a real app, filter by authenticated user ID
    user_id = 1  # Using hardcoded user_id as in the rest of the project
    
    emails = db.query(SentEmail).filter(
        SentEmail.user_id == user_id
    ).order_by(
        SentEmail.sent_at.desc()
    ).offset(skip).limit(limit).all()
    
    return emails