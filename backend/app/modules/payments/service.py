from fastapi import HTTPException, status
from datetime import datetime, timezone
import uuid
from app.modules.payments.models import Payment, PaymentStatus
from app.modules.payments.schemas import PaymentCreate
from app.modules.clients.models import Client, ClientPMHistory
from app.modules.users.models import User, UserRole

class PaymentService:

    async def generate_payment_qr(self, payment_in: PaymentCreate, current_user: User, client_id: str = None, shop_id: str = None):
        if not client_id and not shop_id:
            raise HTTPException(status_code=400, detail="Must provide client_id or shop_id")
        client = None
        if client_id:
            client = await Client.find_one(Client.id == client_id)
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
        elif shop_id:
            from app.modules.shops.models import Shop
            import re
            shop = await Shop.find_one(Shop.id == shop_id)
            if not shop:
                raise HTTPException(status_code=404, detail="Shop not found")
            phone_val = shop.phone
            if phone_val:
                digits = re.sub(r"\D", "", phone_val)
                if len(digits) < 10:
                    phone_val = digits.zfill(10)
            else:
                phone_val = "0000000000"
            email_val = shop.email if shop.email else f"shop_{shop_id}_{uuid.uuid4().hex[:6]}@crm.demo"
            client = Client(name=shop.name, email=email_val, phone=phone_val, organization=shop.name, owner_id=current_user.id)
            await client.insert()
        qr_data = f"upi://pay?pa=business@upi&pn=CRM&am={payment_in.amount}&tr={uuid.uuid4()}"
        payment = Payment(client_id=client.id, amount=payment_in.amount, qr_code_data=qr_data, generated_by_id=current_user.id)
        await payment.insert()
        return payment

    async def verify_payment(self, payment_id: str, current_user: User):
        payment = await Payment.find_one(Payment.id == payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        if payment.status == PaymentStatus.VERIFIED:
            return payment
        try:
            payment.status = PaymentStatus.VERIFIED
            payment.verified_by_id = current_user.id
            payment.verified_at = datetime.now(timezone.utc)
            await payment.save()
            client = await Client.find_one(Client.id == payment.client_id)
            if not client:
                raise Exception("Associated Client not found")
            if not client.pm_id:
                active_pms = await User.find(User.role.in_([UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]), User.is_active == True).to_list()
                if active_pms:
                    count_map = {}
                    for pm in active_pms:
                        count = await Client.find(Client.pm_id == pm.id, Client.is_active == True).count()
                        count_map[pm.id] = count
                    pm = sorted(active_pms, key=lambda p: count_map.get(p.id, 0))[0]
                    client.pm_id = pm.id
                    history = ClientPMHistory(client_id=client.id, pm_id=pm.id)
                    await history.insert()
            await client.save()
            return payment
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")

    async def send_invoice_whatsapp(self, payment_id: str, current_user: User):
        payment = await Payment.find_one(Payment.id == payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        if payment.status != PaymentStatus.VERIFIED:
            raise HTTPException(status_code=400, detail="Cannot send invoice for unverified payment")
        client = await Client.find_one(Client.id == payment.client_id)
        print(f"Sending invoice to WhatsApp for {client.name} ({client.phone}) for amount {payment.amount}")
        return {"success": True, "message": f"Invoice successfully sent to WhatsApp for {client.name}."}
