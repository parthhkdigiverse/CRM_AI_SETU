# backend/app/modules/todos/router.py
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from datetime import datetime, UTC
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.users.models import User, UserRole
from app.modules.todos.models import Todo
from app.modules.todos.schemas import TodoCreate, TodoRead, TodoUpdate

router = APIRouter()


def _is_admin(user: User) -> bool:
    return bool(user and user.role == UserRole.ADMIN)


def _resolve_target_user(db: Session, assigned_to: Optional[str]) -> Optional[User]:
    if not assigned_to:
        return None

    normalized = assigned_to.strip().lower()
    if not normalized:
        return None

    return db.query(User).filter(
        User.is_deleted == False,
        User.is_active == True,
        or_(
            func.lower(User.email) == normalized,
            func.lower(User.name) == normalized,
        )
    ).first()

@router.post("/", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
def create_todo(
    todo_in: TodoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    owner = current_user
    payload = todo_in.model_dump()

    if _is_admin(current_user) and payload.get("assigned_to"):
        owner = _resolve_target_user(db, payload.get("assigned_to"))
        if not owner:
            raise HTTPException(status_code=404, detail="Assigned user not found")
        payload["assigned_to"] = owner.name or owner.email
    else:
        payload["assigned_to"] = current_user.name or current_user.email

    todo = Todo(**payload, user_id=owner.id)
    db.add(todo)
    db.commit()
    db.refresh(todo)

    # --- Synchronization: Create Meeting if client_id is present and NOT already a meeting task ---
    if todo.client_id and not (todo.related_entity and todo.related_entity.startswith("MEETING:")):
        from app.modules.meetings.models import MeetingSummary, MeetingType
        from app.core.enums import GlobalTaskStatus
        meeting = MeetingSummary(
            title=todo.title,
            content=todo.description or "",
            date=todo.due_date or datetime.now(UTC).replace(tzinfo=None),
            status=GlobalTaskStatus.OPEN,
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
    query = db.query(Todo).filter(Todo.is_deleted == False)

    if not _is_admin(current_user):
        query = query.filter(Todo.user_id == current_user.id)

    if status:
        query = query.filter(Todo.status == status)
    if assigned_to:
        query = query.filter(Todo.assigned_to == assigned_to)

    return query.order_by(Todo.created_at.desc()).offset(skip).limit(limit).all()

@router.patch("/{todo_id}", response_model=TodoRead)
def update_todo(
    todo_id: int,
    todo_in: TodoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    todo_query = db.query(Todo).filter(Todo.id == todo_id)
    if not _is_admin(current_user):
        todo_query = todo_query.filter(Todo.user_id == current_user.id)
    todo = todo_query.first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
        
    update_data = todo_in.model_dump(exclude_unset=True)

    if _is_admin(current_user) and "assigned_to" in update_data and update_data.get("assigned_to"):
        owner = _resolve_target_user(db, update_data.get("assigned_to"))
        if not owner:
            raise HTTPException(status_code=404, detail="Assigned user not found")
        todo.user_id = owner.id
        update_data["assigned_to"] = owner.name or owner.email
    elif not _is_admin(current_user):
        update_data.pop("assigned_to", None)

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
            from app.core.enums import GlobalTaskStatus
            if todo.status == TodoStatus.COMPLETED:
                meeting.status = GlobalTaskStatus.RESOLVED
        db.commit()
    # ----------------------------------------------

    return todo

@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    # Fetch todo regardless of is_deleted to allow re-deletion logic if needed, 
    # but mostly to check existence.
    todo_query = db.query(Todo).filter(Todo.id == todo_id)
    if not _is_admin(current_user):
        todo_query = todo_query.filter(Todo.user_id == current_user.id)
    todo = todo_query.first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
        
    from app.modules.salary.models import AppSetting
    policy = db.query(AppSetting).filter(AppSetting.key == "delete_policy").first()
    is_hard = policy and policy.value == "HARD"

    # --- Synchronization: Handle linked Meeting ---
    from app.modules.meetings.models import MeetingSummary
    meeting = db.query(MeetingSummary).filter(MeetingSummary.todo_id == todo.id).first()
    if meeting:
        if is_hard:
            db.delete(meeting)
        else:
            meeting.is_deleted = True
    # ----------------------------------------------

    if is_hard:
        db.delete(todo)
    else:
        todo.is_deleted = True
    db.commit()
    from fastapi import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)
