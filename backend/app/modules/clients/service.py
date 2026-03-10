from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status, Request
from app.modules.clients.models import Client, ClientPMHistory
from app.modules.clients.schemas import ClientCreate, ClientUpdate
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.models import ActionType, EntityType
from app.modules.users.models import User, UserRole
from app.modules.notifications.service import EmailService
from sqlalchemy import func
from typing import List, Dict

class ClientService:
    def __init__(self, db: Session):
        self.db = db
        self.activity_logger = ActivityLogger(db)

    def get_client(self, client_id: int):
        return self.db.query(Client).filter(Client.id == client_id).first()

    def get_clients(self, skip: int = 0, limit: int = 100, search: str = None, sort_by: str = "created_at", sort_order: str = "desc", include_inactive: bool = False, pm_id: int = None):
        try:
            query = self.db.query(Client)
            if not include_inactive:
                query = query.filter(Client.is_active == True)
            if pm_id:
                query = query.filter(Client.pm_id == pm_id)
            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    (Client.name.ilike(search_pattern)) | 
                    (Client.phone.ilike(search_pattern))
                )
            
            # Sorting Whitelist Hardening
            allowed_sort_fields = {"name", "phone", "created_at"}
            
            if sort_by not in allowed_sort_fields:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid sort column. Allowed: {', '.join(allowed_sort_fields)}")

            if hasattr(Client, sort_by):
                column = getattr(Client, sort_by)
                if sort_order.lower() == "desc":
                    query = query.order_by(column.desc())
                else:
                    query = query.order_by(column.asc())

            clients = query.offset(skip).limit(limit).all()
            for c in clients:
                if c.pm:
                    c.pm_name = c.pm.name or c.pm.email or c.pm.employee_code or f"PM #{c.pm_id}"
            return clients
        except Exception as e:
            print(f"Error fetching clients: {e}")
            return []

    async def create_client(self, client: ClientCreate, current_user: User, request: Request):
        db_client = Client(**client.model_dump())

        # --- Workload-balanced PM Auto-Assignment ---
        active_pms = self.db.query(User).filter(
            User.role.in_([UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]),
            User.is_active == True
        ).all()

        assigned_pm: User = None

        if active_pms:
            pm_ids = [pm.id for pm in active_pms]

            # Count active clients per PM
            client_counts = self.db.query(
                Client.pm_id,
                func.count(Client.id).label("client_count")
            ).filter(
                Client.pm_id.in_(pm_ids),
                Client.is_active == True
            ).group_by(Client.pm_id).all()

            count_map = {row.pm_id: row.client_count for row in client_counts}

            # Build list of (pm, workload)
            pm_workloads = [(pm, count_map.get(pm.id, 0)) for pm in active_pms]
            
            # Find the minimum workload
            min_load = min(w[1] for w in pm_workloads)
            
            # Filter all PMs who have this minimum load
            least_loaded_pms = [w[0] for w in pm_workloads if w[1] == min_load]
            
            # Randomly pick one among the least loaded to distribute fairly
            import random
            assigned_pm = random.choice(least_loaded_pms)

            db_client.pm_id = assigned_pm.id
        # -------------------------------------------

        try:
            self.db.add(db_client)
            self.db.commit()
            self.db.refresh(db_client)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client with this phone number or email already exists.")

        # Record PM assignment history
        if assigned_pm:
            history = ClientPMHistory(client_id=db_client.id, pm_id=assigned_pm.id)
            self.db.add(history)
            self.db.commit()

            # Notify the assigned PM by email (non-blocking; errors are swallowed)
            try:
                email_svc = EmailService()
                email_svc.send_pm_assignment_notification(
                    pm_email=assigned_pm.email,
                    pm_name=assigned_pm.name or assigned_pm.email,
                    client_name=db_client.name,
                    client_org=db_client.organization or "-",
                    client_phone=db_client.phone or "-",
                )
            except Exception as e:
                print(f"[PM Notify] Email failed (non-fatal): {e}")

        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=ActionType.CREATE,
            entity_type=EntityType.CLIENT,
            entity_id=db_client.id,
            old_data=None,
            new_data={**client.model_dump(), "auto_assigned_pm_id": assigned_pm.id if assigned_pm else None},
            request=request
        )

        return db_client

    # ------------------------------------------------------------------
    # PM Workload helpers
    # ------------------------------------------------------------------

    def get_pm_workload(self) -> List[Dict]:
        """Return a list of all active PMs with their current active-client counts."""
        active_pms = self.db.query(User).filter(
            User.role.in_([UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]),
            User.is_active == True
        ).all()

        if not active_pms:
            return []

        pm_ids = [pm.id for pm in active_pms]
        client_counts = self.db.query(
            Client.pm_id,
            func.count(Client.id).label("client_count")
        ).filter(
            Client.pm_id.in_(pm_ids),
            Client.is_active == True
        ).group_by(Client.pm_id).all()

        count_map = {row.pm_id: row.client_count for row in client_counts}

        return [
            {
                "pm_id": pm.id,
                "pm_name": pm.name or pm.email,
                "pm_email": pm.email,
                "role": pm.role,
                "active_client_count": count_map.get(pm.id, 0),
            }
            for pm in sorted(active_pms, key=lambda p: count_map.get(p.id, 0))
        ]

    def get_pm_history(self, client_id: int) -> List[ClientPMHistory]:
        """Return the full PM assignment history for a given client."""
        return (
            self.db.query(ClientPMHistory)
            .filter(ClientPMHistory.client_id == client_id)
            .order_by(ClientPMHistory.assigned_at.asc())
            .all()
        )

    async def update_client(self, client_id: int, client_update: ClientUpdate, current_user: User, request: Request):
        db_client = self.get_client(client_id)
        if not db_client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

        old_data = {
            "name": db_client.name,
            "email": db_client.email,
            "phone": db_client.phone,
            "organization": db_client.organization
        }

        update_data = client_update.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(db_client, key, value)

        try:
            self.db.commit()
            self.db.refresh(db_client)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client with this phone number or email already exists.")

        new_data = {k: getattr(db_client, k) for k in old_data.keys()}

        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=ActionType.UPDATE,
            entity_type=EntityType.CLIENT,
            entity_id=client_id,
            old_data=old_data,
            new_data=new_data,
            request=request
        )

        return db_client

    async def delete_client(self, client_id: int, current_user: User, request: Request):
        db_client = self.get_client(client_id)
        if not db_client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

        old_data = {
            "name": db_client.name,
            "email": db_client.email,
            "phone": db_client.phone,
            "organization": db_client.organization
        }

        db_client.is_active = False
        self.db.add(db_client)
        self.db.commit()

        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=ActionType.DELETE,
            entity_type=EntityType.CLIENT,
            entity_id=client_id,
            old_data=old_data,
            new_data=None, # Deleted
            request=request
        )

        return {"detail": "Client deleted"}

    async def assign_pm(self, client_id: int, pm_id: int, current_user: User, request: Request):
        db_client = self.get_client(client_id)
        if not db_client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

        # Verify PM exists and has correct role
        from app.modules.users.models import UserRole
        pm = self.db.query(User).filter(User.id == pm_id).first()
        if not pm or pm.role not in [UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES] or not pm.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or inactive Project Manager ID")

        old_pm_id = db_client.pm_id
        if old_pm_id == pm_id:
            return db_client # Unchanged

        db_client.pm_id = pm_id
        
        # Keep minimal PM history table
        from app.modules.clients.models import ClientPMHistory
        history = ClientPMHistory(client_id=db_client.id, pm_id=pm.id)
        self.db.add(history)
        
        self.db.commit()
        self.db.refresh(db_client)

        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=ActionType.UPDATE,
            entity_type=EntityType.CLIENT,
            entity_id=client_id,
            old_data={"pm_id": old_pm_id},
            new_data={"pm_id": pm_id},
            request=request
        )

        return db_client
