from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

class TaskBase(BaseModel):
    """Base task schema"""
    task_type: str
    title: str
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: str = "medium"

class TaskCreate(TaskBase):
    """Schema for creating a task"""
    call_id: int
    requires_approval: bool = True
    task_metadata: Dict = {}  # CHANGED: metadata -> task_metadata

class TaskUpdate(BaseModel):
    """Schema for updating a task"""
    status: Optional[str] = None
    executed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class TaskApproval(BaseModel):
    """Schema for approving/rejecting a task"""
    approved: bool
    reason: Optional[str] = None

class TaskResponse(TaskBase):
    """Schema for task response"""
    id: int
    call_id: int
    user_id: int
    status: str
    requires_approval: bool
    created_at: datetime
    executed_at: Optional[datetime]
    task_metadata: Dict  # CHANGED: metadata -> task_metadata
    
    class Config:
        from_attributes = True