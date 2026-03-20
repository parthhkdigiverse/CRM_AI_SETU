# backend/app/modules/notifications/service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

class EmailService:
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.sender_email = settings.SENDER_EMAIL or settings.SMTP_USERNAME

    def send_email(self, to_email: str, subject: str, body: str, is_html: bool = False):
        if not self.smtp_username or not self.smtp_password:
            print("SMTP credentials not set. Skipping email.")
            return

        msg = MIMEMultipart()
        msg["From"] = self.sender_email
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "html" if is_html else "plain"))

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.sender_email, to_email, msg.as_string())
            print(f"Email sent successfully to {to_email}")
        except Exception as e:
            print(f"Failed to send email: {e}")

    def send_pm_assignment_notification(
        self,
        pm_email: str,
        pm_name: str,
        client_name: str,
        client_org: str,
        client_phone: str,
    ):
        """Notify a PM that a new client has been auto-assigned to them."""
        subject = f"New Client Assigned: {client_name}"
        body = f"""
        <html>
            <body>
                <h2>Hello {pm_name},</h2>
                <p>A new client has been <strong>automatically assigned</strong> to you based on current workload.</p>
                <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
                    <tr><td><strong>Name</strong></td><td>{client_name}</td></tr>
                    <tr><td><strong>Organisation</strong></td><td>{client_org}</td></tr>
                    <tr><td><strong>Phone</strong></td><td>{client_phone}</td></tr>
                </table>
                <p>Please log in to the SRM to view full client details and get started.</p>
                <br>
                <p>Regards,<br>SRM AI SETU</p>
            </body>
        </html>
        """
        self.send_email(pm_email, subject, body, is_html=True)

    def send_issue_notification(self, pm_email: str, pm_name: str, project_name: str, issue_title: str, issue_description: str, reporter_role: str):
        subject = f"New Issue Reported: {project_name}"
        body = f"""
        <html>
            <body>
                <h2>Hello {pm_name},</h2>
                <p>A new issue has been reported for project <strong>{project_name}</strong>.</p>
                <ul>
                    <li><strong>Title:</strong> {issue_title}</li>
                    <li><strong>Description:</strong> {issue_description}</li>
                    <li><strong>Reported By:</strong> {reporter_role}</li>
                </ul>
                <p>Please check the CMS for more details.</p>
                <br>
                <p>Regards,<br>SRM System</p>
            </body>
        </html>
        """
        self.send_email(pm_email, subject, body, is_html=True)
