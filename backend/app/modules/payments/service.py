from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from datetime import datetime
import uuid

from app.modules.payments.models import Payment, PaymentStatus
from app.modules.payments.schemas import PaymentCreate
from app.modules.clients.models import Client, ClientPMHistory
from app.modules.users.models import User, UserRole

class PaymentService:
    def __init__(self, db: Session):
        self.db = db

    def generate_payment_qr(self, client_id: int, payment_in: PaymentCreate, current_user: User):
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Mock QR generation data URL
        qr_data = f"upi://pay?pa=business@upi&pn=CRM&am={payment_in.amount}&tr={uuid.uuid4()}"
        
        payment = Payment(
            client_id=client.id,
            amount=payment_in.amount,
            qr_code_data=qr_data,
            generated_by_id=current_user.id
        )
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def verify_payment(self, payment_id: int, current_user: User):
        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
            
        # 1. Idempotency Check
        if payment.status == PaymentStatus.VERIFIED:
            # Already verified, do nothing and return. Prevents double assignment.
            return payment
            
        # 2. Transactional execution
        try:
            # Mark payment as verified
            payment.status = PaymentStatus.VERIFIED
            payment.verified_by_id = current_user.id
            payment.verified_at = datetime.utcnow()
            
            client = self.db.query(Client).filter(Client.id == payment.client_id).first()
            if not client:
                raise Exception("Associated Client not found")
            
            # Auto-assign PM
            if not client.pm_id:
                # Load Balanced PM Assignment (fewest active clients first)
                pm = self.db.query(User).filter(
                    User.role.in_([UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]), 
                    User.is_active == True
                ).outerjoin(
                    Client, (Client.pm_id == User.id) & (Client.is_active == True)
                ).group_by(
                    User.id
                ).order_by(
                    func.count(Client.id).asc()
                ).first()
                
                if pm:
                    client.pm_id = pm.id
                    # 4. Keep minimal PM history table
                    history = ClientPMHistory(client_id=client.id, pm_id=pm.id)
                    self.db.add(history)
            
            # Commit the transaction (all or nothing)
            self.db.add(payment)
            self.db.add(client)
            self.db.commit()
            self.db.refresh(payment)
            
            return payment
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")

    def send_invoice_whatsapp(self, payment_id: int, current_user: User):
        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
            
        if payment.status != PaymentStatus.VERIFIED:
            raise HTTPException(status_code=400, detail="Cannot send invoice for unverified payment")
            
        client = self.db.query(Client).filter(Client.id == payment.client_id).first()
        
        # Mock WhatsApp API Call integration
        print(f"Sending invoice to WhatsApp for {client.name} ({client.phone}) for amount {payment.amount}")
        
        return {
            "success": True,
            "message": f"Invoice successfully sent to WhatsApp for {client.name}."
        }
