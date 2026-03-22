from fastapi import HTTPException, status, Request
from app.modules.clients.models import Client, ClientPMHistory
from app.modules.clients.schemas import ClientCreate, ClientUpdate
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.models import ActionType, EntityType
from app.modules.users.models import User, UserRole
from typing import List, Dict
import random

class ClientService:
    def __init__(self):
        self.activity_logger = ActivityLogger()

    async def get_client(self, client_id: str):
        return await Client.find_one(Client.id == client_id, Client.is_deleted != True)

    async def get_clients(self, skip=0, limit=100, search=None, sort_by="created_at", sort_order="desc", include_inactive=False, pm_id=None, is_active=True, owner_id=None, referred_by_id=None, scoped_user_id=None, scoped_mode=None):
        try:
            query_filter = [Client.is_deleted != True]
            if is_active is True:
                query_filter.append(Client.is_active == True)
            elif is_active is False:
                query_filter.append(Client.is_active == False)
            elif not include_inactive:
                query_filter.append(Client.is_active == True)
            if scoped_user_id and scoped_mode:
                mode = str(scoped_mode).lower()
                if mode == "owner":
                    query_filter.append(Client.owner_id == scoped_user_id)
                elif mode == "pm":
                    query_filter.append(Client.pm_id == scoped_user_id)
            elif pm_id:
                query_filter.append(Client.pm_id == pm_id)
            if owner_id:
                query_filter.append(Client.owner_id == owner_id)
            if referred_by_id:
                query_filter.append(Client.referred_by_id == referred_by_id)
            clients = await Client.find(*query_filter).skip(skip).limit(limit).to_list()
            if search:
                token = search.strip().lower()
                clients = [c for c in clients if token in (c.name or "").lower() or token in (c.phone or "").lower() or token in (c.email or "").lower() or token in (c.organization or "").lower()]
            for c in clients:
                if c.pm_id:
                    pm = await User.find_one(User.id == c.pm_id)
                    if pm:
                        c.pm_name = pm.name or pm.email or f"PM #{c.pm_id}"
            return clients
        except Exception as e:
            print(f"Error fetching clients: {e}")
            return []

    async def _get_least_loaded_pm(self) -> User:
        active_pms = await User.find(User.role.in_([UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]), User.is_active == True).to_list()
        if not active_pms:
            return None
        pm_ids = [pm.id for pm in active_pms]
        count_map = {}
        for pm_id in pm_ids:
            count = await Client.find(Client.pm_id == pm_id, Client.is_active == True).count()
            count_map[pm_id] = count
        pm_workloads = [(pm, count_map.get(pm.id, 0)) for pm in active_pms]
        min_load = min(w[1] for w in pm_workloads)
        least_loaded_pms = [w[0] for w in pm_workloads if w[1] == min_load]
        return random.choice(least_loaded_pms)

    async def create_client(self, client: ClientCreate, current_user: User, request: Request):
        db_client = Client(**client.model_dump())
        assigned_pm = await self._get_least_loaded_pm()
        if assigned_pm:
            db_client.pm_id = assigned_pm.id
        else:
            print("[PM Auto-Assign] WARNING: No active Project Managers found.")
        try:
            await db_client.insert()
            if assigned_pm:
                history = ClientPMHistory(client_id=db_client.id, pm_id=assigned_pm.id)
                await history.insert()
                try:
                    from app.modules.notifications.service import EmailService
                    email_svc = EmailService()
                    email_svc.send_pm_assignment_notification(pm_email=assigned_pm.email, pm_name=assigned_pm.name or assigned_pm.email, client_name=db_client.name, client_org=db_client.organization or "-", client_phone=db_client.phone or "-")
                except Exception as e:
                    print(f"[PM Notify] Email failed (non-fatal): {e}")
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client with this phone number or email already exists.")
        await self.activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=ActionType.CREATE, entity_type=EntityType.CLIENT, entity_id=db_client.id, old_data=None, new_data={**client.model_dump(), "auto_assigned_pm_id": assigned_pm.id if assigned_pm else None}, request=request)
        return db_client

    async def get_pm_workload(self) -> List[Dict]:
        active_pms = await User.find(User.role.in_([UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]), User.is_active == True).to_list()
        if not active_pms:
            return []
        result = []
        for pm in active_pms:
            count = await Client.find(Client.pm_id == pm.id, Client.is_active == True).count()
            result.append({"pm_id": pm.id, "pm_name": pm.name or pm.email, "pm_email": pm.email, "role": pm.role, "active_client_count": count})
        return sorted(result, key=lambda x: x["active_client_count"])

    async def retroactive_pm_balance(self):
        stuck_clients = await Client.find(Client.pm_id == None, Client.is_active == True).to_list()
        if not stuck_clients:
            return {"detail": "No unassigned clients found.", "count": 0}
        active_pms = await User.find(User.role.in_([UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]), User.is_active == True).to_list()
        if not active_pms:
            raise HTTPException(status_code=400, detail="Cannot balance: No active Project Managers available.")
        processed_count = 0
        for client in stuck_clients:
            assigned_pm = await self._get_least_loaded_pm()
            client.pm_id = assigned_pm.id
            await client.save()
            history = ClientPMHistory(client_id=client.id, pm_id=assigned_pm.id)
            await history.insert()
            processed_count += 1
        return {"detail": f"Successfully balanced {processed_count} unassigned clients.", "count": processed_count}

    async def get_pm_history(self, client_id: str):
        return await ClientPMHistory.find(ClientPMHistory.client_id == client_id).sort(+ClientPMHistory.assigned_at).to_list()

    async def update_client(self, client_id: str, client_update: ClientUpdate, current_user: User, request: Request):
        db_client = await self.get_client(client_id)
        if not db_client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
        old_data = {"name": db_client.name, "email": db_client.email, "phone": db_client.phone, "organization": db_client.organization}
        update_data = client_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_client, key, value)
        try:
            await db_client.save()
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client with this phone number or email already exists.")
        new_data = {k: getattr(db_client, k) for k in old_data.keys()}
        await self.activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=ActionType.UPDATE, entity_type=EntityType.CLIENT, entity_id=client_id, old_data=old_data, new_data=new_data, request=request)
        return db_client

    async def delete_client(self, client_id: str, current_user: User, request: Request):
        db_client = await Client.find_one(Client.id == client_id)
        if not db_client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
        from app.modules.salary.models import AppSetting
        policy = await AppSetting.find_one(AppSetting.key == "delete_policy")
        is_hard = policy and policy.value == "HARD"
        old_data = {"name": db_client.name, "email": db_client.email, "phone": db_client.phone, "organization": db_client.organization, "policy": "HARD" if is_hard else "SOFT"}
        if is_hard:
            await db_client.delete()
        else:
            db_client.is_deleted = True
            db_client.is_active = False
            await db_client.save()
        await self.activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=ActionType.DELETE, entity_type=EntityType.CLIENT, entity_id=client_id, old_data=old_data, new_data=None, request=request)
        return {"detail": f"Client {'permanently ' if is_hard else ''}deleted"}

    async def assign_pm(self, client_id: str, pm_id: str, current_user: User, request: Request):
        db_client = await self.get_client(client_id)
        if not db_client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
        pm = await User.find_one(User.id == pm_id)
        if not pm or pm.role not in [UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES] or not pm.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or inactive Project Manager ID")
        old_pm_id = db_client.pm_id
        if old_pm_id == pm_id:
            return db_client
        db_client.pm_id = pm_id
        history = ClientPMHistory(client_id=db_client.id, pm_id=pm.id)
        await history.insert()
        await db_client.save()
        await self.activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=ActionType.UPDATE, entity_type=EntityType.CLIENT, entity_id=client_id, old_data={"pm_id": old_pm_id}, new_data={"pm_id": pm_id}, request=request)
        return db_client
