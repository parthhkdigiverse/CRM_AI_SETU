from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Request
from app.modules.billing.models import Bill
from app.modules.billing.schemas import BillCreate
from app.modules.shops.models import Shop
from app.modules.clients.models import Client
from app.modules.clients.service import ClientService
from app.modules.clients.schemas import ClientCreate
from app.modules.users.models import User
import datetime
from datetime import UTC

import uuid

class BillingService:
    def __init__(self, db: Session):
        self.db = db
        self.client_service = ClientService(db)

    async def generate_bill_and_convert(self, bill_in: BillCreate, current_user: User, request: Request):
        # 1. Fetch Shop
        shop = self.db.query(Shop).filter(Shop.id == bill_in.shop_id).first()
        if not shop:
            raise HTTPException(status_code=404, detail="Shop not found")

        # 2. Find or Create Client
        # We search by email first, then phone if available
        client = None
        if shop.email:
            client = self.db.query(Client).filter(Client.email == shop.email).first()
        
        if not client and shop.phone:
            client = self.db.query(Client).filter(Client.phone == shop.phone).first()

        if not client:
            # Auto-convert Shop to Client
            # Note: create_client handles the round-robin PM assignment automatically now
            client_create = ClientCreate(
                name=shop.contact_person or shop.name,
                email=shop.email or f"client_{uuid.uuid4().hex[:8]}@placeholder.com",
                phone=shop.phone,
                organization=shop.name,
                address=shop.address,
                project_type=shop.project_type,
                requirements=shop.requirements,
                owner_id=current_user.id
            )
            client = await self.client_service.create_client(client_create, current_user, request)

        # 3. Create Bill
        invoice_no = f"INV-{datetime.datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

        db_bill = Bill(
            shop_id=shop.id,
            client_id=client.id,
            amount=bill_in.amount,
            invoice_number=invoice_no,
            status="PENDING_CONFIRMATION"
        )
        self.db.add(db_bill)
        self.db.commit()
        self.db.refresh(db_bill)

        return db_bill

    async def confirm_bill(self, bill_id: int):
        bill = self.get_bill(bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")
        
        bill.status = "CONFIRMED"
        self.db.commit()
        
        # Now send WhatsApp
        await self.send_whatsapp_invoice(bill, bill.client)
        return bill

    async def send_whatsapp_invoice(self, bill: Bill, client: Client):
        """
        Mock WhatsApp sending logic.
        """
        message = (
            f"Hello {client.name}, your bill for {bill.amount} with Invoice {bill.invoice_number} "
            f"has been generated. Please complete the payment. Thank you!"
        )
        print(f"--- WHATSAPP SEND (MOCK) ---")
        print(f"To: {client.phone}")
        print(f"Message: {message}")
        print(f"----------------------------")
        
        bill.whatsapp_sent = True
        self.db.commit()

    def get_bill(self, bill_id: int):
        return self.db.query(Bill).filter(Bill.id == bill_id).first()

    def get_all_bills(self, skip: int = 0, limit: int = 100):
        return self.db.query(Bill).offset(skip).limit(limit).all()
