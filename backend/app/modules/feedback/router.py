from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Response
from app.core.dependencies import RoleChecker, get_current_user
from app.modules.users.models import User, UserRole
from app.modules.clients.models import Client
from app.modules.feedback.models import Feedback, UserFeedback
from app.modules.feedback.schemas import FeedbackCreate, FeedbackRead, UserFeedbackCreate, UserFeedbackRead

router = APIRouter()
global_router = APIRouter()

staff_checker = RoleChecker([UserRole.ADMIN, UserRole.SALES, UserRole.TELESALES, UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES])
admin_checker = RoleChecker([UserRole.ADMIN])

@router.post("/{client_id}/feedback", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
async def create_feedback(client_id: str, feedback_in: FeedbackCreate) -> Any:
    db_client = await Client.find_one(Client.id == client_id)
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    feedback_in.client_id = client_id
    feedback = Feedback(**feedback_in.model_dump())
    await feedback.insert()
    return feedback

@global_router.post("/public/submit", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
async def create_public_feedback(feedback_in: FeedbackCreate) -> Any:
    feedback = Feedback(**feedback_in.model_dump())
    await feedback.insert()
    return feedback

@global_router.get("/all", response_model=List[FeedbackRead])
async def read_all_feedback(current_user: User = Depends(staff_checker)) -> Any:
    feedbacks = await Feedback.find(Feedback.is_deleted != True).sort(-Feedback.created_at).to_list()
    # Enrich with agent name and role from referral_code
    ref_codes = list({fb.referral_code for fb in feedbacks if fb.referral_code})
    agent_map = {}
    if ref_codes:
        users = await User.find(User.referral_code.is_in(ref_codes)).to_list()
        for u in users:
            if u.referral_code:
                role_str = u.role.value if hasattr(u.role, 'value') else str(u.role)
                agent_map[u.referral_code] = {
                    "name": u.name or u.email.split('@')[0],
                    "role": role_str.replace("_", " ").title()
                }
    result = []
    for fb in feedbacks:
        data = fb.model_dump(by_alias=True)
        data["id"] = fb.id
        agent_info = agent_map.get(fb.referral_code, {})
        if not data.get("agent_name") and agent_info.get("name"):
            data["agent_name"] = agent_info["name"]
        if agent_info.get("role"):
            data["agent_role"] = agent_info["role"]
        result.append(data)
    return result

@router.get("/{client_id}/feedback", response_model=List[FeedbackRead])
async def read_client_feedback(client_id: str, current_user: User = Depends(staff_checker)) -> Any:
    from app.modules.salary.models import AppSetting
    client = await Client.find_one(Client.id == client_id, Client.is_deleted != True)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if current_user.role != UserRole.ADMIN:
        has_access = (client.owner_id == current_user.id or client.pm_id == current_user.id or client.referred_by_id == current_user.id)
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied")
    policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
    if not policy or policy.value == "SOFT":
        return await Feedback.find(Feedback.client_id == client_id, Feedback.is_deleted != True).to_list()
    return await Feedback.find(Feedback.client_id == client_id).to_list()

@router.get("/feedbacks/all", response_model=List[FeedbackRead])
async def read_all_client_feedbacks(current_user: User = Depends(staff_checker)) -> Any:
    from app.modules.salary.models import AppSetting
    policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
    query_filter = []
    if not policy or policy.value == "SOFT":
        query_filter.append(Feedback.is_deleted != True)
    feedbacks = await Feedback.find(*query_filter).sort(-Feedback.created_at).to_list()
    if current_user.role != UserRole.ADMIN:
        result = []
        for f in feedbacks:
            if f.client_id:
                client = await Client.find_one(Client.id == f.client_id)
                if client and (client.owner_id == current_user.id or client.pm_id == current_user.id or client.referred_by_id == current_user.id):
                    result.append(f)
        return result
    return feedbacks

@router.post("/user", response_model=UserFeedbackRead, status_code=status.HTTP_201_CREATED)
async def create_user_feedback(feedback_in: UserFeedbackCreate, current_user: User = Depends(get_current_user)) -> Any:
    user_id = current_user.id if current_user else 0
    feedback = UserFeedback(user_id=user_id, subject=feedback_in.subject, message=feedback_in.message)
    await feedback.insert()
    return feedback

@router.get("/user", response_model=List[UserFeedbackRead])
async def read_user_feedbacks(current_user: User = Depends(get_current_user)) -> Any:
    from app.modules.salary.models import AppSetting
    policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
    query_filter = []
    if not policy or policy.value == "SOFT":
        query_filter.append(UserFeedback.is_deleted != True)
    feedbacks = await UserFeedback.find(*query_filter).to_list()
    if current_user and current_user.role == UserRole.ADMIN:
        return feedbacks
    user_id = current_user.id if current_user else 0
    return [f for f in feedbacks if f.user_id == user_id]

@router.delete("/client/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client_feedback(feedback_id: int, current_user: User = Depends(admin_checker)) -> None:
    from app.modules.salary.models import AppSetting
    feedback = await Feedback.find_one(Feedback.id == feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
    if policy and policy.value == "HARD":
        await feedback.delete()
    else:
        feedback.is_deleted = True
        await feedback.save()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.delete("/user/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_feedback(feedback_id: int, current_user: User = Depends(admin_checker)) -> None:
    from app.modules.salary.models import AppSetting
    feedback = await UserFeedback.find_one(UserFeedback.id == feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="User feedback not found")
    policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
    if policy and policy.value == "HARD":
        await feedback.delete()
    else:
        feedback.is_deleted = True
        await feedback.save()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@global_router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(feedback_id: int, current_user: User = Depends(staff_checker)) -> None:
    from app.modules.salary.models import AppSetting
    feedback = await Feedback.find_one(Feedback.id == feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
    if policy and policy.value == "HARD":
        await feedback.delete()
    else:
        feedback.is_deleted = True
        await feedback.save()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
