from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate, TaskApproval
from datetime import datetime

router = APIRouter()

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new automated task
    
    This is called by the AI system when it identifies an action to take
    """
    
    # TODO: Get user_id from authentication
    user_id = 1  # Temporary hardcoded
    
    new_task = Task(
        call_id=task_data.call_id,
        user_id=user_id,
        task_type=task_data.task_type,
        title=task_data.title,
        description=task_data.description,
        assigned_to=task_data.assigned_to,
        deadline=task_data.deadline,
        priority=task_data.priority,
        requires_approval=task_data.requires_approval,
        task_metadata=task_data.task_metadata,  # CHANGED: metadata -> task_metadata
        status="pending"
    )
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    return new_task

@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    status: str = None,
    task_type: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all tasks with optional filtering
    
    Parameters:
    - status: Filter by status (pending, approved, executed, etc.)
    - task_type: Filter by type (email, calendar, crm, etc.)
    """
    
    # TODO: Filter by authenticated user
    user_id = 1  # Temporary hardcoded
    
    query = db.query(Task).filter(Task.user_id == user_id)
    
    if status:
        query = query.filter(Task.status == status)
    
    if task_type:
        query = query.filter(Task.task_type == task_type)
    
    tasks = query.order_by(
        Task.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return tasks

@router.get("/pending", response_model=List[TaskResponse])
async def get_pending_tasks(
    db: Session = Depends(get_db)
):
    """
    Get all tasks that require user approval
    """
    
    user_id = 1  # Temporary hardcoded
    
    tasks = db.query(Task).filter(
        Task.user_id == user_id,
        Task.status == "pending",
        Task.requires_approval == True
    ).order_by(Task.created_at.desc()).all()
    
    return tasks

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific task by ID
    """
    
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found"
        )
    
    return task

@router.post("/{task_id}/approve")
async def approve_task(
    task_id: int,
    approval: TaskApproval,
    db: Session = Depends(get_db)
):
    """
    Approve or reject a task
    
    If approved, the task will be executed by the automation system
    """
    
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found"
        )
    
    if approval.approved:
        task.status = "approved"
        task.approved_at = datetime.utcnow()
        
        # TODO: Trigger task execution (Celery task)
        # execute_task.delay(task_id)
    else:
        task.status = "cancelled"
        if approval.reason:
            task.error_message = f"Rejected: {approval.reason}"
    
    db.commit()
    db.refresh(task)
    
    return {
        "task_id": task.id,
        "status": task.status,
        "message": "Task approved and queued for execution" if approval.approved else "Task rejected"
    }

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db)
):
    """
    Update task status (usually called by automation system)
    """
    
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found"
        )
    
    if task_update.status:
        task.status = task_update.status
    
    if task_update.executed_at:
        task.executed_at = task_update.executed_at
    
    if task_update.error_message:
        task.error_message = task_update.error_message
        task.retry_count += 1
    
    db.commit()
    db.refresh(task)
    
    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a task
    """
    
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found"
        )
    
    db.delete(task)
    db.commit()
    
    return None