import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.sender_email = os.getenv("SENDER_EMAIL", self.smtp_username)

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
                <p>Regards,<br>CRM System</p>
            </body>
        </html>
        """
        self.send_email(pm_email, subject, body, is_html=True)
