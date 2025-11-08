from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.call import Call
from app.models.user import User
from app.schemas.call import CallCreate, CallResponse, CallUpdate
from datetime import datetime
from app.services.ai_service import AIService
from app.api.auth import get_current_user  # ADD THIS LINE

router = APIRouter()

@router.post("/", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
async def create_call(
    call_data: CallCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new call record
    
    This endpoint is called when a user starts a new call/meeting
    """
    
    # TODO: Get user_id from authentication
    user_id = 1  # Temporary hardcoded
    
    new_call = Call(
        user_id=user_id,
        platform=call_data.platform,
        meeting_url=call_data.meeting_url,
        start_time=datetime.utcnow(),
        status="in_progress"
    )
    
    db.add(new_call)
    db.commit()
    db.refresh(new_call)
    
    return new_call

@router.get("/", response_model=List[CallResponse])
async def get_calls(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all calls for the current user
    
    Parameters:
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    """
    
    # TODO: Filter by authenticated user
    user_id = 1  # Temporary hardcoded
    
    calls = db.query(Call).filter(
        Call.user_id == user_id
    ).order_by(
        Call.start_time.desc()
    ).offset(skip).limit(limit).all()
    
    return calls

@router.get("/{call_id}", response_model=CallResponse)
async def get_call(
    call_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific call by ID
    """
    
    call = db.query(Call).filter(Call.id == call_id).first()
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call with ID {call_id} not found"
        )
    
    return call

@router.put("/{call_id}", response_model=CallResponse)
async def update_call(
    call_id: int,
    call_update: CallUpdate,
    db: Session = Depends(get_db)
):
    """
    Update call details (transcripts, summary, etc.)
    """
    
    call = db.query(Call).filter(Call.id == call_id).first()
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call with ID {call_id} not found"
        )
    
    # Update fields if provided
    if call_update.end_time:
        call.end_time = call_update.end_time
        call.duration_seconds = int(
            (call.end_time - call.start_time).total_seconds()
        )
    
    if call_update.transcript:
        call.transcript = call_update.transcript
    
    if call_update.summary:
        call.summary = call_update.summary
    
    if call_update.sentiment:
        call.sentiment = call_update.sentiment
    
    if call_update.action_items:
        call.action_items = call_update.action_items
    
    db.commit()
    db.refresh(call)
    
    return call

@router.delete("/{call_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_call(
    call_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a call record
    """
    
    call = db.query(Call).filter(Call.id == call_id).first()
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call with ID {call_id} not found"
        )
    
    db.delete(call)
    db.commit()
    
    return None

@router.get("/{call_id}/transcript")
async def get_call_transcript(
    call_id: int,
    db: Session = Depends(get_db)
):
    """
    Get full transcript for a call
    """
    
    call = db.query(Call).filter(Call.id == call_id).first()
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call with ID {call_id} not found"
        )
    
    return {
        "call_id": call.id,
        "transcript": call.transcript,
        "full_text": call.full_transcript_text
    }

@router.get("/{call_id}/insights")
async def get_call_insights(
    call_id: int,
    db: Session = Depends(get_db)
):
    """
    Get AI-generated insights for a call
    """
    
    call = db.query(Call).filter(Call.id == call_id).first()
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call with ID {call_id} not found"
        )
    
    return {
        "call_id": call.id,
        "summary": call.summary,
        "sentiment": call.sentiment,
        "action_items": call.action_items,
        "key_decisions": call.key_decisions,
        "participants": call.participants,
        "topics": call.topics
    }

@router.get("/{call_id}/analyze")
async def analyze_call_endpoint(
    call_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze a call for AI-generated insights (summary, sentiment, action items, etc.)
    
    This endpoint triggers the AI analysis for a specific call. The analysis results
    are then updated in the call record.
    """
    
    call = db.query(Call).filter(Call.id == call_id).first()
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call with ID {call_id} not found"
        )
    
    # Perform analysis using the AI service
    summary, sentiment, action_items, key_decisions, topics = await AIService.analyze_call(call)
    
    # Update call record with analysis results
    call.summary = summary
    call.sentiment = sentiment
    call.action_items = action_items
    call.key_decisions = key_decisions
    call.topics = topics
    
    db.commit()
    db.refresh(call)
    
    return {
        "call_id": call.id,
        "summary": call.summary,
        "sentiment": call.sentiment,
        "action_items": call.action_items,
        "key_decisions": call.key_decisions,
        "topics": call.topics
    }