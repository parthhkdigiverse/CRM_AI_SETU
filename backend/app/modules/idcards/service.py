from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.modules.employees.models import Employee
from app.modules.idcards.schemas import IDCardData

class IDCardService:
    def __init__(self, db: Session):
        self.db = db

    def get_id_card_data(self, employee_id: int) -> IDCardData:
        employee = self.db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        user = employee.user
        
        return IDCardData(
            employee_name=user.name or "Employee",
            employee_code=employee.employee_code,
            role=user.role.value if hasattr(user.role, 'value') else str(user.role),
            joining_date=employee.joining_date,
            photo_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed={user.name or user.email}",
            qr_data=f"EMP:{employee.employee_code}|NAME:{user.name}"
        )

    def generate_id_card_html(self, employee_id: int) -> str:
        data = self.get_id_card_data(employee_id)
        
        html = f"""
        <html>
        <head>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
                body {{ font-family: 'Inter', sans-serif; display: flex; justify-content: center; padding: 40px; background: #f1f5f9; }}
                .id-card {{ 
                    width: 350px; height: 500px; background: white; border-radius: 20px; 
                    box-shadow: 0 10px 25px rgba(0,0,0,0.1); overflow: hidden; position: relative;
                    border: 1px solid #e2e8f0;
                }}
                .header {{ 
                    height: 120px; background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); 
                    display: flex; flex-direction: column; align-items: center; justify-content: center; color: white;
                }}
                .logo {{ font-weight: 800; font-size: 24px; letter-spacing: -0.5px; }}
                .subtitle {{ font-size: 11px; opacity: 0.8; text-transform: uppercase; letter-spacing: 1px; }}
                .photo-area {{ 
                    width: 120px; height: 120px; background: white; border-radius: 50%; 
                    margin: -60px auto 20px; border: 5px solid white; box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .photo-area img {{ width: 100%; height: 100%; object-fit: cover; }}
                .details {{ text-align: center; padding: 0 30px; }}
                .name {{ font-size: 22px; font-weight: 700; color: #1e293b; margin-bottom: 4px; }}
                .role {{ font-size: 14px; font-weight: 600; color: #6366f1; text-transform: uppercase; margin-bottom: 24px; }}
                .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; text-align: left; margin-bottom: 30px; }}
                .info-label {{ font-size: 10px; color: #64748b; text-transform: uppercase; font-weight: 600; margin-bottom: 2px; }}
                .info-value {{ font-size: 13px; color: #334155; font-weight: 600; }}
                .qr-section {{ border-top: 1px dashed #e2e8f0; padding-top: 20px; }}
                .footer {{ 
                    position: absolute; bottom: 0; width: 100%; height: 10px; 
                    background: linear-gradient(to right, #6366f1, #a855f7); 
                }}
            </style>
        </head>
        <body>
            <div class="id-card">
                <div class="header">
                    <div class="logo">CRM SETU</div>
                    <div class="subtitle">Official Employee ID</div>
                </div>
                <div class="photo-area">
                    <img src="{data.photo_url}" alt="Profile">
                </div>
                <div class="details">
                    <div class="name">{data.employee_name}</div>
                    <div class="role">{data.role}</div>
                    
                    <div class="info-grid">
                        <div>
                            <div class="info-label">Employee ID</div>
                            <div class="info-value">{data.employee_code}</div>
                        </div>
                        <div>
                            <div class="info-label">Joined On</div>
                            <div class="info-value">{data.joining_date}</div>
                        </div>
                    </div>
                    
                    <div class="qr-section">
                        <img src="https://api.qrserver.com/v1/create-qr-code/?size=80x80&data={data.qr_data}" alt="QR">
                    </div>
                </div>
                <div class="footer"></div>
            </div>
        </body>
        </html>
        """
        return html
    def generate_id_card_html_by_user(self, user_id: int) -> str:
        employee = self.db.query(Employee).filter(Employee.user_id == user_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee profile not found for this user")
        return self.generate_id_card_html(employee.id)
