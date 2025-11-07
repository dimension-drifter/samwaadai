"""
Calendar API endpoints
"""
from fastapi import APIRouter, HTTPException
from app.services.calendar_service import CalendarService
from typing import List, Dict, Optional
from pydantic import BaseModel

router = APIRouter()
calendar_service = CalendarService()

class EventResponse(BaseModel):
    """Calendar event response model"""
    id: str
    summary: str
    start: str
    end: str
    link: Optional[str] = None

@router.get("/events", response_model=List[EventResponse])
async def get_calendar_events(max_results: int = 50):
    """
    Get upcoming calendar events
    
    Args:
        max_results: Maximum number of events to return
        
    Returns:
        List of upcoming events
    """
    try:
        events = await calendar_service.get_upcoming_events(max_results=max_results)
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch calendar events: {str(e)}")

@router.delete("/events/{event_id}")
async def delete_calendar_event(event_id: str):
    """
    Delete a calendar event
    
    Args:
        event_id: Google Calendar event ID
        
    Returns:
        Success message
    """
    try:
        success = await calendar_service.delete_event(event_id)
        if success:
            return {"message": f"Event {event_id} deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete event")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete event: {str(e)}")

@router.get("/health")
async def calendar_health():
    """Check if calendar service is authenticated"""
    try:
        authenticated = calendar_service.authenticate()
        return {
            "authenticated": authenticated,
            "service": "Google Calendar"
        }
    except Exception as e:
        return {
            "authenticated": False,
            "error": str(e)
        }
