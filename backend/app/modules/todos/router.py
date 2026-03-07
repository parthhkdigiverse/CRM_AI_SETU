from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, UTC
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.users.models import User
from app.modules.todos.models import Todo
from app.modules.todos.schemas import TodoCreate, TodoRead, TodoUpdate

router = APIRouter()

@router.post("/", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
def create_todo(
    todo_in: TodoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    todo = Todo(**todo_in.model_dump(), user_id=current_user.id)
    db.add(todo)
    db.commit()
    db.refresh(todo)

    # --- Synchronization: Create Meeting if client_id is present and NOT already a meeting task ---
    if todo.client_id and not (todo.related_entity and todo.related_entity.startswith("MEETING:")):
        from app.modules.meetings.models import MeetingSummary, MeetingStatus, MeetingType
        meeting = MeetingSummary(
            title=todo.title,
            content=todo.description or "",
            date=todo.due_date or datetime.now(UTC).replace(tzinfo=None),
            status=MeetingStatus.SCHEDULED,
            meeting_type=MeetingType.IN_PERSON,
            client_id=todo.client_id,
            todo_id=todo.id
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
    # -----------------------------------------------------------

    return todo

from app.modules.todos.models import TodoStatus

@router.get("/", response_model=List[TodoRead])
def read_todos(
    skip: int = 0,
    limit: int = 100,
    status: Optional[TodoStatus] = None,
    assigned_to: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    query = db.query(Todo)
    
    from app.modules.users.models import UserRole
    is_admin = current_user.role == UserRole.ADMIN
    
    if not is_admin:
        query = query.filter(Todo.user_id == current_user.id)
    
    if status:
        query = query.filter(Todo.status == status)
        
    if assigned_to:
        query = query.filter(Todo.assigned_to.ilike(f"%{assigned_to}%"))
        
    return query.order_by(Todo.created_at.desc()).offset(skip).limit(limit).all()

@router.patch("/{todo_id}", response_model=TodoRead)
def update_todo(
    todo_id: int,
    todo_in: TodoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.user_id == current_user.id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
        
    update_data = todo_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(todo, field, value)
        
    db.commit()
    db.refresh(todo)

    # --- Synchronization: Update linked Meeting ---
    from app.modules.meetings.models import MeetingSummary
    meeting = db.query(MeetingSummary).filter(MeetingSummary.todo_id == todo.id).first()
    if meeting:
        if "title" in update_data:
            meeting.title = todo.title
        if "description" in update_data:
            meeting.content = todo.description
        if "due_date" in update_data:
            meeting.date = todo.due_date
        if "status" in update_data:
            from app.modules.meetings.models import MeetingStatus
            if todo.status == TodoStatus.COMPLETED:
                meeting.status = MeetingStatus.COMPLETED
        db.commit()
    # ----------------------------------------------

    return todo

@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.user_id == current_user.id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
        
    # --- Synchronization: Delete linked Meeting ---
    from app.modules.meetings.models import MeetingSummary
    meeting = db.query(MeetingSummary).filter(MeetingSummary.todo_id == todo.id).first()
    if meeting:
        db.delete(meeting)
    # ----------------------------------------------

    db.delete(todo)
    db.commit()
    from fastapi import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)
