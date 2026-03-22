from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from datetime import datetime, timezone
import re
from beanie import PydanticObjectId

from app.core.dependencies import get_current_user
from app.modules.users.models import User
from app.modules.todos.models import Todo, TodoStatus
from app.modules.todos.schemas import TodoCreate, TodoRead, TodoUpdate
from app.modules.meetings.models import MeetingSummary
from app.core.enums import GlobalTaskStatus
from app.modules.salary.models import AppSetting

router = APIRouter()

def _is_admin(user: User) -> bool:
    role_name = (user.role.value if hasattr(user.role, "value") else str(user.role)).upper()
    return role_name == "ADMIN"

async def _resolve_target_user(assigned_to: Optional[str]) -> Optional[User]:
    if not assigned_to:
        return None
    normalized = assigned_to.strip().lower()
    if not normalized:
        return None
    return await User.find_one(
        User.is_deleted != True,
        User.is_active == True,
        {"$or": [
            {"email": {"$regex": f"^{re.escape(normalized)}$", "$options": "i"}},
            {"name": {"$regex": f"^{re.escape(normalized)}$", "$options": "i"}}
        ]}
    )

@router.post("/", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
async def create_todo(
    todo_in: TodoCreate,
    current_user: User = Depends(get_current_user)
) -> Any:
    owner = current_user
    payload = todo_in.model_dump()

    if _is_admin(current_user) and payload.get("assigned_to"):
        target = await _resolve_target_user(payload.get("assigned_to"))
        if not target:
            raise HTTPException(status_code=404, detail="Assigned user not found")
        owner = target
        payload["assigned_to"] = target.name or target.email
    else:
        payload["assigned_to"] = current_user.name or current_user.email

    # SQL na badle MongoDB logic
    todo = Todo(**payload, user_id=str(owner.id))
    await todo.insert()

    if todo.client_id and not (todo.related_entity and todo.related_entity.startswith("MEETING:")):
        meeting = MeetingSummary(
            title=todo.title,
            content=todo.description or "",
            date=todo.due_date or datetime.now(timezone.utc),
            status=GlobalTaskStatus.OPEN,
            client_id=str(todo.client_id),
            todo_id=str(todo.id)
        )
        await meeting.insert()

    return todo

@router.get("/", response_model=List[TodoRead])
async def read_todos(
    skip: int = 0,
    limit: int = 100,
    status: Optional[TodoStatus] = None,
    assigned_to: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> Any:
    query_filter = {"is_deleted": {"$ne": True}}
    
    if not _is_admin(current_user):
        query_filter["user_id"] = str(current_user.id)

    if status:
        query_filter["status"] = status
    if assigned_to:
        query_filter["assigned_to"] = assigned_to

    return await Todo.find(query_filter).sort(-Todo.created_at).skip(skip).limit(limit).to_list()

@router.patch("/{todo_id}", response_model=TodoRead)
async def update_todo(
    todo_id: PydanticObjectId,
    todo_in: TodoUpdate,
    current_user: User = Depends(get_current_user)
) -> Any:
    todo = await Todo.get(todo_id)
    if not todo or todo.is_deleted:
        raise HTTPException(status_code=404, detail="Todo not found")
        
    if not _is_admin(current_user) and todo.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    update_data = todo_in.model_dump(exclude_unset=True)

    if _is_admin(current_user) and "assigned_to" in update_data and update_data.get("assigned_to"):
        target = await _resolve_target_user(update_data.get("assigned_to"))
        if target:
            todo.user_id = str(target.id)
            update_data["assigned_to"] = target.name or target.email
    elif not _is_admin(current_user):
        update_data.pop("assigned_to", None)

    await todo.set(update_data)

    # Sync with Meeting
    meeting = await MeetingSummary.find_one({"todo_id": str(todo.id), "is_deleted": {"$ne": True}})
    if meeting:
        meeting_update = {}
        if "title" in update_data: meeting_update["title"] = todo.title
        if "description" in update_data: meeting_update["content"] = todo.description
        if "due_date" in update_data: meeting_update["date"] = todo.due_date
        if todo.status == TodoStatus.COMPLETED:
            meeting_update["status"] = GlobalTaskStatus.RESOLVED
        
        if meeting_update:
            await meeting.set(meeting_update)

    return todo

@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(
    todo_id: PydanticObjectId,
    current_user: User = Depends(get_current_user)
) -> Response:
    todo = await Todo.get(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
        
    if not _is_admin(current_user) and todo.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
        
    policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
    is_hard = policy and policy.value == "HARD"

    meeting = await MeetingSummary.find_one({"todo_id": str(todo.id)})
    if meeting:
        if is_hard: await meeting.delete()
        else: await meeting.set({"is_deleted": True})

    if is_hard: await todo.delete()
    else: await todo.set({"is_deleted": True})
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)